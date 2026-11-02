"""
Control Tower, Scenario & Decision-Support Domain Entities (7 Entities).
Technical Specification & Pydantic v2 Schemas for Week 02, Day 08 Deliverable.

Defines:
1. DimScenario (Benchmark disruption catalog: Scenarios A-E and what-if parameter sets)
2. FactRiskEvent (Detected supply chain exceptions, composite 0-100 risk scores, and impact dates)
3. BridgeRiskEvidence (Relational links between detected risks and supporting operational records)
4. FactRootCause (Deterministic backward causal hierarchy: Direct Cause, Contributing Factors, Uncertainty)
5. FactMitigationSimulation (What-if simulation runs, shortage reduction %, synthetic cost, and feasibility)
6. FactRecommendation (Ranked planner recommendations enforcing human approval mandates)
7. DatasetManifest (Synthetic data provenance, fixed random seed, table row counts, and date bounds)
"""

from datetime import date, datetime
from enum import Enum
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, model_validator


class RiskSeverity(str, Enum):
    CRITICAL = "Critical"
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


class EvidenceRole(str, Enum):
    DIRECT_CAUSE = "DIRECT_CAUSE"
    CONTRIBUTING_FACTOR = "CONTRIBUTING_FACTOR"
    IMPACTED_OBJECT = "IMPACTED_OBJECT"


class FeasibilityStatus(str, Enum):
    FEASIBLE = "Feasible"
    INFEASIBLE_CAPACITY = "Infeasible_Capacity"
    INFEASIBLE_LEADTIME = "Infeasible_LeadTime"
    INFEASIBLE_STOCK = "Infeasible_Stock"
    INFEASIBLE_SHELF_LIFE = "Infeasible_Shelf_Life"


class RecommendationApprovalStatus(str, Enum):
    PENDING_REVIEW = "Pending_Review"
    APPROVED = "Approved"
    REJECTED = "Rejected"


class DimScenario(BaseModel):
    """
    Scenario Definition Master Entity.
    Grain: One record per simulation scenario or benchmark disruption injection.
    Catalogs baseline unconstrained assumptions and injected shocks (Scenarios A through E).
    """
    scenario_id: str = Field(..., min_length=3, description="Unique scenario ID, e.g. SCN-BASE, SCN-A-API-DELAY")
    scenario_name: str = Field(..., min_length=3, description="Scenario title, e.g. Baseline Supply Plan or 14-Day API Slip")
    scenario_type: str = Field(default="BASELINE", description="BASELINE, SUPPLIER_DELAY, QA_HOLD, DEMAND_SPIKE, CAPACITY_OUTAGE")
    scenario_description: str = Field(..., min_length=10, description="Detailed narrative of injected shock and assumptions")
    assumptions: str = Field(..., description="JSON or structured string describing parameter perturbations")
    baseline_flag: bool = Field(default=False, description="Whether this scenario represents the unperturbed baseline")
    synthetic_data_flag: bool = Field(default=True, description="Mandatory synthetic provenance flag")


class FactRiskEvent(BaseModel):
    """
    Detected Risk Exception Fact Entity.
    Grain: One record per detected supply chain risk event.
    Evaluates 6 risk categories, transparent 0-100 composite scoring, and lead time to impact.
    """
    risk_id: str = Field(..., min_length=3, description="Unique detected exception ID, e.g. RISK-2026-001")
    risk_type: str = Field(..., min_length=3, description="Stockout, Safety_Stock_Breach, Expiry_Exposure, Supplier_Delay, Capacity_Constraint, QA_Delay")
    entity_type: str = Field(..., min_length=3, description="SKU, MATERIAL, PRODUCTION_LINE, SUPPLIER, or SHIPMENT")
    entity_id: str = Field(..., min_length=3, description="Impacted SKU ID, Material ID, or Line ID")
    location_id: str = Field(..., min_length=3, description="Node where risk materializes (e.g. LOC-DC-01 or MKT-IN-HYD)")
    detection_date: date = Field(..., description="Date system algorithm detected the exception")
    impact_date: date = Field(..., description="Expected date of stockout or operational failure")
    severity: str = Field(default="High", description="Critical, High, Medium, or Low")
    risk_score: float = Field(..., ge=0.0, le=100.0, description="Transparent composite 0-100 score: 0.30S + 0.20T + 0.15C + 0.15D + 0.10U + 0.10R")
    shortage_quantity: float = Field(default=0.0, ge=0.0, description="Projected volume deficit in packs or kg")
    days_to_impact: int = Field(default=0, description="Lead time buffer remaining: impact_date - detection_date")
    risk_status: str = Field(default="Active", description="Active, Investigating, Mitigated, or Resolved")
    scenario_id: str = Field(default="SCN-BASE", description="Baseline or disruption scenario identifier")

    @model_validator(mode="after")
    def calculate_days_to_impact(self) -> "FactRiskEvent":
        calc_days = (self.impact_date - self.detection_date).days
        self.days_to_impact = calc_days
        return self


class BridgeRiskEvidence(BaseModel):
    """
    Relational Risk Evidence Linker Bridge.
    Grain: One record per Risk ID and supporting operational record pairing.
    Guarantees 100% evidence grounding by connecting alerts directly to POs, Batches, Lots, and Lines.
    """
    risk_id: str = Field(..., min_length=3, description="Foreign key to fact_risk_event.risk_id")
    evidence_type: str = Field(..., min_length=3, description="PURCHASE_ORDER, PRODUCTION_ORDER, BATCH, INVENTORY_LOT, CAPACITY")
    evidence_record_id: str = Field(..., min_length=3, description="Foreign key to underlying operational record (e.g. PO-2026-001)")
    evidence_role: str = Field(default="DIRECT_CAUSE", description="DIRECT_CAUSE, CONTRIBUTING_FACTOR, or IMPACTED_OBJECT")
    evidence_description: str = Field(..., min_length=5, description="Human readable explanation of how this record substantiates the risk")


class FactRootCause(BaseModel):
    """
    Root Cause Determination Fact Entity.
    Grain: One record per root cause determination.
    Houses the structured backward causal graph and flags data gaps / uncertainty notes.
    """
    root_cause_id: str = Field(..., min_length=3, description="Unique root cause determination ID, e.g. RC-2026-001")
    risk_id: str = Field(..., min_length=3, description="Foreign key to fact_risk_event.risk_id")
    root_cause_category: str = Field(..., min_length=3, description="SUPPLIER_DELIVERY, QA_HOLD, CAPACITY_SHORTFALL, DEMAND_SURGE")
    root_cause_description: str = Field(..., min_length=10, description="Deterministic summary of why the risk occurred")
    contributing_factor: Optional[str] = Field(default=None, description="Secondary aggravating constraint")
    causal_sequence: str = Field(..., min_length=5, description="Ordered causal chain: Event A -> Event B -> Stockout")
    evidence_complete_flag: bool = Field(default=True, description="Whether full audit trail was located in records")
    confidence_or_uncertainty_note: Optional[str] = Field(default=None, description="Explicit statement of unconfirmed parameters or data gaps")


class FactMitigationSimulation(BaseModel):
    """
    What-If Mitigation Simulation Run Fact Entity.
    Grain: One record per what-if simulation execution.
    Evaluates simulated shortage reductions, synthetic costs, and operational feasibility constraints.
    """
    simulation_id: str = Field(..., min_length=3, description="Unique what-if simulation run ID, e.g. SIM-2026-001")
    risk_id: str = Field(..., min_length=3, description="Foreign key to fact_risk_event.risk_id")
    scenario_id: str = Field(..., min_length=3, description="Linked scenario context")
    action_type: str = Field(..., min_length=3, description="SUPPLIER_EXPEDITE, INVENTORY_REALLOCATION, PRODUCTION_RESCHEDULING")
    action_parameters: str = Field(..., description="JSON string of modified parameters (days_expedited, source_dc, etc.)")
    baseline_outcome: str = Field(..., min_length=5, description="Summary of baseline deficit (e.g. 'Shortage of 2,000 packs in W04')")
    simulated_outcome: str = Field(..., min_length=5, description="Summary of post-mitigation state (e.g. 'Shortage resolved, ending stock 450')")
    risk_reduction: float = Field(..., ge=0.0, le=100.0, description="Percentage reduction in projected shortage (0.0 to 100.0%)")
    estimated_cost: float = Field(default=0.0, ge=0.0, description="Estimated synthetic implementation cost in currency units")
    feasibility_status: str = Field(default="Feasible", description="Feasible, Infeasible_Capacity, Infeasible_LeadTime, Infeasible_Stock")
    remaining_constraints: Optional[str] = Field(default=None, description="Downstream constraints not solved by this action")


class FactRecommendation(BaseModel):
    """
    Decision-Support Recommendation Fact Entity.
    Grain: One record per candidate corrective action.
    Strictly enforces human approval requirements (human_approval_required = True) and planner sign-off tracking.
    """
    recommendation_id: str = Field(..., min_length=3, description="Unique decision support recommendation ID, e.g. REC-2026-001")
    risk_id: str = Field(..., min_length=3, description="Foreign key to fact_risk_event.risk_id")
    simulation_id: str = Field(..., min_length=3, description="Foreign key to fact_mitigation_simulation.simulation_id")
    recommended_action: str = Field(..., min_length=10, description="Executive action statement for planner review")
    recommended_quantity: float = Field(..., ge=0.0, description="Packs or units to expedite/transfer")
    expected_benefit: str = Field(..., min_length=5, description="Quantified risk reduction statement")
    estimated_cost: float = Field(default=0.0, ge=0.0, description="Estimated synthetic implementation cost")
    feasibility_status: str = Field(default="Feasible", description="Feasibility state")
    evidence_reference: str = Field(..., min_length=3, description="Citations of operational record IDs justifying recommendation")
    human_approval_required: bool = Field(default=True, description="Mandatory True flag for decision support compliance")
    approval_status: str = Field(default="Pending_Review", description="Pending_Review, Approved, or Rejected")
    created_date: date = Field(..., description="Date recommendation was generated")

    @model_validator(mode="after")
    def enforce_human_approval(self) -> "FactRecommendation":
        if not self.human_approval_required:
            raise ValueError("human_approval_required must strictly remain True for GxP decision support compliance")
        return self


class DatasetManifest(BaseModel):
    """
    Synthetic Dataset Manifest Audit Entity.
    Grain: One record per dataset release / generation run.
    Guarantees reproducible data generation, tracking fixed random seed (20261014), row counts, and date boundaries.
    """
    dataset_version: str = Field(default="v1.0.0-phase1", description="Release version identifier")
    generation_timestamp: datetime = Field(..., description="Exact timestamp of generation run")
    random_seed: int = Field(default=20261014, description="Fixed reproducibility seed")
    record_counts: Dict[str, int] = Field(..., description="Dictionary of row counts per table")
    date_range: Dict[str, str] = Field(..., description="Start and end dates of history and future horizons")
    scenario_coverage: List[str] = Field(..., description="List of scenario IDs generated in this release")
    validation_status: str = Field(default="PASSED", description="PASSED or FAILED")
    synthetic_data_flag: bool = Field(default=True, description="Mandatory synthetic provenance flag")
