"""
genai-agent/app/feedback/feedback_loop.py
Owner: Person 1 | Week: 4

Self-improving feedback loop.
- Logs every prediction, diagnosis, routing decision, and human override
- Periodically analyzes outcomes (was_routing_correct, human_override_reason)
  to adjust confidence thresholds or flag systematic errors
- Feeds "feedback_loop" block of shared/schemas/incident_record.schema.json
- This is what evaluation/metrics.py uses to show improvement over time
  in the Week 6 report
"""
