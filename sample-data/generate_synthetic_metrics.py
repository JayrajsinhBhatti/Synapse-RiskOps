"""
Synapse RiskOps - Synthetic Metrics Generator v2 (With Scenario JSON Export)
=============================================================================
Generates a production-realistic, large-scale time-series metrics dataset
for all 12 services defined in docker/postgres/init.sql.

Outputs:
1. sample-data/sample_metrics.csv (48,384 rows, 14 days, 12 microservices)
2. sample-data/simulated_incidents/scenario_01.json
3. sample-data/simulated_incidents/scenario_02.json
4. sample-data/simulated_incidents/scenario_03.json
"""

import os
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta


def _degradation_curve(t_idx: int, ramp_start: int, ramp_end: int,
                       peak_start: int, peak_end: int,
                       recovery_end: int) -> float:
    if t_idx < ramp_start or t_idx > recovery_end:
        return 0.0
    if ramp_start <= t_idx < ramp_end:
        progress = (t_idx - ramp_start) / max(1, ramp_end - ramp_start)
        return 0.5 * progress
    if ramp_end <= t_idx < peak_start:
        progress = (t_idx - ramp_end) / max(1, peak_start - ramp_end)
        return 0.5 + 0.5 * progress
    if peak_start <= t_idx <= peak_end:
        return 1.0
    if peak_end < t_idx <= recovery_end:
        progress = (t_idx - peak_end) / max(1, recovery_end - peak_end)
        return 1.0 - progress
    return 0.0


def generate_synthetic_telemetry():
    np.random.seed(42)

    services = [
        "api-gateway", "auth-service", "user-service", "order-service",
        "payment-service", "inventory-service", "notification-svc",
        "search-service", "cache-layer", "message-queue",
        "postgres-primary", "postgres-replica",
    ]

    profiles = {
        "api-gateway":       {"cpu": 35, "mem": 60, "latency": 5,   "req": 15000, "err": 0.05, "disk": 14, "p99": 15,  "conn": 300, "gc": 6,  "thr": 120},
        "auth-service":      {"cpu": 25, "mem": 45, "latency": 3,   "req": 8000,  "err": 0.02, "disk": 10, "p99": 9,   "conn": 160, "gc": 4.5,"thr": 64},
        "user-service":      {"cpu": 30, "mem": 50, "latency": 4,   "req": 10000, "err": 0.03, "disk": 12, "p99": 12,  "conn": 200, "gc": 5,  "thr": 80},
        "order-service":     {"cpu": 40, "mem": 65, "latency": 8,   "req": 7000,  "err": 0.04, "disk": 26, "p99": 24,  "conn": 140, "gc": 6.5,"thr": 56},
        "payment-service":   {"cpu": 20, "mem": 55, "latency": 12,  "req": 3000,  "err": 0.01, "disk": 8,  "p99": 36,  "conn": 60,  "gc": 5.5,"thr": 24},
        "inventory-service": {"cpu": 25, "mem": 50, "latency": 6,   "req": 5000,  "err": 0.02, "disk": 10, "p99": 18,  "conn": 100, "gc": 5,  "thr": 40},
        "notification-svc":  {"cpu": 15, "mem": 40, "latency": 15,  "req": 4000,  "err": 0.05, "disk": 6,  "p99": 45,  "conn": 80,  "gc": 4,  "thr": 32},
        "search-service":    {"cpu": 45, "mem": 70, "latency": 20,  "req": 9000,  "err": 0.06, "disk": 18, "p99": 60,  "conn": 180, "gc": 7,  "thr": 72},
        "cache-layer":       {"cpu": 10, "mem": 75, "latency": 1,   "req": 25000, "err": 0.001,"disk": 4,  "p99": 3,   "conn": 500, "gc": 7.5,"thr": 200},
        "message-queue":     {"cpu": 20, "mem": 45, "latency": 2,   "req": 18000, "err": 0.005,"disk": 8,  "p99": 6,   "conn": 360, "gc": 4.5,"thr": 144},
        "postgres-primary":  {"cpu": 50, "mem": 80, "latency": 10,  "req": 12000, "err": 0.01, "disk": 40, "p99": 30,  "conn": 240, "gc": 8,  "thr": 96},
        "postgres-replica":  {"cpu": 35, "mem": 70, "latency": 12,  "req": 8000,  "err": 0.01, "disk": 30, "p99": 36,  "conn": 160, "gc": 7,  "thr": 64},
    }

    start_time = datetime(2026, 7, 1, 0, 0, 0)
    num_points = 14 * 24 * 12  # 4032 time points
    time_points = [start_time + timedelta(minutes=5 * i) for i in range(num_points)]

    # --- Scenario Timelines ---
    S1_ORDER = {"ramp_start": 576, "ramp_end": 720, "peak_start": 780, "peak_end": 816, "recovery_end": 888}
    S1_PAYMENT = {"ramp_start": 648, "ramp_end": 756, "peak_start": 792, "peak_end": 828, "recovery_end": 900}

    S2_PG_PRIMARY = {"ramp_start": 1728, "ramp_end": 1872, "peak_start": 1944, "peak_end": 1980, "recovery_end": 2052}
    S2_PG_REPLICA = {"ramp_start": 1800, "ramp_end": 1908, "peak_start": 1956, "peak_end": 1992, "recovery_end": 2064}
    S2_AUTH = {"ramp_start": 1872, "ramp_end": 1944, "peak_start": 1968, "peak_end": 1992, "recovery_end": 2040}
    S2_USER = {"ramp_start": 1896, "ramp_end": 1944, "peak_start": 1968, "peak_end": 1992, "recovery_end": 2040}

    S3_CACHE = {"ramp_start": 2880, "ramp_end": 3024, "peak_start": 3096, "peak_end": 3132, "recovery_end": 3204}
    S3_SEARCH = {"ramp_start": 2952, "ramp_end": 3060, "peak_start": 3108, "peak_end": 3144, "recovery_end": 3216}
    S3_GATEWAY = {"ramp_start": 3024, "ramp_end": 3096, "peak_start": 3120, "peak_end": 3144, "recovery_end": 3204}

    # Generate scenario metadata
    scenarios_meta = [
        {
            "scenario_id": "scenario_01",
            "name": "Order & Payment Service CPU Saturation Cascade",
            "affected_services": ["order-service", "payment-service"],
            "failure_time": time_points[S1_ORDER["peak_start"]].strftime("%Y-%m-%dT%H:%M:%SZ"),
            "expected_failure": "cpu_saturation",
        },
        {
            "scenario_id": "scenario_02",
            "name": "PostgreSQL Primary Memory Leak & Connection Exhaustion",
            "affected_services": ["postgres-primary", "postgres-replica", "auth-service", "user-service"],
            "failure_time": time_points[S2_PG_PRIMARY["peak_start"]].strftime("%Y-%m-%dT%H:%M:%SZ"),
            "expected_failure": "memory_exhaustion",
        },
        {
            "scenario_id": "scenario_03",
            "name": "Cache Failure & Search Service Latency Storm",
            "affected_services": ["cache-layer", "search-service", "api-gateway"],
            "failure_time": time_points[S3_CACHE["peak_start"]].strftime("%Y-%m-%dT%H:%M:%SZ"),
            "expected_failure": "latency_degradation",
        },
    ]

    rows = []
    for t_idx, t in enumerate(time_points):
        hour = t.hour + t.minute / 60.0
        hour_factor = (0.6 + 0.8 * np.sin((hour - 6) * np.pi / 16)) if (6 <= hour <= 22) else 0.5

        for svc in services:
            p = profiles[svc]
            cpu       = p["cpu"] * hour_factor + np.random.normal(0, 2.5)
            mem       = p["mem"] + np.random.normal(0, 1.2)
            disk      = p["disk"] * (0.8 + 0.4 * hour_factor) + np.random.normal(0, 1.5)
            latency   = p["latency"] * (0.9 + 0.2 * hour_factor) + np.random.normal(0, 0.5)
            req       = int(p["req"] * hour_factor + np.random.normal(0, p["req"] * 0.03))
            err       = p["err"] + np.random.normal(0, 0.005)
            p99       = p["p99"] * (0.9 + 0.2 * hour_factor) + np.random.normal(0, 1.0)
            conn      = int(p["conn"] * (0.7 + 0.6 * hour_factor) + np.random.normal(0, 8))
            gc        = p["gc"] + np.random.normal(0, 0.5)
            thr       = int(p["thr"] * (0.7 + 0.6 * hour_factor) + np.random.normal(0, 4))
            is_anomaly = 0

            # Apply scenarios
            if svc == "order-service":
                d = _degradation_curve(t_idx, **S1_ORDER)
                if d > 0:
                    cpu += d * 55; latency += d * 80; err += d * 18; p99 += d * 400
                    req = int(req * (1 - d * 0.6))
                    if d > 0.3: is_anomaly = 1

            elif svc == "payment-service":
                d = _degradation_curve(t_idx, **S1_PAYMENT)
                if d > 0:
                    cpu += d * 45; latency += d * 120; err += d * 12; p99 += d * 500; conn = int(conn + d * 150)
                    if d > 0.3: is_anomaly = 1

            elif svc == "postgres-primary":
                d = _degradation_curve(t_idx, **S2_PG_PRIMARY)
                if d > 0:
                    mem += d * 18; conn = int(conn + d * 260); err += d * 25; disk += d * 40; cpu += d * 30; gc += d * 50
                    if d > 0.3: is_anomaly = 1

            elif svc == "postgres-replica":
                d = _degradation_curve(t_idx, **S2_PG_REPLICA)
                if d > 0:
                    mem += d * 15; conn = int(conn + d * 180); err += d * 15; latency += d * 50
                    if d > 0.3: is_anomaly = 1

            elif svc == "auth-service":
                d = _degradation_curve(t_idx, **S2_AUTH)
                if d > 0:
                    latency += d * 60; err += d * 10; p99 += d * 200; cpu += d * 20
                    if d > 0.3: is_anomaly = 1

            elif svc == "user-service":
                d = _degradation_curve(t_idx, **S2_USER)
                if d > 0:
                    latency += d * 40; err += d * 8; p99 += d * 150
                    if d > 0.3: is_anomaly = 1

            elif svc == "cache-layer":
                d = _degradation_curve(t_idx, **S3_CACHE)
                if d > 0:
                    mem += d * 23; cpu += d * 40; latency += d * 50; err += d * 15; gc += d * 60
                    if d > 0.3: is_anomaly = 1

            elif svc == "search-service":
                d = _degradation_curve(t_idx, **S3_SEARCH)
                if d > 0:
                    latency += d * 150; p99 += d * 600; cpu += d * 35; err += d * 12
                    if d > 0.3: is_anomaly = 1

            if svc == "api-gateway":
                d = _degradation_curve(t_idx, **S3_GATEWAY)
                if d > 0:
                    latency += d * 100; p99 += d * 350; err += d * 14; cpu += d * 25; conn = int(conn + d * 200)
                    if d > 0.3: is_anomaly = 1

            # Transient noise
            if is_anomaly == 0 and np.random.rand() < 0.01:
                cpu += np.random.uniform(25, 45); err += np.random.uniform(3, 12); is_anomaly = 1

            rows.append({
                "timestamp":          t.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "service_name":       svc,
                "cpu_usage":          round(max(2.0, min(99.5, cpu)), 2),
                "memory_usage":       round(max(5.0, min(99.5, mem)), 2),
                "disk_io":            round(max(0.5, min(99.0, disk)), 2),
                "network_latency_ms": round(max(0.5, min(999.0, latency)), 2),
                "request_count":      max(10, req),
                "error_rate":         round(max(0.0, min(100.0, err)), 4),
                "response_time_p99":  round(max(1.0, min(5000.0, p99)), 2),
                "active_connections": max(5, conn),
                "gc_pause_ms":        round(max(0.5, min(200.0, gc)), 2),
                "thread_count":       max(5, thr),
                "is_anomaly":         is_anomaly,
            })

    df = pd.DataFrame(rows)
    return df, scenarios_meta


if __name__ == "__main__":
    df, scenarios_meta = generate_synthetic_telemetry()
    output_path = "sample-data/sample_metrics.csv"
    df.to_csv(output_path, index=False)

    print(f"Generated {len(df)} rows for {df['service_name'].nunique()} microservices")
    print(f"Saved to {output_path}")

    # Export scenario ground-truth JSON files
    incidents_dir = "sample-data/simulated_incidents"
    os.makedirs(incidents_dir, exist_ok=True)

    for sc in scenarios_meta:
        json_path = os.path.join(incidents_dir, f"{sc['scenario_id']}.json")
        with open(json_path, "w") as f:
            json.dump(sc, f, indent=2)
        print(f"Exported ground truth scenario -> {json_path}")
