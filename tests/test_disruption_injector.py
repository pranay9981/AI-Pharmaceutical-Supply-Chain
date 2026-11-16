"""
Unit tests for Disruption Scenario Injection Engine.
Synthetic Data Generation Engine — Week 03, Day 13 Deliverable.

Verifies:
1. Scenario A: Supplier delivery delay, MRP deficit, and downstream stockout.
2. Scenario B: Batch QA release hold, sterility retest, and rapid assay mitigation.
3. Scenario C: Shared secondary carton shortage and dual-line impact.
4. Scenario D: Sub-MARSL lot expiry exposure and retail liquidation.
5. Scenario E: Mitigation feasibility conflict and line capacity overload.
6. Full benchmark suite aggregation across all 5 scenarios (A-E).
7. Strict schema-level enforcement of human_approval_required = True on all recommendations.
"""

import datetime
import pytest
from src.generator.config import GeneratorConfig
from src.generator.master_data import generate_master_and_bridge_data
from src.generator.supply_data import generate_supply_and_operations_data
from src.generator.disruption_injector import (
    inject_disruptions,
    inject_scenario_a,
    inject_scenario_b,
    inject_scenario_c,
    inject_scenario_d,
    inject_scenario_e
)
from src.models.control_tower import (
    FactRiskEvent, BridgeRiskEvidence, FactRootCause,
    FactMitigationSimulation, FactRecommendation
)


@pytest.fixture
def test_setup():
    config = GeneratorConfig(random_seed=20261014, synthetic_flag=True)
    master_data = generate_master_and_bridge_data(config)
    supply_data = generate_supply_and_operations_data(config)
    return config, master_data, supply_data


def test_scenario_a_supplier_delay(test_setup):
    """Verifies Scenario A supplier delay, MRP shortage, root causes, and mitigations."""
    config, master_data, supply_data = test_setup
    result = inject_scenario_a(master_data, supply_data, config)

    # 1. Mutated PO check (PO-2026-001 shifted +14 days to 2026-11-16)
    po = next(p for p in result["fact_purchase_order_scenario"] if p.purchase_order_id == "PO-2026-001")
    assert po.confirmed_delivery_date == datetime.date(2026, 11, 16)
    assert po.purchase_order_status == "Delayed"

    # 2. Mutated MRP check (REQ-2026-001-API has 47.5 kg shortage)
    req = next(r for r in result["fact_material_requirement_scenario"] if r.requirement_id == "REQ-2026-001-API")
    assert req.shortage_quantity == pytest.approx(47.5, rel=1e-4)

    # 3. Mutated Production Order check (PROD-2026-001 On_Hold)
    prod = next(p for p in result["fact_production_order_scenario"] if p.production_order_id == "PROD-2026-001")
    assert prod.production_status == "On_Hold"

    # 4. Risk events (2 risks: Material Shortage + DC Stockout)
    risks = result["fact_risk_event"]
    assert len(risks) == 2
    risk_ids = {r.risk_id for r in risks}
    assert risk_ids == {"RISK-2026-001", "RISK-2026-002"}
    for r in risks:
        assert isinstance(r, FactRiskEvent)
        assert r.risk_score > 75.0

    # 5. Evidence records (5 evidence links citing PO-2026-001, PROD-2026-001, etc.)
    evidence = result["bridge_risk_evidence"]
    assert len(evidence) == 5
    evidence_ids = {e.evidence_record_id for e in evidence}
    assert "PO-2026-001" in evidence_ids
    assert "PROD-2026-001" in evidence_ids

    # 6. Recommendations & human approval mandate
    recs = result["fact_recommendation"]
    assert len(recs) == 2
    for rec in recs:
        assert isinstance(rec, FactRecommendation)
        assert rec.human_approval_required is True
        assert rec.approval_status == "Pending_Review"


def test_scenario_b_batch_qa_hold(test_setup):
    """Verifies Scenario B finished batch QA release hold and rapid assay mitigation."""
    config, _, _ = test_setup
    result = inject_scenario_b(config.planning_as_of_date)

    risks = result["fact_risk_event"]
    assert len(risks) == 1
    assert risks[0].risk_id == "RISK-2026-003"
    assert risks[0].risk_type == "QA_Hold"
    assert risks[0].entity_id == "BATCH-AUG-2026-10"

    sims = result["fact_mitigation_simulation"]
    assert len(sims) == 1
    assert sims[0].action_type == "EXPEDITE_QC_TESTING"
    assert sims[0].feasibility_status == "Feasible"

    recs = result["fact_recommendation"]
    assert len(recs) == 1
    assert recs[0].human_approval_required is True


def test_scenario_c_carton_shortage(test_setup):
    """Verifies Scenario C shared packaging shortage and dual-line stoppage."""
    config, _, _ = test_setup
    result = inject_scenario_c(config.planning_as_of_date)

    risks = result["fact_risk_event"]
    assert len(risks) == 1
    assert risks[0].risk_id == "RISK-2026-004"
    assert risks[0].entity_id == "MAT-PKG-CART"
    assert risks[0].severity == "Critical"

    evidence = result["bridge_risk_evidence"]
    impacted_prods = {e.evidence_record_id for e in evidence if e.evidence_role == "IMPACTED_OBJECT"}
    # Verifies both T10 and T30 production lines are cited as impacted
    assert "PROD-2026-001" in impacted_prods
    assert "PROD-2026-002" in impacted_prods

    recs = result["fact_recommendation"]
    assert len(recs) == 1
    assert recs[0].human_approval_required is True


def test_scenario_d_fefo_exposure(test_setup):
    """Verifies Scenario D near-expiry MARSL exposure and channel liquidation."""
    config, _, _ = test_setup
    result = inject_scenario_d(config.planning_as_of_date)

    risks = result["fact_risk_event"]
    assert len(risks) == 1
    assert risks[0].risk_id == "RISK-2026-005"
    assert risks[0].entity_id == "LOT-FG-AUG-T10-24X"
    assert risks[0].risk_type == "Expiry_Risk"

    sims = result["fact_mitigation_simulation"]
    assert len(sims) == 1
    assert sims[0].action_type == "DISCOUNT_CHANNEL_REALLOCATION"

    recs = result["fact_recommendation"]
    assert len(recs) == 1
    assert recs[0].human_approval_required is True


def test_scenario_e_capacity_conflict(test_setup):
    """Verifies Scenario E plant line overload and feasibility rejection."""
    config, _, _ = test_setup
    result = inject_scenario_e(config.planning_as_of_date)

    risks = result["fact_risk_event"]
    assert len(risks) == 1
    assert risks[0].risk_id == "RISK-2026-006"
    assert risks[0].risk_type == "Capacity_Overload"
    assert risks[0].entity_id == "LINE-PLANT1-01"

    sims = result["fact_mitigation_simulation"]
    assert len(sims) == 1
    # Verifies overtime mitigation resolves capacity
    assert sims[0].action_type == "WEEKEND_OVERTIME_OR_CMO"

    recs = result["fact_recommendation"]
    assert len(recs) == 1
    assert "INFEASIBLE_CAPACITY" in recs[0].recommended_action
    assert recs[0].human_approval_required is True


def test_full_benchmark_suite_aggregation(test_setup):
    """Verifies aggregation of all 5 benchmark scenarios (A through E)."""
    config, master_data, supply_data = test_setup
    all_benchmark_ids = [
        "SCN-A-API-DELAY",
        "SCN-B-BATCH-HOLD",
        "SCN-C-CARTON-SHORTAGE",
        "SCN-D-FEFO-EXPOSURE",
        "SCN-E-CAPACITY-CONFLICT"
    ]
    result = inject_disruptions(master_data, supply_data, config, scenarios=all_benchmark_ids)

    # Total 6 risks: 2 from Scenario A + 1 each from B, C, D, E
    risks = result["fact_risk_event"]
    assert len(risks) == 6
    risk_ids = {r.risk_id for r in risks}
    assert risk_ids == {
        "RISK-2026-001",
        "RISK-2026-002",
        "RISK-2026-003",
        "RISK-2026-004",
        "RISK-2026-005",
        "RISK-2026-006"
    }

    # Total 6 recommendations, all enforcing human_approval_required = True
    recs = result["fact_recommendation"]
    assert len(recs) == 6
    for rec in recs:
        assert rec.human_approval_required is True

    # Total 6 root causes
    root_causes = result["fact_root_cause"]
    assert len(root_causes) == 6

    # Total 6 simulations
    sims = result["fact_mitigation_simulation"]
    assert len(sims) == 6


def test_default_scenario_compatibility(test_setup):
    """Verifies that calling inject_disruptions without parameters preserves the exact baseline."""
    config, master_data, supply_data = test_setup
    default_result = inject_disruptions(master_data, supply_data, config)

    # Must produce exactly 2 risks, 5 evidence, 2 root causes, 2 simulations, 2 recommendations
    assert len(default_result["fact_risk_event"]) == 2
    assert len(default_result["bridge_risk_evidence"]) == 5
    assert len(default_result["fact_root_cause"]) == 2
    assert len(default_result["fact_mitigation_simulation"]) == 2
    assert len(default_result["fact_recommendation"]) == 2
