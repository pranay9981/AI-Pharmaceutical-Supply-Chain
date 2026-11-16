# Generator Architecture & Master Record Synthesizer
## Phase 1 Synthetic Data Generation Engine — Day 10 Deliverable
### Week 03 (09-Nov-2026) | Indian Pharmaceutical Supply Chain Network

---

## 1. Executive Summary & Purpose

The **Generator Architecture & Master Record Synthesizer** ([`src/generator/master_data.py`](file:///d:/AI%20Pharmaceutical%20Supply%20Chain/src/generator/master_data.py)) serves as the foundational data synthesis engine of the AI-Powered Pharmaceutical Supply Chain Control Tower. It is responsible for programmatically generating all master dimensions, relational bridge entities, and disruption scenario descriptors that populate the Tier 1 relational data layer.

All synthetic records produced by this module are strictly validated against the finalized **Pydantic v2 domain schemas** defined in `src/models/master.py`, `src/models/bridges.py`, and `src/models/control_tower.py`.

```
Generator Engine Workflow:
┌─────────────────────────────────┐
│ GeneratorConfig (Seed: 20261014)│
└───────────────┬─────────────────┘
                ▼
┌─────────────────────────────────────────────────────────────┐
│ src/generator/master_data.py                                │
│ ├── 8 Master Dimensions (Products, SKUs, Materials, etc.)  │
│ ├── 4 Network Bridges (BOM, Supplier-Mat, SKU-Mkt, Routes) │
│ └── Scenario Catalog (SCN-BASE, SCN-A through SCN-E)        │
└───────────────┬─────────────────────────────────────────────┘
                ▼ (Strict Pydantic v2 Model Instantiation)
┌─────────────────────────────────────────────────────────────┐
│ 100% Validated Relational Model Objects                     │
│ └── Fed to runner.py -> SQLite, Parquet, and CSV            │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Seed Reproducibility Strategy

To satisfy strict pharmaceutical governance and auditability standards, the generator avoids pseudo-random drift:
* **Fixed Random Seed:** `20261014` (configured in [`src/generator/config.py`](file:///d:/AI%20Pharmaceutical%20Supply%20Chain/src/generator/config.py)).
* **Dual Random Initialization:** `init_random_seed()` synchronizes both Python's standard `random` module and `numpy.random`.
* **Zero Run-to-Run Divergence:** Successive generator invocations produce bitwise-identical records, verified by automated unit tests (`tests/test_generator_master.py::test_seed_reproducibility`).

---

## 3. Indian Multi-Echelon Network Topology

The synthetic network reflects the real-world geographic distribution of the Indian pharmaceutical industry:

| Node ID | Facility Name | Node Type | City | State | Key Function |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `LOC-SUP-01` | Deccan API Synthesis Plant | `SUPPLIER` | Ahmedabad | Gujarat | Primary chemical synthesis of Amoxicillin / Clavulanate API |
| `LOC-SUP-02` | Western Packaging Converting Facility | `SUPPLIER` | Pune | Maharashtra | Secondary packaging converting (blister foils, bottles, cartons) |
| `LOC-PLANT-01` | Plant Alpha Hyderabad Pharma Campus | `MANUFACTURING_PLANT` | Hyderabad | Telangana | High-speed granulation, tableting, blister packing, and cartoning |
| `LOC-DC-01` | Central India Logistics Distribution Centre | `DISTRIBUTION_CENTRE` | Nagpur | Maharashtra | Central multi-echelon buffer warehouse and transit cross-dock |
| `LOC-MKT-HYD` | Hyderabad Metro Regional Hub | `MARKET` | Hyderabad | Telangana | Destination hub for tertiary hospitals and major institutional buyers |
| `LOC-MKT-PUN` | Pune Urban Regional Hub | `MARKET` | Pune | Maharashtra | Destination hub for urban pharmacy chains and healthcare wholesalers |

---

## 4. Master Dimension Entities (8 Tables)

### 4.1 Product Family (`dim_product`)
* **`PRD-AUG`**: Augmentin (Antibiotic-Penicillin, Anti-Infectives).
* Marked with `critical_medicine_flag = True` and `synthetic_data_flag = True`.

### 4.2 Finished SKUs (`dim_finished_sku`)
* **`SKU-AUG-500-T10`**: Augmentin 500mg/125mg Tablet (10-Tablet Alu-Alu Strip Pack). Approved shelf life: 730 days (2 years).
* **`SKU-AUG-500-T30`**: Augmentin 500mg/125mg Tablet (30-Tablet HDPE Bottle Pack). Approved shelf life: 730 days (2 years).

### 4.3 Component Materials (`dim_material`)
* **`MAT-API-001`**: Synthetic Amoxicillin / Clavulanate API Blend (kg, 540 days shelf life, 5 days QC release lead time, critical).
* **`MAT-EXC-001`**: Microcrystalline Cellulose & Excipient Granules (kg, 720 days shelf life, 3 days QC release lead time).
* **`MAT-PKG-BLIST`**: Printed Aluminum Blister Foil Strip for T10 (units, 1095 days shelf life).
* **`MAT-PKG-BOTT`**: HDPE Pharmaceutical Bottle & Closure 100cc for T30 (units, 1095 days shelf life).
* **`MAT-PKG-CART`**: Printed Outer Carton Packaging Box (units, 730 days shelf life, critical shared component).

### 4.4 Qualified Suppliers (`dim_supplier`)
* **`SUP-001`**: Deccan Active Pharma Chem Pvt Ltd (API Manufacturer, lead time 21 days, MOQ 100 kg, order multiple 50 kg, OTIF target 95%, single-source).
* **`SUP-002`**: Western Healthcare Packaging Solutions Ltd (Packaging Supplier, lead time 14 days, MOQ 5000 units, order multiple 1000 units, OTIF target 96%).

### 4.5 Customer Accounts (`dim_customer`)
* `CUST-001`: Telangana State Health Wholesalers Ltd (Wholesaler, Tier-1, Hyderabad).
* `CUST-002`: Deccan Apex Hospital Network (Hospital, Tier-1, Hyderabad).
* `CUST-003`: Western Medical Logistics Consortium (Wholesaler, Tier-1, Pune).
* `CUST-004`: Sahyadri Care Clinics & Pharmacies (Pharmacy Chain, Tier-2, Pune).

### 4.6 Commercial Demand Zones (`dim_market`)
* `MKT-IN-HYD`: Hyderabad Metro & Telangana Zone (South region).
* `MKT-IN-PUN`: Pune Urban & Western Maharashtra Zone (West region).

### 4.7 Production Lines (`dim_production_line`)
* `LINE-PLANT1-01`: Oral Solid Dosage Granulation & Compression Line 1 (5,000 packs/hr standard rate).
* `LINE-PLANT1-02`: High-Speed Blister Thermoforming & Cartoning Line 2 (6,000 packs/hr standard rate).

---

## 5. Network Topology & Bridge Entities (4 Tables)

### 5.1 Bill of Materials (`bridge_bill_of_material`)
Defines per-pack ingredient requirements and scrap allowances:
$$\text{Gross Component Requirement} = \text{Finished Units} \times \text{Qty Per Unit} \times \left(1 + \frac{\text{Scrap \%}}{100}\right)$$

* **T10 Strip:**
  * `MAT-API-001`: 0.00625 kg/pack (6.25g) + 2.0% scrap
  * `MAT-EXC-001`: 0.00200 kg/pack (2.0g) + 1.5% scrap
  * `MAT-PKG-BLIST`: 1.00000 unit/pack + 1.0% scrap
  * `MAT-PKG-CART`: 1.00000 unit/pack + 1.0% scrap
* **T30 Bottle:**
  * `MAT-API-001`: 0.01875 kg/pack (18.75g) + 2.0% scrap
  * `MAT-EXC-001`: 0.00600 kg/pack (6.0g) + 1.5% scrap
  * `MAT-PKG-BOTT`: 1.00000 unit/pack + 1.0% scrap
  * `MAT-PKG-CART`: 1.00000 unit/pack + 1.0% scrap (*Shared secondary packaging*)

### 5.2 Approved Vendor Sourcing Lanes (`bridge_supplier_material`)
* `SUP-001` approved for `MAT-API-001` (21 days) and `MAT-EXC-001` (14 days).
* `SUP-002` approved for `MAT-PKG-BLIST`, `MAT-PKG-BOTT`, and `MAT-PKG-CART` (14 days each).

### 5.3 Market Authorizations & MARSL Thresholds (`bridge_sku_market`)
* **Hyderabad Metro (`MKT-IN-HYD`)**: Institutional hospital tender market mandating strict **MARSL = 180 days** (6 months minimum shelf life at delivery) with a 98% target service level.
* **Pune Urban (`MKT-IN-PUN`)**: Commercial pharmacy market mandating standard **MARSL = 90 days** (3 months minimum shelf life at delivery) with a 98% target service level.

### 5.4 Inter-Facility Freight Routes (`bridge_location_route`)
1. `LOC-PLANT-01` (Hyderabad) $\rightarrow$ `LOC-DC-01` (Nagpur): 2 days road transit, ₹0.35/unit freight cost.
2. `LOC-DC-01` (Nagpur) $\rightarrow$ `LOC-MKT-HYD` (Hyderabad): 1 day road transit, ₹0.20/unit freight cost.
3. `LOC-DC-01` (Nagpur) $\rightarrow$ `LOC-MKT-PUN` (Pune): 2 days road transit, ₹0.25/unit freight cost.
* Enforces endpoint distinctness: $\text{origin\_location\_id} \neq \text{destination\_location\_id}$.

---

## 6. Disruption Scenario Registry (`dim_scenario`)

The master module provides both baseline generation and full benchmark catalog support:
* `SCN-BASE`: Baseline unconstrained plan.
* `SCN-A-API-DELAY`: 14-day delay in Amoxicillin API delivery from `SUP-001`.
* `SCN-B-BATCH-HOLD`: 10-day QA sterility hold on finished batch `BATCH-AUG-2026-01`.
* `SCN-C-CARTON-SHORTAGE`: Shared secondary packaging shortage on `MAT-PKG-CART`.
* `SCN-D-FEFO-EXPOSURE`: Sub-MARSL lot expiry risk (<90 days remaining shelf life).
* `SCN-E-CAPACITY-CONFLICT`: Feasibility conflict / 116% line utilization overload on `LINE-PLANT1-01`.

---

## 7. Automated Test Suite & Verification Results

The Day 10 deliverable includes dedicated unit tests in [`tests/test_generator_master.py`](file:///d:/AI%20Pharmaceutical%20Supply%20Chain/tests/test_generator_master.py):

| Test Identifier | Verification Focus | Result |
| :--- | :--- | :---: |
| `test_seed_reproducibility` | Bitwise reproducibility across repeated generator runs | ✅ PASSED |
| `test_master_record_counts_and_validation` | Validation and schema compliance of all 8 Master Dimension models | ✅ PASSED |
| `test_bridge_bom_structure_and_scrap_math` | BOM link integrity, shared carton mapping, and gross scrap math | ✅ PASSED |
| `test_bridge_supplier_material_parameters` | Vendor lead times, MOQs, order multiples, and approved flags | ✅ PASSED |
| `test_bridge_sku_market_marsl_thresholds` | Differentiated MARSL criteria (180 days Hyd vs 90 days Pun) | ✅ PASSED |
| `test_bridge_location_routes_and_topology` | Route graph validation, transit times, and self-loop prevention | ✅ PASSED |
| `test_scenario_catalog_options` | Baseline vs full benchmark suite catalog generation | ✅ PASSED |

**Complete Project Test Status:**
```
============================= 59 passed in 1.64s ==============================
```

---

*Document finalized: 09-Nov-2026 (Day 10) | Phase 1 Synthetic Data Generation Engine — On Schedule.*
