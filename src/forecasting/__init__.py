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
from src.forecasting.ml_models import (
    PredictionInterval,
    MLForecastResult,
    MLBenchmarkScorecard,
    RidgeDemandForecaster,
    GradientBoostingDemandForecaster,
    calculate_prediction_intervals,
    generate_recursive_multi_step_forecast,
    evaluate_ml_against_baseline,
    generate_production_26_week_forecast
)
from src.forecasting.evaluation import (
    DriftAlarmSeverity,
    TrackingSignalPoint,
    TrackingSignalAuditResult,
    ForecastSliceMetrics,
    ForecastSliceReport,
    VersionVarianceItem,
    ForecastVersionComparisonReport,
    evaluate_forecast_slices,
    evaluate_tracking_signal_drift,
    analyze_forecast_version_variance,
    ForecastRegistry
)
from src.forecasting.anomaly import (
    AnomalyType,
    AnomalySeverity,
    DownstreamSupplyImpact,
    DemandAnomalyRecord,
    AnomalySummaryByDimension,
    AnomalyDetectionReport,
    assess_downstream_impact,
    evaluate_point_anomaly,
    detect_structural_shift,
    detect_series_anomalies,
    detect_network_demand_anomalies,
    DemandAnomalyDetector
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
    "run_baseline_benchmark_evaluation",
    "PredictionInterval",
    "MLForecastResult",
    "MLBenchmarkScorecard",
    "RidgeDemandForecaster",
    "GradientBoostingDemandForecaster",
    "calculate_prediction_intervals",
    "generate_recursive_multi_step_forecast",
    "evaluate_ml_against_baseline",
    "generate_production_26_week_forecast",
    "DriftAlarmSeverity",
    "TrackingSignalPoint",
    "TrackingSignalAuditResult",
    "ForecastSliceMetrics",
    "ForecastSliceReport",
    "VersionVarianceItem",
    "ForecastVersionComparisonReport",
    "evaluate_forecast_slices",
    "evaluate_tracking_signal_drift",
    "analyze_forecast_version_variance",
    "ForecastRegistry",
    "AnomalyType",
    "AnomalySeverity",
    "DownstreamSupplyImpact",
    "DemandAnomalyRecord",
    "AnomalySummaryByDimension",
    "AnomalyDetectionReport",
    "assess_downstream_impact",
    "evaluate_point_anomaly",
    "detect_structural_shift",
    "detect_series_anomalies",
    "detect_network_demand_anomalies",
    "DemandAnomalyDetector"
]
