import requests


def get_ml_prediction(state):

    response = requests.post(
        "http://localhost:8000/api/risk-score",
        json={
            # request body matching RiskScoreRequest
        }
    )

    response.raise_for_status()

    prediction = response.json()

    return {
        **state,
        "risk_score": prediction["risk_score"],
        "risk_tier": prediction["risk_tier"],
        "prediction_confidence": prediction["confidence"],
        "predicted_failure_type": prediction["predicted_failure_type"],
    }