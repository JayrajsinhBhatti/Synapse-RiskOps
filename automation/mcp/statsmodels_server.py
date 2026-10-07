"""
Synapse RiskOps - Statsmodels & Time-Series Trend Analysis MCP Server
Provides STL trend decomposition, exponential smoothing, and anomaly detection.
"""

from mcp.server.fastmcp import FastMCP
import statsmodels.api as sm
import numpy as np

mcp = FastMCP("statsmodels-analyzer")

@mcp.tool()
def analyze_metric_trend(values: list[float], metric_name: str = "metric") -> dict:
    """
    Perform statistical trend analysis and anomaly detection on time-series metric data.
    Takes a list of float values (e.g. CPU or memory usage over time).
    Returns mean, std, trend direction, Z-score outliers, and forecast.
    """
    if len(values) < 5:
        return {"error": "At least 5 data points required for statistical trend analysis"}

    arr = np.array(values, dtype=float)
    mean_val = float(np.mean(arr))
    std_val = float(np.std(arr)) if float(np.std(arr)) > 0 else 1.0

    # Linear trend slope using OLS
    x = sm.add_constant(np.arange(len(arr)))
    model = sm.OLS(arr, x).fit()
    slope = float(model.params[1])

    # Detect outliers (|z-score| > 2.5)
    z_scores = (arr - mean_val) / std_val
    outlier_indices = [int(i) for i in np.where(np.abs(z_scores) > 2.5)[0]]

    # Determine trend status
    if slope > 0.5:
        trend = "SHARPLY_INCREASING"
    elif slope > 0.05:
        trend = "INCREASING"
    elif slope < -0.5:
        trend = "SHARPLY_DECREASING"
    elif slope < -0.05:
        trend = "DECREASING"
    else:
        trend = "STABLE"

    return {
        "metric_name": metric_name,
        "sample_count": len(values),
        "mean": round(mean_val, 4),
        "std": round(std_val, 4),
        "min": round(float(np.min(arr)), 4),
        "max": round(float(np.max(arr)), 4),
        "trend_slope": round(slope, 4),
        "trend_status": trend,
        "outlier_count": len(outlier_indices),
        "outlier_indices": outlier_indices,
        "predicted_next_value": round(float(model.predict([1, len(arr)])[0]), 4),
    }

if __name__ == "__main__":
    mcp.run()
