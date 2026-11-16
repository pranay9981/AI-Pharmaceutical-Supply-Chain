"""
Unit Test Suite for Pharmaceutical BOM Explosion & MRP Netting Engine.
Phase 2 (Day 17) Core Analytics Validation.

Validates Bill of Materials gross requirement calculations with scrap factors,
multi-factor raw material eligibility (excluding quarantined stock),
supplier PO delivery timing, and Scenario A API shortage detection.
"""

import sqlite3
from datetime import date, timedelta
import pytest
import pandas as pd

from src.models.planning import FactMaterialRequirement
from src.models.bridges import BridgeBillOfMaterial
from src.models.manufacturing_quality import FactProductionOrder
from src.models.procurement_inventory import FactInventoryLot, FactPurchaseOrder
from src.engine.mrp import (
    calculate_bom_gross_requirement,
    explode_bom_for_order,
    net_material_requirement,
    run_mrp_for_production_schedule,
    detect_shared_material_conflicts,
    generate_mrp_from_database,
    export_mrp_to_dataframe,
    ComponentGrossRequirement,
    MaterialNettingResult,
    MRPSummary
)

DB_PATH = "data/processed/control_tower.db"


@pytest.fixture
def base_as_of_date():
    return date(2026, 10, 26)


@pytest.fixture
def sample_bom():
    """Standardized BOM formula for Augmentin 500mg T10 strips."""
    return [
        BridgeBillOfMaterial(
            bom_id="BOM-T10-API", finished_sku_id="SKU-AUG-500-T10", material_sku_id="MAT-API-001",
            quantity_per_finished_unit=0.00625, scrap_factor_pct=2.0, effective_start_date=date(2023, 1, 1), bom_version="V1"
        ),
        BridgeBillOfMaterial(
            bom_id="BOM-T10-EXC", finished_sku_id="SKU-AUG-500-T10", material_sku_id="MAT-EXC-001",
            quantity_per_finished_unit=0.002, scrap_factor_pct=1.5, effective_start_date=date(2023, 1, 1), bom_version="V1"
        ),
        BridgeBillOfMaterial(
            bom_id="BOM-T10-BLIST", finished_sku_id="SKU-AUG-500-T10", material_sku_id="MAT-PKG-BLIST",
            quantity_per_finished_unit=1.0, scrap_factor_pct=1.0, effective_start_date=date(2023, 1, 1), bom_version="V1"
        ),
        BridgeBillOfMaterial(
            bom_id="BOM-T10-CART", finished_sku_id="SKU-AUG-500-T10", material_sku_id="MAT-PKG-CART",
            quantity_per_finished_unit=1.0, scrap_factor_pct=1.0, effective_start_date=date(2023, 1, 1), bom_version="V1"
        )
    ]


# =============================================================================
# 1. BOM EXPLOSION MATHEMATICS TESTS
# =============================================================================

def test_bom_gross_requirement_scrap_calculation():
    """
    Verifies mathematical precision of pharmaceutical scrap explosion:
    Gross = Units * QuantityPerUnit * (1 + ScrapPct / 100).
    """
    # 20,000 packs of T10 with 0.00625 kg API per pack and 2.0% scrap allowance
    # Base = 20,000 * 0.00625 = 125.0 kg
    # Scrap = 125.0 * 0.02 = 2.5 kg
    # Gross = 127.5 kg
    base, scrap, gross = calculate_bom_gross_requirement(20000.0, 0.00625, 2.0)
    assert base == 125.0
    assert scrap == 2.5
    assert gross == 127.5

    # Zero units edge case
    b0, s0, g0 = calculate_bom_gross_requirement(0.0, 0.00625, 2.0)
    assert b0 == 0.0 and s0 == 0.0 and g0 == 0.0


def test_explode_bom_for_production_order(sample_bom):
    """Verifies complete BOM explosion for a planned manufacturing order."""
    prod_order = FactProductionOrder(
        production_order_id="PROD-TEST-001",
        finished_sku_id="SKU-AUG-500-T10",
        location_id="LOC-PLANT-01",
        production_line_id="LINE-PLANT1-01",
        planned_start_date=date(2026, 11, 9),
        planned_completion_date=date(2026, 11, 13),
        planned_quantity=20000.0,
        expected_yield=98.5,
        planned_hours=40.0
    )

    reqs = explode_bom_for_order(prod_order, sample_bom)
    assert len(reqs) == 4

    by_mat = {r.material_sku_id: r for r in reqs}
    assert by_mat["MAT-API-001"].gross_quantity == 127.5
    assert by_mat["MAT-EXC-001"].gross_quantity == 40.6
    assert by_mat["MAT-PKG-BLIST"].gross_quantity == 20200.0
    assert by_mat["MAT-PKG-CART"].gross_quantity == 20200.0

    for r in reqs:
        assert r.need_by_date == date(2026, 11, 9)


# =============================================================================
# 2. MATERIAL NETTING & QUALITY STATUS FILTERING TESTS
# =============================================================================

def test_material_netting_quality_status_exclusion():
    """
    Verifies that Quarantined or Blocked raw material lots are strictly excluded
    from available stock during MRP netting, preventing premature batch charging.
    """
    req = ComponentGrossRequirement(
        production_order_id="PROD-001",
        finished_sku_id="SKU-AUG-500-T10",
        material_sku_id="MAT-API-001",
        need_by_date=date(2026, 11, 9),
        quantity_per_finished_unit=0.00625,
        scrap_factor_pct=2.0,
        base_quantity=125.0,
        scrap_quantity=2.5,
        gross_quantity=127.5
    )

    # Eligible: 80 kg released, 20 kg quarantined (testing in progress)
    # Expected: only 80 kg eligible, resulting in 47.5 kg shortage if no incoming PO
    net_res = net_material_requirement(
        gross_req=req,
        eligible_on_hand=80.0,
        quarantined_on_hand=20.0,
        expected_receipts=0.0
    )

    assert net_res.gross_requirement == 127.5
    assert net_res.eligible_available_quantity == 80.0
    assert net_res.quarantined_quantity == 20.0
    assert net_res.shortage_quantity == 47.5
    assert net_res.is_shortage is True


def test_material_netting_purchase_order_delivery_timing():
    """
    Verifies that PO receipts arriving on/before need_by_date are credited,
    while PO receipts arriving after need_by_date are disqualified.
    """
    req = ComponentGrossRequirement(
        production_order_id="PROD-001",
        finished_sku_id="SKU-AUG-500-T10",
        material_sku_id="MAT-API-001",
        need_by_date=date(2026, 11, 9),
        quantity_per_finished_unit=0.00625,
        scrap_factor_pct=2.0,
        base_quantity=125.0,
        scrap_quantity=2.5,
        gross_quantity=127.5
    )

    # 1. On-time PO receipt of 150 kg on Nov 05 (Prior to Nov 09 need date) -> COVERED
    res_ontime = net_material_requirement(
        gross_req=req,
        eligible_on_hand=80.0,
        expected_receipts=150.0,
        linked_po_ids=["PO-2026-001"]
    )
    assert res_ontime.shortage_quantity == 0.0
    assert res_ontime.is_shortage is False
    assert res_ontime.coverage_ratio > 1.0


# =============================================================================
# 3. MULTI-ORDER SEQUENTIAL ALLOCATION & SHARED MATERIAL CONFLICTS
# =============================================================================

def test_shared_material_contention_and_sequential_netting(sample_bom, base_as_of_date):
    """
    Verifies that multiple production orders competing for a shared material pool
    are depleted chronologically, accurately exposing shortages for later orders.
    """
    # Order 1: Starts Nov 09, requires 127.5 kg API
    order1 = FactProductionOrder(
        production_order_id="PROD-001", finished_sku_id="SKU-AUG-500-T10", location_id="LOC-PLANT-01",
        production_line_id="LINE-PLANT1-01", planned_start_date=date(2026, 11, 9), planned_completion_date=date(2026, 11, 13),
        planned_quantity=20000.0, expected_yield=98.5, planned_hours=40.0
    )
    # Order 2: Starts Nov 16, requires 127.5 kg API
    order2 = FactProductionOrder(
        production_order_id="PROD-002", finished_sku_id="SKU-AUG-500-T10", location_id="LOC-PLANT-01",
        production_line_id="LINE-PLANT1-01", planned_start_date=date(2026, 11, 16), planned_completion_date=date(2026, 11, 20),
        planned_quantity=20000.0, expected_yield=98.5, planned_hours=30.0
    )

    # Stock pool: 200 kg API on-hand (Enough for Order 1 alone, but insufficient for Order 1 + Order 2 = 255 kg)
    # Plus ample excipients and packaging so that only API is the constraining bottle-neck
    lots = [
        FactInventoryLot(
            lot_id="LOT-API-POOL", item_type="RAW_MATERIAL", item_id="MAT-API-001", location_id="LOC-PLANT-01",
            manufacture_date=date(2026, 1, 1), expiry_date=date(2028, 1, 1), quantity_on_hand=200.0,
            reserved_quantity=0.0, blocked_quantity=0.0, quality_status="Released", receipt_date=date(2026, 1, 10),
            recall_status="None"
        ),
        FactInventoryLot(
            lot_id="LOT-EXC-POOL", item_type="RAW_MATERIAL", item_id="MAT-EXC-001", location_id="LOC-PLANT-01",
            manufacture_date=date(2026, 1, 1), expiry_date=date(2028, 1, 1), quantity_on_hand=500.0,
            reserved_quantity=0.0, blocked_quantity=0.0, quality_status="Released", receipt_date=date(2026, 1, 10),
            recall_status="None"
        ),
        FactInventoryLot(
            lot_id="LOT-BLIST-POOL", item_type="RAW_MATERIAL", item_id="MAT-PKG-BLIST", location_id="LOC-PLANT-01",
            manufacture_date=date(2026, 1, 1), expiry_date=date(2028, 1, 1), quantity_on_hand=100000.0,
            reserved_quantity=0.0, blocked_quantity=0.0, quality_status="Released", receipt_date=date(2026, 1, 10),
            recall_status="None"
        ),
        FactInventoryLot(
            lot_id="LOT-CART-POOL", item_type="RAW_MATERIAL", item_id="MAT-PKG-CART", location_id="LOC-PLANT-01",
            manufacture_date=date(2026, 1, 1), expiry_date=date(2028, 1, 1), quantity_on_hand=100000.0,
            reserved_quantity=0.0, blocked_quantity=0.0, quality_status="Released", receipt_date=date(2026, 1, 10),
            recall_status="None"
        )
    ]

    summary = run_mrp_for_production_schedule(
        production_orders=[order1, order2],
        bom_records=sample_bom,
        inventory_lots=lots,
        purchase_orders=[],
        as_of_date=base_as_of_date
    )

    # Order 1 consumes 127.5 kg from the 200 kg pool -> 0 shortage, Order 1 is READY
    res_o1 = next(r for r in summary.netting_results if r.production_order_id == "PROD-001" and r.material_sku_id == "MAT-API-001")
    assert res_o1.eligible_available_quantity == 127.5
    assert res_o1.shortage_quantity == 0.0
    assert summary.order_readiness["PROD-001"] is True

    # Order 2 gets residual (200 - 127.5 = 72.5 kg), needs 127.5 kg -> Shortage of 55.0 kg!
    res_o2 = next(r for r in summary.netting_results if r.production_order_id == "PROD-002" and r.material_sku_id == "MAT-API-001")
    assert res_o2.eligible_available_quantity == 72.5
    assert res_o2.shortage_quantity == 55.0
    assert summary.order_readiness["PROD-002"] is False


# =============================================================================
# 4. REAL DATABASE INTEGRATION & SCENARIO A DISRUPTION TESTS
# =============================================================================

def test_database_integrated_mrp_baseline(base_as_of_date):
    """
    Executes MRP pipeline against real SQLite control_tower.db in Baseline:
    PROD-2026-001 (T10, 20k packs) is 100% covered by API on-hand (80kg) + PO-2026-001 receipt (150kg).
    PROD-2026-002 (T30, 10k packs) exposes an 88.75 kg API deficit because both orders compete for the same API pool.
    """
    conn = sqlite3.connect(DB_PATH)
    summary, pydantic_reqs = generate_mrp_from_database(
        db_conn=conn,
        scenario_id="SCN-BASE",
        as_of_date=base_as_of_date
    )
    conn.close()

    assert summary.production_orders_evaluated == 2
    assert summary.components_exploded_count == 8  # 4 for T10 + 4 for T30

    # PROD-2026-001 is fully covered in Baseline!
    assert summary.order_readiness["PROD-2026-001"] is True
    reqs_p1 = [r for r in summary.netting_results if r.production_order_id == "PROD-2026-001"]
    for r in reqs_p1:
        assert r.shortage_quantity == 0.0

    # PROD-2026-002 starts Nov 16: consumes remaining API (102.5kg) but needs 191.25kg -> 88.75kg shortage
    assert summary.order_readiness["PROD-2026-002"] is False
    assert summary.shortages_by_material["MAT-API-001"] == 88.75

    # Verify all 8 Pydantic instances valid
    assert len(pydantic_reqs) == 8
    for r in pydantic_reqs:
        assert isinstance(r, FactMaterialRequirement)


def test_database_integrated_mrp_scenario_a_disruption(base_as_of_date):
    """
    Executes MRP pipeline against real SQLite control_tower.db in Scenario A (Delayed API Supplier):
    PO-2026-001 is delayed 14 days, arriving after Nov 09 need-by date.
    Results in exact 47.5 kg API deficit, blocking PROD-2026-001!
    """
    conn = sqlite3.connect(DB_PATH)
    summary, pydantic_reqs = generate_mrp_from_database(
        db_conn=conn,
        scenario_id="SCN-A-API-DELAY",
        as_of_date=base_as_of_date
    )
    conn.close()

    assert summary.has_critical_shortage is True
    assert summary.order_readiness["PROD-2026-001"] is False  # Cannot release batch

    # Check API requirement specifically
    api_req = next(r for r in summary.netting_results if r.production_order_id == "PROD-2026-001" and r.material_sku_id == "MAT-API-001")
    assert api_req.gross_requirement == 127.5
    assert api_req.eligible_available_quantity == 80.0
    assert api_req.expected_receipt_quantity == 0.0  # PO arrived late!
    assert api_req.shortage_quantity == 47.5
    assert api_req.is_shortage is True


def test_export_mrp_to_dataframe(base_as_of_date):
    """Verifies that MRP results export cleanly to a Pandas DataFrame matching relational schema."""
    conn = sqlite3.connect(DB_PATH)
    _, pydantic_reqs = generate_mrp_from_database(db_conn=conn, as_of_date=base_as_of_date)
    conn.close()

    df = export_mrp_to_dataframe(pydantic_reqs)
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 8
    expected_cols = [
        "requirement_id", "production_order_id", "material_sku_id",
        "required_quantity", "required_date", "eligible_available_quantity",
        "expected_receipt_quantity", "shortage_quantity", "scenario_id"
    ]
    for c in expected_cols:
        assert c in df.columns
