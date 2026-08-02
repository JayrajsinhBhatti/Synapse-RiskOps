# API Contracts

Agreed Week 1. Any change here must be communicated to both partners before merging.

## ml-engine (Person 2) — http://ml-engine:8000
- `POST /api/risk-score` -> returns risk score per incident_record.schema.json > prediction
  (implemented in ml-engine/app/api/risk_score.py)
- `GET /api/graph/traverse?service={name}` -> returns dependency propagation path
  (implemented in ml-engine/app/api/graph_traversal.py)
- `GET /health` -> service health check (already implemented)

## genai-agent (Person 1) — http://genai-agent:8001
- `POST /diagnose` -> takes risk score + graph traversal, returns diagnosis + guidance
- `POST /route` -> returns routing decision (auto_remediate / escalate)

## backend (Person 2) — http://backend:8080
- `GET/POST/PATCH /api/incidents` -> incident CRUD (backend/.../controller/IncidentController.java)
- `GET /api/health` -> service health check (already implemented)

## Shared schema
See `shared/schemas/incident_record.schema.json` for the full incident record shape
that all services read/write against.
