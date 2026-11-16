# Disruption Scenario Injection Engine
## Phase 1 Synthetic Data Generation Engine — Day 13 Deliverable
### Week 03 (12-Nov-2026) | Indian Pharmaceutical Supply Chain Network

---

## 1. Executive Summary & Purpose

The **Disruption Scenario Injection Engine** ([`src/generator/disruption_injector.py`](file:///d:/AI%20Pharmaceutical%20Supply%20Chain/src/generator/disruption_injector.py)) implements the benchmark stress-testing framework for the AI-Powered Pharmaceutical Supply Chain Control Tower.

It programmatically injects **5 realistic, high-impact pharmaceutical supply chain crises** spanning upstream supplier bottlenecks, plant floor quality deviations, shared bill-of-materials dependencies, shelf-life expiration dynamics, and operational capacity conflicts.

For each crisis, the engine generates:
1. **Mutated operational state** (delayed POs, on-hold production work orders, revised availability dates).
2. **Algorithmic risk events** ([`fact_risk_event`](file:///d:/AI%20Pharmaceutical%20Supply%20Chain/src/models/control_tower.py)) with composite severity scores:
   $$\text{Score} = 0.30S + 0.20T + 0.15C + 0.15D + 0.10U + 0.10R$$
3. **Traceable relational evidence** ([`bridge_risk_evidence`](file:///d:/AI%20Pharmaceutical%20Supply%20Chain/src/models/control_tower.py)) connecting alerts to verifiable underlying database records.
4. **Backward causal root-cause chains** ([`fact_root_cause`](file:///d:/AI%20Pharmaceutical%20Supply%20Chain/src/models/control_tower.py)).
5. **Non-destructive what-if simulation sandboxes** ([`fact_mitigation_simulation`](file:///d:/AI%20Pharmaceutical%20Supply%20Chain/src/models/control_tower.py)) evaluating cost, feasibility, and risk reduction.
6. **Governed decision proposals** ([`fact_recommendation`](file:///d:/AI%20Pharmaceutical%20Supply%20Chain/src/models/control_tower.py)) with **`human_approval_required = True`** strictly mandated at the schema level.

---

## 2. The 5 Benchmark Disruption Scenarios (A Through E)

```
Benchmark Disruption Architecture:
┌────────────────────────────────────────────────────────────────────────┐
│ Scenario A: Supplier Delivery Delay (PO-2026-001 +14d, 47.5kg deficit) │
├────────────────────────────────────────────────────────────────────────┤
│ Scenario B: Batch QA Sterility Hold (BATCH-10 +10d, QEV-2026-001)      │
├────────────────────────────────────────────────────────────────────────┤
│ Scenario C: Shared Carton Shortage (MAT-PKG-CART stops T10 & T30 lines)│
├────────────────────────────────────────────────────────────────────────┤
│ Scenario D: Sub-MARSL Expiry Risk (LOT-24X RSL < 90d hospital cutoff)  │
├────────────────────────────────────────────────────────────────────────┤
│ Scenario E: Capacity Conflict (Overload 116.7% on LINE-PLANT1-01)      │
└────────────────────────────────────────────────────────────────────────┘
```

### 2.1 Scenario A: 14-Day Critical API Supplier Delay (`SCN-A-API-DELAY`)
* **Physical Trigger:** Supplier `SUP-001` (Ahmedabad) experiences a synthesis column breakdown, delaying purchase order `PO-2026-001` (150 kg API `MAT-API-001`) by +14 days (confirmed delivery slips from 02-Nov to 16-Nov-2026).
* **MRP Netting Impact:** For planned production order `PROD-2026-001` on 09-Nov, required API is 127.5 kg. With 80 kg eligible on hand, net shortage is **47.5 kg**.
* **Plant Floor Impact:** `PROD-2026-001` (20,000 packs T10) placed `On_Hold`.
* **Distribution Impact:** Replenishment `SPL-2026-001` delayed; DC Nagpur projected stockout of **2,400 packs** in Week 4.
* **Risks Scored:**
  * `RISK-2026-001`: Material Shortage on `MAT-API-001` (Score: **80.25**, Severity: `High`).
  * `RISK-2026-002`: Finished Goods Stockout on `SKU-AUG-500-T10` (Score: **84.50**, Severity: `Critical`).
* **Evidence Grounding:** `PO-2026-001` (`DIRECT_CAUSE`), `LOT-API-2026-01` (`CONTRIBUTING_FACTOR`), `PROD-2026-001` (`IMPACTED_OBJECT`).
* **Root Causes:** `RC-2026-001` (Supplier column breakdown + single-source qualification); `RC-2026-002` (Upstream production stoppage).
* **Mitigation Projections:**
  * `SIM-2026-001` / `REC-2026-001`: Dedicated priority air freight expediting (Cost: ₹45,000, 95% risk reduction, `Feasible`).
  * `SIM-2026-002` / `REC-2026-002`: Emergency buffer reallocation of 3,000 packs from DC Nagpur to Hyderabad Hub (Cost: ₹18,000, 100% risk reduction, `Feasible`).

### 2.2 Scenario B: Finished Batch QA Release Hold (`SCN-B-BATCH-HOLD`)
* **Physical Trigger:** Finished packaging batch `BATCH-AUG-2026-10` (15,000 packs T10) triggers sterility testing incubator sensor drift `QEV-2026-001`, delaying batch release by **+10 days** (from 30-Oct to 09-Nov).
* **Impact:** Immediate replenishment is stalled, creating unfulfilled hospital delivery risks in Hyderabad Metro.
* **Risk Scored:** `RISK-2026-003`: QA Hold on `BATCH-AUG-2026-10` (Score: **72.50**, Severity: `High`, 7 days to impact).
* **Evidence Grounding:** `BATCH-AUG-2026-10` (`DIRECT_CAUSE`), `QEV-2026-001` (`ROOT_CAUSE_INVESTIGATION`).
* **Mitigation Projection:** `SIM-2026-003` / `REC-2026-003`: Authorize rapid microbial screening assay to accelerate QA clearance (Cost: ₹25,000, recovers 6 days, `Feasible`).

### 2.3 Scenario C: Shared Packaging Component Shortage (`SCN-C-CARTON-SHORTAGE`)
* **Physical Trigger:** Outer carton converting bottleneck at `SUP-002` impacts `MAT-PKG-CART` (40,000 units deficit). Because cartons are shared across the Bill of Materials for both T10 blister strips and T30 bottles, **both packaging lines are halted simultaneously**.
* **Impact:** `PROD-2026-001` (Line 1) and `PROD-2026-002` (Line 2) are blocked, threatening 30,000 total finished packs.
* **Risk Scored:** `RISK-2026-004`: Shared Component Deficit on `MAT-PKG-CART` (Score: **88.00**, Severity: `Critical`).
* **Evidence Grounding:** `MAT-PKG-CART` (`DIRECT_CAUSE`), `PROD-2026-001` (`IMPACTED_OBJECT`), `PROD-2026-002` (`IMPACTED_OBJECT`).
* **Mitigation Projection:** `SIM-2026-004` / `REC-2026-004`: Emergency qualification and procurement of 40,000 units from secondary certified Pune box converter (Cost: ₹35,000, `Feasible`).

### 2.4 Scenario D: Sub-MARSL Lot Expiry Exposure (`SCN-D-FEFO-EXPOSURE`)
* **Physical Trigger:** Finished lot `LOT-FG-AUG-T10-24X` (3,000 packs at DC Nagpur) expires on `2026-11-20`. Its Remaining Shelf Life is 25 days, which falls below Hyderabad's hospital MARSL of 180 days and Pune's retail MARSL of 90 days.
* **Impact:** The FEFO allocation algorithm disqualifies the lot ($E(l,m,t) = 0$). The physical stock cannot be dispatched and faces complete destruction loss (₹4,80,000 write-off).
* **Risk Scored:** `RISK-2026-005`: Sub-MARSL Rejection / Expiry Exposure (Score: **68.00**, Severity: `Medium`).
* **Evidence Grounding:** `LOT-FG-AUG-T10-24X` (`DIRECT_CAUSE`), `MKT-IN-HYD` (`THRESHOLD_CONSTRAINT`).
* **Mitigation Projection:** `SIM-2026-005` / `REC-2026-005`: Reallocate 3,000 packs to rapid short-cycle retail pharmacy tender at 15% discount (Cost: ₹12,000 discount, preserves ₹4,68,000 inventory value, `Feasible`).

### 2.5 Scenario E: Mitigation Feasibility Conflict (`SCN-E-CAPACITY-CONFLICT`)
* **Physical Trigger:** To recover from delayed orders, a planner attempts to schedule an additional catch-up batch of 20,000 packs on `LINE-PLANT1-01` in Week 2 (requiring 40 machine hours).
* **Conflict:** `LINE-PLANT1-01` already has 100 committed hours and 8 maintenance hours out of 120 net available hours. Adding 40 hours pushes committed load to **140 hours (116.7% utilization)**.
* **Risk Scored:** `RISK-2026-006`: Line Capacity Overload on `LINE-PLANT1-01` (Score: **79.00**, Severity: `High`).
* **Evidence Grounding:** `LINE-PLANT1-01` (`DIRECT_CAUSE`), `CAP-PLANT1-01-W03` (`CAPACITY_CONSTRAINT`).
* **Mitigation Projection:** `SIM-2026-006` / `REC-2026-006`: System flags unconstrained schedule as `INFEASIBLE_CAPACITY` and simulates adding a 24-hour weekend 3rd shift overtime differential to lower utilization to 97.2% (Cost: ₹60,000 overtime premium, `Feasible with approval`).

---

## 3. Strict Governance & Architectural Invariants

1. **Human Approval Mandate:**
   * In `FactRecommendation`, `human_approval_required = True` is hardcoded. Any attempt to set it to `False` raises an unhandled `ValidationError`.
   * Initial `approval_status` must always be `Pending_Review`.
2. **Anti-Hallucination Evidence Links:**
   * Every risk in `fact_risk_event` is cross-referenced in `bridge_risk_evidence` to physical records (`PO-2026-001`, `BATCH-AUG-2026-10`, `MAT-PKG-CART`, `LOT-FG-AUG-T10-24X`, `LINE-PLANT1-01`).
3. **Dual Mode Compatibility:**
   * By default, `inject_disruptions()` outputs Scenario A, maintaining the Phase 1 baseline of **691 verified records**.
   * Callers can specify `scenarios = ["SCN-A-API-DELAY", "SCN-B-BATCH-HOLD", ...]` to generate the full benchmark suite on demand.

---

## 4. Automated Test Suite Verification

The Day 13 deliverable is verified by [`tests/test_disruption_injector.py`](file:///d:/AI%20Pharmaceutical%20Supply%20Chain/tests/test_disruption_injector.py):

| Test Identifier | Verification Focus | Result |
| :--- | :--- | :---: |
| `test_scenario_a_supplier_delay` | PO delivery slip (+14d), MRP 47.5kg shortage, 2 risks, 5 evidence links | ✅ PASSED |
| `test_scenario_b_batch_qa_hold` | Sterility retest, QA hold risk (Score 72.50), rapid microbial assay | ✅ PASSED |
| `test_scenario_c_carton_shortage` | Shared carton deficit, dual-line stoppage (T10 & T30), backup converter | ✅ PASSED |
| `test_scenario_d_fefo_exposure` | Sub-MARSL RSL < 90d, hospital disqualification, discount liquidation | ✅ PASSED |
| `test_scenario_e_capacity_conflict` | 116.7% line overload, INFEASIBLE_CAPACITY flag, weekend shift resolution | ✅ PASSED |
| `test_full_benchmark_suite_aggregation` | Aggregates all 6 risks (A-E) and validates human approval on all 6 recs | ✅ PASSED |
| `test_default_scenario_compatibility` | Confirms default call produces exact baseline slice (2 risks, 691 total records) | ✅ PASSED |

**Complete Project Test Status:**
```
============================= 80 passed in 2.01s ==============================
```

---

*Document finalized: 12-Nov-2026 (Day 13) | Phase 1 Synthetic Data Generation Engine — On Schedule.*
