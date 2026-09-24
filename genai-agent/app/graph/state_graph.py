"""
genai-agent/app/graph/state_graph.py
Owner: Person 1 | Week: 3

Defines the LangGraph StateGraph wiring together the agents and remediation:
LogAnalyzer -> RootCauseIdentifier -> GuidanceGenerator -> ConfidenceRouter -> Remediation
- Defines the shared agent state object passed between nodes
- Defines edges/transitions between agent nodes
- Compiles the graph into a runnable pipeline invoked by /diagnose in main.py
- Includes conditional remediation: auto_remediate triggers Docker/Ansible fixes,
  escalate sends to human engineer
"""

from typing import Any, Dict, List, Optional, TypedDict

from langgraph.graph import StateGraph, END
from loguru import logger

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

    # Produced by RemediationNode (Step 6)
    remediation_result: Dict[str, Any]


# -----------------------------------------------------------------------
# Adapter — wraps LogAnalyzer.analyze() so it matches the node signature
# -----------------------------------------------------------------------
_log_analyzer = LogAnalyzer()

def log_analyzer_node(state: PipelineState) -> dict:
    return _log_analyzer.analyze(state)


# -----------------------------------------------------------------------
# Remediation Node — executes Docker/Ansible fixes when auto_remediate
# -----------------------------------------------------------------------
def remediation_node(state: PipelineState) -> dict:
    """
    LangGraph node — executes autonomous remediation when the routing
    decision is 'auto_remediate'. Uses the runbook engine to orchestrate
    Docker SDK and Ansible playbook execution.

    If routing_decision == 'escalate', this node is a no-op.
    """
    routing_decision = state.get("routing_decision", "escalate")

    if routing_decision != "auto_remediate":
        logger.info(
            "[Remediation] Skipping — routing_decision is "
            f"'{routing_decision}', not 'auto_remediate'"
        )
        return {
            "remediation_result": {
                "status": "SKIPPED",
                "reason": f"Routing decision is '{routing_decision}'",
            }
        }

    failure_type = state.get("predicted_failure_type", "unknown")
    metrics = state.get("metrics", {})
    service_name = metrics.get("service_name", "unknown")

    logger.info(
        f"[Remediation] Auto-remediating {failure_type} on {service_name}"
    )

    # Try Docker SDK first (fast, in-process)
    try:
        from app.remediation.docker_healer import get_docker_healer

        healer = get_docker_healer()
        if healer.is_connected:
            result = healer.remediate(failure_type, service_name)
            if result.get("status") == "SUCCESS":
                logger.info(
                    f"[Remediation] Docker fix succeeded: {result}"
                )
                return {"remediation_result": result}
            else:
                logger.warning(
                    f"[Remediation] Docker fix returned {result.get('status')}, "
                    "falling through to runbook engine"
                )
    except Exception as exc:
        logger.warning(f"[Remediation] Docker healer error: {exc}")

    # Fallback: Runbook engine (orchestrated Docker + Ansible steps)
    try:
        import asyncio
        from runbooks.engine import get_runbook_engine

        engine = get_runbook_engine()
        # Run async runbook execution in sync context
        loop = asyncio.new_event_loop()
        result = loop.run_until_complete(
            engine.execute(
                failure_type=failure_type,
                service_name=service_name,
                incident_id=f"AUTO-{service_name}",
                risk_score=state.get("risk_score", 0.0),
            )
        )
        loop.close()

        logger.info(f"[Remediation] Runbook result: {result.get('status')}")
        return {"remediation_result": result}

    except Exception as exc:
        logger.error(f"[Remediation] Runbook engine failed: {exc}")
        return {
            "remediation_result": {
                "status": "FAILED",
                "error": str(exc),
            }
        }


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
      remediation_node
            ↓
           END
    """
    graph = StateGraph(PipelineState)

    graph.add_node("ml_node",                    get_ml_prediction)
    graph.add_node("log_analyzer",               log_analyzer_node)
    graph.add_node("root_cause_identifier",      root_cause_identifier)
    graph.add_node("proactive_guidance_generator", proactive_guidance_generator)
    graph.add_node("confidence_router",          confidence_router)
    graph.add_node("remediation_node",           remediation_node)

    graph.set_entry_point("ml_node")
    graph.add_edge("ml_node",                    "log_analyzer")
    graph.add_edge("log_analyzer",               "root_cause_identifier")
    graph.add_edge("root_cause_identifier",      "proactive_guidance_generator")
    graph.add_edge("proactive_guidance_generator", "confidence_router")
    graph.add_edge("confidence_router",          "remediation_node")
    graph.add_edge("remediation_node",           END)

    return graph.compile()


# Module-level compiled pipeline — imported by main.py
pipeline = build_pipeline()
