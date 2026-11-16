# Supply Chain Operational Transactions Synthesizer
## Phase 1 Synthetic Data Generation Engine — Day 12 Deliverable
### Week 03 (11-Nov-2026) | Indian Pharmaceutical Supply Chain Network

---

## 1. Executive Summary & Purpose

The **Supply Chain Operational Transactions Synthesizer** ([`src/generator/supply_data.py`](file:///d:/AI%20Pharmaceutical%20Supply%20Chain/src/generator/supply_data.py)) generates the multi-echelon operational execution records for the AI-Powered Pharmaceutical Supply Chain Control Tower.

It models the physical flow of active pharmaceutical ingredients, excipients, and packaging materials through plant floor manufacturing, quality assurance batch release, multi-week machine capacity utilization, and inter-facility logistics.

The module manages **9 operational fact and planning tables** comprising **79 verified baseline records**, fully validated against Pydantic v2 domain schemas (`src/models/procurement_inventory.py`, `src/models/manufacturing_quality.py`, `src/models/capacity_logistics.py`, `src/models/planning.py`).

---

## 2. The 9 Operational Fact Tables Breakdown

```
Multi-Echelon Operational Flow:
┌───────────────────────────────┐
│ fact_purchase_order (4 rows)  │ ── Suppliers SUP-001, SUP-002
└───────────────┬───────────────┘
                ▼ Inbound Delivery
┌───────────────────────────────┐
│ fact_inventory_lot (9 rows)   │ ── Raw Materials (Plant Alpha) & Finished Goods (DC Nagpur)
└───────────────┬───────────────┘
                ▼ Dispensing & Line Allocation
┌───────────────────────────────┐
│ fact_material_requirement (4) │ ── Gross-to-Net MRP calculation
│ fact_production_order (2)     │ ── Packaging lines LINE-PLANT1-01 / LINE-PLANT1-02
│ fact_capacity (52 rows)       │ ── 26-week machine hour tracking
└───────────────┬───────────────┘
                ▼ Tableting & Packaging
┌───────────────────────────────┐
│ fact_batch (3 rows)           │ ── QA sampling & Certificate of Analysis (CoA)
│ fact_quality_event (2 rows)   │ ── Routine releases & OOS particle investigations
└───────────────┬───────────────┘
                ▼ Release & Dispatch
┌───────────────────────────────┐
│ fact_supply_plan (2 rows)     │ ── DC replenishment commitments
│ fact_shipment (2 rows)        │ ── Inter-city transit consignments
└───────────────────────────────┘
```

### 2.1 Physical Inventory Lots (`fact_inventory_lot`, 9 rows)
Captures inventory across two network echelons:
1. **Raw Materials at Plant Alpha (`LOC-PLANT-01`)**:
   * `LOT-API-2026-01`: 80.0 kg Amoxicillin/Clavulanate API (`Released`, 12 months RSL).
   * `LOT-API-2026-02-QUAR`: 20.0 kg API (`Quarantined`, blocked due to particle count OOS deviation).
   * `LOT-EXC-2026-01`: 250.0 kg Excipient granules (`Released`).
   * `LOT-BLIST-2026-01`: 45,000 units Blister foil strips (`Released`).
   * `LOT-BOTT-2026-01`: 25,000 units HDPE bottles (`Released`).
   * `LOT-CART-2026-01`: 35,000 units Printed cartons (`Released`, shared component).
2. **Finished Goods at Central DC Nagpur (`LOC-DC-01`)**:
   * `LOT-FG-AUG-T10-26A`: 18,000 packs T10 strip (`Released`, 2,000 packs reserved for open hospital orders).
   * `LOT-FG-AUG-T10-24X`: 3,000 packs T10 strip (`Released`, near-expiry lot expiring in ~3 weeks to stress FEFO rules).
   * `LOT-FG-AUG-T30-26A`: 12,000 packs T30 bottle (`Released`, 1,500 packs reserved).

**Physical Invariants Enforced:**
$$\text{quantity\_on\_hand} \ge \text{reserved\_quantity} + \text{blocked\_quantity}$$
$$\text{manufacture\_date} < \text{receipt\_date} \le \text{release\_date} < \text{expiry\_date}$$

### 2.2 Supplier Purchase Orders (`fact_purchase_order`, 4 rows)
* `PO-2026-001`: 150 kg API from `SUP-001`, promised delivery **02-Nov-2026**. (*Anchors Scenario A delay injection*).
* `PO-2026-002`: 200 kg Excipient from `SUP-001`, promised delivery 09-Nov-2026.
* `PO-2026-003`: 50,000 units Blister foil from `SUP-002`, promised delivery 05-Nov-2026.
* `PO-2026-004`: 40,000 units Cartons from `SUP-002`, promised delivery 05-Nov-2026.

### 2.3 Manufacturing Production Orders (`fact_production_order`, 2 rows)
* `PROD-2026-001`: 20,000 packs T10 strip on `LINE-PLANT1-01` (Planned start: 09-Nov, Planned completion: 13-Nov, 40 line hours, 98.5% expected yield).
* `PROD-2026-002`: 10,000 packs T30 bottle on `LINE-PLANT1-02` (Planned start: 16-Nov, Planned completion: 20-Nov, 30 line hours, 98.0% expected yield).

### 2.4 Gross-to-Net MRP Material Requirements (`fact_material_requirement`, 4 rows)
Calculates component netting for `PROD-2026-001`:
$$\text{Shortage} = \max\Big(0.0, \ \text{Required Quantity} - \text{Eligible Available} - \text{Expected Receipts}\Big)$$

* **API (`MAT-API-001`)**:
  * Gross requirement: $20{,}000 \times 0.00625 \times 1.02 = \mathbf{127.5\text{ kg}}$.
  * Eligible on-hand: $80.0\text{ kg}$. Net deficit before PO: $47.5\text{ kg}$.
  * Baseline receipt from `PO-2026-001`: $150.0\text{ kg}$ on 02-Nov + 5 days QC = Available 07-Nov.
  * Baseline net shortage: $\mathbf{0.0\text{ kg}}$ (covered with 2 days safety buffer).
* **Excipient (`MAT-EXC-001`)**: Required $40.6\text{ kg}$, Available $250.0\text{ kg}$, Shortage $\mathbf{0.0\text{ kg}}$.
* **Blister Foil (`MAT-PKG-BLIST`)**: Required $20{,}200\text{ units}$, Available $45{,}000\text{ units}$, Shortage $\mathbf{0.0\text{ units}}$.
* **Cartons (`MAT-PKG-CART`)**: Required $20{,}200\text{ units}$, Available $35{,}000\text{ units}$, Shortage $\mathbf{0.0\text{ units}}$.

### 2.5 Batch Genealogy Records (`fact_batch`, 3 rows)
* `BATCH-AUG-2026-08`: Released August batch (T10, 20,000 packs).
* `BATCH-AUG-2026-09`: Released September batch (T30, 12,000 packs).
* `BATCH-AUG-2026-10`: In-Testing batch packaged 23-Oct, QA sample submitted 24-Oct, expected release 30-Oct.
* **Enforced Milestone Chronology:**
  $$\text{manufacture\_date} \le \text{quality\_submission\_date} \le \text{expected\_release\_date}$$

### 2.6 Quality Events & Retests (`fact_quality_event`, 2 rows)
* `QEV-2026-001`: Routine release testing on `BATCH-AUG-2026-10` (delay 0 days).
* `QEV-2026-002`: Out-of-Specification (OOS) particle count investigation on `LOT-API-2026-02-QUAR` (delay 150 days).

### 2.7 Production Line Capacity Tracking (`fact_capacity`, 52 rows)
Tracks weekly available vs. committed hours over 26 planning weeks for 2 plant lines:
$$\text{Utilization \%} = \left(\frac{\text{committed\_hours}}{\text{net\_available\_hours}}\right) \times 100$$
* Line availability: 120.0 hours/week, preventive maintenance: 8.0 hours/week.
* `LINE-PLANT1-01`: 40.0 hours booked in Week 2 (PROD-2026-001, utilization = 33.33%).
* `LINE-PLANT1-02`: 30.0 hours booked in Week 3 (PROD-2026-002, utilization = 25.00%).
* All weeks in baseline remain un-overloaded ($\text{is\_overloaded}() = \text{False}$).

### 2.8 Logistics Freight Shipments (`fact_shipment`, 2 rows)
* `SHIP-2026-042`: 10,000 packs T10 delivered from Plant Alpha to DC Nagpur (Road transit, 2 days, 0 cold chain excursions).
* `SHIP-2026-043`: 5,000 packs T10 manifested from DC Nagpur to Hyderabad Hub.

### 2.9 Distribution Supply Plans (`fact_supply_plan`, 2 rows)
* `SPL-2026-001`: 20,000 packs T10 committed for DC Nagpur in Week 3 from `PROD-2026-001`.
* `SPL-2026-002`: 10,000 packs T30 committed for DC Nagpur in Week 4 from `PROD-2026-002`.

---

## 3. Automated Test Suite Verification

The Day 12 implementation is verified by [`tests/test_generator_supply.py`](file:///d:/AI%20Pharmaceutical%20Supply%20Chain/tests/test_generator_supply.py):

| Test Identifier | Verification Focus | Result |
| :--- | :--- | :---: |
| `test_inventory_lots_counts_and_validation` | 9 lots, physical inventory mass conservation, QC status checks | ✅ PASSED |
| `test_purchase_orders_counts_and_milestones` | 4 POs, supplier linkage, delivery date $\ge$ order date milestones | ✅ PASSED |
| `test_production_orders_and_plant_scheduling` | 2 production orders, line assignment, completion $\ge$ start date | ✅ PASSED |
| `test_material_requirements_mrp_netting` | 4 requirements, net shortage formula, 2-day buffer validation | ✅ PASSED |
| `test_batches_genealogy_milestones` | 3 batches, mfg $\le$ QA sample $\le$ release chronological invariant | ✅ PASSED |
| `test_quality_events_linkages` | 2 events, batch and inventory lot foreign key linkages | ✅ PASSED |
| `test_line_capacity_coverage_and_utilization` | 52 records (26 wks $\times$ 2 lines), utilization %, overload method | ✅ PASSED |
| `test_shipments_and_supply_plans` | 2 shipments and 2 supply plans, destination and status integrity | ✅ PASSED |

**Complete Project Test Status:**
```
============================= 73 passed in 1.89s ==============================
```

---

*Document finalized: 11-Nov-2026 (Day 12) | Phase 1 Synthetic Data Generation Engine — On Schedule.*
