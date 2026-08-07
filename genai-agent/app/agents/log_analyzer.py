"""
genai-agent/app/agents/log_analyzer.py
Owner: Person 1 | Week: 3

First agent in the LangGraph RCA pipeline.
- Takes raw logs / risk score context for a service as input (format matches
  sample-data/sample_logs.csv columns: timestamp, service_name, log_level,
  message, trace_id, span_id)
- Extracts relevant signals, anomalies, and error patterns from logs
- Passes structured findings forward to root_cause_identifier.py
- Can be built and unit-tested now against app/mocks/sample_risk_scores.json,
  before ml-engine's real endpoints exist
"""
