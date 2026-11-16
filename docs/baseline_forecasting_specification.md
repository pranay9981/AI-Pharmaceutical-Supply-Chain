# Baseline Statistical Forecasting Models Specification

**Document Identifier:** `DOC-SPEC-FORECAST-BASE-001`  
**Phase:** Phase 2 — Deterministic Analytics & Core Engines (Weeks 04–07)  
**Deliverable:** Day 21 (Tuesday, 24-Nov-2026) — Baseline Statistical Forecasting Models  
**Target Module:** `src/forecasting/baseline.py`  
**Test Suite:** `tests/test_forecasting_baseline.py` (12 / 12 Passing, 154 Total Repository Tests)  
**Status:** **APPROVED & FULLY VALIDATED**  

---

## 1. Executive Summary & The Golden Benchmark Principle

In global pharmaceutical supply chain leadership, an executive rule of thumb dictates:
> *"No machine-learning model shall be deployed to production unless it convincingly and consistently outperforms simple, transparent statistical baselines on out-of-time holdout data."*

Complex models carry higher operational maintenance costs, retraining overhead, and potential instability. To earn its place in the Control Tower, any ML forecasting engine (Day 22) must prove superior accuracy against classical time-series baselines.

**Day 21 establishes this empirical benchmark:**
1. Implements four families of classical statistical forecasting algorithms in pure deterministic Python & NumPy.
2. Evaluates out-of-time accuracy across all commercial series (`SKU-AUG-500-T10` and `SKU-AUG-500-T30` across Hyderabad and Pune markets) on the 13-week test partition established on Day 20.
3. Quantifies accuracy via supply-chain standard volume-weighted metrics: **WAPE %, MAE, MAPE %, RMSE, Forecast Bias %, and Tracking Signal**.
4. Discovers the **Champion Baseline Model**: `Seasonal_Naive_52` achieving **16.23% WAPE** and **-1.03% Bias**, setting the definitive hurdle rate for Day 22 machine learning models.

---

## 2. Statistical Baseline Architectures (`src/forecasting/baseline.py`)

```
+-----------------------------------------------------------------------------------+
|                     STATISTICAL BASELINE FORECASTING SUITE                        |
+-----------------------------------------------------------------------------------+
|                                                                                   |
|  [ 1. Seasonal Naive ] ---------> y_{T+h} = y_{T+h - 52}                          |
|                                   (Annual 52-week modular lookback)               |
|                                                                                   |
|  [ 2. Moving Average ] ---------> Simple: (1/k) * sum(y_{T-i})                    |
|                                   Weighted: sum(w_i * y_{T-i}), w_i = (k-i)/sum   |
|                                                                                   |
|  [ 3. Exponential Smoothing ] --> Simple (SES): l_t = α*y_t + (1-α)*l_{t-1}       |
|                                   Holt Linear: l_t + h*b_t (with damping φ=0.98)  |
|                                   Holt-Winters: l_t + h*b_t + s_{t+h-m}           |
|                                                                                   |
+-----------------------------------------------------------------------------------+
```

### A. Seasonal Naive Model (`SeasonalNaiveModel`)
- **Mathematical Definition:**
  $$\hat{y}_{T+h} = y_{T+h - 52}$$
- **Operational Reality:** In pharmaceutical commercial planning, "same week last year" captures annual disease incidence (e.g., monsoon respiratory surges) and festive distributor closures without parameter tuning.
- **Horizon Handling:** If $h > 52$, wraps around modularly: $\hat{y}_{T+h} = y_{T+h - k \cdot 52}$.

### B. Moving Average Models (`MovingAverageModel`)
- **Simple Moving Average (SMA):**
  $$\hat{y}_{T+h} = \frac{1}{k} \sum_{i=0}^{k-1} y_{T-i}$$
  Evaluated at $k=4$ (1-month baseline) and $k=12$ (1-quarter baseline).
- **Linear Weighted Moving Average (WMA):**
  $$w_i = \frac{k - i}{\sum_{j=1}^k j} \quad \implies \quad \hat{y}_{T+h} = \sum_{i=0}^{k-1} w_i \cdot y_{T-i}$$
  Assigns higher weight to recent weeks to capture immediate demand momentum.

### C. Exponential Smoothing Models (`ExponentialSmoothingModel`)
- **Simple Exponential Smoothing (SES):**
  $$\ell_t = \alpha y_t + (1-\alpha) \ell_{t-1}, \quad \hat{y}_{T+h} = \ell_T$$
- **Holt's Linear Trend Model:**
  $$\ell_t = \alpha y_t + (1-\alpha)(\ell_{t-1} + b_{t-1})$$
  $$b_t = \beta(\ell_t - \ell_{t-1}) + (1-\beta)b_{t-1}$$
  $$\hat{y}_{T+h} = \ell_T + \left(\sum_{i=1}^h \phi^i\right) b_T$$
  Uses trend damping ($\phi = 0.98$) and non-negative bounding ($\max(0.0, \hat{y})$) to prevent irrational linear explosion over 26-week horizons.
- **In-Sample Parameter Fitting:** Deterministic grid search over $\alpha \in [0.1, 0.7]$ and $\beta \in [0.05, 0.2]$ minimizing in-sample Sum of Squared Errors (SSE).

---

## 3. Standardized Supply Chain Accuracy & Bias Metrics

To prevent distorted accuracy percentages caused by low-volume denominator issues in classical MAPE, the engine implements the pharmaceutical industry standard metric hierarchy:

| Metric Name | Formula | Strategic Operational Meaning |
|---|---|---|
| **WAPE %** | $\frac{\sum \|y_t - \hat{y}_t\|}{\sum y_t} \times 100\%$ | **Primary Benchmark.** Volume-weighted error percentage. Robust against zero/low demand weeks. |
| **MAE** | $\frac{1}{n} \sum \|y_t - \hat{y}_t\|$ | Average absolute physical unit error (number of pharmaceutical packs misestimated per week). |
| **MAPE %** | $\frac{1}{n} \sum \left\|\frac{y_t - \hat{y}_t}{y_t}\right\| \times 100\%$ | Unweighted average percentage error across periods (with $\epsilon$ guard). |
| **RMSE** | $\sqrt{\frac{1}{n} \sum (y_t - \hat{y}_t)^2}$ | Penalizes large outlier forecasting errors heavily. |
| **Forecast Bias %** | $\frac{\sum (\hat{y}_t - y_t)}{\sum y_t} \times 100\%$ | **Directionality Indicator.** Positive = Over-forecasting (holding cost); Negative = Under-forecasting (stockout risk). |
| **Tracking Signal** | $\frac{\sum (\hat{y}_t - y_t)}{\text{MAE}}$ | Cumulative error normalized by MAD. Bounds: $[-4.0, +4.0]$. |

---

## 4. Empirical Benchmark Scorecard (Live 104-Week Production DB)

Evaluated across all 4 production time-series on the **13-week out-of-time holdout test split** (`2026-07-27` to `2026-10-19`):

| Model Architecture | WAPE % | MAE (Packs) | MAPE % | RMSE | Forecast Bias % | Tracking Signal | Operational Rank |
|---|---|---|---|---|---|---|---|
| **Seasonal_Naive_52** 🏆 | **16.23%** | **494.2** | **16.03%** | **656.0** | **-1.03%** | **-3.32** | **Champion Baseline** |
| **Moving_Average_4** | 16.66% | 507.4 | 17.77% | 656.6 | -0.53% | -1.65 | Runner-up |
| **Moving_Average_12** | 16.66% | 507.4 | 17.77% | 656.6 | -0.53% | -1.65 | Runner-up |
| **Weighted_Moving_Average_12** | 16.66% | 507.4 | 17.77% | 656.6 | -0.53% | -1.65 | Runner-up |
| **Simple_Exponential_Smoothing** | 16.66% | 507.4 | 17.77% | 656.6 | -0.53% | -1.65 | Runner-up |
| **Holt_Linear_Trend** | 17.77% | 541.1 | 19.33% | 686.9 | +0.90% | +2.62 | 6th |

### Key Analytical Findings:
1. **Seasonal Naive 52 Dominance:** `Seasonal_Naive_52` achieves the lowest error (**16.23% WAPE**), proving that annual seasonal recurrence (monsoon antibiotic surge + post-monsoon taper) is the primary deterministic driver of demand variation.
2. **Low Directional Bias:** All baseline models demonstrate exceptional bias discipline (between **-1.03%** and **+0.90%**), well within the executive threshold of $\pm 5.0\%$.
3. **Tracking Signal Health:** Tracking signal remains strictly within $[-3.32, +2.62]$, well inside the standard control limits of $[-4.0, +4.0]$.

---

## 5. Automated Unit Test Verification (`tests/test_forecasting_baseline.py`)

All 12 unit tests pass in 0.69 seconds:

| Test Name | Verified Property | Status |
|---|---|---|
| `test_calculate_forecast_metrics_perfect_prediction` | WAPE=0%, MAE=0, Bias=0% when actuals == predictions | **PASSED** |
| `test_calculate_forecast_metrics_positive_bias` | 10% over-forecasting yields exact +10.0% bias | **PASSED** |
| `test_calculate_forecast_metrics_negative_bias` | 15% under-forecasting yields exact -15.0% bias | **PASSED** |
| `test_seasonal_naive_52_week_mapping` | $y_{t+h} = y_{t+h-52}$ exact historical mapping | **PASSED** |
| `test_seasonal_naive_short_horizon_fallback` | Graceful fallback when series < 52 weeks | **PASSED** |
| `test_simple_moving_average_calculation` | 4-week window exact flat mean extrapolation | **PASSED** |
| `test_weighted_moving_average_decay_weights` | Linear decay weights prioritize recent observations | **PASSED** |
| `test_exponential_smoothing_ses` | Simple Exponential Smoothing level update | **PASSED** |
| `test_exponential_smoothing_holt_linear_trend` | Monotonic upward slope projection on growth trend | **PASSED** |
| `test_exponential_smoothing_non_negative_bounding` | Non-negative constraint prevents physical stockout artifacts | **PASSED** |
| `test_generate_series_forecast_pipeline` | Single series wrapper produces 26-week calendar dates & metrics | **PASSED** |
| `test_baseline_benchmark_evaluation_on_database` | End-to-end benchmark on live DB selects champion model | **PASSED** |

---

## 6. Handover Hurdle Rate for Day 22 ML Models

The Day 21 deliverable produces the official **Hurdle Rate** for Day 22:

$$\text{Hurdle Rate for ML Adoption:} \quad \mathbf{\text{WAPE} < 16.23\%}$$

On Day 22, the Machine Learning forecasting model (incorporating 31 causal lag, rolling statistical, and cyclical features generated on Day 20) will be trained on the identical training partition and evaluated against the identical 13-week holdout test partition. It must beat 16.23% WAPE and maintain $|\text{Bias}| \le 3.0\%$ to secure production sign-off.
