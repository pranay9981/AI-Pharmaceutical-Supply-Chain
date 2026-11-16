"""
Pharmaceutical BOM Explosion & Material Requirements Planning (MRP) Engine.
Phase 2 (Day 17) Core Analytics Implementation.

Translates master production scheduling (MPS) finished SKU orders into gross ingredient requirements,
nets against QA-released material inventory and confirmed purchase orders, and flags component shortages.
Strictly zero LLM mathematical calculations.
"""

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import List, Dict, Tuple, Optional, Any, Union
import sqlite3
import pandas as pd

from src.models.planning import FactMaterialRequirement
from src.models.bridges import BridgeBillOfMaterial
from src.models.manufacturing_quality import FactProductionOrder
from src.models.procurement_inventory import FactInventoryLot, FactPurchaseOrder
from src.engine.inventory import parse_date, calculate_available_quantity, extract_lot_attributes


@dataclass(frozen=True)
class ComponentGrossRequirement:
    """Gross component requirement derived from Bill of Materials (BOM) explosion."""
    production_order_id: str
    finished_sku_id: str
    material_sku_id: str
    need_by_date: date
    quantity_per_finished_unit: float
    scrap_factor_pct: float
    base_quantity: float
    scrap_quantity: float
    gross_quantity: float


@dataclass(frozen=True)
class MaterialNettingResult:
    """Deterministic material netting result evaluating supply coverage vs gross requirement."""
    requirement_id: str
    production_order_id: str
    material_sku_id: str
    need_by_date: date
    gross_requirement: float
    eligible_available_quantity: float
    quarantined_quantity: float
    expected_receipt_quantity: float
    total_supply_available: float
    shortage_quantity: float
    is_shortage: bool
    coverage_ratio: float
    linked_po_ids: List[str] = field(default_factory=list)
    scenario_id: str = "SCN-BASE"


@dataclass(frozen=True)
class MRPSummary:
    """Executive summary of a complete Material Requirements Planning (MRP) run."""
    production_orders_evaluated: int
    components_exploded_count: int
    shortage_components_count: int
    total_shortage_quantity: float
    shortages_by_material: Dict[str, float]
    order_readiness: Dict[str, bool]  # production_order_id -> True if 100% component availability
    has_critical_shortage: bool
    netting_results: List[MaterialNettingResult] = field(default_factory=list)


def calculate_bom_gross_requirement(
    finished_units: float,
    quantity_per_finished_unit: float,
    scrap_factor_pct: float
) -> Tuple[float, float, float]:
    """
    Computes base, scrap, and gross material requirements using pharmaceutical scrap factors:
    Base = Units * QuantityPerUnit
    Scrap = Base * (ScrapPct / 100)
    Gross = Base + Scrap
    """
    if finished_units <= 0.0 or quantity_per_finished_unit <= 0.0:
        return 0.0, 0.0, 0.0

    base_qty = round(finished_units * quantity_per_finished_unit, 4)
    scrap_qty = round(base_qty * (scrap_factor_pct / 100.0), 4)
    gross_qty = round(base_qty + scrap_qty, 4)
    return base_qty, scrap_qty, gross_qty


def explode_bom_for_order(
    production_order: Any,
    bom_records: List[Any]
) -> List[ComponentGrossRequirement]:
    """
    Explodes planned production order into individual raw material and packaging gross requirements.
    Matches finished_sku_id against active BOM lines.
    """
    if hasattr(production_order, "model_dump"):
        p_dict = production_order.model_dump()
    elif isinstance(production_order, dict):
        p_dict = production_order
    else:
        p_dict = {
            "production_order_id": getattr(production_order, "production_order_id"),
            "finished_sku_id": getattr(production_order, "finished_sku_id"),
            "planned_start_date": getattr(production_order, "planned_start_date"),
            "planned_quantity": getattr(production_order, "planned_quantity")
        }

    p_id = p_dict["production_order_id"]
    sku_id = p_dict["finished_sku_id"]
    need_date = parse_date(p_dict["planned_start_date"])
    planned_qty = float(p_dict["planned_quantity"])

    requirements: List[ComponentGrossRequirement] = []

    for bom in bom_records:
        if hasattr(bom, "model_dump"):
            b_dict = bom.model_dump()
        elif isinstance(bom, dict):
            b_dict = bom
        else:
            b_dict = {
                "finished_sku_id": getattr(bom, "finished_sku_id"),
                "material_sku_id": getattr(bom, "material_sku_id"),
                "quantity_per_finished_unit": getattr(bom, "quantity_per_finished_unit"),
                "scrap_factor_pct": getattr(bom, "scrap_factor_pct", 0.0)
            }

        if b_dict["finished_sku_id"] == sku_id:
            qty_per_unit = float(b_dict["quantity_per_finished_unit"])
            scrap_pct = float(b_dict.get("scrap_factor_pct", 0.0))
            base_q, scrap_q, gross_q = calculate_bom_gross_requirement(planned_qty, qty_per_unit, scrap_pct)

            requirements.append(
                ComponentGrossRequirement(
                    production_order_id=p_id,
                    finished_sku_id=sku_id,
                    material_sku_id=b_dict["material_sku_id"],
                    need_by_date=need_date,
                    quantity_per_finished_unit=qty_per_unit,
                    scrap_factor_pct=scrap_pct,
                    base_quantity=base_q,
                    scrap_quantity=scrap_q,
                    gross_quantity=gross_q
                )
            )

    return sorted(requirements, key=lambda x: x.material_sku_id)


def net_material_requirement(
    gross_req: ComponentGrossRequirement,
    eligible_on_hand: float,
    quarantined_on_hand: float = 0.0,
    expected_receipts: float = 0.0,
    linked_po_ids: Optional[List[str]] = None,
    scenario_id: str = "SCN-BASE"
) -> MaterialNettingResult:
    """
    Nets gross requirement against eligible stock and confirmed receipts:
    Net Shortage = max(0.0, Gross - (Eligible_Stock + Confirmed_Receipts))
    """
    total_supply = round(eligible_on_hand + expected_receipts, 4)
    shortage = max(0.0, round(gross_req.gross_quantity - total_supply, 4))
    is_so = (shortage > 0.0)

    cov_ratio = 1.0 if gross_req.gross_quantity <= 0.0 else round(total_supply / gross_req.gross_quantity, 4)
    req_id = f"REQ-{gross_req.production_order_id}-{gross_req.material_sku_id}"

    return MaterialNettingResult(
        requirement_id=req_id,
        production_order_id=gross_req.production_order_id,
        material_sku_id=gross_req.material_sku_id,
        need_by_date=gross_req.need_by_date,
        gross_requirement=gross_req.gross_quantity,
        eligible_available_quantity=round(eligible_on_hand, 4),
        quarantined_quantity=round(quarantined_on_hand, 4),
        expected_receipt_quantity=round(expected_receipts, 4),
        total_supply_available=total_supply,
        shortage_quantity=shortage,
        is_shortage=is_so,
        coverage_ratio=cov_ratio,
        linked_po_ids=[] if linked_po_ids is None else linked_po_ids,
        scenario_id=scenario_id
    )


def run_mrp_for_production_schedule(
    production_orders: List[Any],
    bom_records: List[Any],
    inventory_lots: List[Any],
    purchase_orders: List[Any],
    as_of_date: Union[date, str] = "2026-10-26",
    plant_location_id: str = "LOC-PLANT-01",
    scenario_id: str = "SCN-BASE"
) -> MRPSummary:
    """
    Executes a multi-order chronological MRP explosion and material netting run.

    Sequential Allocation Logic:
    1. Sorts production orders chronologically by planned_start_date.
    2. Explodes BOM lines for each order.
    3. Allocates eligible on-hand raw material lots and confirmed incoming POs.
    4. Decrements available stock pool as earlier production orders consume raw materials,
       properly detecting downstream shortages when multiple orders compete for shared ingredients.
    """
    as_of = parse_date(as_of_date)

    # 1. Initialize stock pools at plant
    material_eligible_pool: Dict[str, float] = {}
    material_quarantine_pool: Dict[str, float] = {}

    for lot in inventory_lots:
        attr = extract_lot_attributes(lot)
        if attr["location_id"] == plant_location_id:
            m_id = attr["item_id"]
            status = attr["quality_status"].upper()
            avail = calculate_available_quantity(lot)

            if status == "RELEASED":
                material_eligible_pool[m_id] = material_eligible_pool.get(m_id, 0.0) + avail
            elif status in ["QUARANTINED", "QUARANTINE", "PENDING_INSPECTION"]:
                material_quarantine_pool[m_id] = material_quarantine_pool.get(m_id, 0.0) + attr["quantity_on_hand"]

    # 2. Extract PO incoming pipeline
    # Structure: material_sku_id -> List of (delivery_date, qty, po_id, consumed_flag)
    po_pipeline: Dict[str, List[Dict[str, Any]]] = {}
    for po in purchase_orders:
        if hasattr(po, "model_dump"):
            po_dict = po.model_dump()
        elif isinstance(po, dict):
            po_dict = po
        else:
            po_dict = {
                "purchase_order_id": getattr(po, "purchase_order_id"),
                "material_sku_id": getattr(po, "material_sku_id"),
                "confirmed_delivery_date": getattr(po, "confirmed_delivery_date"),
                "ordered_quantity": getattr(po, "ordered_quantity"),
                "purchase_order_status": getattr(po, "purchase_order_status", "Open")
            }

        m_id = po_dict["material_sku_id"]
        status = po_dict.get("purchase_order_status", "Open")
        if status in ["Open", "In_Transit", "Confirmed"]:
            deliv_date = parse_date(po_dict["confirmed_delivery_date"])
            qty = float(po_dict["ordered_quantity"])
            po_id = po_dict["purchase_order_id"]

            if m_id not in po_pipeline:
                po_pipeline[m_id] = []
            po_pipeline[m_id].append({
                "delivery_date": deliv_date,
                "quantity": qty,
                "remaining_quantity": qty,
                "purchase_order_id": po_id
            })

    # Sort orders chronologically
    def get_order_start(order):
        if isinstance(order, dict):
            return parse_date(order["planned_start_date"])
        return parse_date(getattr(order, "planned_start_date"))

    sorted_orders = sorted(production_orders, key=get_order_start)

    netting_results: List[MaterialNettingResult] = []
    order_readiness: Dict[str, bool] = {}
    shortages_by_mat: Dict[str, float] = {}
    tot_shortage = 0.0
    components_count = 0

    for order in sorted_orders:
        if isinstance(order, dict):
            p_id = order["production_order_id"]
        else:
            p_id = getattr(order, "production_order_id")

        gross_reqs = explode_bom_for_order(order, bom_records)
        order_fully_covered = True

        for req in gross_reqs:
            components_count += 1
            m_id = req.material_sku_id
            need_date = req.need_by_date
            gross_needed = req.gross_quantity

            # Current eligible stock
            on_hand_avail = material_eligible_pool.get(m_id, 0.0)
            quar_avail = material_quarantine_pool.get(m_id, 0.0)

            # Draw from on-hand first
            drawn_from_on_hand = min(on_hand_avail, gross_needed)
            material_eligible_pool[m_id] = round(on_hand_avail - drawn_from_on_hand, 4)
            uncovered = round(gross_needed - drawn_from_on_hand, 4)

            # Draw from incoming PO pipeline that arrives on or before need_by_date
            drawn_from_pos = 0.0
            linked_pos = []

            if m_id in po_pipeline and uncovered > 0.0:
                for po_entry in po_pipeline[m_id]:
                    if po_entry["remaining_quantity"] <= 0.0:
                        continue
                    if po_entry["delivery_date"] <= need_date:
                        po_take = min(po_entry["remaining_quantity"], uncovered)
                        po_entry["remaining_quantity"] = round(po_entry["remaining_quantity"] - po_take, 4)
                        drawn_from_pos = round(drawn_from_pos + po_take, 4)
                        uncovered = round(uncovered - po_take, 4)
                        linked_pos.append(po_entry["purchase_order_id"])
                        if uncovered <= 0.0:
                            break

            total_supply_used = drawn_from_on_hand + drawn_from_pos
            net_deficit = uncovered

            if net_deficit > 0.0:
                order_fully_covered = False
                shortages_by_mat[m_id] = round(shortages_by_mat.get(m_id, 0.0) + net_deficit, 4)
                tot_shortage = round(tot_shortage + net_deficit, 4)

            net_res = MaterialNettingResult(
                requirement_id=f"REQ-{p_id}-{m_id}",
                production_order_id=p_id,
                material_sku_id=m_id,
                need_by_date=need_date,
                gross_requirement=gross_needed,
                eligible_available_quantity=drawn_from_on_hand,
                quarantined_quantity=quar_avail,
                expected_receipt_quantity=drawn_from_pos,
                total_supply_available=total_supply_used,
                shortage_quantity=net_deficit,
                is_shortage=(net_deficit > 0.0),
                coverage_ratio=round(total_supply_used / gross_needed, 4) if gross_needed > 0 else 1.0,
                linked_po_ids=linked_pos,
                scenario_id=scenario_id
            )
            netting_results.append(net_res)

        order_readiness[p_id] = order_fully_covered

    shortage_comp_count = sum(1 for r in netting_results if r.is_shortage)

    return MRPSummary(
        production_orders_evaluated=len(sorted_orders),
        components_exploded_count=components_count,
        shortage_components_count=shortage_comp_count,
        total_shortage_quantity=tot_shortage,
        shortages_by_material=shortages_by_mat,
        order_readiness=order_readiness,
        has_critical_shortage=(shortage_comp_count > 0),
        netting_results=netting_results
    )


def detect_shared_material_conflicts(
    production_orders: List[Any],
    bom_records: List[Any],
    inventory_lots: List[Any],
    purchase_orders: List[Any],
    as_of_date: Union[date, str] = "2026-10-26"
) -> Dict[str, Any]:
    """
    Analyzes contention on shared raw materials (e.g. Amoxicillin API MAT-API-001 or
    Unit Cartons MAT-PKG-CART shared across T10 and T30 SKU presentations).
    Identifies multi-order aggregation deficits where individual orders would pass
    in isolation but create a shortage when jointly scheduled.
    """
    mrp_summary = run_mrp_for_production_schedule(
        production_orders=production_orders,
        bom_records=bom_records,
        inventory_lots=inventory_lots,
        purchase_orders=purchase_orders,
        as_of_date=as_of_date
    )

    # Group components by material across orders
    mat_usage: Dict[str, List[Dict[str, Any]]] = {}
    for r in mrp_summary.netting_results:
        if r.material_sku_id not in mat_usage:
            mat_usage[r.material_sku_id] = []
        mat_usage[r.material_sku_id].append({
            "production_order_id": r.production_order_id,
            "gross_requirement": r.gross_requirement,
            "allocated_on_hand": r.eligible_available_quantity,
            "allocated_po": r.expected_receipt_quantity,
            "shortage": r.shortage_quantity
        })

    shared_materials = {m: orders for m, orders in mat_usage.items() if len(orders) > 1}
    contested_materials = {m: orders for m, orders in shared_materials.items() if any(o["shortage"] > 0 for o in orders)}

    return {
        "as_of_date": parse_date(as_of_date).isoformat(),
        "shared_materials_count": len(shared_materials),
        "contested_materials_count": len(contested_materials),
        "contested_material_ids": list(contested_materials.keys()),
        "shared_material_details": shared_materials,
        "is_conflict_detected": (len(contested_materials) > 0)
    }


def generate_mrp_from_database(
    db_conn: sqlite3.Connection,
    scenario_id: str = "SCN-BASE",
    as_of_date: Union[date, str] = "2026-10-26",
    plant_location_id: str = "LOC-PLANT-01"
) -> Tuple[MRPSummary, List[FactMaterialRequirement]]:
    """
    Executes MRP pipeline querying the real SQLite database:
    1. Loads fact_production_order plant manufacturing work orders.
    2. Loads bridge_bill_of_material formula relationships.
    3. Loads plant raw material lots from fact_inventory_lot.
    4. Loads raw material purchase orders from fact_purchase_order.
    5. In SCN-A-API-DELAY, dynamically models the 14-day delay of PO-2026-001.
    6. Returns MRPSummary and validated Pydantic FactMaterialRequirement entities.
    """
    as_of = parse_date(as_of_date)

    # 1. Production Orders
    prod_df = pd.read_sql_query("SELECT * FROM fact_production_order WHERE location_id = ?", db_conn, params=[plant_location_id])
    prod_orders = [FactProductionOrder(**r) for r in prod_df.to_dict(orient="records")]

    # 2. BOM
    bom_df = pd.read_sql_query("SELECT * FROM bridge_bill_of_material", db_conn)
    bom_records = [BridgeBillOfMaterial(**r) for r in bom_df.to_dict(orient="records")]

    # 3. Raw Material Lots
    lots_df = pd.read_sql_query("SELECT * FROM fact_inventory_lot WHERE location_id = ?", db_conn, params=[plant_location_id])
    lots = [FactInventoryLot(**r) for r in lots_df.to_dict(orient="records")]

    # 4. Purchase Orders
    po_df = pd.read_sql_query("SELECT * FROM fact_purchase_order", db_conn)
    raw_pos = po_df.to_dict(orient="records")

    # If Scenario A, model the 14-day supplier delay on PO-2026-001
    if scenario_id == "SCN-A-API-DELAY":
        for po in raw_pos:
            if po["purchase_order_id"] == "PO-2026-001":
                orig_date = parse_date(po["confirmed_delivery_date"])
                po["confirmed_delivery_date"] = (orig_date + timedelta(days=14)).isoformat()
                po["delay_reason"] = "API Customs Clearance Delay (14 Days)"

    pos = [FactPurchaseOrder(**r) for r in raw_pos]

    # Run MRP
    summary = run_mrp_for_production_schedule(
        production_orders=prod_orders,
        bom_records=bom_records,
        inventory_lots=lots,
        purchase_orders=pos,
        as_of_date=as_of,
        plant_location_id=plant_location_id,
        scenario_id=scenario_id
    )

    # Serialize to Pydantic FactMaterialRequirement instances
    pydantic_requirements: List[FactMaterialRequirement] = []
    for r in summary.netting_results:
        pydantic_requirements.append(
            FactMaterialRequirement(
                requirement_id=r.requirement_id,
                production_order_id=r.production_order_id,
                material_sku_id=r.material_sku_id,
                required_quantity=r.gross_requirement,
                required_date=r.need_by_date,
                eligible_available_quantity=r.eligible_available_quantity,
                expected_receipt_quantity=r.expected_receipt_quantity,
                shortage_quantity=r.shortage_quantity,
                scenario_id=scenario_id
            )
        )

    return summary, pydantic_requirements


def export_mrp_to_dataframe(
    mrp_requirements: List[FactMaterialRequirement]
) -> pd.DataFrame:
    """Converts a collection of FactMaterialRequirement models into a structured Pandas DataFrame."""
    records = [r.model_dump() for r in mrp_requirements]
    return pd.DataFrame(records)
