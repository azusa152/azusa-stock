import os
import tempfile
from unittest.mock import patch

# Set environment variables BEFORE any app imports
os.environ.setdefault("LOG_DIR", os.path.join(tempfile.gettempdir(), "folio_test_logs"))
os.environ.setdefault("DATABASE_URL", "sqlite://")

import domain.constants
from domain.enums import FearGreedLevel
from infrastructure.market_data import market_data

domain.constants.DISK_CACHE_DIR = os.path.join(
    tempfile.gettempdir(), "folio_test_cache_fear_greed"
)


@patch("infrastructure.market_data.market_data.compute_composite_fear_greed")
@patch("infrastructure.market_data.market_data.compute_weighted_fear_greed")
@patch("infrastructure.market_data.market_data._fetch_fg_component_history_safe")
@patch("infrastructure.market_data.market_data.get_cnn_fear_greed")
@patch("infrastructure.market_data.market_data.get_vix_data")
def test_fetch_fear_greed_should_fetch_all_components_in_parallel_path(
    mock_vix,
    mock_cnn,
    mock_fetch_component,
    mock_weighted,
    mock_composite,
):
    mock_vix.return_value = {"value": 20.0}
    mock_cnn.return_value = {"score": 60}
    mock_fetch_component.return_value = [100.0, 101.0, 102.0]
    mock_weighted.return_value = (FearGreedLevel.GREED, 55)
    mock_composite.return_value = (FearGreedLevel.GREED, 58)
    real_pool_cls = market_data.ThreadPoolExecutor
    with patch(
        "infrastructure.market_data.market_data.ThreadPoolExecutor",
        wraps=real_pool_cls,
    ) as mock_pool_cls:
        result = market_data._fetch_fear_greed("composite")

    assert result["composite_score"] == 58
    assert result["composite_level"] == FearGreedLevel.GREED.value
    assert result["self_calculated_score"] == 55
    assert "components" in result
    assert "fetched_at" in result

    expected_tickers = {
        domain.constants.FG_SPY_TICKER,
        domain.constants.FG_TLT_TICKER,
        domain.constants.FG_HYG_TICKER,
        domain.constants.FG_RSP_TICKER,
        domain.constants.FG_QQQ_TICKER,
        domain.constants.FG_XLP_TICKER,
    }
    called_tickers = {args[0] for args, _ in mock_fetch_component.call_args_list}
    assert called_tickers == expected_tickers
    assert mock_fetch_component.call_count == 6
    mock_pool_cls.assert_called_once_with(max_workers=8)
