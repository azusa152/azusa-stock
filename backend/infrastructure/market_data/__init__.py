"""infrastructure.market_data sub-package — market data adapters (yfinance, J-Quants, FinMind).

Re-exports the public API of market_data.market_data so that
``from infrastructure.market_data import X`` continues to work unchanged.
"""

from infrastructure.market_data.market_data import (  # noqa: F401
    RateLimiter,
    analyze_market_sentiment,
    analyze_moat_trend,
    batch_download_history,
    clear_all_caches,
    detect_is_etf,
    get_bias_distribution,
    get_cnn_fear_greed,
    get_dividend_info,
    get_earnings_date,
    get_etf_sector_weights,
    get_etf_top_holdings,
    get_exchange_rate,
    get_exchange_rates,
    get_fear_greed_index,
    get_forex_history,
    get_forex_history_long,
    get_jp_volatility_index,
    get_price_history,
    get_stock_beta,
    get_technical_signals,
    get_ticker_sector,
    get_ticker_sector_cached,
    get_tw_volatility_index,
    get_vix_data,
    prewarm_beta_batch,
    prewarm_etf_holdings_batch,
    prewarm_etf_sector_weights_batch,
    prewarm_moat_batch,
    prewarm_signals_batch,
    prime_signals_cache_batch,
)
