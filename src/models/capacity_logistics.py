"""
Capacity & Logistics Domain Entities (2 Entities).
Technical Specification & Pydantic v2 Schemas for Week 02, Day 08 Deliverable.

Defines:
1. FactCapacity (Weekly plant line operating hours, scheduled maintenance, and committed load)
2. FactShipment (Inter-facility transport dispatches, transit durations, and cold-chain temperature logs)
"""

from datetime import date
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, model_validator, field_validator


class ShipmentStatus(str, Enum):
    MANIFESTED = "Manifested"
    IN_TRANSIT = "In_Transit"
    DELIVERED = "Delivered"
    DELAYED = "Delayed"
    CANCELLED = "Cancelled"


class FactCapacity(BaseModel):
    """
    Manufacturing Line Capacity Fact Entity.
    Grain: One record per plant line, weekly planning period, and scenario.
    Monitors machine utilization, scheduled preventive maintenance, and capacity overloads (Scenario E).
    """
    capacity_record_id: str = Field(..., min_length=3, description="Unique capacity weekly record ID, e.g. CAP-PLANT1-LINE1-W44")
    location_id: str = Field(..., min_length=3, description="Plant location identifier")
    production_line_id: str = Field(..., min_length=3, description="Production line identifier")
    period_start_date: date = Field(..., description="Monday start of weekly planning period")
    net_available_hours: float = Field(default=120.0, ge=0.0, description="Gross operating hours minus statutory holidays")
    maintenance_hours: float = Field(default=8.0, ge=0.0, description="Planned preventive maintenance hours")
    downtime_hours: float = Field(default=0.0, ge=0.0, description="Unplanned breakdown or changeover downtime hours")
    committed_hours: float = Field(default=0.0, ge=0.0, description="Hours booked by scheduled production orders")
    scenario_id: str = Field(default="SCN-BASE", description="Baseline or disruption scenario identifier")

    def calculate_utilization_pct(self) -> float:
        """Calculates line capacity utilization percentage against net available hours."""
        if self.net_available_hours <= 0:
            return 0.0
        return round((self.committed_hours / self.net_available_hours) * 100.0, 2)

    def is_overloaded(self) -> bool:
        """Flags whether committed hours exceed net available hours."""
        return self.committed_hours > self.net_available_hours


class FactShipment(BaseModel):
    """
    Inter-Facility Freight Shipment Fact Entity.
    Grain: One record per transport consignment dispatch.
    Tracks transit departure, scheduled vs actual arrival, freight volume, and cold-chain integrity.
    """
    shipment_id: str = Field(..., min_length=3, description="Unique inter-node shipment ID, e.g. SHIP-2026-001")
    origin_location_id: str = Field(..., min_length=3, description="Dispatch facility (Plant or Central DC)")
    destination_location_id: str = Field(..., min_length=3, description="Receiving facility (DC or Regional Hub)")
    finished_sku_id: str = Field(..., min_length=3, description="Foreign key to dim_finished_sku.finished_sku_id")
    lot_id: str = Field(..., min_length=3, description="Foreign key to fact_inventory_lot.lot_id")
    dispatch_date: date = Field(..., description="Actual dispatch departure date")
    expected_arrival_date: date = Field(..., description="Scheduled arrival milestone based on route transit days")
    actual_arrival_date: Optional[date] = Field(default=None, description="Actual physical gate-in date at receiving dock")
    shipped_quantity: float = Field(..., gt=0.0, description="Packs dispatched on consignment")
    received_quantity: float = Field(default=0.0, ge=0.0, description="Packs received intact at destination dock")
    transport_mode: str = Field(default="Road", description="Road, Air, or Rail")
    shipment_status: str = Field(default="In_Transit", description="Manifested, In_Transit, Delivered, or Delayed")
    delay_reason: Optional[str] = Field(default=None, description="Highway Congestion, Monsoon Flooding, Vehicle Breakdown, etc.")
    temperature_excursion_flag: bool = Field(default=False, description="Cold-chain temperature breach indicator")

    @field_validator("destination_location_id")
    @classmethod
    def validate_distinct_endpoints(cls, v: str, info) -> str:
        origin = info.data.get("origin_location_id")
        if origin and v.strip() == origin.strip():
            raise ValueError("destination_location_id cannot be identical to origin_location_id")
        return v

    @model_validator(mode="after")
    def validate_shipment_dates(self) -> "FactShipment":
        if self.expected_arrival_date < self.dispatch_date:
            raise ValueError("expected_arrival_date cannot be earlier than dispatch_date")
        if self.actual_arrival_date and self.actual_arrival_date < self.dispatch_date:
            raise ValueError("actual_arrival_date cannot be earlier than dispatch_date")
        return self
