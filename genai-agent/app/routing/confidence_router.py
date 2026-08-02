"""
genai-agent/app/routing/confidence_router.py
Owner: Person 1 | Week: 4

Confidence-aware autonomy routing.
- Takes RCA confidence + guidance from the agent pipeline
- Decides: auto_remediate vs. escalate to a human engineer
- Start conservative (favor escalation) and tune thresholds using labeled
  outcomes from evaluation/backtest.py
- Output matches the "routing" block of shared/schemas/incident_record.schema.json
- Do NOT start this before Week 3's RCA pipeline is working end-to-end
"""
