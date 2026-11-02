import datetime
from typing import List, Dict
from src.generator.config import GeneratorConfig
from src.models.procurement_inventory import FactPurchaseOrder, FactInventoryLot, FactMaterialConsumption
from src.models.manufacturing_quality import FactProductionOrder, FactBatch, FactQualityEvent
from src.models.capacity_logistics import FactCapacity, FactShipment
from src.models.planning import FactSupplyPlan, FactMaterialRequirement

def generate_supply_and_operations_data(config: GeneratorConfig) -> Dict[str, list]:
    """Generates inventory lots, purchase orders, production plans, batches, capacity, and shipments."""
    
    as_of = config.planning_as_of_date  # 2026-10-26
    
    # --- 1. FACT_INVENTORY_LOT (Lot-Level Inventory Position) ---
    inventory_lots = [
        # RAW MATERIALS AT PLANT ALPHA (LOC-PLANT-01)
        # API MAT-API-001: 80 kg eligible released lot
        FactInventoryLot(
            lot_id="LOT-API-2026-01",
            item_type="RAW_MATERIAL",
            item_id="MAT-API-001",
            location_id="LOC-PLANT-01",
            batch_id=None,
            manufacture_date=datetime.date(2026, 4, 15),
            expiry_date=datetime.date(2027, 10, 15),  # 12 months left
            retest_date=datetime.date(2027, 4, 15),
            quantity_on_hand=80.0,
            reserved_quantity=0.0,
            blocked_quantity=0.0,
            quality_status="Released",
            receipt_date=datetime.date(2026, 5, 2),
            release_date=datetime.date(2026, 5, 7),
            recall_status="None",
            synthetic_data_flag=config.synthetic_flag
        ),
        # API MAT-API-001: 20 kg quarantined lot (OOS investigation, unusable!)
        FactInventoryLot(
            lot_id="LOT-API-2026-02-QUAR",
            item_type="RAW_MATERIAL",
            item_id="MAT-API-001",
            location_id="LOC-PLANT-01",
            batch_id=None,
            manufacture_date=datetime.date(2026, 6, 1),
            expiry_date=datetime.date(2027, 12, 1),
            retest_date=datetime.date(2027, 6, 1),
            quantity_on_hand=20.0,
            reserved_quantity=0.0,
            blocked_quantity=20.0,  # Blocked!
            quality_status="Quarantined",
            receipt_date=datetime.date(2026, 6, 20),
            release_date=None,
            recall_status="Under_Investigation",
            synthetic_data_flag=config.synthetic_flag
        ),
        # Excipient MAT-EXC-001: 250 kg eligible released lot
        FactInventoryLot(
            lot_id="LOT-EXC-2026-01",
            item_type="RAW_MATERIAL",
            item_id="MAT-EXC-001",
            location_id="LOC-PLANT-01",
            batch_id=None,
            manufacture_date=datetime.date(2026, 2, 10),
            expiry_date=datetime.date(2028, 2, 10),
            retest_date=datetime.date(2027, 2, 10),
            quantity_on_hand=250.0,
            reserved_quantity=0.0,
            blocked_quantity=0.0,
            quality_status="Released",
            receipt_date=datetime.date(2026, 3, 1),
            release_date=datetime.date(2026, 3, 4),
            recall_status="None",
            synthetic_data_flag=config.synthetic_flag
        ),
        # Packaging Blister MAT-PKG-BLIST: 45,000 units eligible released lot
        FactInventoryLot(
            lot_id="LOT-BLIST-2026-01",
            item_type="RAW_MATERIAL",
            item_id="MAT-PKG-BLIST",
            location_id="LOC-PLANT-01",
            batch_id=None,
            manufacture_date=datetime.date(2026, 1, 15),
            expiry_date=datetime.date(2029, 1, 15),
            retest_date=None,
            quantity_on_hand=45000.0,
            reserved_quantity=0.0,
            blocked_quantity=0.0,
            quality_status="Released",
            receipt_date=datetime.date(2026, 2, 1),
            release_date=datetime.date(2026, 2, 3),
            recall_status="None",
            synthetic_data_flag=config.synthetic_flag
        ),
        # Packaging Bottles MAT-PKG-BOTT: 25,000 units eligible released lot
        FactInventoryLot(
            lot_id="LOT-BOTT-2026-01",
            item_type="RAW_MATERIAL",
            item_id="MAT-PKG-BOTT",
            location_id="LOC-PLANT-01",
            batch_id=None,
            manufacture_date=datetime.date(2026, 1, 15),
            expiry_date=datetime.date(2029, 1, 15),
            retest_date=None,
            quantity_on_hand=25000.0,
            reserved_quantity=0.0,
            blocked_quantity=0.0,
            quality_status="Released",
            receipt_date=datetime.date(2026, 2, 1),
            release_date=datetime.date(2026, 2, 3),
            recall_status="None",
            synthetic_data_flag=config.synthetic_flag
        ),
        # Packaging Cartons MAT-PKG-CART: 35,000 units eligible released lot
        FactInventoryLot(
            lot_id="LOT-CART-2026-01",
            item_type="RAW_MATERIAL",
            item_id="MAT-PKG-CART",
            location_id="LOC-PLANT-01",
            batch_id=None,
            manufacture_date=datetime.date(2026, 3, 1),
            expiry_date=datetime.date(2028, 3, 1),
            retest_date=None,
            quantity_on_hand=35000.0,
            reserved_quantity=0.0,
            blocked_quantity=0.0,
            quality_status="Released",
            receipt_date=datetime.date(2026, 3, 15),
            release_date=datetime.date(2026, 3, 17),
            recall_status="None",
            synthetic_data_flag=config.synthetic_flag
        ),

        # FINISHED GOODS AT CENTRAL DC NAGPUR (LOC-DC-01)
        # SKU-AUG-500-T10: Lot 1 - 18,000 packs eligible released
        FactInventoryLot(
            lot_id="LOT-FG-AUG-T10-26A",
            item_type="FINISHED_SKU",
            item_id="SKU-AUG-500-T10",
            location_id="LOC-DC-01",
            batch_id="BATCH-AUG-2026-08",
            manufacture_date=datetime.date(2026, 8, 20),
            expiry_date=datetime.date(2028, 8, 19),
            retest_date=None,
            quantity_on_hand=18000.0,
            reserved_quantity=2000.0,  # Allocated to open orders
            blocked_quantity=0.0,
            quality_status="Released",
            receipt_date=datetime.date(2026, 8, 28),
            release_date=datetime.date(2026, 8, 26),
            recall_status="None",
            synthetic_data_flag=config.synthetic_flag
        ),
        # SKU-AUG-500-T10: Lot 2 - 3,000 packs approaching expiry (test FEFO!)
        FactInventoryLot(
            lot_id="LOT-FG-AUG-T10-24X",
            item_type="FINISHED_SKU",
            item_id="SKU-AUG-500-T10",
            location_id="LOC-DC-01",
            batch_id="BATCH-AUG-2024-11",
            manufacture_date=datetime.date(2024, 11, 1),
            expiry_date=datetime.date(2026, 11, 20),  # Expiring in ~3 weeks!
            retest_date=None,
            quantity_on_hand=3000.0,
            reserved_quantity=0.0,
            blocked_quantity=0.0,
            quality_status="Released",
            receipt_date=datetime.date(2024, 11, 10),
            release_date=datetime.date(2024, 11, 8),
            recall_status="None",
            synthetic_data_flag=config.synthetic_flag
        ),
        # SKU-AUG-500-T30: Lot 1 - 12,000 packs eligible released
        FactInventoryLot(
            lot_id="LOT-FG-AUG-T30-26A",
            item_type="FINISHED_SKU",
            item_id="SKU-AUG-500-T30",
            location_id="LOC-DC-01",
            batch_id="BATCH-AUG-2026-09",
            manufacture_date=datetime.date(2026, 9, 10),
            expiry_date=datetime.date(2028, 9, 9),
            retest_date=None,
            quantity_on_hand=12000.0,
            reserved_quantity=1500.0,
            blocked_quantity=0.0,
            quality_status="Released",
            receipt_date=datetime.date(2026, 9, 18),
            release_date=datetime.date(2026, 9, 16),
            recall_status="None",
            synthetic_data_flag=config.synthetic_flag
        )
    ]

    # --- 2. FACT_PURCHASE_ORDER (Inbound Material Supply) ---
    purchase_orders = [
        # Crucial API PO: 150 kg from SUP-001, promised for Nov 02, 2026
        FactPurchaseOrder(
            purchase_order_id="PO-2026-001",
            supplier_id="SUP-001",
            material_sku_id="MAT-API-001",
            order_date=datetime.date(2026, 10, 5),
            requested_delivery_date=datetime.date(2026, 11, 2),
            confirmed_delivery_date=datetime.date(2026, 11, 2),
            actual_receipt_date=None,  # Pending receipt!
            ordered_quantity=150.0,
            received_quantity=0.0,
            purchase_order_status="Open",
            delay_reason=None,
            quality_status="Pending_Inspection"
        ),
        # Excipient PO: 200 kg from SUP-001, promised for Nov 09, 2026
        FactPurchaseOrder(
            purchase_order_id="PO-2026-002",
            supplier_id="SUP-001",
            material_sku_id="MAT-EXC-001",
            order_date=datetime.date(2026, 10, 15),
            requested_delivery_date=datetime.date(2026, 11, 9),
            confirmed_delivery_date=datetime.date(2026, 11, 9),
            actual_receipt_date=None,
            ordered_quantity=200.0,
            received_quantity=0.0,
            purchase_order_status="Open",
            delay_reason=None,
            quality_status="Pending_Inspection"
        ),
        # Blister Foil PO: 50,000 units from SUP-002, promised for Nov 05, 2026
        FactPurchaseOrder(
            purchase_order_id="PO-2026-003",
            supplier_id="SUP-002",
            material_sku_id="MAT-PKG-BLIST",
            order_date=datetime.date(2026, 10, 18),
            requested_delivery_date=datetime.date(2026, 11, 5),
            confirmed_delivery_date=datetime.date(2026, 11, 5),
            actual_receipt_date=None,
            ordered_quantity=50000.0,
            received_quantity=0.0,
            purchase_order_status="Open",
            delay_reason=None,
            quality_status="Pending_Inspection"
        ),
        # Outer Cartons PO: 40,000 units from SUP-002, promised for Nov 05, 2026
        FactPurchaseOrder(
            purchase_order_id="PO-2026-004",
            supplier_id="SUP-002",
            material_sku_id="MAT-PKG-CART",
            order_date=datetime.date(2026, 10, 18),
            requested_delivery_date=datetime.date(2026, 11, 5),
            confirmed_delivery_date=datetime.date(2026, 11, 5),
            actual_receipt_date=None,
            ordered_quantity=40000.0,
            received_quantity=0.0,
            purchase_order_status="Open",
            delay_reason=None,
            quality_status="Pending_Inspection"
        )
    ]

    # --- 3. FACT_PRODUCTION_ORDER (Manufacturing Plan) ---
    production_orders = [
        # Planned production run of 20,000 packs of T10 starting Nov 09
        FactProductionOrder(
            production_order_id="PROD-2026-001",
            finished_sku_id="SKU-AUG-500-T10",
            location_id="LOC-PLANT-01",
            production_line_id="LINE-PLANT1-01",
            planned_start_date=datetime.date(2026, 11, 9),
            planned_completion_date=datetime.date(2026, 11, 13),
            actual_start_date=None,
            actual_completion_date=None,
            planned_quantity=20000.0,
            actual_quantity=0.0,
            expected_yield=98.5,
            actual_yield=None,
            planned_hours=40.0,
            actual_hours=None,
            production_status="Planned",
            delay_reason=None
        ),
        # Planned production run of 10,000 packs of T30 starting Nov 16
        FactProductionOrder(
            production_order_id="PROD-2026-002",
            finished_sku_id="SKU-AUG-500-T30",
            location_id="LOC-PLANT-01",
            production_line_id="LINE-PLANT1-02",
            planned_start_date=datetime.date(2026, 11, 16),
            planned_completion_date=datetime.date(2026, 11, 20),
            actual_start_date=None,
            actual_completion_date=None,
            planned_quantity=10000.0,
            actual_quantity=0.0,
            expected_yield=98.0,
            actual_yield=None,
            planned_hours=30.0,
            actual_hours=None,
            production_status="Planned",
            delay_reason=None
        )
    ]

    # --- 4. FACT_MATERIAL_REQUIREMENT (Calculated BOM Explosion for Production Orders) ---
    # PROD-2026-001 for 20,000 packs T10:
    # Requires: 20,000 * 0.00625 * 1.02 = 127.5 kg API
    # Required date: 2026-11-09
    # Current eligible API stock on hand: 80 kg
    # Shortage before incoming PO: 47.5 kg!
    # Expected PO-2026-001 delivers: 150 kg on 2026-11-02 + 5 days release = available 2026-11-07! (Tight buffer of 2 days!)
    material_requirements = [
        FactMaterialRequirement(
            requirement_id="REQ-2026-001-API",
            production_order_id="PROD-2026-001",
            material_sku_id="MAT-API-001",
            required_quantity=127.5,  # kg
            required_date=datetime.date(2026, 11, 9),
            eligible_available_quantity=80.0,
            expected_receipt_quantity=150.0,
            shortage_quantity=0.0,  # Baseline: covered by PO-2026-001!
            scenario_id="SCN-BASE"
        ),
        FactMaterialRequirement(
            requirement_id="REQ-2026-001-EXC",
            production_order_id="PROD-2026-001",
            material_sku_id="MAT-EXC-001",
            required_quantity=40.6,  # 20000 * 0.002 * 1.015
            required_date=datetime.date(2026, 11, 9),
            eligible_available_quantity=250.0,
            expected_receipt_quantity=0.0,
            shortage_quantity=0.0,
            scenario_id="SCN-BASE"
        ),
        FactMaterialRequirement(
            requirement_id="REQ-2026-001-BLIST",
            production_order_id="PROD-2026-001",
            material_sku_id="MAT-PKG-BLIST",
            required_quantity=20200.0,  # 20000 * 1 * 1.01
            required_date=datetime.date(2026, 11, 9),
            eligible_available_quantity=45000.0,
            expected_receipt_quantity=0.0,
            shortage_quantity=0.0,
            scenario_id="SCN-BASE"
        ),
        FactMaterialRequirement(
            requirement_id="REQ-2026-001-CART",
            production_order_id="PROD-2026-001",
            material_sku_id="MAT-PKG-CART",
            required_quantity=20200.0,
            required_date=datetime.date(2026, 11, 9),
            eligible_available_quantity=35000.0,
            expected_receipt_quantity=0.0,
            shortage_quantity=0.0,
            scenario_id="SCN-BASE"
        )
    ]

    # --- 5. FACT_BATCH (Batch Genealogy & QA Release Status) ---
    batches = [
        # Batch 08: Released and distributed
        FactBatch(
            batch_id="BATCH-AUG-2026-08",
            production_order_id="PROD-2026-HIST-08",
            finished_sku_id="SKU-AUG-500-T10",
            location_id="LOC-PLANT-01",
            manufacture_date=datetime.date(2026, 8, 20),
            quality_submission_date=datetime.date(2026, 8, 21),
            expected_release_date=datetime.date(2026, 8, 26),
            actual_release_date=datetime.date(2026, 8, 26),
            batch_quantity=20000.0,
            batch_status="Released",
            rejection_reason=None
        ),
        # Batch 09: Released and distributed
        FactBatch(
            batch_id="BATCH-AUG-2026-09",
            production_order_id="PROD-2026-HIST-09",
            finished_sku_id="SKU-AUG-500-T30",
            location_id="LOC-PLANT-01",
            manufacture_date=datetime.date(2026, 9, 10),
            quality_submission_date=datetime.date(2026, 9, 11),
            expected_release_date=datetime.date(2026, 9, 16),
            actual_release_date=datetime.date(2026, 9, 16),
            batch_quantity=12000.0,
            batch_status="Released",
            rejection_reason=None
        ),
        # Batch 10: Just finished on line, currently awaiting QA release!
        FactBatch(
            batch_id="BATCH-AUG-2026-10",
            production_order_id="PROD-2026-HIST-10",
            finished_sku_id="SKU-AUG-500-T10",
            location_id="LOC-PLANT-01",
            manufacture_date=datetime.date(2026, 10, 23),
            quality_submission_date=datetime.date(2026, 10, 24),
            expected_release_date=datetime.date(2026, 10, 30),
            actual_release_date=None,  # In testing
            batch_quantity=15000.0,
            batch_status="In_Testing",
            rejection_reason=None
        )
    ]

    # --- 6. FACT_QUALITY_EVENT ---
    quality_events = [
        FactQualityEvent(
            quality_event_id="QEV-2026-001",
            entity_type="BATCH",
            entity_id="BATCH-AUG-2026-10",
            event_type="Routine_Release",
            event_date=datetime.date(2026, 10, 24),
            expected_resolution_date=datetime.date(2026, 10, 30),
            actual_resolution_date=None,
            quality_status="Pending",
            delay_days=0,
            reason_code="QA-NORM-RELEASE"
        ),
        FactQualityEvent(
            quality_event_id="QEV-2026-002",
            entity_type="INVENTORY_LOT",
            entity_id="LOT-API-2026-02-QUAR",
            event_type="OOS_Investigation",
            event_date=datetime.date(2026, 6, 22),
            expected_resolution_date=datetime.date(2026, 11, 30),
            actual_resolution_date=None,
            quality_status="Quarantined",
            delay_days=150,
            reason_code="QC-DEV-PARTICLE-COUNT"
        )
    ]

    # --- 7. FACT_CAPACITY (Line Operating Hours & Commitments) ---
    capacity_records = []
    lines = ["LINE-PLANT1-01", "LINE-PLANT1-02"]
    for w_idx in range(config.future_weeks):
        period_date = as_of + datetime.timedelta(weeks=w_idx)
        for line in lines:
            rec_id = f"CAP-PLANT1-{line[-2:]}-W{w_idx+1:02d}"
            committed = 0.0
            if line == "LINE-PLANT1-01" and w_idx == 2:  # Week of Nov 09 (PROD-2026-001)
                committed = 40.0
            elif line == "LINE-PLANT1-02" and w_idx == 3:  # Week of Nov 16 (PROD-2026-002)
                committed = 30.0
                
            capacity_records.append(
                FactCapacity(
                    capacity_record_id=rec_id,
                    location_id="LOC-PLANT-01",
                    production_line_id=line,
                    period_start_date=period_date,
                    net_available_hours=120.0,
                    maintenance_hours=8.0,
                    downtime_hours=0.0,
                    committed_hours=committed,
                    scenario_id="SCN-BASE"
                )
            )

    # --- 8. FACT_SHIPMENT (Inter-Facility Distribution) ---
    shipments = [
        # Dispatched shipment of 10,000 packs T10 moving from Plant Alpha to Central DC Nagpur
        FactShipment(
            shipment_id="SHIP-2026-042",
            origin_location_id="LOC-PLANT-01",
            destination_location_id="LOC-DC-01",
            finished_sku_id="SKU-AUG-500-T10",
            lot_id="LOT-FG-AUG-T10-26A",
            dispatch_date=datetime.date(2026, 10, 24),
            expected_arrival_date=datetime.date(2026, 10, 26),
            actual_arrival_date=datetime.date(2026, 10, 26),
            shipped_quantity=10000.0,
            received_quantity=10000.0,
            transport_mode="Road",
            shipment_status="Delivered",
            delay_reason=None,
            temperature_excursion_flag=False
        ),
        # Planned replenishment shipment from DC Nagpur to Market Hyderabad for next week
        FactShipment(
            shipment_id="SHIP-2026-043",
            origin_location_id="LOC-DC-01",
            destination_location_id="LOC-MKT-HYD",
            finished_sku_id="SKU-AUG-500-T10",
            lot_id="LOT-FG-AUG-T10-26A",
            dispatch_date=datetime.date(2026, 10, 29),
            expected_arrival_date=datetime.date(2026, 10, 30),
            actual_arrival_date=None,
            shipped_quantity=5000.0,
            received_quantity=0.0,
            transport_mode="Road",
            shipment_status="Manifested",
            delay_reason=None,
            temperature_excursion_flag=False
        )
    ]

    # --- 9. FACT_SUPPLY_PLAN (Planned Supply Receipts at DC Nagpur) ---
    supply_plans = [
        FactSupplyPlan(
            supply_plan_id="SPL-2026-001",
            finished_sku_id="SKU-AUG-500-T10",
            location_id="LOC-DC-01",
            planned_week=datetime.date(2026, 11, 16),  # Week 3
            planned_quantity=20000.0,
            source_type="MANUFACTURING",
            source_order_id="PROD-2026-001",
            expected_availability_date=datetime.date(2026, 11, 18),  # Plant completes 11/13 + release & transit 11/18
            scenario_id="SCN-BASE",
            plan_status="Committed"
        ),
        FactSupplyPlan(
            supply_plan_id="SPL-2026-002",
            finished_sku_id="SKU-AUG-500-T30",
            location_id="LOC-DC-01",
            planned_week=datetime.date(2026, 11, 23),  # Week 4
            planned_quantity=10000.0,
            source_type="MANUFACTURING",
            source_order_id="PROD-2026-002",
            expected_availability_date=datetime.date(2026, 11, 25),
            scenario_id="SCN-BASE",
            plan_status="Committed"
        )
    ]

    return {
        "fact_inventory_lot": inventory_lots,
        "fact_purchase_order": purchase_orders,
        "fact_production_order": production_orders,
        "fact_material_requirement": material_requirements,
        "fact_batch": batches,
        "fact_quality_event": quality_events,
        "fact_capacity": capacity_records,
        "fact_shipment": shipments,
        "fact_supply_plan": supply_plans
    }

