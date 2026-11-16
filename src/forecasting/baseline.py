"""
Pharmaceutical Baseline Statistical Forecasting Engine.
Phase 2 (Day 21) Forecasting Layer Implementation.

Implements standard benchmark statistical forecasting models:
1. Seasonal Naive Model (annual 52-week seasonality: y_{t+h} = y_{t+h-52})
2. Moving Average Models (Simple Moving Average and Linear Weighted Moving Average)
3. Exponential Smoothing Models (Simple Exponential Smoothing, Holt's Linear Trend, Holt-Winters Additive Seasonality)
4. Multi-Series Forecasting Pipeline (26-week point forecasts across all SKUs and markets)
5. Comprehensive Error Evaluation (WAPE, MAE, MAPE, RMSE, Forecast Bias %, Tracking Signal)

Strictly zero LLM mathematical calculations. Pure deterministic time-series algorithms.
"""

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from typing import List, Dict, Tuple, Optional, Any, Union
import math
import numpy as np
import pandas as pd

from src.forecasting.prep import TimeSeriesSplit


# =============================================================================
# DATA CONTRACTS
# =============================================================================

@dataclass(frozen=True)
class ForecastEvaluationMetrics:
    """Standardized supply chain forecast accuracy and bias metrics."""
    wape_pct: float       # Weighted Absolute Percentage Error (MAD/Mean Ratio)
    mae: float            # Mean Absolute Error
    mape_pct: float       # Mean Absolute Percentage Error
    rmse: float           # Root Mean Squared Error
    bias_pct: float       # Forecast Bias % (Positive = Over-forecast, Negative = Under-forecast)
    tracking_signal: float  # Cumulative Error / MAD
    num_samples: int


@dataclass
class SeriesForecastResult:
    """Forecast outcome generated for a single SKU x Market time-series."""
    model_name: str
    finished_sku_id: str
    market_id: str
    cutoff_date: date
    target_weeks: List[date]
    forecast_quantities: List[float]
    metrics: Optional[ForecastEvaluationMetrics] = None


@dataclass
class BaselineBenchmarkReport:
    """Consolidated benchmark evaluation comparing all candidate statistical baseline models."""
    evaluation_horizon_weeks: int
    models_evaluated: List[str]
    series_evaluated: List[str]
    model_performance: Dict[str, ForecastEvaluationMetrics]
    best_model_name: str
    forecast_df: pd.DataFrame
    summary_df: pd.DataFrame
    evaluation_timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def generate_markdown_summary(self) -> str:
        """Formats the baseline benchmark scorecard into an executive Markdown report."""
        lines = [
            "# Baseline Statistical Forecasting Benchmark Scorecard",
            f"**Evaluation Timestamp:** {self.evaluation_timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}  ",
            f"**Evaluation Horizon:** `{self.evaluation_horizon_weeks}` holdout weeks  ",
            f"**Series Evaluated:** {len(self.series_evaluated)} ({', '.join(self.series_evaluated)})  ",
            f"**Champion Baseline Model:** `{self.best_model_name}` (Lowest WAPE)  ",
            "",
            "## 1. Candidate Model Performance Matrix",
            "",
            "| Model Architecture | WAPE % | MAE (Units) | MAPE % | RMSE | Forecast Bias % | Tracking Signal |",
            "|---|---|---|---|---|---|---|"
        ]

        for m_name in self.models_evaluated:
            perf = self.model_performance[m_name]
            champion_tag = " 🏆 (Champion)" if m_name == self.best_model_name else ""
            lines.append(
                f"| **{m_name}**{champion_tag} | {perf.wape_pct:.2f}% | {perf.mae:.1f} | "
                f"{perf.mape_pct:.2f}% | {perf.rmse:.1f} | {perf.bias_pct:+.2f}% | {perf.tracking_signal:+.2f} |"
            )

        lines.extend([
            "",
            "## 2. Metric Interpretation Guidelines",
            "- **WAPE % (Weighted Absolute Percentage Error):** Primary pharmaceutical benchmark metric. Weights absolute volume errors against total demand, avoiding low-volume distortion.",
            "- **Forecast Bias %:** Measures directional tendency. Negative bias indicates chronic under-forecasting (stockout risk); positive bias indicates over-forecasting (inventory holding / expiry risk).",
            "- **Tracking Signal:** Cumulative forecast error divided by MAD. Values outside $[-4.0, +4.0]$ indicate systematic model drift requiring parameter recalibration.",
            "",
            "## 3. Handover Contract for Day 22 ML Models",
            f"All candidate ML forecasting models (LightGBM / Regularized Ridge) developed on Day 22 must achieve a **WAPE < {self.model_performance[self.best_model_name].wape_pct:.2f}%** on the identical holdout split to justify production adoption."
        ])

        return "\n".join(lines)


# =============================================================================
# 1. EVALUATION METRICS MATHEMATICAL ENGINE
# =============================================================================

def calculate_forecast_metrics(
    actuals: Union[List[float], np.ndarray, pd.Series],
    predictions: Union[List[float], np.ndarray, pd.Series]
) -> ForecastEvaluationMetrics:
    """
    Computes deterministic forecast accuracy and directional bias metrics.
    Strictly zero LLM math. Pure NumPy implementations.
    """
    y_true = np.asarray(actuals, dtype=float)
    y_pred = np.asarray(predictions, dtype=float)

    if len(y_true) != len(y_pred):
        raise ValueError(f"Length mismatch: actuals ({len(y_true)}) != predictions ({len(y_pred)})")
    if len(y_true) == 0:
        raise ValueError("Cannot evaluate metrics on empty series")

    n = len(y_true)
    errors = y_pred - y_true
    abs_errors = np.abs(errors)
    sum_actuals = np.sum(y_true)

    # 1. WAPE % = (sum |y - y_hat| / sum y) * 100
    wape_pct = (np.sum(abs_errors) / max(1.0, sum_actuals)) * 100.0

    # 2. MAE = (1/n) sum |y - y_hat|
    mae = float(np.mean(abs_errors))

    # 3. MAPE % = (1/n) sum |(y - y_hat) / y| * 100 (epsilon guard against zero demand)
    nonzero_mask = y_true > 1e-4
    if np.any(nonzero_mask):
        mape_pct = float(np.mean(abs_errors[nonzero_mask] / y_true[nonzero_mask]) * 100.0)
    else:
        mape_pct = 0.0

    # 4. RMSE = sqrt((1/n) sum (y - y_hat)^2)
    rmse = float(np.sqrt(np.mean(errors ** 2)))

    # 5. Forecast Bias % = (sum (y_hat - y) / sum y) * 100
    bias_pct = (np.sum(errors) / max(1.0, sum_actuals)) * 100.0

    # 6. Tracking Signal = Cumulative Error / MAD
    cumulative_error = float(np.sum(errors))
    tracking_signal = cumulative_error / max(1e-4, mae)

    return ForecastEvaluationMetrics(
        wape_pct=round(wape_pct, 4),
        mae=round(mae, 4),
        mape_pct=round(mape_pct, 4),
        rmse=round(rmse, 4),
        bias_pct=round(bias_pct, 4),
        tracking_signal=round(tracking_signal, 4),
        num_samples=n
    )


# =============================================================================
# 2. STATISTICAL BASELINE MODELS
# =============================================================================

class SeasonalNaiveModel:
    """
    Seasonal Naive Forecasting Model.
    y_{T+h} = y_{T+h - k*m}
    
    Default seasonality m=52 (annual weekly cycle).
    If historical series has less than m observations, falls back to m=12 or naive last value.
    """
    def __init__(self, seasonal_period: int = 52):
        self.seasonal_period = seasonal_period
        self.history: np.ndarray = np.array([])

    def fit(self, y: Union[List[float], np.ndarray, pd.Series]) -> "SeasonalNaiveModel":
        self.history = np.asarray(y, dtype=float)
        if len(self.history) == 0:
            raise ValueError("Cannot fit SeasonalNaive on empty series")
        return self

    def predict(self, horizon: int) -> np.ndarray:
        if len(self.history) == 0:
            raise RuntimeError("Model must be fit before predict()")
        
        m = self.seasonal_period
        n = len(self.history)

        # Fallback if history shorter than seasonal period
        if n < m:
            m = 12 if n >= 12 else 4 if n >= 4 else 1

        forecasts = []
        for h in range(1, horizon + 1):
            # Modular historical index mapping
            offset = (h - 1) % m + 1
            idx = n - m + (offset - 1)
            # Ensure index is within history bounds
            idx = idx % n
            val = max(0.0, float(self.history[idx]))
            forecasts.append(val)

        return np.array(forecasts, dtype=float)


class MovingAverageModel:
    """
    Moving Average Forecasting Model.
    Supports Simple Moving Average (SMA) and Linear Weighted Moving Average (WMA).
    Generates flat forward extrapolation: y_{T+h} = RollingMean_k(history).
    """
    def __init__(self, window: int = 12, weighted: bool = False):
        self.window = window
        self.weighted = weighted
        self.history: np.ndarray = np.array([])
        self.forecast_level: float = 0.0

    def fit(self, y: Union[List[float], np.ndarray, pd.Series]) -> "MovingAverageModel":
        self.history = np.asarray(y, dtype=float)
        if len(self.history) == 0:
            raise ValueError("Cannot fit MovingAverage on empty series")

        k = min(self.window, len(self.history))
        tail = self.history[-k:]

        if self.weighted:
            # Linear decay weights: w_i = (k - i) / sum
            weights = np.arange(k, 0, -1, dtype=float)
            weights /= np.sum(weights)
            self.forecast_level = float(np.sum(tail * weights[::-1]))
        else:
            self.forecast_level = float(np.mean(tail))

        self.forecast_level = max(0.0, self.forecast_level)
        return self

    def predict(self, horizon: int) -> np.ndarray:
        if len(self.history) == 0:
            raise RuntimeError("Model must be fit before predict()")
        return np.full(horizon, self.forecast_level, dtype=float)


class ExponentialSmoothingModel:
    """
    Exponential Smoothing Suite:
    - method='ses': Simple Exponential Smoothing (level alpha)
    - method='holt': Holt's Linear Trend (level alpha, trend beta, optional damping phi)
    - method='holt_winters': Holt-Winters Additive Seasonality (level alpha, trend beta, seasonal gamma, period m)
    
    Includes automatic parameter optimization using Grid Search / Nelder-Mead on historical training SSE.
    """
    def __init__(
        self,
        method: str = "holt",
        alpha: float = 0.3,
        beta: float = 0.1,
        gamma: float = 0.2,
        phi: float = 0.95,
        seasonal_period: int = 52,
        auto_fit: bool = True
    ):
        self.method = method.lower()
        if self.method not in ("ses", "holt", "holt_winters"):
            raise ValueError(f"Unknown method {method}; choose 'ses', 'holt', or 'holt_winters'")
        self.alpha = alpha
        self.beta = beta
        self.gamma = gamma
        self.phi = phi
        self.seasonal_period = seasonal_period
        self.auto_fit = auto_fit

        # Fitted state parameters
        self.history: np.ndarray = np.array([])
        self.last_level: float = 0.0
        self.last_trend: float = 0.0
        self.last_seasonals: np.ndarray = np.array([])

    def _optimize_parameters(self, y: np.ndarray):
        """Finds optimal smoothing parameters minimizing Sum of Squared Errors (SSE) over grid."""
        best_sse = float("inf")
        best_params = (self.alpha, self.beta, self.gamma)

        # Compact coarse grid for ultra-fast, robust parameter selection
        alpha_grid = [0.1, 0.2, 0.3, 0.5, 0.7]
        beta_grid = [0.05, 0.1, 0.2] if self.method in ("holt", "holt_winters") else [0.0]
        gamma_grid = [0.1, 0.2, 0.3] if self.method == "holt_winters" else [0.0]

        for a in alpha_grid:
            for b in beta_grid:
                for g in gamma_grid:
                    sse = self._evaluate_in_sample_sse(y, a, b, g)
                    if sse < best_sse:
                        best_sse = sse
                        best_params = (a, b, g)

        self.alpha, self.beta, self.gamma = best_params

    def _evaluate_in_sample_sse(self, y: np.ndarray, alpha: float, beta: float, gamma: float) -> float:
        """Computes in-sample one-step-ahead squared prediction error."""
        n = len(y)
        if n < 4:
            return float("inf")

        level = y[0]
        trend = (y[min(4, n-1)] - y[0]) / min(4, n-1)
        m = self.seasonal_period if self.method == "holt_winters" else 1

        seasonals = np.zeros(m)
        sse = 0.0

        for t in range(n):
            if self.method == "ses":
                pred = level
                err = y[t] - pred
                level = alpha * y[t] + (1 - alpha) * level
            elif self.method == "holt":
                pred = level + trend
                err = y[t] - pred
                new_level = alpha * y[t] + (1 - alpha) * (level + trend)
                trend = beta * (new_level - level) + (1 - beta) * trend
                level = new_level
            elif self.method == "holt_winters":
                s_idx = t % m
                pred = level + trend + seasonals[s_idx]
                err = y[t] - pred
                new_level = alpha * (y[t] - seasonals[s_idx]) + (1 - alpha) * (level + trend)
                trend = beta * (new_level - level) + (1 - beta) * trend
                seasonals[s_idx] = gamma * (y[t] - new_level) + (1 - gamma) * seasonals[s_idx]
                level = new_level

            sse += err ** 2

        return sse

    def fit(self, y: Union[List[float], np.ndarray, pd.Series]) -> "ExponentialSmoothingModel":
        self.history = np.asarray(y, dtype=float)
        n = len(self.history)
        if n == 0:
            raise ValueError("Cannot fit ExponentialSmoothing on empty series")

        if self.auto_fit and n >= 8:
            self._optimize_parameters(self.history)

        # Initialize state components
        self.last_level = float(self.history[0])
        self.last_trend = float((self.history[min(4, n - 1)] - self.history[0]) / max(1, min(4, n - 1)))

        m = self.seasonal_period if self.method == "holt_winters" else 1
        self.last_seasonals = np.zeros(m)

        # Full forward filtering pass
        for t in range(n):
            yt = self.history[t]
            if self.method == "ses":
                self.last_level = self.alpha * yt + (1.0 - self.alpha) * self.last_level
            elif self.method == "holt":
                new_level = self.alpha * yt + (1.0 - self.alpha) * (self.last_level + self.last_trend)
                self.last_trend = self.beta * (new_level - self.last_level) + (1.0 - self.beta) * self.last_trend
                self.last_level = new_level
            elif self.method == "holt_winters":
                s_idx = t % m
                new_level = self.alpha * (yt - self.last_seasonals[s_idx]) + (1.0 - self.alpha) * (self.last_level + self.last_trend)
                self.last_trend = self.beta * (new_level - self.last_level) + (1.0 - self.beta) * self.last_trend
                self.last_seasonals[s_idx] = self.gamma * (yt - new_level) + (1.0 - self.gamma) * self.last_seasonals[s_idx]
                self.last_level = new_level

        return self

    def predict(self, horizon: int) -> np.ndarray:
        if len(self.history) == 0:
            raise RuntimeError("Model must be fit before predict()")

        forecasts = []
        m = self.seasonal_period if self.method == "holt_winters" else 1

        for h in range(1, horizon + 1):
            if self.method == "ses":
                y_hat = self.last_level
            elif self.method == "holt":
                # Damped linear trend projection: level + sum(phi^i)*trend
                if self.phi < 1.0:
                    damp_factor = (self.phi * (1.0 - (self.phi ** h))) / (1.0 - self.phi)
                else:
                    damp_factor = float(h)
                y_hat = self.last_level + damp_factor * self.last_trend
            elif self.method == "holt_winters":
                damp_factor = float(h)
                s_idx = (len(self.history) + h - 1) % m
                y_hat = self.last_level + damp_factor * self.last_trend + self.last_seasonals[s_idx]

            # Physical non-negativity constraint
            forecasts.append(max(0.0, float(y_hat)))

        return np.array(forecasts, dtype=float)


# =============================================================================
# 3. MULTI-SERIES FORECASTING PIPELINE
# =============================================================================

def generate_series_forecast(
    train_series: pd.Series,
    model_name: str,
    horizon_weeks: int = 26,
    sku_id: str = "SKU-AUG-500-T10",
    market_id: str = "MKT-IN-HYD",
    cutoff_date: Optional[date] = None,
    test_actuals: Optional[pd.Series] = None
) -> SeriesForecastResult:
    """
    Fits a specified statistical baseline model on an individual series and generates point forecasts.
    Optionally computes accuracy metrics if test actuals are provided.
    """
    if cutoff_date is None:
        cutoff_date = date.today()

    # Model instantiation factory
    m_lower = model_name.lower()
    if "seasonal_naive" in m_lower or "snaive" in m_lower:
        model = SeasonalNaiveModel(seasonal_period=52)
    elif "sma_4" in m_lower:
        model = MovingAverageModel(window=4, weighted=False)
    elif "sma_12" in m_lower:
        model = MovingAverageModel(window=12, weighted=False)
    elif "wma_12" in m_lower:
        model = MovingAverageModel(window=12, weighted=True)
    elif "ses" in m_lower:
        model = ExponentialSmoothingModel(method="ses", auto_fit=True)
    elif "holt_winters" in m_lower:
        model = ExponentialSmoothingModel(method="holt_winters", seasonal_period=52, auto_fit=True)
    elif "holt" in m_lower:
        model = ExponentialSmoothingModel(method="holt", phi=0.98, auto_fit=True)
    else:
        # Default to Holt Linear
        model = ExponentialSmoothingModel(method="holt", auto_fit=True)

    # Fit & Predict
    model.fit(train_series.values)
    preds = model.predict(horizon=horizon_weeks)

    # Generate forward Monday calendar dates
    target_dates = [cutoff_date + timedelta(days=7 * i) for i in range(1, horizon_weeks + 1)]

    # Compute evaluation metrics if actuals provided
    metrics = None
    if test_actuals is not None and len(test_actuals) > 0:
        eval_len = min(len(test_actuals), len(preds))
        metrics = calculate_forecast_metrics(
            actuals=test_actuals.values[:eval_len],
            predictions=preds[:eval_len]
        )

    return SeriesForecastResult(
        model_name=model_name,
        finished_sku_id=sku_id,
        market_id=market_id,
        cutoff_date=cutoff_date,
        target_weeks=target_dates,
        forecast_quantities=[round(float(q), 1) for q in preds],
        metrics=metrics
    )


# =============================================================================
# 4. BENCHMARK EVALUATOR & SCORECARD GENERATOR
# =============================================================================

def run_baseline_benchmark_evaluation(
    split: TimeSeriesSplit,
    models: Optional[List[str]] = None,
    group_cols: List[str] = ["finished_sku_id", "market_id"],
    target_col: str = "demand_quantity",
    date_col: str = "week_start_date"
) -> BaselineBenchmarkReport:
    """
    Executes a comprehensive benchmark evaluation across all candidate baseline models:
    Trains models strictly on split.train_df, and tests out-of-time accuracy against split.test_df.
    Computes aggregated WAPE %, MAE, MAPE %, RMSE, and Forecast Bias %.
    """
    if models is None:
        models = [
            "Seasonal_Naive_52",
            "Moving_Average_4",
            "Moving_Average_12",
            "Weighted_Moving_Average_12",
            "Simple_Exponential_Smoothing",
            "Holt_Linear_Trend"
        ]

    # Discover unique series
    unique_series = split.train_df[group_cols].drop_duplicates().to_dict(orient="records")
    series_keys = [f"{s['finished_sku_id']}:{s['market_id']}" for s in unique_series]
    test_horizon = split.test_weeks

    model_overall_perf: Dict[str, ForecastEvaluationMetrics] = {}
    all_forecast_records = []

    for model_name in models:
        all_actuals = []
        all_preds = []

        for s in unique_series:
            sku = s["finished_sku_id"]
            mkt = s["market_id"]

            # Filter series data
            tr_mask = (split.train_df["finished_sku_id"] == sku) & (split.train_df["market_id"] == mkt)
            te_mask = (split.test_df["finished_sku_id"] == sku) & (split.test_df["market_id"] == mkt)

            tr_series = split.train_df.loc[tr_mask].sort_values(by=date_col)[target_col]
            te_series = split.test_df.loc[te_mask].sort_values(by=date_col)[target_col]

            res = generate_series_forecast(
                train_series=tr_series,
                model_name=model_name,
                horizon_weeks=test_horizon,
                sku_id=sku,
                market_id=mkt,
                cutoff_date=split.train_end,
                test_actuals=te_series
            )

            all_actuals.extend(te_series.values[:test_horizon])
            all_preds.extend(res.forecast_quantities[:test_horizon])

            # Collect tabular forecast rows
            for dt, q in zip(res.target_weeks, res.forecast_quantities):
                all_forecast_records.append({
                    "model_name": model_name,
                    "finished_sku_id": sku,
                    "market_id": mkt,
                    "target_week": dt,
                    "forecast_quantity": q
                })

        # Aggregated cross-series performance metric
        model_overall_perf[model_name] = calculate_forecast_metrics(
            actuals=all_actuals,
            predictions=all_preds
        )

    # Determine champion model (lowest WAPE)
    best_model = min(models, key=lambda m: model_overall_perf[m].wape_pct)

    # Create summary DataFrame
    summary_rows = []
    for m in models:
        p = model_overall_perf[m]
        summary_rows.append({
            "model_name": m,
            "wape_pct": p.wape_pct,
            "mae": p.mae,
            "mape_pct": p.mape_pct,
            "rmse": p.rmse,
            "bias_pct": p.bias_pct,
            "tracking_signal": p.tracking_signal,
            "is_champion": (m == best_model)
        })
    summary_df = pd.DataFrame(summary_rows).sort_values(by="wape_pct").reset_index(drop=True)
    forecast_df = pd.DataFrame(all_forecast_records)

    return BaselineBenchmarkReport(
        evaluation_horizon_weeks=test_horizon,
        models_evaluated=models,
        series_evaluated=series_keys,
        model_performance=model_overall_perf,
        best_model_name=best_model,
        forecast_df=forecast_df,
        summary_df=summary_df
    )
