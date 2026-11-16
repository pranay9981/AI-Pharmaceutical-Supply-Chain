"""
Unit Tests for Pharmaceutical Demand Anomaly Detection & Impact Propagation Engine.
Phase 2 (Day 24) Forecasting Layer Verification.

Validates rolling volatility-adjusted Z-scores, non-parametric Tukey's IQR fences,
structural step-change identification, cross-market channel distortion, downstream supply chain
impact propagation, edge cases (zero variance, insufficient history), and real database audit.
"""

import os
import sqlite3
import pytest
import numpy as np
import pandas as pd
from datetime import date, datetime, timedelta

from src.forecasting.anomaly import (
    AnomalyType,
    AnomalySeverity,
    DownstreamSupplyImpact,
    DemandAnomalyRecord,
    AnomalySummaryByDimension,
    AnomalyDetectionReport,
    assess_downstream_impact,
    evaluate_point_anomaly,
    detect_structural_shift,
    detect_series_anomalies,
    detect_network_demand_anomalies,
    DemandAnomalyDetector,
    DEFAULT_SKU_PRICES
)
from src.forecasting.prep import load_demand_history_from_db


DB_PATH = "data/processed/control_tower.db"


# =============================================================================
# POINT EVALUATION TESTS
# =============================================================================

def test_evaluate_point_anomaly_normal():
    """Verifies that an observation well within normal distribution bounds is flagged as NORMAL."""
    # Historical series with mean ~ 3000, std ~ 150
    history = [3000.0, 3050.0, 2980.0, 3020.0, 2950.0, 3010.0, 3040.0, 2990.0]
    rec = evaluate_point_anomaly(
        current_val=3025.0,
        historical_series=history,
        observation_date=date(2026, 5, 4),
        finished_sku_id="SKU-AUG-500-T10",
        market_id="MKT-IN-HYD",
        z_threshold=3.0,
        iqr_multiplier=1.5
    )
    assert rec.is_anomaly is False
    assert rec.anomaly_type == AnomalyType.NORMAL
    assert rec.severity == AnomalySeverity.NORMAL
    assert abs(rec.z_score) < 1.0
    assert rec.downstream_impact.stockout_risk_flag is False
    assert rec.downstream_impact.expiry_risk_flag is False


def test_evaluate_point_anomaly_surge_zscore():
    """Verifies that an extreme spike (>3 sigma) is classified as DEMAND_SURGE with high/critical severity."""
    history = [3000.0, 3100.0, 2900.0, 3050.0, 2950.0, 3000.0, 3050.0, 3000.0]
    # Injected massive surge (e.g. epidemic outbreak)
    surge_val = 6500.0
    rec = evaluate_point_anomaly(
        current_val=surge_val,
        historical_series=history,
        observation_date=date(2026, 8, 3),
        finished_sku_id="SKU-AUG-500-T10",
        market_id="MKT-IN-HYD",
        z_threshold=3.0,
        iqr_multiplier=1.5
    )
    assert rec.is_anomaly is True
    assert rec.anomaly_type == AnomalyType.DEMAND_SURGE
    assert rec.severity in (AnomalySeverity.HIGH, AnomalySeverity.CRITICAL)
    assert rec.z_score > 3.0
    assert rec.residual > 0
    assert rec.downstream_impact.safety_stock_depleted_pct > 50.0
    assert rec.downstream_impact.days_of_supply_delta < 0
    assert "EXPEDITE_REPLENISHMENT" in rec.downstream_impact.recommended_action


def test_evaluate_point_anomaly_plunge_iqr():
    """Verifies that a severe demand collapse is flagged as DEMAND_PLUNGE."""
    history = [4000.0, 4200.0, 3900.0, 4100.0, 4050.0, 3950.0, 4150.0, 4000.0]
    # Severe drop (e.g. product recall or lost hospital tender)
    plunge_val = 800.0
    rec = evaluate_point_anomaly(
        current_val=plunge_val,
        historical_series=history,
        observation_date=date(2026, 2, 16),
        finished_sku_id="SKU-AUG-500-T10",
        market_id="MKT-IN-HYD",
        z_threshold=3.0,
        iqr_multiplier=1.5
    )
    assert rec.is_anomaly is True
    assert rec.anomaly_type == AnomalyType.DEMAND_PLUNGE
    assert rec.severity in (AnomalySeverity.HIGH, AnomalySeverity.CRITICAL)
    assert rec.z_score < -3.0
    assert rec.downstream_impact.days_of_supply_delta > 0
    assert "THROTTLE_PRODUCTION" in rec.downstream_impact.recommended_action


def test_evaluate_point_anomaly_constant_series_handling():
    """Verifies that zero-variance constant historical series handles division by zero safely."""
    constant_history = [2500.0, 2500.0, 2500.0, 2500.0, 2500.0]
    
    # 1. Matching value should be normal
    rec_normal = evaluate_point_anomaly(
        current_val=2500.0,
        historical_series=constant_history,
        z_threshold=3.0
    )
    assert rec_normal.is_anomaly is False
    assert rec_normal.z_score == 0.0

    # 2. Deviating value should not crash and should flag outlier
    rec_spike = evaluate_point_anomaly(
        current_val=5000.0,
        historical_series=constant_history,
        z_threshold=3.0
    )
    assert rec_spike.is_anomaly is True
    assert rec_spike.anomaly_type == AnomalyType.DEMAND_SURGE
    assert not np.isnan(rec_spike.z_score)
    assert not np.isinf(rec_spike.z_score)


def test_evaluate_point_anomaly_insufficient_history():
    """Verifies that when history has fewer than min_periods, it returns a non-blocking normal record."""
    short_history = [3000.0, 3200.0]  # Only 2 points, min_periods=4
    rec = evaluate_point_anomaly(
        current_val=5000.0,
        historical_series=short_history,
        min_periods=4
    )
    assert rec.is_anomaly is False
    assert rec.detection_method == "INSUFFICIENT_HISTORY"


# =============================================================================
# STRUCTURAL SHIFT & CHANNEL DISTORTION TESTS
# =============================================================================

def test_detect_structural_shift():
    """Verifies detection of sustained step-changes in mean demand velocity."""
    # 12 weeks of baseline (~2000), followed by 4 weeks of higher demand (~3200, +60% shift)
    baseline = [2000.0] * 12
    shifted_up = [3200.0] * 4
    series_up = baseline + shifted_up
    is_shift_up, s_mean_up, l_mean_up, pct_chg_up = detect_structural_shift(
        series_up, short_window=4, long_window=12, threshold_pct=0.35
    )
    assert is_shift_up is True
    assert s_mean_up == 3200.0
    assert l_mean_up == 2000.0
    assert pytest.approx(pct_chg_up, rel=1e-3) == 0.60

    # Stable series without shift
    stable_series = [2000.0] * 16
    is_shift_stable, _, _, pct_chg_stable = detect_structural_shift(
        stable_series, short_window=4, long_window=12, threshold_pct=0.35
    )
    assert is_shift_stable is False
    assert abs(pct_chg_stable) < 1e-4


def test_assess_downstream_impact_all_types():
    """Verifies downstream supply chain impact metrics across all anomaly types."""
    # 1. Normal
    imp_norm = assess_downstream_impact(AnomalyType.NORMAL, 3000.0, 3000.0)
    assert imp_norm.days_of_supply_delta == 0.0
    assert imp_norm.estimated_financial_exposure_usd == 0.0

    # 2. Surge
    imp_surge = assess_downstream_impact(
        AnomalyType.DEMAND_SURGE, 6000.0, 3000.0, finished_sku_id="SKU-AUG-500-T10", unit_price_usd=10.0
    )
    assert imp_surge.days_of_supply_delta < 0
    assert imp_surge.estimated_financial_exposure_usd == 30000.0  # 3000 excess * $10.0
    assert imp_surge.safety_stock_depleted_pct == 50.0  # default SS is 2 * expected = 6000

    # 3. Plunge
    imp_plunge = assess_downstream_impact(
        AnomalyType.DEMAND_PLUNGE, 1000.0, 3000.0, finished_sku_id="SKU-AUG-500-T10", unit_price_usd=10.0
    )
    assert imp_plunge.days_of_supply_delta > 0
    assert imp_plunge.estimated_financial_exposure_usd == 2000.0 * 10.0 * 0.20  # 20% holding cost rate

    # 4. Structural Shift
    imp_shift = assess_downstream_impact(
        AnomalyType.STRUCTURAL_SHIFT, 4500.0, 3000.0, finished_sku_id="SKU-AUG-500-T10"
    )
    assert "REBASELINE_MRP" in imp_shift.recommended_action


# =============================================================================
# TIME-SERIES & NETWORK-WIDE SCAN TESTS
# =============================================================================

def test_detect_series_anomalies_synthetic():
    """Generates synthetic 52-week time-series and tests sequential rolling anomaly detection."""
    np.random.seed(42)
    dates = pd.date_range("2025-01-06", periods=52, freq="W-MON")
    base_demand = 3000.0 + np.random.normal(0, 100, 52)
    
    # Inject deliberate surge at index 25 (week 26)
    base_demand[25] = 6500.0
    # Inject deliberate plunge at index 40 (week 41)
    base_demand[40] = 500.0

    df = pd.DataFrame({
        "week_start_date": dates,
        "finished_sku_id": "SKU-AUG-500-T10",
        "market_id": "MKT-IN-HYD",
        "demand_quantity": base_demand
    })

    records = detect_series_anomalies(df, window=12, z_threshold=3.0)
    assert len(records) == 52

    # Check that week 25 was detected as surge
    surge_rec = records[25]
    assert surge_rec.is_anomaly is True
    assert surge_rec.anomaly_type == AnomalyType.DEMAND_SURGE
    assert surge_rec.z_score > 3.0

    # Check that week 40 was detected as plunge
    plunge_rec = records[40]
    assert plunge_rec.is_anomaly is True
    assert plunge_rec.anomaly_type == AnomalyType.DEMAND_PLUNGE
    assert plunge_rec.z_score < -3.0


def test_detect_network_demand_anomalies_report():
    """Verifies network-wide multi-echelon demand anomaly reporting and dimensional summaries."""
    dates = pd.date_range("2025-01-06", periods=26, freq="W-MON")
    rows = []
    
    for dt in dates:
        # SKU 1 in Hyd and Pun
        rows.append({"week_start_date": dt, "finished_sku_id": "SKU-AUG-500-T10", "market_id": "MKT-IN-HYD", "demand_quantity": 3000.0})
        rows.append({"week_start_date": dt, "finished_sku_id": "SKU-AUG-500-T10", "market_id": "MKT-IN-PUN", "demand_quantity": 2500.0})
        # SKU 2 in Hyd and Pun
        rows.append({"week_start_date": dt, "finished_sku_id": "SKU-AUG-500-T30", "market_id": "MKT-IN-HYD", "demand_quantity": 1800.0})
        rows.append({"week_start_date": dt, "finished_sku_id": "SKU-AUG-500-T30", "market_id": "MKT-IN-PUN", "demand_quantity": 1500.0})

    df = pd.DataFrame(rows)

    # Inject extreme spike in T10 Hyd at week 20
    idx_spike = df[(df["week_start_date"] == dates[20]) & (df["finished_sku_id"] == "SKU-AUG-500-T10") & (df["market_id"] == "MKT-IN-HYD")].index[0]
    df.loc[idx_spike, "demand_quantity"] = 8000.0

    report = detect_network_demand_anomalies(df, window=12, z_threshold=3.0)

    assert report.total_observations == 26 * 4
    assert report.total_anomalies >= 1
    assert "SKU-AUG-500-T10" in report.summary_by_sku
    assert "MKT-IN-HYD" in report.summary_by_market
    assert report.total_network_exposure_usd > 0
    assert len(report.executive_summary) > 50

    # Test conversion to dataframe
    audit_df = report.to_dataframe()
    assert len(audit_df) == report.total_observations
    assert "z_score" in audit_df.columns
    assert "stockout_risk_flag" in audit_df.columns


def test_demand_anomaly_detector_oop_api():
    """Verifies that DemandAnomalyDetector object-oriented class functions identically."""
    detector = DemandAnomalyDetector(window=12, z_threshold=3.0)
    history = [3000.0] * 12
    rec = detector.evaluate_point(
        current_val=6000.0,
        historical_series=history,
        finished_sku_id="SKU-AUG-500-T10"
    )
    assert rec.is_anomaly is True
    assert rec.anomaly_type == AnomalyType.DEMAND_SURGE


# =============================================================================
# REAL DATABASE AUDIT TEST
# =============================================================================

@pytest.mark.skipif(not os.path.exists(DB_PATH), reason="Database not found")
def test_real_database_demand_history_anomalies():
    """
    Audits actual 104-week commercial demand history from SQLite control tower database.
    Confirms that real historical monsoon respiratory surges are detected by the engine.
    """
    conn = sqlite3.connect(DB_PATH)
    try:
        df = load_demand_history_from_db(conn, scenario_id="SCN-BASE")
        assert len(df) == 416  # 4 series * 104 weeks

        detector = DemandAnomalyDetector(window=12, z_threshold=2.8)
        report = detector.detect_network(df)

        assert report.total_observations == 416
        assert report.total_anomalies > 0
        assert report.surge_count > 0
        assert report.plunge_count > 0

        # Verify that August Monsoon surge dates were captured
        monsoon_surges = [
            r for r in report.anomalies 
            if r.anomaly_type in (AnomalyType.DEMAND_SURGE, AnomalyType.CHANNEL_DISTORTION)
            and r.observation_date.month in (7, 8, 9)
        ]
        assert len(monsoon_surges) >= 2, "Expected August monsoon surges to be detected in real history"

        # Verify executive summary generation
        assert "Network Demand Anomaly Audit" in report.executive_summary
        assert report.total_network_exposure_usd > 0.0

    finally:
        conn.close()
