"""
genai-agent/app/graph/state_graph.py
Owner: Person 1 | Week: 3

Defines the LangGraph StateGraph wiring together the three agents:
LogAnalyzer -> RootCauseIdentifier -> GuidanceGenerator
- Defines the shared agent state object passed between nodes
- Defines edges/transitions between agent nodes
- Compiles the graph into a runnable pipeline invoked by /diagnose in main.py
- Can be scaffolded now with stub nodes, refined as each agent is implemented
"""

from typing import Any, Dict, List, Optional, TypedDict

from langgraph.graph import StateGraph, END

from app.ml_node import get_ml_prediction
from app.agents.log_analyzer import LogAnalyzer
from app.agents.root_cause_identifier import root_cause_identifier
from app.agents.proactive_guidance_generator import proactive_guidance_generator
from app.routing.confidence_router import confidence_router


# -----------------------------------------------------------------------
# Shared pipeline state — every node reads from / writes to this dict
# -----------------------------------------------------------------------
class PipelineState(TypedDict, total=False):
    # Input supplied by the caller
    metrics: Dict[str, Any]           # ServiceMetricsInput-shaped dict
    logs: List[Dict[str, Any]]        # raw log entries

    # Injected by ml_node (Step 1)
    risk_score: float
    risk_tier: str
    prediction_confidence: float
    predicted_failure_type: str
    prediction_horizon_minutes: int
    dependency_graph: Dict[str, Any]  # graph/traverse response from ml-engine

    # Produced by LogAnalyzer (Step 2)
    observations: Dict[str, List[str]]

    # Produced by RootCauseIdentifier (Step 3)
    root_cause_candidates_ranked: List[Dict[str, Any]]

    # Produced by ProactiveGuidanceGenerator (Step 4)
    guidance: Dict[str, Any]

    # Produced by ConfidenceRouter (Step 5)
    routing_decision: str
    routing_reason: str


# -----------------------------------------------------------------------
# Adapter — wraps LogAnalyzer.analyze() so it matches the node signature
# -----------------------------------------------------------------------
_log_analyzer = LogAnalyzer()

def log_analyzer_node(state: PipelineState) -> dict:
    return _log_analyzer.analyze(state)


# -----------------------------------------------------------------------
# Build and compile the graph
# -----------------------------------------------------------------------
def build_pipeline() -> Any:
    """
    Assembles and compiles the LangGraph pipeline:

      get_ml_prediction
            ↓
      log_analyzer
            ↓
      root_cause_identifier
            ↓
      proactive_guidance_generator
            ↓
      confidence_router
            ↓
           END
    """
    graph = StateGraph(PipelineState)

    graph.add_node("ml_node",                    get_ml_prediction)
    graph.add_node("log_analyzer",               log_analyzer_node)
    graph.add_node("root_cause_identifier",      root_cause_identifier)
    graph.add_node("proactive_guidance_generator", proactive_guidance_generator)
    graph.add_node("confidence_router",          confidence_router)

    graph.set_entry_point("ml_node")
    graph.add_edge("ml_node",                    "log_analyzer")
    graph.add_edge("log_analyzer",               "root_cause_identifier")
    graph.add_edge("root_cause_identifier",      "proactive_guidance_generator")
    graph.add_edge("proactive_guidance_generator", "confidence_router")
    graph.add_edge("confidence_router",          END)

    return graph.compile()


# Module-level compiled pipeline — imported by main.py
pipeline = build_pipeline()
