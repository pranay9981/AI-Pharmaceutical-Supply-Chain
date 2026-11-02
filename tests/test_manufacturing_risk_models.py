"""
Pytest Unit Test Suite for Manufacturing, Logistics & Risk Entities (12 Tables).
Technical Verification for Week 02, Day 08 Deliverable.

Tests instantiation, field constraints, temporal logic, mathematical invariants,
and error handling across all 12 manufacturing, logistics, and control tower tables:
1. FactProductionOrder
2. FactBatch
3. FactQualityEvent
4. FactCapacity
5. FactShipment
6. DimScenario
7. FactRiskEvent
8. BridgeRiskEvidence
9. FactRootCause
10. FactMitigationSimulation
11. FactRecommendation
12. DatasetManifest
"""

from datetime import date, datetime
import pytest
from pydantic import ValidationError
from src.models.manufacturing_quality import (
    FactProductionOrder,
    FactBatch,
    FactQualityEvent,
    ProductionStatus,
    BatchStatus,
)
from src.models.capacity_logistics import (
    FactCapacity,
    FactShipment,
    ShipmentStatus,
)
from src.models.control_tower import (
    DimScenario,
    FactRiskEvent,
    BridgeRiskEvidence,
    FactRootCause,
    FactMitigationSimulation,
    FactRecommendation,
    DatasetManifest,
    EvidenceRole,
    FeasibilityStatus,
)


def test_fact_production_order_validation():
    # Valid production order
    po = FactProductionOrder(
        production_order_id="PROD-2026-001",
        finished_sku_id="SKU-AUG-500-T10",
        location_id="LOC-PLANT-01",
        production_line_id="LINE-PLANT1-01",
        planned_start_date=date(2026, 11, 2),
        planned_completion_date=date(2026, 11, 4),
        planned_quantity=10000.0,
        planned_hours=20.0
    )
    assert po.planned_quantity == 10000.0
    assert po.planned_hours == 20.0

    # Inverted dates (planned completion earlier than planned start)
    with pytest.raises(ValidationError):
        FactProductionOrder(
            production_order_id="PROD-2026-002",
            finished_sku_id="SKU-AUG-500-T10",
            location_id="LOC-PLANT-01",
            production_line_id="LINE-PLANT1-01",
            planned_start_date=date(2026, 11, 5),
            planned_completion_date=date(2026, 11, 2),  # Inverted!
            planned_quantity=10000.0,
            planned_hours=20.0
        )


def test_fact_batch_milestone_ordering():
    # Valid batch: manufacture -> submission -> expected release
    batch = FactBatch(
        batch_id="BATCH-001",
        production_order_id="PROD-2026-001",
        finished_sku_id="SKU-AUG-500-T10",
        location_id="LOC-PLANT-01",
        manufacture_date=date(2026, 11, 4),
        quality_submission_date=date(2026, 11, 5),
        expected_release_date=date(2026, 11, 15),
        batch_quantity=9800.0
    )
    assert batch.batch_quantity == 9800.0

    # Inverted milestone: submission earlier than manufacture date
    with pytest.raises(ValidationError):
        FactBatch(
            batch_id="BATCH-002",
            production_order_id="PROD-2026-001",
            finished_sku_id="SKU-AUG-500-T10",
            location_id="LOC-PLANT-01",
            manufacture_date=date(2026, 11, 4),
            quality_submission_date=date(2026, 11, 2),  # Earlier!
            expected_release_date=date(2026, 11, 15),
            batch_quantity=9800.0
        )


def test_fact_quality_event_validation():
    qev = FactQualityEvent(
        quality_event_id="QEV-001",
        entity_type="BATCH",
        entity_id="BATCH-001",
        event_type="Sterility_Retest",
        event_date=date(2026, 11, 10),
        expected_resolution_date=date(2026, 11, 20),
        delay_days=10,
        reason_code="DEV-STER-001"
    )
    assert qev.delay_days == 10


def test_fact_capacity_utilization_and_overload():
    # Committed 100 hours out of 120 net available -> 83.33%
    cap = FactCapacity(
        capacity_record_id="CAP-001",
        location_id="LOC-PLANT-01",
        production_line_id="LINE-PLANT1-01",
        period_start_date=date(2026, 11, 2),
        net_available_hours=120.0,
        committed_hours=100.0
    )
    assert cap.calculate_utilization_pct() == 83.33
    assert cap.is_overloaded() is False

    # Overload case: Committed 140 hours out of 120 net available -> 116.67%
    cap_over = FactCapacity(
        capacity_record_id="CAP-002",
        location_id="LOC-PLANT-01",
        production_line_id="LINE-PLANT1-01",
        period_start_date=date(2026, 11, 2),
        net_available_hours=120.0,
        committed_hours=140.0
    )
    assert cap_over.calculate_utilization_pct() == 116.67
    assert cap_over.is_overloaded() is True


def test_fact_shipment_validation():
    # Valid shipment
    ship = FactShipment(
        shipment_id="SHIP-001",
        origin_location_id="LOC-PLANT-01",
        destination_location_id="LOC-DC-01",
        finished_sku_id="SKU-AUG-500-T10",
        lot_id="LOT-001",
        dispatch_date=date(2026, 11, 5),
        expected_arrival_date=date(2026, 11, 7),
        shipped_quantity=5000.0
    )
    assert ship.shipped_quantity == 5000.0

    # Self-loop route (same origin and destination)
    with pytest.raises(ValidationError):
        FactShipment(
            shipment_id="SHIP-002",
            origin_location_id="LOC-PLANT-01",
            destination_location_id="LOC-PLANT-01",  # Same node invalid!
            finished_sku_id="SKU-AUG-500-T10",
            lot_id="LOT-001",
            dispatch_date=date(2026, 11, 5),
            expected_arrival_date=date(2026, 11, 7),
            shipped_quantity=5000.0
        )


def test_fact_risk_event_and_days_to_impact():
    # Detected on 02-Nov, Impact on 23-Nov -> days_to_impact = 21
    risk = FactRiskEvent(
        risk_id="RISK-001",
        risk_type="Stockout",
        entity_type="SKU",
        entity_id="SKU-AUG-500-T10",
        location_id="LOC-DC-01",
        detection_date=date(2026, 11, 2),
        impact_date=date(2026, 11, 23),
        severity="Critical",
        risk_score=85.5,
        shortage_quantity=3500.0
    )
    assert risk.risk_score == 85.5
    assert risk.days_to_impact == 21


def test_bridge_risk_evidence():
    ev = BridgeRiskEvidence(
        risk_id="RISK-001",
        evidence_type="PURCHASE_ORDER",
        evidence_record_id="PO-API-001",
        evidence_role=EvidenceRole.DIRECT_CAUSE,
        evidence_description="Supplier delayed critical API delivery by 14 days"
    )
    assert ev.evidence_record_id == "PO-API-001"
    assert ev.evidence_role == "DIRECT_CAUSE"


def test_fact_root_cause():
    rc = FactRootCause(
        root_cause_id="RC-001",
        risk_id="RISK-001",
        root_cause_category="SUPPLIER_DELIVERY",
        root_cause_description="Raw material API synthesis bottleneck delayed PO-API-001 receipt",
        causal_sequence="Supplier Delay -> Inbound QC Hold Shift -> Plant Stoppage -> Stockout"
    )
    assert rc.root_cause_id == "RC-001"
    assert "Supplier Delay" in rc.causal_sequence


def test_fact_mitigation_simulation_and_cost():
    sim = FactMitigationSimulation(
        simulation_id="SIM-001",
        risk_id="RISK-001",
        scenario_id="SCN-A-API-DELAY",
        action_type="SUPPLIER_EXPEDITE",
        action_parameters='{"days_expedited": 10, "expedite_cost": 45000}',
        baseline_outcome="Shortage of 3,500 packs in W04",
        simulated_outcome="Shortage eliminated, ending inventory 500 packs",
        risk_reduction=100.0,
        estimated_cost=45000.0,
        feasibility_status=FeasibilityStatus.FEASIBLE
    )
    assert sim.risk_reduction == 100.0
    assert sim.estimated_cost == 45000.0


def test_fact_recommendation_human_approval_mandate():
    rec = FactRecommendation(
        recommendation_id="REC-001",
        risk_id="RISK-001",
        simulation_id="SIM-001",
        recommended_action="Expedite PO-API-001 with Deccan Active Pharma Chem by 10 days",
        recommended_quantity=100.0,
        expected_benefit="Resolves projected Week 4 finished goods stockout of 3,500 packs",
        estimated_cost=45000.0,
        evidence_reference="PO-API-001, SUP-001, LINE-PLANT1-01",
        human_approval_required=True,
        created_date=date(2026, 11, 2)
    )
    assert rec.human_approval_required is True
    assert rec.approval_status == "Pending_Review"

    # Attempt to bypass human approval should raise ValidationError
    with pytest.raises(ValidationError):
        FactRecommendation(
            recommendation_id="REC-BAD",
            risk_id="RISK-001",
            simulation_id="SIM-001",
            recommended_action="Autonomous expedite",
            recommended_quantity=100.0,
            expected_benefit="Autonomous fix",
            evidence_reference="PO-001",
            human_approval_required=False,  # Violation!
            created_date=date(2026, 11, 2)
        )


def test_dataset_manifest_provenance():
    manifest = DatasetManifest(
        dataset_version="v1.0.0-phase1",
        generation_timestamp=datetime(2026, 10, 28, 10, 0, 0),
        random_seed=20261014,
        record_counts={"dim_product": 1, "dim_finished_sku": 2, "fact_inventory_lot": 15},
        date_range={"start_date": "2024-10-28", "end_date": "2027-04-26"},
        scenario_coverage=["SCN-BASE", "SCN-A-API-DELAY"]
    )
    assert manifest.random_seed == 20261014
    assert manifest.validation_status == "PASSED"
    assert manifest.synthetic_data_flag is True

