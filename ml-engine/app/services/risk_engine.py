"""
ml-engine/app/services/risk_engine.py
Owner: Person 2 | Week: 2

Composite RiskScorer — combines anomaly_detector.py and failure_forecaster.py
output into a single risk score with confidence interval (per README's
"Composite risk scores with confidence intervals" capability).
Applies the tiered risk thresholds agreed with Person 1 in Week 2
(e.g. <0.4 healthy, 0.4-0.75 watch, >=0.75 incident-triggering).
Called by api/risk_score.py.
"""
