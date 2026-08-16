import json

def get_dependency_graph():
    with open("app/mocks/sample_risk_scores.json", "r") as f:
        return json.load(f)