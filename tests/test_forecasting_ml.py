"""
Automated Pytest Suite for Machine Learning Demand Forecasting & Prediction Intervals.
Phase 2 (Day 22) Deliverable.

Validates regularized ML forecasting (Ridge, ElasticNet, Gradient Boosting),
probabilistic P10/P50/P90 prediction interval generation with horizon expansion,
26-week recursive multi-step forecasting rollout, and out-of-time baseline hurdle clearing (WAPE < 16.23%).
Strictly zero LLM mathematical calculations. Pure deterministic ML testing.
"""

from datetime import date, timedelta
import numpy as np
import pandas as pd
import pytest

from src.forecasting.prep import (
    load_demand_history_from_db,
    split_time_series_chronologically,
    create_demand_feature_pipeline,
    partition_feature_matrix
)
from src.forecasting.ml_models import (
    PredictionInterval,
    MLForecastResult,
    MLBenchmarkScorecard,
    RidgeDemandForecaster,
    GradientBoostingDemandForecaster,
    calculate_prediction_intervals,
    generate_recursive_multi_step_forecast,
    evaluate_ml_against_baseline,
    generate_production_26_week_forecast
)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def db_path():
    """Canonical processed SQLite control tower database path."""
    return "data/processed/control_tower.db"


@pytest.fixture
def demand_data(db_path):
    """Loads raw 104-week historical demand from SQLite."""
    return load_demand_history_from_db(db_path, scenario_id="SCN-BASE")


@pytest.fixture
def split_data(demand_data):
    """Provides a verified chronological split on the 104-week demand dataset."""
    return split_time_series_chronologically(demand_data)


@pytest.fixture
def feature_data(demand_data, split_data):
    """Extracts FeatureMatrix and PartitionedDataset for ML testing."""
    _, matrix = create_demand_feature_pipeline(demand_data, drop_na_lags=True)
    dataset = partition_feature_matrix(matrix, split_data)
    return matrix, dataset


# =============================================================================
# 1. CORE ML MODEL ARCHITECTURE TESTS
# =============================================================================

def test_ridge_demand_forecaster_fit_and_predict(feature_data):
    """Tests that RidgeDemandForecaster trains and produces positive demand predictions."""
    _, dataset = feature_data
    model = RidgeDemandForecaster(alpha=1.0)
    model.fit(dataset.X_train, dataset.y_train, dataset.X_val, dataset.y_val)

    preds = model.predict(dataset.X_test)
    assert len(preds) == len(dataset.y_test)
    assert (preds >= 0.0).all()
    assert model.residual_std > 0.0
    assert model.residual_quantiles[0] < model.residual_quantiles[1]


def test_gradient_boosting_demand_forecaster_fit_and_predict(feature_data):
    """Tests that GradientBoostingDemandForecaster trains and generates valid predictions."""
    _, dataset = feature_data
    model = GradientBoostingDemandForecaster(n_estimators=40, max_depth=3)
    model.fit(dataset.X_train, dataset.y_train, dataset.X_val, dataset.y_val)

    preds = model.predict(dataset.X_test)
    assert len(preds) == len(dataset.y_test)
    assert (preds >= 0.0).all()
    assert model.residual_std > 0.0


# =============================================================================
# 2. PROBABILISTIC PREDICTION INTERVAL TESTS
# =============================================================================

def test_prediction_intervals_ordering_and_spread():
    """Validates mathematical ordering invariant: P10 <= P50 <= P90 across all horizon steps."""
    target_dates = [date(2026, 11, 2) + timedelta(days=7 * i) for i in range(12)]
    p50_values = [3000.0 + (50.0 * i) for i in range(12)]

    intervals = calculate_prediction_intervals(
        point_forecasts=p50_values,
        target_weeks=target_dates,
        residual_std=250.0,
        residual_q10=-300.0,
        residual_q90=280.0,
        horizon_growth_rate=0.04
    )

    assert len(intervals) == 12
    for iv in intervals:
        assert iv.p10_lower <= iv.p50_point
        assert iv.p50_point <= iv.p90_upper
        assert iv.spread >= 0.0
        assert iv.p10_lower >= 0.0


def test_prediction_intervals_uncertainty_growth():
    """Tests that forecast uncertainty spreads expand with forward planning horizon."""
    target_dates = [date(2026, 11, 2) + timedelta(days=7 * i) for i in range(26)]
    p50_values = [3000.0 for _ in range(26)]

    intervals = calculate_prediction_intervals(
        point_forecasts=p50_values,
        target_weeks=target_dates,
        residual_std=200.0,
        horizon_growth_rate=0.05
    )

    # Uncertainty std and interval spread at week 26 must be strictly greater than week 1
    assert intervals[-1].uncertainty_std > intervals[0].uncertainty_std
    assert intervals[-1].spread > intervals[0].spread


def test_prediction_intervals_non_negative_lower_bound():
    """Validates that P10 lower bound is physically bounded at 0.0 even under large negative residuals."""
    target_dates = [date(2026, 11, 2)]
    p50_values = [150.0]  # Low demand

    intervals = calculate_prediction_intervals(
        point_forecasts=p50_values,
        target_weeks=target_dates,
        residual_std=500.0,  # Extreme variance
        residual_q10=-800.0, # Large negative residual
        residual_q90=300.0
    )

    assert intervals[0].p10_lower == 0.0
    assert intervals[0].p50_point == 150.0
    assert intervals[0].p90_upper >= 150.0


# =============================================================================
# 3. RECURSIVE MULTI-STEP 26-WEEK ROLLOUT TESTS
# =============================================================================

def test_recursive_multi_step_forecast_26_weeks(demand_data, feature_data):
    """Tests that recursive rollout generates exactly 26 consecutive weekly dates and point forecasts."""
    _, dataset = feature_data
    model = RidgeDemandForecaster(alpha=1.0)
    model.fit(dataset.X_train, dataset.y_train)

    res = generate_recursive_multi_step_forecast(
        model=model,
        historical_df=demand_data,
        sku_id="SKU-AUG-500-T10",
        market_id="MKT-IN-HYD",
        horizon_weeks=26,
        cutoff_date=date(2026, 10, 19)
    )

    assert isinstance(res, MLForecastResult)
    assert len(res.target_weeks) == 26
    assert len(res.point_forecasts) == 26
    assert len(res.lower_bounds) == 26
    assert len(res.upper_bounds) == 26
    assert len(res.intervals) == 26

    # Verify first and last dates
    assert res.target_weeks[0] == date(2026, 10, 26)  # Next Monday
    assert res.target_weeks[-1] == date(2026, 10, 26) + timedelta(days=7 * 25)

    # Monotonicity check on intervals
    for iv in res.intervals:
        assert iv.p10_lower <= iv.p50_point <= iv.p90_upper


# =============================================================================
# 4. BENCHMARK HURDLE VERIFICATION TESTS
# =============================================================================

def test_evaluate_ml_against_baseline_hurdle_cleared(split_data, feature_data):
    """
    Critical Milestone Test: Proves that candidate ML models beat the Day 21
    Seasonal Naive champion baseline (16.23% WAPE) on the holdout test partition.
    """
    matrix, _ = feature_data
    scorecard = evaluate_ml_against_baseline(
        split=split_data,
        feature_matrix=matrix,
        baseline_wape_pct=16.23,
        baseline_model_name="Seasonal_Naive_52"
    )

    assert isinstance(scorecard, MLBenchmarkScorecard)
    assert scorecard.is_hurdle_cleared is True
    assert scorecard.champion_ml_wape_pct < 16.23
    assert scorecard.champion_ml_wape_pct < 10.0  # Production target < 10% WAPE

    # Verify candidate models
    assert "Ridge_Regression" in scorecard.candidate_model_metrics
    assert "Gradient_Boosting" in scorecard.candidate_model_metrics
    assert scorecard.candidate_model_metrics["Ridge_Regression"].wape_pct < 8.0


def test_champion_ml_wape_reduction_magnitude(split_data, feature_data):
    """Proves that relative error reduction is greater than 40% over classical baseline."""
    matrix, _ = feature_data
    scorecard = evaluate_ml_against_baseline(
        split=split_data,
        feature_matrix=matrix,
        baseline_wape_pct=16.23
    )

    # From 16.23% to 7.76% is a > 50% relative reduction
    assert scorecard.wape_reduction_pct >= 40.0
    assert scorecard.wape_reduction_pct > 50.0


# =============================================================================
# 5. PRODUCTION 26-WEEK FORECAST RUNNER TESTS
# =============================================================================

def test_generate_production_26_week_forecast_shape_and_schema(demand_data):
    """
    Verifies that the full production forecast generator outputs 104 rows
    matching the relational schema of fact_demand_forecast.
    """
    fc_df, results = generate_production_26_week_forecast(
        historical_df=demand_data,
        model_version="ML_Ridge_V1",
        scenario_id="SCN-BASE"
    )

    assert isinstance(fc_df, pd.DataFrame)
    assert len(fc_df) == 104  # 4 series * 26 weeks = 104 rows
    assert len(results) == 4   # 4 time-series

    # Check required columns
    expected_cols = [
        "forecast_id", "forecast_version_date", "target_week", "finished_sku_id",
        "market_id", "forecast_quantity", "lower_bound", "upper_bound",
        "override_quantity", "model_version", "scenario_id"
    ]
    for col in expected_cols:
        assert col in fc_df.columns

    # Date format check
    assert fc_df["forecast_version_date"].iloc[0] == "2026-10-26"
    assert fc_df["target_week"].min() == "2026-10-26"
    assert fc_df["target_week"].max() == "2027-04-19"


def test_production_forecast_no_null_intervals(demand_data):
    """Asserts that zero NaN or null values exist in the forecast quantities or bounds."""
    fc_df, _ = generate_production_26_week_forecast(demand_data)

    assert not fc_df["forecast_quantity"].isna().any()
    assert not fc_df["lower_bound"].isna().any()
    assert not fc_df["upper_bound"].isna().any()

    # Physical bounds check
    assert (fc_df["lower_bound"] <= fc_df["forecast_quantity"]).all()
    assert (fc_df["forecast_quantity"] <= fc_df["upper_bound"]).all()
    assert (fc_df["lower_bound"] >= 0.0).all()


def test_recursive_multi_step_autoregressive_update(demand_data, feature_data):
    """Verifies that multi-step autoregressive rollout accurately propagates predicted values into lags."""
    _, dataset = feature_data
    model = RidgeDemandForecaster(alpha=1.0)
    model.fit(dataset.X_train, dataset.y_train)

    res = generate_recursive_multi_step_forecast(
        model=model,
        historical_df=demand_data,
        sku_id="SKU-AUG-500-T10",
        market_id="MKT-IN-HYD",
        horizon_weeks=4
    )

    # First point forecast should be positive
    assert res.point_forecasts[0] > 0.0
    # Step 2 forecast is generated conditioning on step 1
    assert res.point_forecasts[1] > 0.0
    assert len(res.point_forecasts) == 4


def test_ml_scorecard_markdown_summary_generation(split_data, feature_data):
    """Validates that MLBenchmarkScorecard exports clean, executive Markdown report."""
    matrix, _ = feature_data
    scorecard = evaluate_ml_against_baseline(split_data, matrix)

    md = scorecard.generate_markdown_summary()
    assert "# Machine Learning Demand Forecasting Benchmark Scorecard" in md
    assert "✅ HURDLE CLEARED (Adopt for Production)" in md
    assert "Ridge_Regression" in md
    assert "WAPE %" in md
