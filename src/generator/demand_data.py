"""
Historical Demand & Forward Forecast Synthesizer.
Synthetic Data Generation Engine — Week 03, Day 11 Deliverable.

Generates:
1. 104 weeks of historical weekly market demand baseline (416 records across 2 SKUs and 2 markets).
   Models baseline volume, annual trend growth, monsoon/respiratory seasonality, holiday events,
   controlled Gaussian noise, and historical stockout / lost sales.
2. 26 weeks of future demand forecasts (104 records) with P10/P90 prediction intervals,
   expanding horizon uncertainty, and strict anti-leakage temporal guards.
3. Active customer purchase orders (32 records) across commercial customer accounts.
"""

import datetime
import math
from typing import Dict, List, Optional, Tuple
import numpy as np

from src.generator.config import GeneratorConfig
from src.models.demand import FactDemandHistory, FactCustomerOrder, DemandEventType, CustomerOrderStatus
from src.models.planning import FactDemandForecast


# Baseline weekly demand parameters (packs/week per SKU-Market pairing)
DEFAULT_BASE_DEMANDS: Dict[Tuple[str, str], float] = {
    ("SKU-AUG-500-T10", "MKT-IN-HYD"): 3500.0,
    ("SKU-AUG-500-T10", "MKT-IN-PUN"): 3000.0,
    ("SKU-AUG-500-T30", "MKT-IN-HYD"): 1800.0,
    ("SKU-AUG-500-T30", "MKT-IN-PUN"): 1500.0,
}

SKUS: List[str] = ["SKU-AUG-500-T10", "SKU-AUG-500-T30"]
MARKETS: List[str] = ["MKT-IN-HYD", "MKT-IN-PUN"]

CUSTOMER_MAPPING: Dict[str, List[str]] = {
    "MKT-IN-HYD": ["CUST-001", "CUST-002"],
    "MKT-IN-PUN": ["CUST-003", "CUST-004"]
}


def calculate_trend_factor(week_index: int, annual_growth_rate: float = 0.05) -> float:
    """Calculates linear trend growth over 52-week cycles."""
    return 1.0 + (annual_growth_rate * (week_index / 52.0))


def calculate_seasonality_factor(week_date: datetime.date, amplitude: float = 0.25) -> float:
    """
    Calculates respiratory/monsoon seasonality factor based on ISO calendar week.
    In India, antibiotic demand peaks in late monsoon / post-monsoon (Weeks 28-36).
    """
    week_of_year = week_date.isocalendar()[1]
    return 1.0 + amplitude * math.sin(2.0 * math.pi * (week_of_year - 15) / 52.0)


def generate_demand_history(
    config: GeneratorConfig,
    base_demands: Optional[Dict[Tuple[str, str], float]] = None
) -> List[FactDemandHistory]:
    """
    Generates 104 weeks of weekly historical demand data.
    Enforces demand conservation: lost_sales = demand - fulfilled.
    """
    if base_demands is None:
        base_demands = DEFAULT_BASE_DEMANDS

    rng = np.random.RandomState(config.random_seed)
    demand_history: List[FactDemandHistory] = []
    start_date = config.history_start_date

    for week_idx in range(config.history_weeks):
        week_date = start_date + datetime.timedelta(weeks=week_idx)
        trend = calculate_trend_factor(week_idx, annual_growth_rate=0.05)
        seasonality = calculate_seasonality_factor(week_date, amplitude=0.25)
        week_of_year = week_date.isocalendar()[1]

        for sku in SKUS:
            for market in MARKETS:
                base = base_demands[(sku, market)]

                # Controlled Gaussian noise +/- 8%
                noise = rng.normal(0, 0.08 * base)

                # Public health epidemiological and holiday adjustments
                event_type = "Normal"
                event_mult = 1.0
                if week_of_year in [32, 33]:
                    event_type = "Monsoon_Respiratory_Surge"
                    event_mult = 1.18
                elif week_of_year in [43, 44]:
                    event_type = "Diwali_Holiday_Adjustment"
                    event_mult = 0.90

                nominal_demand = (base * trend * seasonality * event_mult) + noise
                total_demand = max(500.0, nominal_demand)
                fulfilled = total_demand
                lost_sales = 0.0

                # Synthetic historical packaging bottleneck in Week 48 (T10 strip in Hyderabad)
                if week_idx == 48 and sku == "SKU-AUG-500-T10" and market == "MKT-IN-HYD":
                    fulfilled = total_demand * 0.88
                    lost_sales = total_demand - fulfilled
                    event_type = "Historical_Packaging_Bottleneck"

                demand_history.append(
                    FactDemandHistory(
                        week_start_date=week_date,
                        finished_sku_id=sku,
                        market_id=market,
                        demand_quantity=round(total_demand, 0),
                        fulfilled_quantity=round(fulfilled, 0),
                        lost_sales_quantity=round(lost_sales, 0),
                        event_type=event_type,
                        scenario_id="SCN-BASE",
                        synthetic_data_flag=config.synthetic_flag
                    )
                )

    return demand_history


def generate_demand_forecast(
    config: GeneratorConfig,
    base_demands: Optional[Dict[Tuple[str, str], float]] = None
) -> List[FactDemandForecast]:
    """
    Generates 26 forward weeks of probabilistic demand forecasts.
    Enforces anti-leakage invariant: target_week >= forecast_version_date.
    P10/P90 prediction intervals expand over forecast horizon.
    """
    if base_demands is None:
        base_demands = DEFAULT_BASE_DEMANDS

    forecast_records: List[FactDemandForecast] = []
    as_of_date = config.planning_as_of_date

    for week_idx in range(config.future_weeks):
        target_week = as_of_date + datetime.timedelta(weeks=week_idx)
        abs_week_idx = config.history_weeks + week_idx

        trend = calculate_trend_factor(abs_week_idx, annual_growth_rate=0.05)
        seasonality = calculate_seasonality_factor(target_week, amplitude=0.25)

        for sku in SKUS:
            for market in MARKETS:
                base = base_demands[(sku, market)]
                expected_demand = base * trend * seasonality

                # Prediction intervals widen with forecast horizon (5% at week 1 up to 18% at week 26)
                horizon_uncertainty = 0.05 + 0.13 * (week_idx / float(config.future_weeks))
                lower_bound = max(0.0, expected_demand * (1.0 - horizon_uncertainty))
                upper_bound = expected_demand * (1.0 + horizon_uncertainty)

                fcst_id = f"FCST-{as_of_date.strftime('%Y%m%d')}-{sku}-{market}-W{week_idx+1:02d}"
                forecast_records.append(
                    FactDemandForecast(
                        forecast_id=fcst_id,
                        forecast_version_date=as_of_date,
                        target_week=target_week,
                        finished_sku_id=sku,
                        market_id=market,
                        forecast_quantity=round(expected_demand, 0),
                        lower_bound=round(lower_bound, 0),
                        upper_bound=round(upper_bound, 0),
                        override_quantity=None,
                        model_version="Ensemble-HoltWinters-Ridge-v1.0",
                        scenario_id="SCN-BASE"
                    )
                )

    return forecast_records


def generate_customer_orders(config: GeneratorConfig) -> List[FactCustomerOrder]:
    """
    Generates active customer purchase order lines across commercial accounts.
    Enforces milestone chronology: requested_date >= order_date, promised_date >= order_date.
    """
    customer_orders: List[FactCustomerOrder] = []
    as_of_date = config.planning_as_of_date
    order_id_counter = 1001

    for offset_days in [0, 3, 7, 10]:
        order_date = as_of_date + datetime.timedelta(days=offset_days)
        req_date = order_date + datetime.timedelta(days=4)
        prom_date = req_date

        for market, custs in CUSTOMER_MAPPING.items():
            for cust in custs:
                for sku in SKUS:
                    ordered_qty = 1500.0 if "T10" in sku else 800.0
                    customer_orders.append(
                        FactCustomerOrder(
                            customer_order_id=f"ORD-2026-{order_id_counter}",
                            customer_id=cust,
                            market_id=market,
                            finished_sku_id=sku,
                            order_date=order_date,
                            requested_delivery_date=req_date,
                            promised_delivery_date=prom_date,
                            ordered_quantity=ordered_qty,
                            fulfilled_quantity=0.0,
                            outstanding_quantity=ordered_qty,
                            order_status=CustomerOrderStatus.OPEN.value
                        )
                    )
                    order_id_counter += 1

    return customer_orders


def generate_demand_and_forecast_data(
    config: Optional[GeneratorConfig] = None
) -> Dict[str, list]:
    """
    Main demand generator entry point for Week 03, Day 11.
    Initializes fixed random seed and produces all validated demand history,
    forward forecast, and active customer order Pydantic v2 records.
    """
    if config is None:
        config = GeneratorConfig()

    return {
        "fact_demand_history": generate_demand_history(config),
        "fact_demand_forecast": generate_demand_forecast(config),
        "fact_customer_order": generate_customer_orders(config)
    }
