"""
Procurement & Inventory Fact Entities (3 Entities).
Technical Specification & Pydantic v2 Schemas for Week 02, Day 07 Deliverable.

Defines:
1. FactPurchaseOrder (Vendor purchase order lines, requested/confirmed delivery, and OTIF tracking)
2. FactInventoryLot (Physical batch positions, quality status, shelf-life, and quarantine holds)
3. FactMaterialConsumption (Actual material charging into production batches vs BOM plan)
"""

from datetime import date
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, model_validator


class POStatus(str, Enum):
    OPEN = "Open"
    IN_TRANSIT = "In_Transit"
    RECEIVED = "Received"
    SHORT_SHIPPED = "Short_Shipped"
    DELAYED = "Delayed"
    CANCELLED = "Cancelled"


class LotQualityStatus(str, Enum):
    RELEASED = "Released"
    QUARANTINED = "Quarantined"
    BLOCKED = "Blocked"
    REJECTED = "Rejected"
    EXPIRED = "Expired"


class FactPurchaseOrder(BaseModel):
    """
    Vendor Purchase Order Fact Entity.
    Grain: One record per purchase order line.
    Captures procurement order dates, vendor commitments, actual dock arrivals, and OTIF delivery variance.
    """
    purchase_order_id: str = Field(..., min_length=3, description="Unique purchase order identifier, e.g. PO-2026-001")
    supplier_id: str = Field(..., min_length=3, description="Foreign key to dim_supplier.supplier_id")
    material_sku_id: str = Field(..., min_length=3, description="Foreign key to dim_material.material_sku_id")
    order_date: date = Field(..., description="Date PO was issued to supplier")
    requested_delivery_date: date = Field(..., description="Buyer requested dock delivery milestone")
    confirmed_delivery_date: date = Field(..., description="Supplier confirmed promised milestone")
    actual_receipt_date: Optional[date] = Field(default=None, description="Actual physical gate-in receipt date at plant")
    ordered_quantity: float = Field(..., gt=0.0, description="Quantity ordered in material UOM")
    received_quantity: float = Field(default=0.0, ge=0.0, description="Quantity actually received at factory receiving dock")
    purchase_order_status: str = Field(default="Open", description="Open, In_Transit, Received, Short_Shipped, or Delayed")
    delay_reason: Optional[str] = Field(default=None, description="Customs Hold, Raw Material Bottleneck, Transit Delay, etc.")
    quality_status: str = Field(default="Pending_Inspection", description="Pending_Inspection, Released, or Quarantined")

    @model_validator(mode="after")
    def validate_po_dates(self) -> "FactPurchaseOrder":
        if self.requested_delivery_date < self.order_date:
            raise ValueError("requested_delivery_date cannot be earlier than order_date")
        if self.confirmed_delivery_date < self.order_date:
            raise ValueError("confirmed_delivery_date cannot be earlier than order_date")
        if self.actual_receipt_date is not None and self.actual_receipt_date < self.order_date:
            raise ValueError("actual_receipt_date cannot be earlier than order_date")
        return self


class FactInventoryLot(BaseModel):
    """
    Lot-Level Inventory Position Fact Entity.
    Grain: One record per physical batch lot and warehouse/plant location.
    Underpins the FEFO allocation engine by tracking manufacture date, expiry date, and QA release status.
    """
    lot_id: str = Field(..., min_length=3, description="Traceable lot identity, e.g. LOT-API-2026-01")
    item_type: str = Field(default="FINISHED_SKU", description="FINISHED_SKU or RAW_MATERIAL")
    item_id: str = Field(..., min_length=3, description="finished_sku_id or material_sku_id")
    location_id: str = Field(..., min_length=3, description="Foreign key to dim_location.location_id")
    batch_id: Optional[str] = Field(default=None, description="Linked manufacturing batch if finished goods")
    manufacture_date: date = Field(..., description="Date of component synthesis or finished batch release")
    expiry_date: date = Field(..., description="Batch expiration milestone (must exceed manufacture_date)")
    retest_date: Optional[date] = Field(default=None, description="Periodic re-assay date for APIs/excipients")
    quantity_on_hand: float = Field(..., ge=0.0, description="Total physical stock currently held on-site")
    reserved_quantity: float = Field(default=0.0, ge=0.0, description="Stock allocated to active orders")
    blocked_quantity: float = Field(default=0.0, ge=0.0, description="Stock held under regulatory/quality embargo")
    quality_status: str = Field(default="Released", description="Released, Quarantined, Blocked, Rejected, or Expired")
    receipt_date: date = Field(..., description="Date inventory arrived at this facility")
    release_date: Optional[date] = Field(default=None, description="Date QA released the lot for operational consumption")
    recall_status: str = Field(default="None", description="None, Class-I, Class-II, or Under_Investigation")
    synthetic_data_flag: bool = Field(default=True, description="Mandatory synthetic provenance flag")

    @model_validator(mode="after")
    def validate_lot_dates_and_quantities(self) -> "FactInventoryLot":
        if self.expiry_date <= self.manufacture_date:
            raise ValueError("expiry_date must be strictly later than manufacture_date")
        if self.release_date is not None and self.release_date < self.receipt_date:
            raise ValueError("release_date cannot be earlier than receipt_date")
        if self.reserved_quantity > self.quantity_on_hand:
            raise ValueError("reserved_quantity cannot exceed quantity_on_hand")
        return self


class FactMaterialConsumption(BaseModel):
    """
    Material Consumption Fact Entity.
    Grain: One record per production order, material SKU, and consumed lot.
    Audits actual physical ingredient usage against theoretical BOM requirements.
    """
    consumption_id: str = Field(..., min_length=3, description="Unique consumption transaction ID")
    production_order_id: str = Field(..., min_length=3, description="Foreign key to fact_production_order.production_order_id")
    material_sku_id: str = Field(..., min_length=3, description="Foreign key to dim_material.material_sku_id")
    lot_id: str = Field(..., min_length=3, description="Foreign key to fact_inventory_lot.lot_id")
    planned_quantity: float = Field(..., gt=0.0, description="Theoretical BOM requirement in material UOM")
    actual_quantity: float = Field(..., ge=0.0, description="Actual physical quantity charged into batch")
    consumption_date: date = Field(..., description="Date material was dispensed to plant floor")
    variance_quantity: float = Field(default=0.0, description="actual_quantity - planned_quantity")

    @model_validator(mode="after")
    def calculate_variance(self) -> "FactMaterialConsumption":
        self.variance_quantity = round(self.actual_quantity - self.planned_quantity, 4)
        return self
