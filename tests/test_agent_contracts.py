"""
Pytest Unit Test Suite for Pydantic v2 Tool Interface Contracts.
Verifies Day 04 Technical Architecture Blueprint Contracts.
"""

from datetime import date
import pytest
from pydantic import ValidationError
from src.agent.contracts import (
    RiskCategory,
    MitigationActionType,
    CausalRole,
    InventoryProjectionRequest,
    WeeklyStockPoint,
    InventoryProjectionResponse,
    ActiveRisksRequest,
    RiskAlertItem,
    ActiveRisksResponse,
    RootCauseTraceRequest,
    CausalNode,
    RootCauseTraceResponse,
    MitigationSimulationRequest,
    MitigationSimulationResponse,
)


def test_inventory_projection_contract_validation():
    # Valid request
    req = InventoryProjectionRequest(
        sku_id="SKU-AUG-625-T10",
        location_id="LOC-WH-CHN",
        start_week=1,
        end_week=13
    )
    assert req.sku_id == "SKU-AUG-625-T10"
    assert req.start_week == 1

    # Invalid request (end_week > 26)
    with pytest.raises(ValidationError):
        InventoryProjectionRequest(
            sku_id="SKU-AUG-625-T10",
            location_id="LOC-WH-CHN",
            start_week=1,
            end_week=52
        )


def test_inventory_projection_response_serialization():
    point = WeeklyStockPoint(
        week_num=1,
        week_start_date=date(2026, 11, 2),
        opening_eligible_stock=10000.0,
        confirmed_inbound_receipts=2000.0,
        planned_production_receipts=5000.0,
        forecasted_demand=4000.0,
        closing_eligible_stock=13000.0,
        safety_stock_threshold=3000.0,
        projected_stockout_qty=0.0,
        is_stockout=False,
        is_safety_stock_breach=False
    )
    resp = InventoryProjectionResponse(
        sku_id="SKU-AUG-625-T10",
        location_id="LOC-WH-CHN",
        projection_horizon_weeks=1,
        weekly_trajectory=[point],
        total_unmet_demand=0.0
    )
    assert resp.weekly_trajectory[0].closing_eligible_stock == 13000.0
    assert "Synthetic data" in resp.data_provenance_disclaimer


def test_active_risks_contract_and_evidence_ids():
    alert = RiskAlertItem(
        risk_id="RISK-2026-001",
        sku_id="SKU-AUG-625-T10",
        location_id="LOC-WH-CHN",
        category=RiskCategory.STOCKOUT,
        composite_risk_score=85.5,
        detected_date=date(2026, 11, 1),
        impact_date=date(2026, 11, 23),
        impact_magnitude_units=3500.0,
        financial_exposure_estimate=175000.0,
        alert_summary="Projected stockout in Week 4 due to API delay",
        supporting_evidence_ids=["PO-API-001", "SUP-001"]
    )
    resp = ActiveRisksResponse(
        total_active_alerts=1,
        high_priority_count=1,
        alerts=[alert]
    )
    assert len(resp.alerts) == 1
    assert "PO-API-001" in resp.alerts[0].supporting_evidence_ids


def test_root_cause_trace_contract():
    direct_cause = CausalNode(
        node_id="NODE-01",
        entity_type="PURCHASE_ORDER",
        entity_key="PO-API-001",
        causal_role=CausalRole.DIRECT_CAUSE,
        explanation="Supplier delayed delivery by 14 days",
        observed_delay_days=14,
        supporting_record_id="PO-API-001"
    )
    resp = RootCauseTraceResponse(
        risk_id="RISK-2026-001",
        target_sku_id="SKU-AUG-625-T10",
        root_cause_summary="API delivery delay halted primary tablet granulation",
        primary_direct_cause=direct_cause,
        contributing_factors=[],
        downstream_impacts=[],
        confidence_score=0.95
    )
    assert resp.confidence_score == 0.95
    assert resp.primary_direct_cause.observed_delay_days == 14


def test_mitigation_simulation_human_approval_mandate():
    resp = MitigationSimulationResponse(
        simulation_id="SIM-2026-001",
        risk_id="RISK-2026-001",
        action_type=MitigationActionType.SUPPLIER_EXPEDITE,
        is_feasible=True,
        feasibility_violations=[],
        original_shortage_units=3500.0,
        projected_shortage_units=500.0,
        shortage_reduction_pct=85.7,
        synthetic_implementation_cost=45000.0,
        net_risk_reduction_score=60.0
    )
    # Strictly enforce human-in-the-loop mandate
    assert resp.human_approval_required is True
    assert resp.planner_approval_status == "PENDING_REVIEW"

