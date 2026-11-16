"""
Unit Test Suite for Pharmaceutical Multi-Echelon Inventory & FEFO Engine.
Phase 2 (Day 15) Core Analytics Validation.

Validates multi-factor eligibility filtering, strict FEFO allocation ordering,
mathematical conservation (zero drift/unexplained losses), and real SQLite database integration.
"""

import sqlite3
from datetime import date
import pytest

from src.models.procurement_inventory import FactInventoryLot
from src.engine.inventory import (
    calculate_rsl,
    calculate_available_quantity,
    evaluate_lot_eligibility,
    filter_and_sort_fefo,
    allocate_fefo,
    detect_expiry_exposures,
    evaluate_inventory_posture,
    load_lots_from_database,
    load_sku_market_rules_from_database,
    LotEligibilityResult,
    AllocationSummary
)

DB_PATH = "data/processed/control_tower.db"


@pytest.fixture
def base_as_of_date():
    """Cutoff planning date matching Phase 1 baseline (26-Oct-2026)."""
    return date(2026, 10, 26)


@pytest.fixture
def sample_lots():
    """Standardized batch of synthetic lots representing diverse operational states."""
    return [
        # Lot 1: Healthy released stock, expiring in 2 years
        FactInventoryLot(
            lot_id="LOT-TEST-01-HEALTHY",
            item_type="FINISHED_SKU",
            item_id="SKU-AUG-500-T10",
            location_id="LOC-DC-01",
            manufacture_date=date(2026, 8, 1),
            expiry_date=date(2028, 8, 1),
            quantity_on_hand=10000.0,
            reserved_quantity=1000.0,
            blocked_quantity=0.0,
            quality_status="Released",
            receipt_date=date(2026, 8, 10),
            release_date=date(2026, 8, 12),
            recall_status="None",
            synthetic_data_flag=True
        ),
        # Lot 2: Quarantined stock (sterility hold / QC testing)
        FactInventoryLot(
            lot_id="LOT-TEST-02-QUAR",
            item_type="FINISHED_SKU",
            item_id="SKU-AUG-500-T10",
            location_id="LOC-DC-01",
            manufacture_date=date(2026, 9, 1),
            expiry_date=date(2028, 9, 1),
            quantity_on_hand=5000.0,
            reserved_quantity=0.0,
            blocked_quantity=0.0,
            quality_status="Quarantined",
            receipt_date=date(2026, 9, 10),
            release_date=None,
            recall_status="None",
            synthetic_data_flag=True
        ),
        # Lot 3: Blocked stock (cold chain temperature deviation)
        FactInventoryLot(
            lot_id="LOT-TEST-03-BLOCKED",
            item_type="FINISHED_SKU",
            item_id="SKU-AUG-500-T10",
            location_id="LOC-DC-01",
            manufacture_date=date(2026, 7, 1),
            expiry_date=date(2028, 7, 1),
            quantity_on_hand=4000.0,
            reserved_quantity=0.0,
            blocked_quantity=4000.0,
            quality_status="Blocked",
            receipt_date=date(2026, 7, 10),
            release_date=None,
            recall_status="None",
            synthetic_data_flag=True
        ),
        # Lot 4: Approaching expiry (RSL = 25 days, fails 90-day MARSL)
        FactInventoryLot(
            lot_id="LOT-TEST-04-NEAR-EXP",
            item_type="FINISHED_SKU",
            item_id="SKU-AUG-500-T10",
            location_id="LOC-DC-01",
            manufacture_date=date(2024, 11, 20),
            expiry_date=date(2026, 11, 20),
            quantity_on_hand=3000.0,
            reserved_quantity=0.0,
            blocked_quantity=0.0,
            quality_status="Released",
            receipt_date=date(2024, 12, 1),
            release_date=date(2024, 12, 3),
            recall_status="None",
            synthetic_data_flag=True
        ),
        # Lot 5: Hard expired lot
        FactInventoryLot(
            lot_id="LOT-TEST-05-EXPIRED",
            item_type="FINISHED_SKU",
            item_id="SKU-AUG-500-T10",
            location_id="LOC-DC-01",
            manufacture_date=date(2024, 1, 1),
            expiry_date=date(2026, 1, 1),
            quantity_on_hand=1500.0,
            reserved_quantity=0.0,
            blocked_quantity=0.0,
            quality_status="Expired",
            receipt_date=date(2024, 1, 15),
            release_date=date(2024, 1, 18),
            recall_status="None",
            synthetic_data_flag=True
        ),
        # Lot 6: Regulatory recall lot
        FactInventoryLot(
            lot_id="LOT-TEST-06-RECALL",
            item_type="FINISHED_SKU",
            item_id="SKU-AUG-500-T10",
            location_id="LOC-DC-01",
            manufacture_date=date(2026, 6, 1),
            expiry_date=date(2028, 6, 1),
            quantity_on_hand=2000.0,
            reserved_quantity=0.0,
            blocked_quantity=0.0,
            quality_status="Released",
            receipt_date=date(2026, 6, 10),
            release_date=date(2026, 6, 12),
            recall_status="Class-II",
            synthetic_data_flag=True
        )
    ]


# =============================================================================
# 1. LOT ELIGIBILITY FILTER TESTS
# =============================================================================

def test_healthy_lot_eligibility(base_as_of_date, sample_lots):
    """Verifies that fully released stock with valid shelf life passes eligibility."""
    healthy_lot = sample_lots[0]
    result = evaluate_lot_eligibility(healthy_lot, as_of_date=base_as_of_date, min_acceptable_rsl_days=90)
    assert result.is_eligible is True
    assert result.available_quantity == 9000.0  # 10,000 on hand - 1,000 reserved
    assert result.remaining_shelf_life_days > 600
    assert len(result.disqualification_reasons) == 0


def test_quality_status_rejection(base_as_of_date, sample_lots):
    """Verifies that non-Released lots (Quarantined, Blocked, Expired) are disqualified."""
    # Quarantined
    quar_lot = sample_lots[1]
    res_q = evaluate_lot_eligibility(quar_lot, as_of_date=base_as_of_date)
    assert res_q.is_eligible is False
    assert any("Ineligible quality status: 'Quarantined'" in r for r in res_q.disqualification_reasons)

    # Blocked
    blk_lot = sample_lots[2]
    res_b = evaluate_lot_eligibility(blk_lot, as_of_date=base_as_of_date)
    assert res_b.is_eligible is False
    assert any("Ineligible quality status: 'Blocked'" in r for r in res_b.disqualification_reasons)

    # Expired
    exp_lot = sample_lots[4]
    res_e = evaluate_lot_eligibility(exp_lot, as_of_date=base_as_of_date)
    assert res_e.is_eligible is False
    assert any("Lot expired" in r for r in res_e.disqualification_reasons)


def test_regulatory_recall_rejection(base_as_of_date, sample_lots):
    """Verifies that lots under regulatory recall are immediately disqualified."""
    recall_lot = sample_lots[5]
    res = evaluate_lot_eligibility(recall_lot, as_of_date=base_as_of_date)
    assert res.is_eligible is False
    assert any("Active regulatory embargo: recall_status='Class-II'" in r for r in res.disqualification_reasons)


def test_marsl_market_threshold_filtering(base_as_of_date, sample_lots):
    """
    Verifies that lots with valid quality but insufficient remaining shelf life
    fail market MARSL checks (Scenario D).
    """
    near_exp_lot = sample_lots[3]  # Expiry: 20-Nov-2026, As-Of: 26-Oct-2026 -> RSL = 25 days

    # Market A: Requires 90 days MARSL (Pune tender) -> MUST FAIL
    res_pune = evaluate_lot_eligibility(
        near_exp_lot,
        as_of_date=base_as_of_date,
        min_acceptable_rsl_days=90,
        target_market_id="MKT-IN-PUN"
    )
    assert res_pune.is_eligible is False
    assert res_pune.remaining_shelf_life_days == 25
    assert any("Insufficient shelf life for market 'MKT-IN-PUN'" in r for r in res_pune.disqualification_reasons)

    # Immediate consumption scenario: MARSL threshold = 15 days -> MUST PASS
    res_emergency = evaluate_lot_eligibility(
        near_exp_lot,
        as_of_date=base_as_of_date,
        min_acceptable_rsl_days=15
    )
    assert res_emergency.is_eligible is True


# =============================================================================
# 2. FEFO SORTING & ALLOCATION TESTS
# =============================================================================

def test_fefo_sorting_chronological_order(base_as_of_date):
    """Verifies that eligible lots are ordered strictly by earliest expiry date."""
    lot_a = FactInventoryLot(
        lot_id="LOT-EXP-2027-MAR", item_type="FINISHED_SKU", item_id="SKU-AUG-500-T10",
        location_id="LOC-DC-01", manufacture_date=date(2025, 3, 1), expiry_date=date(2027, 3, 1),
        quantity_on_hand=5000.0, reserved_quantity=0.0, blocked_quantity=0.0, quality_status="Released",
        receipt_date=date(2025, 3, 15), release_date=date(2025, 3, 17), recall_status="None"
    )
    lot_b = FactInventoryLot(
        lot_id="LOT-EXP-2028-JAN", item_type="FINISHED_SKU", item_id="SKU-AUG-500-T10",
        location_id="LOC-DC-01", manufacture_date=date(2026, 1, 1), expiry_date=date(2028, 1, 1),
        quantity_on_hand=8000.0, reserved_quantity=0.0, blocked_quantity=0.0, quality_status="Released",
        receipt_date=date(2026, 1, 15), release_date=date(2026, 1, 17), recall_status="None"
    )
    lot_c = FactInventoryLot(
        lot_id="LOT-EXP-2027-AUG", item_type="FINISHED_SKU", item_id="SKU-AUG-500-T10",
        location_id="LOC-DC-01", manufacture_date=date(2025, 8, 1), expiry_date=date(2027, 8, 1),
        quantity_on_hand=4000.0, reserved_quantity=0.0, blocked_quantity=0.0, quality_status="Released",
        receipt_date=date(2025, 8, 15), release_date=date(2025, 8, 17), recall_status="None"
    )

    # Shuffled input
    lots = [lot_b, lot_a, lot_c]
    sorted_lots = filter_and_sort_fefo(lots, as_of_date=base_as_of_date, min_acceptable_rsl_days=90)

    # Expected order: Mar-2027 -> Aug-2027 -> Jan-2028
    lot_ids = [pair[0].lot_id for pair in sorted_lots]
    assert lot_ids == ["LOT-EXP-2027-MAR", "LOT-EXP-2027-AUG", "LOT-EXP-2028-JAN"]


def test_fefo_allocation_depletion_and_conservation(base_as_of_date):
    """
    Verifies sequential depletion across lots and strict mathematical conservation:
    Requested Demand = Fulfilled Quantity + Unmet Quantity.
    """
    lot1 = FactInventoryLot(
        lot_id="LOT-1-EXP-2027", item_type="FINISHED_SKU", item_id="SKU-AUG-500-T10",
        location_id="LOC-DC-01", manufacture_date=date(2025, 4, 1), expiry_date=date(2027, 4, 1),
        quantity_on_hand=3000.0, reserved_quantity=0.0, blocked_quantity=0.0, quality_status="Released",
        receipt_date=date(2025, 4, 10), release_date=date(2025, 4, 12), recall_status="None"
    )
    lot2 = FactInventoryLot(
        lot_id="LOT-2-EXP-2028", item_type="FINISHED_SKU", item_id="SKU-AUG-500-T10",
        location_id="LOC-DC-01", manufacture_date=date(2026, 4, 1), expiry_date=date(2028, 4, 1),
        quantity_on_hand=5000.0, reserved_quantity=0.0, blocked_quantity=0.0, quality_status="Released",
        receipt_date=date(2026, 4, 10), release_date=date(2026, 4, 12), recall_status="None"
    )

    lots = [lot2, lot1]
    demand = 4500.0

    summary, updated_lots = allocate_fefo(lots, demand_quantity=demand, as_of_date=base_as_of_date, min_acceptable_rsl_days=90)

    # Conservation checks
    assert summary.requested_quantity == 4500.0
    assert summary.fulfilled_quantity == 4500.0
    assert summary.unmet_quantity == 0.0
    assert summary.is_fully_satisfied is True
    assert summary.fulfilled_quantity + summary.unmet_quantity == demand

    # Depletion breakdown: 3,000 from LOT-1 (100% depleted), 1,500 from LOT-2 (partial)
    assert len(summary.allocations) == 2
    assert summary.allocations[0].lot_id == "LOT-1-EXP-2027"
    assert summary.allocations[0].allocated_quantity == 3000.0
    assert summary.allocations[0].remaining_lot_available == 0.0

    assert summary.allocations[1].lot_id == "LOT-2-EXP-2028"
    assert summary.allocations[1].allocated_quantity == 1500.0
    assert summary.allocations[1].remaining_lot_available == 3500.0

    assert summary.depleted_lots_count == 1


def test_fefo_allocation_stockout_condition(base_as_of_date):
    """Verifies that excessive demand results in exact stockout tracking with 0 negative inventory."""
    lot = FactInventoryLot(
        lot_id="LOT-ONLY-1000", item_type="FINISHED_SKU", item_id="SKU-AUG-500-T10",
        location_id="LOC-DC-01", manufacture_date=date(2025, 4, 1), expiry_date=date(2027, 4, 1),
        quantity_on_hand=1000.0, reserved_quantity=200.0, blocked_quantity=0.0, quality_status="Released",
        receipt_date=date(2025, 4, 10), release_date=date(2025, 4, 12), recall_status="None"
    )

    # 800 available, request 2,500
    summary, updated_lots = allocate_fefo([lot], demand_quantity=2500.0, as_of_date=base_as_of_date)

    assert summary.fulfilled_quantity == 800.0
    assert summary.unmet_quantity == 1700.0
    assert summary.is_fully_satisfied is False
    assert summary.fulfilled_quantity + summary.unmet_quantity == 2500.0

    # Ensure no negative balances
    for l in updated_lots:
        assert l["quantity_on_hand"] >= 0.0
        assert l["reserved_quantity"] <= l["quantity_on_hand"]


# =============================================================================
# 3. EXPIRY EXPOSURE & INVENTORY POSTURE DIAGNOSTICS
# =============================================================================

def test_detect_expiry_exposures(base_as_of_date, sample_lots):
    """
    Verifies detection of at-risk lots facing impending MARSL expiration (Scenario D).
    """
    market_rules = {"SKU-AUG-500-T10": 90}
    exposures = detect_expiry_exposures(
        sample_lots,
        as_of_date=base_as_of_date,
        market_rules=market_rules,
        warning_horizon_days=60
    )

    # Expected: LOT-TEST-04-NEAR-EXP has RSL 25, MARSL 90 -> days_until_breach = -65 (CRITICAL)
    # Plus LOT-TEST-05-EXPIRED is already expired (CRITICAL)
    assert len(exposures) >= 1
    near_exp = next(x for x in exposures if x.lot_id == "LOT-TEST-04-NEAR-EXP")
    assert near_exp.risk_tier == "CRITICAL"
    assert near_exp.quantity_at_risk == 3000.0


def test_inventory_posture_aggregation(base_as_of_date, sample_lots):
    """Verifies complete multi-echelon stock posture aggregation."""
    posture = evaluate_inventory_posture(sample_lots, as_of_date=base_as_of_date)

    # Physical total: 10000 + 5000 + 4000 + 3000 + 1500 + 2000 = 25,500
    assert posture["total_physical_stock"] == 25500.0
    assert posture["total_reserved_stock"] == 1000.0
    assert posture["total_blocked_stock"] == 4000.0
    assert posture["total_expired_stock"] == 1500.0
    assert posture["total_lots_count"] == 6


# =============================================================================
# 4. REAL SQLITE DATABASE INTEGRATION TESTS
# =============================================================================

def test_real_database_fefo_allocation(base_as_of_date):
    """
    Loads verified Phase 1 inventory lots from SQLite (`control_tower.db`)
    and executes an end-to-end commercial FEFO allocation.
    """
    conn = sqlite3.connect(DB_PATH)
    lots = load_lots_from_database(conn, item_id="SKU-AUG-500-T10")
    market_rules = load_sku_market_rules_from_database(conn)
    conn.close()

    assert len(lots) == 2, f"Expected 2 lots for SKU-AUG-500-T10 in database, found {len(lots)}"
    lot_ids = {l.lot_id for l in lots}
    assert "LOT-FG-AUG-T10-26A" in lot_ids
    assert "LOT-FG-AUG-T10-24X" in lot_ids

    # 1. Test Hyderabad tender (MARSL = 180 days)
    # Near-expiry lot 24X (RSL = 25 days) MUST BE INELIGIBLE
    marsl_hyd = market_rules[("SKU-AUG-500-T10", "MKT-IN-HYD")]
    assert marsl_hyd == 180

    sorted_hyd = filter_and_sort_fefo(lots, as_of_date=base_as_of_date, min_acceptable_rsl_days=marsl_hyd)
    assert len(sorted_hyd) == 1, "Expected only 1 eligible lot for Hyderabad due to 180-day MARSL"
    assert sorted_hyd[0][0].lot_id == "LOT-FG-AUG-T10-26A"

    # 2. Test Allocation for 5,000 packs to Hyderabad
    summary, _ = allocate_fefo(
        lots,
        demand_quantity=5000.0,
        as_of_date=base_as_of_date,
        min_acceptable_rsl_days=marsl_hyd
    )
    assert summary.is_fully_satisfied is True
    assert summary.fulfilled_quantity == 5000.0
    assert len(summary.allocations) == 1
    assert summary.allocations[0].lot_id == "LOT-FG-AUG-T10-26A"
