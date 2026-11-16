"""
Supply Chain Operational Transactions Synthesizer.
Synthetic Data Generation Engine — Week 03, Day 12 Deliverable.

Generates:
1. Physical inventory lots across plants and distribution centers (fact_inventory_lot, 9 rows).
   Includes raw materials (API, excipient, packaging) and finished SKU lots (released, quarantined, near-expiry).
2. Upstream supplier purchase orders (fact_purchase_order, 4 rows).
3. Plant manufacturing work orders (fact_production_order, 2 rows).
4. Gross-to-net MRP material requirements (fact_material_requirement, 4 rows).
5. Batch manufacturing records & QA testing genealogy (fact_batch, 3 rows).
6. Quality events, sterility retests, and deviations (fact_quality_event, 2 rows).
7. Machine capacity utilization tracking over 26 planning weeks (fact_capacity, 52 rows).
8. Inter-facility freight shipments in transit and delivered (fact_shipment, 2 rows).
9. DC replenishment supply plans (fact_supply_plan, 2 rows).
"""

import datetime
from typing import Dict, List, Optional
import numpy as np

from src.generator.config import GeneratorConfig
from src.models.procurement_inventory import FactPurchaseOrder, FactInventoryLot
from src.models.manufacturing_quality import FactProductionOrder, FactBatch, FactQualityEvent
from src.models.capacity_logistics import FactCapacity, FactShipment
from src.models.planning import FactSupplyPlan, FactMaterialRequirement


def generate_inventory_lots(config: GeneratorConfig) -> List[FactInventoryLot]:
    """
    Generates fact_inventory_lot physical inventory records across network nodes:
    - Plant Alpha (LOC-PLANT-01): Raw materials (API, excipients, primary blister foil, bottles, cartons).
      Includes a 20 kg Quarantined API lot (OOS investigation) to test eligibility filtering.
    - Central DC Nagpur (LOC-DC-01): Finished goods lots (T10 strips, T30 bottles).
      Includes a near-expiry lot (LOT-FG-AUG-T10-24X) with ~3 weeks RSL to test FEFO rules.
    """
    return [
        # RAW MATERIALS AT MANUFACTURING PLANT ALPHA (LOC-PLANT-01)
        # API MAT-API-001: 80 kg eligible released lot
        FactInventoryLot(
            lot_id="LOT-API-2026-01",
            item_type="RAW_MATERIAL",
            item_id="MAT-API-001",
            location_id="LOC-PLANT-01",
            batch_id=None,
            manufacture_date=datetime.date(2026, 4, 15),
            expiry_date=datetime.date(2027, 10, 15),  # 12 months shelf life remaining
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
        # API MAT-API-001: 20 kg quarantined lot (OOS particle count investigation, unusable!)
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
            blocked_quantity=20.0,  # 100% blocked
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
        # Packaging Cartons MAT-PKG-CART: 35,000 units eligible released lot (Shared component)
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

        # FINISHED GOODS AT CENTRAL DISTRIBUTION CENTRE NAGPUR (LOC-DC-01)
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
            reserved_quantity=2000.0,  # Reserved for open hospital orders
            blocked_quantity=0.0,
            quality_status="Released",
            receipt_date=datetime.date(2026, 8, 26),
            release_date=datetime.date(2026, 8, 28),
            recall_status="None",
            synthetic_data_flag=config.synthetic_flag
        ),
        # SKU-AUG-500-T10: Lot 2 - 3,000 packs approaching expiry (tests FEFO prioritization)
        FactInventoryLot(
            lot_id="LOT-FG-AUG-T10-24X",
            item_type="FINISHED_SKU",
            item_id="SKU-AUG-500-T10",
            location_id="LOC-DC-01",
            batch_id="BATCH-AUG-2024-11",
            manufacture_date=datetime.date(2024, 11, 1),
            expiry_date=datetime.date(2026, 11, 20),  # Expiring in ~3 weeks
            retest_date=None,
            quantity_on_hand=3000.0,
            reserved_quantity=0.0,
            blocked_quantity=0.0,
            quality_status="Released",
            receipt_date=datetime.date(2024, 11, 6),
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
            receipt_date=datetime.date(2026, 9, 16),
            release_date=datetime.date(2026, 9, 18),
            recall_status="None",
            synthetic_data_flag=config.synthetic_flag
        )
    ]


def generate_purchase_orders(config: GeneratorConfig) -> List[FactPurchaseOrder]:
    """
    Generates fact_purchase_order inbound replenishment orders.
    Anchors Scenario A: PO-2026-001 (150 kg API from SUP-001 promised for Nov 02, 2026).
    """
    return [
        # Critical API PO: 150 kg from SUP-001, promised for Nov 02, 2026 (Baseline: on time)
        FactPurchaseOrder(
            purchase_order_id="PO-2026-001",
            supplier_id="SUP-001",
            material_sku_id="MAT-API-001",
            order_date=datetime.date(2026, 10, 5),
            requested_delivery_date=datetime.date(2026, 11, 2),
            confirmed_delivery_date=datetime.date(2026, 11, 2),
            actual_receipt_date=None,  # In transit / pending receipt
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


def generate_production_orders(config: GeneratorConfig) -> List[FactProductionOrder]:
    """Generates fact_production_order plant manufacturing work orders."""
    return [
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


def generate_material_requirements(config: GeneratorConfig) -> List[FactMaterialRequirement]:
    """
    Generates fact_material_requirement BOM exploded component netting records for PROD-2026-001.
    Formula: Shortage = max(0, Required - Available - ExpectedReceipts)
    - API: 20,000 * 0.00625 * 1.02 = 127.5 kg needed.
      On hand: 80.0 kg. Net before PO: 47.5 kg shortage.
      Baseline PO receipt: 150.0 kg on Nov 02 -> Shortage = 0.0 kg.
    """
    return [
        FactMaterialRequirement(
            requirement_id="REQ-2026-001-API",
            production_order_id="PROD-2026-001",
            material_sku_id="MAT-API-001",
            required_quantity=127.5,
            required_date=datetime.date(2026, 11, 9),
            eligible_available_quantity=80.0,
            expected_receipt_quantity=150.0,
            shortage_quantity=0.0,
            scenario_id="SCN-BASE"
        ),
        FactMaterialRequirement(
            requirement_id="REQ-2026-001-EXC",
            production_order_id="PROD-2026-001",
            material_sku_id="MAT-EXC-001",
            required_quantity=40.6,
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
            required_quantity=20200.0,
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


def generate_batches(config: GeneratorConfig) -> List[FactBatch]:
    """
    Generates fact_batch manufacturing batch genealogy records.
    Enforces milestone ordering: manufacture_date <= quality_submission_date <= expected_release_date.
    """
    return [
        # Batch 08: Manufactured, released, and distributed in August 2026
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
        # Batch 09: Manufactured, released, and distributed in September 2026
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
        # Batch 10: Just packaged on line, currently undergoing QC sterility & dissolution testing
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


def generate_quality_events(config: GeneratorConfig) -> List[FactQualityEvent]:
    """Generates fact_quality_event deviations, release tests, and holds."""
    return [
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


def generate_line_capacity(config: GeneratorConfig) -> List[FactCapacity]:
    """
    Generates fact_capacity weekly operating hour utilization for production lines over 26 planning weeks.
    Total records = 26 weeks * 2 lines = 52 records.
    - LINE-PLANT1-01: 40 hours booked in Week 2 (Nov 09) for PROD-2026-001 (utilization = 33.3%).
    - LINE-PLANT1-02: 30 hours booked in Week 3 (Nov 16) for PROD-2026-002 (utilization = 25.0%).
    """
    capacity_records: List[FactCapacity] = []
    lines = ["LINE-PLANT1-01", "LINE-PLANT1-02"]
    as_of = config.planning_as_of_date

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

    return capacity_records


def generate_shipments(config: GeneratorConfig) -> List[FactShipment]:
    """Generates fact_shipment logistics consignments."""
    return [
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
        # Planned replenishment shipment from Central DC Nagpur to Hyderabad Hub
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


def generate_supply_plans(config: GeneratorConfig) -> List[FactSupplyPlan]:
    """Generates fact_supply_plan planned supply receipts at distribution centers."""
    return [
        FactSupplyPlan(
            supply_plan_id="SPL-2026-001",
            finished_sku_id="SKU-AUG-500-T10",
            location_id="LOC-DC-01",
            planned_week=datetime.date(2026, 11, 16),
            planned_quantity=20000.0,
            source_type="MANUFACTURING",
            source_order_id="PROD-2026-001",
            expected_availability_date=datetime.date(2026, 11, 18),
            scenario_id="SCN-BASE",
            plan_status="Committed"
        ),
        FactSupplyPlan(
            supply_plan_id="SPL-2026-002",
            finished_sku_id="SKU-AUG-500-T30",
            location_id="LOC-DC-01",
            planned_week=datetime.date(2026, 11, 23),
            planned_quantity=10000.0,
            source_type="MANUFACTURING",
            source_order_id="PROD-2026-002",
            expected_availability_date=datetime.date(2026, 11, 25),
            scenario_id="SCN-BASE",
            plan_status="Committed"
        )
    ]


def generate_supply_and_operations_data(
    config: Optional[GeneratorConfig] = None
) -> Dict[str, list]:
    """
    Main supply & operations generator entry point for Week 03, Day 12.
    Produces validated Pydantic v2 records across inventory, procurement, manufacturing,
    quality, capacity, logistics, and planning.
    """
    if config is None:
        config = GeneratorConfig()

    return {
        "fact_inventory_lot": generate_inventory_lots(config),
        "fact_purchase_order": generate_purchase_orders(config),
        "fact_production_order": generate_production_orders(config),
        "fact_material_requirement": generate_material_requirements(config),
        "fact_batch": generate_batches(config),
        "fact_quality_event": generate_quality_events(config),
        "fact_capacity": generate_line_capacity(config),
        "fact_shipment": generate_shipments(config),
        "fact_supply_plan": generate_supply_plans(config)
    }
