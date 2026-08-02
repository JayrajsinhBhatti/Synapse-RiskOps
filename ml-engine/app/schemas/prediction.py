"""
ml-engine/app/schemas/prediction.py
Owner: Person 2 | Week: 1-2

Pydantic models for the ML engine's request/response payloads.
- Mirrors the "prediction" block of shared/schemas/incident_record.schema.json
- Used by api/risk_score.py and api/graph_traversal.py for validation/serialization
- Keep in sync manually with the shared schema — do not let this drift
"""
