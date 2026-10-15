"""
Synapse RiskOps - Conformal Risk Intervals Test Suite
=====================================================
Tests:
- Split Conformal Prediction calibration procedure and quantile cutoff math.
- Conformal interval prediction (point estimate, lower, upper, interval_width, coverage).
- Boundary clipping strictly within [0, 100].
- Explicit handling of insufficient calibration data (no fabricated bounds).
- Empirical coverage validity on held-out exchangeable test data.
- End-to-end integration with RiskEngine, PredictionResponse schema, and backward compatibility.
- Disclaimers verifying the interval is NOT presented as a failure probability.
"""

import sys
import math
import numpy as np
import pandas as pd
import pytest
from pathlib import Path

# Add ml-engine root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.conformal_calibrator import ConformalCalibrator
from app.services.risk_engine import RiskEngine
from app.services.csv_loader import CSVLoader
from app.schemas.prediction import (
    ConformalInterval,
    PredictionResponse,
    ModelStatusResponse,
    RiskTier,
    AnomalyDetail,
    ForecastDetail,
)


# ==============================================================================
# PART 1: CONFORMAL CALIBRATOR UNIT TESTS
# ==============================================================================

def test_conformal_quantile_formula_exact_order_statistic():
    """Verify finite-sample quantile cutoff math matches ceil((n+1)(1-alpha))."""
    calibrator = ConformalCalibrator(min_samples=30)
    
    # 100 sorted nonconformity scores: 1.0, 2.0, ..., 100.0
    y_true = np.arange(1, 101, dtype=float)
    y_pred = np.zeros(100, dtype=float)  # Residuals are 1, 2, ..., 100
    
    summary = calibrator.calibrate(y_true, y_pred, target_coverage=0.90)
    assert summary["is_calibrated"] is True
    assert summary["calibration_samples"] == 100
    
    # For n=100, 1-alpha=0.90: ceil(101 * 0.90) = ceil(90.9) = 91 -> 91st order statistic is 91.0
    expected_rank = math.ceil((100 + 1) * 0.90)
    assert expected_rank == 91
    assert calibrator.q_hat == 91.0


def test_conformal_predict_interval_and_width():
    """Verify interval generation, width consistency, and metadata."""
    calibrator = ConformalCalibrator(min_samples=30)
    
    # Residuals uniformly spread with q_hat = 10.0
    residuals = np.linspace(1, 15, 50)
    y_true = 50.0 + residuals
    y_pred = np.full(50, 50.0)
    
    calibrator.calibrate(y_true, y_pred, target_coverage=0.90)
    assert calibrator.is_calibrated is True
    
    point_est = 60.0
    interval = calibrator.predict_interval(point_est, target_coverage=0.90)
    
    assert isinstance(interval, ConformalInterval)
    assert interval.point_estimate == point_est
    assert interval.lower is not None
    assert interval.upper is not None
    assert interval.lower < point_est < interval.upper
    assert interval.interval_width == round(interval.upper - interval.lower, 2)
    assert interval.target_coverage == 0.90
    assert interval.is_calibrated is True
    assert interval.status == "calibrated"
    assert interval.method == "split_conformal_residual"


def test_boundary_clipping_strictly_within_0_to_100():
    """Verify bounds are strictly clipped to [0, 100] without exceeding domain."""
    calibrator = ConformalCalibrator(min_samples=30)
    # Calibrate with q_hat = 15.0
    y_true = np.linspace(10, 25, 40)
    y_pred = np.full(40, 10.0)
    calibrator.calibrate(y_true, y_pred, target_coverage=0.90)
    q = calibrator.q_hat
    assert q > 10.0
    
    # Case 1: High risk point estimate (e.g. 95.0) -> raw upper would exceed 100
    high_res = calibrator.predict_interval(95.0)
    assert high_res.upper == 100.0
    assert high_res.lower >= 0.0
    assert high_res.interval_width == round(100.0 - high_res.lower, 2)
    
    # Case 2: Extreme maximum 100.0
    max_res = calibrator.predict_interval(100.0)
    assert max_res.upper == 100.0
    assert max_res.lower == round(100.0 - q, 2)
    
    # Case 3: Low risk point estimate (e.g. 5.0) -> raw lower would drop below 0
    low_res = calibrator.predict_interval(5.0)
    assert low_res.lower == 0.0
    assert low_res.upper <= 100.0
    assert low_res.interval_width == round(low_res.upper - 0.0, 2)
    
    # Case 4: Extreme minimum 0.0
    min_res = calibrator.predict_interval(0.0)
    assert min_res.lower == 0.0
    assert min_res.upper == round(0.0 + q, 2)
    
    # Case 5: Out of bounds input clipped defensively
    clamped_high = calibrator.predict_interval(120.0)
    assert clamped_high.point_estimate == 100.0
    assert clamped_high.upper == 100.0
    
    clamped_low = calibrator.predict_interval(-15.0)
    assert clamped_low.point_estimate == 0.0
    assert clamped_low.lower == 0.0


def test_insufficient_calibration_data_no_fabrication():
    """Verify that fewer than min_samples returns uncalibrated state with None bounds."""
    calibrator = ConformalCalibrator(min_samples=30)
    
    # Only 10 samples (well below 30)
    y_true = [10.0] * 10
    y_pred = [12.0] * 10
    
    summary = calibrator.calibrate(y_true, y_pred)
    assert summary["is_calibrated"] is False
    assert summary["status"] == "insufficient_data"
    assert summary["calibration_samples"] == 10
    assert summary["q_hat"] is None
    
    interval = calibrator.predict_interval(50.0)
    assert interval.is_calibrated is False
    assert interval.status == "insufficient_data"
    assert interval.lower is None
    assert interval.upper is None
    assert interval.interval_width is None
    assert interval.point_estimate == 50.0
    assert interval.q_hat is None


def test_empty_or_uncalibrated_state():
    """Verify freshly instantiated calibrator safely reports uncalibrated."""
    calibrator = ConformalCalibrator()
    assert calibrator.is_calibrated is False
    assert calibrator.status == "uncalibrated"
    
    interval = calibrator.predict_interval(75.0)
    assert interval.is_calibrated is False
    assert interval.status == "uncalibrated"
    assert interval.lower is None
    assert interval.upper is None
    assert interval.interval_width is None
    assert interval.point_estimate == 75.0


def test_empirical_coverage_on_exchangeable_held_out_data():
    """
    Verify split conformal prediction satisfies empirical coverage >= 1 - alpha
    under exchangeable data distributions.
    """
    np.random.seed(42)
    n_cal = 300
    n_test = 500
    alpha = 0.10  # 90% target coverage
    target_cov = 1.0 - alpha
    
    # Generate simulated exchangeable ground-truth and predictions
    true_risk_all = np.random.uniform(10.0, 90.0, size=n_cal + n_test)
    noise_all = np.random.normal(0.0, 5.0, size=n_cal + n_test)
    pred_risk_all = np.clip(true_risk_all + noise_all, 0.0, 100.0)
    
    y_cal_true = true_risk_all[:n_cal]
    y_cal_pred = pred_risk_all[:n_cal]
    
    y_test_true = true_risk_all[n_cal:]
    y_test_pred = pred_risk_all[n_cal:]
    
    calibrator = ConformalCalibrator(min_samples=30)
    calibrator.calibrate(y_cal_true, y_cal_pred, target_coverage=target_cov)
    
    eval_res = calibrator.evaluate_empirical_coverage(y_test_true, y_test_pred, target_coverage=target_cov)
    
    # Finite-sample marginal coverage guarantee: should be approximately >= 90% (within statistical binomial tolerance)
    assert eval_res["empirical_coverage"] >= 0.87
    assert eval_res["target_coverage"] == 0.90
    assert eval_res["mean_interval_width"] > 0.0


# ==============================================================================
# PART 2: END-TO-END RISK ENGINE INTEGRATION TESTS
# ==============================================================================

@pytest.fixture(scope="module")
def trained_risk_engine():
    loader = CSVLoader()
    df = loader.load_metrics()
    
    engine = RiskEngine()
    # Train on first 1000 rows (sufficient for train + held-out calibration)
    engine.train(df.iloc[:1000])
    return engine


def test_risk_engine_score_returns_conformal_interval(trained_risk_engine):
    """Verify RiskEngine.score generates calibrated conformal interval in PredictionResponse."""
    engine = trained_risk_engine
    assert engine.conformal_calibrator.is_calibrated is True
    
    test_metrics = {
        "cpu_usage": 75.0, "memory_usage": 80.0, "disk_io": 25.0,
        "network_latency_ms": 30.0, "request_count": 6000, "error_rate": 2.5,
        "response_time_p99": 90.0, "active_connections": 180, "gc_pause_ms": 15.0, "thread_count": 70,
    }
    
    resp = engine.score("order-service", test_metrics)
    assert isinstance(resp, PredictionResponse)
    assert resp.conformal_interval is not None
    ci = resp.conformal_interval
    
    # Interval sanity
    assert ci.is_calibrated is True
    assert ci.status == "calibrated"
    assert ci.point_estimate == resp.risk_score
    assert ci.lower is not None and ci.upper is not None
    assert 0.0 <= ci.lower <= resp.risk_score <= ci.upper <= 100.0
    assert ci.interval_width == round(ci.upper - ci.lower, 2)
    assert ci.target_coverage == 0.90
    assert ci.calibration_samples > 0
    assert ci.q_hat is not None
    
    # Backward compatibility: confidence_interval dict populated
    assert resp.confidence_interval is not None
    assert resp.confidence_interval["lower"] == ci.lower
    assert resp.confidence_interval["upper"] == ci.upper


def test_risk_engine_status_reports_conformal_metrics(trained_risk_engine):
    """Verify GET /api/model/status shape contains conformal calibrator fields."""
    engine = trained_risk_engine
    status = engine.get_status()
    
    model_status = ModelStatusResponse(**status)
    assert model_status.conformal_calibrated is True
    assert model_status.conformal_status == "calibrated"
    assert model_status.conformal_samples > 0
    assert model_status.conformal_q_hat is not None
    assert model_status.conformal_coverage == 0.90


def test_insufficient_data_training_preserves_engine_without_fabricated_bounds():
    """Verify that training on very small dataset (< 30) yields uncalibrated status and None bounds."""
    loader = CSVLoader()
    df = loader.load_metrics()
    
    engine = RiskEngine()
    engine.train(df.iloc[:20])  # Only 20 samples
    
    assert engine.conformal_calibrator.is_calibrated is False
    assert engine.conformal_calibrator.status == "insufficient_data"
    
    test_metrics = {
        "cpu_usage": 30.0, "memory_usage": 40.0, "disk_io": 10.0,
        "network_latency_ms": 5.0, "request_count": 5000, "error_rate": 0.01,
        "response_time_p99": 20.0, "active_connections": 50, "gc_pause_ms": 5.0, "thread_count": 25,
    }
    resp = engine.score("auth-service", test_metrics)
    assert resp.conformal_interval is not None
    assert resp.conformal_interval.is_calibrated is False
    assert resp.conformal_interval.status == "insufficient_data"
    assert resp.conformal_interval.lower is None
    assert resp.conformal_interval.upper is None
    assert resp.conformal_interval.interval_width is None


def test_disclaimer_and_no_failure_probability_language():
    """Verify conformal documentation states intervals quantify risk score estimation, NOT failure probability."""
    calibrator = ConformalCalibrator()
    note = calibrator.ASSUMPTION_NOTE
    assert "exchangeability" in note.lower()
    assert "probability of failure" in note.lower()
    assert "not" in note.lower()
