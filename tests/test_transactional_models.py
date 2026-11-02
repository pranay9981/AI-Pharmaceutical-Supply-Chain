"""
Pytest Unit Test Suite for Transactional & Planning Fact Entities (9 Tables).
Technical Verification for Week 02, Day 07 Deliverable.

Tests instantiation, field constraints, temporal logic, mathematical invariants,
and error handling across all 9 transactional/planning fact tables:
1. FactDemandHistory
2. FactCustomerOrder
3. FactDemandForecast
4. FactSupplyPlan
5. FactMaterialRequirement
6. FactInventoryProjection
7. FactPurchaseOrder
8. FactInventoryLot
9. FactMaterialConsumption
"""

from datetime import date
import pytest
from pydantic import ValidationError
from src.models.demand import FactDemandHistory, FactCustomerOrder
from src.models.planning import (
    FactDemandForecast,
    FactSupplyPlan,
    FactMaterialRequirement,
    FactInventoryProjection,
)
from src.models.procurement_inventory import (
    FactPurchaseOrder,
    FactInventoryLot,
    FactMaterialConsumption,
)


def test_fact_demand_history_and_lost_sales():
    # Demand = 3500, Fulfilled = 3000 -> Lost Sales should automatically resolve to 500
    dh = FactDemandHistory(
        week_start_date=date(2026, 11, 2),
        finished_sku_id="SKU-AUG-500-T10",
        market_id="MKT-IN-HYD",
        demand_quantity=3500.0,
        fulfilled_quantity=3000.0
    )
    assert dh.demand_quantity == 3500.0
    assert dh.fulfilled_quantity == 3000.0
    assert dh.lost_sales_quantity == 500.0


def test_fact_customer_order_milestone_validation():
    # Valid order
    order = FactCustomerOrder(
        customer_order_id="ORD-2026-001",
        customer_id="CUST-001",
        market_id="MKT-IN-HYD",
        finished_sku_id="SKU-AUG-500-T10",
        order_date=date(2026, 11, 2),
        requested_delivery_date=date(2026, 11, 6),
        promised_delivery_date=date(2026, 11, 6),
        ordered_quantity=1000.0
    )
    assert order.ordered_quantity == 1000.0

    # Inverted date: requested delivery date earlier than order date
    with pytest.raises(ValidationError):
        FactCustomerOrder(
            customer_order_id="ORD-2026-002",
            customer_id="CUST-001",
            market_id="MKT-IN-HYD",
            finished_sku_id="SKU-AUG-500-T10",
            order_date=date(2026, 11, 2),
            requested_delivery_date=date(2026, 10, 25),  # Invalid!
            promised_delivery_date=date(2026, 11, 6),
            ordered_quantity=1000.0
        )


def test_fact_demand_forecast_data_leakage_and_intervals():
    # Valid forecast
    fc = FactDemandForecast(
        forecast_id="FCST-001",
        forecast_version_date=date(2026, 10, 26),
        target_week=date(2026, 11, 2),
        finished_sku_id="SKU-AUG-500-T10",
        market_id="MKT-IN-HYD",
        forecast_quantity=3500.0,
        lower_bound=3100.0,
        upper_bound=3900.0
    )
    assert fc.forecast_quantity == 3500.0

    # Data Leakage Violation: target_week earlier than forecast_version_date
    with pytest.raises(ValidationError):
        FactDemandForecast(
            forecast_id="FCST-002",
            forecast_version_date=date(2026, 11, 15),
            target_week=date(2026, 11, 2),  # Target is in the past!
            finished_sku_id="SKU-AUG-500-T10",
            market_id="MKT-IN-HYD",
            forecast_quantity=3500.0,
            lower_bound=3100.0,
            upper_bound=3900.0
        )

    # Inverted prediction interval: lower_bound > upper_bound
    with pytest.raises(ValidationError):
        FactDemandForecast(
            forecast_id="FCST-003",
            forecast_version_date=date(2026, 10, 26),
            target_week=date(2026, 11, 2),
            finished_sku_id="SKU-AUG-500-T10",
            market_id="MKT-IN-HYD",
            forecast_quantity=3500.0,
            lower_bound=4200.0,  # Lower exceeds upper!
            upper_bound=3900.0
        )


def test_fact_supply_plan_validation():
    sp = FactSupplyPlan(
        supply_plan_id="SP-001",
        finished_sku_id="SKU-AUG-500-T10",
        location_id="LOC-DC-01",
        planned_week=date(2026, 11, 2),
        planned_quantity=5000.0,
        expected_availability_date=date(2026, 11, 6)
    )
    assert sp.planned_quantity == 5000.0


def test_fact_material_requirement_shortage():
    # Need 500 kg, available 200 kg, incoming 100 kg -> Shortage = 200 kg
    mr = FactMaterialRequirement(
        requirement_id="REQ-001",
        production_order_id="PO-PROD-001",
        material_sku_id="MAT-API-001",
        required_quantity=500.0,
        required_date=date(2026, 11, 9),
        eligible_available_quantity=200.0,
        expected_receipt_quantity=100.0
    )
    assert mr.shortage_quantity == 200.0


def test_fact_inventory_projection_math():
    # Opening: 10000, Receipts: 2000, Prod: 3000, Demand: 18000
    # Ending = 10000 + 2000 + 3000 - 18000 = -3000 -> Shortage = 3000
    ip = FactInventoryProjection(
        projection_id="PRJ-001",
        item_id="SKU-AUG-500-T10",
        location_id="LOC-DC-01",
        week_start_date=date(2026, 11, 2),
        opening_inventory=10000.0,
        planned_receipts=2000.0,
        planned_production=3000.0,
        forecast_demand=18000.0,
        projected_ending_inventory=-3000.0,
        safety_stock=2000.0
    )
    assert ip.projected_ending_inventory == -3000.0
    assert ip.projected_shortage == 3000.0


def test_fact_purchase_order_validation():
    po = FactPurchaseOrder(
        purchase_order_id="PO-2026-001",
        supplier_id="SUP-001",
        material_sku_id="MAT-API-001",
        order_date=date(2026, 10, 1),
        requested_delivery_date=date(2026, 10, 22),
        confirmed_delivery_date=date(2026, 10, 22),
        ordered_quantity=100.0
    )
    assert po.ordered_quantity == 100.0


def test_fact_inventory_lot_expiry_and_reserves():
    # Valid Lot
    lot = FactInventoryLot(
        lot_id="LOT-001",
        item_id="SKU-AUG-500-T10",
        location_id="LOC-DC-01",
        manufacture_date=date(2026, 1, 1),
        expiry_date=date(2028, 1, 1),
        quantity_on_hand=5000.0,
        reserved_quantity=1000.0,
        receipt_date=date(2026, 1, 15)
    )
    assert lot.quantity_on_hand == 5000.0

    # Inverted expiry date (expiry earlier than manufacture date)
    with pytest.raises(ValidationError):
        FactInventoryLot(
            lot_id="LOT-BAD",
            item_id="SKU-AUG-500-T10",
            location_id="LOC-DC-01",
            manufacture_date=date(2026, 1, 1),
            expiry_date=date(2025, 1, 1),  # Expiry in past!
            quantity_on_hand=5000.0,
            receipt_date=date(2026, 1, 15)
        )

    # Reserved exceeds on-hand
    with pytest.raises(ValidationError):
        FactInventoryLot(
            lot_id="LOT-OVERRESERVED",
            item_id="SKU-AUG-500-T10",
            location_id="LOC-DC-01",
            manufacture_date=date(2026, 1, 1),
            expiry_date=date(2028, 1, 1),
            quantity_on_hand=500.0,
            reserved_quantity=1000.0,  # Exceeds physical stock!
            receipt_date=date(2026, 1, 15)
        )


def test_fact_material_consumption_variance():
    # Planned 100 kg, actual dispensed 103 kg -> Variance = +3 kg
    mc = FactMaterialConsumption(
        consumption_id="CONS-001",
        production_order_id="PO-PROD-001",
        material_sku_id="MAT-API-001",
        lot_id="LOT-API-01",
        planned_quantity=100.0,
        actual_quantity=103.0,
        consumption_date=date(2026, 11, 2)
    )
    assert mc.variance_quantity == 3.0

