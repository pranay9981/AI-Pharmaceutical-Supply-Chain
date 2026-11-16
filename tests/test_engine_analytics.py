"""
Unit Test Suite for Supplier OTIF & Plant Line Capacity Analytics Engine.
Phase 2 (Day 18) Core Analytics Validation.

Validates vendor On-Time In-Full (OTIF) %, lead-time variance distributions,
manufacturing line capacity utilization % (net available vs committed hours),
and Scenario E capacity conflict modeling.
"""

import sqlite3
from datetime import date, timedelta
import pytest
import pandas as pd

from src.models.procurement_inventory import FactPurchaseOrder
from src.models.capacity_logistics import FactCapacity
from src.models.master import DimSupplier
from src.engine.analytics import (
    evaluate_po_otif_performance,
    calculate_supplier_otif_metrics,
    calculate_line_capacity_metrics,
    detect_capacity_bottlenecks,
    evaluate_capacity_conflict_scenario_e,
    generate_supplier_analytics_from_database,
    generate_capacity_analytics_from_database,
    export_analytics_to_dataframes,
    PurchaseOrderPerformance,
    SupplierOTIFScorecard,
    PlantCapacitySummary
)

DB_PATH = "data/processed/control_tower.db"


@pytest.fixture
def base_as_of_date():
    return date(2026, 10, 26)


# =============================================================================
# 1. PURCHASE ORDER OTIF PERFORMANCE TESTS
# =============================================================================

def test_po_otif_on_time_in_full_pass():
    """Verifies that an order delivered on or before confirmed date in full passes OTIF."""
    po = FactPurchaseOrder(
        purchase_order_id="PO-TEST-001",
        supplier_id="SUP-001",
        material_sku_id="MAT-API-001",
        order_date=date(2026, 9, 1),
        requested_delivery_date=date(2026, 9, 20),
        confirmed_delivery_date=date(2026, 9, 20),
        actual_receipt_date=date(2026, 9, 18),  # 2 days early
        ordered_quantity=100.0,
        received_quantity=100.0,
        purchase_order_status="Received"
    )

    perf = evaluate_po_otif_performance(po)
    assert perf.is_on_time is True
    assert perf.is_in_full is True
    assert perf.is_otif is True
    assert perf.delay_days == 0
    assert perf.fill_rate == 1.0
    assert perf.promised_lead_time_days == 19
    assert perf.actual_lead_time_days == 17
    assert perf.lead_time_variance_days == -2


def test_po_otif_late_delivery_failure():
    """Verifies that an order delivered after confirmed date fails OTIF with exact delay days."""
    po = FactPurchaseOrder(
        purchase_order_id="PO-TEST-002",
        supplier_id="SUP-001",
        material_sku_id="MAT-API-001",
        order_date=date(2026, 9, 1),
        requested_delivery_date=date(2026, 9, 20),
        confirmed_delivery_date=date(2026, 9, 20),
        actual_receipt_date=date(2026, 9, 25),  # 5 days late
        ordered_quantity=100.0,
        received_quantity=100.0,
        purchase_order_status="Received"
    )

    perf = evaluate_po_otif_performance(po)
    assert perf.is_on_time is False
    assert perf.is_in_full is True
    assert perf.is_otif is False
    assert perf.delay_days == 5
    assert perf.lead_time_variance_days == 5


def test_po_otif_partial_delivery_failure():
    """Verifies that an on-time order with short quantity fails In-Full and OTIF."""
    po = FactPurchaseOrder(
        purchase_order_id="PO-TEST-003",
        supplier_id="SUP-001",
        material_sku_id="MAT-API-001",
        order_date=date(2026, 9, 1),
        requested_delivery_date=date(2026, 9, 20),
        confirmed_delivery_date=date(2026, 9, 20),
        actual_receipt_date=date(2026, 9, 20),  # On-time
        ordered_quantity=100.0,
        received_quantity=80.0,   # 20% short
        purchase_order_status="Received"
    )

    perf = evaluate_po_otif_performance(po)
    assert perf.is_on_time is True
    assert perf.is_in_full is False
    assert perf.is_otif is False
    assert perf.fill_rate == 0.80


# =============================================================================
# 2. SUPPLIER SCORECARD AGGREGATION & METRICS
# =============================================================================

def test_supplier_otif_scorecard_aggregation():
    """
    Verifies aggregate OTIF %, lead time statistics, and risk tier evaluation:
    4 orders: 2 perfect OTIF, 1 late, 1 partial delivery -> OTIF = 50.0%.
    """
    pos = [
        # Order 1: OTIF
        FactPurchaseOrder(
            purchase_order_id="PO-1", supplier_id="SUP-TEST", material_sku_id="MAT-1",
            order_date=date(2026, 1, 1), requested_delivery_date=date(2026, 1, 20), confirmed_delivery_date=date(2026, 1, 20),
            actual_receipt_date=date(2026, 1, 19), ordered_quantity=100.0, received_quantity=100.0, purchase_order_status="Received"
        ),
        # Order 2: OTIF
        FactPurchaseOrder(
            purchase_order_id="PO-2", supplier_id="SUP-TEST", material_sku_id="MAT-1",
            order_date=date(2026, 2, 1), requested_delivery_date=date(2026, 2, 20), confirmed_delivery_date=date(2026, 2, 20),
            actual_receipt_date=date(2026, 2, 20), ordered_quantity=150.0, received_quantity=150.0, purchase_order_status="Received"
        ),
        # Order 3: Late by 4 days
        FactPurchaseOrder(
            purchase_order_id="PO-3", supplier_id="SUP-TEST", material_sku_id="MAT-1",
            order_date=date(2026, 3, 1), requested_delivery_date=date(2026, 3, 20), confirmed_delivery_date=date(2026, 3, 20),
            actual_receipt_date=date(2026, 3, 24), ordered_quantity=100.0, received_quantity=100.0, purchase_order_status="Received"
        ),
        # Order 4: Partial delivery (75/100)
        FactPurchaseOrder(
            purchase_order_id="PO-4", supplier_id="SUP-TEST", material_sku_id="MAT-1",
            order_date=date(2026, 4, 1), requested_delivery_date=date(2026, 4, 20), confirmed_delivery_date=date(2026, 4, 20),
            actual_receipt_date=date(2026, 4, 20), ordered_quantity=100.0, received_quantity=75.0, purchase_order_status="Received"
        )
    ]

    card = calculate_supplier_otif_metrics(
        purchase_orders=pos,
        supplier_id="SUP-TEST",
        supplier_name="Global Active Ingredients Ltd",
        target_otif=95.0,
        single_source_dependency=True
    )

    assert card.total_orders_evaluated == 4
    assert card.on_time_orders_count == 3      # PO-1, PO-2, PO-4
    assert card.in_full_orders_count == 3      # PO-1, PO-2, PO-3
    assert card.otif_orders_count == 2         # PO-1, PO-2

    assert card.on_time_percentage == 75.0
    assert card.in_full_percentage == 75.0
    assert card.otif_percentage == 50.0
    assert card.is_target_met is False
    assert card.max_delay_days == 4

    # Single-source supplier below target -> Critical risk
    assert card.supplier_risk_tier == "Critical"


# =============================================================================
# 3. MANUFACTURING LINE CAPACITY UTILISATION TESTS
# =============================================================================

def test_line_capacity_utilisation_and_idle_hours(base_as_of_date):
    """Verifies standard capacity metrics: net available, committed, utilization %, and idle hours."""
    caps = [
        FactCapacity(
            capacity_record_id="CAP-TEST-01",
            location_id="LOC-PLANT-01",
            production_line_id="LINE-PLANT1-01",
            period_start_date=base_as_of_date,
            net_available_hours=120.0,
            maintenance_hours=8.0,
            downtime_hours=0.0,
            committed_hours=40.0
        ),
        FactCapacity(
            capacity_record_id="CAP-TEST-02",
            location_id="LOC-PLANT-01",
            production_line_id="LINE-PLANT1-02",
            period_start_date=base_as_of_date,
            net_available_hours=120.0,
            maintenance_hours=8.0,
            downtime_hours=0.0,
            committed_hours=30.0
        )
    ]

    summary = calculate_line_capacity_metrics(caps, location_id="LOC-PLANT-01")

    assert summary.total_net_available_hours == 240.0
    assert summary.total_committed_hours == 70.0
    assert summary.average_utilization_pct == round((70.0 / 240.0) * 100.0, 2)
    assert summary.has_capacity_overload is False
    assert summary.overload_weeks_count == 0

    # Line 1: 40/120 = 33.33%, 80 hrs idle
    m1 = summary.weekly_line_metrics[0]
    assert m1.utilization_pct == 33.33
    assert m1.idle_available_hours == 80.0
    assert m1.is_overloaded is False


def test_capacity_bottleneck_and_overload_detection(base_as_of_date):
    """Verifies that production lines committed over 100% are flagged as bottlenecks."""
    caps = [
        # Line 1 Overloaded: 144 hours committed / 120 net available = 120.0%
        FactCapacity(
            capacity_record_id="CAP-OVER-01",
            location_id="LOC-PLANT-01",
            production_line_id="LINE-PLANT1-01",
            period_start_date=base_as_of_date,
            net_available_hours=120.0,
            maintenance_hours=8.0,
            downtime_hours=0.0,
            committed_hours=144.0
        ),
        # Line 2 Healthy: 30 hours / 120 net available = 25.0%
        FactCapacity(
            capacity_record_id="CAP-OK-02",
            location_id="LOC-PLANT-01",
            production_line_id="LINE-PLANT1-02",
            period_start_date=base_as_of_date,
            net_available_hours=120.0,
            maintenance_hours=8.0,
            downtime_hours=0.0,
            committed_hours=30.0
        )
    ]

    summary = calculate_line_capacity_metrics(caps)
    assert summary.has_capacity_overload is True
    assert summary.overload_weeks_count == 1
    assert "LINE-PLANT1-01" in summary.overloaded_line_ids

    # Bottleneck filter
    bottlenecks = detect_capacity_bottlenecks(caps, overload_threshold_pct=100.0)
    assert len(bottlenecks) == 1
    assert bottlenecks[0].production_line_id == "LINE-PLANT1-01"
    assert bottlenecks[0].overload_hours == 24.0
    assert bottlenecks[0].utilization_pct == 120.0


# =============================================================================
# 4. SCENARIO E: CAPACITY CONFLICT & RESCHEDULE SIMULATION
# =============================================================================

def test_scenario_e_capacity_conflict_and_parallel_line_offload(base_as_of_date):
    """
    Simulates Benchmark Scenario E (Line 1 Capacity Conflict):
    Line 1 receives +90 surge hours on Week 2 (Nov 09), raising commitment to 130 hours (108.3% overload).
    Tests feasibility of offloading the 10-hour overload to Line 2 (which has 120 hours net available).
    """
    caps = [
        FactCapacity(
            capacity_record_id="CAP-01", location_id="LOC-PLANT-01", production_line_id="LINE-PLANT1-01",
            period_start_date=base_as_of_date + timedelta(weeks=2), net_available_hours=120.0,
            maintenance_hours=8.0, downtime_hours=0.0, committed_hours=40.0
        ),
        FactCapacity(
            capacity_record_id="CAP-02", location_id="LOC-PLANT-01", production_line_id="LINE-PLANT1-02",
            period_start_date=base_as_of_date + timedelta(weeks=2), net_available_hours=120.0,
            maintenance_hours=8.0, downtime_hours=0.0, committed_hours=0.0
        )
    ]

    # Inject 90 extra hours on Line 1 -> Committed = 40 + 90 = 130 hours (10 hours over 120 net available)
    sim = evaluate_capacity_conflict_scenario_e(
        capacity_records=caps,
        target_line_id="LINE-PLANT1-01",
        target_week_start=base_as_of_date + timedelta(weeks=2),
        additional_committed_hours=90.0,
        parallel_line_id="LINE-PLANT1-02"
    )

    assert sim["is_overloaded"] is True
    assert sim["new_committed_hours"] == 130.0
    assert sim["overload_hours"] == 10.0
    assert sim["utilization_pct"] == round((130.0 / 120.0) * 100.0, 2)

    # Line 2 has 120 idle hours available -> can easily absorb the 10-hour deficit!
    assert sim["parallel_line_idle_hours"] == 120.0
    assert sim["can_offload_to_parallel_line"] is True
    assert "Reschedule 10.0 hours to parallel line LINE-PLANT1-02" in sim["recommended_action"]


# =============================================================================
# 5. REAL DATABASE INTEGRATION TESTS
# =============================================================================

def test_database_integrated_supplier_analytics():
    """Queries SQLite control_tower.db and generates scorecards for qualified suppliers."""
    conn = sqlite3.connect(DB_PATH)
    scorecards = generate_supplier_analytics_from_database(conn)
    conn.close()

    assert len(scorecards) == 2
    assert "SUP-001" in scorecards  # API vendor
    assert "SUP-002" in scorecards  # Packaging converter

    sup1 = scorecards["SUP-001"]
    assert sup1.supplier_name == "Deccan Active Pharma Chem Pvt Ltd"
    assert sup1.single_source_dependency is True


def test_database_integrated_capacity_analytics():
    """Queries SQLite control_tower.db and generates 52-week capacity audit for Plant Baddi."""
    conn = sqlite3.connect(DB_PATH)
    cap_summary = generate_capacity_analytics_from_database(conn, location_id="LOC-PLANT-01")
    conn.close()

    assert cap_summary.horizon_weeks == 26
    assert len(cap_summary.weekly_line_metrics) == 52  # 26 weeks * 2 lines
    assert cap_summary.total_net_available_hours == 52 * 120.0
    assert cap_summary.has_capacity_overload is False


def test_export_analytics_to_dataframes():
    """Verifies that analytics results export cleanly into Pandas DataFrames for reporting."""
    conn = sqlite3.connect(DB_PATH)
    scorecards = generate_supplier_analytics_from_database(conn)
    cap_summary = generate_capacity_analytics_from_database(conn)
    conn.close()

    df_supp, df_cap = export_analytics_to_dataframes(scorecards, cap_summary)
    assert isinstance(df_supp, pd.DataFrame)
    assert len(df_supp) == 2
    assert "otif_pct" in df_supp.columns

    assert isinstance(df_cap, pd.DataFrame)
    assert len(df_cap) == 52
    assert "utilization_pct" in df_cap.columns
