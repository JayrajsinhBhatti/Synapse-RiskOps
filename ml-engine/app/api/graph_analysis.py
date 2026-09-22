"""
ml-engine/app/api/graph_analysis.py

Advanced NetworkX graph analysis endpoints.
Provides root cause isolation using PageRank, betweenness centrality,
cascading failure simulation, and multi-service correlation.

Consumed by the GenAI Agent for enhanced root cause identification.
"""

from fastapi import APIRouter, HTTPException, Query
from loguru import logger
from typing import List, Dict, Any

import networkx as nx

from app.services.graph_builder import get_graph_builder

router = APIRouter(prefix="/api/graph", tags=["Graph Analysis"])


# -------------------------------------------------------------------
# PageRank-based root cause scoring
# -------------------------------------------------------------------
@router.get("/root-cause-analysis")
async def root_cause_analysis(
    services: str = Query(
        ...,
        description="Comma-separated list of alerting service names",
    ),
) -> Dict[str, Any]:
    """
    Given multiple alerting services, find the most likely common root cause
    using PageRank scoring on the dependency graph.

    The algorithm:
    1. Build an error-weighted subgraph from the alerting services
    2. Run PageRank on the reversed graph (upstream = higher rank)
    3. Find common ancestors of all alerting services
    4. Rank candidates by PageRank score × criticality weight
    """
    builder = get_graph_builder()
    graph = builder.graph
    service_list = [s.strip() for s in services.split(",") if s.strip()]

    if not service_list:
        raise HTTPException(400, "At least one service must be specified")

    # Validate services exist in graph
    missing = [s for s in service_list if s not in graph]
    if missing:
        raise HTTPException(
            404, f"Services not found in graph: {missing}"
        )

    # 1. Find common ancestors (upstream dependencies shared by all alerting services)
    ancestor_sets = []
    for svc in service_list:
        ancestors = set(nx.descendants(graph, svc))  # upstream deps
        ancestors.add(svc)
        ancestor_sets.append(ancestors)

    common_ancestors = set.intersection(*ancestor_sets) if ancestor_sets else set()

    # 2. Run PageRank on the full graph
    try:
        pagerank_scores = nx.pagerank(graph, alpha=0.85)
    except Exception:
        pagerank_scores = {n: 1.0 / graph.number_of_nodes() for n in graph.nodes}

    # 3. Calculate betweenness centrality for single-point-of-failure detection
    try:
        centrality = nx.betweenness_centrality(graph)
    except Exception:
        centrality = {n: 0.0 for n in graph.nodes}

    # 4. Criticality weights
    criticality_weight = {
        "CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1,
    }

    # 5. Score and rank candidates
    candidates = []
    for node in common_ancestors:
        node_data = graph.nodes[node]
        crit = node_data.get("criticality", "MEDIUM")
        pr_score = pagerank_scores.get(node, 0)
        bc_score = centrality.get(node, 0)
        crit_w = criticality_weight.get(crit, 2)

        # Composite score: PageRank (influence) + centrality (bottleneck) + criticality
        composite = (pr_score * 40) + (bc_score * 30) + (crit_w * 10)

        # Calculate shortest distances to each alerting service
        distances = {}
        for svc in service_list:
            try:
                path = nx.shortest_path(graph, svc, node)
                distances[svc] = len(path) - 1
            except nx.NetworkXNoPath:
                distances[svc] = -1

        candidates.append({
            "service_name": node,
            "composite_score": round(composite, 4),
            "pagerank_score": round(pr_score, 6),
            "betweenness_centrality": round(bc_score, 6),
            "criticality": crit,
            "service_type": node_data.get("service_type", "MICROSERVICE"),
            "distances_from_alerting": distances,
            "is_alerting": node in service_list,
        })

    # Sort by composite score descending
    candidates.sort(key=lambda c: c["composite_score"], reverse=True)

    return {
        "alerting_services": service_list,
        "common_ancestor_count": len(common_ancestors),
        "root_cause_candidates": candidates[:10],  # Top 10
        "most_likely_root_cause": candidates[0] if candidates else None,
    }


# -------------------------------------------------------------------
# Critical paths (single points of failure)
# -------------------------------------------------------------------
@router.get("/critical-paths")
async def critical_paths() -> Dict[str, Any]:
    """
    Identify all critical paths and single-points-of-failure in the
    service dependency graph using betweenness centrality and
    articulation point detection.
    """
    builder = get_graph_builder()
    graph = builder.graph

    # Betweenness centrality — nodes with highest centrality are bottlenecks
    centrality = nx.betweenness_centrality(graph)

    # For articulation points, we need an undirected view
    undirected = graph.to_undirected()
    try:
        articulation_points = list(nx.articulation_points(undirected))
    except Exception:
        articulation_points = []

    # Sort nodes by centrality
    ranked_nodes = sorted(
        centrality.items(), key=lambda x: x[1], reverse=True
    )

    bottlenecks = []
    for node, score in ranked_nodes:
        if score > 0:
            node_data = graph.nodes[node]
            _, blast_score, _ = builder.get_blast_radius(node)
            bottlenecks.append({
                "service_name": node,
                "betweenness_centrality": round(score, 6),
                "criticality": node_data.get("criticality", "MEDIUM"),
                "service_type": node_data.get("service_type", "MICROSERVICE"),
                "blast_radius_pct": blast_score,
                "is_articulation_point": node in articulation_points,
                "in_degree": graph.in_degree(node),
                "out_degree": graph.out_degree(node),
            })

    return {
        "total_nodes": graph.number_of_nodes(),
        "total_edges": graph.number_of_edges(),
        "articulation_points": articulation_points,
        "bottleneck_services": bottlenecks,
    }


# -------------------------------------------------------------------
# Cascading failure simulation
# -------------------------------------------------------------------
@router.get("/cascade-simulation")
async def cascade_simulation(
    failing_service: str = Query(
        ..., description="Name of the initially failing service"
    ),
) -> Dict[str, Any]:
    """
    Simulate a cascading failure starting from a given service.
    Models how failure propagates through the dependency graph.

    Returns a timeline of affected services ordered by propagation depth.
    """
    builder = get_graph_builder()
    graph = builder.graph

    if failing_service not in graph:
        raise HTTPException(404, f"Service '{failing_service}' not in graph")

    # BFS from the failing service in the reverse direction
    # (find all services that depend on the failing one)
    affected_by_depth: Dict[int, List[str]] = {}
    visited = {failing_service}
    current_level = {failing_service}
    depth = 0

    affected_by_depth[0] = [failing_service]

    while current_level:
        next_level = set()
        for node in current_level:
            # Predecessors = services that call this node (depend on it)
            for pred in graph.predecessors(node):
                if pred not in visited:
                    visited.add(pred)
                    next_level.add(pred)
        depth += 1
        if next_level:
            affected_by_depth[depth] = sorted(next_level)
        current_level = next_level

    # Build timeline
    timeline = []
    total_affected = 0
    for d in sorted(affected_by_depth.keys()):
        services_at_depth = affected_by_depth[d]
        for svc in services_at_depth:
            node_data = graph.nodes[svc]
            timeline.append({
                "service_name": svc,
                "propagation_depth": d,
                "criticality": node_data.get("criticality", "MEDIUM"),
                "service_type": node_data.get("service_type", "MICROSERVICE"),
                "estimated_impact_time_seconds": d * 30,  # ~30s per hop
            })
        if d > 0:
            total_affected += len(services_at_depth)

    # Calculate overall blast radius
    blast_pct = round(
        (total_affected / graph.number_of_nodes()) * 100, 1
    ) if graph.number_of_nodes() > 0 else 0

    return {
        "failing_service": failing_service,
        "total_affected_services": total_affected,
        "blast_radius_percentage": blast_pct,
        "max_propagation_depth": max(affected_by_depth.keys()) if affected_by_depth else 0,
        "cascade_timeline": timeline,
    }
