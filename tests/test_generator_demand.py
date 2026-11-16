"""
Unit tests for 104-Week Historical Demand Generator & Forward Forecasting.
Synthetic Data Generation Engine — Week 03, Day 11 Deliverable.

Verifies:
1. Demand history exact record counts (104 weeks x 2 SKUs x 2 markets = 416 rows).
2. Monday weekly bucket alignments and temporal continuity.
3. Annual trend growth, respiratory/monsoon seasonality, and event spikes.
4. Demand conservation and historical stockout / lost sales recording.
5. 26-week forecast generation (104 rows) with P10/P90 expanding intervals.
6. Anti-leakage temporal guard (target_week >= forecast_version_date).
7. Customer sales orders (32 rows) milestone ordering and customer mapping.
8. Bitwise deterministic seed reproducibility.
"""

import datetime
import pytest
from src.generator.config import GeneratorConfig
from src.generator.demand_data import (
    generate_demand_and_forecast_data,
    generate_demand_history,
    generate_demand_forecast,
    generate_customer_orders,
    calculate_trend_factor,
    calculate_seasonality_factor
)
from src.models.demand import FactDemandHistory, FactCustomerOrder
from src.models.planning import FactDemandForecast


@pytest.fixture
def config():
    return GeneratorConfig(random_seed=20261014, synthetic_flag=True)


def test_demand_history_record_count_and_continuity(config):
    """Verifies 104-week demand history row count, weekly Mondays, and SKU-Market coverage."""
    history = generate_demand_history(config)

    # 104 weeks * 2 SKUs * 2 markets = 416 rows
    assert len(history) == 416

    dates = {r.week_start_date for r in history}
    assert len(dates) == 104

    # Every week_start_date must be a Monday (weekday == 0)
    for d in dates:
        assert d.weekday() == 0, f"Date {d} is not a Monday"

    # Start date = 2024-10-28, end date = 2026-10-19
    sorted_dates = sorted(dates)
    assert sorted_dates[0] == datetime.date(2024, 10, 28)
    assert sorted_dates[-1] == datetime.date(2026, 10, 19)

    # All records are FactDemandHistory instances with positive demand
    for rec in history:
        assert isinstance(rec, FactDemandHistory)
        assert rec.demand_quantity >= 500.0
        assert rec.scenario_id == "SCN-BASE"
        assert rec.synthetic_data_flag is True


def test_demand_trend_and_seasonality_dynamics(config):
    """Verifies mathematical properties of trend growth and monsoon peak seasonality."""
    # Trend factor test
    t_start = calculate_trend_factor(0, annual_growth_rate=0.05)
    t_year1 = calculate_trend_factor(52, annual_growth_rate=0.05)
    t_year2 = calculate_trend_factor(104, annual_growth_rate=0.05)
    assert t_start == 1.00
    assert t_year1 == 1.05
    assert t_year2 == 1.10

    # Seasonality factor test (Week 28 monsoon vs Week 15 baseline)
    date_peak = datetime.date(2025, 7, 14)  # Week 29 (Monsoon peak)
    date_trough = datetime.date(2025, 4, 14)  # Week 16 (Spring)
    s_peak = calculate_seasonality_factor(date_peak)
    s_trough = calculate_seasonality_factor(date_trough)
    assert s_peak > s_trough
    assert s_peak > 1.15

    # Verify actual generated history averages
    history = generate_demand_history(config)
    y1_demand = [r.demand_quantity for r in history if r.week_start_date < datetime.date(2025, 10, 27)]
    y2_demand = [r.demand_quantity for r in history if r.week_start_date >= datetime.date(2025, 10, 27)]
    avg_y1 = sum(y1_demand) / len(y1_demand)
    avg_y2 = sum(y2_demand) / len(y2_demand)

    # Year 2 demand should exceed Year 1 by ~5%
    assert avg_y2 > avg_y1
    growth = (avg_y2 - avg_y1) / avg_y1
    assert 0.03 <= growth <= 0.08


def test_historical_stockout_and_lost_sales_recording(config):
    """Verifies that Week 48 stockout correctly records lost sales and fulfillment deficits."""
    history = generate_demand_history(config)

    # Identify Week 48 event for T10 in Hyderabad
    stockout_records = [
        r for r in history
        if r.finished_sku_id == "SKU-AUG-500-T10"
        and r.market_id == "MKT-IN-HYD"
        and r.event_type == "Historical_Packaging_Bottleneck"
    ]
    assert len(stockout_records) == 1
    sr = stockout_records[0]
    assert sr.lost_sales_quantity > 0.0
    assert sr.fulfilled_quantity < sr.demand_quantity
    assert sr.fulfilled_quantity + sr.lost_sales_quantity == pytest.approx(sr.demand_quantity, abs=1.0)

    # Normal records must have zero lost sales
    normal_records = [r for r in history if r.event_type == "Normal"]
    assert len(normal_records) > 300
    for nr in normal_records:
        assert nr.lost_sales_quantity == 0.0
        assert nr.fulfilled_quantity == nr.demand_quantity


def test_demand_forecast_record_count_and_leakage_guards(config):
    """Verifies 26-week forecast horizon, anti-leakage invariant, and P10/P90 interval expansion."""
    forecasts = generate_demand_forecast(config)

    # 26 weeks * 2 SKUs * 2 markets = 104 rows
    assert len(forecasts) == 104

    target_weeks = {f.target_week for f in forecasts}
    assert len(target_weeks) == 26

    # Verify anti-leakage: target_week >= forecast_version_date
    for f in forecasts:
        assert isinstance(f, FactDemandForecast)
        assert f.target_week >= f.forecast_version_date
        assert f.lower_bound <= f.forecast_quantity <= f.upper_bound
        assert f.model_version == "Ensemble-HoltWinters-Ridge-v1.0"
        assert f.scenario_id == "SCN-BASE"

    # Verify prediction intervals widen over horizon
    # Week 1 vs Week 26
    w1_fcst = next(f for f in forecasts if f.finished_sku_id == "SKU-AUG-500-T10" and f.market_id == "MKT-IN-HYD" and f.target_week == config.planning_as_of_date)
    w26_date = config.planning_as_of_date + datetime.timedelta(weeks=25)
    w26_fcst = next(f for f in forecasts if f.finished_sku_id == "SKU-AUG-500-T10" and f.market_id == "MKT-IN-HYD" and f.target_week == w26_date)

    w1_spread = (w1_fcst.upper_bound - w1_fcst.lower_bound) / w1_fcst.forecast_quantity
    w26_spread = (w26_fcst.upper_bound - w26_fcst.lower_bound) / w26_fcst.forecast_quantity
    assert w26_spread > w1_spread
    assert w1_spread == pytest.approx(0.10, abs=0.02)   # +/- 5% = 10% spread
    assert w26_spread == pytest.approx(0.36, abs=0.04)  # +/- 18% = 36% spread


def test_customer_orders_structure_and_milestones(config):
    """Verifies customer orders count, milestone ordering, and customer account validity."""
    orders = generate_customer_orders(config)

    # 4 order dates * 2 markets * 2 customers * 2 SKUs = 32 orders
    assert len(orders) == 32

    order_ids = [o.customer_order_id for o in orders]
    assert len(order_ids) == len(set(order_ids)), "Duplicate customer_order_id found"

    valid_customers = {"CUST-001", "CUST-002", "CUST-003", "CUST-004"}
    for o in orders:
        assert isinstance(o, FactCustomerOrder)
        assert o.customer_id in valid_customers
        assert o.requested_delivery_date >= o.order_date
        assert o.promised_delivery_date >= o.order_date
        assert o.ordered_quantity > 0.0
        assert o.outstanding_quantity == o.ordered_quantity
        assert o.fulfilled_quantity == 0.0
        assert o.order_status == "Open"


def test_demand_seed_reproducibility(config):
    """Verifies that identical seed produces bitwise identical demand history."""
    h1 = generate_demand_history(config)
    h2 = generate_demand_history(config)

    assert len(h1) == len(h2)
    for r1, r2 in zip(h1, h2):
        assert r1.model_dump() == r2.model_dump()

    # Changing seed should alter Gaussian noise
    config_diff = GeneratorConfig(random_seed=99999999)
    h_diff = generate_demand_history(config_diff)
    diff_count = sum(1 for r1, rd in zip(h1, h_diff) if r1.demand_quantity != rd.demand_quantity)
    assert diff_count > 400
