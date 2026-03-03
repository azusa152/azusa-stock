from unittest.mock import patch

from domain.constants import MOAT_PERSISTENT_FAILURE_THRESHOLD
from domain.enums import MoatStatus
from infrastructure.market_data import market_data


def _na_result(ticker: str = "NET") -> dict:
    return {
        "ticker": ticker,
        "moat": MoatStatus.NOT_AVAILABLE.value,
        "details": "N/A failed to get new data",
    }


def _ok_result(ticker: str = "NET") -> dict:
    return {
        "ticker": ticker,
        "moat": MoatStatus.STABLE.value,
        "details": "ok",
    }


def setup_function() -> None:
    market_data._moat_failure_counts.clear()


@patch("infrastructure.market_data.market_data._disk_set")
@patch("infrastructure.market_data.market_data._cached_fetch")
def test_should_not_write_sentinel_before_threshold(mock_cached_fetch, mock_disk_set):
    mock_cached_fetch.return_value = _na_result()

    for _ in range(MOAT_PERSISTENT_FAILURE_THRESHOLD - 1):
        market_data.analyze_moat_trend("NET")

    assert mock_disk_set.call_count == 0


@patch("infrastructure.market_data.market_data._disk_set")
@patch("infrastructure.market_data.market_data._cached_fetch")
def test_should_write_sentinel_only_once_when_threshold_crossed(
    mock_cached_fetch, mock_disk_set
):
    mock_cached_fetch.return_value = _na_result()

    for _ in range(MOAT_PERSISTENT_FAILURE_THRESHOLD + 2):
        market_data.analyze_moat_trend("NET")

    mock_disk_set.assert_called_once()


@patch("infrastructure.market_data.market_data._disk_set")
@patch("infrastructure.market_data.market_data._cached_fetch")
def test_should_reset_failure_count_on_success(mock_cached_fetch, mock_disk_set):
    # Reach threshold once.
    mock_cached_fetch.return_value = _na_result()
    for _ in range(MOAT_PERSISTENT_FAILURE_THRESHOLD):
        market_data.analyze_moat_trend("NET")
    mock_disk_set.assert_called_once()

    # Success resets state.
    mock_cached_fetch.return_value = _ok_result()
    market_data.analyze_moat_trend("NET")

    # Need threshold failures again to write one more time.
    mock_cached_fetch.return_value = _na_result()
    for _ in range(MOAT_PERSISTENT_FAILURE_THRESHOLD):
        market_data.analyze_moat_trend("NET")

    assert mock_disk_set.call_count == 2
