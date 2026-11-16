"""
Pharmaceutical Supplier OTIF & Manufacturing Line Capacity Analytics Engine.
Phase 2 (Day 18) Core Analytics Implementation.

Calculates vendor On-Time In-Full (OTIF) %, lead-time variance distributions,
and manufacturing line capacity utilisation % (net available vs committed production hours).
Strictly zero LLM mathematical calculations.
"""

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import List, Dict, Tuple, Optional, Any, Union
import math
import sqlite3
import pandas as pd

from src.models.master import DimSupplier, DimProductionLine
from src.models.procurement_inventory import FactPurchaseOrder
from src.models.capacity_logistics import FactCapacity
from src.engine.inventory import parse_date


@dataclass(frozen=True)
class PurchaseOrderPerformance:
    """Individual purchase order delivery performance audit record."""
    purchase_order_id: str
    supplier_id: str
    material_sku_id: str
    order_date: date
    confirmed_delivery_date: date
    actual_receipt_date: Optional[date]
    ordered_quantity: float
    received_quantity: float
    promised_lead_time_days: int
    actual_lead_time_days: Optional[int]
    lead_time_variance_days: Optional[int]
    delay_days: int
    is_on_time: bool
    is_in_full: bool
    is_otif: bool
    fill_rate: float
    order_status: str


@dataclass(frozen=True)
class SupplierOTIFScorecard:
    """Executive vendor scorecard measuring fulfillment reliability and sourcing risk."""
    supplier_id: str
    supplier_name: str
    total_orders_evaluated: int
    completed_orders_count: int
    on_time_orders_count: int
    in_full_orders_count: int
    otif_orders_count: int
    on_time_percentage: float
    in_full_percentage: float
    otif_percentage: float
    target_otif_percentage: float
    is_target_met: bool
    mean_lead_time_days: float
    lead_time_variance_days: float
    lead_time_std_dev: float
    max_delay_days: int
    single_source_dependency: bool
    supplier_risk_tier: str  # "Low", "Medium", "High", "Critical"
    order_performances: List[PurchaseOrderPerformance] = field(default_factory=list)


@dataclass(frozen=True)
class WeeklyLineCapacityMetric:
    """Detailed capacity utilization audit for a production line in a single weekly bucket."""
    capacity_record_id: str
    production_line_id: str
    location_id: str
    period_start_date: date
    net_available_hours: float
    maintenance_hours: float
    downtime_hours: float
    committed_hours: float
    idle_available_hours: float
    utilization_rate: float        # committed / net_available (e.g. 1.20)
    utilization_pct: float         # utilization_rate * 100 (e.g. 120.0%)
    is_overloaded: bool            # True if utilization_rate > 1.0
    overload_hours: float          # max(0.0, committed - net_available)
    scenario_id: str = "SCN-BASE"


@dataclass(frozen=True)
class PlantCapacitySummary:
    """Executive summary of plant manufacturing line capacity utilization across horizon."""
    location_id: str
    scenario_id: str
    horizon_weeks: int
    total_net_available_hours: float
    total_committed_hours: float
    average_utilization_pct: float
    peak_utilization_pct: float
    overload_weeks_count: int
    overloaded_line_ids: List[str]
    has_capacity_overload: bool
    weekly_line_metrics: List[WeeklyLineCapacityMetric] = field(default_factory=list)


def evaluate_po_otif_performance(
    po: Any,
    as_of_date: Optional[Union[date, str]] = None
) -> PurchaseOrderPerformance:
    """
    Evaluates On-Time In-Full performance for a single purchase order.

    Rules:
    * On-Time: actual_receipt_date <= confirmed_delivery_date.
      If not yet received, checks if as_of_date > confirmed_delivery_date (flagging open delays).
    * In-Full: received_quantity >= ordered_quantity * 0.999 (0.1% tolerance for bulk weighing variance).
    * OTIF: Both On-Time AND In-Full are True.
    """
    if hasattr(po, "model_dump"):
        p_dict = po.model_dump()
    elif isinstance(po, dict):
        p_dict = po
    else:
        p_dict = {
            "purchase_order_id": getattr(po, "purchase_order_id"),
            "supplier_id": getattr(po, "supplier_id"),
            "material_sku_id": getattr(po, "material_sku_id"),
            "order_date": getattr(po, "order_date"),
            "confirmed_delivery_date": getattr(po, "confirmed_delivery_date"),
            "actual_receipt_date": getattr(po, "actual_receipt_date", None),
            "ordered_quantity": getattr(po, "ordered_quantity"),
            "received_quantity": getattr(po, "received_quantity", 0.0),
            "purchase_order_status": getattr(po, "purchase_order_status", "Open")
        }

    ord_date = parse_date(p_dict["order_date"])
    conf_date = parse_date(p_dict["confirmed_delivery_date"])
    rec_date = parse_date(p_dict["actual_receipt_date"]) if p_dict.get("actual_receipt_date") else None
    as_of = parse_date(as_of_date) if as_of_date else date.today()

    ord_qty = float(p_dict["ordered_quantity"])
    rec_qty = float(p_dict.get("received_quantity", 0.0))
    status = p_dict.get("purchase_order_status", "Open")

    promised_lt = (conf_date - ord_date).days

    if rec_date is not None:
        actual_lt = (rec_date - ord_date).days
        lt_var = actual_lt - promised_lt
        delay_days = max(0, (rec_date - conf_date).days)
        is_ot = (rec_date <= conf_date)
        is_if = (rec_qty >= ord_qty * 0.999)
    else:
        # Open / In-transit PO
        actual_lt = None
        lt_var = None
        if as_of > conf_date:
            delay_days = (as_of - conf_date).days
            is_ot = False  # Past promised date without delivery
        else:
            delay_days = 0
            is_ot = True  # Not yet due
        is_if = False if status == "Received" else (rec_qty >= ord_qty * 0.999)

    is_otif = (is_ot and is_if)
    fill_rate = round(rec_qty / ord_qty, 4) if ord_qty > 0 else 0.0

    return PurchaseOrderPerformance(
        purchase_order_id=p_dict["purchase_order_id"],
        supplier_id=p_dict["supplier_id"],
        material_sku_id=p_dict["material_sku_id"],
        order_date=ord_date,
        confirmed_delivery_date=conf_date,
        actual_receipt_date=rec_date,
        ordered_quantity=ord_qty,
        received_quantity=rec_qty,
        promised_lead_time_days=promised_lt,
        actual_lead_time_days=actual_lt,
        lead_time_variance_days=lt_var,
        delay_days=delay_days,
        is_on_time=is_ot,
        is_in_full=is_if,
        is_otif=is_otif,
        fill_rate=fill_rate,
        order_status=status
    )


def calculate_supplier_otif_metrics(
    purchase_orders: List[Any],
    supplier_id: str,
    supplier_name: str = "Vendor",
    target_otif: float = 95.0,
    single_source_dependency: bool = False,
    as_of_date: Optional[Union[date, str]] = None
) -> SupplierOTIFScorecard:
    """
    Computes vendor On-Time In-Full (OTIF) %, lead time distributions,
    and assigns an executive risk tier.
    """
    po_perfs = [
        evaluate_po_otif_performance(po, as_of_date=as_of_date)
        for po in purchase_orders
        if (getattr(po, "supplier_id", None) or (isinstance(po, dict) and po.get("supplier_id"))) == supplier_id
    ]

    total_orders = len(po_perfs)
    if total_orders == 0:
        return SupplierOTIFScorecard(
            supplier_id=supplier_id,
            supplier_name=supplier_name,
            total_orders_evaluated=0,
            completed_orders_count=0,
            on_time_orders_count=0,
            in_full_orders_count=0,
            otif_orders_count=0,
            on_time_percentage=100.0,
            in_full_percentage=100.0,
            otif_percentage=100.0,
            target_otif_percentage=target_otif,
            is_target_met=True,
            mean_lead_time_days=0.0,
            lead_time_variance_days=0.0,
            lead_time_std_dev=0.0,
            max_delay_days=0,
            single_source_dependency=single_source_dependency,
            supplier_risk_tier="Low"
        )

    # For metrics, prioritize orders that have reached delivery or breached promised date
    completed_or_due = [p for p in po_perfs if p.actual_receipt_date is not None or p.delay_days > 0]
    eval_set = completed_or_due if completed_or_due else po_perfs
    eval_count = len(eval_set)

    on_time_count = sum(1 for p in eval_set if p.is_on_time)
    in_full_count = sum(1 for p in eval_set if p.is_in_full)
    otif_count = sum(1 for p in eval_set if p.is_otif)

    on_time_pct = round((on_time_count / eval_count) * 100.0, 2)
    in_full_pct = round((in_full_count / eval_count) * 100.0, 2)
    otif_pct = round((otif_count / eval_count) * 100.0, 2)

    # Lead time statistics
    completed_lead_times = [p.actual_lead_time_days for p in po_perfs if p.actual_lead_time_days is not None]
    if completed_lead_times:
        mean_lt = round(sum(completed_lead_times) / len(completed_lead_times), 2)
        variance = round(sum((x - mean_lt) ** 2 for x in completed_lead_times) / len(completed_lead_times), 2)
        std_dev = round(math.sqrt(variance), 2)
    else:
        # Fall back to promised lead times
        promised_lts = [p.promised_lead_time_days for p in po_perfs]
        mean_lt = round(sum(promised_lts) / len(promised_lts), 2) if promised_lts else 0.0
        variance = 0.0
        std_dev = 0.0

    max_delay = max([p.delay_days for p in po_perfs], default=0)
    target_met = (otif_pct >= target_otif)

    # Risk tier determination
    if otif_pct < 80.0 or (single_source_dependency and otif_pct < target_otif):
        tier = "Critical" if single_source_dependency else "High"
    elif otif_pct < target_otif or single_source_dependency:
        tier = "Medium"
    else:
        tier = "Low"

    return SupplierOTIFScorecard(
        supplier_id=supplier_id,
        supplier_name=supplier_name,
        total_orders_evaluated=total_orders,
        completed_orders_count=len(completed_or_due),
        on_time_orders_count=on_time_count,
        in_full_orders_count=in_full_count,
        otif_orders_count=otif_count,
        on_time_percentage=on_time_pct,
        in_full_percentage=in_full_pct,
        otif_percentage=otif_pct,
        target_otif_percentage=target_otif,
        is_target_met=target_met,
        mean_lead_time_days=mean_lt,
        lead_time_variance_days=variance,
        lead_time_std_dev=std_dev,
        max_delay_days=max_delay,
        single_source_dependency=single_source_dependency,
        supplier_risk_tier=tier,
        order_performances=po_perfs
    )


def calculate_line_capacity_metrics(
    capacity_records: List[Any],
    location_id: str = "LOC-PLANT-01",
    scenario_id: str = "SCN-BASE"
) -> PlantCapacitySummary:
    """
    Computes plant manufacturing line utilization metrics, detects overloads,
    and identifies bottleneck production lines.
    """
    metrics: List[WeeklyLineCapacityMetric] = []
    tot_net_avail = 0.0
    tot_committed = 0.0
    peak_util = 0.0
    overload_count = 0
    overloaded_lines = set()

    for cap in capacity_records:
        if hasattr(cap, "model_dump"):
            c_dict = cap.model_dump()
        elif isinstance(cap, dict):
            c_dict = cap
        else:
            c_dict = {
                "capacity_record_id": getattr(cap, "capacity_record_id"),
                "production_line_id": getattr(cap, "production_line_id"),
                "location_id": getattr(cap, "location_id"),
                "period_start_date": getattr(cap, "period_start_date"),
                "net_available_hours": getattr(cap, "net_available_hours"),
                "maintenance_hours": getattr(cap, "maintenance_hours", 0.0),
                "downtime_hours": getattr(cap, "downtime_hours", 0.0),
                "committed_hours": getattr(cap, "committed_hours", 0.0),
                "scenario_id": getattr(cap, "scenario_id", scenario_id)
            }

        net_avail = float(c_dict["net_available_hours"])
        committed = float(c_dict.get("committed_hours", 0.0))
        maint = float(c_dict.get("maintenance_hours", 0.0))
        downtime = float(c_dict.get("downtime_hours", 0.0))

        tot_net_avail += net_avail
        tot_committed += committed

        util_rate = round(committed / net_avail, 4) if net_avail > 0 else 0.0
        util_pct = round(util_rate * 100.0, 2)

        if util_pct > peak_util:
            peak_util = util_pct

        is_over = (util_rate > 1.0)
        over_hrs = max(0.0, round(committed - net_avail, 2))
        idle_hrs = max(0.0, round(net_avail - committed, 2))

        if is_over:
            overload_count += 1
            overloaded_lines.add(c_dict["production_line_id"])

        m = WeeklyLineCapacityMetric(
            capacity_record_id=c_dict["capacity_record_id"],
            production_line_id=c_dict["production_line_id"],
            location_id=c_dict["location_id"],
            period_start_date=parse_date(c_dict["period_start_date"]),
            net_available_hours=net_avail,
            maintenance_hours=maint,
            downtime_hours=downtime,
            committed_hours=committed,
            idle_available_hours=idle_hrs,
            utilization_rate=util_rate,
            utilization_pct=util_pct,
            is_overloaded=is_over,
            overload_hours=over_hrs,
            scenario_id=c_dict.get("scenario_id", scenario_id)
        )
        metrics.append(m)

    avg_util = round((tot_committed / tot_net_avail) * 100.0, 2) if tot_net_avail > 0 else 0.0

    # Sort metrics chronologically by period_start_date, then production_line_id
    sorted_metrics = sorted(metrics, key=lambda x: (x.period_start_date, x.production_line_id))
    unique_weeks = len(set(m.period_start_date for m in sorted_metrics))

    return PlantCapacitySummary(
        location_id=location_id,
        scenario_id=scenario_id,
        horizon_weeks=unique_weeks,
        total_net_available_hours=round(tot_net_avail, 2),
        total_committed_hours=round(tot_committed, 2),
        average_utilization_pct=avg_util,
        peak_utilization_pct=peak_util,
        overload_weeks_count=overload_count,
        overloaded_line_ids=sorted(list(overloaded_lines)),
        has_capacity_overload=(overload_count > 0),
        weekly_line_metrics=sorted_metrics
    )


def detect_capacity_bottlenecks(
    capacity_records: List[Any],
    overload_threshold_pct: float = 100.0
) -> List[WeeklyLineCapacityMetric]:
    """
    Filters and returns capacity records where utilization exceeds threshold.
    Default threshold = 100.0% (strict overload); can be set to 85.0% for early-warning buffer alert.
    """
    summary = calculate_line_capacity_metrics(capacity_records)
    bottlenecks = [m for m in summary.weekly_line_metrics if m.utilization_pct >= overload_threshold_pct]
    return sorted(bottlenecks, key=lambda x: (-x.utilization_pct, x.period_start_date))


def evaluate_capacity_conflict_scenario_e(
    capacity_records: List[Any],
    target_line_id: str = "LINE-PLANT1-01",
    target_week_start: Union[date, str] = "2026-11-09",
    additional_committed_hours: float = 90.0,
    parallel_line_id: str = "LINE-PLANT1-02"
) -> Dict[str, Any]:
    """
    Models Benchmark Scenario E (Capacity Conflict & Production Reschedule):
    Injects surge production hours onto target_line_id during target_week_start,
    measuring resulting overload deficit and evaluating offload feasibility to parallel_line_id.
    """
    target_date = parse_date(target_week_start)

    # 1. Baseline analysis
    base_summary = calculate_line_capacity_metrics(capacity_records, scenario_id="SCN-BASE")

    # 2. Inject surge hours into deep-copied records
    disrupted_records = []
    parallel_idle_hours = 0.0

    for r in capacity_records:
        r_dict = r.model_dump() if hasattr(r, "model_dump") else dict(r)
        c_date = parse_date(r_dict["period_start_date"])

        if r_dict["production_line_id"] == target_line_id and c_date == target_date:
            r_dict["committed_hours"] = float(r_dict.get("committed_hours", 0.0)) + additional_committed_hours
            r_dict["scenario_id"] = "SCN-E-CAPACITY-CONFLICT"

        if r_dict["production_line_id"] == parallel_line_id and c_date == target_date:
            avail = float(r_dict["net_available_hours"])
            comm = float(r_dict.get("committed_hours", 0.0))
            parallel_idle_hours = max(0.0, avail - comm)

        disrupted_records.append(r_dict)

    disrupted_summary = calculate_line_capacity_metrics(disrupted_records, scenario_id="SCN-E-CAPACITY-CONFLICT")

    target_metric = next(
        m for m in disrupted_summary.weekly_line_metrics
        if m.production_line_id == target_line_id and m.period_start_date == target_date
    )

    can_offload = (parallel_idle_hours >= target_metric.overload_hours)

    return {
        "scenario_id": "SCN-E-CAPACITY-CONFLICT",
        "target_line_id": target_line_id,
        "target_week": target_date.isoformat(),
        "baseline_committed_hours": base_summary.total_committed_hours,
        "new_committed_hours": target_metric.committed_hours,
        "net_available_hours": target_metric.net_available_hours,
        "utilization_pct": target_metric.utilization_pct,
        "is_overloaded": target_metric.is_overloaded,
        "overload_hours": target_metric.overload_hours,
        "parallel_line_id": parallel_line_id,
        "parallel_line_idle_hours": parallel_idle_hours,
        "can_offload_to_parallel_line": can_offload,
        "recommended_action": (
            f"Reschedule {target_metric.overload_hours} hours to parallel line {parallel_line_id}"
            if can_offload else "Activate overtime / weekend shift at formulation plant"
        )
    }


def generate_supplier_analytics_from_database(
    db_conn: sqlite3.Connection
) -> Dict[str, SupplierOTIFScorecard]:
    """Queries SQLite database to generate comprehensive OTIF scorecards for all suppliers."""
    supp_df = pd.read_sql_query("SELECT * FROM dim_supplier", db_conn)
    po_df = pd.read_sql_query("SELECT * FROM fact_purchase_order", db_conn)

    scorecards: Dict[str, SupplierOTIFScorecard] = {}
    for _, s_row in supp_df.iterrows():
        s_id = s_row["supplier_id"]
        s_name = s_row["supplier_name"]
        target = float(s_row.get("otif_target", 95.0))
        single_source = bool(s_row.get("single_source_dependency_flag", False))

        card = calculate_supplier_otif_metrics(
            purchase_orders=po_df.to_dict(orient="records"),
            supplier_id=s_id,
            supplier_name=s_name,
            target_otif=target,
            single_source_dependency=single_source
        )
        scorecards[s_id] = card

    return scorecards


def generate_capacity_analytics_from_database(
    db_conn: sqlite3.Connection,
    location_id: str = "LOC-PLANT-01",
    scenario_id: str = "SCN-BASE"
) -> PlantCapacitySummary:
    """Queries fact_capacity from SQLite database to calculate complete plant capacity summary."""
    cap_df = pd.read_sql_query(
        "SELECT * FROM fact_capacity WHERE location_id = ? AND scenario_id = ?",
        db_conn,
        params=[location_id, scenario_id]
    )
    return calculate_line_capacity_metrics(
        capacity_records=cap_df.to_dict(orient="records"),
        location_id=location_id,
        scenario_id=scenario_id
    )


def export_analytics_to_dataframes(
    supplier_scorecards: Dict[str, SupplierOTIFScorecard],
    plant_capacity: PlantCapacitySummary
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Converts scorecards and capacity metrics into Pandas DataFrames for reporting and dashboard rendering."""
    # 1. Supplier Scorecard DataFrame
    supp_rows = []
    for s_id, card in supplier_scorecards.items():
        supp_rows.append({
            "supplier_id": card.supplier_id,
            "supplier_name": card.supplier_name,
            "total_orders": card.total_orders_evaluated,
            "on_time_pct": card.on_time_percentage,
            "in_full_pct": card.in_full_percentage,
            "otif_pct": card.otif_percentage,
            "target_otif": card.target_otif_percentage,
            "is_target_met": card.is_target_met,
            "mean_lead_time_days": card.mean_lead_time_days,
            "lead_time_std_dev": card.lead_time_std_dev,
            "max_delay_days": card.max_delay_days,
            "single_source": card.single_source_dependency,
            "risk_tier": card.supplier_risk_tier
        })
    df_supp = pd.DataFrame(supp_rows)

    # 2. Line Capacity DataFrame
    cap_rows = []
    for m in plant_capacity.weekly_line_metrics:
        cap_rows.append({
            "capacity_record_id": m.capacity_record_id,
            "production_line_id": m.production_line_id,
            "period_start_date": m.period_start_date,
            "net_available_hours": m.net_available_hours,
            "committed_hours": m.committed_hours,
            "idle_available_hours": m.idle_available_hours,
            "utilization_pct": m.utilization_pct,
            "is_overloaded": m.is_overloaded,
            "overload_hours": m.overload_hours,
            "scenario_id": m.scenario_id
        })
    df_cap = pd.DataFrame(cap_rows)

    return df_supp, df_cap
