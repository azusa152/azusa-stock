from domain.analysis.guru_backtest import (
    HoldingSnapshot,
    QuarterInput,
    compute_alpha,
    compute_clone_returns,
    compute_quarter_return,
)


def test_compute_quarter_return_should_apply_weighted_average():
    holdings = [
        HoldingSnapshot(ticker="AAPL", weight_pct=60.0),
        HoldingSnapshot(ticker="MSFT", weight_pct=40.0),
    ]
    price_data = {
        "AAPL": [
            {"date": "2025-02-14", "close": 100.0},
            {"date": "2025-05-15", "close": 110.0},
        ],
        "MSFT": [
            {"date": "2025-02-14", "close": 200.0},
            {"date": "2025-05-15", "close": 220.0},
        ],
    }

    result = compute_quarter_return(
        holdings=holdings,
        price_data=price_data,
        entry_date="2025-02-14",
        exit_date="2025-05-15",
    )

    assert result == 10.0


def test_compute_quarter_return_should_renormalize_when_one_ticker_missing():
    holdings = [
        HoldingSnapshot(ticker="AAPL", weight_pct=60.0),
        HoldingSnapshot(ticker="MSFT", weight_pct=40.0),
    ]
    price_data = {
        "AAPL": [
            {"date": "2025-02-14", "close": 100.0},
            {"date": "2025-05-15", "close": 110.0},
        ]
    }

    result = compute_quarter_return(
        holdings=holdings,
        price_data=price_data,
        entry_date="2025-02-14",
        exit_date="2025-05-15",
    )

    assert result == 10.0


def test_compute_alpha_should_subtract_benchmark():
    assert compute_alpha(18.25, 12.0) == 6.25


def test_compute_clone_returns_should_return_quarter_rows_and_cumulative_series():
    quarter_inputs = [
        QuarterInput(
            report_date="2024-12-31",
            filing_date="2025-02-14",
            holdings=[
                HoldingSnapshot(ticker="AAPL", weight_pct=100.0),
            ],
        ),
        QuarterInput(
            report_date="2025-03-31",
            filing_date="2025-05-15",
            holdings=[
                HoldingSnapshot(ticker="AAPL", weight_pct=100.0),
            ],
        ),
    ]
    price_data = {
        "AAPL": [
            {"date": "2025-02-14", "close": 100.0},
            {"date": "2025-03-14", "close": 102.0},
            {"date": "2025-05-15", "close": 110.0},
            {"date": "2025-06-16", "close": 112.0},
        ]
    }
    benchmark_prices = [
        {"date": "2025-02-14", "close": 200.0},
        {"date": "2025-03-14", "close": 202.0},
        {"date": "2025-05-15", "close": 210.0},
        {"date": "2025-06-16", "close": 211.0},
    ]

    result = compute_clone_returns(
        quarter_inputs=quarter_inputs,
        price_data=price_data,
        benchmark_prices=benchmark_prices,
    )

    assert len(result["quarters"]) == 2
    assert result["cumulative_clone_return"] > result["cumulative_benchmark_return"]
    assert len(result["cumulative_series"]["dates"]) > 0
    assert len(result["cumulative_series"]["dates"]) == len(
        result["cumulative_series"]["clone_returns"]
    )
