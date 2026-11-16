# Forecast Evaluation, Slice Analytics & Versioning Registry Specification

**Document Identifier:** `DOC-SPEC-FORECAST-EVAL-001`  
**Phase:** Phase 2 — Deterministic Analytics & Core Engines (Weeks 04–07)  
**Deliverable:** Day 23 (Thursday, 26-Nov-2026) — Forecast Evaluation & Versioning Engine  
**Target Module:** `src/forecasting/evaluation.py`  
**Test Suite:** `tests/test_forecasting_evaluation.py` (12 / 12 Passing, 178 Total Repository Tests)  
**Status:** **APPROVED & FULLY VALIDATED**  

---

## 1. Executive Summary & Strategic Scope

In enterprise pharmaceutical supply chains, aggregate forecast error metrics (e.g. single-number WAPE) can obscure dangerous localized operational risks:
- An aggregate WAPE of 8% can hide a 25% under-forecast in an active clinical market or a major over-estimate during plant changeover weeks.
- Furthermore, forecasts are continuously updated across monthly and weekly Sales & Operations Planning (S&OP) cycles, requiring formal **version lineage, variance waterfall tracking, and automated drift alarming**.

**Day 23 implements the operational evaluation and governance backbone:**
1. **Multi-Horizon Slice-and-Dice Analytics:** Disaggregates forecast accuracy across Finished SKUs, Regional Markets, SKU $\times$ Market intersections, and three distinct planning horizons (Weeks 1–4, Weeks 5–12, Weeks 13–26).
2. **Automated Tracking Signal & Drift Monitor:** Continuously audits cumulative forecast error against Mean Absolute Deviation ($MAD$), triggering automated statistical drift alarms when $|TS| > 4.0$.
3. **Version-to-Version Waterfall Variance Analysis:** Reconciles forecast revisions between successive planning cycles, identifying material shifts ($>20\%$ or $>1,000$ packs) that impact master production schedules.
4. **SQLite Multi-Version Forecast Registry:** Provides clean, idempotent persistence into `fact_demand_forecast` with version tagging and rollback capability.

---

## 2. Multi-Horizon Slice-and-Dice Dimensional Analysis

The engine evaluates paired actuals and forecasts across four operational dimensions, enforcing strict mathematical volume conservation ($\sum \text{Slice Volumes} \equiv \text{Total Network Volume}$):

```
+-----------------------------------------------------------------------------------+
|                     MULTI-DIMENSIONAL SLICE-AND-DICE HIERARCHY                     |
+-----------------------------------------------------------------------------------+
|                                                                                   |
|  [ Dimension 1: Product Family ] ----> SKU-AUG-500-T10 vs SKU-AUG-500-T30        |
|                                                                                   |
|  [ Dimension 2: Regional Market ] ---> Hyderabad (MKT-IN-HYD) vs Pune (MKT-IN-PUN) |
|                                                                                   |
|  [ Dimension 3: Planning Horizon ] --> Weeks 01-04 (Operational Lead Time)       |
|                                        Weeks 05-12 (Tactical S&OP Planning)       |
|                                        Weeks 13-26 (Strategic Capacity Planning) |
|                                                                                   |
|  [ Dimension 4: Intersections ] -----> SKU x Market (4 discrete local series)     |
|                                                                                   |
+-----------------------------------------------------------------------------------+
```

### Operational Meaning of Planning Horizon Slices:
1. **Operational Lead Time (Weeks 1–4):** Governs plant line packaging changeovers, immediate transport vehicle assignments, and warehouse picking buffer replenishment.
2. **Tactical Planning (Weeks 5–12):** Governs API procurement release, batch manufacturing work orders (`fact_production_order`), and regional hub transfers.
3. **Strategic Capacity (Weeks 13–26):** Governs raw material annual supplier contracts, plant line shift scheduling, and long-term safety stock recalibrations.

### Production Holdout Slice Breakdown (`Ridge_Regression`):
| Dimension | Slice Key | WAPE % | MAE (Packs) | Bias % | Actual Packs | Forecast Packs | Volume Delta |
|---|---|---|---|---|---|---|---|
| **SKU** | `SKU-AUG-500-T10` | 9.05% | 363.6 | -1.11% | 313,302 | 309,818 | -3,484 |
| **SKU** | `SKU-AUG-500-T30` | 7.07% | 146.6 | -0.02% | 161,805 | 161,773 | -32 |
| **Market** | `MKT-IN-HYD` | 7.85% | 260.0 | -1.42% | 258,204 | 254,533 | -3,671 |
| **Market** | `MKT-IN-PUN` | 9.00% | 250.2 | +0.07% | 216,903 | 217,058 | +155 |
| **Horizon** | `Weeks 01-04 (Lead Time)` | 9.87% | 355.3 | -6.96% | 172,731 | 160,717 | -12,014 |
| **Horizon** | `Weeks 05-12 (Tactical)` | 6.25% | 180.4 | +1.11% | 277,242 | 280,320 | +3,078 |
| **Horizon** | `Weeks 13-26 (Strategic)` | 21.59% | 452.1 | +21.57% | 25,134 | 30,554 | +5,420 |
| **Overall** | **Consolidated Network** | **8.38%** | **255.1** | **-0.74%** | **475,107** | **471,591** | **-3,516** |

---

## 3. Automated Tracking Signal & Statistical Drift Monitoring

Tracking Signal measures whether forecast errors are random noise or exhibit persistent directional bias:

### Mathematical Definition:
$$\text{Cumulative Error}_t = \sum_{i=1}^t (\hat{y}_i - y_i)$$
$$\text{MAD}_t = \frac{1}{t} \sum_{i=1}^t |\hat{y}_i - y_i|$$
$$\text{Tracking Signal}_t = \frac{\text{Cumulative Error}_t}{\text{MAD}_t}$$

### Statistical Control Thresholds:
```
           STATISTICAL CONTROL CHART (TRACKING SIGNAL)
   TS
  +6.0 |-------------------------------------------------  UPPER ALARM (+4.0)
       |               /----------------- WARNING (+3.0)
  +3.0 |              /
   0.0 | -----------/-\--------/-\-----------------------  CENTERED (0.0)
  -3.0 |                 \----/   \------ WARNING (-3.0)
  -6.0 |-------------------------------------------------  LOWER ALARM (-4.0)
       +-------------------------------------------------> Time (Weeks)
```

- **$|\text{TS}| \le 3.0$ (`NORMAL`):** Statistically centered; errors fluctuate randomly around zero.
- **$3.0 < |\text{TS}| \le 4.0$ (`WARNING`):** Emerging directional drift; triggers planner review notification.
- **$|\text{TS}| > 4.0$ (`ALARM`):** Statistically significant persistent bias. Triggers automated recalibration recommendation:
  - If $\text{TS} > +4.0$: `PERSISTENT_OVERFORECAST` $\to$ excess working capital / expiry hazard.
  - If $\text{TS} < -4.0$: `PERSISTENT_UNDERFORECAST` $\to$ stockout / unmet patient demand hazard.

---

## 4. Version-to-Version Forecast Variance Analysis

To maintain manufacturing stability, the engine tracks forecast volatility between successive versions (e.g. `ML_Ridge_V1` vs `Baseline_SNaive_V1`):
$$\Delta \text{Packs} = \hat{y}_{\text{comparison}} - \hat{y}_{\text{base}}$$
$$\% \Delta = \frac{\Delta \text{Packs}}{\max(1.0, \hat{y}_{\text{base}})} \times 100\%$$

### Material Disruption Gate:
A point is flagged as a **Material Planning Shift** if:
$$|\% \Delta| > 20.0\% \quad \lor \quad |\Delta \text{Packs}| > 1,000 \text{ packs}$$
If more than 25% of points exhibit material shifts, the report triggers a **Critical Volatility Warning**, alerting supply planners to evaluate raw material component netting before releasing revised production schedules.

---

## 5. Multi-Version Forecast Registry (`ForecastRegistry`)

Provides structured, transaction-safe database persistence into SQLite `fact_demand_forecast`:
- **Lineage Tracking:** Discovers distinct forecast versions, version creation dates, and horizon spans.
- **Idempotent Updates:** `save_forecast_version(df, overwrite=True)` replaces prior forecasts for the given `model_version` and `scenario_id` without duplicate key inflation.
- **Selective Retrieval:** `load_forecast_version(model_version, scenario_id)` loads versioned tables for downstream MRP explosion and simulation.

---

## 6. Automated Unit Test Verification (`tests/test_forecasting_evaluation.py`)

All 12 unit tests pass in 2.38 seconds:

| Test Name | Verified Property | Status |
|---|---|---|
| `test_evaluate_forecast_slices_overall_and_dimensions` | Computes metrics across SKU, Market, Horizon, and Intersection slices | **PASSED** |
| `test_evaluate_forecast_slices_volume_conservation` | $\sum \text{Slice Volumes} \equiv \text{Total Network Volume}$ | **PASSED** |
| `test_evaluate_forecast_slices_horizon_boundaries` | Correctly partitions W01-W04, W05-W12, and W13-W26 buckets | **PASSED** |
| `test_tracking_signal_centered_normal_severity` | Balanced random noise maintains $|TS| \le 1.0$ and severity `NORMAL` | **PASSED** |
| `test_tracking_signal_positive_drift_alarm` | Persistent over-forecasting triggers `ALARM` with TS $> 4.0$ | **PASSED** |
| `test_tracking_signal_negative_drift_alarm` | Persistent under-forecasting triggers `ALARM` with TS $< -4.0$ | **PASSED** |
| `test_forecast_version_variance_exact_delta` | Waterfall variance reconciles exact volume differences | **PASSED** |
| `test_forecast_version_variance_material_shift_detection` | Detects material planning shifts ($>20\%$ or $>1,000$ packs) | **PASSED** |
| `test_forecast_registry_save_and_load_roundtrip` | Saves versioned forecast into SQLite and loads with 100% parity | **PASSED** |
| `test_forecast_registry_list_versions` | Queries distinct model versions and horizon dates | **PASSED** |
| `test_forecast_registry_overwrite_protection` | `overwrite=True` cleanly updates records without duplicate rows | **PASSED** |
| `test_forecast_slice_report_markdown_generation` | Scorecard renders clean, executive Markdown report | **PASSED** |

---

## 7. Integration Handover for Day 24 (Forecast Model Card)

The Day 23 deliverable completes the analytical machinery of Week 05, feeding directly into **Day 24 (Forecast Model Card & Demand Anomaly Detector)**:
- Consolidates out-of-time accuracy, dimensional slice benchmarks, and tracking signal tolerances into the official **Forecast Model Card**.
- Implements an online statistical anomaly detector flagging real-time commercial volume surges or drops.
