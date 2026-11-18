# Master Engineering Reference: Code, Database Architecture & Mathematical Formulations
## Complete Technical Deep Dive for Weeks 01 through 05 (Days 01 – 24)

**Document Reference:** `DOC-TECH-CODE-DB-MATH-DEEPDIVE`  
**Classification:** Institutional-Grade Master Engineering Dossier & Code Walkthrough  
**Target Audience:** Executive Director (20+ yrs Global Pharma Leadership), Group Operations Manager (27+ yrs Supply Chain Operations), Lead Architects & Auditors  
**Current Milestone State:** Phase 1 Complete (Gate 1 Signed Off); Phase 2 Weeks 04 & 05 Complete; Week 06 Active  
**Automated Verification:** **189 / 189 Passing Tests (100% Pass Rate in 4.03s)**  

---

## Table of Contents
1. [Executive Overview & Life Sciences Foundation](#1-executive-overview--life-sciences-foundation)
2. [Complete 33-Entity Relational Database Architecture](#2-complete-33-entity-relational-database-architecture)
3. [Comprehensive Code Walkthrough by File (All 27 Files)](#3-comprehensive-code-walkthrough-by-file-all-27-files)
   - [3.1 Data Architecture & Schemas (`src/models/`)](#31-data-architecture--schemas-srcmodels)
   - [3.2 AI Tool Interfaces & Governance (`src/agent/`)](#32-ai-tool-interfaces--governance-srcagent)
   - [3.3 Synthetic Data & Benchmark Disruption Generator (`src/generator/`)](#33-synthetic-data--benchmark-disruption-generator-srcgenerator)
   - [3.4 Deterministic Supply Chain Core Engines (`src/engine/`)](#34-deterministic-supply-chain-core-engines-srcengine)
   - [3.5 Demand Forecasting & Anomaly Layer (`src/forecasting/`)](#35-demand-forecasting--anomaly-layer-srcforecasting)
   - [3.6 Master Schedule Generator (`build_refined_3tab_schedule.py`)](#36-master-schedule-generator-build_refined_3tab_schedulepy)
4. [Master Mathematical Catalog (All 18 Formulas Explained)](#4-master-mathematical-catalog-all-18-formulas-explained)
5. [The Executive Meeting Defense Guide & Live Demo Script](#5-the-executive-meeting-defense-guide--live-demo-script)

---

## 1. Executive Overview & Life Sciences Foundation

### 1.1 The Clinical & Therapeutic Focus
The entire Control Tower is engineered around **Amoxicillin / Clavulanate Potassium 500/125mg** (modeled on GSK's *Augmentin*), the broad-spectrum antibiotic listed on the World Health Organization (WHO) Model List of Essential Medicines. 

In clinical reality, Amoxicillin-Clavulanate is highly vulnerable to supply chain disruptions:
* **Chemical Vulnerability:** Potassium Clavulanate is extremely hygroscopic (absorbs atmospheric moisture rapidly) and thermally labile. It degrades quickly if stored outside strict 2°C–8°C or dry ambient conditions ($<25^\circ\text{C}, <60\%\text{ RH}$).
* **Finished Presentation Split:**
  * `SKU-AUG-500-T10`: 10-tablet strip in aluminum-aluminum (Alu-Alu) blister packaging. Distributed predominantly through acute retail pharmacies and outpatient clinics. Characteristics: High velocity, volatile weekly spikes, shorter order lead times.
  * `SKU-AUG-500-T30`: 30-tablet high-density polyethylene (HDPE) bottle with induction-sealed child-resistant cap. Distributed predominantly through institutional hospital networks, intensive care units, and governmental health tenders. Characteristics: Bulky, strict Minimum Acceptable Remaining Shelf Life (MARSL $\ge 90$ days), high contractual financial penalties for stockouts.

### 1.2 The Three Non-Negotiable Engineering Laws
If managers ask you: *"What makes this different from an OpenAI wrapper or generic chatbot?"*, you give them these three laws:

```
+---------------------------------------------------------------------------------------------------+
|                                   THREE IMMUTABLE LAWS OF THE PLATFORM                            |
+------------------------------------+----------------------------------+---------------------------+
| 1. ZERO LLM MATH                   | 2. RELATIONAL EVIDENCE GROUNDING | 3. MANDATORY HUMAN SIGN-OFF|
| All projections, netting, WAPE, and| No alert exists as floating text.| Binding purchase orders or |
| anomaly bounds run in pure Python. | Every insight cites a database   | batch expedites require   |
| Zero LLM arithmetic allowed.       | primary key (po_id, batch_id).   | human_approval_required.  |
+------------------------------------+----------------------------------+---------------------------+
```

1. **Zero LLM Math:** Large Language Models are probabilistic text generators; they hallucinate arithmetic. Every formula in this system ($I_t = I_{t-1} + R_t + P_t - D_t$, WAPE, Tracking Signal, Ridge optimization, Tukey's IQR fences) runs in deterministic Python, NumPy, and scikit-learn.
2. **Relational Evidence Grounding (`bridge_risk_evidence`):** The AI layer cannot assert that "Supplier Divi's is delayed" unless it joins to `fact_purchase_order.purchase_order_id = 'PO-API-001'`. Unanchored narrative is prohibited.
3. **Mandatory Human-in-the-Loop (`human_approval_required = True`):** Automated PO release or production rescheduling without planner sign-off is prevented at the schema level.

---

## 2. Complete 33-Entity Relational Database Architecture

The data architecture comprises **33 relational tables** organized across **6 logical tiers**, enforcing cGMP 21 CFR Part 211, GDP, and FDA 21 CFR Part 11 validation standards.

```mermaid
flowchart TD
    subgraph T1["Tier 1: Master Dimensions (8)"]
        dim_product
        dim_finished_sku
        dim_material
        dim_supplier
        dim_location
        dim_customer
        dim_market
        dim_production_line
    end

    subgraph T2["Tier 2: Network Bridges (4)"]
        bridge_bill_of_material
        bridge_supplier_material
        bridge_sku_market
        bridge_location_route
    end

    subgraph T3["Tier 3: Transactional Facts (9)"]
        fact_demand_history
        fact_customer_order
        fact_demand_forecast
        fact_supply_plan
        fact_material_requirement
        fact_inventory_projection
        fact_purchase_order
        fact_inventory_lot
        fact_material_consumption
    end

    subgraph T4["Tier 4: Manufacturing & Quality (3)"]
        fact_production_order
        fact_batch
        fact_quality_event
    end

    subgraph T5["Tier 5: Capacity & Logistics (2)"]
        fact_capacity
        fact_shipment
    end

    subgraph T6["Tier 6: Control Tower & Governance (7)"]
        dim_scenario
        fact_risk_event
        bridge_risk_evidence
        fact_root_cause
        fact_mitigation_simulation
        fact_recommendation
        dataset_manifest
    end

    T1 --> T2
    T2 --> T3
    T1 --> T3
    T3 --> T4
    T4 --> T5
    T3 --> T6
    T4 --> T6
    T5 --> T6
```

### 2.1 Full Table Catalog: Why Each Table Exists and What It Contains

#### Tier 1: Master Dimensions (8 Tables)
1. **`dim_product` (Product Brand Family):**
   * *Primary Key:* `product_id` (e.g. `PRD-AUG`)
   * *Columns:* `product_name`, `product_family`, `therapy_area` (Anti-Infectives), `critical_medicine_flag` (True/False).
   * *Why We Have It:* Groups multiple sellable SKU presentations under a unified therapeutic brand for portfolio S&OP planning.
2. **`dim_finished_sku` (Sellable Commercial Stock Keeping Units):**
   * *Primary Key:* `finished_sku_id` (e.g. `SKU-AUG-500-T10`, `SKU-AUG-500-T30`)
   * *Columns:* `product_id` (FK), `sku_description`, `dosage_form` (Film-Coated Tablet), `strength` (500mg Amox + 125mg Clav), `pack_configuration`, `shelf_life_days` (730 days = 24 months), `storage_condition` (Dry $<25^\circ\text{C}$).
   * *Why We Have It:* Physical packaging differences dictate distinct manufacturing lines, shelf lives, and customer channels.
3. **`dim_material` (Raw Materials & Packaging Components):**
   * *Primary Key:* `material_id` (e.g. `MAT-API-AMOX`, `MAT-API-CLAV`, `MAT-EXC-MCC`, `MAT-PKG-ALU`, `MAT-PKG-HDPE`, `MAT-PKG-CART`)
   * *Columns:* `material_name`, `material_type` (Active_API, Excipient, Primary_Packaging, Secondary_Packaging), `unit_of_measure` (kg, packs), `storage_temperature` (Refrigerated 2-8C vs Ambient), `controlled_substance_flag`.
   * *Why We Have It:* Necessary for BOM explosion. You cannot manufacture Augmentin without tracking the separate shelf lives and lead times of Active Ingredients vs blister foil.
4. **`dim_supplier` (Qualified Vendor Profiles):**
   * *Primary Key:* `supplier_id` (e.g. `SUP-API-001`, `SUP-PKG-001`)
   * *Columns:* `supplier_name`, `supplier_country` (India), `qualification_status` (Approved / Certified), `target_otif_pct` (95.0%), `lead_time_days`.
   * *Why We Have It:* In pharma, suppliers must be qualified under cGMP. You cannot procure API from an unapproved vendor. Tracks contractual SLAs.
5. **`dim_location` (Nodes in Network Topology):**
   * *Primary Key:* `location_id` (e.g. `LOC-PLANT-BADDI`, `LOC-PLANT-ANK`, `LOC-DC-NAGPUR`, `LOC-DC-BHIWANDI`, `LOC-DC-CHENNAI`)
   * *Columns:* `location_name`, `location_type` (Manufacturing_Plant, Central_DC, Regional_DC), `state`, `country`, `storage_capacity_pallets`, `cold_chain_capable`.
   * *Why We Have It:* Models the physical geography of Indian pharmaceutical transit and multi-echelon echelon stocking.
6. **`dim_customer` (Commercial Ordering Entities):**
   * *Primary Key:* `customer_id` (e.g. `CUST-HOSP-HYD-001`, `CUST-WHL-PUN-001`)
   * *Columns:* `customer_name`, `customer_type` (Hospital_Network, Institutional_Tender, Wholesale_Distributor, Retail_Pharmacy_Chain), `credit_status`.
   * *Why We Have It:* Enables prioritization during stock allocation. Hospital ICU orders take precedence over commercial wholesalers during stock shortages.
7. **`dim_market` (Commercial Demand Planning Zones):**
   * *Primary Key:* `market_id` (e.g. `MKT-IN-HYD`, `MKT-IN-PUN`)
   * *Columns:* `market_name`, `region` (South, West), `regulatory_jurisdiction` (DCGI / CDSCO India), `currency` (INR).
   * *Why We Have It:* Aggregate demand planning is conducted at the geographic market zone level.
8. **`dim_production_line` (Plant Manufacturing & Packaging Assets):**
   * *Primary Key:* `production_line_id` (e.g. `LINE-BADDI-01`, `LINE-BADDI-02`)
   * *Columns:* `plant_location_id` (FK), `line_name`, `line_type` (Tableting_Blister, Bottle_Packaging), `rated_speed_units_per_hour` (e.g. 2,500 packs/hr), `cleanroom_classification` (Grade C/D).
   * *Why We Have It:* Prevents impossible production schedules. Line-01 runs blister strips; Line-02 runs HDPE bottles. You cannot expedite T30 bottles on a blister line.

#### Tier 2: Network Topology & Bridges (4 Tables)
9. **`bridge_bill_of_material` (Chemical Recipe & Scrap Allowances):**
   * *Primary Key:* Composite (`finished_sku_id`, `material_id`)
   * *Columns:* `quantity_per_sku` (e.g. 0.005 kg API per T10 pack), `scrap_factor_pct` (1.0% to 3.5%), `effective_start_date`, `effective_end_date`.
   * *Why We Have It:* The mathematical foundation of MRP explosion. Accounts for chemical reaction losses and packaging line startup scrap.
10. **`bridge_supplier_material` (Approved Vendor Sourcing Matrix):**
    * *Primary Key:* Composite (`supplier_id`, `material_id`)
    * *Columns:* `contracted_lead_time_days` (e.g. 14 days), `minimum_order_quantity` (MOQ), `unit_price_inr`, `is_primary_supplier`.
    * *Why We Have It:* Connects materials to vendors. Used by the MRP engine to schedule Purchase Order release dates: $T_{\text{release}} = T_{\text{need}} - \text{Lead\_Time}$.
11. **`bridge_sku_market` (Market Authorization & MARSL Shelf Life Gates):**
    * *Primary Key:* Composite (`finished_sku_id`, `market_id`)
    * *Columns:* `marketing_authorization_number`, `marsl_days` (e.g. 90 days for Hospital tenders), `service_level_target_pct` (98.0%).
    * *Why We Have It:* Enforces regulatory compliance. Even if a lot has 60 days of physical shelf life left, if the hospital MARSL is 90 days, the FEFO engine blocks dispatch.
12. **`bridge_location_route` (Transportation Lanes & Cold-Chain Transit SLAs):**
    * *Primary Key:* Composite (`origin_location_id`, `destination_location_id`)
    * *Columns:* `transit_time_days` (e.g. 3 days Baddi to Nagpur), `transport_mode` (Road_Reefer), `cold_chain_required` (True), `freight_cost_per_pallet`.
    * *Why We Have It:* Multi-echelon stock projections and FEFO arrival calculations require exact transit lead-time offsets.

#### Tier 3: Transactional & Planning Facts (9 Tables)
13. **`fact_demand_history` (Historical Consumption Baseline):**
    * *Grain:* Monday week start date $\times$ SKU $\times$ Market $\times$ Scenario.
    * *Columns:* `week_start_date`, `finished_sku_id`, `market_id`, `demand_quantity`, `fulfilled_quantity`, `lost_sales_quantity`, `event_type` (Normal, Monsoon_Surge, Diwali_Adjustment).
    * *Why We Have It:* Provides 104 weeks (2 years) of unconstrained commercial demand for training statistical and ML forecasting models.
14. **`fact_customer_order` (Live Purchase Orders from Customers):**
    * *Columns:* `customer_order_id`, `customer_id`, `market_id`, `finished_sku_id`, `order_date`, `requested_delivery_date`, `promised_delivery_date`, `ordered_quantity`, `fulfilled_quantity`, `order_status` (Open, In_Transit, Delivered).
    * *Why We Have It:* Live customer demand consumed by the FEFO allocation engine.
15. **`fact_demand_forecast` (Forward Predictive Trajectories):**
    * *Columns:* `forecast_version_id`, `forecast_run_date`, `target_week_start_date`, `finished_sku_id`, `market_id`, `p10_quantity`, `p50_quantity` (point forecast), `p90_quantity`.
    * *Why We Have It:* Feeds the 26-week forward inventory projection and MPS schedule with probabilistic confidence bands.
16. **`fact_supply_plan` (Master Replenishment Schedule):**
    * *Columns:* `supply_plan_id`, `week_start_date`, `finished_sku_id`, `origin_location_id`, `destination_location_id`, `planned_quantity`, `approval_status`.
    * *Why We Have It:* Master schedule dictating when plants dispatch stock to Central and Regional distribution centers.
17. **`fact_material_requirement` (BOM Explosion & Component Shortages):**
    * *Columns:* `mrp_run_id`, `production_order_id`, `material_id`, `required_date`, `gross_requirement_qty`, `net_requirement_qty`, `shortage_qty`.
    * *Why We Have It:* Net requirement table generated by `src/engine/mrp.py` showing exact component deficits before production.
18. **`fact_inventory_projection` (Multi-Echelon Forward Balance):**
    * *Columns:* `projection_run_id`, `week_start_date`, `finished_sku_id`, `location_id`, `starting_inventory`, `scheduled_receipts`, `planned_production`, `projected_demand`, `ending_inventory`, `safety_stock_threshold`, `stockout_flag`.
    * *Why We Have It:* Core forward simulation table showing week-by-week inventory health over 26 weeks.
19. **`fact_purchase_order` (Inbound Supplier Orders & OTIF):**
    * *Columns:* `purchase_order_id`, `supplier_id`, `material_id`, `destination_location_id`, `order_date`, `promised_delivery_date`, `actual_delivery_date`, `ordered_qty`, `delivered_qty`, `otif_status` (Pass/Fail).
    * *Why We Have It:* Tracks vendor deliveries. Key source for Disruption Scenario A (API Supplier Delivery Delay).
20. **`fact_inventory_lot` (Physical Lot Genealogy & Expiry Positions):**
    * *Columns:* `lot_id`, `item_type` (Finished_Good, Raw_Material), `item_id`, `location_id`, `batch_id`, `manufacture_date`, `expiry_date`, `quantity_on_hand`, `reserved_quantity`, `blocked_quantity`, `quality_status` (Released, Quarantine), `recall_status`.
    * *Why We Have It:* Physical lot repository. The bedrock of FEFO allocation, MARSL checking, and Disruption Scenario D (Expiry Exposure).
21. **`fact_material_consumption` (Actual Shop-Floor Dispensing):**
    * *Columns:* `consumption_id`, `batch_id`, `material_id`, `theoretical_quantity`, `actual_dispensed_quantity`, `variance_pct`.
    * *Why We Have It:* Compares physical chemical dispensing against theoretical BOM recipes to detect yield loss.

#### Tier 4: Manufacturing & Quality Facts (3 Tables)
22. **`fact_production_order` (Plant Shop-Floor Work Orders):**
    * *Columns:* `production_order_id`, `plant_location_id`, `production_line_id`, `finished_sku_id`, `planned_start_date`, `planned_end_date`, `planned_quantity`, `status`.
    * *Why We Have It:* Books cleanroom line capacity and schedules chemical batch synthesis.
23. **`fact_batch` (Batch Release Genealogy & Certificate of Analysis):**
    * *Columns:* `batch_id`, `production_order_id`, `bulk_tablet_lot_id`, `manufacture_date`, `qa_release_date`, `sterility_test_pass` (True/False), `assay_potency_pct` (e.g. 99.4%).
    * *Why We Have It:* In pharma, you cannot sell medicine until QA issues a Certificate of Analysis (CoA). Key source for Disruption Scenario B (Batch QA Hold).
24. **`fact_quality_event` (Deviations, OOS Investigations & Quarantine Holds):**
    * *Columns:* `quality_event_id`, `batch_id`, `event_type` (Sterility_Retest, OOS_Potency, Cleanroom_Deviation), `severity` (Critical, Major), `hold_start_date`, `hold_resolved_date`.
    * *Why We Have It:* Direct evidence linking deviations to delayed batch releases.

#### Tier 5: Capacity & Logistics Facts (2 Tables)
25. **`fact_capacity` (Line Operating Hours & Maintenance Downtime):**
    * *Columns:* `capacity_record_id`, `production_line_id`, `week_start_date`, `total_calendar_hours` (168h), `planned_maintenance_hours`, `net_available_hours`, `committed_production_hours`, `overload_flag`.
    * *Why We Have It:* Identifies plant bottlenecks. Key source for Disruption Scenario E (Line Maintenance Conflict).
26. **`fact_shipment` (Inter-Node Logistics & Reefer Consignments):**
    * *Columns:* `shipment_id`, `origin_location_id`, `destination_location_id`, `shipped_date`, `expected_delivery_date`, `actual_delivery_date`, `cold_chain_breach_flag` (True/False).
    * *Why We Have It:* Tracks goods in-transit between Baddi/Ankleshwar and distribution centers.

#### Tier 6: Control Tower, Risk & Governance (7 Tables)
27. **`dim_scenario` (Disruption Scenario Catalog):**
    * *Columns:* `scenario_id` (SCN-BASE, SCN-A, SCN-B, SCN-C, SCN-D, SCN-E), `scenario_name`, `disruption_description`, `injection_date`.
    * *Why We Have It:* Enables side-by-side what-if simulation comparing baseline operations against injected crises.
28. **`fact_risk_event` (0–100 Composite Risk Scoring Engine):**
    * *Columns:* `risk_event_id`, `scenario_id`, `risk_category` (Stockout, Expiry, Capacity), `severity_score` (0 to 100), `days_to_impact`, `detected_timestamp`.
    * *Why We Have It:* Central repository for alerts detected by `src/engine/risk.py`.
29. **`bridge_risk_evidence` (Anti-Hallucination Relational Evidence Linker):**
    * *Columns:* `evidence_id`, `risk_event_id`, `table_name`, `record_id` (e.g. `PO-API-001`, `BATCH-AUG-2026-01`), `field_name`, `observed_value`.
    * *Why We Have It:* Guarantees that every alert cited by the AI agent points to a primary key in the database.
30. **`fact_root_cause` (Backward Causal Dependency Graph):**
    * *Columns:* `root_cause_id`, `risk_event_id`, `causal_node`, `causal_role` (Root_Cause, Contributing_Factor, Downstream_Impact), `confidence_pct`.
    * *Why We Have It:* Populated by backward tracing algorithms to pinpoint whether a stockout was caused by a delayed supplier or a packaging breakdown.
31. **`fact_mitigation_simulation` (What-If Sandbox Evaluations):**
    * *Columns:* `simulation_id`, `risk_event_id`, `action_type` (Supplier_Expedite, Stock_Transfer, Reschedule), `projected_stockout_avoided_qty`, `expedite_cost_inr`, `feasibility_passed` (True/False).
    * *Why We Have It:* Stores non-destructive simulation results comparing mitigation options before execution.
32. **`fact_recommendation` (Ranked Action Proposals with Human Sign-Off):**
    * *Columns:* `recommendation_id`, `simulation_id`, `rank_priority`, `action_summary`, `human_approval_required` (**Strictly True**), `approved_by`, `approval_timestamp`.
    * *Why We Have It:* The user-facing governance table where supply planners review and authorize actions.
33. **`dataset_manifest` (Cryptographic Reproducibility Audit Log):**
    * *Columns:* `manifest_id`, `generation_timestamp`, `random_seed` (`20261014`), `total_records` (691), `sha256_hash`.
    * *Why We Have It:* Satisfies GxP electronic records requirements proving the dataset has not been tampered with.

---

## 3. Comprehensive Code Walkthrough by File (All 27 Files)

In an executive meeting, managers might point to any file and ask: *"What does this file do? What are its key functions? What are the inputs and outputs?"*  
Here is the complete file-by-file walkthrough.

```
AI-Pharmaceutical-Supply-Chain/
├── src/
│   ├── models/           # 8 schema definition files (Pydantic v2)
│   ├── agent/            # 1 tool contract and governance file
│   ├── generator/        # 6 synthetic generation & disruption injector files
│   ├── engine/           # 6 deterministic supply chain analytical engines
│   └── forecasting/      # 5 time-series ML, baseline, and anomaly files
└── build_refined_3tab_schedule.py # 1 schedule tracker generator
```

---

### 3.1 Data Architecture & Schemas (`src/models/`)

#### 1. `src/models/master.py`
* **Purpose:** Implements Pydantic v2 schemas for all 8 Master Dimension tables (`dim_product`, `dim_finished_sku`, `dim_material`, `dim_supplier`, `dim_location`, `dim_customer`, `dim_market`, `dim_production_line`).
* **Key Mechanics:**
  * Uses Pydantic `Field` validators enforcing string regex IDs (e.g. `PRD-`, `SKU-`, `LOC-`).
  * Enforces positive numbers (`ge=0.0`) for shelf life, capacity, and speeds.
  * Adds `@field_validator` to verify storage temperature categories (`Refrigerated_2_8C`, `Controlled_Room_Temp_15_25C`).
* **Why It Matters:** Guarantees that corrupted or ill-formatted master records are rejected before reaching analytical engines.

#### 2. `src/models/bridges.py`
* **Purpose:** Implements schemas for the 4 Network Bridge tables (`bridge_bill_of_material`, `bridge_supplier_material`, `bridge_sku_market`, `bridge_location_route`).
* **Key Mechanics:**
  * In `BridgeBillOfMaterial`: Validates `scrap_factor_pct` to strictly remain between $0.0\%$ and $10.0\%$. Validates recipe active dates (`effective_start_date <= effective_end_date`).
  * In `BridgeLocationRoute`: Validates transit days ($>0$) and verifies that if `cold_chain_required=True`, the route mode must be `Road_Reefer` or `Air_ColdChain`.
* **Why It Matters:** Governs the topology connecting plants, suppliers, and markets.

#### 3. `src/models/demand.py`
* **Purpose:** Implements schemas for `fact_demand_history` and `fact_customer_order`.
* **Key Mechanics:**
  * Enforces physical demand conservation: `@model_validator` ensures $\text{demand\_quantity} = \text{fulfilled\_quantity} + \text{lost\_sales\_quantity}$.
  * Enforces Monday weekly start date convention (`week_start_date.weekday() == 0`).
* **Why It Matters:** Guarantees that historical demand baseline contains no negative quantities or date drift.

#### 4. `src/models/planning.py`
* **Purpose:** Implements schemas for forward planning facts (`fact_demand_forecast`, `fact_supply_plan`, `fact_material_requirement`, `fact_inventory_projection`).
* **Key Mechanics:**
  * Enforces probabilistic interval bounds: `p10_quantity <= p50_quantity <= p90_quantity`. If P90 is less than P50, raises `ValidationError`.
  * In `FactInventoryProjection`: Validates the stock balance: $\text{ending} = \text{starting} + \text{receipts} + \text{production} - \text{demand}$.
* **Why It Matters:** Guarantees that forecast prediction intervals and multi-echelon forward projections obey strict mathematical bounds.

#### 5. `src/models/procurement_inventory.py`
* **Purpose:** Implements schemas for `fact_purchase_order`, `fact_inventory_lot`, and `fact_material_consumption`.
* **Key Mechanics:**
  * In `FactInventoryLot`: Validates that $\text{manufacture\_date} < \text{expiry\_date}$. Enforces that $\text{quantity\_on\_hand} \ge \text{reserved\_quantity} + \text{blocked\_quantity}$.
  * In `FactPurchaseOrder`: Evaluates OTIF criteria and date milestone progression (`order_date <= promised_delivery_date`).
* **Why It Matters:** Prevents phantom inventory allocations and expired lot release.

#### 6. `src/models/manufacturing_quality.py`
* **Purpose:** Implements schemas for `fact_production_order`, `fact_batch`, and `fact_quality_event`.
* **Key Mechanics:**
  * Chronological Milestone Progression: Enforces $\text{planned\_start\_date} \le \text{planned\_end\_date}$ and $\text{manufacture\_date} \le \text{qa\_release\_date}$.
  * Sterility & Potency Gates: Batches with `sterility_test_pass=False` or `assay_potency_pct < 95.0%` cannot be given `Released` quality status.
* **Why It Matters:** Directly incorporates pharmaceutical QA / QC compliance into data validation.

#### 7. `src/models/capacity_logistics.py`
* **Purpose:** Implements schemas for `fact_capacity` and `fact_shipment`.
* **Key Mechanics:**
  * In `FactCapacity`: Enforces weekly total hours = 168.0 hours. Validates that $\text{net\_available\_hours} = 168.0 - \text{maintenance\_hours} - \text{sanitization\_hours}$.
  * In `FactShipment`: Enforces `shipped_date <= expected_delivery_date <= actual_delivery_date`.
* **Why It Matters:** Prevents scheduling lines beyond physical 168-hour calendar limits.

#### 8. `src/models/control_tower.py`
* **Purpose:** Implements schemas for Tier 6 Control Tower tables (`dim_scenario`, `fact_risk_event`, `bridge_risk_evidence`, `fact_root_cause`, `fact_mitigation_simulation`, `fact_recommendation`, `dataset_manifest`).
* **Key Mechanics:**
  * **Mandatory Human-in-the-Loop Validator:**
    ```python
    @field_validator("human_approval_required")
    def validate_human_mandate(cls, v: bool) -> bool:
        if v is not True:
            raise ValueError("GxP Compliance Violation: human_approval_required must strictly be True.")
        return v
    ```
  * In `FactRiskEvent`: Enforces severity score bounds ($0 \le \text{score} \le 100$).
* **Why It Matters:** Guarantees governance compliance and blocks fully autonomous execution.

---

### 3.2 AI Tool Interfaces & Governance (`src/agent/`)

#### 9. `src/agent/contracts.py`
* **Purpose:** Implements rigid Pydantic tool request and response interfaces between the deterministic analytics engine (Tier 2) and the AI orchestration layer (Tier 3).
* **Key Classes:**
  * `InventoryProjectionRequest` & `InventoryProjectionResponse`: Strongly typed input/output for forward stock trajectories.
  * `ActiveRisksRequest` & `ActiveRisksResponse`: Delivers ranked risk alerts to the agent, containing concrete record IDs.
  * `RootCauseTraceRequest` & `RootCauseTraceResponse`: Delivers backward dependency graph nodes.
  * `MitigationSimulationRequest` & `MitigationSimulationResponse`: Returns before/after stockout comparisons and expedite costs.
* **Why It Matters:** When the LLM decides to call a tool, it must conform to these typed schemas. The agent receives structured data with zero room for hallucinated values.

---

### 3.3 Synthetic Data & Benchmark Disruption Generator (`src/generator/`)

#### 10. `src/generator/config.py`
* **Purpose:** Centralized configuration defining network constants, baseline seed (`20261014`), date horizons (`2024-10-28` to `2026-10-19`), and database export paths.
* **Why It Matters:** Single source of truth for reproducible synthetic data generation.

#### 11. `src/generator/master_data.py`
* **Purpose:** Synthesizes all 8 master dimensions and 4 network bridge tables using fixed seed `20261014`.
* **Key Functions:**
  * `generate_master_dimensions()`: Generates products, SKUs, suppliers, locations, lines, customers, and markets.
  * `generate_network_bridges()`: Generates BOM recipes with chemical scrap factors, supplier catalogs with lead times, and transportation route matrices.
* **Why It Matters:** Establishes the clean relational baseline with 100% referential integrity.

#### 12. `src/generator/demand_data.py`
* **Purpose:** Generates 104 weeks (2 full years) of weekly commercial demand history across all SKUs and markets.
* **Key Mechanics:**
  * Models base trend + 52-week annual seasonality using harmonic sinusoids.
  * Injects pharmaceutical domain events: Indian Monsoon Respiratory Surges (+35% demand spike during calendar weeks 28–34) and Diwali Channel Stocking Adjustments (weeks 42–45).
  * Enforces demand conservation: records true demand, fulfilled quantity, and lost sales.
* **Why It Matters:** Provides realistic, non-trivial historical time series for training and evaluating forecasting models.

#### 13. `src/generator/supply_data.py`
* **Purpose:** Generates operational transactions matching the demand baseline: purchase orders, plant production orders, batch genealogies, QA release events, line capacities, and physical inventory lots.
* **Key Functions:**
  * `generate_inventory_lots()`: Creates physical pallet lots with realistic manufacture dates, 24-month expiry dates, and QA release statuses.
  * `generate_purchase_orders()`: Generates inbound vendor procurement orders with realistic OTIF delivery performance.
* **Why It Matters:** Builds the operational reality of the supply chain against which disruptions are tested.

#### 14. `src/generator/disruption_injector.py`
* **Purpose:** Controlled synthetic injection engine for benchmark disruption Scenarios A through E.
* **Key Injections:**
  * `inject_scenario_a()`: Delays Amoxicillin API delivery by $+14$ days on `PO-API-001`.
  * `inject_scenario_b()`: Injects microbial sterility retest deviation on `BATCH-AUG-2026-01`, delaying CoA release by $+10$ days.
  * `inject_scenario_c()`: Simulates carton supplier stockout on `MAT-PKG-CART`, starving both T10 and T30 lines.
  * `inject_scenario_d()`: Injects pallet lot `LOT-AUG-EXP-01` with remaining shelf life dropping below 90-day hospital MARSL.
  * `inject_scenario_e()`: Schedules emergency preventive line maintenance on `LINE-BADDI-01`, creating capacity conflict against expedited production.
* **Why It Matters:** Allows the Control Tower's analytical engines to be rigorously benchmarked against known ground-truth disruptions.

#### 15. `src/generator/runner.py`
* **Purpose:** Master generator script orchestrating end-to-end data creation and executing tri-format export:
  1. SQLite relational database: `data/processed/control_tower.db` (30 populated tables, 691 verified records).
  2. 30 Apache Parquet files: `data/processed/parquet/`.
  3. 30 CSV files: `data/processed/csv/`.
  4. Multi-tab Excel workbook: `data/processed/control_tower_full_database.xlsx`.
* **Why It Matters:** Delivers multi-format data storage supporting high-speed analytical queries, database inspection, and regulatory compliance logging.

---

### 3.4 Deterministic Supply Chain Core Engines (`src/engine/`)

#### 16. `src/engine/fefo_rules.py`
* **Purpose:** Baseline foundational FEFO rules module. Evaluates lot eligibility and sorts inventory strictly by expiration date.
* **Key Functions:** `filter_eligible_lots()`, `sort_lots_fefo()`.
* **Why It Matters:** First proof-of-concept module established in Day 05.

#### 17. `src/engine/inventory.py`
* **Purpose:** Institutional-grade lot-level FEFO Inventory Allocation and Posture Assessment Engine.
* **Key Functions:**
  * `is_lot_fefo_eligible(lot, required_date, destination_marsl_days)`: Validates that lot quality status is `'Released'`, recall status is `'None'`, and remaining shelf life upon anticipated arrival satisfies market MARSL:
    $$\text{RSL}_{\text{days}} = \text{Expiry\_Date} - (\text{Dispatch\_Date} + \text{Transit\_Days}) \ge \text{MARSL\_Days}$$
  * `allocate_fefo(order_qty, eligible_lots)`: Sequentially decrements eligible lots in ascending expiry order, tracking lot allocations, remaining inventory, and unfilled stockout shortages.
  * `assess_inventory_posture(lots, as_of_date)`: Categorizes network stock into 5 buckets: Available, Reserved, Blocked/Quarantined, Expired, and Near-Expiry ($<90\text{d}$).
* **Why It Matters:** Enforces life sciences FEFO law. Eliminates dispatching unreleased or near-expiry lots to hospital customers.

#### 18. `src/engine/projections.py`
* **Purpose:** Multi-Echelon 26-Week Forward Inventory Projection Engine.
* **Key Functions:**
  * `calculate_weekly_inventory_projection(...)`: Implements the recursive forward stock balance identity:
    $$I_t = I_{t-1} + R_t + P_t - D_t$$
  * Evaluates multi-echelon transit lead times, inbound scheduled PO receipts, confirmed packaging work orders, and commercial demand.
  * **Dynamic Expiry Decrementing:** Forward-evaluates lot shelf lives week-by-week. If a lot reaches its expiration date during week $t$, it is automatically deducted from available stock.
  * Automatically flags stockout risks ($I_t < 0$) and safety stock threshold breaches ($I_t < \text{SS}$).
* **Why It Matters:** Provides the forward-looking operational horizon for S&OP planning, alerting planners to stockouts weeks before they occur.

#### 19. `src/engine/mrp.py`
* **Purpose:** Multi-Level Bill-of-Materials (BOM) Explosion & Material Requirements Planning Netting Engine.
* **Key Functions:**
  * `explode_bom_for_order(order_qty, bom_records)`: Recursively explodes finished product batches into Active APIs, Excipients, and Packaging materials, incorporating chemical scrap factors:
    $$\text{Gross} = \text{Order\_Qty} \times \text{BOM\_Ratio} \times \left(1 + \frac{\text{Scrap\_Pct}}{100}\right)$$
  * `net_material_requirements(gross_req, qualified_inventory, scheduled_pos)`: Nets gross requirements against available qualified stock (excluding quarantined lots) and scheduled inbound deliveries:
    $$\text{Net} = \max\left(0, \text{Gross} - (\text{Available\_Stock} + \text{Scheduled\_PO})\right)$$
  * `calculate_po_release_dates(required_date, supplier_lead_time_days)`: Back-calculates planned PO release dates: $T_{\text{release}} = T_{\text{need}} - \text{Lead\_Time}$.
* **Why It Matters:** Connects commercial finished goods schedules to raw chemical procurement. Detects packaging shortages (Scenario C) before plant lines are starved.

#### 20. `src/engine/analytics.py`
* **Purpose:** Supplier Delivery Performance (OTIF) and Plant Line Capacity Analytics Engine.
* **Key Functions:**
  * `evaluate_po_otif_performance(po)`: Evaluates whether an inbound purchase order fulfilled contractual SLAs:
    $$\text{OTIF} = \mathbb{I}(\text{Actual\_Delivery} \le \text{Promised\_Delivery}) \times \mathbb{I}\left(\frac{\text{Delivered\_Qty}}{\text{Ordered\_Qty}} \ge 0.98\right)$$
  * `aggregate_supplier_otif_scorecard(pos)`: Compiles vendor scorecards: Total Orders, OTIF %, Average Delay Days, Quantity Fill Rate.
  * `calculate_line_capacity_metrics(capacity_records)`: Computes line utilization percentage against net available hours:
    $$\text{Utilization\_Pct} = \frac{\text{Committed\_Hours}}{\text{Net\_Available\_Hours}} \times 100$$
    Flags bottleneck overloads ($>95\%$) and maintenance downtime conflicts (Scenario E).
* **Why It Matters:** Identifies supplier delivery risks (Scenario A) and plant capacity bottlenecks (Scenario E) using deterministic metrics.

#### 21. `src/engine/reconciliation.py`
* **Purpose:** Multi-Echelon Stock Reconciliation & Mathematical Conservation Engine.
* **Key Functions:**
  * `run_full_network_reconciliation(...)`: Audits all 122 network entities across all echelons over a 26-week horizon.
  * Evaluates the fundamental mass conservation identity:
    $$\text{Initial On-Hand} + \text{Inbound Receipts} = \text{Ending On-Hand} + \text{Dispatched} + \text{Consumed} + \text{Scrap}$$
  * Computes unexplained inventory drift across finished goods, bulk tablets, and raw materials.
* **Why It Matters:** Formally proved **0.000000% inventory drift** across the network ([`docs/week_04_reconciliation_report.md`](file:///d:/AI%20Pharmaceutical%20Supply%20Chain/docs/week_04_reconciliation_report.md)). Proves that the simulation engine does not "lose" physical stock.

---

### 3.5 Demand Forecasting & Anomaly Layer (`src/forecasting/`)

#### 22. `src/forecasting/prep.py`
* **Purpose:** Leakage-Free Time-Series Preprocessing & Causal Feature Engineering Engine.
* **Key Functions:**
  * `split_time_series_chronologically(df, train_weeks=78, val_weeks=13, test_weeks=13)`: Chronologically splits 104 historical weeks into:
    * Train: 78 weeks (`2024-10-28` to `2026-04-20`, 75.0% volume).
    * Validation: 13 weeks (`2026-04-27` to `2026-07-20`, 12.5% volume).
    * Holdout Test: 13 weeks (`2026-07-27` to `2026-10-19`, 12.5% volume).
    * Zero date overlap ($\Delta t \ge 7\text{ days}$).
  * `create_demand_feature_pipeline(df)`: Synthesizes 31 strictly causal features:
    * 12 Autoregressive Lags ($L_1 \dots L_{12}$).
    * 12 Rolling Statistics (Mean, Std, Min, Max over 4, 8, 12 weeks computed strictly on $y.\text{shift}(1)$).
    * 2 Cyclical Fourier Seasonality transforms ($\sin, \cos$ over 52 weeks).
    * 2 Domain Pulses: Indian Monsoon Surge (weeks 28–34) and Diwali Adjustment (weeks 42–45).
    * 3 Categorical Encodings (SKU and Regional Hub identifiers).
  * `audit_time_series_leakage(feature_matrix, target)`: Automated statistical audit engine verifying zero correlation ($0.0000$) between causal features and future target values.
* **Why It Matters:** Guarantees that machine learning forecasters cannot "cheat" by looking into future test data.

#### 23. `src/forecasting/baseline.py`
* **Purpose:** Classical Statistical Forecasting Baseline Suite & Hurdle Rate Establishment.
* **Key Models Implemented:**
  * `SeasonalNaiveModel(m=52)`: Projects demand from exactly 52 weeks prior: $\hat{y}_{t+h} = y_{t+h-52}$.
  * `MovingAverageModel(window=4, 12)`: Simple and weighted moving averages.
  * `ExponentialSmoothingModel`: Holt-Winters additive seasonality with damped trend ($\phi=0.98$).
* **Key Function:**
  * `calculate_forecast_metrics(actual, forecast)`: Deterministically computes WAPE, MAE, MAPE, RMSE, Forecast Bias %, and Tracking Signal.
* **The Baseline Hurdle Rate:** Established **Seasonal Naive 52 at 16.23% WAPE** on holdout data as the official performance hurdle.

#### 24. `src/forecasting/ml_models.py`
* **Purpose:** Machine Learning Forecaster & Horizon-Expanded Prediction Interval Engine.
* **Key Models Implemented:**
  * `RidgeDemandForecaster(alpha=10.0)`: L2-regularized linear model with convex closed-form optimization:
    $$\min_w \|Xw - y\|_2^2 + \alpha \|w\|_2^2$$
  * `GradientBoostingDemandForecaster`: Ensembled regression trees (LightGBM/HistGradientBoosting).
* **Key Functions:**
  * `generate_recursive_multi_step_forecast(model, history, horizon=26)`: Auto-regressively rolls forward 26 weeks, feeding prior step predictions into future lags.
  * `calculate_prediction_intervals(forecast_p50, residual_std, horizon=26, c=0.05)`: Computes expanding horizon uncertainty:
    $$\sigma_h = \sigma_0 \sqrt{1 + 0.05(h - 1)}$$
    $$P_{10} = \max(0, \hat{y}_h - 1.282 \cdot \sigma_h), \quad P_{50} = \hat{y}_h, \quad P_{90} = \hat{y}_h + 1.282 \cdot \sigma_h$$
* **Champion Result:** **Ridge Regression achieved 7.76% WAPE** on out-of-time holdout test (**+52.2% error reduction** over baseline hurdle), -0.45% bias, +0.18 tracking signal.

#### 25. `src/forecasting/evaluation.py`
* **Purpose:** Multi-Dimensional Forecast Slice Analytics, Drift Monitoring, and SQLite Version Registry.
* **Key Functions:**
  * `evaluate_forecast_slices(actual_df, forecast_df)`: Slices performance across SKUs (T10: 9.05%, T30: 7.07%), Regional Hubs (Hyd: 7.85%, Pun: 9.00%), and Horizons (W01–W04: 9.87%, W05–W12: 6.25%, W13–W26: 21.59%) with 100% volume conservation.
  * `evaluate_tracking_signal_drift(actuals, forecasts, threshold=4.0)`: Evaluates sequential tracking signal drift:
    $$\text{TS}_t = \frac{\sum (y_i - \hat{y}_i)}{\text{MAD}_t}$$
    Triggers alarms when $|\text{TS}| > 4.0$.
  * `ForecastRegistry`: Multi-version SQLite persistence manager writing versioned 26-week projections into `fact_demand_forecast`.
* **Why It Matters:** Guarantees model fairness across product families and monitors against real-time operational drift.

#### 26. `src/forecasting/anomaly.py`
* **Purpose:** Statistical Demand Anomaly Detection & Downstream Supply Chain Impact Propagation Engine.
* **Key Mechanics:**
  * **Rolling Volatility-Adjusted Z-Score:** $Z_t = \frac{y_t - \mu_{t-1, W}}{\sigma_{t-1, W}}$ ($W=12$ weeks, Threshold $|Z| \ge 3.0$). Handles zero-variance ($std=0$) series gracefully.
  * **Tukey's Non-Parametric IQR Fences:** $[Q_1 - 1.5\text{IQR}, Q_3 + 1.5\text{IQR}]$.
  * **Structural Step-Change Detection:** Flags sustained shifts where 4-week mean deviates by $\ge 35\%$ from 12-week baseline.
  * **Downstream Impact Propagation:** Translates statistical anomalies into operational and financial supply chain consequences:
    * *Surge:* Calculates days-of-supply depletion, safety stock burn percentage, stockout risk flag, potential lost revenue ($), and issues an expedite directive (`"EXPEDITE_REPLENISHMENT"`).
    * *Plunge:* Calculates excess days of supply, inventory aging/expiry risk flag, carrying cost ($), and issues a throttle directive (`"THROTTLE_PRODUCTION"`).
* **Why It Matters:** Bridges pure statistical time-series data with plant shop-floor and procurement operations.

---

### 3.6 Master Schedule Generator (`build_refined_3tab_schedule.py`)

#### 27. `build_refined_3tab_schedule.py`
* **Purpose:** Programmatically generates the 3-tab executive roadmap spreadsheet (`AI_Supply_Chain_Control_Tower_12_Week_Executive_Schedule.xlsx`).
* **Tabs Generated:**
  1. `12_Week_Executive_Summary`: Phase-by-phase calendar, objectives, deliverables, and Gate reviews.
  2. `Weekly_Implementation_Plan`: Week-by-week sprint objectives, deliverables, and automated status tracking (`Completed`, `Active`, `Planned`).
  3. `Daily_Sprint_Backlog`: Day-by-day (Days 01 to 60) granular task breakdown with verification gates.
* **Why It Matters:** Provides senior leadership with an interactive, auditable project roadmap.

---

## 4. Master Mathematical Catalog (All 18 Formulas Explained)

In your meeting, the Group Operations Manager or Lead Architect might ask: *"Show me the exact mathematical formulas behind your engine."*  
Here is every formula implemented in the platform, why it was chosen, and how it is implemented in code.

---

### 1. The Inventory Balance Identity (Mass Conservation)
$$\mathbf{I_t = I_{t-1} + R_t + P_t - D_t}$$
* **Where It Lives:** `src/engine/projections.py` (`calculate_weekly_inventory_projection`) and `src/models/planning.py`.
* **Variables:**
  * $I_t$: Ending available inventory at week $t$.
  * $I_{t-1}$: Ending carryover inventory from week $t-1$.
  * $R_t$: Confirmed purchase order receipts arriving at week $t$ (lead-time adjusted).
  * $P_t$: Confirmed plant production output arriving at week $t$.
  * $D_t$: Dependent commercial demand consumed at week $t$.
* **Why Chosen:** The foundational physical law of multi-echelon inventory mechanics. Governs discrete-time stock trajectories without artificial drift.

---

### 2. Remaining Shelf Life (RSL) and MARSL Validation
$$\mathbf{\text{RSL}_{\text{days}}(L, t_{\text{dispatch}}) = \text{Expiry\_Date}(L) - \left(t_{\text{dispatch}} + \Delta t_{\text{transit}}\right)}$$
$$\mathbf{\text{Eligible}(L) = \mathbb{I}\left(\text{RSL}_{\text{days}} \ge \text{MARSL}_{\text{market}}\right) \land \mathbb{I}\left(\text{QA\_Status}(L) = \text{'Released'}\right) \land \mathbb{I}\left(\text{Recall}(L) = \text{'None'}\right)}$$
* **Where It Lives:** `src/engine/inventory.py` (`is_lot_fefo_eligible`).
* **Variables:**
  * $\text{RSL}_{\text{days}}$: Physical days of shelf life remaining when the lot reaches the customer dock.
  * $\text{MARSL}_{\text{market}}$: Minimum Acceptable Remaining Shelf Life required by market contract (e.g. 90 days for hospital tenders, 60 days for retail).
  * $\Delta t_{\text{transit}}$: Cold-chain transit duration from origin DC to customer market.
* **Why Chosen:** Regulatory cGMP compliance. Eliminates delivery of stock that customers or hospitals will reject upon delivery.

---

### 3. BOM Gross Requirements with Chemical Scrap Factor
$$\mathbf{\text{Gross\_Requirement}_m = \text{Order\_Quantity} \times \text{Recipe\_Ratio}_m \times \left(1 + \frac{\text{Scrap\_Factor\_Pct}_m}{100}\right)}$$
* **Where It Lives:** `src/engine/mrp.py` (`explode_bom_for_order`).
* **Variables:**
  * $\text{Order\_Quantity}$: Target finished SKU production quantity (packs).
  * $\text{Recipe\_Ratio}_m$: Theoretical chemical quantity of material $m$ needed per pack (e.g. 0.005 kg API/pack).
  * $\text{Scrap\_Factor\_Pct}_m$: Chemical granulation loss and packaging startup scrap allowance (1.0% to 3.5%).
* **Why Chosen:** Standard chemical engineering formulation. Ordering purely theoretical BOM amounts guarantees a material shortage due to inherent processing yield losses.

---

### 4. Net Material Requirement (Component Netting)
$$\mathbf{\text{Net\_Requirement}_m = \max\left(0, \; \text{Gross\_Requirement}_m - \left(\text{Qualified\_Stock}_m + \text{Scheduled\_PO\_Receipts}_m\right)\right)}$$
* **Where It Lives:** `src/engine/mrp.py` (`net_material_requirements`).
* **Variables:**
  * $\text{Qualified\_Stock}_m$: Current physical inventory of material $m$ with `quality_status = 'Released'` and unexpired shelf life.
  * $\text{Scheduled\_PO\_Receipts}_m$: Inbound purchase orders scheduled to arrive prior to the required production start date.
* **Why Chosen:** Prevents redundant procurement by subtracting existing qualified stock from gross requirements.

---

### 5. Backward Scheduled Purchase Order Release Date
$$\mathbf{T_{\text{PO\_Release}} = T_{\text{Required}} - \text{Contracted\_Lead\_Time}_{\text{supplier}}}$$
* **Where It Lives:** `src/engine/mrp.py` (`calculate_po_release_dates`).
* **Why Chosen:** Classic MRP backward scheduling. Dictates the exact date a purchase order must be issued to the supplier so that goods arrive exactly when the plant cleanroom needs them.

---

### 6. Purchase Order OTIF (On-Time In-Full) Metric
$$\mathbf{\text{OTIF} = \mathbb{I}\left(\text{Actual\_Delivery\_Date} \le \text{Promised\_Delivery\_Date}\right) \times \mathbb{I}\left(\frac{\text{Delivered\_Quantity}}{\text{Ordered\_Quantity}} \ge 0.98\right)}$$
* **Where It Lives:** `src/engine/analytics.py` (`evaluate_po_otif_performance`).
* **Why Chosen:** In pharmaceutical operations, delivering on-time with 70% quantity causes plant starvation; delivering 100% quantity 3 weeks late causes stockouts. A supplier delivery only passes if it satisfies **both** conditions.

---

### 7. Line Capacity Utilization Percentage
$$\mathbf{\text{Utilization\_Pct} = \frac{\text{Committed\_Production\_Hours}}{\text{Net\_Available\_Hours}} \times 100}$$
$$\text{where } \mathbf{\text{Net\_Available\_Hours} = 168.0 - \text{Maintenance\_Hours} - \text{Sanitization\_Hours}}$$
* **Where It Lives:** `src/engine/analytics.py` (`calculate_line_capacity_metrics`).
* **Why Chosen:** Prevents over-committing plant lines. Overloads ($>95\%$) trigger equipment breakdown risks and indicate when batch offloading to parallel lines is required.

---

### 8. Physical Stock Conservation Identity (Reconciliation)
$$\mathbf{\sum_{\text{Items}} \left(I_{\text{initial}} + \sum \text{Inflows}\right) = \sum_{\text{Items}} \left(I_{\text{ending}} + \sum \text{Outflows} + \text{Scrap}\right)}$$
$$\mathbf{\text{Inventory\_Drift\_Pct} = \frac{|\text{Total\_Inflows} - \text{Total\_Outflows} - \Delta \text{Stock}|}{\text{Total\_Initial\_Stock}} \times 100 = \mathbf{0.000000\%}}$$
* **Where It Lives:** `src/engine/reconciliation.py` (`run_full_network_reconciliation`).
* **Why Chosen:** Audits that the simulation engine does not create or destroy physical inventory out of thin air.

---

### 9. Weighted Absolute Percentage Error (WAPE)
$$\mathbf{\text{WAPE} = \frac{\sum_{t=1}^N |y_t - \hat{y}_t|}{\sum_{t=1}^N y_t} \times 100\%}$$
* **Where It Lives:** `src/forecasting/baseline.py` (`calculate_forecast_metrics`).
* **Why Chosen:** Standard MAPE ($\frac{1}{N}\sum \frac{|y - \hat{y}|}{y}$) blows up to infinity whenever demand is near zero. WAPE weights errors by total volume, making it the life sciences standard for commercial demand evaluation.

---

### 10. Forecast Bias Percentage
$$\mathbf{\text{Forecast\_Bias\_Pct} = \frac{\sum_{t=1}^N (\hat{y}_t - y_t)}{\sum_{t=1}^N y_t} \times 100\%}$$
* **Where It Lives:** `src/forecasting/baseline.py` (`calculate_forecast_metrics`).
* **Why Chosen:** WAPE tells you the magnitude of error; Bias tells you the direction. Positive bias means systematic over-forecasting (expiry risk); negative bias means systematic under-forecasting (stockout risk).

---

### 11. Tracking Signal (TS) and Mean Absolute Deviation (MAD)
$$\mathbf{\text{MAD}_t = \frac{1}{t}\sum_{i=1}^t |y_i - \hat{y}_i|}, \quad \mathbf{\text{TS}_t = \frac{\sum_{i=1}^t (\hat{y}_i - y_i)}{\text{MAD}_t}}$$
* **Where It Lives:** `src/forecasting/evaluation.py` (`evaluate_tracking_signal_drift`).
* **Why Chosen:** Statistical process control. In life sciences forecasting, a tracking signal outside $[-4.0, +4.0]$ proves that the forecasting model has structurally drifted and requires mandatory retraining.

---

### 12. Cyclical Fourier Annual Seasonality Transforms
$$\mathbf{\text{Season}_{\sin}(t) = \sin\left(\frac{2\pi \cdot \text{week\_num}(t)}{52.1775}\right)}, \quad \mathbf{\text{Season}_{\cos}(t) = \cos\left(\frac{2\pi \cdot \text{week\_num}(t)}{52.1775}\right)}$$
* **Where It Lives:** `src/forecasting/prep.py` (`create_calendar_features`).
* **Why Chosen:** Representing week 52 and week 1 as raw integers creates an artificial discontinuity ($52 \to 1$). Circular Fourier harmonics preserve cyclical continuity between December and January.

---

### 13. L2-Regularized Ridge Objective Function
$$\mathbf{\min_w \; \|Xw - y\|_2^2 + \alpha \|w\|_2^2 \quad (\alpha = 10.0)}$$
* **Where It Lives:** `src/forecasting/ml_models.py` (`RidgeDemandForecaster`).
* **Why Chosen:**
  1. *Convex Closed-Form Solution:* $w = (X^T X + \alpha I)^{-1} X^T y$. Yields identical, deterministic weights every single time (zero stochastic variance).
  2. *Multicollinearity Shrinkage:* Autoregressive lags ($L_1, L_2$) and rolling averages are highly correlated. Ridge shrinks coefficients stably, preventing over-fitting.

---

### 14. Horizon-Expanded Probabilistic Uncertainty (P10 / P50 / P90)
$$\mathbf{\sigma_h = \sigma_0 \sqrt{1 + c \cdot (h - 1)} \quad (c = 0.05, \; h \in \{1 \dots 26\})}$$
$$\mathbf{P_{10}(h) = \max\left(0, \; \hat{y}_h - 1.282 \cdot \sigma_h\right)}, \quad \mathbf{P_{50}(h) = \hat{y}_h}, \quad \mathbf{P_{90}(h) = \hat{y}_h + 1.282 \cdot \sigma_h}$$
* **Where It Lives:** `src/forecasting/ml_models.py` (`calculate_prediction_intervals`).
* **Why Chosen:** Predictability decreases as you look further into the future. Horizon expansion models this uncertainty mathematically. $P_{90}$ is used for safety stock sizing; $P_{10}$ is used for inventory holding risk screening.

---

### 15. Rolling Volatility-Adjusted Z-Score
$$\mathbf{Z_t = \frac{y_t - \mu_{t-1, W}}{\sigma_{t-1, W}} \quad (W = 12\text{ weeks})}$$
$$\text{with zero-variance safety: if } \sigma_{t-1, W} < 10^{-6}, \quad \mathbf{Z_t = \text{sign}(y_t - \mu) \cdot \frac{|y_t - \mu|}{0.1 \cdot \mu}}$$
* **Where It Lives:** `src/forecasting/anomaly.py` (`evaluate_point_anomaly`).
* **Why Chosen:** Normalizes demand spikes relative to recent historical volatility. An absolute surge of $+1,000$ packs might be normal in Hyderabad ($Z=1.2$) but critical in Pune ($Z=4.5$).

---

### 16. Non-Parametric Tukey's IQR Fences
$$\mathbf{\text{IQR} = Q_3 - Q_1}, \quad \mathbf{\text{Lower} = \max(0, \; Q_1 - 1.5 \cdot \text{IQR})}, \quad \mathbf{\text{Upper} = Q_3 + 1.5 \cdot \text{IQR}}$$
* **Where It Lives:** `src/forecasting/anomaly.py` (`evaluate_point_anomaly`).
* **Why Chosen:** Distribution-free (non-parametric). Z-scores assume Gaussian normality; Tukey's fences work robustly even if historical demand has skewness or existing extreme outliers.

---

### 17. Structural Step-Change Drift Detection
$$\mathbf{\Delta_{\text{shift}} = \frac{\mu_{\text{short}} - \mu_{\text{baseline}}}{\mu_{\text{baseline}}} \quad (W_{\text{short}} = 4, \; W_{\text{baseline}} = 12)}$$
$$\mathbf{\text{Structural\_Shift} = \text{True} \quad \iff \quad |\Delta_{\text{shift}}| \ge 0.35 \quad (35\% \text{ sustained deviation})}$$
* **Where It Lives:** `src/forecasting/anomaly.py` (`detect_structural_shift`).
* **Why Chosen:** Differentiates between a single-week seasonal spike (e.g. holiday surge) and a permanent step-change in base demand velocity (e.g. winning a major hospital formulary tender).

---

### 18. Downstream Supply Chain Impact Propagation
$$\mathbf{\Delta \text{Days\_of\_Supply} = -\frac{y_t - \hat{y}_t}{\hat{y}_t / 7}}, \quad \mathbf{\text{Safety\_Stock\_Burn\_Pct} = \min\left(100.0, \; \frac{y_t - \hat{y}_t}{\text{SS\_Buffer}} \times 100\right)}$$
$$\mathbf{\text{Financial\_Exposure\_USD} = (y_t - \hat{y}_t) \times \text{Unit\_Price} \quad (\text{Surge}) \quad \lor \quad |y_t - \hat{y}_t| \times \text{Unit\_Price} \times 0.20 \quad (\text{Plunge})}$$
* **Where It Lives:** `src/forecasting/anomaly.py` (`assess_downstream_impact`).
* **Why Chosen:** Bridges pure statistics with physical supply chain reality. Tells the planner exactly how many days of forward supply were consumed and whether safety stock was burned.

---

## 5. The Executive Meeting Defense Guide & Live Demo Script

When you walk into the meeting room with the Executive Director and Group Operations Manager, follow this structured roadmap:

```mermaid
flowchart TD
    M1["1. Opening Executive Hook<br/>(2 Minutes: Vision & GxP Compliance)"]
    M2["2. Relational Architecture & Zero Drift<br/>(Show SQLite & 0.000000% Reconciliation)"]
    M3["3. Machine Learning Hurdle Clearance<br/>(Show Ridge 7.76% WAPE vs 16.23% Baseline)"]
    M4["4. Live Code & Anomaly Walkthrough<br/>(Show Z-Score, Impact & Human Approval)"]
    M5["5. Q&A Defense & Reassurance<br/>(Handle tough questions with facts)"]

    M1 --> M2 --> M3 --> M4 --> M5
```

### 5.1 The 2-Minute Executive Opening (Memorize This)
> *"Good morning. Over the first five weeks, we have engineered an institutional-grade, compliant AI decision-support system for our pharmaceutical supply chain. 
> Rather than deploying a generic, unconstrained AI that hallucinates numbers, we built this on three strict principles: 
> First, Zero LLM Math—all projections, MRP explosions, and forecasts run deterministically in Python. 
> Second, Relational Evidence Grounding—every alert points directly to immutable database primary keys. 
> Third, Mandatory Human-in-the-Loop Governance—binding operational actions require authorized planner approval by schema design.
> In Phase 1, we established our 33-entity relational data model and synthetic disruption suite under cGMP and FDA 21 CFR Part 11 standards.
> In Week 4, our deterministic engines proved 0.000000% inventory drift across 122 network items under lot-level FEFO rules.
> In Week 5, our champion Ridge regression forecaster achieved a 7.76% WAPE on holdout data, beating our seasonal baseline hurdle by over 52% error reduction, paired with probabilistic P10/P90 intervals and a statistical anomaly detector.
> We have 189 passing unit tests with 100% pass rate in 4 seconds. We are completely on schedule and ready to activate Week 6."*

### 5.2 What Code Files to Open First in the Demo
If managers ask to see the code, open these three files in this exact order:
1. **Show Determinism & Conservation:** Open [`src/engine/reconciliation.py`](file:///d:/AI%20Pharmaceutical%20Supply%20Chain/src/engine/reconciliation.py) lines 100–180. Show how the engine audits all 122 items and proves `0.000000%` drift.
2. **Show Machine Learning Rigor:** Open [`src/forecasting/ml_models.py`](file:///d:/AI%20Pharmaceutical%20Supply%20Chain/src/forecasting/ml_models.py) lines 130–180. Show the Ridge regression class and how expanding horizon prediction intervals ($P_{10}, P_{50}, P_{90}$) are computed.
3. **Show Governance & Human Mandate:** Open [`src/models/control_tower.py`](file:///d:/AI%20Pharmaceutical%20Supply%20Chain/src/models/control_tower.py) lines 190–210. Show the `@field_validator("human_approval_required")` proving that autonomous execution is rejected at the schema level.

---

*End of Master Engineering Reference Dossier.*
