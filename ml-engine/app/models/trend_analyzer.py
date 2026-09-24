"""
ml-engine/app/models/trend_analyzer.py

Advanced time-series analysis using Statsmodels.
Provides STL decomposition, Holt-Winters seasonal forecasting,
multi-variate correlation, and change-point detection.

Enhances the RiskEngine with deeper predictive analytics.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from loguru import logger

try:
    from statsmodels.tsa.seasonal import STL
    from statsmodels.tsa.holtwinters import ExponentialSmoothing
    from statsmodels.tsa.stattools import adfuller
    STATSMODELS_AVAILABLE = True
except ImportError:
    STATSMODELS_AVAILABLE = False
    logger.warning("[TrendAnalyzer] statsmodels not available")


class TrendAnalyzer:
    """
    Advanced time-series analysis for service metrics.
    Combines STL decomposition, Holt-Winters forecasting,
    and change-point detection for comprehensive trend analysis.
    """

    def __init__(self, forecast_periods: int = 12):
        self.forecast_periods = forecast_periods

    # -----------------------------------------------------------------
    # STL Decomposition
    # -----------------------------------------------------------------

    def decompose(
        self, series: pd.Series, period: int = 12
    ) -> Optional[Dict]:
        """
        Perform STL (Seasonal and Trend decomposition using Loess).

        Returns:
            Dict with trend, seasonal, residual components and
            anomaly flags from residuals.
        """
        if not STATSMODELS_AVAILABLE:
            return None

        if len(series) < 2 * period:
            logger.warning(
                f"[TrendAnalyzer] Series too short for STL "
                f"({len(series)} < {2 * period})"
            )
            return None

        try:
            stl = STL(series, period=period, robust=True)
            result = stl.fit()

            # Anomalies: residuals beyond 2 standard deviations
            residual_std = result.resid.std()
            residual_mean = result.resid.mean()
            anomaly_mask = (
                (result.resid > residual_mean + 2 * residual_std)
                | (result.resid < residual_mean - 2 * residual_std)
            )

            return {
                "trend": result.trend.tolist(),
                "seasonal": result.seasonal.tolist(),
                "residual": result.resid.tolist(),
                "anomaly_indices": list(
                    np.where(anomaly_mask)[0].astype(int)
                ),
                "anomaly_count": int(anomaly_mask.sum()),
                "trend_direction": self._trend_direction(result.trend),
                "residual_std": round(float(residual_std), 4),
            }
        except Exception as exc:
            logger.error(f"[TrendAnalyzer] STL decomposition failed: {exc}")
            return None

    # -----------------------------------------------------------------
    # Holt-Winters Forecasting
    # -----------------------------------------------------------------

    def forecast_holt_winters(
        self,
        series: pd.Series,
        periods: Optional[int] = None,
        seasonal: str = "add",
        seasonal_periods: int = 12,
    ) -> Optional[Dict]:
        """
        Holt-Winters exponential smoothing forecast with confidence intervals.

        Returns:
            Dict with forecast values, confidence intervals, and trend.
        """
        if not STATSMODELS_AVAILABLE:
            return None

        periods = periods or self.forecast_periods

        if len(series) < 2 * seasonal_periods:
            logger.warning("[TrendAnalyzer] Series too short for Holt-Winters")
            return None

        try:
            model = ExponentialSmoothing(
                series,
                trend="add",
                seasonal=seasonal,
                seasonal_periods=seasonal_periods,
                initialization_method="estimated",
            )
            fitted = model.fit(optimized=True)

            # Forecast
            forecast = fitted.forecast(periods)

            # Confidence intervals (approximate using residual std)
            residuals = fitted.resid
            residual_std = residuals.std()
            ci_multiplier = 1.96  # 95% CI

            forecast_lower = forecast - ci_multiplier * residual_std
            forecast_upper = forecast + ci_multiplier * residual_std

            return {
                "forecast_values": forecast.tolist(),
                "confidence_interval_lower": forecast_lower.tolist(),
                "confidence_interval_upper": forecast_upper.tolist(),
                "confidence_level": 0.95,
                "periods_ahead": periods,
                "model_aic": round(float(fitted.aic), 2),
                "residual_std": round(float(residual_std), 4),
            }
        except Exception as exc:
            logger.error(f"[TrendAnalyzer] Holt-Winters failed: {exc}")
            return None

    # -----------------------------------------------------------------
    # Multi-variate Correlation
    # -----------------------------------------------------------------

    def correlate_metrics(
        self, metrics_df: pd.DataFrame, target_col: str = "error_rate"
    ) -> Dict:
        """
        Compute cross-correlations between the target metric and all other
        numeric columns. Identifies which metrics are most strongly correlated
        with the target (e.g., error_rate).

        Args:
            metrics_df: DataFrame with multiple metric columns
            target_col: The target metric to correlate against

        Returns:
            Dict with correlation matrix and top correlated features.
        """
        numeric_cols = metrics_df.select_dtypes(include=[np.number]).columns
        if target_col not in numeric_cols:
            return {"error": f"Target column '{target_col}' not found"}

        try:
            correlations = metrics_df[numeric_cols].corr()[target_col]
            correlations = correlations.drop(target_col, errors="ignore")

            sorted_corrs = correlations.abs().sort_values(ascending=False)

            return {
                "target_metric": target_col,
                "correlations": {
                    col: round(float(correlations[col]), 4)
                    for col in sorted_corrs.index
                },
                "top_correlated": [
                    {
                        "metric": col,
                        "correlation": round(float(correlations[col]), 4),
                        "direction": "positive" if correlations[col] > 0 else "negative",
                        "strength": (
                            "strong" if abs(correlations[col]) > 0.7
                            else "moderate" if abs(correlations[col]) > 0.4
                            else "weak"
                        ),
                    }
                    for col in sorted_corrs.index[:5]
                ],
            }
        except Exception as exc:
            logger.error(f"[TrendAnalyzer] Correlation failed: {exc}")
            return {"error": str(exc)}

    # -----------------------------------------------------------------
    # Change-Point Detection
    # -----------------------------------------------------------------

    def detect_change_points(
        self, series: pd.Series, window: int = 10, threshold: float = 2.0
    ) -> List[Dict]:
        """
        Detect change points in a time series using rolling statistics.
        A change point is detected when the local mean shifts by more
        than `threshold` standard deviations.

        Returns:
            List of detected change points with index and magnitude.
        """
        if len(series) < 2 * window:
            return []

        try:
            rolling_mean = series.rolling(window=window, center=True).mean()
            rolling_std = series.rolling(window=window, center=True).std()

            # Calculate z-scores of differences between consecutive windows
            diffs = rolling_mean.diff()
            overall_std = series.std()

            change_points = []
            for i in range(window, len(series) - window):
                if pd.isna(diffs.iloc[i]) or pd.isna(rolling_std.iloc[i]):
                    continue

                z_score = abs(diffs.iloc[i]) / (overall_std + 1e-10)
                if z_score > threshold:
                    change_points.append({
                        "index": int(i),
                        "z_score": round(float(z_score), 3),
                        "magnitude": round(float(diffs.iloc[i]), 4),
                        "direction": "increase" if diffs.iloc[i] > 0 else "decrease",
                    })

            return change_points
        except Exception as exc:
            logger.error(f"[TrendAnalyzer] Change-point detection failed: {exc}")
            return []

    # -----------------------------------------------------------------
    # Stationarity Test
    # -----------------------------------------------------------------

    def test_stationarity(self, series: pd.Series) -> Dict:
        """
        Run the Augmented Dickey-Fuller test for stationarity.
        Non-stationary series may indicate a trend or structural change.
        """
        if not STATSMODELS_AVAILABLE:
            return {"error": "statsmodels not available"}

        try:
            result = adfuller(series.dropna(), autolag="AIC")
            return {
                "test_statistic": round(float(result[0]), 4),
                "p_value": round(float(result[1]), 6),
                "lags_used": int(result[2]),
                "observations": int(result[3]),
                "is_stationary": result[1] < 0.05,
                "critical_values": {
                    k: round(float(v), 4) for k, v in result[4].items()
                },
            }
        except Exception as exc:
            logger.error(f"[TrendAnalyzer] ADF test failed: {exc}")
            return {"error": str(exc)}

    # -----------------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------------

    @staticmethod
    def _trend_direction(trend: pd.Series) -> str:
        """Determine overall trend direction from STL trend component."""
        if len(trend) < 2:
            return "flat"
        start_avg = trend.iloc[:5].mean()
        end_avg = trend.iloc[-5:].mean()
        diff_pct = ((end_avg - start_avg) / (abs(start_avg) + 1e-10)) * 100
        if diff_pct > 5:
            return "increasing"
        elif diff_pct < -5:
            return "decreasing"
        return "stable"


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------
_analyzer: Optional[TrendAnalyzer] = None


def get_trend_analyzer() -> TrendAnalyzer:
    global _analyzer
    if _analyzer is None:
        _analyzer = TrendAnalyzer()
    return _analyzer
