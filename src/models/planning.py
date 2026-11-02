"""
Planning & Forecasting Fact Entities (4 Entities).
Technical Specification & Pydantic v2 Schemas for Week 02, Day 07 Deliverable.

Defines:
1. FactDemandForecast (26-week horizon forecasts with P10/P90 prediction intervals & versioning)
2. FactSupplyPlan (Replenishment targets across manufacturing & logistics)
3. FactMaterialRequirement (BOM exploded gross and net component MRP requirements)
4. FactInventoryProjection (Multi-echelon weekly stock trajectories & shortage detection)
"""

from datetime import date
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, model_validator


class SupplySourceType(str, Enum):
    MANUFACTURING = "MANUFACTURING"
    INTER_DC_TRANSFER = "INTER_DC_TRANSFER"
    CMO_PURCHASE = "CMO_PURCHASE"


class SupplyPlanStatus(str, Enum):
    DRAFT = "Draft"
    COMMITTED = "Committed"
    EXECUTED = "Executed"
    CANCELLED = "Cancelled"


class InventoryItemType(str, Enum):
    FINISHED_SKU = "FINISHED_SKU"
    RAW_MATERIAL = "RAW_MATERIAL"


class FactDemandForecast(BaseModel):
    """
    Demand Forecast Fact Entity.
    Grain: One record per forecast version date, target horizon week, SKU, Market, and Scenario.
    Includes point estimates, P10/P90 probabilistic prediction intervals, and planner overrides.
    """
    forecast_id: str = Field(..., min_length=3, description="Unique forecast record ID, e.g. FCST-20261026-001")
    forecast_version_date: date = Field(..., description="As-of creation date to prevent future data leakage")
    target_week: date = Field(..., description="Monday start date of predicted horizon week")
    finished_sku_id: str = Field(..., min_length=3, description="Foreign key to dim_finished_sku.finished_sku_id")
    market_id: str = Field(..., min_length=3, description="Foreign key to dim_market.market_id")
    forecast_quantity: float = Field(..., ge=0.0, description="Point estimate of forecasted demand in packs")
    lower_bound: float = Field(..., ge=0.0, description="P10 lower prediction interval bound")
    upper_bound: float = Field(..., ge=0.0, description="P90 upper prediction interval bound")
    override_quantity: Optional[float] = Field(default=None, ge=0.0, description="Documented human planner override")
    model_version: str = Field(default="Ensemble-HoltWinters-Ridge-v1.0", description="Forecasting model identifier")
    scenario_id: str = Field(default="SCN-BASE", description="Baseline or disruption scenario identifier")

    @model_validator(mode="after")
    def validate_forecast_intervals(self) -> "FactDemandForecast":
        if self.lower_bound > self.upper_bound:
            raise ValueError(f"lower_bound ({self.lower_bound}) cannot exceed upper_bound ({self.upper_bound})")
        if self.target_week < self.forecast_version_date:
            raise ValueError("target_week cannot be earlier than forecast_version_date (Data Leakage Violation)")
        return self


class FactSupplyPlan(BaseModel):
    """
    Supply Replenishment Plan Entity.
    Grain: One record per supply plan ID, planned week, SKU, location, and scenario.
    Defines master production scheduling (MPS) and inter-DC replenishment targets.
    """
    supply_plan_id: str = Field(..., min_length=3, description="Unique supply replenishment record ID")
    finished_sku_id: str = Field(..., min_length=3, description="Foreign key to dim_finished_sku.finished_sku_id")
    location_id: str = Field(..., min_length=3, description="Destination node, e.g. LOC-DC-01")
    planned_week: date = Field(..., description="Target weekly replenishment bucket")
    planned_quantity: float = Field(..., ge=0.0, description="Planned replenishment volume in sellable packs")
    source_type: str = Field(default="MANUFACTURING", description="MANUFACTURING, INTER_DC_TRANSFER, or CMO_PURCHASE")
    source_order_id: Optional[str] = Field(default=None, description="Linked production_order_id or shipment_id")
    expected_availability_date: date = Field(..., description="Milestone when stock becomes eligible for fulfilment")
    scenario_id: str = Field(default="SCN-BASE", description="Baseline or disruption scenario identifier")
    plan_status: str = Field(default="Committed", description="Draft, Committed, or Executed")

    @model_validator(mode="after")
    def validate_availability_milestone(self) -> "FactSupplyPlan":
        if self.expected_availability_date < self.planned_week:
            raise ValueError("expected_availability_date cannot be earlier than planned_week start")
        return self


class FactMaterialRequirement(BaseModel):
    """
    Material Requirements Planning (MRP) Fact Entity.
    Grain: One record per production order, material SKU, and scenario.
    Calculates gross component need, nets against eligible stock and open POs, and flags component deficits.
    """
    requirement_id: str = Field(..., min_length=3, description="Unique requirement line ID")
    production_order_id: str = Field(..., min_length=3, description="Foreign key to fact_production_order.production_order_id")
    material_sku_id: str = Field(..., min_length=3, description="Foreign key to dim_material.material_sku_id")
    required_quantity: float = Field(..., ge=0.0, description="Gross component requirement calculated via BOM")
    required_date: date = Field(..., description="Need-by date at factory production dock")
    eligible_available_quantity: float = Field(default=0.0, ge=0.0, description="Eligible unreserved stock on-hand by need-by date")
    expected_receipt_quantity: float = Field(default=0.0, ge=0.0, description="Confirmed incoming PO receipts arriving before need-by date")
    shortage_quantity: float = Field(default=0.0, ge=0.0, description="Net unfulfilled component deficit")
    scenario_id: str = Field(default="SCN-BASE", description="Baseline or disruption scenario identifier")

    @model_validator(mode="after")
    def calculate_shortage(self) -> "FactMaterialRequirement":
        net_available = self.eligible_available_quantity + self.expected_receipt_quantity
        deficit = max(0.0, round(self.required_quantity - net_available, 4))
        if self.shortage_quantity == 0.0 and deficit > 0:
            self.shortage_quantity = deficit
        return self


class FactInventoryProjection(BaseModel):
    """
    Multi-Echelon Forward Inventory Projection Fact Entity.
    Grain: One record per item, facility location, weekly bucket, and scenario.
    Tracks recursive inventory balance: I_t = I_{t-1} + Receipts + Prod - Demand.
    """
    projection_id: str = Field(..., min_length=3, description="Unique projection row ID, e.g. PRJ-SKU1-DC1-W04")
    item_type: str = Field(default="FINISHED_SKU", description="FINISHED_SKU or RAW_MATERIAL")
    item_id: str = Field(..., min_length=3, description="finished_sku_id or material_sku_id")
    location_id: str = Field(..., min_length=3, description="Foreign key to dim_location.location_id")
    week_start_date: date = Field(..., description="Target horizon week start date")
    opening_inventory: float = Field(..., description="Starting eligible stock balance")
    planned_receipts: float = Field(default=0.0, ge=0.0, description="Confirmed incoming shipments / purchase orders")
    planned_production: float = Field(default=0.0, ge=0.0, description="Scheduled finished goods manufacturing receipts")
    forecast_demand: float = Field(default=0.0, ge=0.0, description="Demand forecast or material gross consumption")
    projected_ending_inventory: float = Field(..., description="Calculated ending stock: Open + Receipts + Prod - Demand")
    safety_stock: float = Field(default=0.0, ge=0.0, description="Configured target buffer units")
    projected_shortage: float = Field(default=0.0, ge=0.0, description="Deficit below zero: max(0, -projected_ending_inventory)")
    scenario_id: str = Field(default="SCN-BASE", description="Baseline or disruption scenario identifier")

    @model_validator(mode="after")
    def validate_projection_math(self) -> "FactInventoryProjection":
        # Calculate expected ending inventory
        expected_ending = round(
            self.opening_inventory + self.planned_receipts + self.planned_production - self.forecast_demand, 4
        )
        # Verify shortage calculation
        expected_shortage = max(0.0, round(-expected_ending, 4)) if expected_ending < 0 else 0.0
        if self.projected_shortage == 0.0 and expected_shortage > 0:
            self.projected_shortage = expected_shortage
        return self
