"""
Pytest Unit Test Suite for FEFO Mathematical Rules & Eligibility Logic.
Verifies Day 03 Operating Principles and Mathematical Formulations.
"""

from datetime import date
import pytest
from src.engine.fefo_rules import (
    QualityStatus,
    InventoryLot,
    MarketShelfLifeRule,
    calculate_remaining_shelf_life,
    is_lot_eligible,
    filter_and_sort_fefo,
    allocate_fefo,
    calculate_expiry_exposure,
)


@pytest.fixture
def base_date():
    return date(2026, 11, 1)


@pytest.fixture
def hospital_market_rule():
    # Strict hospital tender rule: requires at least 90 days remaining shelf life
    return MarketShelfLifeRule(
        market_id="MKT-CHN-001",
        sku_id="SKU-AUG-625-T10",
        min_acceptable_rsl_days=90
    )


def test_remaining_shelf_life_calculation(base_date):
    expiry = date(2027, 5, 1)  # 181 days later
    rsl = calculate_remaining_shelf_life(expiry, base_date)
    assert rsl == 181


def test_lot_eligibility_quality_status_filtering(base_date, hospital_market_rule):
    # Released lot
    lot_released = InventoryLot(
        lot_id="LOT-001", sku_id="SKU-AUG-625-T10", location_id="LOC-WH-NAG",
        quantity=5000, mfg_date=date(2026, 8, 1), expiry_date=date(2028, 8, 1),
        quality_status=QualityStatus.RELEASED
    )
    is_ok, reason = is_lot_eligible(lot_released, hospital_market_rule, base_date)
    assert is_ok is True
    assert reason is None

    # Quarantined lot (e.g. pending QC assay)
    lot_quarantine = InventoryLot(
        lot_id="LOT-002", sku_id="SKU-AUG-625-T10", location_id="LOC-WH-NAG",
        quantity=5000, mfg_date=date(2026, 10, 1), expiry_date=date(2028, 10, 1),
        quality_status=QualityStatus.QUARANTINE
    )
    is_ok, reason = is_lot_eligible(lot_quarantine, hospital_market_rule, base_date)
    assert is_ok is False
    assert "Ineligible quality status: 'QUARANTINE'" in reason

    # Blocked lot (e.g. temperature excursion investigation)
    lot_blocked = InventoryLot(
        lot_id="LOT-003", sku_id="SKU-AUG-625-T10", location_id="LOC-WH-NAG",
        quantity=3000, mfg_date=date(2026, 9, 1), expiry_date=date(2028, 9, 1),
        quality_status=QualityStatus.BLOCKED
    )
    is_ok, reason = is_lot_eligible(lot_blocked, hospital_market_rule, base_date)
    assert is_ok is False
    assert "Ineligible quality status: 'BLOCKED'" in reason


def test_lot_eligibility_shelf_life_threshold(base_date, hospital_market_rule):
    # Lot with 120 days RSL (> 90 days required) -> PASS
    lot_valid = InventoryLot(
        lot_id="LOT-VALID", sku_id="SKU-AUG-625-T10", location_id="LOC-WH-NAG",
        quantity=2000, mfg_date=date(2025, 3, 1), expiry_date=date(2027, 3, 1),
        quality_status=QualityStatus.RELEASED
    )
    assert is_lot_eligible(lot_valid, hospital_market_rule, base_date)[0] is True

    # Lot with 45 days RSL (< 90 days required) -> FAIL (Scenario D exposure)
    lot_near_expiry = InventoryLot(
        lot_id="LOT-NEAR-EXPIRY", sku_id="SKU-AUG-625-T10", location_id="LOC-WH-NAG",
        quantity=2000, mfg_date=date(2024, 12, 16), expiry_date=date(2026, 12, 16),
        quality_status=QualityStatus.RELEASED
    )
    is_ok, reason = is_lot_eligible(lot_near_expiry, hospital_market_rule, base_date)
    assert is_ok is False
    assert "Insufficient shelf life: RSL (45 days) is below market 'MKT-CHN-001' threshold (90 days)" in reason


def test_fefo_sorting_priority(base_date, hospital_market_rule):
    # Create 3 lots with different expiry dates
    lot_early = InventoryLot(
        lot_id="LOT-EARLY", sku_id="SKU-AUG-625-T10", location_id="LOC-WH-NAG",
        quantity=1000, mfg_date=date(2025, 4, 1), expiry_date=date(2027, 4, 1),
        quality_status=QualityStatus.RELEASED
    )
    lot_mid = InventoryLot(
        lot_id="LOT-MID", sku_id="SKU-AUG-625-T10", location_id="LOC-WH-NAG",
        quantity=1500, mfg_date=date(2025, 6, 1), expiry_date=date(2027, 6, 1),
        quality_status=QualityStatus.RELEASED
    )
    lot_late = InventoryLot(
        lot_id="LOT-LATE", sku_id="SKU-AUG-625-T10", location_id="LOC-WH-NAG",
        quantity=2000, mfg_date=date(2025, 9, 1), expiry_date=date(2027, 9, 1),
        quality_status=QualityStatus.RELEASED
    )

    # Pass in shuffled order
    shuffled = [lot_late, lot_early, lot_mid]
    sorted_lots = filter_and_sort_fefo(shuffled, hospital_market_rule, base_date)

    # Verify strict FEFO order: LOT-EARLY -> LOT-MID -> LOT-LATE
    assert [l.lot_id for l in sorted_lots] == ["LOT-EARLY", "LOT-MID", "LOT-LATE"]


def test_fefo_allocation_depletion_logic(base_date, hospital_market_rule):
    lot1 = InventoryLot(
        lot_id="LOT-1", sku_id="SKU-AUG-625-T10", location_id="LOC-WH-NAG",
        quantity=1000, mfg_date=date(2025, 3, 1), expiry_date=date(2027, 3, 1),
        quality_status=QualityStatus.RELEASED
    )
    lot2 = InventoryLot(
        lot_id="LOT-2", sku_id="SKU-AUG-625-T10", location_id="LOC-WH-NAG",
        quantity=2500, mfg_date=date(2025, 5, 1), expiry_date=date(2027, 5, 1),
        quality_status=QualityStatus.RELEASED
    )
    lot_unreleased = InventoryLot(
        lot_id="LOT-UNREL", sku_id="SKU-AUG-625-T10", location_id="LOC-WH-NAG",
        quantity=5000, mfg_date=date(2025, 6, 1), expiry_date=date(2027, 6, 1),
        quality_status=QualityStatus.QUARANTINE
    )

    lots = [lot2, lot_unreleased, lot1]

    # Order for 2,000 units
    # Expect: 1,000 from LOT-1 (fully consumed), 1,000 from LOT-2 (partial), 0 from LOT-UNREL
    result = allocate_fefo(lots, demand_qty=2000, market_rule=hospital_market_rule, as_of_date=base_date)

    assert result.is_fully_satisfied is True
    assert result.fulfilled_qty == 2000
    assert result.unmet_qty == 0.0
    assert len(result.allocations) == 2

    assert result.allocations[0].lot_id == "LOT-1"
    assert result.allocations[0].allocated_qty == 1000

    assert result.allocations[1].lot_id == "LOT-2"
    assert result.allocations[1].allocated_qty == 1000


def test_fefo_allocation_with_stockout(base_date, hospital_market_rule):
    lot1 = InventoryLot(
        lot_id="LOT-1", sku_id="SKU-AUG-625-T10", location_id="LOC-WH-NAG",
        quantity=800, mfg_date=date(2025, 3, 1), expiry_date=date(2027, 3, 1),
        quality_status=QualityStatus.RELEASED
    )
    lots = [lot1]

    # Demand for 1,200 units (only 800 available)
    result = allocate_fefo(lots, demand_qty=1200, market_rule=hospital_market_rule, as_of_date=base_date)

    assert result.is_fully_satisfied is False
    assert result.fulfilled_qty == 800.0
    assert result.unmet_qty == 400.0


def test_expiry_exposure_warning(base_date, hospital_market_rule):
    # MARSL is 90 days.
    # Lot A: RSL = 105 days -> Days to ineligibility = 15 days (Within 30d warning window -> AT RISK)
    lot_at_risk = InventoryLot(
        lot_id="LOT-EXP-RISK", sku_id="SKU-AUG-625-T10", location_id="LOC-WH-NAG",
        quantity=1200, mfg_date=date(2025, 2, 14), expiry_date=date(2027, 2, 14),
        quality_status=QualityStatus.RELEASED
    )
    # Lot B: RSL = 300 days -> Days to ineligibility = 210 days (SAFE)
    lot_safe = InventoryLot(
        lot_id="LOT-SAFE", sku_id="SKU-AUG-625-T10", location_id="LOC-WH-NAG",
        quantity=4000, mfg_date=date(2025, 8, 28), expiry_date=date(2027, 8, 28),
        quality_status=QualityStatus.RELEASED
    )

    lots = [lot_at_risk, lot_safe]
    exposure_list = calculate_expiry_exposure(lots, hospital_market_rule, base_date, warning_horizon_days=30)

    assert len(exposure_list) == 1
    assert exposure_list[0][0].lot_id == "LOT-EXP-RISK"
    assert exposure_list[0][1] == 15  # 15 days left before becoming ineligible
    assert exposure_list[0][2] == 1200  # at-risk quantity

