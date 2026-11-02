import datetime
from typing import Dict, List
from src.generator.config import GeneratorConfig
from src.models.procurement_inventory import FactPurchaseOrder
from src.models.manufacturing_quality import FactProductionOrder
from src.models.planning import FactMaterialRequirement, FactSupplyPlan
from src.models.control_tower import (
    FactRiskEvent, BridgeRiskEvidence, FactRootCause,
    FactMitigationSimulation, FactRecommendation
)

def inject_disruptions(master_data: Dict, supply_data: Dict, config: GeneratorConfig) -> Dict[str, list]:
    """
    Injects Scenario A: 14-Day API Supplier Delivery Delay and constructs the
    corresponding risk events, linked evidence, root causes, and simulated mitigations.
    """
    
    as_of = config.planning_as_of_date  # 2026-10-26
    
    # Clone and modify affected purchase order for Scenario A
    scenario_pos: List[FactPurchaseOrder] = []
    for po in supply_data["fact_purchase_order"]:
        po_copy = po.model_copy()
        if po.purchase_order_id == "PO-2026-001":
            # 14-day slip
            po_copy.confirmed_delivery_date = po.confirmed_delivery_date + datetime.timedelta(days=14)  # Nov 16, 2026
            po_copy.purchase_order_status = "Delayed"
            po_copy.delay_reason = "Supplier synthesis column breakdown at Deccan API Plant"
        scenario_pos.append(po_copy)

    # Clone and update material requirements under Scenario A
    scenario_mrp: List[FactMaterialRequirement] = []
    for req in supply_data["fact_material_requirement"]:
        req_copy = req.model_copy()
        if req.requirement_id == "REQ-2026-001-API":
            req_copy.scenario_id = "SCN-A-API-DELAY"
            req_copy.expected_receipt_quantity = 0.0  # Arrives too late (Nov 16 > Nov 09 need date)
            req_copy.shortage_quantity = max(0.0, req_copy.required_quantity - req_copy.eligible_available_quantity)  # 127.5 - 80.0 = 47.5 kg
        scenario_mrp.append(req_copy)

    # Clone and update production orders under Scenario A
    scenario_prod: List[FactProductionOrder] = []
    for prod in supply_data["fact_production_order"]:
        prod_copy = prod.model_copy()
        if prod.production_order_id == "PROD-2026-001":
            prod_copy.production_status = "On_Hold"
            prod_copy.delay_reason = "Raw material shortage: 47.5 kg deficit on MAT-API-001"
        scenario_prod.append(prod_copy)

    # Clone and update supply plans under Scenario A
    scenario_spl: List[FactSupplyPlan] = []
    for spl in supply_data["fact_supply_plan"]:
        spl_copy = spl.model_copy()
        if spl.supply_plan_id == "SPL-2026-001":
            spl_copy.scenario_id = "SCN-A-API-DELAY"
            spl_copy.plan_status = "Delayed"
            spl_copy.expected_availability_date = spl.expected_availability_date + datetime.timedelta(days=14)
        scenario_spl.append(spl_copy)

    # --- FACT_RISK_EVENT (Detected Risks for Scenario A) ---
    risk_events = [
        # Risk 1: Upstream Material Deficit
        FactRiskEvent(
            risk_id="RISK-2026-001",
            risk_type="Material_Shortage",
            entity_type="MATERIAL",
            entity_id="MAT-API-001",
            location_id="LOC-PLANT-01",
            detection_date=as_of,
            impact_date=datetime.date(2026, 11, 9),  # Production need-by date
            severity="High",
            # Score: S=80, T=85 (14 days), C=95 (critical API), D=90 (single-source), U=40, R=75 -> ~80.25
            risk_score=80.25,
            shortage_quantity=47.5,
            days_to_impact=14,
            risk_status="Active",
            scenario_id="SCN-A-API-DELAY"
        ),
        # Risk 2: Downstream Market Finished-Goods Stockout
        FactRiskEvent(
            risk_id="RISK-2026-002",
            risk_type="Stockout",
            entity_type="SKU",
            entity_id="SKU-AUG-500-T10",
            location_id="LOC-DC-01",
            detection_date=as_of,
            impact_date=datetime.date(2026, 11, 23),  # Week 4 stockout
            severity="Critical",
            # Score: S=90, T=70 (28 days), C=95, D=80, U=50, R=80 -> ~80.75
            risk_score=84.50,
            shortage_quantity=2400.0,  # Projected net pack shortage in W04
            days_to_impact=28,
            risk_status="Active",
            scenario_id="SCN-A-API-DELAY"
        )
    ]

    # --- BRIDGE_RISK_EVIDENCE (Relational Audit Links) ---
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

    # --- FACT_ROOT_CAUSE (Structured Causal Breakdown) ---
    root_causes = [
        FactRootCause(
            root_cause_id="RC-2026-001",
            risk_id="RISK-2026-001",
            root_cause_category="SUPPLIER_DELIVERY",
            root_cause_description="Supplier SUP-001 confirmed delivery date slipped +14 days to 2026-11-16 due to column breakdown, breaching need-by date 2026-11-09.",
            contributing_factor="Single-source reliance on SUP-001 for MAT-API-001; 20 kg on-hand stock locked in QC quarantine (LOT-API-2026-02-QUAR).",
            causal_sequence="PO-2026-001 Slipped (+14d) -> Inbound Dock Receipt Missed -> Plant API Deficit (47.5 kg) -> PROD-2026-001 Blocked.",
            evidence_complete_flag=True,
            confidence_or_uncertainty_note="Supplier root-cause confirmed via procurement notice; exact internal plant repair duration at supplier remains unmonitored."
        ),
        FactRootCause(
            root_cause_id="RC-2026-002",
            risk_id="RISK-2026-002",
            root_cause_category="UPSTREAM_MATERIAL_SHORTAGE",
            root_cause_description="Finished goods replenishment SPL-2026-001 delayed due to blocked upstream manufacturing PROD-2026-001 at Plant Alpha.",
            contributing_factor="High regional demand in Hyderabad and Pune markets consuming existing DC stock buffer within 21 days.",
            causal_sequence="API Shortage -> Production Postponed -> Finished Batch Release Missed -> Central DC Stock Depletion -> Week 4 Stockout.",
            evidence_complete_flag=True,
            confidence_or_uncertainty_note="Direct causal link proven through linked BOM requirements and production schedules."
        )
    ]

    # --- FACT_MITIGATION_SIMULATION (Simulation Sandbox Results) ---
    simulations = [
        # Option 1: Expedite Supplier PO-2026-001 by 7 days via air freight
        FactMitigationSimulation(
            simulation_id="SIM-2026-001",
            risk_id="RISK-2026-001",
            scenario_id="SCN-A-API-DELAY",
            action_type="SUPPLIER_EXPEDITE",
            action_parameters='{"purchase_order_id": "PO-2026-001", "expedite_days": 7, "mode": "Dedicated_Air_Freight"}',
            baseline_outcome="Material shortage of 47.5 kg on 2026-11-09; production blocked.",
            simulated_outcome="Material arrives 2026-11-09; emergency 48-hr QA release clears API on 2026-11-11; production starts with 2-day shift; W04 stockout averted.",
            risk_reduction=95.0,
            estimated_cost=45000.0,  # INR expediting premium
            feasibility_status="Feasible",
            remaining_constraints="Requires fast-track 48-hour Quality Control release protocol at Plant Alpha."
        ),
        # Option 2: Reallocate 3,000 packs from Western Regional Buffer
        FactMitigationSimulation(
            simulation_id="SIM-2026-002",
            risk_id="RISK-2026-002",
            scenario_id="SCN-A-API-DELAY",
            action_type="INVENTORY_REALLOCATION",
            action_parameters='{"source_location_id": "LOC-DC-01", "destination_market_id": "MKT-IN-HYD", "reallocate_quantity": 3000}',
            baseline_outcome="Projected stockout of 2,400 packs in Week 4 in Hyderabad market.",
            simulated_outcome="3,000 packs transferred via priority road express; covers Week 4 demand; ending buffer 600 packs.",
            risk_reduction=100.0,
            estimated_cost=18000.0,  # INR expedited road transit
            feasibility_status="Feasible",
            remaining_constraints="Reduces DC safety stock buffer in Pune market to 7 days of supply."
        )
    ]

    # --- FACT_RECOMMENDATION (Ranked Human Decision Support Options) ---
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

