"""
Tests for _deduped_fetch in-flight deduplication logic.

Covers:
- Two concurrent threads with the same key: only one fetcher call is made.
- Waiter thread receives the result via result_getter after the fetcher completes.
- Independent keys are fetched concurrently without interference.
- Fetcher exception: waiters fall through to result_getter (which retries via fetcher).
"""

import os
import tempfile
import threading

# Set environment variables BEFORE any app imports
os.environ.setdefault("LOG_DIR", os.path.join(tempfile.gettempdir(), "folio_test_logs"))
os.environ.setdefault("DATABASE_URL", "sqlite://")

import domain.constants  # noqa: E402

domain.constants.DISK_CACHE_DIR = os.path.join(
    tempfile.gettempdir(), "folio_test_cache_dedup"
)


import pytest  # noqa: E402

from infrastructure.market_data import _deduped_fetch, _inflight_events  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_barrier_fetcher(barrier: threading.Barrier, return_value):
    """Return a fetcher that waits at a barrier so threads can be synchronised."""
    call_count = {"n": 0}

    def _fetcher():
        call_count["n"] += 1
        barrier.wait()  # both threads rendezvous here before fetcher "finishes"
        return return_value

    return _fetcher, call_count


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestDedupedFetch:
    """_deduped_fetch should ensure only one yfinance call per in-flight key."""

    def setup_method(self):
        # Clear any leftover in-flight state between tests
        _inflight_events.clear()

    def test_two_concurrent_threads_same_key_should_call_fetcher_once(self):
        """Only the first thread calls the fetcher; the second waits and reads from result_getter."""
        fetcher_calls = {"n": 0}
        getter_calls = {"n": 0}
        results = {}
        fetcher_started = threading.Event()
        fetcher_can_finish = threading.Event()

        def _slow_fetcher():
            fetcher_calls["n"] += 1
            fetcher_started.set()  # signal: I'm inside the fetcher
            fetcher_can_finish.wait(timeout=5)
            return "fetched_value"

        def _result_getter():
            getter_calls["n"] += 1
            return "cached_value"

        # t1 starts first and becomes the fetcher (held open until we release it)
        t1 = threading.Thread(
            target=lambda: results.update(
                {"t1": _deduped_fetch("signals:AAPL", _slow_fetcher, _result_getter)}
            )
        )
        t1.start()
        fetcher_started.wait(timeout=5)  # wait until t1 is inside _slow_fetcher

        # t2 arrives while t1 is still fetching — it should become the waiter
        t2 = threading.Thread(
            target=lambda: results.update(
                {"t2": _deduped_fetch("signals:AAPL", _slow_fetcher, _result_getter)}
            )
        )
        t2.start()

        # Release the fetcher once t2 is likely waiting on the in-flight event
        import time

        time.sleep(0.05)
        fetcher_can_finish.set()
        t1.join(timeout=5)
        t2.join(timeout=5)

        # t1 called fetcher exactly once; t2 went through result_getter
        assert fetcher_calls["n"] == 1
        assert getter_calls["n"] == 1
        assert results["t1"] == "fetched_value"
        assert results["t2"] == "cached_value"

    def test_waiter_receives_result_from_result_getter(self):
        """Thread waiting on an in-flight key gets its result from result_getter, not fetcher."""
        ready_event = threading.Event()
        release_event = threading.Event()

        def _slow_fetcher():
            ready_event.set()  # signal that fetcher has started
            release_event.wait()  # hold until test releases
            return "fetcher_result"

        results = {}

        def _fast_getter():
            return "getter_result"

        # Start a thread that will be the "fetcher" and hold
        def _fetcher_thread():
            results["fetcher"] = _deduped_fetch(
                "signals:TSLA", _slow_fetcher, _fast_getter
            )

        ft = threading.Thread(target=_fetcher_thread)
        ft.start()
        ready_event.wait(timeout=3)  # wait until fetcher is in-flight

        # Now a second thread arrives — it should wait and then call result_getter
        def _waiter_thread():
            results["waiter"] = _deduped_fetch(
                "signals:TSLA", _slow_fetcher, _fast_getter
            )

        wt = threading.Thread(target=_waiter_thread)
        wt.start()

        # Release the fetcher
        release_event.set()
        ft.join(timeout=5)
        wt.join(timeout=5)

        assert results["fetcher"] == "fetcher_result"
        assert results["waiter"] == "getter_result"

    def test_independent_keys_do_not_interfere(self):
        """Separate keys each run their own fetcher independently."""
        fetcher_calls = []

        def _make_fetcher(key):
            def _f():
                fetcher_calls.append(key)
                return f"result_{key}"

            return _f

        def _getter():
            return "should_not_be_called"

        results = {}
        threads = []
        for key in ("signals:AAPL", "signals:NVDA", "signals:TSLA"):
            k = key  # capture

            def _run(k=k):
                results[k] = _deduped_fetch(k, _make_fetcher(k), _getter)

            threads.append(threading.Thread(target=_run))

        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5)

        # All three fetchers were called (each key is independent)
        assert sorted(fetcher_calls) == [
            "signals:AAPL",
            "signals:NVDA",
            "signals:TSLA",
        ]
        assert results["signals:AAPL"] == "result_signals:AAPL"

    def test_fetcher_exception_propagates_to_fetching_thread(self):
        """If the fetcher raises, the fetching thread re-raises; the event is still set."""

        def _bad_fetcher():
            raise ValueError("yfinance unavailable")

        def _getter():
            return "fallback"

        with pytest.raises(ValueError, match="yfinance unavailable"):
            _deduped_fetch("signals:BAD", _bad_fetcher, _getter)

        # Event must be cleaned up so subsequent calls can proceed
        assert "signals:BAD" not in _inflight_events

    def test_after_fetcher_exception_waiter_calls_result_getter(self):
        """Waiters wake up after fetcher exception and call result_getter (which retries)."""
        ready_event = threading.Event()
        release_event = threading.Event()
        getter_calls = {"n": 0}

        def _bad_fetcher():
            ready_event.set()
            release_event.wait()
            raise RuntimeError("fetch failed")

        def _getter():
            getter_calls["n"] += 1
            return "fallback_value"

        results = {}
        errors = {}

        def _fetcher_thread():
            try:
                results["fetcher"] = _deduped_fetch(
                    "signals:ERR", _bad_fetcher, _getter
                )
            except RuntimeError as exc:
                errors["fetcher"] = exc

        def _waiter_thread():
            results["waiter"] = _deduped_fetch("signals:ERR", _bad_fetcher, _getter)

        ft = threading.Thread(target=_fetcher_thread)
        ft.start()
        ready_event.wait(timeout=3)

        wt = threading.Thread(target=_waiter_thread)
        wt.start()

        release_event.set()
        ft.join(timeout=5)
        wt.join(timeout=5)

        # Fetcher thread raised; waiter got fallback from result_getter
        assert "fetcher" in errors
        assert results.get("waiter") == "fallback_value"
        assert getter_calls["n"] == 1
