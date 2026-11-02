"""
Pydantic v2 Analytical Tool Contracts.
Architectural Interface between Agentic AI Layer (Tier 4) and Deterministic Engines (Tier 2).
Technical Deliverable for Day 04 Blueprint Ratification.

Strict Rule: The LLM invokes tools conforming strictly to these typed Pydantic contracts.
All outputs must include concrete record citations and explicit uncertainty fields.
"""

from datetime import date
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


# --- ENUMS ---

class RiskCategory(str, Enum):
    STOCKOUT = "STOCKOUT"
    SAFETY_STOCK_BREACH = "SAFETY_STOCK_BREACH"
    EXPIRY_EXPOSURE = "EXPIRY_EXPOSURE"
    SUPPLIER_DELAY = "SUPPLIER_DELAY"
    LINE_CAPACITY_OVERLOAD = "LINE_CAPACITY_OVERLOAD"
    BATCH_QA_RELEASE_DELAY = "BATCH_QA_RELEASE_DELAY"


class MitigationActionType(str, Enum):
    SUPPLIER_EXPEDITE = "SUPPLIER_EXPEDITE"
    INVENTORY_REALLOCATION = "INVENTORY_REALLOCATION"
    PRODUCTION_RESCHEDULE = "PRODUCTION_RESCHEDULE"


class CausalRole(str, Enum):
    DIRECT_CAUSE = "DIRECT_CAUSE"
    CONTRIBUTING_FACTOR = "CONTRIBUTING_FACTOR"
    DOWNSTREAM_IMPACT = "DOWNSTREAM_IMPACT"
    ROOT_CAUSE = "ROOT_CAUSE"


# --- 1. INVENTORY PROJECTION CONTRACT ---

class InventoryProjectionRequest(BaseModel):
    sku_id: str = Field(..., description="Unique finished SKU or material SKU identifier (e.g. SKU-AUG-625-T10)")
    location_id: str = Field(..., description="Warehouse or plant location identifier (e.g. LOC-WH-CHN)")
    start_week: int = Field(default=1, ge=1, le=26, description="Start week of projection horizon (1 to 26)")
    end_week: int = Field(default=13, ge=1, le=26, description="End week of projection horizon (1 to 26)")


class WeeklyStockPoint(BaseModel):
    week_num: int
    week_start_date: date
    opening_eligible_stock: float
    confirmed_inbound_receipts: float
    planned_production_receipts: float
    forecasted_demand: float
    closing_eligible_stock: float
    safety_stock_threshold: float
    projected_stockout_qty: float
    is_stockout: bool
    is_safety_stock_breach: bool


class InventoryProjectionResponse(BaseModel):
    sku_id: str
    location_id: str
    projection_horizon_weeks: int
    weekly_trajectory: List[WeeklyStockPoint]
    total_unmet_demand: float
    first_stockout_week: Optional[int] = None
    data_provenance_disclaimer: str = Field(
        default="Synthetic data for demonstration only. Not for operational decision making."
    )


# --- 2. ACTIVE RISKS CONTRACT ---

class ActiveRisksRequest(BaseModel):
    category_filter: Optional[RiskCategory] = Field(default=None, description="Optional filter by risk category")
    min_severity_score: float = Field(default=0.0, ge=0.0, le=100.0, description="Minimum composite risk score (0-100)")
    sku_filter: Optional[str] = Field(default=None, description="Optional finished SKU identifier filter")


class RiskAlertItem(BaseModel):
    risk_id: str
    sku_id: str
    location_id: str
    category: RiskCategory
    composite_risk_score: float = Field(..., ge=0.0, le=100.0)
    detected_date: date
    impact_date: date
    impact_magnitude_units: float
    financial_exposure_estimate: float
    alert_summary: str
    supporting_evidence_ids: List[str] = Field(
        ..., description="List of primary key IDs supporting this alert (e.g. ['PO-API-001', 'SUP-001'])"
    )


class ActiveRisksResponse(BaseModel):
    total_active_alerts: int
    high_priority_count: int
    alerts: List[RiskAlertItem]


# --- 3. ROOT-CAUSE TRACING CONTRACT ---

class RootCauseTraceRequest(BaseModel):
    risk_id: str = Field(..., description="Unique identifier of the detected risk event (e.g. RISK-2026-001)")
    max_causal_depth: int = Field(default=3, ge=1, le=5, description="Search depth across multi-echelon network")


class CausalNode(BaseModel):
    node_id: str
    entity_type: str  # 'PURCHASE_ORDER', 'BATCH', 'PRODUCTION_LINE', 'SUPPLIER'
    entity_key: str  # 'PO-API-001'
    causal_role: CausalRole
    explanation: str
    observed_delay_days: Optional[int] = None
    supporting_record_id: str


class RootCauseTraceResponse(BaseModel):
    risk_id: str
    target_sku_id: str
    root_cause_summary: str
    primary_direct_cause: CausalNode
    contributing_factors: List[CausalNode]
    downstream_impacts: List[CausalNode]
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    uncertainty_disclosure: Optional[str] = None


# --- 4. WHAT-IF SIMULATION CONTRACT ---

class MitigationSimulationRequest(BaseModel):
    risk_id: str = Field(..., description="Target risk event to mitigate")
    action_type: MitigationActionType
    parameters: Dict[str, Any] = Field(
        ..., 
        description="Action parameters (e.g. {'po_id': 'PO-API-001', 'days_accelerated': 10, 'expedite_cost': 50000})"
    )


class MitigationSimulationResponse(BaseModel):
    simulation_id: str
    risk_id: str
    action_type: MitigationActionType
    is_feasible: bool
    feasibility_violations: List[str]
    original_shortage_units: float
    projected_shortage_units: float
    shortage_reduction_pct: float
    synthetic_implementation_cost: float
    net_risk_reduction_score: float
    human_approval_required: bool = Field(default=True)
    planner_approval_status: str = Field(default="PENDING_REVIEW")

