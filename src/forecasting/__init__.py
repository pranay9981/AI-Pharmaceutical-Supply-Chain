"""
Demand Forecasting & Time-Series Analytics Module.
Phase 2 (Weeks 05) Core Implementation.

Provides leakage-free chronological time-series splitting, feature engineering (lags, rolling stats, calendar),
statistical baselines, machine learning models, prediction intervals, and evaluation metrics.
Strictly zero LLM mathematical calculations.
"""

from src.forecasting.prep import (
    TimeSeriesSplit,
    FeatureMatrix,
    PartitionedDataset,
    LeakageAuditReport,
    split_time_series_chronologically,
    create_calendar_features,
    create_demand_lag_features,
    create_demand_feature_pipeline,
    partition_feature_matrix,
    audit_time_series_leakage,
    load_demand_history_from_db
)
from src.forecasting.baseline import (
    ForecastEvaluationMetrics,
    SeriesForecastResult,
    BaselineBenchmarkReport,
    calculate_forecast_metrics,
    SeasonalNaiveModel,
    MovingAverageModel,
    ExponentialSmoothingModel,
    generate_series_forecast,
    run_baseline_benchmark_evaluation
)

__all__ = [
    "TimeSeriesSplit",
    "FeatureMatrix",
    "PartitionedDataset",
    "LeakageAuditReport",
    "split_time_series_chronologically",
    "create_calendar_features",
    "create_demand_lag_features",
    "create_demand_feature_pipeline",
    "partition_feature_matrix",
    "audit_time_series_leakage",
    "load_demand_history_from_db",
    "ForecastEvaluationMetrics",
    "SeriesForecastResult",
    "BaselineBenchmarkReport",
    "calculate_forecast_metrics",
    "SeasonalNaiveModel",
    "MovingAverageModel",
    "ExponentialSmoothingModel",
    "generate_series_forecast",
    "run_baseline_benchmark_evaluation"
]
