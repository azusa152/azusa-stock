"""domain.analysis sub-package — technical analysis, FX analysis, smart money."""

from domain.analysis.analysis import (  # noqa: F401
    classify_cnn_fear_greed,
    classify_vix,
    compute_bias,
    compute_bias_percentile,
    compute_composite_fear_greed,
    compute_daily_change_pct,
    compute_moving_average,
    compute_rsi,
    compute_twr,
    compute_volume_ratio,
    compute_weighted_fear_greed,
    detect_rogue_wave,
    determine_market_sentiment,
    determine_moat_status,
    determine_scan_signal,
    score_breadth,
    score_junk_bond_demand,
    score_momentum_composite,
    score_nikkei_vi_linear,
    score_price_strength,
    score_safe_haven,
    score_sector_rotation,
    score_tw_vol_linear,
    score_vix_linear,
)
from domain.analysis.fx_analysis import (  # noqa: F401
    FXRateAlert,
    FXTimingResult,
    analyze_fx_rate_changes,
    assess_exchange_timing,
    count_consecutive_increases,
    determine_fx_risk_level,
    is_recent_high,
)
from domain.analysis.smart_money import (  # noqa: F401
    classify_holding_change,
    compute_change_pct,
    compute_holding_weight,
    compute_resonance_matches,
)
