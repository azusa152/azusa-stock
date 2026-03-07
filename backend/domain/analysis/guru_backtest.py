"""
Domain — Guru 13F backtesting pure calculation helpers.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class HoldingSnapshot:
    """Single holding snapshot used by clone portfolio simulation."""

    ticker: str
    weight_pct: float


@dataclass(frozen=True)
class QuarterInput:
    """Per-quarter rebalance input."""

    report_date: str
    filing_date: str
    holdings: list[HoldingSnapshot]


@dataclass(frozen=True)
class QuarterResult:
    """Per-quarter backtest output."""

    report_date: str
    filing_date: str
    clone_return_pct: float
    benchmark_return_pct: float
    alpha_pct: float
    holdings_count: int


def _point_date(point: dict) -> date:
    return date.fromisoformat(str(point["date"]))


def _point_close(point: dict) -> float:
    return float(point["close"])


def _first_close_on_or_after(series: list[dict], target: date) -> float | None:
    for point in series:
        if _point_date(point) >= target:
            close = _point_close(point)
            if close > 0:
                return close
    return None


def _latest_close_on_or_before(series: list[dict], target: date) -> float | None:
    latest: float | None = None
    for point in series:
        if _point_date(point) > target:
            break
        close = _point_close(point)
        if close > 0:
            latest = close
    return latest


def _compute_security_return(
    series: list[dict],
    entry_date: date,
    exit_date: date,
) -> float | None:
    entry_close = _first_close_on_or_after(series, entry_date)
    if entry_close is None:
        return None
    exit_close = _latest_close_on_or_before(series, exit_date)
    if exit_close is None:
        return None
    return (exit_close / entry_close - 1) * 100


def compute_alpha(clone_return_pct: float, benchmark_return_pct: float) -> float:
    """Return alpha as clone minus benchmark."""
    return round(clone_return_pct - benchmark_return_pct, 4)


def compute_quarter_return(
    holdings: list[HoldingSnapshot],
    price_data: dict[str, list[dict]],
    entry_date: str,
    exit_date: str,
) -> float:
    """
    Compute weighted clone portfolio return for a quarter.

    Holdings without usable entry/exit prices are excluded and remaining holdings
    are re-normalized by effective weight.
    """
    entry_dt = date.fromisoformat(entry_date)
    exit_dt = date.fromisoformat(exit_date)

    weighted_return_sum = 0.0
    effective_weight_sum = 0.0

    for holding in holdings:
        series = price_data.get(holding.ticker)
        if not series:
            continue
        security_return = _compute_security_return(series, entry_dt, exit_dt)
        if security_return is None:
            continue
        effective_weight_sum += holding.weight_pct
        weighted_return_sum += security_return * holding.weight_pct

    if effective_weight_sum <= 0:
        return 0.0
    return round(weighted_return_sum / effective_weight_sum, 4)


def _compute_benchmark_return(
    benchmark_prices: list[dict],
    entry_date: str,
    exit_date: str,
) -> float:
    entry_dt = date.fromisoformat(entry_date)
    exit_dt = date.fromisoformat(exit_date)

    security_return = _compute_security_return(benchmark_prices, entry_dt, exit_dt)
    if security_return is None:
        return 0.0
    return round(security_return, 4)


def _compute_clone_return_on_date(
    holdings: list[HoldingSnapshot],
    price_data: dict[str, list[dict]],
    entry_dt: date,
    current_dt: date,
) -> float:
    weighted_return_sum = 0.0
    effective_weight_sum = 0.0

    for holding in holdings:
        series = price_data.get(holding.ticker)
        if not series:
            continue

        entry_close = _first_close_on_or_after(series, entry_dt)
        current_close = _latest_close_on_or_before(series, current_dt)
        if entry_close is None or current_close is None:
            continue

        security_return = (current_close / entry_close - 1) * 100
        weighted_return_sum += security_return * holding.weight_pct
        effective_weight_sum += holding.weight_pct

    if effective_weight_sum <= 0:
        return 0.0
    return weighted_return_sum / effective_weight_sum


def compute_clone_returns(
    quarter_inputs: list[QuarterInput],
    price_data: dict[str, list[dict]],
    benchmark_prices: list[dict],
) -> dict:
    """
    Compute quarter-level returns and cumulative series for guru clone portfolio.
    """
    if not quarter_inputs:
        return {
            "quarters": [],
            "cumulative_series": {
                "dates": [],
                "clone_returns": [],
                "benchmark_returns": [],
            },
            "cumulative_clone_return": 0.0,
            "cumulative_benchmark_return": 0.0,
            "alpha": 0.0,
        }

    sorted_quarters = sorted(quarter_inputs, key=lambda q: q.filing_date)
    benchmark_sorted = sorted(benchmark_prices, key=_point_date)

    quarter_results: list[QuarterResult] = []
    clone_cumulative_multiplier = 1.0
    benchmark_cumulative_multiplier = 1.0

    dates: list[str] = []
    clone_series: list[float] = []
    benchmark_series: list[float] = []

    for idx, quarter in enumerate(sorted_quarters):
        entry_date = quarter.filing_date
        if idx + 1 < len(sorted_quarters):
            exit_date = sorted_quarters[idx + 1].filing_date
        elif benchmark_sorted:
            exit_date = str(_point_date(benchmark_sorted[-1]))
        else:
            exit_date = entry_date

        quarter_clone = compute_quarter_return(
            holdings=quarter.holdings,
            price_data=price_data,
            entry_date=entry_date,
            exit_date=exit_date,
        )
        quarter_benchmark = _compute_benchmark_return(
            benchmark_prices=benchmark_sorted,
            entry_date=entry_date,
            exit_date=exit_date,
        )
        quarter_alpha = compute_alpha(quarter_clone, quarter_benchmark)

        quarter_results.append(
            QuarterResult(
                report_date=quarter.report_date,
                filing_date=quarter.filing_date,
                clone_return_pct=quarter_clone,
                benchmark_return_pct=quarter_benchmark,
                alpha_pct=quarter_alpha,
                holdings_count=len(quarter.holdings),
            )
        )

        clone_cumulative_multiplier *= 1 + quarter_clone / 100
        benchmark_cumulative_multiplier *= 1 + quarter_benchmark / 100

        entry_dt = date.fromisoformat(entry_date)
        exit_dt = date.fromisoformat(exit_date)
        for point in benchmark_sorted:
            point_dt = _point_date(point)
            if point_dt < entry_dt:
                continue
            if idx + 1 < len(sorted_quarters):
                if point_dt >= exit_dt:
                    break
            elif point_dt > exit_dt:
                break

            quarter_clone_on_date = _compute_clone_return_on_date(
                holdings=quarter.holdings,
                price_data=price_data,
                entry_dt=entry_dt,
                current_dt=point_dt,
            )
            quarter_benchmark_on_date = _compute_benchmark_return(
                benchmark_prices=benchmark_sorted,
                entry_date=entry_date,
                exit_date=str(point_dt),
            )

            clone_total = (clone_cumulative_multiplier / (1 + quarter_clone / 100)) * (
                1 + quarter_clone_on_date / 100
            ) - 1
            benchmark_total = (
                benchmark_cumulative_multiplier / (1 + quarter_benchmark / 100)
            ) * (1 + quarter_benchmark_on_date / 100) - 1

            dates.append(str(point_dt))
            clone_series.append(round(clone_total * 100, 4))
            benchmark_series.append(round(benchmark_total * 100, 4))

    cumulative_clone_return = round((clone_cumulative_multiplier - 1) * 100, 4)
    cumulative_benchmark_return = round((benchmark_cumulative_multiplier - 1) * 100, 4)
    return {
        "quarters": [
            {
                "report_date": item.report_date,
                "filing_date": item.filing_date,
                "clone_return_pct": item.clone_return_pct,
                "benchmark_return_pct": item.benchmark_return_pct,
                "alpha_pct": item.alpha_pct,
                "holdings_count": item.holdings_count,
            }
            for item in quarter_results
        ],
        "cumulative_series": {
            "dates": dates,
            "clone_returns": clone_series,
            "benchmark_returns": benchmark_series,
        },
        "cumulative_clone_return": cumulative_clone_return,
        "cumulative_benchmark_return": cumulative_benchmark_return,
        "alpha": compute_alpha(cumulative_clone_return, cumulative_benchmark_return),
    }
