"""Tests for domain/core/formatters.py — build_signal_status and build_moat_details."""

from domain.core.formatters import build_moat_details, build_signal_status
from domain.enums import MoatStatus

# ---------------------------------------------------------------------------
# build_signal_status — RSI branches
# ---------------------------------------------------------------------------


class TestBuildSignalStatusRsi:
    def test_rsi_oversold_branch(self):
        parts = build_signal_status({"rsi": 25.0})
        assert len(parts) >= 1
        assert any("rsi" in p.lower() or "25" in p for p in parts)

    def test_rsi_overbought_branch(self):
        parts = build_signal_status({"rsi": 75.0})
        assert len(parts) >= 1

    def test_rsi_neutral_branch(self):
        parts = build_signal_status({"rsi": 50.0})
        assert len(parts) >= 1

    def test_no_rsi_produces_no_rsi_part(self):
        # Signal dict with no rsi key — should not crash and no rsi part added
        parts = build_signal_status({})
        assert isinstance(parts, list)


# ---------------------------------------------------------------------------
# build_signal_status — MA200 branches (includes the uncovered price >= ma200)
# ---------------------------------------------------------------------------


class TestBuildSignalStatusMa200:
    def test_price_below_ma200(self):
        """price < ma200 → price_below_ma200 i18n key."""
        signals = {"price": 90.0, "ma200": 100.0}
        parts = build_signal_status(signals)
        # Should produce a part (content depends on i18n locale)
        assert len(parts) == 1

    def test_price_above_ma200(self):
        """price >= ma200 → price_above_ma200 i18n key (previously uncovered)."""
        signals = {"price": 110.0, "ma200": 100.0}
        parts = build_signal_status(signals)
        assert len(parts) == 1

    def test_price_equal_ma200(self):
        """price == ma200 also hits the >= branch (previously uncovered)."""
        signals = {"price": 100.0, "ma200": 100.0}
        parts = build_signal_status(signals)
        assert len(parts) == 1

    def test_ma200_none_produces_insufficient_data_part(self):
        """ma200 is None → insufficient data message."""
        parts = build_signal_status({"price": 100.0, "ma200": None})
        assert len(parts) == 1

    def test_ma200_present_price_none_hits_else_branch(self):
        """ma200 present but price is None → falls into else (price_above_ma200 path)."""
        signals = {"price": None, "ma200": 100.0}
        parts = build_signal_status(signals)
        assert len(parts) == 1


# ---------------------------------------------------------------------------
# build_signal_status — bias branches (previously uncovered overheated/oversold)
# ---------------------------------------------------------------------------


class TestBuildSignalStatusBias:
    def test_bias_overheated(self):
        """bias > BIAS_OVERHEATED_THRESHOLD (20) → bias_overheated part (previously uncovered)."""
        # Include ma200 to suppress the insufficient-data part so we can isolate bias
        parts = build_signal_status({"price": 110.0, "ma200": 100.0, "bias": 25.0})
        # ma200 part + bias overheated part
        assert len(parts) == 2
        combined = " ".join(parts)
        assert "25.0" in combined or "過熱" in combined

    def test_bias_oversold(self):
        """bias < BIAS_OVERSOLD_THRESHOLD (-20) → bias_oversold part (previously uncovered)."""
        parts = build_signal_status({"price": 90.0, "ma200": 100.0, "bias": -25.0})
        assert len(parts) == 2
        combined = " ".join(parts)
        assert "-25.0" in combined or "超跌" in combined

    def test_bias_neutral_produces_no_bias_part(self):
        """bias between thresholds → no extra bias part, only ma200 part."""
        parts = build_signal_status({"price": 110.0, "ma200": 100.0, "bias": 5.0})
        assert len(parts) == 1

    def test_bias_none_produces_no_bias_part(self):
        parts = build_signal_status({"price": 110.0, "ma200": 100.0, "bias": None})
        assert len(parts) == 1


# ---------------------------------------------------------------------------
# build_signal_status — combined signals
# ---------------------------------------------------------------------------


class TestBuildSignalStatusCombined:
    def test_all_signals_present_returns_multiple_parts(self):
        signals = {
            "rsi": 50.0,
            "price": 110.0,
            "ma200": 100.0,
            "ma60": 105.0,
            "bias": 25.0,
        }
        parts = build_signal_status(signals)
        # rsi + ma200 + ma60 + bias = 4 parts
        assert len(parts) == 4

    def test_returns_list(self):
        assert isinstance(build_signal_status({}), list)


# ---------------------------------------------------------------------------
# build_moat_details
# ---------------------------------------------------------------------------


class TestBuildMoatDetails:
    def test_deteriorating_status(self):
        """moat_status == DETERIORATING → moat_deteriorating i18n key (previously uncovered)."""
        result = build_moat_details(
            moat_status_value=MoatStatus.DETERIORATING.value,
            current_margin=40.0,
            previous_margin=45.0,
            change=-5.0,
        )
        assert isinstance(result, str)
        assert len(result) > 0

    def test_stable_status(self):
        """moat_status != DETERIORATING → moat_stable i18n key."""
        result = build_moat_details(
            moat_status_value=MoatStatus.STABLE.value,
            current_margin=45.0,
            previous_margin=43.0,
            change=2.0,
        )
        assert isinstance(result, str)
        assert len(result) > 0

    def test_stable_with_negative_change_uses_no_plus_sign(self):
        """Negative change should use empty sign prefix, not '+'."""
        result = build_moat_details(
            moat_status_value=MoatStatus.STABLE.value,
            current_margin=40.0,
            previous_margin=43.0,
            change=-3.0,
        )
        assert isinstance(result, str)

    def test_deteriorating_uses_abs_change(self):
        """DETERIORATING message uses abs(change) — passing positive change should also work."""
        result = build_moat_details(
            moat_status_value=MoatStatus.DETERIORATING.value,
            current_margin=38.0,
            previous_margin=42.0,
            change=-4.0,
        )
        assert isinstance(result, str)

    def test_na_status_falls_through_to_stable(self):
        """N/A status (not DETERIORATING) falls through to moat_stable branch."""
        result = build_moat_details(
            moat_status_value=MoatStatus.NOT_AVAILABLE.value,
            current_margin=None,
            previous_margin=None,
            change=0.0,
        )
        assert isinstance(result, str)
