"""
evaluation/metrics.py
Owner: Person 1 | Week: 2 (initial) -> extended through Week 4 and Week 6

Reusable metric calculation functions, organized by area:
- Failure prediction: precision, recall, F1, lead time, false alarm rate
- Root cause analysis: accuracy, accuracy@k, propagation path accuracy, diagnosis latency
- Guidance & routing: routing accuracy, false autonomy rate, escalation
  appropriateness, confidence calibration
- End-to-end: MTTR, MTTR reduction %, retry/escalation rate, feedback loop
  improvement rate over time
Called by backtest.py and used to compile the Week 6 evaluation report.
"""
