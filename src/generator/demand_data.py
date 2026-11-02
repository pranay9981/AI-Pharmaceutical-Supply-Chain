import datetime
import math
import numpy as np
from typing import List, Dict
from src.generator.config import GeneratorConfig
from src.models.demand import FactDemandHistory, FactCustomerOrder
from src.models.planning import FactDemandForecast

def generate_demand_and_forecast_data(config: GeneratorConfig) -> Dict[str, list]:
    """Generates 104 weeks of demand history and 26 weeks of future forecasts."""
    
    rng = np.random.RandomState(config.random_seed)
    
    demand_history: List[FactDemandHistory] = []
    forecast_records: List[FactDemandForecast] = []
    customer_orders: List[FactCustomerOrder] = []
    
    skus = ["SKU-AUG-500-T10", "SKU-AUG-500-T30"]
    markets = ["MKT-IN-HYD", "MKT-IN-PUN"]
    
    # Base weekly demand parameters (packs/week)
    base_demands = {
        ("SKU-AUG-500-T10", "MKT-IN-HYD"): 3500.0,
        ("SKU-AUG-500-T10", "MKT-IN-PUN"): 3000.0,
        ("SKU-AUG-500-T30", "MKT-IN-HYD"): 1800.0,
        ("SKU-AUG-500-T30", "MKT-IN-PUN"): 1500.0,
    }
    
    # --- 1. HISTORICAL DEMAND (104 WEEKS) ---
    start_date = config.history_start_date
    for week_idx in range(config.history_weeks):
        week_date = start_date + datetime.timedelta(weeks=week_idx)
        
        # Trend factor: 5% annual growth over 2 years
        trend = 1.0 + (0.05 * (week_idx / 52.0))
        
        # Seasonality: Antibiotics demand peaks in Monsoon / Post-monsoon (Weeks 28-40 each year)
        week_of_year = week_date.isocalendar()[1]
        seasonality = 1.0 + 0.25 * math.sin(2 * math.pi * (week_of_year - 15) / 52.0)
        
        for sku in skus:
            for market in markets:
                base = base_demands[(sku, market)]
                
                # Random variation: Gaussian noise +/- 8%
                noise = rng.normal(0, 0.08 * base)
                
                # Occasional public health antibiotic spike (e.g. week 35)
                event_type = "Normal"
                event_mult = 1.0
                if week_of_year in [32, 33]:
                    event_type = "Monsoon_Respiratory_Surge"
                    event_mult = 1.18
                elif week_of_year in [43, 44]:
                    event_type = "Diwali_Holiday_Adjustment"
                    event_mult = 0.90
                    
                total_demand = max(500.0, (base * trend * seasonality * event_mult) + noise)
                # In history, 99.2% of demand was fulfilled normally
                fulfilled = total_demand
                lost_sales = 0.0
                
                # Synthetic minor historical stockout in week 48
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

    # --- 2. FUTURE DEMAND FORECAST (26 WEEKS) ---
    as_of_date = config.planning_as_of_date
    for week_idx in range(config.future_weeks):
        target_week = as_of_date + datetime.timedelta(weeks=week_idx)
        abs_week_idx = config.history_weeks + week_idx
        
        trend = 1.0 + (0.05 * (abs_week_idx / 52.0))
        week_of_year = target_week.isocalendar()[1]
        seasonality = 1.0 + 0.25 * math.sin(2 * math.pi * (week_of_year - 15) / 52.0)
        
        for sku in skus:
            for market in markets:
                base = base_demands[(sku, market)]
                expected_demand = base * trend * seasonality
                
                # Uncertainty widens with longer forecast horizons (e.g. 5% at week 1 up to 18% at week 26)
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

    # --- 3. CUSTOMER ORDERS (CURRENT & UPCOMING 2 WEEKS) ---
    order_id_counter = 1001
    customer_mapping = {
        "MKT-IN-HYD": ["CUST-001", "CUST-002"],
        "MKT-IN-PUN": ["CUST-003", "CUST-004"]
    }
    
    for offset_days in [0, 3, 7, 10]:
        order_date = as_of_date + datetime.timedelta(days=offset_days)
        req_date = order_date + datetime.timedelta(days=4)
        prom_date = req_date
        
        for market, custs in customer_mapping.items():
            for cust in custs:
                for sku in skus:
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
                            order_status="Open"
                        )
                    )
                    order_id_counter += 1

    return {
        "fact_demand_history": demand_history,
        "fact_demand_forecast": forecast_records,
        "fact_customer_order": customer_orders
    }

