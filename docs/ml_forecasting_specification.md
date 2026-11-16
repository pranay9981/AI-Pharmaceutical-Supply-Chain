# Machine Learning Demand Forecasting Models & Prediction Intervals Specification

**Document Identifier:** `DOC-SPEC-FORECAST-ML-001`  
**Phase:** Phase 2 — Deterministic Analytics & Core Engines (Weeks 04–07)  
**Deliverable:** Day 22 (Wednesday, 25-Nov-2026) — ML Forecasting Models & Confidence Intervals  
**Target Module:** `src/forecasting/ml_models.py`  
**Test Suite:** `tests/test_forecasting_ml.py` (12 / 12 Passing, 166 Total Repository Tests)  
**Status:** **APPROVED & FULLY VALIDATED**  

---

## 1. Executive Summary & Hurdle Rate Victory

On Day 21, the golden baseline benchmark was established:
$$\text{Baseline Benchmark (Seasonal Naive 52):} \quad \mathbf{16.23\% \text{ WAPE}}, \quad \text{MAE } 494.2 \text{ packs}, \quad \text{Bias } -1.03\%$$

Any candidate machine-learning architecture had to prove its right to exist in the Control Tower by beating this threshold on the identical 13-week out-of-time holdout test partition (`2026-07-27` to `2026-10-19`).

### Executive Decision: **HURDLE CLEARED EMPIRICALLY**
- **Champion ML Model:** `Ridge_Regression` (L2 Regularized Linear Model with Scaled Causal Features)
- **Holdout Accuracy:** **7.76% WAPE** (MAE **236.2 packs**, Bias **-0.45%**, RMSE **337.1**)
- **Relative Error Reduction:** **+52.2%** error reduction over the Seasonal Naive champion baseline!
- **Probabilistic Bands:** Generates calibrated P10 (downside buffer), P50 (median plan), and P90 (surge capacity) bounds with expanding horizon uncertainty.
- **Production Rollout:** Produces a 26-week forward recursive forecast (104 rows) across all finished SKUs and commercial markets matching `fact_demand_forecast`.

---

## 2. Candidate ML Model Performance Scorecard

Evaluated on the 13-week holdout test split (`2026-07-27` to `2026-10-19`) across all 4 commercial series (`SKU-AUG-500-T10` & `SKU-AUG-500-T30` in Hyderabad and Pune markets):

| Model Architecture | WAPE % | MAE (Packs) | MAPE % | RMSE | Forecast Bias % | Tracking Signal | Operational Decision |
|---|---|---|---|---|---|---|---|
| *Baseline (Seasonal_Naive_52)* | *16.23%* | *494.2* | *16.03%* | *656.0* | *-1.03%* | *-3.32* | *Hurdle Benchmark* |
| **Ridge_Regression** 🏆 | **7.76%** | **236.2** | **7.62%** | **337.1** | **-0.45%** | **-3.00** | **Adopted for Production** |
| **ElasticNet_Regression** | 8.10% | 246.7 | 8.01% | 355.9 | -0.02% | -0.12 | Production Backup |
| **Gradient_Boosting** | 9.27% | 282.4 | 9.09% | 375.2 | -1.75% | -9.84 | Non-Linear Alternative |

### Why Ridge Regression Won:
1. **Convex Stability:** Minimizes $\|y - X\beta\|_2^2 + \alpha \|\beta\|_2^2$ with closed-form solution $\hat{\beta} = (X^T X + \alpha I)^{-1} X^T y$.
2. **Superior Generalization:** Feature scaling prevents dominant variance artifacts from overshadowing small trigonometric cyclicals, while L2 shrinkage controls collinearity between consecutive lags ($L_1, L_2$) and rolling averages.
3. **Execution Speed:** Computes full multi-series 26-week forecasts in under 3 milliseconds, fully supporting interactive what-if simulation re-runs.

---

## 3. Probabilistic Prediction Intervals (P10 / P50 / P90)

```
       DEMAND FORECAST WITH EXPANDING UNCERTAINTY FAN BANDS
Demand
(Units)
  ^
  |                                        /--- P90 (Surge Upside Bound)
  |                                 /------
  |                          /------
  |                   /------  ================ P50 (Median Baseline Plan)
  |            /------          \------
  |     /------                        \--- P10 (Safety Buffer Downside)
  | ---
  +------------------------------------------------------------>
    Week 1 (Near Horizon)             Week 26 (Far Horizon)
    Narrow Interval (High Certainty)  Wide Fan (Compounding Uncertainty)
```

### Mathematical Formulation
To reflect real-world supply chain reality, forecast uncertainty compounds over time:
$$\sigma_h = \sigma_{\text{residual}} \times \sqrt{1 + c \cdot (h - 1)}$$
where:
- $\sigma_{\text{residual}}$ is the standard deviation of residuals measured on the validation partition ($X_{\text{val}}, y_{\text{val}}$).
- $c = 0.04$ is the multi-step autoregressive variance expansion coefficient.
- $h \in [1, 26]$ is the forecast horizon step.

### Bounds Calculation:
$$\text{P10}_{T+h} = \max\left(0.0, \hat{y}_{T+h} + q_{10} \times \sqrt{1 + c(h-1)}\right)$$
$$\text{P50}_{T+h} = \max(0.0, \hat{y}_{T+h})$$
$$\text{P90}_{T+h} = \max\left(\text{P50}_{T+h}, \hat{y}_{T+h} + q_{90} \times \sqrt{1 + c(h-1)}\right)$$

### Invariants Guaranteed:
1. **Monotonicity:** $\text{P10} \le \text{P50} \le \text{P90}$ strictly holds across every forward step.
2. **Physical Feasibility:** $\text{P10} \ge 0.0$ prevents irrational negative demand artifacts.
3. **Horizon Expansion:** Uncertainty spread $(\text{P90} - \text{P10})$ expands monotonically from Week 1 to Week 26.

---

## 4. Recursive 26-Week Forward Rollout Engine

For forward horizon planning (`2026-10-26` to `2027-04-19`), future demand observations do not yet exist. The engine employs **Recursive Multi-Step Autoregressive Rollout**:

```
[ Step h=1 ]  Known Lags & Rolling Stats --------> Predicts y_hat(T+1)
                                                         |
                                                         v
[ Step h=2 ]  Lag_1 <- y_hat(T+1); Recalculate Stats -> Predicts y_hat(T+2)
                                                         |
                                                         v
[ Step h=3 ]  Lag_1 <- y_hat(T+2); Lag_2 <- y_hat(T+1) -> Predicts y_hat(T+3)
...
[ Step h=26]  Full 26-Week Projection Completed
```

### Relational Schema Parity (`fact_demand_forecast`):
The output format maps directly to the relational database schema:
- `forecast_id`: e.g. `FC-2026-ML-001`
- `forecast_version_date`: `2026-10-26`
- `target_week`: `2026-10-26` through `2027-04-19` (26 Mondays)
- `finished_sku_id`: `SKU-AUG-500-T10` / `SKU-AUG-500-T30`
- `market_id`: `MKT-IN-HYD` / `MKT-IN-PUN`
- `forecast_quantity`: P50 point forecast
- `lower_bound`: P10 safety lower bound
- `upper_bound`: P90 surge upper bound
- `model_version`: `ML_Ridge_V1`
- `scenario_id`: `SCN-BASE`

Total generated rows: **104 records** (4 series $\times$ 26 weeks).

---

## 5. Automated Unit Test Verification (`tests/test_forecasting_ml.py`)

All 12 unit tests pass in 3.13 seconds:

| Test Name | Verified Property | Status |
|---|---|---|
| `test_ridge_demand_forecaster_fit_and_predict` | Ridge trains and predicts positive demand with calibrated residuals | **PASSED** |
| `test_gradient_boosting_demand_forecaster_fit_and_predict` | Gradient boosting trains with tree depth 3 | **PASSED** |
| `test_prediction_intervals_ordering_and_spread` | Invariant $P10 \le P50 \le P90$ holds with spread $\ge 0$ | **PASSED** |
| `test_prediction_intervals_uncertainty_growth` | Uncertainty spread expands with forward horizon $h$ | **PASSED** |
| `test_prediction_intervals_non_negative_lower_bound` | P10 physically bounded at 0.0 even under large negative errors | **PASSED** |
| `test_recursive_multi_step_forecast_26_weeks` | Rollout produces exactly 26 consecutive weekly dates | **PASSED** |
| `test_evaluate_ml_against_baseline_hurdle_cleared` | Champion ML model beats baseline hurdle (WAPE $< 16.23\%$) | **PASSED** |
| `test_champion_ml_wape_reduction_magnitude` | Error reduction $\ge 40\%$ (achieved +52.2%) | **PASSED** |
| `test_generate_production_26_week_forecast_shape_and_schema` | Generates 104 rows matching `fact_demand_forecast` | **PASSED** |
| `test_production_forecast_no_null_intervals` | Zero null or NaN values in point forecast or bounds | **PASSED** |
| `test_recursive_multi_step_autoregressive_update` | Predictions accurately propagate into subsequent lag features | **PASSED** |
| `test_ml_scorecard_markdown_summary_generation` | Executive scorecard renders clean Markdown summary | **PASSED** |

---

## 6. Integration Contract for Days 23 & 24

The Day 22 deliverable provides the foundation for the final two days of Week 05:

- **Day 23 (Forecast Evaluation & Versioning Engine):**
  - Implement versioned forecast storage and comparison in SQLite (`fact_demand_forecast`).
  - Formal tracking of model versions (`ML_Ridge_V1` vs `Baseline_SNaive_V1`).
  - Automated tracking signal drift alarms outside $[-4.0, +4.0]$.
- **Day 24 (Forecast Model Card & Demand Anomaly Detector):**
  - Author official Forecast Model Card documenting training cutoff, error metrics, operational limits, and Responsible AI notes.
  - Implement statistical demand anomaly detector flagging unexpected commercial volume deviations.
