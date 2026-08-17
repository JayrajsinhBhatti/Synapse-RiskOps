"""
Synapse RiskOps - Graph Schemas
================================
Owner: Person 2 | Week: 3

Pydantic request/response models for the Dependency Graph Engine.
Consumed by:
  - api/graph_traversal.py endpoints
  - Person 1's genai-agent (reads JSON responses to perform RCA)
"""

from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum


# =====================================================
# Enums
# =====================================================

class ServiceType(str, Enum):
    GATEWAY = "GATEWAY"
    MICROSERVICE = "MICROSERVICE"
    INFRASTRUCTURE = "INFRASTRUCTURE"
    DATABASE = "DATABASE"


class Criticality(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class DependencyType(str, Enum):
    SYNC = "SYNC"
    ASYNC = "ASYNC"
    REPLICATION = "REPLICATION"


# =====================================================
# Node & Edge Schemas
# =====================================================

class NodeSchema(BaseModel):
    """Represents a single service node in the dependency graph."""
    service_name: str = Field(..., description="Unique service name (e.g. 'api-gateway')")
    service_type: ServiceType = Field(default=ServiceType.MICROSERVICE, description="Service category")
    criticality: Criticality = Field(default=Criticality.HIGH, description="Business criticality level")
    owner: str = Field(default="", description="Team responsible for this service")
    in_degree: int = Field(default=0, description="Number of services depending on this service")
    out_degree: int = Field(default=0, description="Number of services this service depends on")


class EdgeSchema(BaseModel):
    """Represents a directed dependency edge: source depends on target."""
    source: str = Field(..., description="Service that initiates the dependency call")
    target: str = Field(..., description="Service being depended upon")
    dependency_type: DependencyType = Field(default=DependencyType.SYNC, description="Type of dependency link")
    protocol: str = Field(default="HTTP", description="Communication protocol (HTTP, TCP, AMQP)")
    timeout_ms: int = Field(default=5000, description="Timeout in milliseconds")
    is_critical: bool = Field(default=False, description="Whether this dependency is on the critical path")


# =====================================================
# Root Cause Candidate
# =====================================================

class RootCauseCandidate(BaseModel):
    """A ranked upstream service that may be the root cause of a failure."""
    service_name: str = Field(..., description="Name of the upstream service")
    criticality: Criticality = Field(..., description="Business criticality of this service")
    distance: int = Field(..., description="Graph distance (hops) from the failing service")
    dependency_type: DependencyType = Field(..., description="Type of dependency link connecting this service")
    service_type: ServiceType = Field(default=ServiceType.MICROSERVICE, description="Service category")
    path: List[str] = Field(default_factory=list, description="Full dependency path from failing service to this candidate")


# =====================================================
# API Response Schemas
# =====================================================

class GraphTraversalResponse(BaseModel):
    """
    Response for GET /api/graph/traverse?service={name}.
    This is the primary contract consumed by Person 1's genai-agent for RCA.
    """
    target_service: str = Field(..., description="The service being analyzed")
    upstream_dependencies: List[str] = Field(default_factory=list, description="All transitive upstream services (ancestors)")
    downstream_dependents: List[str] = Field(default_factory=list, description="All transitive downstream services (descendants)")
    root_cause_candidates: List[RootCauseCandidate] = Field(
        default_factory=list,
        description="Ranked list of upstream services most likely to be root cause"
    )
    blast_radius_services: List[str] = Field(default_factory=list, description="Services affected if target service fails")
    blast_radius_score: float = Field(default=0.0, description="Percentage of total services affected")
    total_services: int = Field(default=0, description="Total number of services in the graph")


class GraphTopologyResponse(BaseModel):
    """
    Response for GET /api/graph/topology.
    Full network graph for frontend React Flow rendering (Week 6).
    """
    nodes: List[NodeSchema] = Field(default_factory=list, description="All service nodes")
    edges: List[EdgeSchema] = Field(default_factory=list, description="All dependency edges")
    total_nodes: int = Field(default=0, description="Total service count")
    total_edges: int = Field(default=0, description="Total dependency edge count")


class BlastRadiusResponse(BaseModel):
    """Response for GET /api/graph/blast-radius?service={name}."""
    source_service: str = Field(..., description="Service whose failure is being analyzed")
    affected_services: List[str] = Field(default_factory=list, description="Downstream services that would be impacted")
    affected_count: int = Field(default=0, description="Number of affected services")
    blast_radius_score: float = Field(default=0.0, description="Percentage of total services affected")
    total_services: int = Field(default=0, description="Total services in the graph")
    propagation_paths: dict = Field(
        default_factory=dict,
        description="Map of affected service -> shortest path from source"
    )
