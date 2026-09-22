"""
Tests for TrendAnalyzer (Statsmodels STL, Holt-Winters, Correlation, Change-Points).
"""

import sys
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

ML_ENGINE_ROOT = Path(__file__).resolve().parent.parent
if str(ML_ENGINE_ROOT) not in sys.path:
    sys.path.insert(0, str(ML_ENGINE_ROOT))

from app.models.trend_analyzer import TrendAnalyzer


@pytest.fixture
def analyzer():
    return TrendAnalyzer(forecast_periods=12)


@pytest.fixture
def sample_series():
    # 72 points with trend + sine seasonality + noise
    np.random.seed(42)
    t = np.arange(72)
    trend = 0.5 * t
    seasonal = 5.0 * np.sin(2 * np.pi * t / 12)
    noise = np.random.normal(0, 0.5, size=72)
    return pd.Series(trend + seasonal + noise)


@pytest.fixture
def sample_multivariate_df():
    np.random.seed(42)
    n = 60
    cpu = np.random.uniform(20, 90, n)
    # error_rate strongly correlated with cpu
    error_rate = 0.05 * cpu + np.random.normal(0, 0.2, n)
    memory = np.random.uniform(40, 80, n)
    return pd.DataFrame({
        "cpu_usage": cpu,
        "error_rate": error_rate,
        "memory_usage": memory,
    })


def test_stl_decomposition(analyzer, sample_series):
    result = analyzer.decompose(sample_series, period=12)
    assert result is not None
    assert "trend" in result
    assert "seasonal" in result
    assert "residual" in result
    assert len(result["trend"]) == len(sample_series)
    assert result["trend_direction"] in ("increasing", "decreasing", "stable", "rising", "falling")


def test_holt_winters_forecast_with_ci(analyzer, sample_series):
    result = analyzer.forecast_holt_winters(sample_series, periods=12, seasonal_periods=12)
    assert result is not None
    assert "forecast_values" in result
    assert "confidence_interval_lower" in result
    assert "confidence_interval_upper" in result
    assert len(result["forecast_values"]) == 12
    assert len(result["confidence_interval_lower"]) == 12
    # Upper CI >= lower CI
    for low, up in zip(result["confidence_interval_lower"], result["confidence_interval_upper"]):
        assert up >= low


def test_correlate_metrics(analyzer, sample_multivariate_df):
    result = analyzer.correlate_metrics(sample_multivariate_df, target_col="error_rate")
    assert "correlations" in result
    assert "cpu_usage" in result["correlations"]
    assert "top_correlated" in result
    # cpu_usage should have strong positive correlation with error_rate
    assert result["correlations"]["cpu_usage"] > 0.8


def test_detect_change_points(analyzer):
    # Series with abrupt jump from 10 to 50 at index 25
    data = [10.0 + np.random.normal(0, 0.2) for _ in range(25)] + [50.0 + np.random.normal(0, 0.2) for _ in range(25)]
    series = pd.Series(data)
    change_points = analyzer.detect_change_points(series, window=5, threshold=0.3)
    assert len(change_points) > 0
    assert any(cp["direction"] == "increase" for cp in change_points)
