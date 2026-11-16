# Demand Time-Series Preprocessing & Leakage Controls Specification

**Document Identifier:** `DOC-SPEC-FORECAST-PREP-001`  
**Phase:** Phase 2 — Deterministic Analytics & Core Engines (Weeks 04–07)  
**Deliverable:** Day 20 (Monday, 23-Nov-2026) — Demand Time-Series Preprocessing & Splitting  
**Target Module:** `src/forecasting/prep.py`  
**Test Suite:** `tests/test_forecasting_prep.py` (12 / 12 Passing, 142 Total Repository Tests)  
**Status:** **APPROVED & FULLY VALIDATED**  

---

## 1. Executive Summary & Architectural Intent

In pharmaceutical supply chain operations, demand forecasting directly determines master production schedules (MPS), active ingredient procurement (API), packaging materials, and warehouse buffer allocations.

A critical vulnerability in machine-learning forecasting systems is **future target leakage (lookahead bias)**:
- Random cross-validation or unconstrained feature engineering mistakenly includes future observations (e.g., target values from week $t$ or $t+k$, or rolling averages centered on the target).
- When models train on leaked features, they report unrealistically low errors during validation, but suffer catastrophic failure upon live deployment when future data is unavailable.

**Day 20 establishes a rigid, mathematically proven, leakage-free preprocessing foundation** for the Week 05 forecasting layer:
1. **Chronological Splitting Protocol:** Partitions 104 historical weeks into strictly ordered, non-overlapping train (75%), validation (12.5%), and test (12.5%) partitions.
2. **Strictly Causal Feature Engineering:** Generates 31 deterministic features where all lag and rolling statistical windows are computed exclusively on shifted history ($t-1$ and earlier).
3. **Domain-Specific Pharmaceutical Seasonality:** Integrates cyclical trigonometric transforms and Indian market demand surges (Monsoon respiratory surge, Diwali distributor channel loading, quarter-end loading).
4. **Automated Leakage Audit Engine:** Performs automated verification asserting zero temporal overlap, strict lag causality, target independence, and exclusion of downstream operational outcomes.

---

## 2. Chronological Splitting Protocol

```
+---------------------------------------------------------------------------------------------------+
|                        104-WEEK CHRONOLOGICAL SPLIT TOPOLOGY (ZERO LEAKAGE)                       |
+---------------------------------------------------------------------------------------------------+
|                                                                                                   |
|  [ TRAIN SPLIT: 78 Weeks (75.0%) ]  -->  [ VAL SPLIT: 13 Weeks (12.5%) ]  -->  [ TEST: 13 Weeks ] |
|  2024-10-28 to 2026-04-20                 2026-04-27 to 2026-07-20              2026-07-27 to     |
|  (312 series rows)                        (52 series rows)                      2026-10-19        |
|                                                                                 (52 series rows)  |
|                                                                                                   |
|  Invariant: max(Train_Dates) < min(Val_Dates) <= max(Val_Dates) < min(Test_Dates)                 |
|  Intersection: Train ∩ Val = ∅, Val ∩ Test = ∅, Train ∩ Test = ∅                                  |
+---------------------------------------------------------------------------------------------------+
```

### Partition Boundary Verification
- **Total Historical Horizon:** 104 weeks (4 multi-echelon series: 2 SKUs $\times$ 2 Markets = 416 observations).
- **Training Partition:**
  - Start Date: `2024-10-28` | End Date: `2026-04-20`
  - Duration: 78 consecutive calendar weeks
  - Allocation: 312 series-week records (75.0%)
- **Validation Partition:**
  - Start Date: `2026-04-27` | End Date: `2026-07-20`
  - Duration: 13 consecutive calendar weeks (Q2)
  - Allocation: 52 series-week records (12.5%)
- **Test Partition (Out-of-Time Holdout):**
  - Start Date: `2026-07-27` | End Date: `2026-10-19`
  - Duration: 13 consecutive calendar weeks (Q3)
  - Allocation: 52 series-week records (12.5%)

---

## 3. Causal Feature Engineering Architecture (31 Features)

The pipeline transforms raw demand records into a structured `FeatureMatrix` $(X, y, \text{metadata})$ containing 31 causal features:

```
                                  FEATURE HIERARCHY
                                          |
        +---------------------------------+---------------------------------+
        |                                 |                                 |
 [ Calendar & Cyclical ]      [ Causal Lags & Rolling ]             [ Series Encodings ]
 - calendar_year              - lag_1, lag_2, lag_4, lag_8, lag_12  - is_SKU_AUG_500_T10
 - calendar_month             - rolling_mean_4, rolling_std_4       - is_SKU_AUG_500_T30
 - calendar_quarter           - rolling_min_4, rolling_max_4        - is_MKT_IN_HYD
 - week_of_year               - rolling_mean_12, rolling_std_12     - is_MKT_IN_PUN
 - sin/cos_week_of_year       - rolling_min_12, rolling_max_12
 - sin/cos_month              - ratio_mean4_to_mean12
 - is_quarter_end_month       - diff_lag1_lag2, diff_lag1_lag4
 - is_monsoon_surge
 - is_diwali_period
```

### 1. Calendar & Trigonometric Cyclical Encodings
- **Trigonometric Week Transform:** Preserves continuous annual seasonality between week 52 and week 1:
  $$\sin\left(\frac{2\pi \times \text{week}}{52.1775}\right), \quad \cos\left(\frac{2\pi \times \text{week}}{52.1775}\right)$$
- **Trigonometric Month Transform:** $\sin(2\pi \times \text{month} / 12), \cos(2\pi \times \text{month} / 12)$
- **Pharmaceutical Market Indicators:**
  - `is_monsoon_surge`: Weeks 24 to 38 (June to September peak respiratory antibiotic demand in India).
  - `is_diwali_period`: Weeks 42 to 45 (Distributor channel inventory adjustments ahead of festive holidays).
  - `is_quarter_end_month`: Channel loading spike during months 3, 6, 9, 12.

### 2. Autoregressive Lags ($L_k$)
- Evaluates individual historical demands:
  $$L_1 = y_{t-1}, \quad L_2 = y_{t-2}, \quad L_4 = y_{t-4}, \quad L_8 = y_{t-8}, \quad L_{12} = y_{t-12}$$
- When annual seasonality is enabled: $L_{52} = y_{t-52}$.

### 3. Causal Rolling Window Statistics
- **Critical Leakage Guard:** Rolling calculations are applied strictly to $y.\text{shift}(1)$:
  $$\text{Rolling Mean}_w(t) = \frac{1}{w} \sum_{i=1}^w y_{t-i}$$
  $$\text{Rolling Std}_w(t) = \sqrt{\frac{1}{w-1} \sum_{i=1}^w \left(y_{t-i} - \text{Rolling Mean}_w(t)\right)^2}$$
- Windows evaluated: $w = 4$ weeks (short-term momentum) and $w = 12$ weeks (quarterly baseline).
- **Trend Acceleration Ratio:**
  $$\text{Ratio} = \frac{\text{Rolling Mean}_4(t)}{\text{Rolling Mean}_{12}(t) + 10^{-5}}$$
- **Velocity Differentials:** $y_{t-1} - y_{t-2}$ and $y_{t-1} - y_{t-4}$.

---

## 4. Automated Data Leakage Audit Engine

The function `audit_time_series_leakage` executes five mathematical proofs:

| Audit Check # | Verification Standard | Mathematical Invariant | Result |
|---|---|---|---|
| **Check 1** | Strict Temporal Ordering | $\max(T_{\text{train}}) < \min(T_{\text{val}}) \le \max(T_{\text{val}}) < \min(T_{\text{test}})$ | **PASSED** |
| **Check 2** | Disjoint Calendar Sets | $Dates_{\text{train}} \cap Dates_{\text{val}} = \emptyset \land Dates_{\text{val}} \cap Dates_{\text{test}} = \emptyset$ | **PASSED** |
| **Check 3** | Causal Feature Alignment | $\forall t: X_{t, \text{lag\_1}} \equiv y_{t-1}$ across all series | **PASSED** |
| **Check 4** | Target Independence | $y_t \notin X_t$ and $\forall f \in X_t: |\text{corr}(f, y_t)| < 0.9999$ | **PASSED** |
| **Check 5** | Downstream Outcome Exclusion | `lost_sales_quantity`, `fulfilled_quantity`, `actual_yield` $\notin X_t$ | **PASSED** |

**Consolidated Audit Verdict:** `is_leakage_free == True` (0 detected violations).

---

## 5. Automated Unit Test Verification (`tests/test_forecasting_prep.py`)

All 12 unit tests pass in 0.82 seconds:

| Test Name | Verified Invariant | Status |
|---|---|---|
| `test_load_demand_history_structure_and_counts` | 416 rows loaded, 4 series, 104 distinct weeks | **PASSED** |
| `test_chronological_split_ratios_and_boundaries` | 78 weeks train, 13 weeks val, 13 weeks test | **PASSED** |
| `test_chronological_split_strict_date_ordering` | Train End < Val Start < Test Start | **PASSED** |
| `test_chronological_split_zero_date_overlap` | Disjoint date sets across all splits | **PASSED** |
| `test_calendar_and_cyclical_feature_engineering` | Trigonometric sin/cos bounds $[-1, 1]$ and seasonal flags | **PASSED** |
| `test_causal_lag_alignment_exact_shift` | $L_1(t) == y(t-1)$ and $L_2(t) == y(t-2)$ | **PASSED** |
| `test_causal_rolling_statistics_exclude_current_target` | Rolling windows strictly exclude current period $y_t$ | **PASSED** |
| `test_feature_pipeline_end_to_end_shape_and_metadata` | Feature matrix shape (368, 31) and metadata tracking | **PASSED** |
| `test_partition_feature_matrix_shapes_and_continuity` | PartitionedDataset train/val/test splits match cutoffs | **PASSED** |
| `test_leakage_audit_engine_clean_pass` | Audit passes 5/5 compliance checks | **PASSED** |
| `test_leakage_audit_engine_catches_target_leakage` | Detects artificial target leakage in features | **PASSED** |
| `test_leakage_audit_engine_catches_downstream_leakage` | Detects forbidden downstream operational fields | **PASSED** |

---

## 6. Integration Contract for Days 21–24

The output artifacts produced by Day 20 serve as the rigid contract for the remainder of Week 05:

- **Day 21 (Baseline Models):** Ingests `split.train_df` and evaluates Seasonal Naive and Exponential Smoothing on `split.test_df`.
- **Day 22 (ML Models):** Ingests `dataset.X_train, dataset.y_train` and fits regularized models generating P10/P50/P90 prediction intervals.
- **Day 23 (Evaluation Engine):** Ingests actual vs predicted on `dataset.X_test` and computes WAPE, MAE, Bias %, and Tracking Signal.
- **Day 24 (Forecast Model Card):** Consolidates benchmark scores into official Model Card.
