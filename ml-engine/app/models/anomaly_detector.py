"""
ml-engine/app/models/anomaly_detector.py
Owner: Person 2 | Week: 2

Isolation Forest based anomaly detection on streaming server metrics
(cpu_usage, memory_usage, disk_io, network_latency_ms, error_rate, etc. —
see sample-data/sample_metrics.csv for the exact column set to train against).
- train(): fit Isolation Forest on historical metric windows
- predict(): score a new metric window, return anomaly score
Called by services/risk_engine.py.
"""
