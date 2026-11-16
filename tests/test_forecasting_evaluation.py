"""
Automated Pytest Suite for Forecast Evaluation, Slice-and-Dice Analytics & Versioning Registry.
Phase 2 (Day 23) Deliverable.

Validates multi-dimensional slice evaluation (SKU, Market, Horizon buckets),
tracking signal statistical drift monitoring (|TS| > 4.0 alarms),
version-to-version waterfall variance analysis, and multi-version SQLite registry persistence.
Strictly zero LLM mathematical dependencies. Pure deterministic testing.
"""

from datetime import date, timedelta
import sqlite3
import numpy as np
import pandas as pd
import pytest

from src.forecasting.prep import (
    load_demand_history_from_db,
    split_time_series_chronologically,
    create_demand_feature_pipeline
)
from src.forecasting.ml_models import (
    evaluate_ml_against_baseline,
    generate_production_26_week_forecast
)
from src.forecasting.evaluation import (
    DriftAlarmSeverity,
    TrackingSignalPoint,
    TrackingSignalAuditResult,
    ForecastSliceMetrics,
    ForecastSliceReport,
    VersionVarianceItem,
    ForecastVersionComparisonReport,
    evaluate_forecast_slices,
    evaluate_tracking_signal_drift,
    analyze_forecast_version_variance,
    ForecastRegistry
)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def db_path():
    """Canonical processed SQLite control tower database path."""
    return "data/processed/control_tower.db"


@pytest.fixture
def memory_db():
    """Provides an isolated in-memory SQLite database populated with fact_demand_forecast schema."""
    conn = sqlite3.connect(":memory:")
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE fact_demand_forecast (
            forecast_id TEXT,
            forecast_version_date DATE,
            target_week DATE,
            finished_sku_id TEXT,
            market_id TEXT,
            forecast_quantity REAL,
            lower_bound REAL,
            upper_bound REAL,
            override_quantity TEXT,
            model_version TEXT,
            scenario_id TEXT
        )
    """)
    conn.commit()
    yield conn
    conn.close()


@pytest.fixture
def sample_evaluation_data():
    """Constructs a deterministic 16-week, 2-SKU x 2-Market dataset for slice testing."""
    records = []
    dates = [date(2026, 11, 2) + timedelta(days=7 * i) for i in range(16)]
    for sku in ["SKU-AUG-500-T10", "SKU-AUG-500-T30"]:
        for mkt in ["MKT-IN-HYD", "MKT-IN-PUN"]:
            base = 3000.0 if "T10" in sku else 1500.0
            for i, dt in enumerate(dates):
                act = base + (i * 20.0)
                # Prediction with deterministic slight error (+/- 5%)
                err = 50.0 if i % 2 == 0 else -40.0
                fc = act + err
                records.append({
                    "target_week": dt,
                    "finished_sku_id": sku,
                    "market_id": mkt,
                    "actual_demand": act,
                    "forecast_quantity": fc
                })
    return pd.DataFrame(records)


# =============================================================================
# 1. MULTI-HORIZON SLICE-AND-DICE TESTS
# =============================================================================

def test_evaluate_forecast_slices_overall_and_dimensions(sample_evaluation_data):
    """Verifies that evaluate_forecast_slices computes metrics across all 4 operational dimensions."""
    report = evaluate_forecast_slices(
        sample_evaluation_data,
        model_name="Test_Model"
    )

    assert isinstance(report, ForecastSliceReport)
    assert report.overall_metrics.wape_pct < 5.0  # Tight synthetic error
    assert len(report.sku_slices) == 2
    assert len(report.market_slices) == 2
    assert len(report.horizon_slices) == 3       # W01-W04, W05-W12, W13-W26
    assert len(report.intersection_slices) == 4  # 2 SKUs * 2 Markets

    # Check that summary dataframe includes all slices
    assert "dimension" in report.summary_df.columns
    assert "wape_pct" in report.summary_df.columns
    assert "volume_delta" in report.summary_df.columns
    assert len(report.summary_df) == (2 + 2 + 3 + 4)  # 11 slice rows


def test_evaluate_forecast_slices_volume_conservation(sample_evaluation_data):
    """Mathematically proves volume conservation: sum(SKU actuals) == Total Network actuals."""
    report = evaluate_forecast_slices(sample_evaluation_data)

    total_sku_actual = sum(s.total_actual_packs for s in report.sku_slices.values())
    total_market_actual = sum(s.total_actual_packs for s in report.market_slices.values())
    raw_total_actual = float(sample_evaluation_data["actual_demand"].sum())

    assert pytest.approx(total_sku_actual, rel=1e-5) == raw_total_actual
    assert pytest.approx(total_market_actual, rel=1e-5) == raw_total_actual


def test_evaluate_forecast_slices_horizon_boundaries(sample_evaluation_data):
    """Verifies that horizon buckets correctly partition into W01-W04, W05-W12, and W13-W26."""
    report = evaluate_forecast_slices(sample_evaluation_data)

    # 16 total weeks -> W01-W04 has 4 weeks, W05-W12 has 8 weeks, W13-W26 has 4 weeks (weeks 13, 14, 15, 16)
    # Each week has 4 series -> sample counts: 16, 32, 16
    assert report.horizon_slices["W01-W04"].metrics.num_samples == 16
    assert report.horizon_slices["W05-W12"].metrics.num_samples == 32
    assert report.horizon_slices["W13-W26"].metrics.num_samples == 16


# =============================================================================
# 2. TRACKING SIGNAL DRIFT MONITOR TESTS
# =============================================================================

def test_tracking_signal_centered_normal_severity():
    """Tests that balanced, zero-mean alternating errors remain within normal statistical bounds (|TS| <= 3.0)."""
    dates = [date(2026, 11, 2) + timedelta(days=7 * i) for i in range(20)]
    records = []
    for i, dt in enumerate(dates):
        act = 3000.0
        # Alternating error: +50, -50, +50, -50...
        fc = act + (50.0 if i % 2 == 0 else -50.0)
        records.append({
            "target_week": dt,
            "actual_demand": act,
            "forecast_quantity": fc
        })
    df = pd.DataFrame(records)

    result = evaluate_tracking_signal_drift(df)
    assert isinstance(result, TrackingSignalAuditResult)
    assert abs(result.final_tracking_signal) <= 1.0
    assert result.has_alarm is False
    assert result.severity == DriftAlarmSeverity.NORMAL
    assert "COMPLIANT" in result.prescriptive_action


def test_tracking_signal_positive_drift_alarm():
    """Tests that persistent over-forecasting triggers a critical drift ALARM (TS > 4.0)."""
    dates = [date(2026, 11, 2) + timedelta(days=7 * i) for i in range(10)]
    records = []
    for dt in dates:
        act = 3000.0
        # Chronic over-forecasting by 200 packs every week
        fc = act + 200.0
        records.append({
            "target_week": dt,
            "actual_demand": act,
            "forecast_quantity": fc
        })
    df = pd.DataFrame(records)

    result = evaluate_tracking_signal_drift(df)
    assert result.has_alarm is True
    assert result.severity == DriftAlarmSeverity.ALARM
    assert result.final_tracking_signal > 4.0
    assert "Over-Forecasting" in result.prescriptive_action


def test_tracking_signal_negative_drift_alarm():
    """Tests that persistent under-forecasting triggers a critical drift ALARM (TS < -4.0)."""
    dates = [date(2026, 11, 2) + timedelta(days=7 * i) for i in range(10)]
    records = []
    for dt in dates:
        act = 3000.0
        # Chronic under-forecasting by 200 packs every week
        fc = act - 200.0
        records.append({
            "target_week": dt,
            "actual_demand": act,
            "forecast_quantity": fc
        })
    df = pd.DataFrame(records)

    result = evaluate_tracking_signal_drift(df)
    assert result.has_alarm is True
    assert result.severity == DriftAlarmSeverity.ALARM
    assert result.final_tracking_signal < -4.0
    assert "Under-Forecasting" in result.prescriptive_action


# =============================================================================
# 3. VERSION-TO-VERSION WATERFALL & VARIANCE TESTS
# =============================================================================

def test_forecast_version_variance_exact_delta():
    """Tests waterfall comparison between identical base and comparison forecasts."""
    dates = [date(2026, 11, 2) + timedelta(days=7 * i) for i in range(4)]
    base_rows = []
    comp_rows = []
    for dt in dates:
        base_rows.append({
            "finished_sku_id": "SKU-01",
            "market_id": "MKT-01",
            "target_week": dt,
            "forecast_quantity": 2000.0
        })
        comp_rows.append({
            "finished_sku_id": "SKU-01",
            "market_id": "MKT-01",
            "target_week": dt,
            "forecast_quantity": 2100.0  # +100 packs shift
        })

    report = analyze_forecast_version_variance(
        pd.DataFrame(base_rows),
        pd.DataFrame(comp_rows),
        base_version_name="V1",
        comparison_version_name="V2"
    )

    assert isinstance(report, ForecastVersionComparisonReport)
    assert report.total_points_evaluated == 4
    assert report.net_volumetric_shift_packs == 400.0
    assert report.overall_variance_pct == 5.0
    assert report.material_shift_count == 0  # 5% is below 20% threshold
    assert report.has_critical_volatility is False


def test_forecast_version_variance_material_shift_detection():
    """Validates detection of material planning shifts (>20% or >1000 packs)."""
    dates = [date(2026, 11, 2)]
    base = pd.DataFrame([{
        "finished_sku_id": "SKU-01",
        "market_id": "MKT-01",
        "target_week": dates[0],
        "forecast_quantity": 2000.0
    }])
    comp = pd.DataFrame([{
        "finished_sku_id": "SKU-01",
        "market_id": "MKT-01",
        "target_week": dates[0],
        "forecast_quantity": 3500.0  # +1500 packs (+75% surge!)
    }])

    report = analyze_forecast_version_variance(base, comp)
    assert report.material_shift_count == 1
    assert report.has_critical_volatility is True
    assert report.variances[0].is_material_shift is True
    assert report.variances[0].variance_pct == 75.0


# =============================================================================
# 4. FORECAST REGISTRY & SQLITE PERSISTENCE TESTS
# =============================================================================

def test_forecast_registry_save_and_load_roundtrip(memory_db):
    """Tests saving a 26-week forecast version into SQLite and loading it back cleanly."""
    registry = ForecastRegistry(memory_db)

    # Construct dummy forecast table (2 rows)
    df = pd.DataFrame([
        {
            "forecast_id": "FC-TEST-001",
            "forecast_version_date": "2026-10-26",
            "target_week": "2026-11-02",
            "finished_sku_id": "SKU-AUG-500-T10",
            "market_id": "MKT-IN-HYD",
            "forecast_quantity": 3200.0,
            "lower_bound": 2900.0,
            "upper_bound": 3500.0,
            "override_quantity": None,
            "model_version": "ML_Ridge_Test_V1",
            "scenario_id": "SCN-BASE"
        },
        {
            "forecast_id": "FC-TEST-002",
            "forecast_version_date": "2026-10-26",
            "target_week": "2026-11-09",
            "finished_sku_id": "SKU-AUG-500-T10",
            "market_id": "MKT-IN-HYD",
            "forecast_quantity": 3250.0,
            "lower_bound": 2950.0,
            "upper_bound": 3550.0,
            "override_quantity": None,
            "model_version": "ML_Ridge_Test_V1",
            "scenario_id": "SCN-BASE"
        }
    ])

    saved_count = registry.save_forecast_version(df, overwrite=True)
    assert saved_count == 2

    # Load back
    loaded = registry.load_forecast_version("ML_Ridge_Test_V1", "SCN-BASE")
    assert len(loaded) == 2
    assert loaded["forecast_quantity"].iloc[0] == 3200.0
    assert loaded["model_version"].iloc[0] == "ML_Ridge_Test_V1"


def test_forecast_registry_list_versions(memory_db):
    """Tests list_registered_versions querying distinct model lineages."""
    registry = ForecastRegistry(memory_db)
    df = pd.DataFrame([{
        "forecast_id": "FC-V1-01",
        "forecast_version_date": "2026-10-26",
        "target_week": "2026-11-02",
        "finished_sku_id": "SKU-AUG-500-T10",
        "market_id": "MKT-IN-HYD",
        "forecast_quantity": 3000.0,
        "lower_bound": 2800.0,
        "upper_bound": 3200.0,
        "override_quantity": None,
        "model_version": "Version_A",
        "scenario_id": "SCN-BASE"
    }])
    registry.save_forecast_version(df)

    versions = registry.list_registered_versions()
    assert len(versions) == 1
    assert versions[0]["model_version"] == "Version_A"
    assert versions[0]["record_count"] == 1


def test_forecast_registry_overwrite_protection(memory_db):
    """Tests that overwrite=True cleanly replaces existing version without duplicate row inflation."""
    registry = ForecastRegistry(memory_db)
    df1 = pd.DataFrame([{
        "forecast_id": "FC-V1-01",
        "forecast_version_date": "2026-10-26",
        "target_week": "2026-11-02",
        "finished_sku_id": "SKU-AUG-500-T10",
        "market_id": "MKT-IN-HYD",
        "forecast_quantity": 3000.0,
        "lower_bound": 2800.0,
        "upper_bound": 3200.0,
        "override_quantity": None,
        "model_version": "Version_Overwrite_Test",
        "scenario_id": "SCN-BASE"
    }])
    df2 = pd.DataFrame([{
        "forecast_id": "FC-V1-01-REVISED",
        "forecast_version_date": "2026-10-26",
        "target_week": "2026-11-02",
        "finished_sku_id": "SKU-AUG-500-T10",
        "market_id": "MKT-IN-HYD",
        "forecast_quantity": 3500.0,
        "lower_bound": 3200.0,
        "upper_bound": 3800.0,
        "override_quantity": None,
        "model_version": "Version_Overwrite_Test",
        "scenario_id": "SCN-BASE"
    }])

    registry.save_forecast_version(df1, overwrite=True)
    registry.save_forecast_version(df2, overwrite=True)

    loaded = registry.load_forecast_version("Version_Overwrite_Test", "SCN-BASE")
    assert len(loaded) == 1
    assert loaded["forecast_quantity"].iloc[0] == 3500.0
    assert loaded["forecast_id"].iloc[0] == "FC-V1-01-REVISED"


def test_forecast_slice_report_markdown_generation(sample_evaluation_data):
    """Validates that ForecastSliceReport exports clean executive Markdown report."""
    report = evaluate_forecast_slices(sample_evaluation_data, model_name="Ridge_Regression")
    md = report.generate_markdown_summary()

    assert "# Multi-Horizon Forecast Slice-and-Dice Scorecard" in md
    assert "SKU-AUG-500-T10" in md
    assert "Weeks 01-04 (Lead Time)" in md
    assert "WAPE %" in md
