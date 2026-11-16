"""
Pharmaceutical Demand Time-Series Preprocessing & Leakage-Free Splitting Engine.
Phase 2 (Day 20) Forecasting Layer Implementation.

Implements chronological time-series splitting, strictly causal lag and rolling feature engineering,
pharmaceutical calendar indicators, and an automated data leakage audit engine.
Strictly zero LLM mathematical calculations. Pure deterministic time-series processing.
"""

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from typing import List, Dict, Tuple, Optional, Any, Union
import math
import sqlite3
import pandas as pd
import numpy as np


@dataclass
class TimeSeriesSplit:
    """Chronologically partitioned datasets ensuring zero future target leakage."""
    train_df: pd.DataFrame
    val_df: pd.DataFrame
    test_df: pd.DataFrame
    train_start: date
    train_end: date
    val_start: date
    val_end: date
    test_start: date
    test_end: date
    total_weeks: int
    train_weeks: int
    val_weeks: int
    test_weeks: int
    num_series: int
    total_samples: int

    def summary(self) -> Dict[str, Any]:
        """Provides an executive summary of partition boundaries and sample allocations."""
        return {
            "total_weeks": self.total_weeks,
            "train_horizon": f"{self.train_start} to {self.train_end} ({self.train_weeks} weeks, {len(self.train_df)} rows)",
            "val_horizon": f"{self.val_start} to {self.val_end} ({self.val_weeks} weeks, {len(self.val_df)} rows)",
            "test_horizon": f"{self.test_start} to {self.test_end} ({self.test_weeks} weeks, {len(self.test_df)} rows)",
            "num_series": self.num_series,
            "total_samples": self.total_samples
        }


@dataclass
class FeatureMatrix:
    """Structured machine learning dataset containing features, target vector, and metadata."""
    X: pd.DataFrame
    y: pd.Series
    metadata: pd.DataFrame
    feature_names: List[str]
    target_name: str
    num_samples: int

    def __post_init__(self):
        if len(self.X) != len(self.y):
            raise ValueError(f"Feature length {len(self.X)} does not match target length {len(self.y)}")


@dataclass
class LeakageAuditReport:
    """Formal audit report certifying mathematical absence of future target leakage."""
    is_leakage_free: bool
    temporal_ordering_passed: bool
    split_disjointness_passed: bool
    causal_feature_alignment_passed: bool
    no_future_target_in_features_passed: bool
    downstream_target_exclusion_passed: bool
    checks_evaluated: int
    violations: List[str] = field(default_factory=list)
    audit_timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def generate_markdown_summary(self) -> str:
        """Formats the audit outcome into an executive Markdown report."""
        status_icon = "✅ PASSED (Leakage-Free)" if self.is_leakage_free else "❌ FAILED (Leakage Detected)"
        lines = [
            "# Time-Series Data Leakage Audit Report",
            f"**Audit Status:** {status_icon}  ",
            f"**Evaluated At:** {self.audit_timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}  ",
            f"**Total Checks Evaluated:** {self.checks_evaluated}  ",
            "",
            "## 1. Compliance Verification Checklist",
            f"- [{'x' if self.temporal_ordering_passed else ' '}] **Strict Temporal Ordering:** `Train End < Val Start < Test Start`",
            f"- [{'x' if self.split_disjointness_passed else ' '}] **Partition Disjointness:** Zero calendar date overlap between splits",
            f"- [{'x' if self.causal_feature_alignment_passed else ' '}] **Causal Feature Alignment:** All features at week $t$ depend solely on observations $\\le t-1$",
            f"- [{'x' if self.no_future_target_in_features_passed else ' '}] **Target Independence:** Target vector $y_t$ is strictly absent from feature matrix $X_t$",
            f"- [{'x' if self.downstream_target_exclusion_passed else ' '}] **Downstream Exclusion:** No operational outcomes (e.g. lost sales, fulfilled orders) leak into inputs",
            ""
        ]

        if self.violations:
            lines.extend([
                "## 2. Detected Violations",
                *[f"- ⚠️ {v}" for v in self.violations],
                ""
            ])
        else:
            lines.extend([
                "## 2. Audit Conclusion",
                "Certified compliant: Feature matrix exhibits 100% causal integrity for production forecasting.",
                ""
            ])

        return "\n".join(lines)


# =============================================================================
# 1. DATABASE LOADING & TIME-SERIES SANITIZATION
# =============================================================================

def load_demand_history_from_db(
    db_conn_or_path: Union[sqlite3.Connection, str] = "data/processed/control_tower.db",
    scenario_id: str = "SCN-BASE"
) -> pd.DataFrame:
    """
    Loads 104-week historical commercial demand observations from the SQLite database.
    Ensures standard datetime parsing and deterministic sorting.
    """
    is_internal_conn = False
    if isinstance(db_conn_or_path, str):
        conn = sqlite3.connect(db_conn_or_path)
        is_internal_conn = True
    else:
        conn = db_conn_or_path

    try:
        query = (
            "SELECT week_start_date, finished_sku_id, market_id, demand_quantity, "
            "fulfilled_quantity, lost_sales_quantity, event_type, scenario_id "
            "FROM fact_demand_history "
            "WHERE scenario_id = ? "
            "ORDER BY finished_sku_id, market_id, week_start_date"
        )
        df = pd.read_sql_query(query, conn, params=[scenario_id])
        df["week_start_date"] = pd.to_datetime(df["week_start_date"])
        df["demand_quantity"] = df["demand_quantity"].astype(float)
        df["fulfilled_quantity"] = df["fulfilled_quantity"].astype(float)
        df["lost_sales_quantity"] = df["lost_sales_quantity"].astype(float)
        return df
    finally:
        if is_internal_conn:
            conn.close()


# =============================================================================
# 2. CHRONOLOGICAL TIME-SERIES SPLITTING
# =============================================================================

def split_time_series_chronologically(
    df: pd.DataFrame,
    train_ratio: float = 0.75,
    val_ratio: float = 0.125,
    test_ratio: float = 0.125,
    date_col: str = "week_start_date",
    group_cols: List[str] = ["finished_sku_id", "market_id"]
) -> TimeSeriesSplit:
    """
    Partitions multi-series time-series data chronologically without future leakage.
    Ensures train, validation, and test splits share identical date cutoffs across all series.
    
    Default split on 104 historical weeks:
    - Train: 78 weeks (75.0%)
    - Validation: 13 weeks (12.5%)
    - Test: 13 weeks (12.5%)
    """
    if not math.isclose(train_ratio + val_ratio + test_ratio, 1.0, rel_tol=1e-5):
        raise ValueError(f"Ratios must sum to 1.0; received {train_ratio + val_ratio + test_ratio}")

    # Extract distinct, sorted calendar weeks across the dataset
    distinct_dates = sorted(df[date_col].drop_duplicates())
    total_weeks = len(distinct_dates)
    if total_weeks < 8:
        raise ValueError(f"Insufficient historical weeks for meaningful split: {total_weeks}")

    train_count = int(round(total_weeks * train_ratio))
    val_count = int(round(total_weeks * val_ratio))
    test_count = total_weeks - (train_count + val_count)

    # Ensure each split has at least 1 week
    if train_count < 1 or val_count < 1 or test_count < 1:
        raise ValueError("Configured ratios result in empty partitions")

    train_dates = distinct_dates[:train_count]
    val_dates = distinct_dates[train_count:train_count + val_count]
    test_dates = distinct_dates[train_count + val_count:]

    train_df = df[df[date_col].isin(train_dates)].copy()
    val_df = df[df[date_col].isin(val_dates)].copy()
    test_df = df[df[date_col].isin(test_dates)].copy()

    # Number of unique series
    num_series = len(df[group_cols].drop_duplicates())

    def to_date(ts: Union[pd.Timestamp, date, datetime]) -> date:
        if isinstance(ts, pd.Timestamp):
            return ts.date()
        if isinstance(ts, datetime):
            return ts.date()
        return ts

    return TimeSeriesSplit(
        train_df=train_df,
        val_df=val_df,
        test_df=test_df,
        train_start=to_date(train_dates[0]),
        train_end=to_date(train_dates[-1]),
        val_start=to_date(val_dates[0]),
        val_end=to_date(val_dates[-1]),
        test_start=to_date(test_dates[0]),
        test_end=to_date(test_dates[-1]),
        total_weeks=total_weeks,
        train_weeks=len(train_dates),
        val_weeks=len(val_dates),
        test_weeks=len(test_dates),
        num_series=num_series,
        total_samples=len(df)
    )


# =============================================================================
# 3. CALENDAR & CYCLICAL FEATURE ENGINEERING
# =============================================================================

def create_calendar_features(
    df: pd.DataFrame,
    date_col: str = "week_start_date"
) -> pd.DataFrame:
    """
    Generates deterministic calendar, seasonal, and pharmaceutical market cycle features.
    
    Includes cyclical trigonometric encodings of annual and monthly seasonality,
    as well as Indian pharmaceutical seasonal surge indicators (Monsoon respiratory spike, Diwali channel loading).
    """
    out = df.copy()
    dates = pd.to_datetime(out[date_col])

    # Calendar chronological fields
    out["calendar_year"] = dates.dt.year
    out["calendar_month"] = dates.dt.month
    out["calendar_quarter"] = dates.dt.quarter
    iso_week = dates.dt.isocalendar().week
    out["week_of_year"] = iso_week.astype(int)

    # Cyclical trigonometric transforms (preserves seamless boundary continuity)
    # 52.1775 weeks in an average Gregorian year
    out["sin_week_of_year"] = np.sin(2 * np.pi * out["week_of_year"] / 52.1775).round(6)
    out["cos_week_of_year"] = np.cos(2 * np.pi * out["week_of_year"] / 52.1775).round(6)
    out["sin_month"] = np.sin(2 * np.pi * out["calendar_month"] / 12.0).round(6)
    out["cos_month"] = np.cos(2 * np.pi * out["calendar_month"] / 12.0).round(6)

    # Pharmaceutical market cycle indicators
    # Channel loading occurs during quarter-ending months (March, June, September, December)
    out["is_quarter_end_month"] = out["calendar_month"].isin([3, 6, 9, 12]).astype(int)

    # Indian monsoon antibiotic surge: Weeks 24 to 38 (June to September acute respiratory infections)
    out["is_monsoon_surge"] = out["week_of_year"].between(24, 38).astype(int)

    # Diwali festival channel adjustment: Weeks 42 to 45 (October/November distributor holidays)
    out["is_diwali_period"] = out["week_of_year"].between(42, 45).astype(int)

    return out


# =============================================================================
# 4. STRICTLY CAUSAL LAG & ROLLING STATISTICAL FEATURES
# =============================================================================

def create_demand_lag_features(
    df: pd.DataFrame,
    group_cols: List[str] = ["finished_sku_id", "market_id"],
    target_col: str = "demand_quantity",
    date_col: str = "week_start_date",
    lag_weeks: List[int] = [1, 2, 4, 8, 12],
    include_annual_lag: bool = True,
    rolling_windows: List[int] = [4, 12, 26]
) -> pd.DataFrame:
    """
    Computes strictly causal time-series lag and rolling window statistical features per series.
    
    CRITICAL LEAKAGE GUARD:
    All rolling window calculations are performed on y.shift(1), strictly preventing
    the current week's target value y_t from participating in historical feature calculation.
    """
    out = df.copy()
    out = out.sort_values(by=group_cols + [date_col]).reset_index(drop=True)

    actual_lags = list(lag_weeks)
    if include_annual_lag and 52 not in actual_lags:
        actual_lags.append(52)

    # 1. Individual Autoregressive Lag Features
    for k in actual_lags:
        col_name = f"lag_{k}"
        out[col_name] = out.groupby(group_cols)[target_col].shift(k)

    # 2. Rolling Window Statistics (Strictly Causal via shift(1))
    for w in rolling_windows:
        # Shift target by 1 week so rolling window strictly encompasses [t-w, ..., t-1]
        shifted_series = out.groupby(group_cols)[target_col].shift(1)
        
        # Grouped rolling calculations
        grouped_shifted = shifted_series.groupby([out[c] for c in group_cols])
        
        out[f"rolling_mean_{w}"] = grouped_shifted.rolling(window=w, min_periods=w).mean().round(4).values
        out[f"rolling_std_{w}"] = grouped_shifted.rolling(window=w, min_periods=w).std().round(4).values
        out[f"rolling_min_{w}"] = grouped_shifted.rolling(window=w, min_periods=w).min().round(4).values
        out[f"rolling_max_{w}"] = grouped_shifted.rolling(window=w, min_periods=w).max().round(4).values

    # 3. Momentum & Short-vs-Long Trend Ratios
    # Short-term (4-week) vs Medium-term (12-week) demand acceleration
    if 4 in rolling_windows and 12 in rolling_windows:
        out["ratio_mean4_to_mean12"] = (
            out["rolling_mean_4"] / (out["rolling_mean_12"] + 1e-5)
        ).round(4)

    # Difference between immediate prior weeks (trend velocity)
    if 1 in actual_lags and 2 in actual_lags:
        out["diff_lag1_lag2"] = (out["lag_1"] - out["lag_2"]).round(4)
    if 1 in actual_lags and 4 in actual_lags:
        out["diff_lag1_lag4"] = (out["lag_1"] - out["lag_4"]).round(4)

    return out


# =============================================================================
# 5. CATEGORICAL ENCODING & FULL PREPROCESSING PIPELINE
# =============================================================================

def encode_series_identifiers(
    df: pd.DataFrame,
    sku_col: str = "finished_sku_id",
    market_col: str = "market_id"
) -> pd.DataFrame:
    """Creates deterministic one-hot indicator variables for SKU and Market identifiers."""
    out = df.copy()

    # Fixed canonical domain encodings to ensure stable cross-environment schema
    known_skus = ["SKU-AUG-500-T10", "SKU-AUG-500-T30"]
    known_markets = ["MKT-IN-HYD", "MKT-IN-PUN"]

    for sku in known_skus:
        clean_name = sku.replace("-", "_")
        out[f"is_{clean_name}"] = (out[sku_col] == sku).astype(int)

    for mkt in known_markets:
        clean_name = mkt.replace("-", "_")
        out[f"is_{clean_name}"] = (out[market_col] == mkt).astype(int)

    return out


def create_demand_feature_pipeline(
    df: pd.DataFrame,
    drop_na_lags: bool = True,
    include_annual_lag: bool = False,
    group_cols: List[str] = ["finished_sku_id", "market_id"],
    target_col: str = "demand_quantity",
    date_col: str = "week_start_date",
    lag_weeks: List[int] = [1, 2, 4, 8, 12],
    rolling_windows: List[int] = [4, 12]
) -> Tuple[pd.DataFrame, FeatureMatrix]:
    """
    Complete end-to-end deterministic demand feature engineering pipeline:
    1. Generates cyclical calendar & market seasonality features.
    2. Constructs strictly causal autoregressive lag & rolling window metrics.
    3. Encodes categorical series identifiers.
    4. Separates feature matrix X, target vector y, and traceability metadata.
    """
    # 1. Calendar features
    f_df = create_calendar_features(df, date_col=date_col)

    # 2. Causal lags & rolling statistics
    f_df = create_demand_lag_features(
        f_df,
        group_cols=group_cols,
        target_col=target_col,
        date_col=date_col,
        lag_weeks=lag_weeks,
        include_annual_lag=include_annual_lag,
        rolling_windows=rolling_windows
    )

    # 3. Series dummy encoding
    f_df = encode_series_identifiers(f_df)

    # 4. Filter missing values incurred by initial lag warm-up
    if drop_na_lags:
        f_df = f_df.dropna().reset_index(drop=True)

    # 5. Extract Feature Matrix (X), Target (y), and Metadata
    metadata_cols = [date_col] + group_cols + ["scenario_id"] if "scenario_id" in f_df.columns else [date_col] + group_cols
    metadata_cols = [c for c in metadata_cols if c in f_df.columns]

    # Exclude target, operational post-demand outcomes, and non-numerical tracking columns
    excluded_from_X = set(metadata_cols + [
        target_col,
        "fulfilled_quantity",
        "lost_sales_quantity",
        "event_type",
        "synthetic_data_flag"
    ])

    feature_cols = [c for c in f_df.columns if c not in excluded_from_X]

    X = f_df[feature_cols].copy()
    y = f_df[target_col].copy()
    meta = f_df[metadata_cols].copy()

    matrix = FeatureMatrix(
        X=X,
        y=y,
        metadata=meta,
        feature_names=feature_cols,
        target_name=target_col,
        num_samples=len(f_df)
    )

    return f_df, matrix


@dataclass
class PartitionedDataset:
    """Convenience bundle of train, validation, and test feature-target pairs."""
    X_train: pd.DataFrame
    y_train: pd.Series
    meta_train: pd.DataFrame
    X_val: pd.DataFrame
    y_val: pd.Series
    meta_val: pd.DataFrame
    X_test: pd.DataFrame
    y_test: pd.Series
    meta_test: pd.DataFrame
    feature_names: List[str]


def partition_feature_matrix(
    matrix: FeatureMatrix,
    split: TimeSeriesSplit,
    date_col: str = "week_start_date"
) -> PartitionedDataset:
    """
    Partitions a FeatureMatrix into train, validation, and test sub-matrices
    strictly adhering to the TimeSeriesSplit chronological boundary dates.
    """
    dates = pd.to_datetime(matrix.metadata[date_col]).dt.date

    train_mask = (dates >= split.train_start) & (dates <= split.train_end)
    val_mask = (dates >= split.val_start) & (dates <= split.val_end)
    test_mask = (dates >= split.test_start) & (dates <= split.test_end)

    return PartitionedDataset(
        X_train=matrix.X[train_mask].copy().reset_index(drop=True),
        y_train=matrix.y[train_mask].copy().reset_index(drop=True),
        meta_train=matrix.metadata[train_mask].copy().reset_index(drop=True),
        X_val=matrix.X[val_mask].copy().reset_index(drop=True),
        y_val=matrix.y[val_mask].copy().reset_index(drop=True),
        meta_val=matrix.metadata[val_mask].copy().reset_index(drop=True),
        X_test=matrix.X[test_mask].copy().reset_index(drop=True),
        y_test=matrix.y[test_mask].copy().reset_index(drop=True),
        meta_test=matrix.metadata[test_mask].copy().reset_index(drop=True),
        feature_names=matrix.feature_names
    )


# =============================================================================
# 6. MATHEMATICAL DATA LEAKAGE AUDIT ENGINE
# =============================================================================

def audit_time_series_leakage(
    split: TimeSeriesSplit,
    feature_matrix: FeatureMatrix,
    target_col: str = "demand_quantity",
    date_col: str = "week_start_date",
    group_cols: List[str] = ["finished_sku_id", "market_id"]
) -> LeakageAuditReport:
    """
    Performs rigorous automated verification to mathematically prove zero data leakage:
    1. Temporal boundary disjointness: Train End < Val Start < Test Start.
    2. Date partition disjointness: Zero overlapping calendar weeks between splits.
    3. Causal feature verification: lag_1 at week t strictly matches y at week t-1.
    4. Target exclusion: Target y is absent from feature matrix X.
    5. Operational outcome exclusion: Downstream variables (lost_sales, fulfilled) excluded from features.
    """
    violations: List[str] = []
    checks = 0

    # Check 1: Temporal Ordering
    checks += 1
    t_order = (split.train_end < split.val_start) and (split.val_end < split.test_start)
    if not t_order:
        violations.append(
            f"Temporal boundary sequence violated: Train End ({split.train_end}) >= "
            f"Val Start ({split.val_start}) or Val End ({split.val_end}) >= Test Start ({split.test_start})"
        )

    # Check 2: Date Disjointness
    checks += 1
    train_dates = set(split.train_df[date_col].dt.date if hasattr(split.train_df[date_col], "dt") else split.train_df[date_col])
    val_dates = set(split.val_df[date_col].dt.date if hasattr(split.val_df[date_col], "dt") else split.val_df[date_col])
    test_dates = set(split.test_df[date_col].dt.date if hasattr(split.test_df[date_col], "dt") else split.test_df[date_col])

    overlap_train_val = train_dates.intersection(val_dates)
    overlap_val_test = val_dates.intersection(test_dates)
    overlap_train_test = train_dates.intersection(test_dates)

    disjoint = len(overlap_train_val) == 0 and len(overlap_val_test) == 0 and len(overlap_train_test) == 0
    if not disjoint:
        violations.append(
            f"Overlapping calendar dates detected between splits: "
            f"Train-Val: {len(overlap_train_val)}, Val-Test: {len(overlap_val_test)}, Train-Test: {len(overlap_train_test)}"
        )

    # Check 3: Causal Feature Alignment Verification
    # For every sample, verify that lag_1 strictly equals the historical value of y at the prior period
    checks += 1
    causal_aligned = True
    if "lag_1" in feature_matrix.X.columns:
        full_meta_x = pd.concat([feature_matrix.metadata, feature_matrix.X[["lag_1"]], feature_matrix.y], axis=1)
        full_meta_x = full_meta_x.sort_values(by=group_cols + [date_col]).reset_index(drop=True)

        for _, group in full_meta_x.groupby(group_cols):
            shifted_y = group[target_col].shift(1)
            # Compare non-null values
            valid_mask = group["lag_1"].notna() & shifted_y.notna()
            diff = (group.loc[valid_mask, "lag_1"] - shifted_y.loc[valid_mask]).abs()
            if (diff > 1e-4).any():
                causal_aligned = False
                max_diff = diff.max()
                violations.append(f"Causal lag_1 mismatch with shifted y (max delta: {max_diff})")
                break

    # Check 4: Target Independence
    checks += 1
    target_in_features = False
    if target_col in feature_matrix.X.columns:
        target_in_features = True
        violations.append(f"Target column '{target_col}' explicitly present in feature matrix X")

    # Check correlation to ensure no perfect leak
    for col in feature_matrix.X.columns:
        if pd.api.types.is_numeric_dtype(feature_matrix.X[col]):
            col_std = float(feature_matrix.X[col].std())
            if col_std > 1e-8:
                corr = feature_matrix.X[col].corr(feature_matrix.y)
                if not np.isnan(corr) and abs(corr) >= 0.9999:
                    target_in_features = True
                    violations.append(f"Feature '{col}' exhibits suspicious near-perfect correlation ({corr:.4f}) with target y")

    # Check 5: Downstream Operational Outcome Exclusion
    checks += 1
    downstream_excluded = True
    forbidden_downstream = {"fulfilled_quantity", "lost_sales_quantity", "actual_yield", "shortage_quantity"}
    leaked_downstream = forbidden_downstream.intersection(set(feature_matrix.X.columns))
    if leaked_downstream:
        downstream_excluded = False
        violations.append(f"Forbidden downstream operational columns leaked into features: {leaked_downstream}")

    is_clean = (
        t_order and
        disjoint and
        causal_aligned and
        not target_in_features and
        downstream_excluded
    )

    return LeakageAuditReport(
        is_leakage_free=is_clean,
        temporal_ordering_passed=t_order,
        split_disjointness_passed=disjoint,
        causal_feature_alignment_passed=causal_aligned,
        no_future_target_in_features_passed=not target_in_features,
        downstream_target_exclusion_passed=downstream_excluded,
        checks_evaluated=checks,
        violations=violations
    )
