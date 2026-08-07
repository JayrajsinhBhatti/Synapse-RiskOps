"""
ml-engine/app/api/risk_score.py
Owner: Person 2 | Week: 2

RiskScorer API route.
- POST /api/risk-score -> runs services/risk_engine.py, returns risk score,
  predicted failure type, and horizon
- Response shape must match the "prediction" block of
  shared/schemas/incident_record.schema.json
- Registered on the FastAPI app in main.py
"""
