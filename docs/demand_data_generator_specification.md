# 104-Week Historical Demand & Forward Forecast Synthesizer
## Phase 1 Synthetic Data Generation Engine — Day 11 Deliverable
### Week 03 (10-Nov-2026) | Indian Pharmaceutical Supply Chain Network

---

## 1. Executive Summary & Purpose

The **104-Week Historical Demand & Forward Forecast Synthesizer** ([`src/generator/demand_data.py`](file:///d:/AI%20Pharmaceutical%20Supply%20Chain/src/generator/demand_data.py)) generates the commercial demand foundation of the AI-Powered Pharmaceutical Supply Chain Control Tower.

It produces three core transactional and planning entities:
1. **`fact_demand_history` (416 rows)**: 104 weeks of historical weekly sales records across 2 Finished SKUs and 2 Regional Planning Markets.
2. **`fact_demand_forecast` (104 rows)**: 26 forward weeks of probabilistic demand forecasts with P10/P90 prediction intervals and anti-leakage temporal guards.
3. **`fact_customer_order` (32 rows)**: Active customer sales order lines placed by major hospital and wholesale accounts.

All records are validated upon instantiation against the Pydantic v2 schemas defined in `src/models/demand.py` and `src/models/planning.py`.

---

## 2. Mathematical Demand Modeling Architecture

To ensure the synthetic data provides a realistic training and evaluation foundation for forecasting models, the generator implements a composite time-series equation:

$$D_{s,m,t} = \max\Big(500.0, \ B_{s,m} \times T_t \times S_t \times E_t + \epsilon_t\Big)$$

```
Decomposition of Weekly Pharmaceutical Demand:
┌────────────────────────────────────────────────────────┐
│ Base Demand (Bs,m) — Market size & pack presentation   │
│   × Linear Trend (Tt) — 5% annual organic growth       │
│   × Seasonality (St) — Monsoon & respiratory peak      │
│   × Event Multiplier (Et) — Epidemiological & Holidays │
│   + Gaussian Noise (εt) — Controlled stochastic jitter │
└───────────────────────────┬────────────────────────────┘
                            ▼
              Weekly Market Demand (Ds,m,t)
```

### 2.1 Baseline Weekly Demand ($B_{s,m}$)
Antibiotic demand varies by pack presentation format and regional demographics:

| SKU ID | Presentation | Market ID | Baseline ($B_{s,m}$) | Typical Clinical Setting |
| :--- | :--- | :--- | :---: | :--- |
| `SKU-AUG-500-T10` | 10-Tablet Strip | `MKT-IN-HYD` (Hyderabad) | **3,500 packs/wk** | Acute respiratory out-patient dispensing |
| `SKU-AUG-500-T10` | 10-Tablet Strip | `MKT-IN-PUN` (Pune) | **3,000 packs/wk** | Acute respiratory out-patient dispensing |
| `SKU-AUG-500-T30` | 30-Tablet Bottle | `MKT-IN-HYD` (Hyderabad) | **1,800 packs/wk** | Extended/chronic courses & bulk hospital tenders |
| `SKU-AUG-500-T30` | 30-Tablet Bottle | `MKT-IN-PUN` (Pune) | **1,500 packs/wk** | Extended/chronic courses & bulk hospital tenders |

### 2.2 Annual Trend Growth ($T_t$)
Models a 5% annual linear volume expansion over the 2-year historical observation window:
$$T_t = 1.0 + 0.05 \times \left(\frac{t}{52.0}\right) \quad \text{for } t \in [0, 103]$$
* At $t = 0$ (Week 1, Oct 2024): $T_0 = 1.000$
* At $t = 52$ (Week 53, Oct 2025): $T_{52} = 1.050$
* At $t = 103$ (Week 104, Oct 2026): $T_{103} \approx 1.099$

### 2.3 Respiratory & Monsoon Seasonality ($S_t$)
In India, bacterial respiratory infections and secondary complications surge during the southwest monsoon and post-monsoon months (July through September, ISO weeks 28–36):
$$S_t = 1.0 + 0.25 \times \sin\left(\frac{2\pi \times (w_t - 15)}{52.0}\right)$$
* $w_t \in [1, 52]$: ISO calendar week of the year.
* Amplitude: 25% peak-to-trough seasonal swing.
* Peak: Weeks 28–30 (July/August, $S_t \approx 1.25$).
* Trough: Weeks 2–4 (January/February) and spring months.

### 2.4 Epidemiological Surges & Holiday Adjustments ($E_t$)
* **Monsoon Respiratory Surge (Weeks 32–33)**: Severe seasonal spike (+18%, $E_t = 1.18$). Event tagged as `Monsoon_Respiratory_Surge`.
* **Diwali Commercial Closure (Weeks 43–44)**: Wholesaler destocking and clinic holiday closures (−10%, $E_t = 0.90$). Event tagged as `Diwali_Holiday_Adjustment`.
* **Normal Weeks**: $E_t = 1.00$, event tagged as `Normal`.

### 2.5 Controlled Gaussian Noise ($\epsilon_t$)
To prevent artificial regularity while preserving underlying structural dynamics, controlled Gaussian noise is injected with standard deviation equal to 8% of baseline:
$$\epsilon_t \sim \mathcal{N}\left(0, \ (0.08 \times B_{s,m})^2\right)$$

### 2.6 Fulfillment & Historical Stockout Recording
Over the 104-week baseline, demand was fulfilled at 100% with zero lost sales, except for a synthetic historical event:
* **Week 48 Historical Event**: In Week 48 (late September 2025), a packaging foil bottleneck at the plant caused a temporary 12% fulfillment deficit for `SKU-AUG-500-T10` in `MKT-IN-HYD`:
  $$F_{48} = 0.88 \times D_{48}, \quad L_{48} = 0.12 \times D_{48}$$
  Event tagged as `Historical_Packaging_Bottleneck`.
* Strict demand conservation is enforced:
  $$D_t = F_t + L_t$$

---

## 3. Forward Demand Forecasts (`fact_demand_forecast`)

The generator produces a 26-week forward planning horizon (104 rows: 26 weeks $\times$ 2 SKUs $\times$ 2 markets).

### 3.1 Anti-Leakage Temporal Guard
To prevent machine learning models from training on future information, the schema strictly enforces:
$$\text{target\_week} \ge \text{forecast\_version\_date}$$
Any record attempting to specify a target week earlier than the planning as-of date (`2026-10-26`) triggers an unhandled `ValidationError`.

### 3.2 Probabilistic Prediction Intervals (P10 / P90)
Uncertainty widens monotonically over the forecast horizon:
$$u_h = 0.05 + 0.13 \times \left(\frac{h}{26.0}\right) \quad \text{for } h \in [0, 25]$$
* **Week 1 ($h=0$):** Uncertainty = $\pm 5.0\%$ (P10 = $0.95 \times \hat{D}$, P90 = $1.05 \times \hat{D}$).
* **Week 26 ($h=25$):** Uncertainty = $\pm 17.5\%$ (P10 = $0.825 \times \hat{D}$, P90 = $1.175 \times \hat{D}$).
* Prediction bounds satisfy: $\text{lower\_bound} \le \text{forecast\_quantity} \le \text{upper\_bound}$.

---

## 4. Commercial Customer Orders (`fact_customer_order`)

To model immediate operational execution, 32 open sales order lines are synthesized across 4 ordering cycles ($+0, +3, +7, +10$ days from as-of cutoff):
* Accounts: `CUST-001` & `CUST-002` (Hyderabad); `CUST-003` & `CUST-004` (Pune).
* Presentation quantities: 1,500 packs for T10 strips; 800 packs for T30 bottles.
* Milestone constraint strictly enforced:
  $$\text{requested\_delivery\_date} \ge \text{order\_date} \quad \text{and} \quad \text{promised\_delivery\_date} \ge \text{order\_date}$$

---

## 5. Automated Test Suite & Verification Results

The Day 11 deliverable is verified by [`tests/test_generator_demand.py`](file:///d:/AI%20Pharmaceutical%20Supply%20Chain/tests/test_generator_demand.py):

| Test Identifier | Verification Focus | Result |
| :--- | :--- | :---: |
| `test_demand_history_record_count_and_continuity` | Exactly 416 rows, 104 distinct Monday weekly dates, temporal bounds | ✅ PASSED |
| `test_demand_trend_and_seasonality_dynamics` | Trend math, monsoon peak vs spring trough, Year 2 vs Year 1 growth | ✅ PASSED |
| `test_historical_stockout_and_lost_sales_recording` | Week 48 lost sales deficit ($D = F + L$) and normal zero-deficit periods | ✅ PASSED |
| `test_demand_forecast_record_count_and_leakage_guards` | 104 forecast rows, anti-leakage invariant, widening P10/P90 spread | ✅ PASSED |
| `test_customer_orders_structure_and_milestones` | 32 order lines, unique PKs, delivery date $\ge$ order date milestones | ✅ PASSED |
| `test_demand_seed_reproducibility` | Bitwise reproducibility with seed `20261014`, sensitivity to seed shifts | ✅ PASSED |

**Complete Project Test Status:**
```
============================= 65 passed in 2.08s ==============================
```

---

*Document finalized: 10-Nov-2026 (Day 11) | Phase 1 Synthetic Data Generation Engine — On Schedule.*
