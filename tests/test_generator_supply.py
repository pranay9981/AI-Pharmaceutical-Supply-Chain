"""
Unit tests for Supply Chain Operational Transactions Synthesizer.
Synthetic Data Generation Engine — Week 03, Day 12 Deliverable.

Verifies:
1. Inventory lot counts (9 rows), physical inventory invariants, and QC statuses.
2. Purchase order records (4 rows), vendor alignment, and milestone chronology.
3. Production work orders (2 rows), scheduled start/end dates, and yield standards.
4. Material requirement MRP gross-to-net calculation and zero-shortage baseline.
5. Batch genealogy (3 rows) and milestone ordering (mfg <= QA sample <= expected release).
6. Quality events (2 rows), investigation tracking, and entity foreign key linkage.
7. Machine capacity records (52 rows = 26 weeks x 2 lines) and committed hours.
8. Inter-facility shipments (2 rows) and supply replenishment plans (2 rows).
"""

import datetime
import pytest
from src.generator.config import GeneratorConfig
from src.generator.supply_data import (
    generate_supply_and_operations_data,
    generate_inventory_lots,
    generate_purchase_orders,
    generate_production_orders,
    generate_material_requirements,
    generate_batches,
    generate_quality_events,
    generate_line_capacity,
    generate_shipments,
    generate_supply_plans
)
from src.models.procurement_inventory import FactPurchaseOrder, FactInventoryLot
from src.models.manufacturing_quality import FactProductionOrder, FactBatch, FactQualityEvent
from src.models.capacity_logistics import FactCapacity, FactShipment
from src.models.planning import FactSupplyPlan, FactMaterialRequirement


@pytest.fixture
def config():
    return GeneratorConfig(random_seed=20261014, synthetic_flag=True)


def test_inventory_lots_counts_and_validation(config):
    """Verifies inventory lot counts (9 rows), physical invariants, and QC filtering."""
    lots = generate_inventory_lots(config)
    assert len(lots) == 9

    raw_lots = [l for l in lots if l.item_type == "RAW_MATERIAL"]
    fg_lots = [l for l in lots if l.item_type == "FINISHED_SKU"]
    assert len(raw_lots) == 6
    assert len(fg_lots) == 3

    # All lots must satisfy physical mass balance and date ordering
    for lot in lots:
        assert isinstance(lot, FactInventoryLot)
        assert lot.quantity_on_hand >= (lot.reserved_quantity + lot.blocked_quantity)
        assert lot.expiry_date > lot.manufacture_date
        if lot.release_date is not None:
            assert lot.release_date >= lot.receipt_date

    # Quarantined lot check (LOT-API-2026-02-QUAR)
    quar_lot = next(l for l in lots if l.lot_id == "LOT-API-2026-02-QUAR")
    assert quar_lot.quality_status == "Quarantined"
    assert quar_lot.blocked_quantity == 20.0
    assert quar_lot.release_date is None
    assert quar_lot.recall_status == "Under_Investigation"

    # Near-expiry lot check (LOT-FG-AUG-T10-24X)
    near_exp_lot = next(l for l in lots if l.lot_id == "LOT-FG-AUG-T10-24X")
    assert near_exp_lot.expiry_date == datetime.date(2026, 11, 20)
    assert near_exp_lot.quality_status == "Released"


def test_purchase_orders_counts_and_milestones(config):
    """Verifies purchase order counts (4 rows), supplier links, and date milestones."""
    pos = generate_purchase_orders(config)
    assert len(pos) == 4

    po_ids = {p.purchase_order_id for p in pos}
    assert po_ids == {"PO-2026-001", "PO-2026-002", "PO-2026-003", "PO-2026-004"}

    api_po = next(p for p in pos if p.purchase_order_id == "PO-2026-001")
    assert api_po.supplier_id == "SUP-001"
    assert api_po.material_sku_id == "MAT-API-001"
    assert api_po.ordered_quantity == 150.0
    assert api_po.purchase_order_status == "Open"

    for po in pos:
        assert isinstance(po, FactPurchaseOrder)
        assert po.requested_delivery_date >= po.order_date
        assert po.confirmed_delivery_date >= po.order_date
        assert po.ordered_quantity > 0.0


def test_production_orders_and_plant_scheduling(config):
    """Verifies production orders (2 rows), plant lines, and schedule milestones."""
    orders = generate_production_orders(config)
    assert len(orders) == 2

    t10_order = next(o for o in orders if o.production_order_id == "PROD-2026-001")
    t30_order = next(o for o in orders if o.production_order_id == "PROD-2026-002")

    assert t10_order.finished_sku_id == "SKU-AUG-500-T10"
    assert t10_order.planned_quantity == 20000.0
    assert t10_order.planned_completion_date >= t10_order.planned_start_date
    assert t10_order.expected_yield >= 98.0

    assert t30_order.finished_sku_id == "SKU-AUG-500-T30"
    assert t30_order.planned_quantity == 10000.0
    assert t30_order.planned_completion_date >= t30_order.planned_start_date


def test_material_requirements_mrp_netting(config):
    """Verifies gross-to-net MRP calculations for planned production run."""
    reqs = generate_material_requirements(config)
    assert len(reqs) == 4

    api_req = next(r for r in reqs if r.material_sku_id == "MAT-API-001")
    # Gross requirement: 20000 * 0.00625 * 1.02 = 127.5 kg
    assert api_req.required_quantity == pytest.approx(127.5, rel=1e-4)
    assert api_req.eligible_available_quantity == 80.0
    assert api_req.expected_receipt_quantity == 150.0
    # Baseline: 127.5 required <= (80 available + 150 receipt) -> shortage = 0
    assert api_req.shortage_quantity == 0.0

    for r in reqs:
        assert isinstance(r, FactMaterialRequirement)
        calc_shortage = max(0.0, r.required_quantity - r.eligible_available_quantity - r.expected_receipt_quantity)
        assert r.shortage_quantity == pytest.approx(calc_shortage, abs=1e-4)


def test_batches_genealogy_milestones(config):
    """Verifies batch genealogy (3 rows) and milestone ordering constraints."""
    batches = generate_batches(config)
    assert len(batches) == 3

    for b in batches:
        assert isinstance(b, FactBatch)
        assert b.quality_submission_date >= b.manufacture_date
        assert b.expected_release_date >= b.quality_submission_date
        if b.actual_release_date is not None:
            assert b.actual_release_date >= b.manufacture_date

    # Batch 10 in testing
    b10 = next(b for b in batches if b.batch_id == "BATCH-AUG-2026-10")
    assert b10.batch_status == "In_Testing"
    assert b10.actual_release_date is None


def test_quality_events_linkages(config):
    """Verifies quality events (2 rows) and entity linkages."""
    events = generate_quality_events(config)
    assert len(events) == 2

    e_batch = next(e for e in events if e.quality_event_id == "QEV-2026-001")
    assert e_batch.entity_type == "BATCH"
    assert e_batch.entity_id == "BATCH-AUG-2026-10"
    assert e_batch.event_type == "Routine_Release"

    e_lot = next(e for e in events if e.quality_event_id == "QEV-2026-002")
    assert e_lot.entity_type == "INVENTORY_LOT"
    assert e_lot.entity_id == "LOT-API-2026-02-QUAR"
    assert e_lot.quality_status == "Quarantined"
    assert e_lot.delay_days == 150


def test_line_capacity_coverage_and_utilization(config):
    """Verifies line capacity records (52 rows = 26 weeks x 2 lines) and booking."""
    cap = generate_line_capacity(config)
    assert len(cap) == 52

    line1_records = [c for c in cap if c.production_line_id == "LINE-PLANT1-01"]
    line2_records = [c for c in cap if c.production_line_id == "LINE-PLANT1-02"]
    assert len(line1_records) == 26
    assert len(line2_records) == 26

    # Verify committed hours on Line 1 in Week 2 (PROD-2026-001)
    w2_line1 = line1_records[2]
    assert w2_line1.committed_hours == 40.0
    assert w2_line1.net_available_hours == 120.0
    assert w2_line1.is_overloaded() is False
    assert w2_line1.calculate_utilization_pct() == pytest.approx(33.33, rel=1e-2)

    for c in cap:
        assert isinstance(c, FactCapacity)
        assert c.net_available_hours > 0.0
        assert c.maintenance_hours >= 0.0


def test_shipments_and_supply_plans(config):
    """Verifies inter-facility shipments (2 rows) and supply plans (2 rows)."""
    shipments = generate_shipments(config)
    plans = generate_supply_plans(config)
    assert len(shipments) == 2
    assert len(plans) == 2

    s1 = shipments[0]
    assert s1.origin_location_id == "LOC-PLANT-01"
    assert s1.destination_location_id == "LOC-DC-01"
    assert s1.shipment_status == "Delivered"
    assert s1.actual_arrival_date is not None

    p1 = plans[0]
    assert p1.finished_sku_id == "SKU-AUG-500-T10"
    assert p1.source_order_id == "PROD-2026-001"
    assert p1.planned_quantity == 20000.0
    assert p1.plan_status == "Committed"
