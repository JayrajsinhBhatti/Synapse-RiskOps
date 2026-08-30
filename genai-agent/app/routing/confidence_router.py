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

# Thresholds — tune these with evaluation/backtest.py as outcomes accumulate
ML_CONFIDENCE_THRESHOLD = 0.85   # minimum ML prediction confidence for auto-remediation
RCA_CONFIDENCE_THRESHOLD = 0.80  # minimum top-candidate RCA confidence for auto-remediation


def confidence_router(state: dict) -> dict:
    """
    LangGraph node — decides whether to auto-remediate or escalate.

    Reads from state:
      prediction_confidence  — ML Engine model confidence (0-1)
      root_cause_candidates_ranked — ordered list from RCA agent

    Writes to state:
      routing_decision  — "auto_remediate" | "escalate"
      routing_reason    — short human-readable explanation
    """
    ml_confidence: float = state.get("prediction_confidence", 0.0)

    candidates = state.get("root_cause_candidates_ranked", [])
    rca_confidence: float = candidates[0].get("confidence", 0.0) if candidates else 0.0

    if ml_confidence >= ML_CONFIDENCE_THRESHOLD and rca_confidence >= RCA_CONFIDENCE_THRESHOLD:
        decision = "auto_remediate"
        reason = (
            f"ML confidence {ml_confidence:.2f} >= {ML_CONFIDENCE_THRESHOLD} and "
            f"RCA confidence {rca_confidence:.2f} >= {RCA_CONFIDENCE_THRESHOLD}. "
            "Autonomous remediation approved."
        )
    else:
        decision = "escalate"
        reason = (
            f"ML confidence {ml_confidence:.2f} (threshold {ML_CONFIDENCE_THRESHOLD}) or "
            f"RCA confidence {rca_confidence:.2f} (threshold {RCA_CONFIDENCE_THRESHOLD}) "
            "below threshold. Escalating to on-call engineer."
        )

    return {
        "routing_decision": decision,
        "routing_reason": reason,
    }
