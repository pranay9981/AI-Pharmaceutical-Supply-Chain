"""
Pharmaceutical Demand Anomaly Detection & Downstream Supply Chain Impact Propagation Engine.
Phase 2 (Day 24) Forecasting Layer Implementation.

Implements statistical demand anomaly detection (Rolling Volatility-Adjusted Z-Score, Non-Parametric IQR Fences),
structural step-change drift detection, cross-market channel distortion identification, and
deterministic downstream supply chain impact propagation (safety stock depletion, stockout exposure,
inventory aging/expiry risk, and financial exposure estimation).
Strictly zero LLM mathematical calculations. Pure deterministic time-series analytics.
"""

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from enum import Enum
from typing import List, Dict, Tuple, Optional, Any, Union
import math
import numpy as np
import pandas as pd


# =============================================================================
# DATA CONTRACTS & ENUMS
# =============================================================================

class AnomalyType(str, Enum):
    """Categorization of commercial demand anomaly phenomena."""
    NORMAL = "NORMAL"
    DEMAND_SURGE = "DEMAND_SURGE"          # Sudden spike (epidemic, outbreak, hoarding, tender win)
    DEMAND_PLUNGE = "DEMAND_PLUNGE"        # Sudden drop (recall, safety warning, competitor entry, tender loss)
    STRUCTURAL_SHIFT = "STRUCTURAL_SHIFT"  # Persistent change in base velocity / step-change
    CHANNEL_DISTORTION = "CHANNEL_DISTORTION" # Localized channel/market imbalance vs network


class AnomalySeverity(str, Enum):
    """Operational urgency and statistical magnitude of the anomaly."""
    NORMAL = "NORMAL"      # |Z| < 2.0 and within IQR
    LOW = "LOW"            # 2.0 <= |Z| < 2.5 or marginal IQR breach
    MEDIUM = "MEDIUM"      # 2.5 <= |Z| < 3.5
    HIGH = "HIGH"          # 3.5 <= |Z| < 5.0
    CRITICAL = "CRITICAL"  # |Z| >= 5.0 or > 200% baseline deviation


@dataclass(frozen=True)
class DownstreamSupplyImpact:
    """Deterministic propagation of demand anomaly into supply chain operations."""
    days_of_supply_delta: float           # Change in available days of forward supply (+ excess, - deficit)
    safety_stock_depleted_pct: float      # Estimated percentage of regional safety stock consumed
    stockout_risk_flag: bool              # True if surge breaches buffer and poses stockout danger
    expiry_risk_flag: bool                # True if plunge creates excess holding and aging/expiry danger
    estimated_financial_exposure_usd: float # Estimated financial exposure (lost sales or holding/write-off)
    recommended_action: str               # Prescriptive operational directive for supply planner


@dataclass
class DemandAnomalyRecord:
    """Individual observation evaluation record with statistical metrics and impact analysis."""
    observation_date: date
    finished_sku_id: str
    market_id: str
    actual_demand: float
    expected_demand: float                # Rolling baseline mean or model forecast
    residual: float                       # actual - expected
    z_score: float                        # (actual - mean) / std
    iqr_lower: float                      # Q1 - k * IQR
    iqr_upper: float                      # Q3 + k * IQR
    anomaly_type: AnomalyType
    severity: AnomalySeverity
    detection_method: str                 # "Z_SCORE", "IQR", "STRUCTURAL_SHIFT", "COMBINED"
    is_anomaly: bool
    downstream_impact: Optional[DownstreamSupplyImpact] = None
    context_notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Serializes record to plain dictionary for JSON/logging."""
        return {
            "observation_date": str(self.observation_date),
            "finished_sku_id": self.finished_sku_id,
            "market_id": self.market_id,
            "actual_demand": round(float(self.actual_demand), 2),
            "expected_demand": round(float(self.expected_demand), 2),
            "residual": round(float(self.residual), 2),
            "z_score": round(float(self.z_score), 4),
            "iqr_lower": round(float(self.iqr_lower), 2),
            "iqr_upper": round(float(self.iqr_upper), 2),
            "anomaly_type": self.anomaly_type.value,
            "severity": self.severity.value,
            "detection_method": self.detection_method,
            "is_anomaly": self.is_anomaly,
            "context_notes": self.context_notes,
            "days_of_supply_delta": round(float(self.downstream_impact.days_of_supply_delta), 1) if self.downstream_impact else 0.0,
            "safety_stock_depleted_pct": round(float(self.downstream_impact.safety_stock_depleted_pct), 1) if self.downstream_impact else 0.0,
            "stockout_risk_flag": self.downstream_impact.stockout_risk_flag if self.downstream_impact else False,
            "expiry_risk_flag": self.downstream_impact.expiry_risk_flag if self.downstream_impact else False,
            "estimated_financial_exposure_usd": round(float(self.downstream_impact.estimated_financial_exposure_usd), 2) if self.downstream_impact else 0.0,
            "recommended_action": self.downstream_impact.recommended_action if self.downstream_impact else "NO_ACTION"
        }


@dataclass
class AnomalySummaryByDimension:
    """Aggregated anomaly metrics by SKU or Market partition."""
    dimension_key: str
    total_observations: int
    anomaly_count: int
    surge_count: int
    plunge_count: int
    shift_count: int
    distortion_count: int
    critical_count: int
    max_z_score: float
    total_financial_exposure_usd: float


@dataclass
class AnomalyDetectionReport:
    """Executive network-wide demand anomaly detection report."""
    total_observations: int
    total_anomalies: int
    surge_count: int
    plunge_count: int
    shift_count: int
    distortion_count: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    records: List[DemandAnomalyRecord]
    anomalies: List[DemandAnomalyRecord]
    summary_by_sku: Dict[str, AnomalySummaryByDimension]
    summary_by_market: Dict[str, AnomalySummaryByDimension]
    total_network_exposure_usd: float
    executive_summary: str

    def to_dataframe(self) -> pd.DataFrame:
        """Converts anomaly records to pandas DataFrame for audit/analytics."""
        return pd.DataFrame([r.to_dict() for r in self.records])


# =============================================================================
# DEFAULT PHARMACEUTICAL REFERENCE PARAMETERS
# =============================================================================

DEFAULT_SKU_PRICES: Dict[str, float] = {
    "SKU-AUG-500-T10": 12.50,  # Amoxicillin-Clav 500/125mg 10-pack blister
    "SKU-AUG-500-T30": 32.00,  # Amoxicillin-Clav 500/125mg 30-pack bottle
}
DEFAULT_HOLDING_COST_RATE: float = 0.20  # 20% annual carrying/depreciation cost
DEFAULT_MIN_SHELF_LIFE_DAYS: int = 730   # 24 months


# =============================================================================
# DOWNSTREAM IMPACT PROPAGATION
# =============================================================================

def assess_downstream_impact(
    anomaly_type: AnomalyType,
    actual_demand: float,
    expected_demand: float,
    finished_sku_id: str = "SKU-AUG-500-T10",
    current_inventory_packs: Optional[float] = None,
    weekly_burn_rate: Optional[float] = None,
    safety_stock_buffer_packs: Optional[float] = None,
    unit_price_usd: Optional[float] = None
) -> DownstreamSupplyImpact:
    """
    Deterministically computes downstream operational consequences of a demand anomaly.
    Evaluates safety stock consumption, forward days of supply shift, stockout/expiry risk flags,
    financial exposure, and generates a prescriptive operational directive.
    """
    price = unit_price_usd if unit_price_usd is not None else DEFAULT_SKU_PRICES.get(finished_sku_id, 15.00)
    expected = max(1.0, float(expected_demand))
    actual = max(0.0, float(actual_demand))
    residual = actual - expected

    # Baseline daily consumption rate
    daily_rate = expected / 7.0

    # Default safety stock is typically ~2 weeks of expected demand
    ss_buffer = safety_stock_buffer_packs if safety_stock_buffer_packs is not None else (expected * 2.0)
    ss_buffer = max(1.0, ss_buffer)

    # Default inventory on hand is typically ~4 weeks of expected demand
    inv_on_hand = current_inventory_packs if current_inventory_packs is not None else (expected * 4.0)

    if anomaly_type == AnomalyType.NORMAL:
        return DownstreamSupplyImpact(
            days_of_supply_delta=0.0,
            safety_stock_depleted_pct=0.0,
            stockout_risk_flag=False,
            expiry_risk_flag=False,
            estimated_financial_exposure_usd=0.0,
            recommended_action="NORMAL_CADENCE: Continue standard production and distribution schedules."
        )

    elif anomaly_type == AnomalyType.DEMAND_SURGE:
        # Surge consumes safety stock and shortens days of supply
        excess_packs = residual
        days_delta = - (excess_packs / daily_rate)
        ss_depleted_pct = min(100.0, max(0.0, (excess_packs / ss_buffer) * 100.0))
        
        # Remaining forward inventory after this surge
        remaining_inv = max(0.0, inv_on_hand - actual)
        forward_days_left = remaining_inv / daily_rate
        stockout_risk = forward_days_left < 14.0 or ss_depleted_pct >= 80.0

        # Financial exposure: potential lost sales / penalty revenue if unfulfilled
        exposure_usd = excess_packs * price

        action = (
            f"EXPEDITE_REPLENISHMENT: Demand surge of +{int(excess_packs):,} packs depleted "
            f"{ss_depleted_pct:.1f}% of regional safety stock. Expedite packaging batch on primary line "
            f"and verify active API inventory at Formulation Plant."
        )

        return DownstreamSupplyImpact(
            days_of_supply_delta=days_delta,
            safety_stock_depleted_pct=ss_depleted_pct,
            stockout_risk_flag=stockout_risk,
            expiry_risk_flag=False,
            estimated_financial_exposure_usd=exposure_usd,
            recommended_action=action
        )

    elif anomaly_type == AnomalyType.DEMAND_PLUNGE:
        # Plunge builds excess stock, lengthening days of supply and elevating expiry risk
        unconsumed_packs = abs(residual)
        days_delta = (unconsumed_packs / daily_rate)
        
        # New inventory level is higher than projected
        projected_inv = inv_on_hand + unconsumed_packs
        forward_days_accumulated = projected_inv / daily_rate
        expiry_risk = forward_days_accumulated > 90.0

        # Financial exposure: annual inventory holding and obsolescence risk
        exposure_usd = unconsumed_packs * price * DEFAULT_HOLDING_COST_RATE

        action = (
            f"THROTTLE_PRODUCTION: Demand collapse of -{int(unconsumed_packs):,} packs created "
            f"+{days_delta:.1f} days of excess pipeline inventory. Pause planned production lot release, "
            f"inspect regional hospital tender status, and audit quality recall logs."
        )

        return DownstreamSupplyImpact(
            days_of_supply_delta=days_delta,
            safety_stock_depleted_pct=0.0,
            stockout_risk_flag=False,
            expiry_risk_flag=expiry_risk,
            estimated_financial_exposure_usd=exposure_usd,
            recommended_action=action
        )

    elif anomaly_type == AnomalyType.STRUCTURAL_SHIFT:
        direction = "upward" if residual > 0 else "downward"
        pct_shift = (residual / expected) * 100.0
        exposure_usd = abs(residual) * price * 0.5

        action = (
            f"REBASELINE_MRP: Persistent {direction} step-change ({pct_shift:+.1f}%) detected. "
            f"Re-baseline safety stock levels and re-optimize (s, S) min-max reorder policies in MRP engine."
        )

        return DownstreamSupplyImpact(
            days_of_supply_delta=- (residual / daily_rate),
            safety_stock_depleted_pct=50.0 if residual > 0 else 0.0,
            stockout_risk_flag=residual > 0 and (inv_on_hand / daily_rate) < 21.0,
            expiry_risk_flag=residual < 0 and (inv_on_hand / daily_rate) > 60.0,
            estimated_financial_exposure_usd=exposure_usd,
            recommended_action=action
        )

    elif anomaly_type == AnomalyType.CHANNEL_DISTORTION:
        exposure_usd = abs(residual) * price * 0.3
        action = (
            f"INTER_DC_REBALANCE: Regional channel skew detected. Transship inventory between "
            f"Hyderabad Central DC and Pune Regional DC to restore target safety stock equilibrium."
        )

        return DownstreamSupplyImpact(
            days_of_supply_delta=0.0,
            safety_stock_depleted_pct=30.0 if residual > 0 else 0.0,
            stockout_risk_flag=False,
            expiry_risk_flag=False,
            estimated_financial_exposure_usd=exposure_usd,
            recommended_action=action
        )

    # Fallback
    return DownstreamSupplyImpact(
        days_of_supply_delta=0.0,
        safety_stock_depleted_pct=0.0,
        stockout_risk_flag=False,
        expiry_risk_flag=False,
        estimated_financial_exposure_usd=0.0,
        recommended_action="MONITOR: Maintain standard operational monitoring."
    )


# =============================================================================
# STATISTICAL EVALUATION FUNCTIONS
# =============================================================================

def evaluate_point_anomaly(
    current_val: float,
    historical_series: Union[List[float], np.ndarray, pd.Series],
    observation_date: Union[date, str, datetime] = date(2026, 1, 1),
    finished_sku_id: str = "SKU-AUG-500-T10",
    market_id: str = "MKT-IN-HYD",
    z_threshold: float = 3.0,
    iqr_multiplier: float = 1.5,
    min_periods: int = 4,
    current_inventory_packs: Optional[float] = None
) -> DemandAnomalyRecord:
    """
    Evaluates a single demand observation point against a historical window.
    Calculates rolling Z-score and Tukey's IQR fences.
    Assigns anomaly classification, severity grade, and downstream impact.
    """
    if isinstance(observation_date, str):
        obs_date = datetime.strptime(observation_date, "%Y-%m-%d").date()
    elif isinstance(observation_date, datetime):
        obs_date = observation_date.date()
    else:
        obs_date = observation_date

    # Clean and filter historical values
    hist = np.array(historical_series, dtype=float)
    hist = hist[~np.isnan(hist)]

    cur = float(current_val)

    if len(hist) < min_periods:
        # Insufficient data to reliably declare an anomaly
        return DemandAnomalyRecord(
            observation_date=obs_date,
            finished_sku_id=finished_sku_id,
            market_id=market_id,
            actual_demand=cur,
            expected_demand=cur,
            residual=0.0,
            z_score=0.0,
            iqr_lower=cur,
            iqr_upper=cur,
            anomaly_type=AnomalyType.NORMAL,
            severity=AnomalySeverity.NORMAL,
            detection_method="INSUFFICIENT_HISTORY",
            is_anomaly=False,
            downstream_impact=assess_downstream_impact(
                AnomalyType.NORMAL, cur, cur, finished_sku_id
            ),
            context_notes=f"Insufficient history ({len(hist)} < {min_periods} periods)."
        )

    # Compute baseline statistics
    mean_val = float(np.mean(hist))
    std_val = float(np.std(hist, ddof=1)) if len(hist) > 1 else 0.0

    # Non-parametric IQR bounds
    q25 = float(np.percentile(hist, 25))
    q75 = float(np.percentile(hist, 75))
    iqr = max(0.0, q75 - q25)
    iqr_lower = max(0.0, q25 - iqr_multiplier * iqr)
    iqr_upper = q75 + iqr_multiplier * iqr

    # Compute Volatility-Adjusted Z-Score
    residual = cur - mean_val
    if std_val > 1e-6:
        z_score = residual / std_val
    else:
        # Constant historical series: fallback to relative deviation
        if abs(residual) < 1e-6:
            z_score = 0.0
        else:
            base = max(mean_val, 1.0)
            rel_diff = residual / base
            # If relative diff is >= 20%, map to scaled z-score
            z_score = rel_diff * 10.0

    # Detect Outliers
    z_outlier = abs(z_score) >= z_threshold
    iqr_outlier = (cur < iqr_lower) or (cur > iqr_upper)

    is_anomaly = False
    anomaly_type = AnomalyType.NORMAL
    detection_method = "NORMAL"

    if z_outlier or iqr_outlier:
        is_anomaly = True
        if z_outlier and iqr_outlier:
            detection_method = "COMBINED_Z_IQR"
        elif z_outlier:
            detection_method = "Z_SCORE"
        else:
            detection_method = "IQR_FENCE"

        if cur > mean_val:
            anomaly_type = AnomalyType.DEMAND_SURGE
        else:
            anomaly_type = AnomalyType.DEMAND_PLUNGE

    # Determine Severity Grade
    abs_z = abs(z_score)
    pct_deviation = abs(residual) / max(mean_val, 1.0)

    if not is_anomaly:
        severity = AnomalySeverity.NORMAL
    elif abs_z >= 5.0 or pct_deviation >= 2.0:
        severity = AnomalySeverity.CRITICAL
    elif abs_z >= 3.5 or pct_deviation >= 1.0:
        severity = AnomalySeverity.HIGH
    elif abs_z >= 2.5:
        severity = AnomalySeverity.MEDIUM
    else:
        severity = AnomalySeverity.LOW

    # Assess Downstream Impact
    impact = assess_downstream_impact(
        anomaly_type=anomaly_type,
        actual_demand=cur,
        expected_demand=mean_val,
        finished_sku_id=finished_sku_id,
        current_inventory_packs=current_inventory_packs
    )

    notes = ""
    if is_anomaly:
        notes = (
            f"{anomaly_type.value} ({severity.value}): actual {cur:,.0f} vs expected {mean_val:,.0f} "
            f"(Z={z_score:+.2f}, IQR bounds [{iqr_lower:,.0f}, {iqr_upper:,.0f}])."
        )

    return DemandAnomalyRecord(
        observation_date=obs_date,
        finished_sku_id=finished_sku_id,
        market_id=market_id,
        actual_demand=cur,
        expected_demand=mean_val,
        residual=residual,
        z_score=z_score,
        iqr_lower=iqr_lower,
        iqr_upper=iqr_upper,
        anomaly_type=anomaly_type,
        severity=severity,
        detection_method=detection_method,
        is_anomaly=is_anomaly,
        downstream_impact=impact,
        context_notes=notes
    )


def detect_structural_shift(
    series: Union[List[float], np.ndarray, pd.Series],
    short_window: int = 4,
    long_window: int = 12,
    threshold_pct: float = 0.35
) -> Tuple[bool, float, float, float]:
    """
    Detects persistent step-changes in mean demand between a recent short window
    and the preceding baseline window.
    Returns: (is_shift, short_mean, long_mean, pct_change)
    """
    arr = np.array(series, dtype=float)
    arr = arr[~np.isnan(arr)]
    total_needed = short_window + long_window

    if len(arr) < total_needed:
        return False, 0.0, 0.0, 0.0

    recent_part = arr[-short_window:]
    baseline_part = arr[-total_needed:-short_window]

    short_mean = float(np.mean(recent_part))
    long_mean = float(np.mean(baseline_part))

    if long_mean < 1e-6:
        pct_change = 0.0 if short_mean < 1e-6 else 1.0
    else:
        pct_change = (short_mean - long_mean) / long_mean

    is_shift = abs(pct_change) >= threshold_pct
    return is_shift, short_mean, long_mean, pct_change


# =============================================================================
# TIME-SERIES BATCH ANOMALY DETECTION
# =============================================================================

def detect_series_anomalies(
    df: pd.DataFrame,
    date_col: str = "week_start_date",
    value_col: str = "demand_quantity",
    sku_col: str = "finished_sku_id",
    market_col: str = "market_id",
    window: int = 12,
    z_threshold: float = 3.0,
    iqr_multiplier: float = 1.5,
    min_periods: int = 4,
    check_structural_shift: bool = True
) -> List[DemandAnomalyRecord]:
    """
    Executes sequential, backward-looking rolling anomaly detection over a single time-series.
    Strictly avoids future target contamination: period t is evaluated against periods [t-window, t-1].
    """
    if df.empty:
        return []

    sorted_df = df.sort_values(by=date_col).copy()
    dates = pd.to_datetime(sorted_df[date_col]).dt.date.tolist()
    values = sorted_df[value_col].astype(float).values
    sku_id = sorted_df[sku_col].iloc[0] if sku_col in sorted_df.columns else "UNKNOWN_SKU"
    mkt_id = sorted_df[market_col].iloc[0] if market_col in sorted_df.columns else "UNKNOWN_MKT"

    records: List[DemandAnomalyRecord] = []
    n = len(values)

    for i in range(n):
        cur_val = values[i]
        cur_date = dates[i]

        # Strictly backward-looking window
        start_idx = max(0, i - window)
        history = values[start_idx:i]

        rec = evaluate_point_anomaly(
            current_val=cur_val,
            historical_series=history,
            observation_date=cur_date,
            finished_sku_id=sku_id,
            market_id=mkt_id,
            z_threshold=z_threshold,
            iqr_multiplier=iqr_multiplier,
            min_periods=min_periods
        )

        # Check for structural shift if at least 16 periods of history exist
        if check_structural_shift and i >= 16:
            full_hist = values[max(0, i - 16):i + 1]
            is_shift, s_mean, l_mean, pct_chg = detect_structural_shift(
                full_hist, short_window=4, long_window=12, threshold_pct=0.35
            )
            # If a structural shift is confirmed and current observation is an anomaly or strong shift
            if is_shift and (rec.is_anomaly or abs(pct_chg) >= 0.40):
                rec.anomaly_type = AnomalyType.STRUCTURAL_SHIFT
                rec.detection_method = "STRUCTURAL_SHIFT"
                rec.is_anomaly = True
                rec.context_notes = (
                    f"Structural shift: 4-wk mean {s_mean:,.0f} shifted {pct_chg:+.1f}% "
                    f"vs 12-wk baseline {l_mean:,.0f}."
                )
                rec.downstream_impact = assess_downstream_impact(
                    anomaly_type=AnomalyType.STRUCTURAL_SHIFT,
                    actual_demand=cur_val,
                    expected_demand=l_mean,
                    finished_sku_id=sku_id
                )

        records.append(rec)

    return records


# =============================================================================
# NETWORK-WIDE DEMAND ANOMALY SCANNER
# =============================================================================

def detect_network_demand_anomalies(
    demand_df: pd.DataFrame,
    date_col: str = "week_start_date",
    sku_col: str = "finished_sku_id",
    market_col: str = "market_id",
    value_col: str = "demand_quantity",
    window: int = 12,
    z_threshold: float = 3.0,
    iqr_multiplier: float = 1.5,
    min_periods: int = 4
) -> AnomalyDetectionReport:
    """
    Scans entire pharmaceutical commercial network across all SKUs, Markets, and Channels.
    Identifies localized surges, network plunges, structural step changes, and inter-channel distortions.
    Compiles dimensional summaries and executive impact briefing.
    """
    if demand_df.empty:
        return AnomalyDetectionReport(
            total_observations=0,
            total_anomalies=0,
            surge_count=0,
            plunge_count=0,
            shift_count=0,
            distortion_count=0,
            critical_count=0,
            high_count=0,
            medium_count=0,
            low_count=0,
            records=[],
            anomalies=[],
            summary_by_sku={},
            summary_by_market={},
            total_network_exposure_usd=0.0,
            executive_summary="Empty dataset provided. Zero observations analyzed."
        )

    all_records: List[DemandAnomalyRecord] = []
    grouped = demand_df.groupby([sku_col, market_col])

    # 1. Series-by-series rolling evaluation
    for (sku, mkt), group in grouped:
        series_recs = detect_series_anomalies(
            df=group,
            date_col=date_col,
            value_col=value_col,
            sku_col=sku_col,
            market_col=market_col,
            window=window,
            z_threshold=z_threshold,
            iqr_multiplier=iqr_multiplier,
            min_periods=min_periods
        )
        all_records.extend(series_recs)

    # 2. Check Channel Distortion across markets for the same SKU at identical dates
    # If one market surges while another drops or stays flat
    records_df = pd.DataFrame([
        {
            "idx": i,
            "date": r.observation_date,
            "sku": r.finished_sku_id,
            "mkt": r.market_id,
            "actual": r.actual_demand,
            "expected": r.expected_demand,
            "z": r.z_score,
            "is_anomaly": r.is_anomaly
        }
        for i, r in enumerate(all_records)
    ])

    if not records_df.empty:
        # Check cross-market dates
        for (obs_date, sku), sub_df in records_df.groupby(["date", "sku"]):
            if len(sub_df) >= 2:
                max_z = sub_df["z"].max()
                min_z = sub_df["z"].min()
                z_spread = max_z - min_z
                # Extreme divergence: one market is surging (Z > 2.5) while other is normal or dropping (Z < 0.5)
                if z_spread >= 3.5 and max_z >= 2.5 and min_z <= 0.5:
                    # Flag the surging market as having channel distortion impact
                    surging_idx = sub_df.loc[sub_df["z"].idxmax()]["idx"]
                    orig_rec = all_records[surging_idx]
                    if orig_rec.anomaly_type == AnomalyType.DEMAND_SURGE:
                        orig_rec.anomaly_type = AnomalyType.CHANNEL_DISTORTION
                        orig_rec.detection_method = "CHANNEL_DISTORTION"
                        orig_rec.context_notes += (
                            f" [Channel Distortion: Z-spread {z_spread:.2f} across regional markets]."
                        )
                        orig_rec.downstream_impact = assess_downstream_impact(
                            anomaly_type=AnomalyType.CHANNEL_DISTORTION,
                            actual_demand=orig_rec.actual_demand,
                            expected_demand=orig_rec.expected_demand,
                            finished_sku_id=orig_rec.finished_sku_id
                        )

    # Compile aggregated statistics
    anomalies_only = [r for r in all_records if r.is_anomaly]
    total_obs = len(all_records)
    total_anom = len(anomalies_only)

    surge_cnt = sum(1 for r in anomalies_only if r.anomaly_type == AnomalyType.DEMAND_SURGE)
    plunge_cnt = sum(1 for r in anomalies_only if r.anomaly_type == AnomalyType.DEMAND_PLUNGE)
    shift_cnt = sum(1 for r in anomalies_only if r.anomaly_type == AnomalyType.STRUCTURAL_SHIFT)
    distort_cnt = sum(1 for r in anomalies_only if r.anomaly_type == AnomalyType.CHANNEL_DISTORTION)

    crit_cnt = sum(1 for r in anomalies_only if r.severity == AnomalySeverity.CRITICAL)
    high_cnt = sum(1 for r in anomalies_only if r.severity == AnomalySeverity.HIGH)
    med_cnt = sum(1 for r in anomalies_only if r.severity == AnomalySeverity.MEDIUM)
    low_cnt = sum(1 for r in anomalies_only if r.severity == AnomalySeverity.LOW)

    total_exposure = sum(
        r.downstream_impact.estimated_financial_exposure_usd
        for r in anomalies_only
        if r.downstream_impact is not None
    )

    # Dimensional summary by SKU
    summary_sku: Dict[str, AnomalySummaryByDimension] = {}
    sku_groups = {}
    for r in all_records:
        sku_groups.setdefault(r.finished_sku_id, []).append(r)

    for sku_key, group_recs in sku_groups.items():
        anoms = [r for r in group_recs if r.is_anomaly]
        summary_sku[sku_key] = AnomalySummaryByDimension(
            dimension_key=sku_key,
            total_observations=len(group_recs),
            anomaly_count=len(anoms),
            surge_count=sum(1 for r in anoms if r.anomaly_type == AnomalyType.DEMAND_SURGE),
            plunge_count=sum(1 for r in anoms if r.anomaly_type == AnomalyType.DEMAND_PLUNGE),
            shift_count=sum(1 for r in anoms if r.anomaly_type == AnomalyType.STRUCTURAL_SHIFT),
            distortion_count=sum(1 for r in anoms if r.anomaly_type == AnomalyType.CHANNEL_DISTORTION),
            critical_count=sum(1 for r in anoms if r.severity == AnomalySeverity.CRITICAL),
            max_z_score=float(max((abs(r.z_score) for r in group_recs), default=0.0)),
            total_financial_exposure_usd=sum(
                r.downstream_impact.estimated_financial_exposure_usd
                for r in anoms if r.downstream_impact is not None
            )
        )

    # Dimensional summary by Market
    summary_mkt: Dict[str, AnomalySummaryByDimension] = {}
    mkt_groups = {}
    for r in all_records:
        mkt_groups.setdefault(r.market_id, []).append(r)

    for mkt_key, group_recs in mkt_groups.items():
        anoms = [r for r in group_recs if r.is_anomaly]
        summary_mkt[mkt_key] = AnomalySummaryByDimension(
            dimension_key=mkt_key,
            total_observations=len(group_recs),
            anomaly_count=len(anoms),
            surge_count=sum(1 for r in anoms if r.anomaly_type == AnomalyType.DEMAND_SURGE),
            plunge_count=sum(1 for r in anoms if r.anomaly_type == AnomalyType.DEMAND_PLUNGE),
            shift_count=sum(1 for r in anoms if r.anomaly_type == AnomalyType.STRUCTURAL_SHIFT),
            distortion_count=sum(1 for r in anoms if r.anomaly_type == AnomalyType.CHANNEL_DISTORTION),
            critical_count=sum(1 for r in anoms if r.severity == AnomalySeverity.CRITICAL),
            max_z_score=float(max((abs(r.z_score) for r in group_recs), default=0.0)),
            total_financial_exposure_usd=sum(
                r.downstream_impact.estimated_financial_exposure_usd
                for r in anoms if r.downstream_impact is not None
            )
        )

    # Executive Briefing Narrative
    exec_summary = (
        f"Network Demand Anomaly Audit: Scanned {total_obs:,} observations across {len(summary_sku)} SKUs "
        f"and {len(summary_mkt)} markets. Detected {total_anom} anomalies ({total_anom / max(total_obs, 1) * 100:.1f}% rate): "
        f"{surge_cnt} surges, {plunge_cnt} plunges, {shift_cnt} structural shifts, {distort_cnt} channel distortions. "
        f"Severity breakdown: {crit_cnt} critical, {high_cnt} high, {med_cnt} medium, {low_cnt} low. "
        f"Total network financial exposure: ${total_exposure:,.2f} USD."
    )

    return AnomalyDetectionReport(
        total_observations=total_obs,
        total_anomalies=total_anom,
        surge_count=surge_cnt,
        plunge_count=plunge_cnt,
        shift_count=shift_cnt,
        distortion_count=distort_cnt,
        critical_count=crit_cnt,
        high_count=high_cnt,
        medium_count=med_cnt,
        low_count=low_cnt,
        records=all_records,
        anomalies=anomalies_only,
        summary_by_sku=summary_sku,
        summary_by_market=summary_mkt,
        total_network_exposure_usd=total_exposure,
        executive_summary=exec_summary
    )


# =============================================================================
# OBJECT-ORIENTED DETECTOR INTERFACE
# =============================================================================

class DemandAnomalyDetector:
    """
    Configurable Pharmaceutical Demand Anomaly Detector.
    Encapsulates statistical parameters, price lookups, and inventory assumptions.
    """

    def __init__(
        self,
        window: int = 12,
        z_threshold: float = 3.0,
        iqr_multiplier: float = 1.5,
        min_periods: int = 4,
        sku_prices: Optional[Dict[str, float]] = None
    ):
        self.window = window
        self.z_threshold = z_threshold
        self.iqr_multiplier = iqr_multiplier
        self.min_periods = min_periods
        self.sku_prices = sku_prices or DEFAULT_SKU_PRICES.copy()

    def evaluate_point(
        self,
        current_val: float,
        historical_series: Union[List[float], np.ndarray, pd.Series],
        observation_date: Union[date, str, datetime] = date(2026, 1, 1),
        finished_sku_id: str = "SKU-AUG-500-T10",
        market_id: str = "MKT-IN-HYD",
        current_inventory_packs: Optional[float] = None
    ) -> DemandAnomalyRecord:
        """Evaluates a single point observation."""
        return evaluate_point_anomaly(
            current_val=current_val,
            historical_series=historical_series,
            observation_date=observation_date,
            finished_sku_id=finished_sku_id,
            market_id=market_id,
            z_threshold=self.z_threshold,
            iqr_multiplier=self.iqr_multiplier,
            min_periods=self.min_periods,
            current_inventory_packs=current_inventory_packs
        )

    def detect_series(
        self,
        df: pd.DataFrame,
        date_col: str = "week_start_date",
        value_col: str = "demand_quantity",
        sku_col: str = "finished_sku_id",
        market_col: str = "market_id"
    ) -> List[DemandAnomalyRecord]:
        """Runs rolling detection over a single series."""
        return detect_series_anomalies(
            df=df,
            date_col=date_col,
            value_col=value_col,
            sku_col=sku_col,
            market_col=market_col,
            window=self.window,
            z_threshold=self.z_threshold,
            iqr_multiplier=self.iqr_multiplier,
            min_periods=self.min_periods
        )

    def detect_network(
        self,
        demand_df: pd.DataFrame,
        date_col: str = "week_start_date",
        sku_col: str = "finished_sku_id",
        market_col: str = "market_id",
        value_col: str = "demand_quantity"
    ) -> AnomalyDetectionReport:
        """Runs multi-echelon network-wide scan."""
        return detect_network_demand_anomalies(
            demand_df=demand_df,
            date_col=date_col,
            sku_col=sku_col,
            market_col=market_col,
            value_col=value_col,
            window=self.window,
            z_threshold=self.z_threshold,
            iqr_multiplier=self.iqr_multiplier,
            min_periods=self.min_periods
        )
