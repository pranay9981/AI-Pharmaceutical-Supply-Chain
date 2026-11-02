"""
FEFO (First-Expired, First-Out) Mathematical Rules and Eligibility Engine.
Technical Reference Implementation for Day 03 Deliverable.

This module provides pure, testable deterministic functions that evaluate lot eligibility,
remaining shelf-life constraints, FEFO priority sorting, and order allocation.
Strictly zero LLM dependencies or probabilistic approximations.
"""

from dataclasses import dataclass
from datetime import date
from typing import List, Tuple, Optional
from enum import Enum


class QualityStatus(str, Enum):
    QUARANTINE = "QUARANTINE"
    RELEASED = "RELEASED"
    BLOCKED = "BLOCKED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


@dataclass(frozen=True)
class InventoryLot:
    lot_id: str
    sku_id: str
    location_id: str
    quantity: float
    mfg_date: date
    expiry_date: date
    quality_status: QualityStatus
    unit_cost: float = 0.0


@dataclass(frozen=True)
class MarketShelfLifeRule:
    market_id: str
    sku_id: str
    min_acceptable_rsl_days: int  # MARSL threshold in days


@dataclass
class AllocationItem:
    lot_id: str
    allocated_qty: float
    lot_expiry_date: date
    remaining_shelf_life_days: int


@dataclass
class AllocationResult:
    fulfilled_qty: float
    unmet_qty: float
    allocations: List[AllocationItem]
    is_fully_satisfied: bool


def calculate_remaining_shelf_life(expiry_date: date, as_of_date: date) -> int:
    """
    Calculate the Remaining Shelf Life (RSL) in calendar days.
    RSL = ExpiryDate - CurrentDate
    """
    return (expiry_date - as_of_date).days


def is_lot_eligible(
    lot: InventoryLot,
    market_rule: Optional[MarketShelfLifeRule],
    as_of_date: date
) -> Tuple[bool, Optional[str]]:
    """
    Evaluate the binary indicator function: E(l, m, t)
    E(l, m, t) = I(status == 'RELEASED') * I(RSL >= MARSL(m)) * I(quantity > 0)

    Returns:
        (is_eligible: bool, disqualification_reason: Optional[str])
    """
    # Rule 1: Zero or negative physical quantity
    if lot.quantity <= 0:
        return False, "Zero or negative physical quantity on-hand"

    # Rule 2: Quality status must be explicitly RELEASED
    if lot.quality_status != QualityStatus.RELEASED:
        return False, f"Ineligible quality status: '{lot.quality_status.value}' (Requires 'RELEASED')"

    # Rule 3: Calendar date has surpassed expiry date
    rsl_days = calculate_remaining_shelf_life(lot.expiry_date, as_of_date)
    if rsl_days <= 0:
        return False, f"Lot has expired (RSL = {rsl_days} days)"

    # Rule 4: Minimum Acceptable Remaining Shelf Life (MARSL) for destination market
    if market_rule is not None:
        if rsl_days < market_rule.min_acceptable_rsl_days:
            return False, (
                f"Insufficient shelf life: RSL ({rsl_days} days) is below "
                f"market '{market_rule.market_id}' threshold ({market_rule.min_acceptable_rsl_days} days)"
            )

    return True, None


def filter_and_sort_fefo(
    lots: List[InventoryLot],
    market_rule: Optional[MarketShelfLifeRule],
    as_of_date: date
) -> List[InventoryLot]:
    """
    Filter candidate lots by eligibility and sort strictly by First-Expired, First-Out (FEFO).
    Sorting key: expiry_date ASC, tie breaker: lot_id ASC.
    """
    eligible = [lot for lot in lots if is_lot_eligible(lot, market_rule, as_of_date)[0]]
    # FEFO sort: earliest expiry first
    return sorted(eligible, key=lambda l: (l.expiry_date, l.lot_id))


def allocate_fefo(
    lots: List[InventoryLot],
    demand_qty: float,
    market_rule: Optional[MarketShelfLifeRule],
    as_of_date: date
) -> AllocationResult:
    """
    Execute FEFO allocation against customer demand.
    Depletes stock strictly from earliest expiring eligible lots first.
    """
    if demand_qty <= 0:
        return AllocationResult(fulfilled_qty=0.0, unmet_qty=0.0, allocations=[], is_fully_satisfied=True)

    sorted_lots = filter_and_sort_fefo(lots, market_rule, as_of_date)
    remaining_demand = demand_qty
    allocations: List[AllocationItem] = []

    for lot in sorted_lots:
        if remaining_demand <= 0:
            break

        take_qty = min(lot.quantity, remaining_demand)
        rsl = calculate_remaining_shelf_life(lot.expiry_date, as_of_date)
        allocations.append(
            AllocationItem(
                lot_id=lot.lot_id,
                allocated_qty=take_qty,
                lot_expiry_date=lot.expiry_date,
                remaining_shelf_life_days=rsl
            )
        )
        remaining_demand -= take_qty

    fulfilled_qty = demand_qty - remaining_demand
    return AllocationResult(
        fulfilled_qty=fulfilled_qty,
        unmet_qty=max(0.0, remaining_demand),
        allocations=allocations,
        is_fully_satisfied=(remaining_demand <= 0.0)
    )


def calculate_expiry_exposure(
    lots: List[InventoryLot],
    market_rule: MarketShelfLifeRule,
    as_of_date: date,
    warning_horizon_days: int = 30
) -> List[Tuple[InventoryLot, int, float]]:
    """
    Detect lots approaching ineligibility (Scenario D).
    Returns list of (lot, days_until_ineligible, at_risk_quantity) where:
    0 <= (RSL - MARSL) <= warning_horizon_days
    """
    at_risk = []
    for lot in lots:
        if lot.quality_status == QualityStatus.RELEASED and lot.quantity > 0:
            rsl = calculate_remaining_shelf_life(lot.expiry_date, as_of_date)
            days_to_ineligibility = rsl - market_rule.min_acceptable_rsl_days
            if 0 <= days_to_ineligibility <= warning_horizon_days:
                at_risk.append((lot, days_to_ineligibility, lot.quantity))
    return at_risk

