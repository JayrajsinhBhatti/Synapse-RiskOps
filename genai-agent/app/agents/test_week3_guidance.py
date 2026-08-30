from app.ml_node import get_ml_prediction
from app.agents.log_analyzer import LogAnalyzer
from app.agents.root_cause_identifier import root_cause_identifier
from app.agents.proactive_guidance_generator import proactive_guidance_generator


# ---------------------------------------------------------
# 1. Initial input
# ---------------------------------------------------------

state = {
    "metrics": {
        "service_name": "order-service",
        "cpu_usage": 78.5,
        "memory_usage": 85.2,
        "disk_io": 32.1,
        "network_latency_ms": 45.3,
        "request_count": 5200,
        "error_rate": 8.5,
        "response_time_p99": 180.0,
        "active_connections": 120,
        "gc_pause_ms": 12.5,
        "thread_count": 48,
        "timestamp": "2026-08-30T21:58:00Z"
    },

    "logs": [
        {
            "service": "order-service",
            "message": "DB connection timeout after 5s"
        },
        {
            "service": "payment-service",
            "message": "Connection pool utilization 92%"
        },
        {
            "service": "order-service",
            "message": "Request latency exceeded threshold"
        }
    ]
}


# ---------------------------------------------------------
# 2. REAL ML NODE
# ---------------------------------------------------------

print("\n========== ML NODE ==========")

state = get_ml_prediction(state)

print("Risk Score:",
      state["risk_score"])

print("Risk Tier:",
      state["risk_tier"])

print("Confidence:",
      state["prediction_confidence"])

print("Failure Type:",
      state["predicted_failure_type"])

print("Prediction Horizon:",
      state["prediction_horizon_minutes"])

print("Dependency Graph:")
print(state["dependency_graph"])


# ---------------------------------------------------------
# 3. REAL LOG ANALYZER
# ---------------------------------------------------------

print("\n========== LOG ANALYZER ==========")

log_analyzer = LogAnalyzer()
log_result = log_analyzer.analyze(state)

state.update(log_result)

print("Observations:")
print(state.get("observations"))


# ---------------------------------------------------------
# 4. REAL ROOT CAUSE IDENTIFIER
# ---------------------------------------------------------

print("\n========== ROOT CAUSE IDENTIFIER ==========")

rca_result = root_cause_identifier(state)

state.update(rca_result)

for candidate in state["root_cause_candidates_ranked"]:
    print("\nCause:", candidate["cause"])
    print("Confidence:", candidate["confidence"])
    print("Affected Services:", candidate["affected_services"])
    print("Reason:", candidate["reason"])


# ---------------------------------------------------------
# 5. REAL PROACTIVE GUIDANCE GENERATOR
# ---------------------------------------------------------

print("\n========== PROACTIVE GUIDANCE GENERATOR ==========")

guidance_result = proactive_guidance_generator(state)

state.update(guidance_result)

print("Summary:", state["guidance"]["summary"])
print("Relevance Score:", state["guidance"]["relevance_score"])
print("Immediate Actions:")
for action in state["guidance"]["immediate_actions"]:
    print(" -", action)



# ---------------------------------------------------------
# 1. Initial input
# ---------------------------------------------------------

state = {
    "metrics": {
        "service_name": "order-service",
        "cpu_usage": 78.5,
        "memory_usage": 85.2,
        "disk_io": 32.1,
        "network_latency_ms": 45.3,
        "request_count": 5200,
        "error_rate": 8.5,
        "response_time_p99": 180.0,
        "active_connections": 120,
        "gc_pause_ms": 12.5,
        "thread_count": 48,
        "timestamp": "2026-08-30T21:58:00Z"
    },

    "logs": [
        {
            "service": "order-service",
            "message": "DB connection timeout after 5s"
        },
        {
            "service": "payment-service",
            "message": "Connection pool utilization 92%"
        },
        {
            "service": "order-service",
            "message": "Request latency exceeded threshold"
        }
    ]
}


# ---------------------------------------------------------
# 2. REAL ML NODE
# ---------------------------------------------------------

print("\n========== ML NODE ==========")

state = get_ml_prediction(state)

print("Risk Score:",
      state["risk_score"])

print("Risk Tier:",
      state["risk_tier"])

print("Confidence:",
      state["prediction_confidence"])

print("Failure Type:",
      state["predicted_failure_type"])

print("Prediction Horizon:",
      state["prediction_horizon_minutes"])

print("Dependency Graph:")
print(state["dependency_graph"])


# ---------------------------------------------------------
# 3. REAL LOG ANALYZER
# ---------------------------------------------------------

print("\n========== LOG ANALYZER ==========")

log_analyzer = LogAnalyzer()
log_result = log_analyzer.analyze(state)

state.update(log_result)

print("Observations:")
print(state.get("observations"))


# ---------------------------------------------------------
# 4. REAL ROOT CAUSE IDENTIFIER
# ---------------------------------------------------------

print("\n========== ROOT CAUSE IDENTIFIER ==========")

rca_result = root_cause_identifier(state)

state.update(rca_result)

for candidate in state["root_cause_candidates_ranked"]:
    print("\nCause:", candidate["cause"])
    print("Confidence:", candidate["confidence"])
    print("Affected Services:", candidate["affected_services"])
    print("Reason:", candidate["reason"])


# ---------------------------------------------------------
# 5. REAL GUIDANCE GENERATOR
# ---------------------------------------------------------

print("\n========== GUIDANCE GENERATOR ==========")

guidance_result = guidance_generator(state)

print(guidance_result)