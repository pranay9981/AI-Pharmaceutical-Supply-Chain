"""
Multi-Echelon Weekly Inventory Projection Engine.
Phase 2 (Day 16) Core Analytics Implementation.

Calculates forward recursive inventory balances:
I_t = I_{t-1} + Receipts_t + Production_t - Demand_t
Tracks projected stockouts, safety stock breaches, days of supply (DOS),
and unmet patient demand across all network echelons.
Strictly zero LLM mathematical calculations.
"""

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import List, Dict, Tuple, Optional, Any, Union
import sqlite3
import pandas as pd

from src.models.planning import FactInventoryProjection
from src.engine.inventory import (
    load_lots_from_database,
    evaluate_lot_eligibility,
    extract_lot_attributes,
    parse_date
)


@dataclass(frozen=True)
class WeeklyProjectionBucket:
    """Calculated inventory balance and risk metrics for a single weekly planning bucket."""
    week_index: int
    week_start_date: date
    opening_inventory: float
    planned_receipts: float
    planned_production: float
    forecast_demand: float
    net_change: float
    projected_ending_inventory: float  # Cumulative net inventory position (can go negative)
    physical_ending_inventory: float   # Bounded on-hand stock: max(0.0, projected_ending_inventory)
    safety_stock: float
    projected_shortage: float          # max(0.0, -projected_ending_inventory)
    unmet_demand: float                # New deficit incurred specifically in this bucket
    is_stockout: bool                  # True if projected_ending_inventory < 0
    is_safety_stock_breach: bool       # True if 0 <= projected_ending_inventory < safety_stock
    weeks_of_supply: float             # Forward demand coverage in weeks
    days_of_supply: float              # weeks_of_supply * 7


@dataclass(frozen=True)
class ProjectionTrajectorySummary:
    """Executive summary of a forward inventory projection trajectory across the planning horizon."""
    item_id: str
    location_id: str
    scenario_id: str
    horizon_weeks: int
    as_of_date: date
    initial_opening_inventory: float
    total_planned_receipts: float
    total_planned_production: float
    total_forecast_demand: float
    net_total_change: float
    final_projected_inventory: float
    minimum_projected_inventory: float
    maximum_projected_inventory: float
    safety_stock: float
    stockout_weeks_count: int
    safety_stock_breach_weeks_count: int
    first_stockout_week_date: Optional[date]
    first_stockout_week_index: Optional[int]
    first_safety_stock_breach_date: Optional[date]
    first_safety_stock_breach_index: Optional[int]
    total_projected_shortage: float
    runway_days_to_stockout: Optional[float]
    runway_days_to_breach: Optional[float]
    weekly_buckets: List[WeeklyProjectionBucket] = field(default_factory=list)


def calculate_weeks_of_supply(
    current_inventory: float,
    remaining_demands: List[float]
) -> float:
    """
    Computes exact forward-looking Weeks of Supply (WOS).
    Simulates forward weekly consumption of current_inventory against actual forward demand buckets.
    """
    if current_inventory <= 0.0 or not remaining_demands:
        return 0.0

    inv = current_inventory
    full_weeks = 0.0

    for demand in remaining_demands:
        if demand <= 0.0:
            full_weeks += 1.0
            continue
        if inv >= demand:
            inv -= demand
            full_weeks += 1.0
        else:
            # Fractional week coverage
            fraction = inv / demand
            full_weeks += fraction
            inv = 0.0
            break

    # If inventory still remains beyond horizon, extrapolate using horizon average weekly demand
    if inv > 0.0 and remaining_demands:
        avg_demand = sum(remaining_demands) / len(remaining_demands)
        if avg_demand > 0.0:
            full_weeks += (inv / avg_demand)

    return round(full_weeks, 2)


def calculate_inventory_projection(
    initial_inventory: float,
    weekly_demands: List[float],
    weekly_receipts: Optional[List[float]] = None,
    weekly_productions: Optional[List[float]] = None,
    safety_stock: float = 0.0,
    start_date: Union[date, str] = "2026-10-26",
    item_id: str = "SKU-AUG-500-T10",
    location_id: str = "LOC-DC-01",
    scenario_id: str = "SCN-BASE"
) -> ProjectionTrajectorySummary:
    """
    Executes the deterministic weekly recursive inventory projection:
    I_t = I_{t-1} + Receipts_t + Production_t - Demand_t

    Guarantees 100% mathematical conservation:
    Ending Inventory - Opening Inventory = Total Inflows - Total Outflows.
    """
    horizon = len(weekly_demands)
    if horizon == 0:
        raise ValueError("weekly_demands must contain at least 1 planning period")

    # Default missing inflow lists to zero
    receipts = [0.0] * horizon if weekly_receipts is None else list(weekly_receipts)
    productions = [0.0] * horizon if weekly_productions is None else list(weekly_productions)

    if len(receipts) != horizon:
        raise ValueError(f"weekly_receipts length ({len(receipts)}) does not match demands ({horizon})")
    if len(productions) != horizon:
        raise ValueError(f"weekly_productions length ({len(productions)}) does not match demands ({horizon})")

    base_date = parse_date(start_date)

    buckets: List[WeeklyProjectionBucket] = []
    current_open = initial_inventory

    stockout_count = 0
    breach_count = 0
    first_stockout_date: Optional[date] = None
    first_stockout_idx: Optional[int] = None
    first_breach_date: Optional[date] = None
    first_breach_idx: Optional[int] = None
    total_shortage = 0.0

    min_inv = initial_inventory
    max_inv = initial_inventory

    for t in range(horizon):
        week_date = base_date + timedelta(weeks=t)
        dem = float(weekly_demands[t])
        rec = float(receipts[t])
        prd = float(productions[t])

        net_delta = rec + prd - dem
        ending_inv = round(current_open + net_delta, 4)

        if ending_inv < min_inv:
            min_inv = ending_inv
        if ending_inv > max_inv:
            max_inv = ending_inv

        # Physical on-hand stock is bounded at zero (cannot be physically negative)
        physical_inv = max(0.0, ending_inv)

        # Shortage and breach detection
        is_so = (ending_inv < 0.0)
        is_breach = (0.0 <= ending_inv < safety_stock)

        shortage = round(max(0.0, -ending_inv), 4) if is_so else 0.0
        # Unmet demand in this specific period
        if is_so:
            if current_open + rec + prd <= 0.0:
                unmet_this_week = dem
            else:
                unmet_this_week = max(0.0, dem - (current_open + rec + prd))
        else:
            unmet_this_week = 0.0

        if is_so:
            stockout_count += 1
            if first_stockout_date is None:
                first_stockout_date = week_date
                first_stockout_idx = t
            total_shortage = shortage

        if is_breach:
            breach_count += 1
            if first_breach_date is None:
                first_breach_date = week_date
                first_breach_idx = t

        # Calculate forward coverage
        future_demands = weekly_demands[t:]
        wos = calculate_weeks_of_supply(physical_inv, future_demands)
        dos = round(wos * 7.0, 1)

        bucket = WeeklyProjectionBucket(
            week_index=t,
            week_start_date=week_date,
            opening_inventory=current_open,
            planned_receipts=rec,
            planned_production=prd,
            forecast_demand=dem,
            net_change=net_delta,
            projected_ending_inventory=ending_inv,
            physical_ending_inventory=physical_inv,
            safety_stock=safety_stock,
            projected_shortage=shortage,
            unmet_demand=round(unmet_this_week, 4),
            is_stockout=is_so,
            is_safety_stock_breach=is_breach,
            weeks_of_supply=wos,
            days_of_supply=dos
        )
        buckets.append(bucket)

        # Recursive advance
        current_open = ending_inv

    # Runway calculations
    runway_so: Optional[float] = None
    if first_stockout_date is not None:
        runway_so = float((first_stockout_date - base_date).days)

    runway_breach: Optional[float] = None
    if first_breach_date is not None:
        runway_breach = float((first_breach_date - base_date).days)
    elif first_stockout_date is not None:
        runway_breach = runway_so

    tot_rec = sum(receipts)
    tot_prd = sum(productions)
    tot_dem = sum(weekly_demands)
    final_inv = buckets[-1].projected_ending_inventory if buckets else initial_inventory
    net_tot = tot_rec + tot_prd - tot_dem

    return ProjectionTrajectorySummary(
        item_id=item_id,
        location_id=location_id,
        scenario_id=scenario_id,
        horizon_weeks=horizon,
        as_of_date=base_date,
        initial_opening_inventory=initial_inventory,
        total_planned_receipts=tot_rec,
        total_planned_production=tot_prd,
        total_forecast_demand=tot_dem,
        net_total_change=net_tot,
        final_projected_inventory=final_inv,
        minimum_projected_inventory=min_inv,
        maximum_projected_inventory=max_inv,
        safety_stock=safety_stock,
        stockout_weeks_count=stockout_count,
        safety_stock_breach_weeks_count=breach_count,
        first_stockout_week_date=first_stockout_date,
        first_stockout_week_index=first_stockout_idx,
        first_safety_stock_breach_date=first_breach_date,
        first_safety_stock_breach_index=first_breach_idx,
        total_projected_shortage=total_shortage,
        runway_days_to_stockout=runway_so,
        runway_days_to_breach=runway_breach,
        weekly_buckets=buckets
    )


def generate_projection_from_database(
    db_conn: sqlite3.Connection,
    finished_sku_id: str = "SKU-AUG-500-T10",
    location_id: str = "LOC-DC-01",
    as_of_date: Union[date, str] = "2026-10-26",
    scenario_id: str = "SCN-BASE",
    safety_stock: float = 4000.0,
    min_acceptable_rsl_days: int = 0
) -> Tuple[ProjectionTrajectorySummary, List[FactInventoryProjection]]:
    """
    Constructs a complete forward inventory projection pipeline querying the SQLite database:
    1. Loads current eligible on-hand lots from fact_inventory_lot via FEFO engine.
    2. Aggregates forward 26-week demand forecasts across relevant regional markets.
    3. Integrates planned replenishment from fact_supply_plan / fact_production_order.
    4. Computes trajectory and returns validated FactInventoryProjection Pydantic entities.
    """
    as_of = parse_date(as_of_date)

    # 1. Opening eligible inventory at location
    lots = load_lots_from_database(db_conn, location_id=location_id, item_id=finished_sku_id)
    initial_inventory = 0.0
    for lot in lots:
        eval_res = evaluate_lot_eligibility(
            lot,
            as_of_date=as_of,
            min_acceptable_rsl_days=min_acceptable_rsl_days
        )
        if eval_res.is_eligible:
            initial_inventory += eval_res.available_quantity

    # 2. Query 26 forward forecast weeks
    fc_df = pd.read_sql_query(
        "SELECT target_week, SUM(forecast_quantity) as total_demand "
        "FROM fact_demand_forecast "
        "WHERE finished_sku_id = ? "
        "GROUP BY target_week ORDER BY target_week",
        db_conn,
        params=[finished_sku_id]
    )
    if fc_df.empty:
        raise ValueError(f"No forecast found for SKU {finished_sku_id}")

    target_weeks = [parse_date(w) for w in fc_df["target_week"]]
    weekly_demands = [float(d) for d in fc_df["total_demand"]]
    horizon = len(target_weeks)

    # 3. Query planned supply receipts
    # Query fact_supply_plan for scheduled replenishment into this facility
    sp_df = pd.read_sql_query(
        "SELECT planned_week, planned_quantity "
        "FROM fact_supply_plan "
        "WHERE finished_sku_id = ? AND location_id = ? AND scenario_id = ?",
        db_conn,
        params=[finished_sku_id, location_id, scenario_id]
    )

    supply_by_week: Dict[date, float] = {}
    if not sp_df.empty:
        for _, r in sp_df.iterrows():
            p_week = parse_date(r["planned_week"])
            supply_by_week[p_week] = supply_by_week.get(p_week, 0.0) + float(r["planned_quantity"])

    weekly_receipts = [supply_by_week.get(w, 0.0) for w in target_weeks]

    # In baseline Phase 1 single-DC topology, receipts represent replenishment arrivals
    trajectory = calculate_inventory_projection(
        initial_inventory=initial_inventory,
        weekly_demands=weekly_demands,
        weekly_receipts=weekly_receipts,
        weekly_productions=[0.0] * horizon,
        safety_stock=safety_stock,
        start_date=target_weeks[0],
        item_id=finished_sku_id,
        location_id=location_id,
        scenario_id=scenario_id
    )

    # 4. Generate Pydantic FactInventoryProjection entities
    pydantic_projections: List[FactInventoryProjection] = []
    for b in trajectory.weekly_buckets:
        proj_id = f"PRJ-{finished_sku_id}-{location_id}-W{b.week_index:02d}-{scenario_id}"
        pydantic_projections.append(
            FactInventoryProjection(
                projection_id=proj_id,
                item_type="FINISHED_SKU",
                item_id=finished_sku_id,
                location_id=location_id,
                week_start_date=b.week_start_date,
                opening_inventory=b.opening_inventory,
                planned_receipts=b.planned_receipts,
                planned_production=b.planned_production,
                forecast_demand=b.forecast_demand,
                projected_ending_inventory=b.projected_ending_inventory,
                safety_stock=b.safety_stock,
                projected_shortage=b.projected_shortage,
                scenario_id=scenario_id
            )
        )

    return trajectory, pydantic_projections


def compare_projection_scenarios(
    baseline: ProjectionTrajectorySummary,
    disrupted: ProjectionTrajectorySummary
) -> Dict[str, Any]:
    """
    Compares Baseline vs Disrupted projection trajectories (e.g. SCN-BASE vs SCN-A-API-DELAY).
    Quantifies delta stockout weeks, shortage magnitude, and lost runway days.
    """
    delta_stockout_weeks = disrupted.stockout_weeks_count - baseline.stockout_weeks_count
    delta_breach_weeks = disrupted.safety_stock_breach_weeks_count - baseline.safety_stock_breach_weeks_count

    # Calculate peak shortage delta across all planning buckets
    max_shortage_delta = 0.0
    for b, d in zip(baseline.weekly_buckets, disrupted.weekly_buckets):
        diff = d.projected_shortage - b.projected_shortage
        if diff > max_shortage_delta:
            max_shortage_delta = diff

    delta_shortage = max_shortage_delta if max_shortage_delta > 0.0 else (disrupted.total_projected_shortage - baseline.total_projected_shortage)

    runway_loss_days = 0.0
    if baseline.runway_days_to_stockout is not None and disrupted.runway_days_to_stockout is not None:
        runway_loss_days = baseline.runway_days_to_stockout - disrupted.runway_days_to_stockout
    elif baseline.runway_days_to_stockout is None and disrupted.runway_days_to_stockout is not None:
        runway_loss_days = (baseline.horizon_weeks * 7.0) - disrupted.runway_days_to_stockout

    is_severe = (runway_loss_days > 0.0 or delta_stockout_weeks > 0 or max_shortage_delta > 0.0)

    return {
        "item_id": baseline.item_id,
        "location_id": baseline.location_id,
        "baseline_scenario": baseline.scenario_id,
        "disrupted_scenario": disrupted.scenario_id,
        "delta_stockout_weeks": delta_stockout_weeks,
        "delta_safety_stock_breach_weeks": delta_breach_weeks,
        "delta_shortage_units": round(delta_shortage, 2),
        "peak_shortage_delta": round(max_shortage_delta, 2),
        "runway_loss_days": round(runway_loss_days, 1),
        "baseline_first_stockout_date": baseline.first_stockout_week_date.isoformat() if baseline.first_stockout_week_date else None,
        "disrupted_first_stockout_date": disrupted.first_stockout_week_date.isoformat() if disrupted.first_stockout_week_date else None,
        "is_disruption_impact_severe": is_severe
    }


def export_projections_to_dataframe(
    projections: List[FactInventoryProjection]
) -> pd.DataFrame:
    """Converts a collection of FactInventoryProjection models into a structured Pandas DataFrame."""
    records = [p.model_dump() for p in projections]
    return pd.DataFrame(records)
