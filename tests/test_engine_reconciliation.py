"""
Automated Pytest Suite for Multi-Echelon Analytics Reconciliation & Mathematical Conservation.
Phase 2 (Day 19) Deliverable.

Validates zero unexplained stock drift, mass-balance conservation, and cross-echelon cohesion:
1. Node-level recursive inventory balance: I_t = I_{t-1} + R_t + P_t - D_t (0.00% drift)
2. Inter-echelon logistics handoffs (Shipped == Received + In-Transit)
3. BOM gross explosion and scrap factor bounds (1.0% to 5.0%)
4. FEFO order fulfillment conservation (Requested == Fulfilled + Unmet) & quality gating
5. Supplier purchase order receipts and OTIF logical consistency
6. Plant production line machine hours conservation (Net Available == Committed + Idle - Overload)
7. Full SQLite database network reconciliation (122/122 items conserved, 100.0% pass rate)

Strictly zero LLM mathematical calculations. Pure deterministic verification.
"""

import sqlite3
from datetime import date, timedelta
import pandas as pd
import pytest

from src.models.procurement_inventory import FactInventoryLot, FactPurchaseOrder
from src.models.manufacturing_quality import FactProductionOrder
from src.models.capacity_logistics import FactShipment, FactCapacity
from src.models.bridges import BridgeBillOfMaterial
from src.engine.inventory import parse_date, allocate_fefo
from src.engine.projections import (
    calculate_inventory_projection,
    generate_projection_from_database,
    WeeklyProjectionBucket,
    ProjectionTrajectorySummary
)
from src.engine.reconciliation import (
    AuditType,
    AuditStatus,
    ReconciliationItemResult,
    AuditCategorySummary,
    ReconciliationReport,
    reconcile_inventory_balance_equation,
    audit_inventory_projection_trajectory,
    audit_inter_echelon_shipments,
    audit_bom_explosion_mass_balance,
    audit_fefo_allocation_conservation,
    audit_procurement_po_receipts,
    audit_line_capacity_conservation,
    run_full_network_reconciliation
)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def db_path():
    """Canonical processed SQLite control tower database path."""
    return "data/processed/control_tower.db"


@pytest.fixture
def db_connection(db_path):
    """Provides an active SQLite connection to the production database."""
    conn = sqlite3.connect(db_path)
    yield conn
    conn.close()


@pytest.fixture
def mock_projection_summary():
    """Constructs a deterministic 4-week inventory projection summary for mathematical testing."""
    buckets = [
        WeeklyProjectionBucket(
            week_index=1,
            week_start_date=date(2026, 11, 2),
            opening_inventory=10000.0,
            planned_receipts=2000.0,
            planned_production=3000.0,
            forecast_demand=4000.0,
            net_change=1000.0,
            projected_ending_inventory=11000.0,
            physical_ending_inventory=11000.0,
            safety_stock=4000.0,
            projected_shortage=0.0,
            unmet_demand=0.0,
            is_stockout=False,
            is_safety_stock_breach=False,
            weeks_of_supply=2.75,
            days_of_supply=19.25
        ),
        WeeklyProjectionBucket(
            week_index=2,
            week_start_date=date(2026, 11, 9),
            opening_inventory=11000.0,
            planned_receipts=0.0,
            planned_production=0.0,
            forecast_demand=5000.0,
            net_change=-5000.0,
            projected_ending_inventory=6000.0,
            physical_ending_inventory=6000.0,
            safety_stock=4000.0,
            projected_shortage=0.0,
            unmet_demand=0.0,
            is_stockout=False,
            is_safety_stock_breach=False,
            weeks_of_supply=1.2,
            days_of_supply=8.4
        ),
        WeeklyProjectionBucket(
            week_index=3,
            week_start_date=date(2026, 11, 16),
            opening_inventory=6000.0,
            planned_receipts=0.0,
            planned_production=0.0,
            forecast_demand=4000.0,
            net_change=-4000.0,
            projected_ending_inventory=2000.0,
            physical_ending_inventory=2000.0,
            safety_stock=4000.0,
            projected_shortage=0.0,
            unmet_demand=0.0,
            is_stockout=False,
            is_safety_stock_breach=True,  # Safety stock breach!
            weeks_of_supply=0.5,
            days_of_supply=3.5
        ),
        WeeklyProjectionBucket(
            week_index=4,
            week_start_date=date(2026, 11, 23),
            opening_inventory=2000.0,
            planned_receipts=5000.0,
            planned_production=0.0,
            forecast_demand=3000.0,
            net_change=2000.0,
            projected_ending_inventory=4000.0,
            physical_ending_inventory=4000.0,
            safety_stock=4000.0,
            projected_shortage=0.0,
            unmet_demand=0.0,
            is_stockout=False,
            is_safety_stock_breach=False,
            weeks_of_supply=1.33,
            days_of_supply=9.33
        )
    ]

    return ProjectionTrajectorySummary(
        item_id="SKU-AUG-500-T10",
        location_id="LOC-DC-01",
        scenario_id="SCN-TEST",
        horizon_weeks=4,
        as_of_date=date(2026, 11, 2),
        initial_opening_inventory=10000.0,
        total_planned_receipts=7000.0,
        total_planned_production=3000.0,
        total_forecast_demand=16000.0,
        net_total_change=-6000.0,
        final_projected_inventory=4000.0,
        minimum_projected_inventory=2000.0,
        maximum_projected_inventory=11000.0,
        safety_stock=4000.0,
        stockout_weeks_count=0,
        safety_stock_breach_weeks_count=1,
        first_stockout_week_date=None,
        first_stockout_week_index=None,
        first_safety_stock_breach_date=date(2026, 11, 16),
        first_safety_stock_breach_index=3,
        total_projected_shortage=0.0,
        runway_days_to_stockout=None,
        runway_days_to_breach=14.0,
        weekly_buckets=buckets
    )


# =============================================================================
# 1. INVENTORY BALANCE TESTS
# =============================================================================

def test_inventory_balance_discrete_conservation():
    """Proves exact mathematical conservation: Closing = Opening + Inflows - Outflows."""
    is_conserved, drift, drift_pct = reconcile_inventory_balance_equation(
        opening=10000.0,
        inflows=[2500.0, 1500.0],
        outflows=[4000.0],
        closing=10000.0
    )
    assert is_conserved is True
    assert drift == 0.0
    assert drift_pct == 0.0


def test_inventory_balance_unexplained_drift_detection():
    """Detects artificial phantom inventory drift (e.g., 50 units unaccounted for)."""
    is_conserved, drift, drift_pct = reconcile_inventory_balance_equation(
        opening=10000.0,
        inflows=[2000.0],
        outflows=[3000.0],
        closing=8950.0  # Should be 9000.0 -> Drift = 50.0
    )
    assert is_conserved is False
    assert drift == 50.0
    assert round(drift_pct, 4) > 0.0


def test_projection_trajectory_stepwise_and_horizon_conservation(mock_projection_summary):
    """Audits 4-week trajectory and verifies 0.00% drift on both step-by-step and full horizon levels."""
    findings = audit_inventory_projection_trajectory(mock_projection_summary)
    assert len(findings) == 5  # 1 full horizon + 4 weekly buckets
    for f in findings:
        assert f.is_conserved is True
        assert f.status == AuditStatus.CONSERVED
        assert f.drift == 0.0
        assert f.drift_pct == 0.0


# =============================================================================
# 2. INTER-ECHELON LOGISTICS & SHIPMENT TESTS
# =============================================================================

def test_inter_echelon_shipment_conservation():
    """Audits delivered and manifested shipments, verifying mass-balance conservation."""
    shipments = [
        FactShipment(
            shipment_id="SHIP-TEST-001",
            origin_location_id="LOC-PLANT-01",
            destination_location_id="LOC-DC-01",
            finished_sku_id="SKU-AUG-500-T10",
            lot_id="LOT-01",
            dispatch_date=date(2026, 10, 20),
            expected_arrival_date=date(2026, 10, 22),
            actual_arrival_date=date(2026, 10, 22),
            shipped_quantity=8000.0,
            received_quantity=8000.0,
            transport_mode="Road",
            shipment_status="Delivered"
        ),
        FactShipment(
            shipment_id="SHIP-TEST-002",
            origin_location_id="LOC-DC-01",
            destination_location_id="LOC-MKT-HYD",
            finished_sku_id="SKU-AUG-500-T10",
            lot_id="LOT-01",
            dispatch_date=date(2026, 10, 25),
            expected_arrival_date=date(2026, 10, 27),
            actual_arrival_date=None,
            shipped_quantity=4000.0,
            received_quantity=0.0,
            transport_mode="Road",
            shipment_status="In-Transit"
        )
    ]

    findings = audit_inter_echelon_shipments(shipments)
    assert len(findings) == 2
    for f in findings:
        assert f.is_conserved is True
        assert f.drift == 0.0


def test_inter_echelon_shipment_quantity_leakage_detection():
    """Detects shipment where delivered volume is less than shipped volume without explanation."""
    leak_shipment = [
        FactShipment(
            shipment_id="SHIP-LEAK-001",
            origin_location_id="LOC-PLANT-01",
            destination_location_id="LOC-DC-01",
            finished_sku_id="SKU-AUG-500-T10",
            lot_id="LOT-01",
            dispatch_date=date(2026, 10, 20),
            expected_arrival_date=date(2026, 10, 22),
            actual_arrival_date=date(2026, 10, 22),
            shipped_quantity=10000.0,
            received_quantity=9500.0,  # 500 units lost/unexplained!
            transport_mode="Road",
            shipment_status="Delivered"
        )
    ]
    findings = audit_inter_echelon_shipments(leak_shipment)
    assert len(findings) == 1
    assert findings[0].is_conserved is False
    assert findings[0].drift == 500.0
    assert findings[0].status == AuditStatus.DISCREPANCY_DETECTED


# =============================================================================
# 3. BOM & CHEMICAL MASS-BALANCE TESTS
# =============================================================================

def test_bom_explosion_mass_balance_and_scrap_verification():
    """Audits planned production order vs BOM explosion, validating formula: Gross = Base + Scrap."""
    po = FactProductionOrder(
        production_order_id="PROD-TEST-001",
        finished_sku_id="SKU-AUG-500-T10",
        location_id="LOC-PLANT-01",
        production_line_id="LINE-PLANT1-01",
        planned_start_date=date(2026, 11, 2),
        planned_completion_date=date(2026, 11, 6),
        planned_quantity=10000.0,
        actual_quantity=0.0,
        expected_yield=98.5,
        planned_hours=40.0,
        production_status="Planned"
    )
    boms = [
        BridgeBillOfMaterial(
            bom_id="BOM-T10-API",
            finished_sku_id="SKU-AUG-500-T10",
            material_sku_id="MAT-API-001",
            quantity_per_finished_unit=0.00625,  # 62.5 kg base
            scrap_factor_pct=2.0,                # 2% scrap -> +1.25 kg -> 63.75 kg gross
            effective_start_date=date(2023, 1, 1),
            bom_version="V1"
        )
    ]

    findings = audit_bom_explosion_mass_balance([po], boms)
    assert len(findings) == 1
    f = findings[0]
    assert f.is_conserved is True
    assert f.actual_closing == 63.75
    assert f.drift == 0.0


# =============================================================================
# 4. FEFO ALLOCATION TESTS
# =============================================================================

def test_fefo_allocation_conservation_and_depletion():
    """Audits order fulfillment conservation: Requested == Fulfilled + Unmet."""
    lots = [
        FactInventoryLot(
            lot_id="LOT-EARLY-01",
            item_type="FINISHED_SKU",
            item_id="SKU-AUG-500-T10",
            location_id="LOC-DC-01",
            quantity_on_hand=2000.0,
            reserved_quantity=0.0,
            blocked_quantity=0.0,
            manufacture_date=date(2026, 1, 1),
            expiry_date=date(2027, 6, 1),   # Expires first
            receipt_date=date(2026, 1, 10),
            quality_status="Released"
        ),
        FactInventoryLot(
            lot_id="LOT-LATE-02",
            item_type="FINISHED_SKU",
            item_id="SKU-AUG-500-T10",
            location_id="LOC-DC-01",
            quantity_on_hand=3000.0,
            reserved_quantity=0.0,
            blocked_quantity=0.0,
            manufacture_date=date(2026, 3, 1),
            expiry_date=date(2028, 1, 1),   # Expires later
            receipt_date=date(2026, 3, 10),
            quality_status="Released"
        )
    ]

    summary, _ = allocate_fefo(
        lots=lots,
        demand_quantity=3500.0,
        as_of_date=date(2026, 10, 26),
        min_acceptable_rsl_days=180
    )

    findings = audit_fefo_allocation_conservation(summary, lots, as_of_date=date(2026, 10, 26))
    for f in findings:
        assert f.is_conserved is True
        assert f.drift == 0.0

    # Ensure earliest lot was depleted first
    assert summary.fulfilled_quantity == 3500.0
    assert summary.unmet_quantity == 0.0
    assert len(summary.allocations) == 2
    assert summary.allocations[0].lot_id == "LOT-EARLY-01"
    assert summary.allocations[0].allocated_quantity == 2000.0  # Fully exhausted
    assert summary.allocations[1].lot_id == "LOT-LATE-02"
    assert summary.allocations[1].allocated_quantity == 1500.0  # Partially drawn


def test_fefo_allocation_quarantine_exclusion():
    """Validates that quarantined inventory is never allocated to commercial demand."""
    quarantine_lot = FactInventoryLot(
        lot_id="LOT-QUAR-01",
        item_type="FINISHED_SKU",
        item_id="SKU-AUG-500-T10",
        location_id="LOC-DC-01",
        quantity_on_hand=5000.0,
        reserved_quantity=0.0,
        blocked_quantity=0.0,
        manufacture_date=date(2026, 1, 1),
        expiry_date=date(2027, 6, 1),
        receipt_date=date(2026, 1, 10),
        quality_status="Quarantine"  # Quarantined!
    )

    summary, _ = allocate_fefo(
        lots=[quarantine_lot],
        demand_quantity=1000.0,
        as_of_date=date(2026, 10, 26),
        min_acceptable_rsl_days=180
    )

    assert summary.fulfilled_quantity == 0.0
    assert summary.unmet_quantity == 1000.0
    assert len(summary.allocations) == 0


# =============================================================================
# 5. PROCUREMENT & PO TESTS
# =============================================================================

def test_procurement_po_receipt_and_otif_consistency():
    """Audits purchase order receipts and verifies OTIF logical consistency."""
    pos = [
        FactPurchaseOrder(
            purchase_order_id="PO-TEST-001",
            supplier_id="SUP-001",
            material_sku_id="MAT-API-001",
            order_date=date(2026, 9, 1),
            requested_delivery_date=date(2026, 10, 1),
            confirmed_delivery_date=date(2026, 10, 1),
            actual_receipt_date=date(2026, 10, 1),
            ordered_quantity=100.0,
            received_quantity=100.0,
            purchase_order_status="Received"
        ),
        FactPurchaseOrder(
            purchase_order_id="PO-TEST-002",
            supplier_id="SUP-001",
            material_sku_id="MAT-API-001",
            order_date=date(2026, 9, 15),
            requested_delivery_date=date(2026, 10, 15),
            confirmed_delivery_date=date(2026, 10, 15),
            actual_receipt_date=date(2026, 10, 25),  # 10 days late!
            ordered_quantity=100.0,
            received_quantity=80.0,                  # Short by 20!
            purchase_order_status="Received"
        )
    ]

    findings = audit_procurement_po_receipts(pos)
    assert len(findings) == 2
    for f in findings:
        assert f.is_conserved is True

    # PO 1 should be OTIF=True
    assert findings[0].metadata["is_otif"] is True
    # PO 2 should be OTIF=False
    assert findings[1].metadata["is_otif"] is False
    assert findings[1].metadata["delay_days"] == 10


# =============================================================================
# 6. PLANT LINE CAPACITY TESTS
# =============================================================================

def test_line_capacity_operating_hours_conservation():
    """Audits manufacturing line operating hours: Net Available == Committed + Idle - Overload."""
    cap_records = [
        FactCapacity(
            capacity_record_id="CAP-TEST-01",
            location_id="LOC-PLANT-01",
            production_line_id="LINE-PLANT1-01",
            period_start_date=date(2026, 11, 2),
            net_available_hours=120.0,
            maintenance_hours=8.0,
            downtime_hours=0.0,
            committed_hours=100.0,
            scenario_id="SCN-BASE"
        ),
        FactCapacity(
            capacity_record_id="CAP-TEST-02",
            location_id="LOC-PLANT-01",
            production_line_id="LINE-PLANT1-01",
            period_start_date=date(2026, 11, 9),
            net_available_hours=120.0,
            maintenance_hours=8.0,
            downtime_hours=0.0,
            committed_hours=130.0,  # 10 hours overload!
            scenario_id="SCN-BASE"
        )
    ]

    findings = audit_line_capacity_conservation(cap_records)
    assert len(findings) == 2
    for f in findings:
        assert f.is_conserved is True
        assert f.drift == 0.0

    # Test 1 should have 20 idle hours
    assert findings[0].metadata["idle_hours"] == 20.0
    assert findings[0].metadata["overload_hours"] == 0.0
    # Test 2 should have 10 overload hours
    assert findings[1].metadata["idle_hours"] == 0.0
    assert findings[1].metadata["overload_hours"] == 10.0


# =============================================================================
# 7. FULL DATABASE NETWORK RECONCILIATION TESTS
# =============================================================================

def test_full_network_database_reconciliation(db_path):
    """
    Executes master network reconciliation against the full 30-table SQLite production database.
    Asserts 100.0% conservation rate, zero unexplained network drift, and all domains passing.
    """
    report = run_full_network_reconciliation(db_path, scenario_id="SCN-BASE")

    assert report.passed is True
    assert report.total_items_evaluated == 122
    assert report.total_items_conserved == 122
    assert report.total_items_discrepant == 0
    assert report.overall_conservation_rate_pct == 100.0
    assert report.max_network_drift == 0.0
    assert report.total_categories_evaluated == 6

    # Verify each domain category passed
    assert report.category_summaries["INVENTORY_BALANCE"].passed is True
    assert report.category_summaries["INTER_ECHELON_HANDOFF"].passed is True
    assert report.category_summaries["BOM_MASS_BALANCE"].passed is True
    assert report.category_summaries["FEFO_ALLOCATION"].passed is True
    assert report.category_summaries["PROCUREMENT_RECEIPTS"].passed is True
    assert report.category_summaries["CAPACITY_UTILIZATION"].passed is True


def test_reconciliation_report_dataframe_and_markdown_export(db_path):
    """Validates that ReconciliationReport converts cleanly to DataFrame and Markdown formats."""
    report = run_full_network_reconciliation(db_path, scenario_id="SCN-BASE")

    # DataFrame serialization check
    df = report.to_dataframe()
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 122
    assert "audit_code" in df.columns
    assert "drift" in df.columns
    assert "is_conserved" in df.columns
    assert (df["is_conserved"] == True).all()

    # Markdown export check
    md = report.generate_markdown_report()
    assert "# Executive Mathematical Reconciliation Report" in md
    assert "**Overall Conservation Rate:** `100.00%`" in md
    assert "✅ PASSED (100% Conserved)" in md
