"""
Disruption Scenario Injection Engine.
Synthetic Data Generation Engine — Week 03, Day 13 Deliverable.

Implements the benchmark disruption test suite modeling 5 realistic supply chain crises:
1. Scenario A (SCN-A-API-DELAY): 14-day critical API supplier delivery delay (SUP-001, PO-2026-001).
2. Scenario B (SCN-B-BATCH-HOLD): 10-day finished batch QA sterility hold (BATCH-AUG-2026-10, QEV-2026-001).
3. Scenario C (SCN-C-CARTON-SHORTAGE): Shared secondary packaging shortage halting both T10 and T30 SKUs.
4. Scenario D (SCN-D-FEFO-EXPOSURE): Sub-MARSL lot expiry exposure (<90 days remaining shelf life).
5. Scenario E (SCN-E-CAPACITY-CONFLICT): Feasibility conflict / plant packaging line capacity overload (>100%).

Produces:
- Mutated operational scenario records
- Detected risk events with composite scores (0.30S + 0.20T + 0.15C + 0.15D + 0.10U + 0.10R)
- Traceable relational audit links (bridge_risk_evidence)
- Backward causal root-cause graphs (fact_root_cause)
- What-if simulation sandbox projections (fact_mitigation_simulation)
- Governed decision recommendations with mandatory human_approval_required = True
"""

import datetime
from typing import Dict, List, Optional
from src.generator.config import GeneratorConfig
from src.models.procurement_inventory import FactPurchaseOrder
from src.models.manufacturing_quality import FactProductionOrder
from src.models.planning import FactMaterialRequirement, FactSupplyPlan
from src.models.control_tower import (
    FactRiskEvent,
    BridgeRiskEvidence,
    FactRootCause,
    FactMitigationSimulation,
    FactRecommendation
)


def inject_scenario_a(
    master_data: Dict,
    supply_data: Dict,
    config: GeneratorConfig
) -> Dict[str, list]:
    """
    Scenario A: 14-Day Critical API Supplier Delivery Delay.
    Supplier SUP-001 delivery of 150 kg API slips by 14 days, creating a 47.5 kg plant deficit
    and cascading into a Week 4 finished goods stockout of 2,400 packs at DC Nagpur.
    """
    as_of = config.planning_as_of_date  # 2026-10-26

    # 1. Mutated PO
    scenario_pos: List[FactPurchaseOrder] = []
    for po in supply_data["fact_purchase_order"]:
        po_copy = po.model_copy()
        if po.purchase_order_id == "PO-2026-001":
            po_copy.confirmed_delivery_date = po.confirmed_delivery_date + datetime.timedelta(days=14)
            po_copy.purchase_order_status = "Delayed"
            po_copy.delay_reason = "Supplier synthesis column breakdown at Deccan API Plant"
        scenario_pos.append(po_copy)

    # 2. Mutated MRP requirement
    scenario_mrp: List[FactMaterialRequirement] = []
    for req in supply_data["fact_material_requirement"]:
        req_copy = req.model_copy()
        if req.requirement_id == "REQ-2026-001-API":
            req_copy.scenario_id = "SCN-A-API-DELAY"
            req_copy.expected_receipt_quantity = 0.0
            req_copy.shortage_quantity = max(0.0, req_copy.required_quantity - req_copy.eligible_available_quantity)
        scenario_mrp.append(req_copy)

    # 3. Mutated Production Order
    scenario_prod: List[FactProductionOrder] = []
    for prod in supply_data["fact_production_order"]:
        prod_copy = prod.model_copy()
        if prod.production_order_id == "PROD-2026-001":
            prod_copy.production_status = "On_Hold"
            prod_copy.delay_reason = "Raw material shortage: 47.5 kg deficit on MAT-API-001"
        scenario_prod.append(prod_copy)

    # 4. Mutated Supply Plan
    scenario_spl: List[FactSupplyPlan] = []
    for spl in supply_data["fact_supply_plan"]:
        spl_copy = spl.model_copy()
        if spl.supply_plan_id == "SPL-2026-001":
            spl_copy.scenario_id = "SCN-A-API-DELAY"
            spl_copy.plan_status = "Delayed"
            spl_copy.expected_availability_date = spl.expected_availability_date + datetime.timedelta(days=14)
        scenario_spl.append(spl_copy)

    # 5. Detected Risks
    risk_events = [
        FactRiskEvent(
            risk_id="RISK-2026-001",
            risk_type="Material_Shortage",
            entity_type="MATERIAL",
            entity_id="MAT-API-001",
            location_id="LOC-PLANT-01",
            detection_date=as_of,
            impact_date=datetime.date(2026, 11, 9),
            severity="High",
            risk_score=80.25,
            shortage_quantity=47.5,
            days_to_impact=14,
            risk_status="Active",
            scenario_id="SCN-A-API-DELAY"
        ),
        FactRiskEvent(
            risk_id="RISK-2026-002",
            risk_type="Stockout",
            entity_type="SKU",
            entity_id="SKU-AUG-500-T10",
            location_id="LOC-DC-01",
            detection_date=as_of,
            impact_date=datetime.date(2026, 11, 23),
            severity="Critical",
            risk_score=84.50,
            shortage_quantity=2400.0,
            days_to_impact=28,
            risk_status="Active",
            scenario_id="SCN-A-API-DELAY"
        )
    ]

    # 6. Relational Evidence Links
    risk_evidence = [
        BridgeRiskEvidence(
            risk_id="RISK-2026-001",
            evidence_type="PURCHASE_ORDER",
            evidence_record_id="PO-2026-001",
            evidence_role="DIRECT_CAUSE",
            evidence_description="Supplier SUP-001 delivery slipped from 2026-11-02 to 2026-11-16 (14-day delay)."
        ),
        BridgeRiskEvidence(
            risk_id="RISK-2026-001",
            evidence_type="INVENTORY_LOT",
            evidence_record_id="LOT-API-2026-01",
            evidence_role="CONTRIBUTING_FACTOR",
            evidence_description="Plant on-hand eligible API stock is 80 kg, insufficient to cover 127.5 kg requirement."
        ),
        BridgeRiskEvidence(
            risk_id="RISK-2026-001",
            evidence_type="PRODUCTION_ORDER",
            evidence_record_id="PROD-2026-001",
            evidence_role="IMPACTED_OBJECT",
            evidence_description="Production of 20,000 packs of Augmentin T10 cannot commence on 2026-11-09."
        ),
        BridgeRiskEvidence(
            risk_id="RISK-2026-002",
            evidence_type="PRODUCTION_ORDER",
            evidence_record_id="PROD-2026-001",
            evidence_role="DIRECT_CAUSE",
            evidence_description="Delayed batch output from Plant Alpha leaves DC Nagpur without planned 20,000 pack replenishment."
        ),
        BridgeRiskEvidence(
            risk_id="RISK-2026-002",
            evidence_type="INVENTORY_LOT",
            evidence_record_id="LOT-FG-AUG-T10-26A",
            evidence_role="CONTRIBUTING_FACTOR",
            evidence_description="DC unreserved stock of 16,000 packs is depleted by baseline customer demand across Weeks 1-3."
        )
    ]

    # 7. Root Cause Causal Graphs
    root_causes = [
        FactRootCause(
            root_cause_id="RC-2026-001",
            risk_id="RISK-2026-001",
            root_cause_category="SUPPLIER_DELIVERY",
            root_cause_description="Supplier SUP-001 confirmed delivery date slipped +14 days to 2026-11-16 due to column breakdown.",
            contributing_factor="Single-source reliance on SUP-001 for MAT-API-001; 20 kg on-hand stock locked in QC quarantine.",
            causal_sequence="PO-2026-001 Slipped (+14d) -> Inbound Dock Receipt Missed -> Plant API Deficit (47.5 kg) -> PROD-2026-001 Blocked.",
            evidence_complete_flag=True,
            confidence_or_uncertainty_note="Supplier root-cause confirmed via procurement notice."
        ),
        FactRootCause(
            root_cause_id="RC-2026-002",
            risk_id="RISK-2026-002",
            root_cause_category="UPSTREAM_MATERIAL_SHORTAGE",
            root_cause_description="Finished goods replenishment SPL-2026-001 delayed due to blocked upstream manufacturing PROD-2026-001.",
            contributing_factor="High regional demand in Hyderabad and Pune markets consuming existing DC stock buffer within 21 days.",
            causal_sequence="API Shortage -> Production Postponed -> Finished Batch Release Missed -> Central DC Stock Depletion -> Week 4 Stockout.",
            evidence_complete_flag=True,
            confidence_or_uncertainty_note="Direct causal link proven through linked BOM requirements and production schedules."
        )
    ]

    # 8. Mitigation Simulations
    simulations = [
        FactMitigationSimulation(
            simulation_id="SIM-2026-001",
            risk_id="RISK-2026-001",
            scenario_id="SCN-A-API-DELAY",
            action_type="SUPPLIER_EXPEDITE",
            action_parameters='{"purchase_order_id": "PO-2026-001", "expedite_days": 7, "mode": "Dedicated_Air_Freight"}',
            baseline_outcome="Material shortage of 47.5 kg on 2026-11-09; production blocked.",
            simulated_outcome="Material arrives 2026-11-09; emergency 48-hr QA release clears API on 2026-11-11; production starts with 2-day shift; W04 stockout averted.",
            risk_reduction=95.0,
            estimated_cost=45000.0,
            feasibility_status="Feasible",
            remaining_constraints="Requires fast-track 48-hour Quality Control release protocol at Plant Alpha."
        ),
        FactMitigationSimulation(
            simulation_id="SIM-2026-002",
            risk_id="RISK-2026-002",
            scenario_id="SCN-A-API-DELAY",
            action_type="INVENTORY_REALLOCATION",
            action_parameters='{"source_location_id": "LOC-DC-01", "destination_market_id": "MKT-IN-HYD", "reallocate_quantity": 3000}',
            baseline_outcome="Projected stockout of 2,400 packs in Week 4 in Hyderabad market.",
            simulated_outcome="3,000 packs transferred via priority road express; covers Week 4 demand; ending buffer 600 packs.",
            risk_reduction=100.0,
            estimated_cost=18000.0,
            feasibility_status="Feasible",
            remaining_constraints="Reduces DC safety stock buffer in Pune market to 7 days of supply."
        )
    ]

    # 9. Governed Decision Recommendations
    recommendations = [
        FactRecommendation(
            recommendation_id="REC-2026-001",
            risk_id="RISK-2026-001",
            simulation_id="SIM-2026-001",
            recommended_action="Expedite purchase order PO-2026-001 with Supplier SUP-001 via priority dedicated air transit.",
            recommended_quantity=150.0,
            expected_benefit="Recovers 7 days of delivery slip; allows PROD-2026-001 to commence with minimal 48-hour schedule shift, preventing downstream stockout.",
            estimated_cost=45000.0,
            feasibility_status="Feasible",
            evidence_reference="PO-2026-001, PROD-2026-001, SUP-001",
            human_approval_required=True,
            approval_status="Pending_Review",
            created_date=as_of
        ),
        FactRecommendation(
            recommendation_id="REC-2026-002",
            risk_id="RISK-2026-002",
            simulation_id="SIM-2026-002",
            recommended_action="Execute inter-node emergency stock transfer of 3,000 packs of Augmentin T10 to Hyderabad market hub.",
            recommended_quantity=3000.0,
            expected_benefit="Guarantees 100% customer fulfilment across Week 4 while production catch-up batch completes.",
            estimated_cost=18000.0,
            feasibility_status="Feasible",
            evidence_reference="LOT-FG-AUG-T10-26A, MKT-IN-HYD",
            human_approval_required=True,
            approval_status="Pending_Review",
            created_date=as_of
        )
    ]

    return {
        "fact_purchase_order_scenario": scenario_pos,
        "fact_material_requirement_scenario": scenario_mrp,
        "fact_production_order_scenario": scenario_prod,
        "fact_supply_plan_scenario": scenario_spl,
        "fact_risk_event": risk_events,
        "bridge_risk_evidence": risk_evidence,
        "fact_root_cause": root_causes,
        "fact_mitigation_simulation": simulations,
        "fact_recommendation": recommendations
    }


def inject_scenario_b(as_of: datetime.date) -> Dict[str, list]:
    """
    Scenario B: 10-Day Finished Batch QA Release Hold.
    Batch BATCH-AUG-2026-10 triggers sterility retest deviation QEV-2026-001.
    """
    risk = FactRiskEvent(
        risk_id="RISK-2026-003",
        risk_type="QA_Hold",
        entity_type="BATCH",
        entity_id="BATCH-AUG-2026-10",
        location_id="LOC-PLANT-01",
        detection_date=as_of,
        impact_date=datetime.date(2026, 11, 2),
        severity="High",
        risk_score=72.50,
        shortage_quantity=15000.0,
        days_to_impact=7,
        risk_status="Active",
        scenario_id="SCN-B-BATCH-HOLD"
    )
    evidence = [
        BridgeRiskEvidence(
            risk_id="RISK-2026-003",
            evidence_type="BATCH",
            evidence_record_id="BATCH-AUG-2026-10",
            evidence_role="DIRECT_CAUSE",
            evidence_description="Batch actual release delayed +10 days pending sterility retest results."
        ),
        BridgeRiskEvidence(
            risk_id="RISK-2026-003",
            evidence_type="QUALITY_EVENT",
            evidence_record_id="QEV-2026-001",
            evidence_role="ROOT_CAUSE_INVESTIGATION",
            evidence_description="Routine QA testing deviation logged in plant cleanroom incubation protocol."
        )
    ]
    root_cause = FactRootCause(
        root_cause_id="RC-2026-003",
        risk_id="RISK-2026-003",
        root_cause_category="QUALITY_HOLD",
        root_cause_description="Sterility test incubator drift triggered automated retest investigation.",
        contributing_factor="Routine microbiological assay standard operating procedure requires 10-day incubation cycle.",
        causal_sequence="Incubation Sensor Alert -> OOS Investigation Logged -> Quarantine Imposed -> Release Delayed.",
        evidence_complete_flag=True,
        confidence_or_uncertainty_note="QC laboratory investigation logged and signed off by QA officer."
    )
    simulation = FactMitigationSimulation(
        simulation_id="SIM-2026-003",
        risk_id="RISK-2026-003",
        scenario_id="SCN-B-BATCH-HOLD",
        action_type="EXPEDITE_QC_TESTING",
        action_parameters='{"batch_id": "BATCH-AUG-2026-10", "retest_protocol": "Rapid_Microbial_Screening"}',
        baseline_outcome="Batch release delayed 10 days; hospital replenishment order shorted.",
        simulated_outcome="Rapid microbial test clears batch in 4 days; releases 15,000 packs on Nov 03.",
        risk_reduction=85.0,
        estimated_cost=25000.0,
        feasibility_status="Feasible",
        remaining_constraints="Requires Qualified Person sign-off on rapid assay CoA."
    )
    recommendation = FactRecommendation(
        recommendation_id="REC-2026-003",
        risk_id="RISK-2026-003",
        simulation_id="SIM-2026-003",
        recommended_action="Authorize rapid microbial testing protocol for Batch BATCH-AUG-2026-10 to accelerate QA clearance.",
        recommended_quantity=15000.0,
        expected_benefit="Recovers 6 days of testing delay, releasing 15,000 packs before regional DC buffer depletes.",
        estimated_cost=25000.0,
        feasibility_status="Feasible",
        evidence_reference="BATCH-AUG-2026-10, QEV-2026-001",
        human_approval_required=True,
        approval_status="Pending_Review",
        created_date=as_of
    )
    return {
        "fact_risk_event": [risk],
        "bridge_risk_evidence": evidence,
        "fact_root_cause": [root_cause],
        "fact_mitigation_simulation": [simulation],
        "fact_recommendation": [recommendation]
    }


def inject_scenario_c(as_of: datetime.date) -> Dict[str, list]:
    """
    Scenario C: Shared Packaging Component Shortage.
    Carton shortage on MAT-PKG-CART simultaneously blocks T10 strip and T30 bottle packaging lines.
    """
    risk = FactRiskEvent(
        risk_id="RISK-2026-004",
        risk_type="Material_Shortage",
        entity_type="MATERIAL",
        entity_id="MAT-PKG-CART",
        location_id="LOC-PLANT-01",
        detection_date=as_of,
        impact_date=datetime.date(2026, 11, 5),
        severity="Critical",
        risk_score=88.00,
        shortage_quantity=40000.0,
        days_to_impact=10,
        risk_status="Active",
        scenario_id="SCN-C-CARTON-SHORTAGE"
    )
    evidence = [
        BridgeRiskEvidence(
            risk_id="RISK-2026-004",
            evidence_type="MATERIAL",
            evidence_record_id="MAT-PKG-CART",
            evidence_role="DIRECT_CAUSE",
            evidence_description="Supplier SUP-002 carton converting shortage impacts MAT-PKG-CART."
        ),
        BridgeRiskEvidence(
            risk_id="RISK-2026-004",
            evidence_type="PRODUCTION_ORDER",
            evidence_record_id="PROD-2026-001",
            evidence_role="IMPACTED_OBJECT",
            evidence_description="Halts 20,000 pack Augmentin T10 packaging run."
        ),
        BridgeRiskEvidence(
            risk_id="RISK-2026-004",
            evidence_type="PRODUCTION_ORDER",
            evidence_record_id="PROD-2026-002",
            evidence_role="IMPACTED_OBJECT",
            evidence_description="Halts 10,000 pack Augmentin T30 packaging run."
        )
    ]
    root_cause = FactRootCause(
        root_cause_id="RC-2026-004",
        risk_id="RISK-2026-004",
        root_cause_category="SHARED_COMPONENT_SHORTAGE",
        root_cause_description="Outer carton component shared across both finished presentation formats.",
        contributing_factor="Single certified packaging converter for printed pharmaceutical cartons.",
        causal_sequence="Converter Paperboard Shortage -> Carton Dispatch Delayed -> Both Packaging Lines Blocked.",
        evidence_complete_flag=True,
        confidence_or_uncertainty_note="Confirmed via supplier notice."
    )
    simulation = FactMitigationSimulation(
        simulation_id="SIM-2026-004",
        risk_id="RISK-2026-004",
        scenario_id="SCN-C-CARTON-SHORTAGE",
        action_type="EMERGENCY_SOURCING",
        action_parameters='{"material_sku_id": "MAT-PKG-CART", "backup_supplier": "Pune_Converter_Alt", "quantity": 40000}',
        baseline_outcome="Both T10 and T30 lines stopped; 30,000 packs delayed.",
        simulated_outcome="Secondary qualified box maker delivers 40,000 cartons in 5 days; lines restart on schedule.",
        risk_reduction=90.0,
        estimated_cost=35000.0,
        feasibility_status="Feasible",
        remaining_constraints="Requires fast-track artwork verification check."
    )
    recommendation = FactRecommendation(
        recommendation_id="REC-2026-004",
        risk_id="RISK-2026-004",
        simulation_id="SIM-2026-004",
        recommended_action="Execute emergency purchase order with secondary certified packaging supplier for 40,000 cartons.",
        recommended_quantity=40000.0,
        expected_benefit="Restores shared component availability, unblocking both T10 and T30 lines simultaneously.",
        estimated_cost=35000.0,
        feasibility_status="Feasible",
        evidence_reference="MAT-PKG-CART, PROD-2026-001, PROD-2026-002",
        human_approval_required=True,
        approval_status="Pending_Review",
        created_date=as_of
    )
    return {
        "fact_risk_event": [risk],
        "bridge_risk_evidence": evidence,
        "fact_root_cause": [root_cause],
        "fact_mitigation_simulation": [simulation],
        "fact_recommendation": [recommendation]
    }


def inject_scenario_d(as_of: datetime.date) -> Dict[str, list]:
    """
    Scenario D: Sub-MARSL Lot Expiry Exposure.
    Finished lot LOT-FG-AUG-T10-24X has remaining shelf life < 90 days, breaching hospital MARSL.
    """
    risk = FactRiskEvent(
        risk_id="RISK-2026-005",
        risk_type="Expiry_Risk",
        entity_type="INVENTORY_LOT",
        entity_id="LOT-FG-AUG-T10-24X",
        location_id="LOC-DC-01",
        detection_date=as_of,
        impact_date=datetime.date(2026, 11, 20),
        severity="Medium",
        risk_score=68.00,
        shortage_quantity=3000.0,
        days_to_impact=25,
        risk_status="Active",
        scenario_id="SCN-D-FEFO-EXPOSURE"
    )
    evidence = [
        BridgeRiskEvidence(
            risk_id="RISK-2026-005",
            evidence_type="INVENTORY_LOT",
            evidence_record_id="LOT-FG-AUG-T10-24X",
            evidence_role="DIRECT_CAUSE",
            evidence_description="Lot has 25 days remaining shelf life, failing market MARSL acceptance threshold."
        ),
        BridgeRiskEvidence(
            risk_id="RISK-2026-005",
            evidence_type="MARKET",
            evidence_record_id="MKT-IN-HYD",
            evidence_role="THRESHOLD_CONSTRAINT",
            evidence_description="Institutional hospital tender market requires >= 180 days MARSL at receiving dock."
        )
    ]
    root_cause = FactRootCause(
        root_cause_id="RC-2026-005",
        risk_id="RISK-2026-005",
        root_cause_category="SHELF_LIFE_EXPIRATION",
        root_cause_description="Lot aged past hospital tender shelf-life acceptance window.",
        contributing_factor="Older batch was not prioritized in earlier replenishment cycles.",
        causal_sequence="Aging Stock -> Sub-MARSL Shelf Life -> Hospital Acceptance Disqualification -> Dead Inventory.",
        evidence_complete_flag=True,
        confidence_or_uncertainty_note="Verified via batch expiry date."
    )
    simulation = FactMitigationSimulation(
        simulation_id="SIM-2026-005",
        risk_id="RISK-2026-005",
        scenario_id="SCN-D-FEFO-EXPOSURE",
        action_type="DISCOUNT_CHANNEL_REALLOCATION",
        action_parameters='{"lot_id": "LOT-FG-AUG-T10-24X", "channel": "Retail_Emergency_Clinic_Tender", "discount_pct": 15}',
        baseline_outcome="3,000 packs write-off destruction loss of ₹4,80,000.",
        simulated_outcome="3,000 packs liquidated to rapid-dispensing urban clinic network within 10 days; 0 packs expired.",
        risk_reduction=92.0,
        estimated_cost=12000.0,
        feasibility_status="Feasible",
        remaining_constraints="Requires fast-track commercial sales sign-off."
    )
    recommendation = FactRecommendation(
        recommendation_id="REC-2026-005",
        risk_id="RISK-2026-005",
        simulation_id="SIM-2026-005",
        recommended_action="Reallocate 3,000 packs of LOT-FG-AUG-T10-24X to rapid short-cycle retail pharmacy tender at 15% promotional discount.",
        recommended_quantity=3000.0,
        expected_benefit="Recovers ₹4.68L in inventory value before expiration and prevents ₹4.80L physical stock write-off.",
        estimated_cost=12000.0,
        feasibility_status="Feasible",
        evidence_reference="LOT-FG-AUG-T10-24X, MKT-IN-HYD",
        human_approval_required=True,
        approval_status="Pending_Review",
        created_date=as_of
    )
    return {
        "fact_risk_event": [risk],
        "bridge_risk_evidence": evidence,
        "fact_root_cause": [root_cause],
        "fact_mitigation_simulation": [simulation],
        "fact_recommendation": [recommendation]
    }


def inject_scenario_e(as_of: datetime.date) -> Dict[str, list]:
    """
    Scenario E: Mitigation Feasibility Conflict / Line Capacity Overload.
    Proposed mitigation to run catch-up production on LINE-PLANT1-01 exceeds 100% capacity.
    """
    risk = FactRiskEvent(
        risk_id="RISK-2026-006",
        risk_type="Capacity_Overload",
        entity_type="PRODUCTION_LINE",
        entity_id="LINE-PLANT1-01",
        location_id="LOC-PLANT-01",
        detection_date=as_of,
        impact_date=datetime.date(2026, 11, 9),
        severity="High",
        risk_score=79.00,
        shortage_quantity=20.0,  # hours over committed
        days_to_impact=14,
        risk_status="Active",
        scenario_id="SCN-E-CAPACITY-CONFLICT"
    )
    evidence = [
        BridgeRiskEvidence(
            risk_id="RISK-2026-006",
            evidence_type="PRODUCTION_LINE",
            evidence_record_id="LINE-PLANT1-01",
            evidence_role="DIRECT_CAUSE",
            evidence_description="Packaging line committed hours exceed net available hours (140 hrs vs 120 hrs = 116.7%)."
        ),
        BridgeRiskEvidence(
            risk_id="RISK-2026-006",
            evidence_type="CAPACITY",
            evidence_record_id="CAP-PLANT1-01-W03",
            evidence_role="CAPACITY_CONSTRAINT",
            evidence_description="Line booked beyond maximum 120 operating hours."
        )
    ]
    root_cause = FactRootCause(
        root_cause_id="RC-2026-006",
        risk_id="RISK-2026-006",
        root_cause_category="CAPACITY_BOTTLENECK",
        root_cause_description="Proposed catch-up production order exceeds line operating hours.",
        contributing_factor="Scheduled preventive maintenance of 8 hours locks out Sunday shift.",
        causal_sequence="Shortage Mitigation Requested -> Extra Batch Added -> 140 Hours Booked -> 116.7% Overload.",
        evidence_complete_flag=True,
        confidence_or_uncertainty_note="Derived deterministically from line capacity table."
    )
    simulation = FactMitigationSimulation(
        simulation_id="SIM-2026-006",
        risk_id="RISK-2026-006",
        scenario_id="SCN-E-CAPACITY-CONFLICT",
        action_type="WEEKEND_OVERTIME_OR_CMO",
        action_parameters='{"line_id": "LINE-PLANT1-01", "additional_shift": "Weekend_3rd_Shift", "cost_premium": 60000}',
        baseline_outcome="Production order rejected due to line capacity overload.",
        simulated_outcome="Authorizing 3rd shift weekend overtime adds 24 operating hours; utilization drops to 97.2%; feasible.",
        risk_reduction=95.0,
        estimated_cost=60000.0,
        feasibility_status="Feasible",
        remaining_constraints="Requires plant labor union approval and overtime shift differential."
    )
    recommendation = FactRecommendation(
        recommendation_id="REC-2026-006",
        risk_id="RISK-2026-006",
        simulation_id="SIM-2026-006",
        recommended_action="Reject unconstrained line loading (INFEASIBLE_CAPACITY). Authorize 24-hour weekend 3rd shift overtime differential to expand line capacity.",
        recommended_quantity=20000.0,
        expected_benefit="Resolves capacity overload, allowing catch-up production run to proceed while respecting safety maintenance windows.",
        estimated_cost=60000.0,
        feasibility_status="Feasible",
        evidence_reference="LINE-PLANT1-01, CAP-PLANT1-01-W03",
        human_approval_required=True,
        approval_status="Pending_Review",
        created_date=as_of
    )
    return {
        "fact_risk_event": [risk],
        "bridge_risk_evidence": evidence,
        "fact_root_cause": [root_cause],
        "fact_mitigation_simulation": [simulation],
        "fact_recommendation": [recommendation]
    }


def inject_disruptions(
    master_data: Dict,
    supply_data: Dict,
    config: GeneratorConfig,
    scenarios: Optional[List[str]] = None
) -> Dict[str, list]:
    """
    Main disruption engine entry point for Week 03, Day 13.
    By default (scenarios is None or contains SCN-A-API-DELAY), injects Scenario A matching the
    Phase 1 production baseline.
    If include_all_benchmarks is desired, callers can pass all scenario IDs to get the full suite.
    """
    as_of = config.planning_as_of_date

    # Always inject Scenario A baseline
    result_a = inject_scenario_a(master_data, supply_data, config)

    if scenarios is None or scenarios == ["SCN-A-API-DELAY"]:
        return result_a

    # If extended benchmark suite requested, aggregate all scenarios
    aggregated = {
        "fact_purchase_order_scenario": result_a["fact_purchase_order_scenario"],
        "fact_material_requirement_scenario": result_a["fact_material_requirement_scenario"],
        "fact_production_order_scenario": result_a["fact_production_order_scenario"],
        "fact_supply_plan_scenario": result_a["fact_supply_plan_scenario"],
        "fact_risk_event": list(result_a["fact_risk_event"]),
        "bridge_risk_evidence": list(result_a["bridge_risk_evidence"]),
        "fact_root_cause": list(result_a["fact_root_cause"]),
        "fact_mitigation_simulation": list(result_a["fact_mitigation_simulation"]),
        "fact_recommendation": list(result_a["fact_recommendation"])
    }

    if "SCN-B-BATCH-HOLD" in scenarios:
        res_b = inject_scenario_b(as_of)
        for k in ["fact_risk_event", "bridge_risk_evidence", "fact_root_cause", "fact_mitigation_simulation", "fact_recommendation"]:
            aggregated[k].extend(res_b[k])

    if "SCN-C-CARTON-SHORTAGE" in scenarios:
        res_c = inject_scenario_c(as_of)
        for k in ["fact_risk_event", "bridge_risk_evidence", "fact_root_cause", "fact_mitigation_simulation", "fact_recommendation"]:
            aggregated[k].extend(res_c[k])

    if "SCN-D-FEFO-EXPOSURE" in scenarios:
        res_d = inject_scenario_d(as_of)
        for k in ["fact_risk_event", "bridge_risk_evidence", "fact_root_cause", "fact_mitigation_simulation", "fact_recommendation"]:
            aggregated[k].extend(res_d[k])

    if "SCN-E-CAPACITY-CONFLICT" in scenarios:
        res_e = inject_scenario_e(as_of)
        for k in ["fact_risk_event", "bridge_risk_evidence", "fact_root_cause", "fact_mitigation_simulation", "fact_recommendation"]:
            aggregated[k].extend(res_e[k])

    return aggregated
