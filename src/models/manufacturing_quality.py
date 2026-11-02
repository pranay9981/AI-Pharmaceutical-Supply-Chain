"""
Manufacturing & Quality Domain Entities (3 Entities).
Technical Specification & Pydantic v2 Schemas for Week 02, Day 08 Deliverable.

Defines:
1. FactProductionOrder (Plant work orders, planned vs actual start/finish dates, yields, and line hours)
2. FactBatch (Physical batch genealogy, QA sampling submission, testing milestones, and CoA release)
3. FactQualityEvent (GMP deviations, out-of-specification investigations, and QA release holds)
"""

from datetime import date
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, model_validator


class ProductionStatus(str, Enum):
    PLANNED = "Planned"
    RELEASED = "Released"
    IN_PROGRESS = "In_Progress"
    COMPLETED = "Completed"
    ON_HOLD = "On_Hold"
    CANCELLED = "Cancelled"


class BatchStatus(str, Enum):
    IN_TESTING = "In_Testing"
    RELEASED = "Released"
    QUARANTINED = "Quarantined"
    REJECTED = "Rejected"


class QualityEventType(str, Enum):
    STERILITY_RETEST = "Sterility_Retest"
    OOS_INVESTIGATION = "OOS_Investigation"
    TEMPERATURE_EXCURSION = "Temperature_Excursion"
    ROUTINE_RELEASE = "Routine_Release"
    PACKAGING_DEFECT = "Packaging_Defect"


class FactProductionOrder(BaseModel):
    """
    Manufacturing Work Order Fact Entity.
    Grain: One record per manufacturing order line.
    Captures scheduled start/completion dates, actual run times, committed line hours, and production yields.
    """
    production_order_id: str = Field(..., min_length=3, description="Unique production order ID, e.g. PROD-2026-001")
    finished_sku_id: str = Field(..., min_length=3, description="Foreign key to dim_finished_sku.finished_sku_id")
    location_id: str = Field(..., min_length=3, description="Foreign key to dim_location (MANUFACTURING_PLANT)")
    production_line_id: str = Field(..., min_length=3, description="Foreign key to dim_production_line.production_line_id")
    planned_start_date: date = Field(..., description="Scheduled production start date")
    planned_completion_date: date = Field(..., description="Scheduled production completion date")
    actual_start_date: Optional[date] = Field(default=None, description="Actual manufacturing start date")
    actual_completion_date: Optional[date] = Field(default=None, description="Actual manufacturing completion date")
    planned_quantity: float = Field(..., gt=0.0, description="Order target output in sellable packs")
    actual_quantity: float = Field(default=0.0, ge=0.0, description="Gross sellable packs produced")
    expected_yield: float = Field(default=98.0, ge=0.0, le=100.0, description="Expected operational yield percentage")
    actual_yield: Optional[float] = Field(default=None, ge=0.0, le=100.0, description="Actual yield percentage achieved")
    planned_hours: float = Field(..., gt=0.0, description="Committed manufacturing line hours")
    actual_hours: Optional[float] = Field(default=None, ge=0.0, description="Actual line run hours")
    production_status: str = Field(default="Planned", description="Planned, Released, In_Progress, Completed, or On_Hold")
    delay_reason: Optional[str] = Field(default=None, description="API Shortage, Line Breakdown, Changeover Delay, etc.")

    @model_validator(mode="after")
    def validate_production_dates(self) -> "FactProductionOrder":
        if self.planned_completion_date < self.planned_start_date:
            raise ValueError("planned_completion_date cannot be earlier than planned_start_date")
        if self.actual_start_date and self.actual_completion_date:
            if self.actual_completion_date < self.actual_start_date:
                raise ValueError("actual_completion_date cannot be earlier than actual_start_date")
        return self


class FactBatch(BaseModel):
    """
    Manufacturing Batch Genealogy Fact Entity.
    Grain: One record per synthesized chemical batch.
    Tracks physical manufacture finish date, QC laboratory submission, testing duration, and final CoA release.
    """
    batch_id: str = Field(..., min_length=3, description="Unique manufacturing batch identifier, e.g. BATCH-AUG-2026-01")
    production_order_id: str = Field(..., min_length=3, description="Foreign key to fact_production_order.production_order_id")
    finished_sku_id: str = Field(..., min_length=3, description="Foreign key to dim_finished_sku.finished_sku_id")
    location_id: str = Field(..., min_length=3, description="Plant location identifier")
    manufacture_date: date = Field(..., description="Date batch processing finished on manufacturing line")
    quality_submission_date: date = Field(..., description="Date samples were sent to Quality Control lab")
    expected_release_date: date = Field(..., description="Promised QA release date based on standard testing protocol")
    actual_release_date: Optional[date] = Field(default=None, description="Date Certificate of Analysis (CoA) was signed")
    batch_quantity: float = Field(..., gt=0.0, description="Net usable packs produced in batch")
    batch_status: str = Field(default="In_Testing", description="In_Testing, Released, Quarantined, or Rejected")
    rejection_reason: Optional[str] = Field(default=None, description="Out of Specification, Dissolution Failure, Contamination, etc.")

    @model_validator(mode="after")
    def validate_batch_milestones(self) -> "FactBatch":
        if self.quality_submission_date < self.manufacture_date:
            raise ValueError("quality_submission_date cannot be earlier than manufacture_date")
        if self.expected_release_date < self.quality_submission_date:
            raise ValueError("expected_release_date cannot be earlier than quality_submission_date")
        if self.actual_release_date and self.actual_release_date < self.quality_submission_date:
            raise ValueError("actual_release_date cannot be earlier than quality_submission_date")
        return self


class FactQualityEvent(BaseModel):
    """
    Quality Investigation & Deviation Fact Entity.
    Grain: One record per quality event or laboratory investigation.
    Directly substantiates Scenario B (Batch QA Release Hold) by quantifying release delays.
    """
    quality_event_id: str = Field(..., min_length=3, description="Unique QA event ID, e.g. QEV-2026-001")
    entity_type: str = Field(..., description="BATCH, INVENTORY_LOT, or PURCHASE_ORDER")
    entity_id: str = Field(..., min_length=3, description="Linked batch_id, lot_id, or po_id")
    event_type: str = Field(default="Sterility_Retest", description="Sterility_Retest, OOS_Investigation, Temperature_Excursion, or Routine_Release")
    event_date: date = Field(..., description="Date quality event occurred or was flagged")
    expected_resolution_date: date = Field(..., description="Target investigation resolution milestone")
    actual_resolution_date: Optional[date] = Field(default=None, description="Actual date deviation was closed")
    quality_status: str = Field(default="Pending", description="Pending, Cleared, Rejected, or Quarantined")
    delay_days: int = Field(default=0, ge=0, description="Downstream delivery slip introduced by QA event")
    reason_code: str = Field(..., min_length=3, description="Standardized pharmaceutical deviation code")

    @model_validator(mode="after")
    def validate_event_dates(self) -> "FactQualityEvent":
        if self.expected_resolution_date < self.event_date:
            raise ValueError("expected_resolution_date cannot be earlier than event_date")
        if self.actual_resolution_date and self.actual_resolution_date < self.event_date:
            raise ValueError("actual_resolution_date cannot be earlier than event_date")
        return self
