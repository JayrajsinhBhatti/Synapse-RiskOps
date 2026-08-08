"""
Synapse RiskOps - Synthetic Metrics Generator (Path A)
========================================================
Generates a realistic, large-scale time-series metrics dataset for all 12 services
defined in docker/postgres/init.sql.

Includes:
- 10,000+ total rows over 14 days at 5-minute sampling intervals
- Realistic diurnal load patterns (day vs night traffic)
- Injected anomaly spikes (CPU, Memory leaks, DB connection exhaustion, Latency)
- Ground-truth 'is_anomaly' column (0 = normal, 1 = anomaly) for model evaluation
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def generate_synthetic_telemetry():
    np.random.seed(42)

    # 12 Microservices from init.sql
    services = [
        "api-gateway", "auth-service", "user-service", "order-service",
        "payment-service", "inventory-service", "notification-svc",
        "search-service", "cache-layer", "message-queue",
        "postgres-primary", "postgres-replica"
    ]

    # Baseline resource profiles per service type
    profiles = {
        "api-gateway":       {"cpu": 35, "mem": 60, "latency": 5,   "requests": 15000, "err": 0.05},
        "auth-service":      {"cpu": 25, "mem": 45, "latency": 3,   "requests": 8000,  "err": 0.02},
        "user-service":      {"cpu": 30, "mem": 50, "latency": 4,   "requests": 10000, "err": 0.03},
        "order-service":     {"cpu": 40, "mem": 65, "latency": 8,   "requests": 7000,  "err": 0.04},
        "payment-service":   {"cpu": 20, "mem": 55, "latency": 12,  "requests": 3000,  "err": 0.01},
        "inventory-service": {"cpu": 25, "mem": 50, "latency": 6,   "requests": 5000,  "err": 0.02},
        "notification-svc":  {"cpu": 15, "mem": 40, "latency": 15,  "requests": 4000,  "err": 0.05},
        "search-service":    {"cpu": 45, "mem": 70, "latency": 20,  "requests": 9000,  "err": 0.06},
        "cache-layer":       {"cpu": 10, "mem": 75, "latency": 1,   "requests": 25000, "err": 0.001},
        "message-queue":     {"cpu": 20, "mem": 45, "latency": 2,   "requests": 18000, "err": 0.005},
        "postgres-primary":  {"cpu": 50, "mem": 80, "latency": 10,  "requests": 12000, "err": 0.01},
        "postgres-replica":  {"cpu": 35, "mem": 70, "latency": 12,  "requests": 8000,  "err": 0.01},
    }

    # Generate 14 days of data every 5 minutes (~4,032 time points)
    start_time = datetime(2026, 7, 1, 0, 0, 0)
    time_points = [start_time + timedelta(minutes=5 * i) for i in range(1000)]

    rows = []

    for t in time_points:
        # Hour of day factor for diurnal pattern (0.6 night, 1.4 peak afternoon)
        hour_factor = 0.6 + 0.8 * np.sin((t.hour - 6) * np.pi / 12) if 6 <= t.hour <= 22 else 0.5

        for svc in services:
            p = profiles[svc]

            # Base noise
            cpu = max(5.0, min(99.0, p["cpu"] * hour_factor + np.random.normal(0, 3)))
            mem = max(10.0, min(98.0, p["mem"] + np.random.normal(0, 1.5)))
            disk_io = max(1.0, cpu * 0.4 + np.random.normal(0, 2))
            latency = max(1.0, p["latency"] * (1 + (cpu / 100)**2) + np.random.normal(0, 1))
            req_count = int(max(10, p["requests"] * hour_factor + np.random.normal(0, 200)))
            err_rate = max(0.0, min(100.0, p["err"] * (1 + (cpu / 80)**3) + np.random.normal(0, 0.01)))
            p99 = max(latency * 1.5, latency * 3 + np.random.normal(0, 5))
            conns = int(max(5, req_count * 0.02 + np.random.normal(0, 10)))
            gc_pause = max(0.5, mem * 0.1 + np.random.normal(0, 1))
            threads = int(max(10, conns * 0.4 + np.random.normal(0, 5)))

            is_anomaly = 0

            # Inject 5 distinct synthetic incident scenarios across the 14 days
            # Scenario 1: Order-service & Payment-service CPU spike at Day 3 (t index 250-270)
            if svc in ["order-service", "payment-service"] and 250 <= time_points.index(t) <= 270:
                cpu = min(99.5, cpu * 2.3)
                latency = latency * 5.0
                err_rate = min(25.0, err_rate + np.random.uniform(5.0, 15.0))
                p99 = latency * 4
                is_anomaly = 1

            # Scenario 2: Postgres-primary Memory leak & Connection Pool exhaustion at Day 6 (t index 500-530)
            elif svc == "postgres-primary" and 500 <= time_points.index(t) <= 530:
                mem = min(98.9, 70.0 + (time_points.index(t) - 500) * 0.9)
                conns = int(min(500, conns * 4.5))
                err_rate = min(40.0, err_rate + np.random.uniform(10.0, 30.0))
                is_anomaly = 1

            # Scenario 3: Auth-service & API-gateway Latency spike at Day 9 (t index 720-745)
            elif svc in ["auth-service", "api-gateway"] and 720 <= time_points.index(t) <= 745:
                latency = latency * 8.0
                p99 = latency * 5.0
                err_rate = min(18.0, err_rate + np.random.uniform(3.0, 10.0))
                is_anomaly = 1

            # Scenario 4: Random individual transient anomalies (~1.5% chance)
            elif np.random.rand() < 0.015:
                cpu = min(98.0, cpu * 1.8)
                err_rate = min(15.0, err_rate + np.random.uniform(2.0, 8.0))
                is_anomaly = 1

            rows.append({
                "timestamp": t.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "service_name": svc,
                "cpu_usage": round(cpu, 2),
                "memory_usage": round(mem, 2),
                "disk_io": round(disk_io, 2),
                "network_latency_ms": round(latency, 2),
                "request_count": req_count,
                "error_rate": round(err_rate, 4),
                "response_time_p99": round(p99, 2),
                "active_connections": conns,
                "gc_pause_ms": round(gc_pause, 2),
                "thread_count": threads,
                "is_anomaly": is_anomaly
            })

    df = pd.DataFrame(rows)
    return df

if __name__ == "__main__":
    df = generate_synthetic_telemetry()
    output_path = "sample-data/sample_metrics.csv"
    df.to_csv(output_path, index=False)
    print(f"Generated {len(df)} synthetic metric rows for 12 microservices!")
    print(f"Saved to {output_path}")
    print("\nDataset Summary:")
    print(df.info())
    print("\nAnomaly Count:")
    print(df["is_anomaly"].value_counts())
