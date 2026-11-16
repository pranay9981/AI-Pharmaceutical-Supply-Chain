"""
Automated Pytest Suite for Demand Time-Series Preprocessing & Leakage Controls.
Phase 2 (Day 20) Deliverable.

Validates chronological splitting, causal lag & rolling feature generation,
pharmaceutical calendar indicators, and automated data leakage detection.
Strictly zero LLM mathematical dependencies. Pure deterministic testing.
"""

from datetime import date, datetime
import pandas as pd
import numpy as np
import pytest

from src.forecasting.prep import (
    TimeSeriesSplit,
    FeatureMatrix,
    PartitionedDataset,
    LeakageAuditReport,
    load_demand_history_from_db,
    split_time_series_chronologically,
    create_calendar_features,
    create_demand_lag_features,
    encode_series_identifiers,
    create_demand_feature_pipeline,
    partition_feature_matrix,
    audit_time_series_leakage
)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def db_path():
    """Canonical processed SQLite control tower database path."""
    return "data/processed/control_tower.db"


@pytest.fixture
def raw_demand_df(db_path):
    """Loads raw 104-week historical demand from SQLite."""
    return load_demand_history_from_db(db_path, scenario_id="SCN-BASE")


@pytest.fixture
def mock_synthetic_series():
    """Constructs a deterministic synthetic 2-series time-series dataframe for controlled testing."""
    dates = pd.date_range(start="2024-10-28", periods=20, freq="7D")
    records = []
    for s_idx, sku in enumerate(["SKU-01", "SKU-02"]):
        base_demand = 1000.0 * (s_idx + 1)
        for i, dt in enumerate(dates):
            # Demand has linear trend + known deterministic step
            demand = base_demand + (i * 50.0)
            records.append({
                "week_start_date": dt,
                "finished_sku_id": sku,
                "market_id": "MKT-01",
                "demand_quantity": demand,
                "fulfilled_quantity": demand,
                "lost_sales_quantity": 0.0,
                "scenario_id": "SCN-TEST"
            })
    df = pd.DataFrame(records)
    return df


# =============================================================================
# 1. DATABASE LOADING & STRUCTURE TESTS
# =============================================================================

def test_load_demand_history_structure_and_counts(raw_demand_df):
    """Verifies that 104 weeks across 2 SKUs and 2 markets (416 rows) are loaded cleanly."""
    assert len(raw_demand_df) == 416
    assert set(raw_demand_df["finished_sku_id"].unique()) == {"SKU-AUG-500-T10", "SKU-AUG-500-T30"}
    assert set(raw_demand_df["market_id"].unique()) == {"MKT-IN-HYD", "MKT-IN-PUN"}
    assert raw_demand_df["demand_quantity"].min() > 0.0
    assert len(raw_demand_df["week_start_date"].unique()) == 104


# =============================================================================
# 2. CHRONOLOGICAL SPLITTING TESTS
# =============================================================================

def test_chronological_split_ratios_and_boundaries(raw_demand_df):
    """Tests splitting 104 weeks with 75% train, 12.5% val, and 12.5% test allocations."""
    split = split_time_series_chronologically(
        raw_demand_df,
        train_ratio=0.75,
        val_ratio=0.125,
        test_ratio=0.125
    )

    assert split.total_weeks == 104
    assert split.train_weeks == 78
    assert split.val_weeks == 13
    assert split.test_weeks == 13

    # Row counts: 4 series * split weeks
    assert len(split.train_df) == 78 * 4  # 312
    assert len(split.val_df) == 13 * 4    # 52
    assert len(split.test_df) == 13 * 4   # 52
    assert split.num_series == 4


def test_chronological_split_strict_date_ordering(raw_demand_df):
    """Proves strict chronological sequence: Train End < Val Start < Test Start."""
    split = split_time_series_chronologically(raw_demand_df)

    assert split.train_end < split.val_start
    assert split.val_end < split.test_start

    # Exact boundary check (7-day cadence)
    assert (split.val_start - split.train_end).days == 7
    assert (split.test_start - split.val_end).days == 7


def test_chronological_split_zero_date_overlap(raw_demand_df):
    """Mathematically proves disjoint calendar partitions with zero date overlap."""
    split = split_time_series_chronologically(raw_demand_df)

    train_dates = set(split.train_df["week_start_date"].dt.date)
    val_dates = set(split.val_df["week_start_date"].dt.date)
    test_dates = set(split.test_df["week_start_date"].dt.date)

    assert len(train_dates.intersection(val_dates)) == 0
    assert len(val_dates.intersection(test_dates)) == 0
    assert len(train_dates.intersection(test_dates)) == 0


# =============================================================================
# 3. CALENDAR & CYCLICAL FEATURE TESTS
# =============================================================================

def test_calendar_and_cyclical_feature_engineering(mock_synthetic_series):
    """Validates trigonometric sin/cos encoding bounds [-1, 1] and pharma market indicators."""
    feat_df = create_calendar_features(mock_synthetic_series)

    assert "calendar_year" in feat_df.columns
    assert "week_of_year" in feat_df.columns
    assert "sin_week_of_year" in feat_df.columns
    assert "cos_week_of_year" in feat_df.columns

    # Check bounds
    assert feat_df["sin_week_of_year"].between(-1.0, 1.0).all()
    assert feat_df["cos_week_of_year"].between(-1.0, 1.0).all()
    assert feat_df["sin_month"].between(-1.0, 1.0).all()
    assert feat_df["cos_month"].between(-1.0, 1.0).all()

    # Binary indicators
    assert set(feat_df["is_quarter_end_month"].unique()).issubset({0, 1})
    assert set(feat_df["is_monsoon_surge"].unique()).issubset({0, 1})
    assert set(feat_df["is_diwali_period"].unique()).issubset({0, 1})


# =============================================================================
# 4. CAUSAL LAG & ROLLING STATISTICAL FEATURE TESTS
# =============================================================================

def test_causal_lag_alignment_exact_shift(mock_synthetic_series):
    """Verifies that lag_1(t) strictly equals y(t-1) and lag_2(t) strictly equals y(t-2)."""
    lag_df = create_demand_lag_features(
        mock_synthetic_series,
        group_cols=["finished_sku_id", "market_id"],
        lag_weeks=[1, 2, 4],
        include_annual_lag=False,
        rolling_windows=[4]
    )

    sku1 = lag_df[lag_df["finished_sku_id"] == "SKU-01"].reset_index(drop=True)

    # First row must be NaN for lag_1
    assert pd.isna(sku1.loc[0, "lag_1"])
    assert pd.isna(sku1.loc[1, "lag_2"])

    # For subsequent rows, verify exact equality with prior target
    for t in range(1, len(sku1)):
        expected_lag1 = sku1.loc[t - 1, "demand_quantity"]
        actual_lag1 = sku1.loc[t, "lag_1"]
        assert actual_lag1 == expected_lag1

    for t in range(2, len(sku1)):
        expected_lag2 = sku1.loc[t - 2, "demand_quantity"]
        actual_lag2 = sku1.loc[t, "lag_2"]
        assert actual_lag2 == expected_lag2


def test_causal_rolling_statistics_exclude_current_target(mock_synthetic_series):
    """
    Critical Leakage Test: Confirms rolling window statistics strictly encompass [t-w ... t-1],
    and do not include the current period's demand y_t.
    """
    lag_df = create_demand_lag_features(
        mock_synthetic_series,
        group_cols=["finished_sku_id", "market_id"],
        lag_weeks=[1],
        include_annual_lag=False,
        rolling_windows=[4]
    )

    sku1 = lag_df[lag_df["finished_sku_id"] == "SKU-01"].reset_index(drop=True)

    # For window w=4, the first 4 rows (index 0, 1, 2, 3) must be NaN
    # because row 0 has no history, row 1 has 1 history, row 2 has 2, row 3 has 3
    # Only row 4 has 4 historical points: y_0, y_1, y_2, y_3!
    assert pd.isna(sku1.loc[0, "rolling_mean_4"])
    assert pd.isna(sku1.loc[1, "rolling_mean_4"])
    assert pd.isna(sku1.loc[2, "rolling_mean_4"])
    assert pd.isna(sku1.loc[3, "rolling_mean_4"])

    # At row 4: historical points are y[0], y[1], y[2], y[3]
    expected_mean_at_4 = sku1.loc[0:3, "demand_quantity"].mean()
    actual_mean_at_4 = sku1.loc[4, "rolling_mean_4"]
    assert pytest.approx(actual_mean_at_4, rel=1e-4) == expected_mean_at_4

    # Crucial test: Ensure y[4] is NOT in rolling_mean_4
    assert actual_mean_at_4 != sku1.loc[1:4, "demand_quantity"].mean()


# =============================================================================
# 5. FULL PIPELINE & PARTITION TESTS
# =============================================================================

def test_feature_pipeline_end_to_end_shape_and_metadata(raw_demand_df):
    """Executes full pipeline and validates feature matrix structure and column types."""
    f_df, matrix = create_demand_feature_pipeline(
        raw_demand_df,
        drop_na_lags=True,
        include_annual_lag=False
    )

    assert isinstance(matrix, FeatureMatrix)
    assert matrix.X.shape[0] == 368  # 416 - (12 lag warmup * 4 series) = 368
    assert matrix.X.shape[1] >= 25   # Engineered feature count
    assert "demand_quantity" not in matrix.X.columns
    assert "fulfilled_quantity" not in matrix.X.columns
    assert "lost_sales_quantity" not in matrix.X.columns

    # Metadata tracking integrity
    assert "week_start_date" in matrix.metadata.columns
    assert "finished_sku_id" in matrix.metadata.columns
    assert "market_id" in matrix.metadata.columns


def test_partition_feature_matrix_shapes_and_continuity(raw_demand_df):
    """Tests partitioning a FeatureMatrix into train/val/test using TimeSeriesSplit."""
    split = split_time_series_chronologically(raw_demand_df)
    _, matrix = create_demand_feature_pipeline(raw_demand_df, drop_na_lags=True)

    dataset = partition_feature_matrix(matrix, split)

    assert isinstance(dataset, PartitionedDataset)
    assert len(dataset.X_train) == len(dataset.y_train)
    assert len(dataset.X_val) == len(dataset.y_val)
    assert len(dataset.X_test) == len(dataset.y_test)

    # Total rows in train/val/test match matrix length
    assert len(dataset.X_train) + len(dataset.X_val) + len(dataset.X_test) == len(matrix.X)

    # Validation and test are completely non-empty and have identical columns
    assert len(dataset.X_val) == 52   # 13 weeks * 4 series
    assert len(dataset.X_test) == 52  # 13 weeks * 4 series
    assert list(dataset.X_train.columns) == list(dataset.X_val.columns) == list(dataset.X_test.columns)


# =============================================================================
# 6. DATA LEAKAGE AUDIT ENGINE TESTS
# =============================================================================

def test_leakage_audit_engine_clean_pass(raw_demand_df):
    """Asserts that production feature pipeline passes all 5 leakage checks."""
    split = split_time_series_chronologically(raw_demand_df)
    _, matrix = create_demand_feature_pipeline(raw_demand_df, drop_na_lags=True)

    report = audit_time_series_leakage(split, matrix)

    assert isinstance(report, LeakageAuditReport)
    assert report.is_leakage_free is True
    assert report.temporal_ordering_passed is True
    assert report.split_disjointness_passed is True
    assert report.causal_feature_alignment_passed is True
    assert report.no_future_target_in_features_passed is True
    assert report.downstream_target_exclusion_passed is True
    assert report.checks_evaluated == 5
    assert len(report.violations) == 0

    # Test Markdown serialization
    md = report.generate_markdown_summary()
    assert "✅ PASSED (Leakage-Free)" in md


def test_leakage_audit_engine_catches_target_leakage(raw_demand_df):
    """Injects intentional target leak into feature matrix and asserts automated failure."""
    split = split_time_series_chronologically(raw_demand_df)
    _, matrix = create_demand_feature_pipeline(raw_demand_df, drop_na_lags=True)

    # ARTIFICIAL LEAK: Copy target demand into features
    leaked_X = matrix.X.copy()
    leaked_X["leaked_target"] = matrix.y.values

    leaked_matrix = FeatureMatrix(
        X=leaked_X,
        y=matrix.y,
        metadata=matrix.metadata,
        feature_names=list(leaked_X.columns),
        target_name=matrix.target_name,
        num_samples=len(matrix.y)
    )

    report = audit_time_series_leakage(split, leaked_matrix)
    assert report.is_leakage_free is False
    assert report.no_future_target_in_features_passed is False
    assert any("near-perfect correlation" in v for v in report.violations)


def test_leakage_audit_engine_catches_downstream_leakage(raw_demand_df):
    """Injects forbidden operational outcome (lost_sales) and asserts detection."""
    split = split_time_series_chronologically(raw_demand_df)
    _, matrix = create_demand_feature_pipeline(raw_demand_df, drop_na_lags=True)

    # ARTIFICIAL LEAK: Include downstream variable in features
    leaked_X = matrix.X.copy()
    leaked_X["lost_sales_quantity"] = 50.0

    leaked_matrix = FeatureMatrix(
        X=leaked_X,
        y=matrix.y,
        metadata=matrix.metadata,
        feature_names=list(leaked_X.columns),
        target_name=matrix.target_name,
        num_samples=len(matrix.y)
    )

    report = audit_time_series_leakage(split, leaked_matrix)
    assert report.is_leakage_free is False
    assert report.downstream_target_exclusion_passed is False
    assert any("downstream" in v for v in report.violations)
