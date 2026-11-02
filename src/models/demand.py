"""
Demand Transactional Fact Entities (2 Entities).
Technical Specification & Pydantic v2 Schemas for Week 02, Day 07 Deliverable.

Defines:
1. FactDemandHistory (104-week historical market demand baseline)
2. FactCustomerOrder (Customer purchase order lines, requested milestones, and fulfilment)
"""

from datetime import date
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, model_validator


class DemandEventType(str, Enum):
    NORMAL = "Normal"
    HOLIDAY_SPIKE = "Holiday_Spike"
    EPIDEMIC_SURGE = "Epidemic_Surge"
    PROMOTION = "Promotion"


class CustomerOrderStatus(str, Enum):
    OPEN = "Open"
    IN_TRANSIT = "In_Transit"
    DELIVERED = "Delivered"
    SHORT_SHIPPED = "Short_Shipped"
    CANCELLED = "Cancelled"


class FactDemandHistory(BaseModel):
    """
    Historical Demand Fact Entity.
    Grain: One record per Monday week start date, Finished SKU, Market, and Scenario.
    Captures true historical consumption, fulfilled orders, lost sales, and seasonal demand surges.
    """
    week_start_date: date = Field(..., description="Monday weekly planning period start date")
    finished_sku_id: str = Field(..., min_length=3, description="Foreign key to dim_finished_sku.finished_sku_id")
    market_id: str = Field(..., min_length=3, description="Foreign key to dim_market.market_id")
    demand_quantity: float = Field(..., ge=0.0, description="True customer/market demand in sellable packs")
    fulfilled_quantity: float = Field(..., ge=0.0, description="Actual commercial shipments fulfilled against demand")
    lost_sales_quantity: float = Field(default=0.0, ge=0.0, description="Unmet customer demand resulting in stockout")
    event_type: str = Field(default="Normal", description="Normal, Holiday_Spike, Epidemic_Surge, or Promotion")
    scenario_id: str = Field(default="SCN-BASE", description="Baseline or specific disruption scenario identifier")
    synthetic_data_flag: bool = Field(default=True, description="Mandatory synthetic provenance flag")

    @model_validator(mode="after")
    def validate_demand_conservation(self) -> "FactDemandHistory":
        # Lost sales should reflect demand minus fulfillment
        calculated_deficit = max(0.0, round(self.demand_quantity - self.fulfilled_quantity, 4))
        if self.lost_sales_quantity == 0.0 and calculated_deficit > 0:
            self.lost_sales_quantity = calculated_deficit
        return self


class FactCustomerOrder(BaseModel):
    """
    Commercial Sales Order Line Entity.
    Grain: One record per customer order line.
    Captures order placement date, requested vs promised delivery dates, and order status.
    """
    customer_order_id: str = Field(..., min_length=3, description="Unique sales order identifier, e.g. ORD-2026-001")
    customer_id: str = Field(..., min_length=3, description="Foreign key to dim_customer.customer_id")
    market_id: str = Field(..., min_length=3, description="Foreign key to dim_market.market_id")
    finished_sku_id: str = Field(..., min_length=3, description="Foreign key to dim_finished_sku.finished_sku_id")
    order_date: date = Field(..., description="Date customer order was formally registered")
    requested_delivery_date: date = Field(..., description="Customer requested delivery milestone")
    promised_delivery_date: date = Field(..., description="Confirmed promised delivery milestone")
    ordered_quantity: float = Field(..., gt=0.0, description="Quantity ordered in sellable packs")
    fulfilled_quantity: float = Field(default=0.0, ge=0.0, description="Quantity successfully delivered")
    outstanding_quantity: float = Field(default=0.0, ge=0.0, description="Unfulfilled backorder balance")
    order_status: str = Field(default="Open", description="Open, In_Transit, Delivered, Short_Shipped, or Cancelled")

    @model_validator(mode="after")
    def validate_order_milestones(self) -> "FactCustomerOrder":
        if self.requested_delivery_date < self.order_date:
            raise ValueError("requested_delivery_date cannot be earlier than order_date")
        if self.promised_delivery_date < self.order_date:
            raise ValueError("promised_delivery_date cannot be earlier than order_date")
        return self
