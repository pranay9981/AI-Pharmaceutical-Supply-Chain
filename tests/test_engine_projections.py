"""
Unit Test Suite for Multi-Echelon Weekly Inventory Projection Engine.
Phase 2 (Day 16) Core Analytics Validation.

Validates recursive balance equations, mathematical conservation (zero unexplained drift),
forward weeks of supply (WOS), stockout/safety stock breach detection, and Scenario A impact.
"""

import sqlite3
from datetime import date, timedelta
import pytest
import pandas as pd

from src.models.planning import FactInventoryProjection
from src.engine.projections import (
    calculate_inventory_projection,
    calculate_weeks_of_supply,
    generate_projection_from_database,
    compare_projection_scenarios,
    export_projections_to_dataframe,
    WeeklyProjectionBucket,
    ProjectionTrajectorySummary
)

DB_PATH = "data/processed/control_tower.db"


@pytest.fixture
def base_as_of_date():
    return date(2026, 10, 26)


# =============================================================================
# 1. MATHEMATICAL CONSERVATION & RECURSIVE BALANCE TESTS
# =============================================================================

def test_inventory_projection_mathematical_conservation(base_as_of_date):
    """
    Verifies the fundamental law of inventory conservation:
    Ending Inventory - Opening Inventory = Total Inflows - Total Outflows.
    Zero unexplained drift across all weeks.
    """
    initial_inv = 10000.0
    demands = [2000.0, 2500.0, 1800.0, 3000.0, 2200.0]
    receipts = [0.0, 5000.0, 0.0, 0.0, 4000.0]
    productions = [0.0, 0.0, 2000.0, 0.0, 0.0]
    safety_stock = 1500.0

    summary = calculate_inventory_projection(
        initial_inventory=initial_inv,
        weekly_demands=demands,
        weekly_receipts=receipts,
        weekly_productions=productions,
        safety_stock=safety_stock,
        start_date=base_as_of_date
    )

    assert summary.horizon_weeks == 5
    assert summary.initial_opening_inventory == 10000.0
    assert summary.total_forecast_demand == sum(demands)
    assert summary.total_planned_receipts == sum(receipts)
    assert summary.total_planned_production == sum(productions)

    # 1. Total horizon conservation
    expected_net = sum(receipts) + sum(productions) - sum(demands)
    expected_final = initial_inv + expected_net
    assert summary.net_total_change == expected_net
    assert summary.final_projected_inventory == expected_final

    # 2. Step-by-step per-week conservation
    prev_end = initial_inv
    for b in summary.weekly_buckets:
        assert b.opening_inventory == prev_end
        expected_step_end = round(b.opening_inventory + b.planned_receipts + b.planned_production - b.forecast_demand, 4)
        assert b.projected_ending_inventory == expected_step_end
        assert b.net_change == round(b.planned_receipts + b.planned_production - b.forecast_demand, 4)
        prev_end = b.projected_ending_inventory


def test_weeks_of_supply_exact_forward_coverage():
    """Verifies fractional forward-looking Weeks of Supply (WOS) calculation."""
    # 6,000 packs on hand
    # Forward demands: Week 1=2000, Week 2=2000, Week 3=4000
    # Consumes Week 1 (rem 4000), Week 2 (rem 2000), covers 2000/4000 of Week 3 = 2.5 weeks
    demands = [2000.0, 2000.0, 4000.0, 3000.0]
    wos = calculate_weeks_of_supply(6000.0, demands)
    assert wos == 2.5

    # Zero inventory -> 0.0 WOS
    assert calculate_weeks_of_supply(0.0, demands) == 0.0

    # Large inventory covering entire horizon
    wos_large = calculate_weeks_of_supply(22000.0, demands)
    assert wos_large > 4.0  # Extrapolates beyond 4 weeks


# =============================================================================
# 2. STOCKOUT & SAFETY STOCK BREACH DETECTION TESTS
# =============================================================================

def test_stockout_and_safety_stock_breach_detection(base_as_of_date):
    """
    Tests trajectory transitioning through:
    Healthy -> Safety Stock Breach -> Stockout -> Replenishment Recovery.
    """
    initial_inv = 5000.0
    # Week 0: 5000 - 2000 = 3000 (Above SS 2500 -> HEALTHY)
    # Week 1: 3000 - 1500 = 1500 (Below SS 2500 -> BREACH)
    # Week 2: 1500 - 2500 = -1000 (Below 0 -> STOCKOUT, Shortage 1000)
    # Week 3: -1000 + 6000 - 2000 = 3000 (Replenished -> HEALTHY)
    demands = [2000.0, 1500.0, 2500.0, 2000.0]
    receipts = [0.0, 0.0, 0.0, 6000.0]
    safety_stock = 2500.0

    summary = calculate_inventory_projection(
        initial_inventory=initial_inv,
        weekly_demands=demands,
        weekly_receipts=receipts,
        safety_stock=safety_stock,
        start_date=base_as_of_date
    )

    # Week 0
    b0 = summary.weekly_buckets[0]
    assert b0.projected_ending_inventory == 3000.0
    assert b0.is_stockout is False
    assert b0.is_safety_stock_breach is False

    # Week 1: Safety Stock Breach
    b1 = summary.weekly_buckets[1]
    assert b1.projected_ending_inventory == 1500.0
    assert b1.is_stockout is False
    assert b1.is_safety_stock_breach is True
    assert summary.first_safety_stock_breach_index == 1
    assert summary.first_safety_stock_breach_date == base_as_of_date + timedelta(weeks=1)

    # Week 2: Stockout
    b2 = summary.weekly_buckets[2]
    assert b2.projected_ending_inventory == -1000.0
    assert b2.physical_ending_inventory == 0.0  # Physically bounded
    assert b2.is_stockout is True
    assert b2.projected_shortage == 1000.0
    assert summary.first_stockout_week_index == 2
    assert summary.first_stockout_week_date == base_as_of_date + timedelta(weeks=2)

    # Week 3: Recovered
    b3 = summary.weekly_buckets[3]
    assert b3.projected_ending_inventory == 3000.0
    assert b3.is_stockout is False

    # Runway days
    assert summary.runway_days_to_breach == 7.0   # 1 week to breach
    assert summary.runway_days_to_stockout == 14.0  # 2 weeks to stockout


def test_safety_stock_breach_without_stockout(base_as_of_date):
    """Verifies safety stock buffer breach detection while inventory remains strictly positive."""
    initial_inv = 3000.0
    demands = [1000.0, 1000.0]
    safety_stock = 1500.0

    # Week 0: 3000 - 1000 = 2000 (Above SS 1500)
    # Week 1: 2000 - 1000 = 1000 (Below SS 1500, but > 0 -> Breach without stockout)
    summary = calculate_inventory_projection(
        initial_inventory=initial_inv,
        weekly_demands=demands,
        safety_stock=safety_stock,
        start_date=base_as_of_date
    )

    assert summary.stockout_weeks_count == 0
    assert summary.safety_stock_breach_weeks_count == 1
    assert summary.first_stockout_week_date is None
    assert summary.first_safety_stock_breach_index == 1


def test_zero_demand_and_edge_cases(base_as_of_date):
    """Verifies edge case handling for empty or zero inflows/demands."""
    # Zero demand throughout
    summary = calculate_inventory_projection(
        initial_inventory=5000.0,
        weekly_demands=[0.0, 0.0, 0.0],
        safety_stock=1000.0,
        start_date=base_as_of_date
    )
    assert summary.final_projected_inventory == 5000.0
    assert summary.stockout_weeks_count == 0

    # Length mismatch raises ValueError
    with pytest.raises(ValueError):
        calculate_inventory_projection(
            initial_inventory=5000.0,
            weekly_demands=[100.0, 200.0],
            weekly_receipts=[100.0]  # Mismatched length
        )


# =============================================================================
# 3. REAL DATABASE INTEGRATION & SCENARIO A IMPACT TESTS
# =============================================================================

def test_database_integrated_sku_projection(base_as_of_date):
    """
    Executes end-to-end forward projection from real SQLite control_tower.db:
    Verifies 26 weeks generated, Pydantic FactInventoryProjection validation passes.
    """
    conn = sqlite3.connect(DB_PATH)
    trajectory, pydantic_projections = generate_projection_from_database(
        db_conn=conn,
        finished_sku_id="SKU-AUG-500-T10",
        location_id="LOC-DC-01",
        as_of_date=base_as_of_date,
        scenario_id="SCN-BASE",
        safety_stock=4000.0,
        min_acceptable_rsl_days=0
    )
    conn.close()

    assert trajectory.horizon_weeks == 26
    assert len(trajectory.weekly_buckets) == 26
    assert len(pydantic_projections) == 26
    assert trajectory.initial_opening_inventory == 19000.0  # All physical released stock on site (18k - 2k res + 3k near-exp)

    # Verify Pydantic validator passes
    for p in pydantic_projections:
        assert isinstance(p, FactInventoryProjection)
        assert p.item_id == "SKU-AUG-500-T10"
        assert p.location_id == "LOC-DC-01"
        assert p.scenario_id == "SCN-BASE"


def test_scenario_a_disruption_impact_comparison(base_as_of_date):
    """
    Verifies Scenario A (Delayed API Supplier delivery PO-2026-001):
    In SCN-BASE, replenishment arrives in Week 3 (Nov 16, 20,000 packs) preventing stockout.
    In SCN-A-API-DELAY, receipts in Week 3 are zero due to supplier delay (shifted to Week 5),
    triggering severe stockout across Weeks 3 and 4!
    """
    conn = sqlite3.connect(DB_PATH)
    base_traj, _ = generate_projection_from_database(
        db_conn=conn,
        finished_sku_id="SKU-AUG-500-T10",
        location_id="LOC-DC-01",
        as_of_date=base_as_of_date,
        scenario_id="SCN-BASE",
        safety_stock=4000.0,
        min_acceptable_rsl_days=0
    )
    conn.close()

    # In Baseline: Week 3 receives 20,000 packs -> ending inventory = 14,034 (Healthy)
    assert base_traj.weekly_buckets[3].planned_receipts == 20000.0
    assert base_traj.weekly_buckets[3].projected_ending_inventory == 14034.0
    assert base_traj.weekly_buckets[3].is_stockout is False

    # Construct disrupted trajectory: Week 3 (index 3, Nov 16) planned receipt of 20,000 is delayed 14 days to Week 5 (index 5)
    disrupted_receipts = [0.0] * 26
    disrupted_receipts[5] = 20000.0  # Arrives 2 weeks late

    weekly_demands = [b.forecast_demand for b in base_traj.weekly_buckets]

    disrupted_traj = calculate_inventory_projection(
        initial_inventory=base_traj.initial_opening_inventory,
        weekly_demands=weekly_demands,
        weekly_receipts=disrupted_receipts,
        safety_stock=4000.0,
        start_date=base_as_of_date,
        item_id="SKU-AUG-500-T10",
        location_id="LOC-DC-01",
        scenario_id="SCN-A-API-DELAY"
    )

    comparison = compare_projection_scenarios(base_traj, disrupted_traj)

    # In Disruption: Week 3 receives 0 -> ending inventory = -5,966 (STOCKOUT!)
    assert disrupted_traj.weekly_buckets[3].is_stockout is True
    assert disrupted_traj.weekly_buckets[3].projected_ending_inventory == -5966.0
    assert disrupted_traj.weekly_buckets[3].projected_shortage == 5966.0

    # Week 4 continues stockout: -5966 - 5833 = -11,799
    assert disrupted_traj.weekly_buckets[4].is_stockout is True
    assert disrupted_traj.weekly_buckets[4].projected_ending_inventory == -11799.0
    assert disrupted_traj.weekly_buckets[4].projected_shortage == 11799.0

    assert disrupted_traj.first_stockout_week_index == 3
    assert disrupted_traj.first_stockout_week_date == date(2026, 11, 16)

    # Comparison metrics
    assert comparison["is_disruption_impact_severe"] is True
    assert comparison["delta_stockout_weeks"] >= 2
    assert comparison["delta_shortage_units"] > 11000.0


def test_export_projections_to_dataframe(base_as_of_date):
    """Verifies that projections export to a valid Pandas DataFrame matching relational schema."""
    conn = sqlite3.connect(DB_PATH)
    _, pydantic_projections = generate_projection_from_database(
        db_conn=conn,
        finished_sku_id="SKU-AUG-500-T10",
        location_id="LOC-DC-01",
        as_of_date=base_as_of_date
    )
    conn.close()

    df = export_projections_to_dataframe(pydantic_projections)
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 26
    expected_cols = [
        "projection_id", "item_type", "item_id", "location_id", "week_start_date",
        "opening_inventory", "planned_receipts", "planned_production", "forecast_demand",
        "projected_ending_inventory", "safety_stock", "projected_shortage", "scenario_id"
    ]
    for col in expected_cols:
        assert col in df.columns
