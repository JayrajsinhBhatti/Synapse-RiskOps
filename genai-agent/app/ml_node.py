import os
import requests


# Resolve the ML Engine base URL from the environment so that this works
# both inside Docker (http://ml-engine:8000) and locally (http://localhost:8000).
ML_ENGINE_URL = os.getenv("ML_ENGINE_URL", "http://localhost:8000")


def get_ml_prediction(state: dict) -> dict:
    """
    LangGraph node — calls the ML Engine and injects prediction results
    into the shared pipeline state.

    Reads:
      state["metrics"]  — ServiceMetricsInput-shaped dict

    Writes (merged into state):
      risk_score, risk_tier, prediction_confidence,
      predicted_failure_type, prediction_horizon_minutes,
      dependency_graph
    """
    metrics: dict = state["metrics"]
    service_name: str = metrics["service_name"]

    # -----------------------------------------------------------------
    # 1. Risk scoring — POST /api/risk-score
    # -----------------------------------------------------------------
    risk_response = requests.post(
        f"{ML_ENGINE_URL}/api/risk-score",
        json={"metrics": metrics},
        timeout=10,
    )
    risk_response.raise_for_status()
    prediction = risk_response.json()

    # -----------------------------------------------------------------
    # 2. Dependency graph — GET /api/graph/traverse?service=<name>
    # -----------------------------------------------------------------
    graph_response = requests.get(
        f"{ML_ENGINE_URL}/api/graph/traverse",
        params={"service": service_name},
        timeout=10,
    )
    # A 404 means the service isn't in the graph yet — degrade gracefully
    if graph_response.status_code == 404:
        dependency_graph = {}
    else:
        graph_response.raise_for_status()
        dependency_graph = graph_response.json()

    return {
        **state,
        "risk_score": prediction["risk_score"],
        "risk_tier": prediction["risk_tier"],
        "prediction_confidence": prediction["confidence"],
        "predicted_failure_type": prediction["predicted_failure_type"],
        "prediction_horizon_minutes": prediction.get("prediction_horizon_minutes", 0),
        "dependency_graph": dependency_graph,
    }