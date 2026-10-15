"""
Synapse RiskOps - Chaos-Calibrated Causal Graph Schemas
======================================================
Defines Pydantic models for:
1. Controlled chaos experiments (target, fault type, duration, bounds, safety)
2. Telemetry delta observations and propagation delay detection
3. Statistical causal inference (Difference-in-Differences, effect size, repeatability)
4. Calibrated NetworkX graph representation with provenance tiers
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class CausalProvenance(str, Enum):
    """Provenance tiers for graph dependencies."""
    DECLARED = "DECLARED"                    # Declared in architecture / config; unverified experimentally
    OBSERVED = "OBSERVED"                    # Statistically significant effect observed (1-2 runs)
    VALIDATED_CAUSAL = "VALIDATED_CAUSAL"    # Experimentally confirmed (>=3 runs, high repeatability, low confounder bias)
    UNCERTAIN = "UNCERTAIN"                  # Inconclusive, noisy, or conflicting experimental results


class FaultType(str, Enum):
    """Approved fault injection types."""
    LATENCY = "latency"
    ERROR = "error"
    UNAVAILABILITY = "unavailability"
    CPU_STRESS = "cpu_stress"


class CausalExperimentRequest(BaseModel):
    """Request payload to execute a controlled calibration experiment."""
    target_service: str = Field(..., description="Service to inject fault into (e.g. payment-service)")
    fault_type: FaultType = Field(FaultType.LATENCY, description="Type of fault to inject")
    intensity: float = Field(0.8, ge=0.1, le=1.0, description="Fault intensity (bounded between 0.1 and 1.0)")
    duration_seconds: int = Field(30, ge=5, le=300, description="Duration in seconds (bounded <= 300s)")
    control_service: Optional[str] = Field("auth-service", description="Control service for Difference-in-Differences confounder mitigation")
    environment: str = Field("demo", description="Isolated test environment (production requires explicit flag)")
    allow_production: bool = Field(False, description="Explicit override for production (requires admin governance)")


class ObservedNeighborImpact(BaseModel):
    """Measured telemetry changes on an upstream/downstream neighbor."""
    neighbor_service: str
    direction: str = "UPSTREAM_CALLER"  # UPSTREAM_CALLER, DOWNSTREAM_DEPENDENT, or CONTROL
    baseline_latency_ms: float
    treatment_latency_ms: float
    delta_latency_ms: float
    delta_error_rate_pct: float
    delta_throughput_rps: float
    propagation_delay_ms: float = Field(..., description="Observed delay between injection and downstream onset")
    did_effect_size: float = Field(..., description="Difference-in-Differences effect size vs control")
    z_score: float
    statistical_significance: bool
    causal_contribution: float = Field(..., ge=0.0, le=1.0)


class CausalEdgeSchema(BaseModel):
    """Enriched graph edge with experimental causal calibration."""
    source: str = Field(..., description="Caller service (depends on target)")
    target: str = Field(..., description="Callee service")
    dependency_type: str = "SYNC"
    causal_strength: float = Field(0.5, ge=0.0, le=1.0, description="Calibrated causal strength (0.0 to 1.0)")
    propagation_delay_ms: float = Field(120.0, description="Observed failure propagation delay in ms")
    provenance: CausalProvenance = Field(CausalProvenance.DECLARED, description="Provenance category")
    confidence: float = Field(0.5, ge=0.0, le=1.0, description="Statistical confidence (0.0 to 1.0)")
    repeatability: float = Field(0.5, ge=0.0, le=1.0, description="Consistency across repeated trials")
    experiment_count: int = Field(0, description="Number of supporting experiments")
    is_declared: bool = Field(True, description="Whether this is a declared architecture edge")
    did_effect_size: float = Field(0.0, description="Latest Difference-in-Differences standardized effect size")
    p_value_estimate: float = Field(0.05, description="Estimated empirical p-value")
    last_calibrated_at: Optional[str] = None
    evidence_summary: str = Field("Declared architectural dependency; awaiting experimental calibration.")
    historical_effect_sizes: List[float] = Field(default_factory=list)


class CausalNodeSchema(BaseModel):
    """Graph node representing a service."""
    id: str
    label: str
    tier: int = 1
    service_type: str = "MICROSERVICE"
    criticality: str = "MEDIUM"
    owner: str = "Platform Team"
    is_target: bool = False
    is_control: bool = False


class CausalGraphSummary(BaseModel):
    """Summary metrics of the calibrated causal graph."""
    total_services: int
    total_edges: int
    validated_causal_edges: int
    observed_edges: int
    declared_unvalidated_edges: int
    uncertain_edges: int
    mean_propagation_delay_ms: float
    mean_causal_confidence: float
    total_experiments_recorded: int


class CausalGraphResponse(BaseModel):
    """Complete calibrated causal graph payload."""
    nodes: List[CausalNodeSchema]
    edges: List[CausalEdgeSchema]
    summary: CausalGraphSummary
    calibrated_at: str


class CausalExperimentResult(BaseModel):
    """Full execution output of a controlled calibration experiment."""
    experiment_id: str
    target_service: str
    control_service: str
    fault_type: str
    intensity: float
    duration_seconds: int
    environment: str
    status: str
    started_at: str
    restored_at: str
    duration_elapsed_seconds: float
    baseline_metrics: Dict[str, Any]
    treatment_metrics: Dict[str, Any]
    recovery_metrics: Dict[str, Any]
    observed_impacts: List[ObservedNeighborImpact]
    calibrated_edges: List[CausalEdgeSchema]
    safety_audit: Dict[str, Any]
    causal_inference_method: str = "Difference-in-Differences (DiD) with Directional Asymmetry Verification"


class CausalEdgeEvidenceResponse(BaseModel):
    """Deep-dive evidence for a specific edge."""
    source: str
    target: str
    calibration: CausalEdgeSchema
    supporting_experiments: List[Dict[str, Any]]
    did_distribution: List[float]
    causal_conclusion: str
    recommendation: str
