"""
Pharmaceutical Forecast Evaluation, Slice-and-Dice Analytics & Versioning Registry Engine.
Phase 2 (Day 23) Forecasting Layer Implementation.

Implements multi-dimensional forecast evaluation across products, markets, and horizon buckets,
tracking signal drift monitoring with automated statistical alarms (|TS| > 4.0),
version-to-version forecast waterfall variance analysis, and multi-version SQLite database persistence.
Strictly zero LLM mathematical calculations. Pure deterministic time-series evaluation.
"""

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from enum import Enum
from typing import List, Dict, Tuple, Optional, Any, Union
import math
import sqlite3
import numpy as np
import pandas as pd

from src.forecasting.baseline import (
    ForecastEvaluationMetrics,
    calculate_forecast_metrics
)
from src.models.planning import FactDemandForecast


# =============================================================================
# DATA CONTRACTS & ENUMS
# =============================================================================

class DriftAlarmSeverity(str, Enum):
    """Tracking signal statistical drift severity levels."""
    NORMAL = "NORMAL"
    WARNING = "WARNING"
    ALARM = "ALARM"


@dataclass(frozen=True)
class TrackingSignalPoint:
    """Sequential tracking signal monitoring point for a single weekly period."""
    target_week: date
    actual_demand: float
    forecast_demand: float
    period_error: float          # forecast - actual
    cumulative_error: float      # sum(forecast - actual)
    mean_absolute_deviation: float # cumulative MAD
    tracking_signal: float       # cumulative_error / MAD
    severity: DriftAlarmSeverity
    is_alarm: bool


@dataclass
class TrackingSignalAuditResult:
    """Consolidated tracking signal audit report for a time-series."""
    finished_sku_id: str
    market_id: str
    model_name: str
    total_periods_evaluated: int
    final_tracking_signal: float
    max_tracking_signal: float
    min_tracking_signal: float
    has_alarm: bool
    alarm_periods_count: int
    severity: DriftAlarmSeverity
    prescriptive_action: str
    points: List[TrackingSignalPoint] = field(default_factory=list)


@dataclass
class ForecastSliceMetrics:
    """Performance metrics for an individual dimensional slice (e.g. SKU, Market, Horizon)."""
    slice_dimension: str         # 'SKU', 'Market', 'Horizon_Bucket', 'SKU_x_Market'
    slice_key: str               # e.g. 'SKU-AUG-500-T10', 'MKT-IN-HYD', 'W01-W04'
    metrics: ForecastEvaluationMetrics
    total_actual_packs: float
    total_forecast_packs: float
    net_pack_variance: float


@dataclass
class ForecastSliceReport:
    """Multi-dimensional slice-and-dice evaluation scorecard."""
    model_name: str
    overall_metrics: ForecastEvaluationMetrics
    sku_slices: Dict[str, ForecastSliceMetrics]
    market_slices: Dict[str, ForecastSliceMetrics]
    horizon_slices: Dict[str, ForecastSliceMetrics]
    intersection_slices: Dict[str, ForecastSliceMetrics]
    summary_df: pd.DataFrame
    evaluation_timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def generate_markdown_summary(self) -> str:
        """Formats the multi-dimensional slice analysis into an executive Markdown report."""
        lines = [
            f"# Multi-Horizon Forecast Slice-and-Dice Scorecard ({self.model_name})",
            f"**Evaluation Timestamp:** {self.evaluation_timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}  ",
            f"**Overall Network Performance:** `{self.overall_metrics.wape_pct:.2f}%` WAPE | Bias: `{self.overall_metrics.bias_pct:+.2f}%` | MAE: `{self.overall_metrics.mae:.1f}` packs  ",
            "",
            "## 1. Dimensional Slice Breakdown",
            "",
            "| Dimension | Slice Key | WAPE % | MAE (Packs) | Bias % | Actual Total | Forecast Total | Volume Delta |",
            "|---|---|---|---|---|---|---|---|"
        ]

        for s in self.summary_df.to_dict(orient="records"):
            lines.append(
                f"| {s['dimension']} | **{s['slice_key']}** | {s['wape_pct']:.2f}% | "
                f"{s['mae']:.1f} | {s['bias_pct']:+.2f}% | {s['total_actual']:,.0f} | "
                f"{s['total_forecast']:,.0f} | {s['volume_delta']:+,.0f} |"
            )

        lines.extend([
            "",
            "## 2. Operational Observations",
            "- **Lead-Time Horizons:** Short-term horizon (Weeks 1–4) governs plant line changeovers and replenishment; medium-term (Weeks 5–12) dictates API sourcing.",
            "- **Bias Directionality:** Negative volume delta indicates potential stockout vulnerability; positive volume delta indicates inventory holding exposure."
        ])

        return "\n".join(lines)


@dataclass
class VersionVarianceItem:
    """Variance analysis for a single SKU x Market x Target Week point."""
    finished_sku_id: str
    market_id: str
    target_week: date
    base_forecast: float
    comparison_forecast: float
    variance_packs: float        # comparison - base
    variance_pct: float          # variance / base * 100
    is_material_shift: bool      # True if abs(variance_pct) > 20% or abs(variance) > 1000


@dataclass
class ForecastVersionComparisonReport:
    """Waterfall variance report comparing two forecast versions."""
    base_version_name: str
    comparison_version_name: str
    total_points_evaluated: int
    net_volumetric_shift_packs: float
    average_absolute_shift_packs: float
    overall_variance_pct: float
    material_shift_count: int
    has_critical_volatility: bool
    sku_summaries: Dict[str, Dict[str, float]]
    variances: List[VersionVarianceItem] = field(default_factory=list)
    evaluation_timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def generate_markdown_summary(self) -> str:
        """Formats the version comparison into an executive Markdown report."""
        status_tag = "⚠️ CRITICAL VOLATILITY" if self.has_critical_volatility else "✅ STABLE TRANSITION"
        lines = [
            f"# Forecast Version-to-Version Waterfall Report ({status_tag})",
            f"**Baseline Version:** `{self.base_version_name}`  ",
            f"**Comparison Version:** `{self.comparison_version_name}`  ",
            f"**Net Volumetric Shift:** `{self.net_volumetric_shift_packs:+,.1f}` packs ({self.overall_variance_pct:+.2f}%)  ",
            f"**Material Shifts Detected (>20% or >1,000 packs):** `{self.material_shift_count}` / {self.total_points_evaluated} points  ",
            "",
            "## 1. Product Family Shift Summary",
            "",
            "| Finished SKU | Base Volume | Comparison Volume | Net Shift (Packs) | Shift % |",
            "|---|---|---|---|---|"
        ]

        for sku, d in self.sku_summaries.items():
            lines.append(
                f"| **{sku}** | {d['base_total']:,.0f} | {d['comparison_total']:,.0f} | "
                f"{d['shift_packs']:+,.0f} | {d['shift_pct']:+.2f}% |"
            )

        return "\n".join(lines)


# =============================================================================
# 1. MULTI-HORIZON SLICE-AND-DICE EVALUATION ENGINE
# =============================================================================

def evaluate_forecast_slices(
    evaluation_df: pd.DataFrame,
    actual_col: str = "actual_demand",
    forecast_col: str = "forecast_quantity",
    date_col: str = "target_week",
    sku_col: str = "finished_sku_id",
    market_col: str = "market_id",
    model_name: str = "Candidate_Model"
) -> ForecastSliceReport:
    """
    Computes deterministic forecast error metrics across multiple operational slices:
    1. Overall Network Total
    2. By Product SKU
    3. By Regional Market
    4. By Planning Horizon Buckets:
       - Weeks 1–4 (Operational lead-time bucket)
       - Weeks 5–12 (Tactical production planning bucket)
       - Weeks 13–26 (Strategic capacity bucket)
    5. By SKU x Market Intersection
    """
    df = evaluation_df.copy()
    df[date_col] = pd.to_datetime(df[date_col])

    # 1. Overall Metrics
    overall_metrics = calculate_forecast_metrics(df[actual_col], df[forecast_col])

    summary_rows = []

    def build_slice(sub_df: pd.DataFrame, dim_name: str, key: str) -> ForecastSliceMetrics:
        metrics = calculate_forecast_metrics(sub_df[actual_col], sub_df[forecast_col])
        tot_act = float(sub_df[actual_col].sum())
        tot_fc = float(sub_df[forecast_col].sum())
        delta = tot_fc - tot_act

        summary_rows.append({
            "dimension": dim_name,
            "slice_key": key,
            "wape_pct": metrics.wape_pct,
            "mae": metrics.mae,
            "mape_pct": metrics.mape_pct,
            "rmse": metrics.rmse,
            "bias_pct": metrics.bias_pct,
            "total_actual": tot_act,
            "total_forecast": tot_fc,
            "volume_delta": delta
        })

        return ForecastSliceMetrics(
            slice_dimension=dim_name,
            slice_key=key,
            metrics=metrics,
            total_actual_packs=tot_act,
            total_forecast_packs=tot_fc,
            net_pack_variance=delta
        )

    # 2. Product SKU Slices
    sku_slices = {}
    for sku in df[sku_col].unique():
        sub = df[df[sku_col] == sku]
        sku_slices[sku] = build_slice(sub, "SKU", sku)

    # 3. Market Slices
    market_slices = {}
    for mkt in df[market_col].unique():
        sub = df[df[market_col] == mkt]
        market_slices[mkt] = build_slice(sub, "Market", mkt)

    # 4. Horizon Bucket Slices
    horizon_slices = {}
    sorted_dates = sorted(df[date_col].drop_duplicates())
    date_to_idx = {d: i + 1 for i, d in enumerate(sorted_dates)}
    df["horizon_week_idx"] = df[date_col].map(date_to_idx)

    # Bucket 1: Weeks 1-4
    b1_mask = df["horizon_week_idx"].between(1, 4)
    if b1_mask.any():
        horizon_slices["W01-W04"] = build_slice(df[b1_mask], "Horizon", "Weeks 01-04 (Lead Time)")

    # Bucket 2: Weeks 5-12
    b2_mask = df["horizon_week_idx"].between(5, 12)
    if b2_mask.any():
        horizon_slices["W05-W12"] = build_slice(df[b2_mask], "Horizon", "Weeks 05-12 (Tactical)")

    # Bucket 3: Weeks 13-26
    b3_mask = df["horizon_week_idx"] >= 13
    if b3_mask.any():
        horizon_slices["W13-W26"] = build_slice(df[b3_mask], "Horizon", "Weeks 13-26 (Strategic)")

    # 5. SKU x Market Intersection Slices
    intersection_slices = {}
    for (sku, mkt), sub in df.groupby([sku_col, market_col]):
        key = f"{sku} @ {mkt}"
        intersection_slices[key] = build_slice(sub, "SKU_x_Market", key)

    summary_df = pd.DataFrame(summary_rows)

    return ForecastSliceReport(
        model_name=model_name,
        overall_metrics=overall_metrics,
        sku_slices=sku_slices,
        market_slices=market_slices,
        horizon_slices=horizon_slices,
        intersection_slices=intersection_slices,
        summary_df=summary_df
    )


# =============================================================================
# 2. TRACKING SIGNAL & STATISTICAL DRIFT MONITOR
# =============================================================================

def evaluate_tracking_signal_drift(
    df: pd.DataFrame,
    actual_col: str = "actual_demand",
    forecast_col: str = "forecast_quantity",
    date_col: str = "target_week",
    sku_id: str = "SKU-AUG-500-T10",
    market_id: str = "MKT-IN-HYD",
    model_name: str = "Candidate_Model",
    alarm_threshold: float = 4.0,
    warning_threshold: float = 3.0
) -> TrackingSignalAuditResult:
    """
    Computes sequential tracking signal over time and triggers automated drift alarms.
    
    Formula:
    Period Error: e_t = forecast_t - actual_t
    Cumulative Error: CE_t = sum_{i=1}^t e_i
    Cumulative MAD: MAD_t = (1/t) sum_{i=1}^t |e_i|
    Tracking Signal: TS_t = CE_t / MAD_t
    
    Industrial Alarms:
    |TS| <= 3.0: NORMAL
    3.0 < |TS| <= 4.0: WARNING (Emerging directional bias)
    |TS| > 4.0: ALARM (Statistically significant persistent drift -> Model Recalibration Required)
    """
    sorted_df = df.sort_values(by=date_col).copy().reset_index(drop=True)
    if sorted_df.empty:
        raise ValueError("Cannot audit tracking signal on empty dataframe")

    points: List[TrackingSignalPoint] = []
    cumulative_error = 0.0
    cumulative_abs_error = 0.0
    alarm_count = 0

    ts_values = []

    for t, row in sorted_df.iterrows():
        act = float(row[actual_col])
        fc = float(row[forecast_col])
        err = fc - act
        abs_err = abs(err)

        cumulative_error += err
        cumulative_abs_error += abs_err

        mad = cumulative_abs_error / (t + 1)
        ts = cumulative_error / max(1e-4, mad)
        ts_values.append(ts)

        abs_ts = abs(ts)
        if abs_ts > alarm_threshold:
            severity = DriftAlarmSeverity.ALARM
            is_alarm = True
            alarm_count += 1
        elif abs_ts > warning_threshold:
            severity = DriftAlarmSeverity.WARNING
            is_alarm = False
        else:
            severity = DriftAlarmSeverity.NORMAL
            is_alarm = False

        target_dt = pd.to_datetime(row[date_col]).date()
        points.append(TrackingSignalPoint(
            target_week=target_dt,
            actual_demand=act,
            forecast_demand=fc,
            period_error=round(err, 1),
            cumulative_error=round(cumulative_error, 1),
            mean_absolute_deviation=round(mad, 2),
            tracking_signal=round(ts, 2),
            severity=severity,
            is_alarm=is_alarm
        ))

    final_ts = ts_values[-1]
    max_ts = max(ts_values)
    min_ts = min(ts_values)

    # Determine overall status and prescriptive recommendation
    if abs(final_ts) > alarm_threshold or alarm_count >= 2:
        overall_severity = DriftAlarmSeverity.ALARM
        has_alarm = True
        if final_ts > 0:
            action = "CRITICAL_DRIFT: Persistent Over-Forecasting detected. Recalibrate baseline and reduce channel inventory buffers."
        else:
            action = "CRITICAL_DRIFT: Persistent Under-Forecasting detected. Recalibrate model and increase safety stock to prevent stockouts."
    elif abs(final_ts) > warning_threshold:
        overall_severity = DriftAlarmSeverity.WARNING
        has_alarm = False
        action = "WARNING: Emerging directional drift. Monitor upcoming weekly sales orders closely."
    else:
        overall_severity = DriftAlarmSeverity.NORMAL
        has_alarm = False
        action = "COMPLIANT: Tracking signal centered within normal statistical bounds (|TS| <= 3.0)."

    return TrackingSignalAuditResult(
        finished_sku_id=sku_id,
        market_id=market_id,
        model_name=model_name,
        total_periods_evaluated=len(sorted_df),
        final_tracking_signal=round(final_ts, 2),
        max_tracking_signal=round(max_ts, 2),
        min_tracking_signal=round(min_ts, 2),
        has_alarm=has_alarm,
        alarm_periods_count=alarm_count,
        severity=overall_severity,
        prescriptive_action=action,
        points=points
    )


# =============================================================================
# 3. VERSION-TO-VERSION WATERFALL & VARIANCE ANALYSIS
# =============================================================================

def analyze_forecast_version_variance(
    base_df: pd.DataFrame,
    comparison_df: pd.DataFrame,
    base_version_name: str = "Base_Version",
    comparison_version_name: str = "Comparison_Version",
    material_shift_pct_threshold: float = 20.0,
    material_shift_vol_threshold: float = 1000.0
) -> ForecastVersionComparisonReport:
    """
    Executes a deterministic version-to-version waterfall variance analysis:
    Delta = Forecast(Comparison) - Forecast(Base)
    Identifies material shifts (>20% or >1000 packs) that could disrupt supply chain operations.
    """
    key_cols = ["finished_sku_id", "market_id", "target_week"]
    b_df = base_df[key_cols + ["forecast_quantity"]].copy()
    c_df = comparison_df[key_cols + ["forecast_quantity"]].copy()

    b_df["target_week"] = pd.to_datetime(b_df["target_week"]).dt.date
    c_df["target_week"] = pd.to_datetime(c_df["target_week"]).dt.date

    merged = pd.merge(
        b_df,
        c_df,
        on=key_cols,
        suffixes=("_base", "_comp"),
        how="inner"
    )

    if merged.empty:
        raise ValueError("No matching SKU x Market x Target Week points found between versions")

    variances: List[VersionVarianceItem] = []
    material_count = 0
    tot_base = 0.0
    tot_comp = 0.0

    sku_totals: Dict[str, Dict[str, float]] = {}

    for _, row in merged.iterrows():
        sku = str(row["finished_sku_id"])
        mkt = str(row["market_id"])
        dt = row["target_week"]
        y_b = float(row["forecast_quantity_base"])
        y_c = float(row["forecast_quantity_comp"])

        var_packs = y_c - y_b
        var_pct = (var_packs / max(1.0, y_b)) * 100.0

        is_material = (abs(var_pct) > material_shift_pct_threshold) or (abs(var_packs) > material_shift_vol_threshold)
        if is_material:
            material_count += 1

        tot_base += y_b
        tot_comp += y_c

        # SKU rollup
        if sku not in sku_totals:
            sku_totals[sku] = {"base_total": 0.0, "comparison_total": 0.0}
        sku_totals[sku]["base_total"] += y_b
        sku_totals[sku]["comparison_total"] += y_c

        variances.append(VersionVarianceItem(
            finished_sku_id=sku,
            market_id=mkt,
            target_week=dt,
            base_forecast=y_b,
            comparison_forecast=y_c,
            variance_packs=round(var_packs, 1),
            variance_pct=round(var_pct, 2),
            is_material_shift=is_material
        ))

    for sku in sku_totals:
        b_tot = sku_totals[sku]["base_total"]
        c_tot = sku_totals[sku]["comparison_total"]
        shift = c_tot - b_tot
        shift_pct = (shift / max(1.0, b_tot)) * 100.0
        sku_totals[sku]["shift_packs"] = round(shift, 1)
        sku_totals[sku]["shift_pct"] = round(shift_pct, 2)

    net_shift = tot_comp - tot_base
    net_pct = (net_shift / max(1.0, tot_base)) * 100.0
    avg_abs_shift = float(np.mean([abs(v.variance_packs) for v in variances]))
    has_critical = (material_count / len(variances)) > 0.25  # More than 25% of points material

    return ForecastVersionComparisonReport(
        base_version_name=base_version_name,
        comparison_version_name=comparison_version_name,
        total_points_evaluated=len(variances),
        net_volumetric_shift_packs=round(net_shift, 1),
        average_absolute_shift_packs=round(avg_abs_shift, 1),
        overall_variance_pct=round(net_pct, 2),
        material_shift_count=material_count,
        has_critical_volatility=has_critical,
        sku_summaries=sku_totals,
        variances=variances
    )


# =============================================================================
# 4. MULTI-VERSION FORECAST REGISTRY & DATABASE STORE
# =============================================================================

class ForecastRegistry:
    """
    Manages versioned forecast persistence, query, and comparison in SQLite fact_demand_forecast.
    """
    def __init__(self, db_conn_or_path: Union[sqlite3.Connection, str] = "data/processed/control_tower.db"):
        self.is_internal_conn = False
        if isinstance(db_conn_or_path, str):
            self.conn = sqlite3.connect(db_conn_or_path)
            self.is_internal_conn = True
        else:
            self.conn = db_conn_or_path

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def close(self):
        if self.is_internal_conn:
            self.conn.close()

    def list_registered_versions(self) -> List[Dict[str, Any]]:
        """Queries database for distinct model versions, version dates, and record counts."""
        query = (
            "SELECT model_version, forecast_version_date, scenario_id, COUNT(*) as record_count, "
            "MIN(target_week) as min_target_week, MAX(target_week) as max_target_week "
            "FROM fact_demand_forecast "
            "GROUP BY model_version, forecast_version_date, scenario_id "
            "ORDER BY forecast_version_date DESC, model_version"
        )
        df = pd.read_sql_query(query, self.conn)
        return df.to_dict(orient="records")

    def load_forecast_version(
        self,
        model_version: str,
        scenario_id: str = "SCN-BASE"
    ) -> pd.DataFrame:
        """Loads a specific forecast version from fact_demand_forecast."""
        query = (
            "SELECT * FROM fact_demand_forecast "
            "WHERE model_version = ? AND scenario_id = ? "
            "ORDER BY finished_sku_id, market_id, target_week"
        )
        return pd.read_sql_query(query, self.conn, params=[model_version, scenario_id])

    def save_forecast_version(
        self,
        forecast_df: pd.DataFrame,
        overwrite: bool = True
    ) -> int:
        """
        Registers a new forecast version into SQLite fact_demand_forecast.
        Validates columns against schema before writing.
        """
        required_cols = [
            "forecast_id", "forecast_version_date", "target_week", "finished_sku_id",
            "market_id", "forecast_quantity", "lower_bound", "upper_bound",
            "model_version", "scenario_id"
        ]
        for c in required_cols:
            if c not in forecast_df.columns:
                raise ValueError(f"Missing required forecast column: {c}")

        model_version = str(forecast_df["model_version"].iloc[0])
        scenario_id = str(forecast_df["scenario_id"].iloc[0])

        cur = self.conn.cursor()
        if overwrite:
            cur.execute(
                "DELETE FROM fact_demand_forecast WHERE model_version = ? AND scenario_id = ?",
                [model_version, scenario_id]
            )

        # Prepare write dataframe
        write_cols = required_cols + ["override_quantity"] if "override_quantity" in forecast_df.columns else required_cols
        write_df = forecast_df[write_cols].copy()

        write_df.to_sql("fact_demand_forecast", self.conn, if_exists="append", index=False)
        self.conn.commit()
        return len(write_df)
