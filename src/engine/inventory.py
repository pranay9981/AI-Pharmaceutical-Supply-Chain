"""
Pharmaceutical Multi-Echelon Inventory Eligibility & FEFO Allocation Engine.
Phase 2 (Day 15) Core Analytics Implementation.

Evaluates lot-level eligibility across quality, recall, and shelf-life constraints (MARSL),
and executes deterministic First-Expired, First-Out (FEFO) depletion against commercial demand.
Strictly zero LLM mathematical calculations.
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import List, Dict, Tuple, Optional, Any, Union
import sqlite3
import pandas as pd

from src.models.procurement_inventory import FactInventoryLot
from src.models.bridges import BridgeSKUMarket


@dataclass(frozen=True)
class LotEligibilityResult:
    """Detailed evaluation result of a single inventory lot's commercial eligibility."""
    lot_id: str
    item_id: str
    location_id: str
    is_eligible: bool
    available_quantity: float
    remaining_shelf_life_days: int
    marsl_threshold_days: int
    days_to_ineligibility: int
    disqualification_reasons: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class AllocationItem:
    """Individual lot draw executed during FEFO order fulfillment."""
    lot_id: str
    item_id: str
    location_id: str
    allocated_quantity: float
    remaining_lot_available: float
    lot_expiry_date: date
    remaining_shelf_life_days: int
    unit_cost: float = 0.0
    allocated_value: float = 0.0


@dataclass(frozen=True)
class AllocationSummary:
    """Executive outcome of a deterministic FEFO allocation run."""
    item_id: str
    requested_quantity: float
    fulfilled_quantity: float
    unmet_quantity: float
    is_fully_satisfied: bool
    allocations: List[AllocationItem] = field(default_factory=list)
    lots_evaluated_count: int = 0
    eligible_lots_count: int = 0
    depleted_lots_count: int = 0
    total_allocated_value: float = 0.0


@dataclass(frozen=True)
class ExpiryRiskItem:
    """Diagnostic record for lots facing shelf-life expiry or MARSL breach (Scenario D)."""
    lot_id: str
    item_id: str
    location_id: str
    quantity_at_risk: float
    expiry_date: date
    remaining_shelf_life_days: int
    target_market_id: Optional[str]
    marsl_threshold_days: int
    days_until_breach: int
    estimated_loss_value: float
    risk_tier: str  # "CRITICAL", "HIGH", "MEDIUM", "LOW"


def parse_date(d: Union[date, datetime, str]) -> date:
    """Converts date, datetime, or ISO string to a standard datetime.date."""
    if isinstance(d, datetime):
        return d.date()
    if isinstance(d, date):
        return d
    if isinstance(d, str):
        return datetime.fromisoformat(d.replace("Z", "")).date()
    raise TypeError(f"Cannot parse object of type {type(d)} into date: {d}")


def calculate_rsl(expiry_date: Union[date, str], as_of_date: Union[date, str]) -> int:
    """
    Computes Remaining Shelf Life (RSL) in calendar days.
    RSL = ExpiryDate - AsOfDate
    """
    exp = parse_date(expiry_date)
    as_of = parse_date(as_of_date)
    return (exp - as_of).days


def extract_lot_attributes(lot: Any) -> Dict[str, Any]:
    """Extracts standardized lot attributes from Pydantic model, dict, or object."""
    if isinstance(lot, dict):
        return {
            "lot_id": lot.get("lot_id", ""),
            "item_id": lot.get("item_id", lot.get("sku_id", "")),
            "location_id": lot.get("location_id", ""),
            "quantity_on_hand": float(lot.get("quantity_on_hand", lot.get("quantity", 0.0))),
            "reserved_quantity": float(lot.get("reserved_quantity", 0.0)),
            "blocked_quantity": float(lot.get("blocked_quantity", 0.0)),
            "quality_status": str(lot.get("quality_status", "Released")),
            "recall_status": str(lot.get("recall_status", "None")),
            "expiry_date": parse_date(lot.get("expiry_date")),
            "manufacture_date": parse_date(lot.get("manufacture_date", lot.get("mfg_date", "2000-01-01"))),
            "unit_cost": float(lot.get("unit_cost", 0.0))
        }
    elif hasattr(lot, "model_dump"):  # Pydantic model
        data = lot.model_dump()
        return extract_lot_attributes(data)
    else:  # Dataclass or generic object
        return {
            "lot_id": getattr(lot, "lot_id", ""),
            "item_id": getattr(lot, "item_id", getattr(lot, "sku_id", "")),
            "location_id": getattr(lot, "location_id", ""),
            "quantity_on_hand": float(getattr(lot, "quantity_on_hand", getattr(lot, "quantity", 0.0))),
            "reserved_quantity": float(getattr(lot, "reserved_quantity", 0.0)),
            "blocked_quantity": float(getattr(lot, "blocked_quantity", 0.0)),
            "quality_status": str(getattr(lot, "quality_status", "Released")),
            "recall_status": str(getattr(lot, "recall_status", "None")),
            "expiry_date": parse_date(getattr(lot, "expiry_date")),
            "manufacture_date": parse_date(getattr(lot, "manufacture_date", getattr(lot, "mfg_date", date(2000, 1, 1)))),
            "unit_cost": float(getattr(lot, "unit_cost", 0.0))
        }


def calculate_available_quantity(lot: Any) -> float:
    """
    Computes unreserved, unblocked physically available stock:
    Q_available = max(0.0, Q_on_hand - Q_reserved - Q_blocked)
    """
    attr = extract_lot_attributes(lot)
    net_avail = attr["quantity_on_hand"] - attr["reserved_quantity"] - attr["blocked_quantity"]
    return max(0.0, round(net_avail, 4))


def evaluate_lot_eligibility(
    lot: Any,
    as_of_date: Union[date, str],
    min_acceptable_rsl_days: int = 0,
    target_market_id: Optional[str] = None
) -> LotEligibilityResult:
    """
    Evaluates multi-factor pharmaceutical commercial eligibility for an inventory lot.

    Eligibility Rules:
    1. Quantity: Net available physical stock (On-Hand - Reserved - Blocked) must be > 0.
    2. Quality Status: Must be explicitly 'Released' (rejects 'Quarantine', 'Blocked', 'Rejected', 'Expired').
    3. Recall Status: Must be 'None' (rejects lots under active regulatory recall or investigation).
    4. Expiry: Calendar date must not have surpassed expiration date (RSL > 0).
    5. MARSL: Remaining Shelf Life must meet or exceed destination market threshold (RSL >= MARSL).
    """
    attr = extract_lot_attributes(lot)
    as_of = parse_date(as_of_date)
    rsl = calculate_rsl(attr["expiry_date"], as_of)
    avail_qty = calculate_available_quantity(lot)
    days_to_ineligibility = rsl - min_acceptable_rsl_days

    reasons: List[str] = []

    # Rule 1: Physical Availability
    if avail_qty <= 0.0:
        reasons.append(
            f"Zero available quantity: on_hand={attr['quantity_on_hand']}, "
            f"reserved={attr['reserved_quantity']}, blocked={attr['blocked_quantity']}"
        )

    # Rule 2: Quality Release Status
    status = attr["quality_status"].upper().replace("QUALITYSTATUS.", "")
    if status != "RELEASED":
        reasons.append(f"Ineligible quality status: '{attr['quality_status']}' (Requires 'Released')")

    # Rule 3: Regulatory Recall Embargo
    recall = attr["recall_status"].upper()
    if recall != "NONE":
        reasons.append(f"Active regulatory embargo: recall_status='{attr['recall_status']}'")

    # Rule 4: Hard Expiration
    if rsl <= 0:
        reasons.append(f"Lot expired on {attr['expiry_date']} (RSL = {rsl} days)")

    # Rule 5: MARSL Threshold
    if min_acceptable_rsl_days > 0 and rsl < min_acceptable_rsl_days:
        market_str = f" for market '{target_market_id}'" if target_market_id else ""
        reasons.append(
            f"Insufficient shelf life{market_str}: RSL ({rsl} days) < MARSL ({min_acceptable_rsl_days} days)"
        )

    is_eligible = (len(reasons) == 0)

    return LotEligibilityResult(
        lot_id=attr["lot_id"],
        item_id=attr["item_id"],
        location_id=attr["location_id"],
        is_eligible=is_eligible,
        available_quantity=avail_qty,
        remaining_shelf_life_days=rsl,
        marsl_threshold_days=min_acceptable_rsl_days,
        days_to_ineligibility=days_to_ineligibility,
        disqualification_reasons=reasons
    )


def filter_and_sort_fefo(
    lots: List[Any],
    as_of_date: Union[date, str],
    min_acceptable_rsl_days: int = 0,
    target_market_id: Optional[str] = None
) -> List[Tuple[Any, LotEligibilityResult]]:
    """
    Filters lots by multi-factor eligibility and sorts strictly by First-Expired, First-Out (FEFO).
    Sorting priority: Expiry Date ASC, then Lot ID ASC (deterministic tiebreaker).
    """
    eligible_pairs = []
    for lot in lots:
        eval_res = evaluate_lot_eligibility(
            lot,
            as_of_date=as_of_date,
            min_acceptable_rsl_days=min_acceptable_rsl_days,
            target_market_id=target_market_id
        )
        if eval_res.is_eligible:
            eligible_pairs.append((lot, eval_res))

    # Strict FEFO sort
    def sort_key(pair):
        attr = extract_lot_attributes(pair[0])
        return (attr["expiry_date"], attr["lot_id"])

    return sorted(eligible_pairs, key=sort_key)


def allocate_fefo(
    lots: List[Any],
    demand_quantity: float,
    as_of_date: Union[date, str],
    min_acceptable_rsl_days: int = 0,
    target_market_id: Optional[str] = None,
    item_cost_lookup: Optional[Dict[str, float]] = None
) -> Tuple[AllocationSummary, List[Dict[str, Any]]]:
    """
    Executes deterministic FEFO stock allocation against requested commercial demand.

    Depletes stock strictly from earliest expiring eligible lots first.
    Preserves exact mathematical conservation:
    Requested Demand = Fulfilled Quantity + Unmet Quantity (Stockout).

    Returns:
        (AllocationSummary, updated_lots_state)
    """
    if demand_quantity <= 0.0:
        return AllocationSummary(
            item_id="",
            requested_quantity=0.0,
            fulfilled_quantity=0.0,
            unmet_quantity=0.0,
            is_fully_satisfied=True
        ), [extract_lot_attributes(l) for l in lots]

    as_of = parse_date(as_of_date)
    item_id_found = ""

    # Deep-copy lot attributes to track residual state without mutating callers
    lots_state = [extract_lot_attributes(l) for l in lots]
    sorted_eligible = filter_and_sort_fefo(
        lots_state,
        as_of_date=as_of,
        min_acceptable_rsl_days=min_acceptable_rsl_days,
        target_market_id=target_market_id
    )

    remaining_demand = demand_quantity
    allocations: List[AllocationItem] = []
    depleted_count = 0
    total_val = 0.0

    for lot_dict, eval_res in sorted_eligible:
        if remaining_demand <= 0.0:
            break

        item_id_found = lot_dict["item_id"]
        avail = calculate_available_quantity(lot_dict)
        if avail <= 0.0:
            continue

        take_qty = min(avail, remaining_demand)
        new_avail = avail - take_qty

        # Costing
        cost = lot_dict.get("unit_cost", 0.0)
        if (cost == 0.0) and item_cost_lookup and (lot_dict["item_id"] in item_cost_lookup):
            cost = item_cost_lookup[lot_dict["item_id"]]
        alloc_val = round(take_qty * cost, 2)
        total_val += alloc_val

        allocations.append(
            AllocationItem(
                lot_id=lot_dict["lot_id"],
                item_id=lot_dict["item_id"],
                location_id=lot_dict["location_id"],
                allocated_quantity=take_qty,
                remaining_lot_available=new_avail,
                lot_expiry_date=lot_dict["expiry_date"],
                remaining_shelf_life_days=eval_res.remaining_shelf_life_days,
                unit_cost=cost,
                allocated_value=alloc_val
            )
        )

        # Mutate residual state in tracking dictionary
        lot_dict["reserved_quantity"] += take_qty
        if new_avail == 0.0:
            depleted_count += 1

        remaining_demand -= take_qty

    fulfilled_qty = round(demand_quantity - remaining_demand, 4)
    unmet_qty = round(max(0.0, remaining_demand), 4)

    summary = AllocationSummary(
        item_id=item_id_found,
        requested_quantity=demand_quantity,
        fulfilled_quantity=fulfilled_qty,
        unmet_quantity=unmet_qty,
        is_fully_satisfied=(unmet_qty == 0.0),
        allocations=allocations,
        lots_evaluated_count=len(lots),
        eligible_lots_count=len(sorted_eligible),
        depleted_lots_count=depleted_count,
        total_allocated_value=round(total_val, 2)
    )

    return summary, lots_state


def detect_expiry_exposures(
    lots: List[Any],
    as_of_date: Union[date, str],
    market_rules: Optional[Dict[str, int]] = None,
    warning_horizon_days: int = 60,
    unit_cost_lookup: Optional[Dict[str, float]] = None
) -> List[ExpiryRiskItem]:
    """
    Detects lots approaching expiry or MARSL disqualification within a forward warning window (Scenario D).
    Triggers when: 0 <= (RSL - MARSL) <= warning_horizon_days, or when already expired (RSL <= 0).
    """
    as_of = parse_date(as_of_date)
    at_risk: List[ExpiryRiskItem] = []

    for lot in lots:
        attr = extract_lot_attributes(lot)
        avail = calculate_available_quantity(lot)
        if avail <= 0.0:
            continue

        rsl = calculate_rsl(attr["expiry_date"], as_of)
        marsl = 0
        target_mkt = None
        if market_rules and attr["item_id"] in market_rules:
            marsl = market_rules[attr["item_id"]]

        days_to_breach = rsl - marsl
        cost = attr.get("unit_cost", 0.0)
        if cost == 0.0 and unit_cost_lookup and (attr["item_id"] in unit_cost_lookup):
            cost = unit_cost_lookup[attr["item_id"]]
        loss_val = round(avail * cost, 2)

        if days_to_breach <= warning_horizon_days:
            # Determine risk tier
            if days_to_breach <= 0:
                tier = "CRITICAL"  # Already breached MARSL or expired
            elif days_to_breach <= 15:
                tier = "HIGH"
            elif days_to_breach <= 30:
                tier = "MEDIUM"
            else:
                tier = "LOW"

            at_risk.append(
                ExpiryRiskItem(
                    lot_id=attr["lot_id"],
                    item_id=attr["item_id"],
                    location_id=attr["location_id"],
                    quantity_at_risk=avail,
                    expiry_date=attr["expiry_date"],
                    remaining_shelf_life_days=rsl,
                    target_market_id=target_mkt,
                    marsl_threshold_days=marsl,
                    days_until_breach=days_to_breach,
                    estimated_loss_value=loss_val,
                    risk_tier=tier
                )
            )

    return sorted(at_risk, key=lambda x: (x.days_until_breach, -x.quantity_at_risk))


def evaluate_inventory_posture(
    lots: List[Any],
    as_of_date: Union[date, str],
    marsl_lookup: Optional[Dict[str, int]] = None
) -> Dict[str, Any]:
    """
    Generates multi-echelon inventory posture metrics: total physical stock,
    released eligible stock, reserved, blocked/quarantine, and expired capital.
    """
    as_of = parse_date(as_of_date)
    total_physical = 0.0
    total_eligible = 0.0
    total_reserved = 0.0
    total_blocked = 0.0
    total_expired = 0.0

    by_status: Dict[str, float] = {}
    by_item: Dict[str, Dict[str, float]] = {}

    for lot in lots:
        attr = extract_lot_attributes(lot)
        item = attr["item_id"]
        on_hand = attr["quantity_on_hand"]
        res = attr["reserved_quantity"]
        blk = attr["blocked_quantity"]
        status = attr["quality_status"]
        rsl = calculate_rsl(attr["expiry_date"], as_of)

        total_physical += on_hand
        total_reserved += res
        total_blocked += blk
        by_status[status] = by_status.get(status, 0.0) + on_hand

        if item not in by_item:
            by_item[item] = {"on_hand": 0.0, "eligible": 0.0, "reserved": 0.0, "blocked": 0.0}
        by_item[item]["on_hand"] += on_hand
        by_item[item]["reserved"] += res
        by_item[item]["blocked"] += blk

        marsl = marsl_lookup.get(item, 0) if marsl_lookup else 0
        eval_res = evaluate_lot_eligibility(lot, as_of, min_acceptable_rsl_days=marsl)
        if eval_res.is_eligible:
            total_eligible += eval_res.available_quantity
            by_item[item]["eligible"] += eval_res.available_quantity

        if rsl <= 0:
            total_expired += on_hand

    return {
        "as_of_date": as_of.isoformat(),
        "total_lots_count": len(lots),
        "total_physical_stock": round(total_physical, 2),
        "total_eligible_stock": round(total_eligible, 2),
        "total_reserved_stock": round(total_reserved, 2),
        "total_blocked_stock": round(total_blocked, 2),
        "total_expired_stock": round(total_expired, 2),
        "stock_by_status": by_status,
        "stock_by_item": by_item
    }


def load_lots_from_database(
    db_conn: sqlite3.Connection,
    location_id: Optional[str] = None,
    item_id: Optional[str] = None
) -> List[FactInventoryLot]:
    """Queries SQLite fact_inventory_lot table and returns validated Pydantic models."""
    query = "SELECT * FROM fact_inventory_lot WHERE 1=1"
    params = []
    if location_id:
        query += " AND location_id = ?"
        params.append(location_id)
    if item_id:
        query += " AND item_id = ?"
        params.append(item_id)

    df = pd.read_sql_query(query, db_conn, params=params)
    records = df.to_dict(orient="records")
    return [FactInventoryLot(**r) for r in records]


def load_sku_market_rules_from_database(
    db_conn: sqlite3.Connection
) -> Dict[Tuple[str, str], int]:
    """Queries bridge_sku_market and returns mapping: (finished_sku_id, market_id) -> min_acceptable_rsl_days."""
    df = pd.read_sql_query(
        "SELECT finished_sku_id, market_id, min_acceptable_rsl_days FROM bridge_sku_market",
        db_conn
    )
    mapping = {}
    for _, row in df.iterrows():
        mapping[(row["finished_sku_id"], row["market_id"])] = int(row["min_acceptable_rsl_days"])
    return mapping
