"""
Synapse RiskOps - Failure Forecaster
Statsmodels Exponential Smoothing + Velocity Analysis

Owner: Person 2 | Week: 2

Time-series failure prediction combining Statsmodels
Exponential Smoothing with recent metric velocity
and acceleration analysis.
"""

import numpy as np
import pandas as pd
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from loguru import logger
from typing import Dict, List


class FailureForecaster:
    """
    Time-series forecaster combining Exponential Smoothing
    with recent trend velocity to predict threshold breaches.
    """

    # Critical failure thresholds
    FAILURE_THRESHOLDS = {
        "cpu_usage": 80.0,
        "memory_usage": 85.0,
        "error_rate": 3.0,
        "network_latency_ms": 50.0,
        "response_time_p99": 200.0,
        "active_connections": 220,
        "disk_io": 60.0,
    }

    # Map metrics to failure types
    METRIC_TO_FAILURE_TYPE = {
        "cpu_usage": "cpu_saturation",
        "memory_usage": "memory_exhaustion",
        "error_rate": "error_rate_spike",
        "network_latency_ms": "latency_degradation",
        "response_time_p99": "latency_degradation",
        "active_connections": "connection_pool_exhaustion",
        "disk_io": "disk_io_bottleneck",
    }

    # Metrics used for forecasting
    FORECAST_METRICS = [
        "cpu_usage",
        "memory_usage",
        "error_rate",
        "network_latency_ms",
        "response_time_p99",
        "active_connections",
        "disk_io",
    ]

    def __init__(self, forecast_periods: int = 12):
        """
        forecast_periods:
        Number of future steps.

        Each step = 5 minutes.
        12 steps = 60 minutes.
        """
        self.forecast_periods = forecast_periods

        self.models: Dict[str, Dict[str, object]] = {}

        self.recent_history: Dict[
            str, Dict[str, np.ndarray]
        ] = {}

        self.is_trained = False

        self._services_trained: List[str] = []

        self._sampling_interval_minutes = 5

    def train(self, df: pd.DataFrame) -> Dict:
        """
        Train one forecasting model for every
        service + metric combination.
        """

        if "timestamp" not in df.columns:
            raise ValueError(
                "DataFrame must have 'timestamp' column"
            )

        if "service_name" not in df.columns:
            raise ValueError(
                "DataFrame must have 'service_name' column"
            )

        df = df.copy()

        # Convert timestamp to datetime
        if df["timestamp"].dtype == "object":
            df["timestamp"] = pd.to_datetime(
                df["timestamp"]
            )

        services = df["service_name"].unique()

        total_models = 0
        failed_models = 0

        for service in services:

            svc_df = df[
                df["service_name"] == service
            ].sort_values("timestamp")

            self.models[service] = {}
            self.recent_history[service] = {}

            for metric in self.FORECAST_METRICS:

                if metric not in svc_df.columns:
                    continue

                series = svc_df[metric].values

                # Need enough historical data
                if len(series) < 12:
                    continue

                # Save recent history
                self.recent_history[service][metric] = (
                    series[-24:]
                )

                try:

                    model = ExponentialSmoothing(
                        series,
                        trend="add",
                        seasonal=None,
                        initialization_method="estimated",
                    )

                    try:

                        fitted = model.fit(
                            optimized=True,
                            use_brute=False,
                            method="lbfgs",
                        )

                    except Exception as e:

                        logger.warning(
                            f"Fast fit failed for "
                            f"{service}/{metric}: {e}. "
                            f"Using fallback."
                        )

                        fitted = model.fit(
                            optimized=False,
                            smoothing_level=0.3,
                            smoothing_trend=0.1,
                        )

                    self.models[service][metric] = fitted

                    total_models += 1

                except Exception as e:

                    logger.warning(
                        f"Failed to train "
                        f"{service}/{metric}: {e}"
                    )

                    failed_models += 1

        self._services_trained = list(
            self.models.keys()
        )

        self.is_trained = True

        logger.info(
            f"FailureForecaster trained: "
            f"{total_models} models across "
            f"{len(services)} services "
            f"({failed_models} failures)"
        )

        return {
            "services_trained": len(services),
            "models_trained": total_models,
            "models_failed": failed_models,
            "forecast_horizon_minutes": (
                self.forecast_periods
                * self._sampling_interval_minutes
            ),
        }

    def forecast(self, service_name: str) -> Dict:
        """
        Forecast future metric values and
        evaluate threshold breach risk.
        """

        if not self.is_trained:
            raise RuntimeError(
                "FailureForecaster not trained. "
                "Call train() first."
            )

        if (
            service_name not in self.recent_history
            or not self.recent_history[service_name]
        ):
            return {
                "forecast_risk": 0.0,
                "predicted_failure_type": "none",
                "prediction_horizon_minutes": 0,
                "trend_direction": "unknown",
            }

        worst_risk = 0.0
        worst_failure_type = "none"
        worst_horizon = 0
        overall_trend = "stable"

        for metric, history in (
            self.recent_history[service_name].items()
        ):

            threshold = self.FAILURE_THRESHOLDS.get(
                metric,
                float("inf")
            )

            if len(history) < 6:
                continue

            current_val = float(history[-1])

            # -------------------------------
            # Exponential Smoothing Forecast
            # -------------------------------

            fitted_model = (
                self.models
                .get(service_name, {})
                .get(metric)
            )

            es_forecast = None

            if fitted_model is not None:

                try:

                    es_forecast = fitted_model.forecast(
                        self.forecast_periods
                    )

                except Exception:

                    es_forecast = None

            # -------------------------------
            # Velocity Analysis
            # -------------------------------

            short_window = history[-6:]

            velocity = np.mean(
                np.diff(short_window)
            )

            # -------------------------------
            # Acceleration Analysis
            # -------------------------------

            if len(short_window) >= 4:

                diffs = np.diff(short_window)

                acceleration = np.mean(
                    np.diff(diffs)
                )

            else:

                acceleration = 0.0

            # -------------------------------
            # Future Trajectory
            # -------------------------------

            steps = np.arange(
                1,
                self.forecast_periods + 1
            )

            accel_factor = max(
                0.0,
                acceleration
            )

            velocity_trajectory = (
                current_val
                + velocity * steps
                + 0.5
                * accel_factor
                * (steps ** 2)
            )

            # Combine both forecasts

            if es_forecast is not None:

                combined_trajectory = (
                    0.5 * np.array(es_forecast)
                    + 0.5 * velocity_trajectory
                )

            else:

                combined_trajectory = (
                    velocity_trajectory
                )

            # -------------------------------
            # Threshold Detection
            # -------------------------------

            breach_idx = None

            for i, val in enumerate(
                combined_trajectory
            ):

                if val >= threshold:

                    breach_idx = i

                    break

            metric_risk = 0.0
            horizon_min = 0

            # -------------------------------
            # Threshold Breached
            # -------------------------------

            if breach_idx is not None:

                horizon_min = (
                    breach_idx + 1
                ) * self._sampling_interval_minutes

                urgency = (
                    1.0
                    - (
                        breach_idx
                        / self.forecast_periods
                    )
                    * 0.4
                )

                metric_risk = min(
                    1.0,
                    max(0.5, urgency)
                )

            # -------------------------------
            # Approaching Threshold
            # -------------------------------

            else:

                max_proj = float(
                    np.max(combined_trajectory)
                )

                proximity = (
                    max_proj / threshold
                    if threshold > 0
                    else 0
                )

                if (
                    proximity >= 0.75
                    and velocity > 0
                ):

                    metric_risk = min(
                        0.85,
                        proximity * 0.75
                    )

                    remaining_dist = (
                        threshold
                        - current_val
                    )

                    if velocity > 0:

                        est_steps = (
                            remaining_dist
                            / velocity
                        )

                        horizon_min = int(
                            min(
                                60,
                                max(
                                    5,
                                    est_steps * 5
                                )
                            )
                        )

                    else:

                        horizon_min = 60

                elif current_val >= (
                    threshold * 0.8
                ):

                    metric_risk = round(
                        current_val
                        / threshold
                        * 0.5,
                        2
                    )

                    horizon_min = 60

            # -------------------------------
            # Trend Detection
            # -------------------------------

            if velocity > (
                0.01 * threshold
            ):

                trend = "rising"

            elif velocity < (
                -0.01 * threshold
            ):

                trend = "falling"

            else:

                trend = "stable"

            # -------------------------------
            # Keep Worst Risk
            # -------------------------------

            if metric_risk > worst_risk:

                worst_risk = metric_risk

                worst_failure_type = (
                    self.METRIC_TO_FAILURE_TYPE.get(
                        metric,
                        "none"
                    )
                )

                worst_horizon = horizon_min

                overall_trend = trend

        return {
            "forecast_risk": round(
                worst_risk,
                4
            ),
            "predicted_failure_type":
                worst_failure_type,
            "prediction_horizon_minutes":
                worst_horizon,
            "trend_direction":
                overall_trend,
        }


if __name__ == "__main__":

    from app.services.csv_loader import CSVLoader

    loader = CSVLoader()

    df = loader.load_metrics()

    forecaster = FailureForecaster(
        forecast_periods=12
    )

    summary = forecaster.train(df)

    print("\n--- Training Summary ---")

    for k, v in summary.items():

        print(f"  {k}: {v}")

    print("\n--- Sample Forecasts ---")

    for service in [
        "order-service",
        "postgres-primary",
        "api-gateway",
    ]:

        result = forecaster.forecast(service)

        print(f"\n  {service}:")

        for k, v in result.items():

            print(f"    {k}: {v}")