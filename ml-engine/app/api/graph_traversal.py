"""
Synapse RiskOps - Graph Traversal API
======================================
Owner: Person 2 | Week: 3

Exposes the dependency graph engine as REST endpoints for Person 1's genai-agent.

Endpoints:
  - GET /api/graph/traverse?service={name}  -> Propagation path + RCA candidates
  - GET /api/graph/topology                 -> Full graph (nodes + edges) for frontend
  - GET /api/graph/blast-radius?service={name} -> Impact analysis if service fails

Contract defined in shared/api-contracts.md.
"""

from fastapi import APIRouter, HTTPException, Query
from loguru import logger

from app.services.graph_builder import get_graph_builder
from app.schemas.graph import (
    GraphTraversalResponse,
    GraphTopologyResponse,
    BlastRadiusResponse,
)

router = APIRouter(prefix="/api/graph", tags=["Dependency Graph"])


@router.get("/traverse", response_model=GraphTraversalResponse)
async def traverse_dependencies(
    service: str = Query(..., description="Service name to analyze (e.g. 'order-service')")
):
    """
    Traverse the dependency graph for a given service.

    Returns:
    - Upstream dependencies (services this service calls, transitively)
    - Downstream dependents (services that call this service, transitively)
    - Root cause candidates ranked by criticality, service type, and distance
    - Blast radius score (% of total services affected if this service fails)

    This is the primary endpoint consumed by Person 1's genai-agent for
    automated root cause analysis.
    """
    builder = get_graph_builder()

    if service not in builder.graph:
        raise HTTPException(
            status_code=404,
            detail=f"Service '{service}' not found in the dependency graph. "
                   f"Available services: {list(builder.graph.nodes)}"
        )

    upstream = builder.get_upstream_dependencies(service)
    downstream = builder.get_downstream_dependents(service)
    candidates = builder.rank_root_cause_candidates(service)
    blast_affected, blast_score, _ = builder.get_blast_radius(service)

    logger.info(
        f"Graph traversal for '{service}': "
        f"{len(upstream)} upstream, {len(downstream)} downstream, "
        f"{len(candidates)} RCA candidates, {blast_score}% blast radius"
    )

    return GraphTraversalResponse(
        target_service=service,
        upstream_dependencies=upstream,
        downstream_dependents=downstream,
        root_cause_candidates=candidates,
        blast_radius_services=blast_affected,
        blast_radius_score=blast_score,
        total_services=builder.graph.number_of_nodes(),
    )


@router.get("/topology", response_model=GraphTopologyResponse)
async def get_topology():
    """
    Return the full network topology (all nodes + all edges).
    Used by the React Flow frontend dashboard (Week 6) to render
    the interactive dependency graph visualization.
    """
    builder = get_graph_builder()
    nodes = builder.get_all_nodes()
    edges = builder.get_all_edges()

    return GraphTopologyResponse(
        nodes=nodes,
        edges=edges,
        total_nodes=len(nodes),
        total_edges=len(edges),
    )


@router.get("/blast-radius", response_model=BlastRadiusResponse)
async def get_blast_radius(
    service: str = Query(..., description="Service whose failure to analyze")
):
    """
    Calculate the blast radius if a specific service fails.

    Returns the list of affected downstream services, the percentage
    of total infrastructure impacted, and the shortest propagation
    path from each affected service to the failing service.
    """
    builder = get_graph_builder()

    if service not in builder.graph:
        raise HTTPException(
            status_code=404,
            detail=f"Service '{service}' not found in the dependency graph."
        )

    affected, score, paths = builder.get_blast_radius(service)

    logger.info(
        f"Blast radius for '{service}': {len(affected)} services affected ({score}%)"
    )

    return BlastRadiusResponse(
        source_service=service,
        affected_services=affected,
        affected_count=len(affected),
        blast_radius_score=score,
        total_services=builder.graph.number_of_nodes(),
        propagation_paths=paths,
    )
