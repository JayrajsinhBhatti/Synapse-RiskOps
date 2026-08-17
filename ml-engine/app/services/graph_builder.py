"""
Synapse RiskOps - Dependency Graph Builder (NetworkX)
=====================================================
Owner: Person 2 | Week: 3

Builds and maintains the service dependency graph using NetworkX.
Source data: sample-data/sample_dependencies.csv (and init.sql schema).

Core capabilities:
- build_graph(): Construct directed graph from CSV topology
- get_upstream_dependencies(): All transitive ancestors of a service
- get_downstream_dependents(): All transitive descendants (blast radius)
- find_propagation_path(): Shortest path between two services
- rank_root_cause_candidates(): Trace upstream and rank by criticality + depth

Queried by api/graph_traversal.py and consumed by genai-agent for RCA.
"""

import pandas as pd
import networkx as nx
from loguru import logger
from typing import Dict, List, Optional, Tuple
from pathlib import Path

from app.core.config import settings
from app.schemas.graph import (
    Criticality, ServiceType, DependencyType,
    NodeSchema, EdgeSchema, RootCauseCandidate,
)


# Service metadata from docker/postgres/init.sql
SERVICE_METADATA = {
    "api-gateway":       {"type": ServiceType.GATEWAY,        "criticality": Criticality.CRITICAL, "owner": "Platform Team"},
    "auth-service":      {"type": ServiceType.MICROSERVICE,   "criticality": Criticality.CRITICAL, "owner": "Security Team"},
    "user-service":      {"type": ServiceType.MICROSERVICE,   "criticality": Criticality.HIGH,     "owner": "Backend Team"},
    "order-service":     {"type": ServiceType.MICROSERVICE,   "criticality": Criticality.HIGH,     "owner": "Commerce Team"},
    "payment-service":   {"type": ServiceType.MICROSERVICE,   "criticality": Criticality.CRITICAL, "owner": "Payments Team"},
    "inventory-service": {"type": ServiceType.MICROSERVICE,   "criticality": Criticality.HIGH,     "owner": "Supply Team"},
    "notification-svc":  {"type": ServiceType.MICROSERVICE,   "criticality": Criticality.MEDIUM,   "owner": "Platform Team"},
    "search-service":    {"type": ServiceType.MICROSERVICE,   "criticality": Criticality.MEDIUM,   "owner": "Search Team"},
    "cache-layer":       {"type": ServiceType.INFRASTRUCTURE, "criticality": Criticality.HIGH,     "owner": "Platform Team"},
    "message-queue":     {"type": ServiceType.INFRASTRUCTURE, "criticality": Criticality.CRITICAL, "owner": "Platform Team"},
    "postgres-primary":  {"type": ServiceType.DATABASE,       "criticality": Criticality.CRITICAL, "owner": "DBA Team"},
    "postgres-replica":  {"type": ServiceType.DATABASE,       "criticality": Criticality.HIGH,     "owner": "DBA Team"},
}

# Criticality ranking for root cause sorting (higher = more likely root cause)
CRITICALITY_WEIGHT = {
    Criticality.CRITICAL: 4,
    Criticality.HIGH: 3,
    Criticality.MEDIUM: 2,
    Criticality.LOW: 1,
}


class GraphBuilder:
    """
    Builds and queries a directed dependency graph using NetworkX.

    Edge semantics: source_service -> target_service means
    "source depends on target" (source calls target).

    Therefore:
    - Upstream dependencies (ancestors) = follow edges forward from a node
      (services this node calls).
    - Downstream dependents (blast radius) = follow edges backward to a node
      (services that call this node).
    """

    def __init__(self):
        self.graph: nx.DiGraph = nx.DiGraph()
        self.is_built = False

    def build_graph(self, csv_path: Optional[Path] = None) -> Dict:
        """
        Build the directed dependency graph from sample_dependencies.csv.

        CSV columns: source_service, target_service, dependency_type, protocol, timeout_ms, is_critical

        Edge direction: source_service -> target_service
        (source depends on target; source calls target)
        """
        if csv_path is None:
            csv_path = settings.DEPENDENCIES_FILE

        df = pd.read_csv(csv_path)
        self.graph = nx.DiGraph()

        # Add all known services as nodes with metadata
        for svc_name, meta in SERVICE_METADATA.items():
            self.graph.add_node(
                svc_name,
                service_type=meta["type"].value,
                criticality=meta["criticality"].value,
                owner=meta["owner"],
            )

        # Add edges from CSV
        for _, row in df.iterrows():
            src = row["source_service"]
            tgt = row["target_service"]

            # Ensure nodes exist (defensive)
            for s in [src, tgt]:
                if s not in self.graph:
                    self.graph.add_node(
                        s,
                        service_type=ServiceType.MICROSERVICE.value,
                        criticality=Criticality.MEDIUM.value,
                        owner="Unknown",
                    )

            self.graph.add_edge(
                src, tgt,
                dependency_type=row.get("dependency_type", "SYNC"),
                protocol=row.get("protocol", "HTTP"),
                timeout_ms=int(row.get("timeout_ms", 5000)),
                is_critical=str(row.get("is_critical", "false")).lower() == "true",
            )

        self.is_built = True
        logger.info(
            f"Dependency graph built: {self.graph.number_of_nodes()} nodes, "
            f"{self.graph.number_of_edges()} edges"
        )

        return {
            "nodes": self.graph.number_of_nodes(),
            "edges": self.graph.number_of_edges(),
            "services": list(self.graph.nodes),
        }

    def get_all_nodes(self) -> List[NodeSchema]:
        """Return all service nodes with their metadata."""
        nodes = []
        for name in self.graph.nodes:
            data = self.graph.nodes[name]
            nodes.append(NodeSchema(
                service_name=name,
                service_type=ServiceType(data.get("service_type", "MICROSERVICE")),
                criticality=Criticality(data.get("criticality", "HIGH")),
                owner=data.get("owner", ""),
                in_degree=self.graph.in_degree(name),
                out_degree=self.graph.out_degree(name),
            ))
        return nodes

    def get_all_edges(self) -> List[EdgeSchema]:
        """Return all dependency edges."""
        edges = []
        for src, tgt, data in self.graph.edges(data=True):
            edges.append(EdgeSchema(
                source=src,
                target=tgt,
                dependency_type=DependencyType(data.get("dependency_type", "SYNC")),
                protocol=data.get("protocol", "HTTP"),
                timeout_ms=data.get("timeout_ms", 5000),
                is_critical=data.get("is_critical", False),
            ))
        return edges

    def get_upstream_dependencies(self, service_name: str) -> List[str]:
        """
        Get all transitive upstream dependencies (services this service calls).

        In our graph, edges go source -> target (source depends on target).
        So "upstream" of service S means: all nodes reachable by following
        edges forward from S (successors / descendants in the DAG).
        """
        if service_name not in self.graph:
            return []
        return list(nx.descendants(self.graph, service_name))

    def get_downstream_dependents(self, service_name: str) -> List[str]:
        """
        Get all transitive downstream dependents (services that depend on this service).

        "Downstream" of service S means: all nodes that can reach S by following
        edges forward (ancestors in the DAG / predecessors).
        These are the services affected if S fails (blast radius).
        """
        if service_name not in self.graph:
            return []
        return list(nx.ancestors(self.graph, service_name))

    def find_propagation_path(self, source: str, target: str) -> List[str]:
        """
        Find the shortest dependency path from source to target.
        Returns an empty list if no path exists.
        """
        if source not in self.graph or target not in self.graph:
            return []
        try:
            return list(nx.shortest_path(self.graph, source, target))
        except nx.NetworkXNoPath:
            return []

    def get_blast_radius(self, service_name: str) -> Tuple[List[str], float, Dict[str, List[str]]]:
        """
        Calculate the blast radius if a service fails.

        Returns:
            - affected_services: List of services that depend on the failing service
            - blast_radius_score: Percentage of total services affected
            - propagation_paths: Dict mapping each affected service to its shortest path
        """
        if service_name not in self.graph:
            return [], 0.0, {}

        # Services that have this service as a dependency (direct or transitive)
        affected = self.get_downstream_dependents(service_name)
        total = self.graph.number_of_nodes()
        score = round((len(affected) / total) * 100, 1) if total > 0 else 0.0

        # Compute shortest paths from each affected service to the failing service
        propagation_paths = {}
        for svc in affected:
            path = self.find_propagation_path(svc, service_name)
            if path:
                propagation_paths[svc] = path

        return affected, score, propagation_paths

    def rank_root_cause_candidates(self, service_name: str) -> List[RootCauseCandidate]:
        """
        Rank upstream dependencies as potential root cause candidates.

        Ranking criteria (descending priority):
        1. Criticality weight (CRITICAL > HIGH > MEDIUM > LOW)
        2. Service type weight (DATABASE > INFRASTRUCTURE > MICROSERVICE > GATEWAY)
        3. Graph distance (closer = higher priority)
        """
        if service_name not in self.graph:
            return []

        upstream = self.get_upstream_dependencies(service_name)
        if not upstream:
            return []

        candidates = []
        for dep_name in upstream:
            dep_data = self.graph.nodes[dep_name]
            criticality = Criticality(dep_data.get("criticality", "MEDIUM"))
            svc_type = ServiceType(dep_data.get("service_type", "MICROSERVICE"))

            # Calculate graph distance
            path = self.find_propagation_path(service_name, dep_name)
            distance = len(path) - 1 if path else 999

            # Determine dependency type from direct edge (if exists)
            if self.graph.has_edge(service_name, dep_name):
                edge_data = self.graph.edges[service_name, dep_name]
                dep_type = DependencyType(edge_data.get("dependency_type", "SYNC"))
            else:
                # Multi-hop: find the first edge type in the path
                dep_type = DependencyType.SYNC
                if len(path) >= 2:
                    first_edge = self.graph.edges.get((path[0], path[1]), {})
                    dep_type = DependencyType(first_edge.get("dependency_type", "SYNC"))

            # Service type weight (infra/DB services are more likely root causes)
            type_weight = {
                ServiceType.DATABASE: 4,
                ServiceType.INFRASTRUCTURE: 3,
                ServiceType.MICROSERVICE: 2,
                ServiceType.GATEWAY: 1,
            }

            candidates.append(RootCauseCandidate(
                service_name=dep_name,
                criticality=criticality,
                distance=distance,
                dependency_type=dep_type,
                service_type=svc_type,
                path=path,
                _sort_key=(
                    CRITICALITY_WEIGHT.get(criticality, 0),
                    type_weight.get(svc_type, 0),
                    -distance,  # Negative: closer is better
                ),
            ))

        # Sort by: criticality desc, type weight desc, distance asc
        candidates.sort(
            key=lambda c: (
                CRITICALITY_WEIGHT.get(c.criticality, 0),
                {ServiceType.DATABASE: 4, ServiceType.INFRASTRUCTURE: 3,
                 ServiceType.MICROSERVICE: 2, ServiceType.GATEWAY: 1}.get(c.service_type, 0),
                -c.distance,
            ),
            reverse=True,
        )

        return candidates


# Module-level singleton for reuse across endpoints
_graph_builder: Optional[GraphBuilder] = None


def get_graph_builder() -> GraphBuilder:
    """Get or initialize the global GraphBuilder singleton."""
    global _graph_builder
    if _graph_builder is None or not _graph_builder.is_built:
        _graph_builder = GraphBuilder()
        _graph_builder.build_graph()
    return _graph_builder


if __name__ == "__main__":
    builder = GraphBuilder()
    summary = builder.build_graph()
    print(f"\n--- Graph Summary ---")
    print(f"  Nodes: {summary['nodes']}")
    print(f"  Edges: {summary['edges']}")
    print(f"  Services: {summary['services']}")

    # Test traversal for order-service
    test_svc = "order-service"
    print(f"\n--- Traversal: {test_svc} ---")
    print(f"  Upstream deps:    {builder.get_upstream_dependencies(test_svc)}")
    print(f"  Downstream deps:  {builder.get_downstream_dependents(test_svc)}")

    affected, score, paths = builder.get_blast_radius("postgres-primary")
    print(f"\n--- Blast Radius: postgres-primary ---")
    print(f"  Affected: {affected}")
    print(f"  Score:    {score}%")

    candidates = builder.rank_root_cause_candidates("api-gateway")
    print(f"\n--- Root Cause Candidates: api-gateway ---")
    for c in candidates:
        print(f"  {c.service_name:22s} | {c.criticality.value:8s} | dist={c.distance} | {c.dependency_type.value}")
