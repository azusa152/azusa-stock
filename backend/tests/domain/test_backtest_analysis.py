from datetime import UTC, datetime

from domain.analysis.backtest import (
    BacktestSignalEvent,
    classify_confidence,
    compute_forward_returns,
    compute_signal_metrics,
    deduplicate_signal_events,
)


def test_deduplicate_signal_events_should_collapse_consecutive_same_signal_per_ticker():
    logs = [
        BacktestSignalEvent(
            ticker="AAPL",
            signal="OVERSOLD",
            market_status="BULLISH",
            scanned_at=datetime(2026, 1, 1, tzinfo=UTC),
        ),
        BacktestSignalEvent(
            ticker="AAPL",
            signal="OVERSOLD",
            market_status="BULLISH",
            scanned_at=datetime(2026, 1, 2, tzinfo=UTC),
        ),
        BacktestSignalEvent(
            ticker="AAPL",
            signal="CONTRARIAN_BUY",
            market_status="BULLISH",
            scanned_at=datetime(2026, 1, 3, tzinfo=UTC),
        ),
    ]

    deduped = deduplicate_signal_events(logs)

    assert len(deduped) == 2
    assert deduped[0].signal == "OVERSOLD"
    assert deduped[1].signal == "CONTRARIAN_BUY"


def test_compute_forward_returns_should_use_trading_day_indexing():
    prices = [
        {"date": "2026-01-02", "close": 100.0},
        {"date": "2026-01-05", "close": 110.0},
        {"date": "2026-01-06", "close": 121.0},
    ]

    returns = compute_forward_returns(
        signal_date=datetime(2026, 1, 2, tzinfo=UTC).date(),
        price_series=prices,
        windows=[1, 2],
    )

    assert returns[1] == 10.0
    assert returns[2] == 21.0


def test_compute_forward_returns_should_return_none_when_window_out_of_range():
    prices = [
        {"date": "2026-01-02", "close": 100.0},
        {"date": "2026-01-05", "close": 110.0},
    ]

    returns = compute_forward_returns(
        signal_date=datetime(2026, 1, 2, tzinfo=UTC).date(),
        price_series=prices,
        windows=[5],
    )

    assert returns[5] is None


def test_compute_signal_metrics_should_calculate_buy_hit_and_false_positive_rates():
    metrics = compute_signal_metrics(
        forward_returns=[{30: 5.0}, {30: -2.0}, {30: 1.0}],
        signal_type="DEEP_VALUE",
    )

    assert metrics["direction"] == "buy"
    assert metrics["false_positive_rate"] == 0.3333
    window_30 = next(w for w in metrics["windows"] if w["window_days"] == 30)
    assert window_30["hit_rate"] == 0.6667
    assert window_30["sample_count"] == 3


def test_compute_signal_metrics_should_calculate_sell_hit_and_false_positive_rates():
    metrics = compute_signal_metrics(
        forward_returns=[{30: -4.0}, {30: 3.0}, {30: -1.0}],
        signal_type="THESIS_BROKEN",
    )

    assert metrics["direction"] == "sell"
    assert metrics["false_positive_rate"] == 0.3333
    window_30 = next(w for w in metrics["windows"] if w["window_days"] == 30)
    assert window_30["hit_rate"] == 0.6667


def test_classify_confidence_should_respect_boundaries():
    assert classify_confidence(9) == "low"
    assert classify_confidence(10) == "medium"
    assert classify_confidence(29) == "medium"
    assert classify_confidence(30) == "high"
