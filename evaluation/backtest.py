"""
evaluation/backtest.py
Owner: Person 1 | Week: 2 (synthetic) -> Week 6 (real data, final report)

Backtesting harness for failure prediction.
- Loads prediction data (initially synthetic — see note below — then real
  logged incident records) and ground truth
- Computes precision, recall, F1, mean/median lead time, false alarm rate
- Data-source agnostic: point it at ml-engine's sample-data/sample_metrics.csv
  plus a labeled outcome column, or at real logged incident records later,
  without changing the analysis logic
- Uses metrics.py for the actual metric calculations
"""
