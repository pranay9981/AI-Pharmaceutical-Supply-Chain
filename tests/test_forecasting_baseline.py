"""
Automated Pytest Suite for Baseline Statistical Forecasting Models.
Phase 2 (Day 21) Deliverable.

Validates Seasonal Naive, Moving Average, and Exponential Smoothing algorithms,
26-week forward point forecast generation, and standardized error metrics (WAPE, MAE, Bias %).
Strictly zero LLM mathematical calculations. Pure deterministic time-series testing.
"""

from datetime import date
import numpy as np
import pandas as pd
import pytest

from src.forecasting.prep import load_demand_history_from_db, split_time_series_chronologically
from src.forecasting.baseline import (
    ForecastEvaluationMetrics,
    SeriesForecastResult,
    BaselineBenchmarkReport,
    calculate_forecast_metrics,
    SeasonalNaiveModel,
    MovingAverageModel,
    ExponentialSmoothingModel,
    generate_series_forecast,
    run_baseline_benchmark_evaluation
)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def db_path():
    """Canonical processed SQLite control tower database path."""
    return "data/processed/control_tower.db"


@pytest.fixture
def prepared_split(db_path):
    """Provides a verified chronological split on the 104-week production demand dataset."""
    df = load_demand_history_from_db(db_path, scenario_id="SCN-BASE")
    return split_time_series_chronologically(df)


@pytest.fixture
def linear_trend_series():
    """Deterministic synthetic series with constant upward slope (+50 units/week)."""
    return pd.Series([1000.0 + (50.0 * i) for i in range(52)])


@pytest.fixture
def seasonal_synthetic_series():
    """Deterministic 104-week synthetic series with prominent annual peak at week 25."""
    values = []
    for yr in range(2):
        for w in range(52):
            seasonal_surge = 500.0 if 24 <= w <= 32 else 0.0
            values.append(2000.0 + seasonal_surge + (w * 10.0))
    return pd.Series(values)


# =============================================================================
# 1. FORECAST METRICS MATHEMATICAL TESTS
# =============================================================================

def test_calculate_forecast_metrics_perfect_prediction():
    """Proves WAPE=0%, MAE=0, Bias=0% when forecasts match actuals identically."""
    actuals = [100.0, 200.0, 300.0, 400.0]
    preds = [100.0, 200.0, 300.0, 400.0]

    metrics = calculate_forecast_metrics(actuals, preds)
    assert metrics.wape_pct == 0.0
    assert metrics.mae == 0.0
    assert metrics.rmse == 0.0
    assert metrics.bias_pct == 0.0
    assert metrics.tracking_signal == 0.0
    assert metrics.num_samples == 4


def test_calculate_forecast_metrics_positive_bias():
    """Verifies that 10% consistent over-forecasting yields exact +10% forecast bias."""
    actuals = [1000.0, 1000.0, 1000.0, 1000.0]
    preds = [1100.0, 1100.0, 1100.0, 1100.0]  # Over-forecast by 100 per week

    metrics = calculate_forecast_metrics(actuals, preds)
    assert metrics.wape_pct == 10.0
    assert metrics.mae == 100.0
    assert metrics.bias_pct == 10.0
    assert metrics.tracking_signal > 0.0


def test_calculate_forecast_metrics_negative_bias():
    """Verifies that 15% consistent under-forecasting yields exact -15% forecast bias."""
    actuals = [1000.0, 1000.0, 1000.0, 1000.0]
    preds = [850.0, 850.0, 850.0, 850.0]  # Under-forecast by 150 per week

    metrics = calculate_forecast_metrics(actuals, preds)
    assert metrics.wape_pct == 15.0
    assert metrics.mae == 150.0
    assert metrics.bias_pct == -15.0
    assert metrics.tracking_signal < 0.0


# =============================================================================
# 2. SEASONAL NAIVE MODEL TESTS
# =============================================================================

def test_seasonal_naive_52_week_mapping(seasonal_synthetic_series):
    """Validates that SeasonalNaiveModel maps y_{t+h} = y_{t+h-52} over a 26-week horizon."""
    model = SeasonalNaiveModel(seasonal_period=52)
    model.fit(seasonal_synthetic_series.values)

    preds = model.predict(horizon=26)
    assert len(preds) == 26

    # Verify that prediction for horizon h matches history at (end - 52 + h - 1)
    n = len(seasonal_synthetic_series)
    for h in range(1, 27):
        expected_val = seasonal_synthetic_series.iloc[n - 52 + (h - 1)]
        assert preds[h - 1] == expected_val


def test_seasonal_naive_short_horizon_fallback():
    """Validates fallback to shorter periodicity when history has fewer than 52 observations."""
    short_series = [100.0, 120.0, 140.0, 160.0] * 3  # 12 observations
    model = SeasonalNaiveModel(seasonal_period=52)
    model.fit(short_series)

    preds = model.predict(horizon=8)
    assert len(preds) == 8
    # Should fall back to 12-week or 4-week cycle
    assert preds[0] == short_series[0]
    assert preds[1] == short_series[1]


# =============================================================================
# 3. MOVING AVERAGE MODEL TESTS
# =============================================================================

def test_simple_moving_average_calculation():
    """Tests that Simple Moving Average produces an exact flat forward mean of the tail window."""
    history = [100.0, 200.0, 300.0, 400.0, 500.0, 600.0]
    # Tail 4: [300, 400, 500, 600] -> Mean = 450.0
    model = MovingAverageModel(window=4, weighted=False)
    model.fit(history)

    preds = model.predict(horizon=10)
    assert len(preds) == 10
    assert (preds == 450.0).all()


def test_weighted_moving_average_decay_weights():
    """Tests that Weighted Moving Average assigns higher weight to recent weeks."""
    history = [100.0, 200.0, 300.0]
    # Window 3 weights: 1/6 for idx 0, 2/6 for idx 1, 3/6 for idx 2
    # Weighted sum: (100*1 + 200*2 + 300*3) / 6 = (100 + 400 + 900) / 6 = 1400 / 6 = 233.3333
    model = MovingAverageModel(window=3, weighted=True)
    model.fit(history)

    preds = model.predict(horizon=4)
    expected_level = (100.0 * 1 + 200.0 * 2 + 300.0 * 3) / 6.0
    assert pytest.approx(preds[0], rel=1e-4) == expected_level
    # SMA would be (100+200+300)/3 = 200.0; WMA must be > 200.0 due to recency
    assert preds[0] > 200.0


# =============================================================================
# 4. EXPONENTIAL SMOOTHING TESTS
# =============================================================================

def test_exponential_smoothing_ses():
    """Tests Simple Exponential Smoothing (SES) level filtering and flat extrapolation."""
    history = [1000.0, 1050.0, 980.0, 1020.0, 1010.0]
    model = ExponentialSmoothingModel(method="ses", alpha=0.3, auto_fit=False)
    model.fit(history)

    preds = model.predict(horizon=12)
    assert len(preds) == 12
    # SES produces flat extrapolation
    assert len(set(preds)) == 1
    assert 980.0 < preds[0] < 1050.0


def test_exponential_smoothing_holt_linear_trend(linear_trend_series):
    """Tests that Holt's Linear Trend successfully projects upward slope over horizon."""
    # Series grows +50 per week: 1000, 1050, ..., 3550
    model = ExponentialSmoothingModel(method="holt", alpha=0.3, beta=0.1, phi=1.0, auto_fit=False)
    model.fit(linear_trend_series.values)

    preds = model.predict(horizon=10)
    assert len(preds) == 10
    # Predictions must be strictly monotonically increasing
    for i in range(len(preds) - 1):
        assert preds[i] < preds[i + 1]


def test_exponential_smoothing_non_negative_bounding():
    """Tests that strong downward trends are bounded at 0.0 to prevent negative demand."""
    downward_series = [1000.0, 800.0, 600.0, 400.0, 200.0, 50.0]
    model = ExponentialSmoothingModel(method="holt", alpha=0.5, beta=0.3, phi=1.0, auto_fit=False)
    model.fit(downward_series)

    preds = model.predict(horizon=20)
    # Even if mathematical trend goes negative, physical demand must be >= 0.0
    assert (preds >= 0.0).all()


# =============================================================================
# 5. MULTI-SERIES & BENCHMARK PIPELINE TESTS
# =============================================================================

def test_generate_series_forecast_pipeline():
    """Tests single series forecast wrapper generating 26-week calendar dates and point forecasts."""
    history = pd.Series([2000.0 + (i * 20.0) for i in range(52)])
    actuals = pd.Series([3040.0 + (i * 20.0) for i in range(26)])

    res = generate_series_forecast(
        train_series=history,
        model_name="Holt_Linear_Trend",
        horizon_weeks=26,
        sku_id="SKU-AUG-500-T10",
        market_id="MKT-IN-HYD",
        cutoff_date=date(2026, 4, 20),
        test_actuals=actuals
    )

    assert isinstance(res, SeriesForecastResult)
    assert len(res.target_weeks) == 26
    assert len(res.forecast_quantities) == 26
    assert res.target_weeks[0] == date(2026, 4, 27)  # Next Monday
    assert res.metrics is not None
    assert res.metrics.wape_pct >= 0.0


def test_baseline_benchmark_evaluation_on_database(prepared_split):
    """
    Executes full baseline benchmark evaluation on the 104-week production database split.
    Asserts champion model selection, summary table structure, and valid error bounds.
    """
    report = run_baseline_benchmark_evaluation(prepared_split)

    assert isinstance(report, BaselineBenchmarkReport)
    assert report.evaluation_horizon_weeks == 13
    assert len(report.series_evaluated) == 4
    assert len(report.models_evaluated) == 6

    # Verify summary DataFrame
    assert "model_name" in report.summary_df.columns
    assert "wape_pct" in report.summary_df.columns
    assert "bias_pct" in report.summary_df.columns
    assert "is_champion" in report.summary_df.columns

    # Champion model check
    assert report.best_model_name in report.models_evaluated
    best_row = report.summary_df[report.summary_df["is_champion"] == True]
    assert len(best_row) == 1
    assert best_row["wape_pct"].iloc[0] < 20.0  # Production baseline standard < 20% WAPE

    # Markdown export check
    md = report.generate_markdown_summary()
    assert "# Baseline Statistical Forecasting Benchmark Scorecard" in md
    assert "Champion Baseline Model:" in md
    assert "Handover Contract for Day 22 ML Models" in md
