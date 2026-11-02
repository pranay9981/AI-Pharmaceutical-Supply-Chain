"""
Network Topology & Bridge Domain Entities (4 Entities).
Technical Specification & Pydantic v2 Schemas for Week 02, Day 06 Deliverable.

Defines the relational bridge entities linking:
1. Finished SKUs to Materials (Bill of Materials with scrap factors)
2. Suppliers to Materials (Qualified sourcing lanes & procurement parameters)
3. Finished SKUs to Regional Markets (Service SLA & MARSL shelf-life thresholds)
4. Location Nodes to Location Nodes (Multi-tier inter-facility freight routes)
"""

from datetime import date
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, field_validator, model_validator


class TransportMode(str, Enum):
    ROAD = "Road"
    AIR = "Air"
    RAIL = "Rail"
    SEA = "Sea"


class RouteStatus(str, Enum):
    ACTIVE = "Active"
    CONGESTED = "Congested"
    CLOSED = "Closed"


class BridgeBillOfMaterial(BaseModel):
    """
    Relational Bridge linking Finished SKU to component Raw Materials / Packaging.
    Defines per-unit consumption rates and process scrap factors.
    Grain: One record per Finished SKU and Material SKU combination.
    """
    bom_id: str = Field(..., min_length=3, description="Unique BOM record identifier, e.g. BOM-AUG-T10-01")
    finished_sku_id: str = Field(..., min_length=3, description="Foreign key to dim_finished_sku.finished_sku_id")
    material_sku_id: str = Field(..., min_length=3, description="Foreign key to dim_material.material_sku_id")
    quantity_per_finished_unit: float = Field(
        ..., gt=0.0, description="Net component quantity required to produce 1 finished pack"
    )
    scrap_factor_pct: float = Field(
        default=2.0, ge=0.0, le=50.0, description="Process loss scrap percentage (e.g. 2.0% = 0.02)"
    )
    effective_start_date: date = Field(..., description="BOM revision validity start date")
    effective_end_date: Optional[date] = Field(default=None, description="BOM revision expiry date")
    bom_version: str = Field(default="V1", min_length=1, description="Formulation master batch record version")
    synthetic_data_flag: bool = Field(default=True, description="Mandatory synthetic provenance flag")

    @model_validator(mode="after")
    def validate_effective_dates(self) -> "BridgeBillOfMaterial":
        if self.effective_end_date is not None and self.effective_end_date < self.effective_start_date:
            raise ValueError("effective_end_date cannot be earlier than effective_start_date")
        return self

    def calculate_gross_requirement(self, finished_units: float) -> float:
        """
        Calculates gross component requirement including scrap factor:
        Gross = Units * QuantityPerUnit * (1 + ScrapPct / 100)
        """
        if finished_units <= 0:
            return 0.0
        net_qty = finished_units * self.quantity_per_finished_unit
        return net_qty * (1.0 + (self.scrap_factor_pct / 100.0))


class BridgeSupplierMaterial(BaseModel):
    """
    Relational Bridge linking Approved Suppliers to Material SKUs.
    Defines vendor-specific lead times, minimum order quantities, and sourcing priority.
    Grain: One record per Supplier and Material SKU pairing.
    """
    supplier_id: str = Field(..., min_length=3, description="Foreign key to dim_supplier.supplier_id")
    material_sku_id: str = Field(..., min_length=3, description="Foreign key to dim_material.material_sku_id")
    supplier_lead_time_days: int = Field(
        ..., gt=0, description="Replenishment lead time for this specific vendor-material pairing"
    )
    minimum_order_quantity: float = Field(
        default=100.0, ge=0.0, description="Minimum order quantity (MOQ) in material base UOM"
    )
    order_multiple: float = Field(
        default=50.0, gt=0.0, description="Procurement batch order increment multiple"
    )
    approved_supplier_flag: bool = Field(
        default=True, description="Whether supplier is GMP-certified and qualified for this material"
    )
    supplier_priority: int = Field(
        default=1, ge=1, le=5, description="Sourcing rank: 1 = Primary, 2 = Secondary backup, etc."
    )
    effective_start_date: date = Field(..., description="Vendor qualification approval date")
    effective_end_date: Optional[date] = Field(default=None, description="Vendor qualification expiration date")

    @model_validator(mode="after")
    def validate_effective_dates(self) -> "BridgeSupplierMaterial":
        if self.effective_end_date is not None and self.effective_end_date < self.effective_start_date:
            raise ValueError("effective_end_date cannot be earlier than effective_start_date")
        return self


class BridgeSKUMarket(BaseModel):
    """
    Relational Bridge linking Finished SKUs to Regional Consumer Markets.
    Defines commercial service levels and destination Minimum Acceptable Remaining Shelf Life (MARSL).
    Grain: One record per Finished SKU and Regional Market pairing.
    """
    finished_sku_id: str = Field(..., min_length=3, description="Foreign key to dim_finished_sku.finished_sku_id")
    market_id: str = Field(..., min_length=3, description="Foreign key to dim_market.market_id")
    market_priority: int = Field(
        default=1, ge=1, le=5, description="Allocation priority ranking during constrained supply (1 = Highest)"
    )
    service_level_target: float = Field(
        default=98.0, ge=0.0, le=100.0, description="Target OTIF fulfilment service level percentage"
    )
    min_acceptable_rsl_days: int = Field(
        default=90, gt=0, description="Minimum Acceptable Remaining Shelf Life (MARSL) required by this market"
    )
    effective_start_date: date = Field(..., description="Commercial market introduction date")
    effective_end_date: Optional[date] = Field(default=None, description="Market withdrawal date")

    @model_validator(mode="after")
    def validate_effective_dates(self) -> "BridgeSKUMarket":
        if self.effective_end_date is not None and self.effective_end_date < self.effective_start_date:
            raise ValueError("effective_end_date cannot be earlier than effective_start_date")
        return self


class BridgeLocationRoute(BaseModel):
    """
    Relational Bridge linking Network Nodes (Physical Connectivity Matrix).
    Defines transit lead times, freight costs, transport modes, and temperature controls between facilities.
    Grain: One record per Origin Location and Destination Location route.
    """
    route_id: str = Field(..., min_length=3, description="Unique freight route identifier, e.g. RT-PLANT1-DC01")
    origin_location_id: str = Field(..., min_length=3, description="Foreign key to dim_location (Origin node)")
    destination_location_id: str = Field(..., min_length=3, description="Foreign key to dim_location (Destination node)")
    transport_mode: str = Field(default="Road", description="Transport mode: Road, Air, Rail, Sea")
    standard_transit_days: int = Field(
        default=2, ge=0, description="Standard transit duration in calendar days (L_transit)"
    )
    transport_cost_per_unit: float = Field(
        default=0.35, ge=0.0, description="Synthetic freight transportation cost per unit/pack"
    )
    cold_chain_required_flag: bool = Field(
        default=False, description="Whether temperature-controlled reefer transit (2-8C) is required"
    )
    route_status: str = Field(default="Active", description="Operational status: Active, Congested, or Closed")

    @field_validator("destination_location_id")
    @classmethod
    def validate_distinct_endpoints(cls, v: str, info) -> str:
        origin = info.data.get("origin_location_id")
        if origin and v.strip() == origin.strip():
            raise ValueError("destination_location_id cannot be identical to origin_location_id")
        return v
