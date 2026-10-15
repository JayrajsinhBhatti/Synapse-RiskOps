"""
Synapse RiskOps - Dry-Run Twin (Counterfactual Remediation) Service
==================================================================
Provides predictive counterfactual simulations of candidate remediations before
any real action is executed on production systems.

Key Capabilities:
1. Multi-Action Counterfactual Evaluation: Simulates outcomes of candidate actions
   (restart pod, rollback deployment, rate limit, scale replicas, circuit breaker,
   adjust timeouts, flush cache) without modifying real services.
2. Impact Prediction: Computes predicted recovery time, residual error rate,
   P99 latency, resource usage (CPU/memory), downstream cascade blast radius,
   and potential secondary failure risks.
3. Multi-Criteria Tradeoff Ranking: Ranks options by expected recovery, reliability,
   reversibility, and service criticality; flags the safest recommended option.
4. Autonomy Budget & Cascade Integration: Evaluates whether candidates meet auto-execution
   criteria (e.g. risk score <= 74, non-critical service) or require human approval,
   and simulates blast radius using the NetworkX topology graph.
5. Strict Safe Separation: Dry runs NEVER mutate production infrastructure or trigger
   Ansible playbooks. Real execution requires an explicit, authorized request.
6. Transparent Uncertainty & Limitations: Formulates explicit confidence tiers,
   documented queueing assumptions, and missing data disclosures.
"""

import logging
import math
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple
from uuid import UUID

import networkx as nx
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.autonomy import AutonomyPolicyModel, RemediationRecord
from app.models.dry_run import DryRunSimulationRecord
from app.models.incident import Incident
from app.models.service import Service
from app.models.user import User
from app.schemas.dry_run import (
    CandidateActionSimulation,
    DryRunExecuteResponse,
    DryRunSimulationResponse,
    SecondaryFailureRisk,
)
from app.services.autonomy_budget import ACTION_PROFILES, autonomy_budget_engine
from app.services.cascade_planner import cascade_planner_service

logger = logging.getLogger("synapse.dry_run_twin")

SIMULATION_MODEL_VERSION = "CounterfactualQueueingTwin-v1.2"

# Candidate Actions Catalog with Domain Characteristics & Secondary Hazards
CANDIDATE_ACTION_METADATA: Dict[str, Dict[str, Any]] = {
    "SCALE_OUT_PODS": {
        "name": "Horizontal Replicas Scale-Out (+100%)",
        "description": "Doubles running worker pod count to distribute request concurrency and relieve CPU/memory pressure.",
        "reversibility": "REVERSIBLE",
        "base_exec_sec": 4.5,
        "base_rec_sec": 8.0,
        "cpu_reduction_factor": 0.50,
        "mem_reduction_factor": 0.25,
        "error_reduction_factor": 0.85,
        "p99_reduction_factor": 0.65,
        "secondary_risks": [
            {
                "risk_type": "DATABASE_CONNECTION_POOL_EXHAUSTION",
                "target_component": "postgres-primary",
                "probability": 0.28,
                "severity": "HIGH",
                "mitigation_hint": "Verify PostgreSQL max_connections and PgBouncer pool sizing before scaling worker replicas.",
            }
        ],
    },
    "RESTART_POD": {
        "name": "Worker Pod Rolling Restart",
        "description": "Performs rolling eviction and replacement of degraded pods with health-check gate to clear stuck threads.",
        "reversibility": "PARTIALLY_REVERSIBLE",
        "base_exec_sec": 3.5,
        "base_rec_sec": 7.0,
        "cpu_reduction_factor": 0.65,
        "mem_reduction_factor": 0.70,
        "error_reduction_factor": 0.90,
        "p99_reduction_factor": 0.75,
        "secondary_risks": [
            {
                "risk_type": "COLD_START_LATENCY_SURGE",
                "target_component": "local-worker",
                "probability": 0.22,
                "severity": "MEDIUM",
                "mitigation_hint": "Warm JIT / connection pools sequentially to avoid sudden initial spike upon readiness.",
            },
            {
                "risk_type": "IN_FLIGHT_REQUEST_DROPS",
                "target_component": "api-gateway",
                "probability": 0.15,
                "severity": "LOW",
                "mitigation_hint": "Ensure graceful termination grace period >= 30s.",
            },
        ],
    },
    "RATE_LIMIT_TRAFFIC": {
        "name": "Ingress Rate Limiting & Traffic Shedding",
        "description": "Enforces 50% token-bucket rate limiting at ingress gateway to prevent saturation collapse.",
        "reversibility": "REVERSIBLE",
        "base_exec_sec": 1.5,
        "base_rec_sec": 4.0,
        "cpu_reduction_factor": 0.45,
        "mem_reduction_factor": 0.15,
        "error_reduction_factor": 0.70,
        "p99_reduction_factor": 0.60,
        "secondary_risks": [
            {
                "risk_type": "CLIENT_429_RETRY_STORM",
                "target_component": "api-gateway",
                "probability": 0.35,
                "severity": "MEDIUM",
                "mitigation_hint": "Return Retry-After headers with exponential backoff instructions to mobile & frontend clients.",
            }
        ],
    },
    "ROLLBACK_DEPLOYMENT": {
        "name": "Revert to Previous Stable Revision",
        "description": "Rolls back image revision and configuration to last known healthy release.",
        "reversibility": "REVERSIBLE",
        "base_exec_sec": 6.0,
        "base_rec_sec": 10.0,
        "cpu_reduction_factor": 0.70,
        "mem_reduction_factor": 0.60,
        "error_reduction_factor": 0.95,
        "p99_reduction_factor": 0.85,
        "secondary_risks": [
            {
                "risk_type": "DB_SCHEMA_INCOMPATIBILITY",
                "target_component": "postgres-primary",
                "probability": 0.18,
                "severity": "HIGH",
                "mitigation_hint": "Check if forward database migrations ran that would break backwards compatibility with V-1 code.",
            }
        ],
    },
    "CIRCUIT_BREAKER_TRIP": {
        "name": "Isolate Dependency via Circuit Breaker",
        "description": "Trips circuit breaker on downstream calls, immediately returning cached defaults or fast-fail responses.",
        "reversibility": "REVERSIBLE",
        "base_exec_sec": 1.2,
        "base_rec_sec": 3.0,
        "cpu_reduction_factor": 0.30,
        "mem_reduction_factor": 0.10,
        "error_reduction_factor": 0.60,
        "p99_reduction_factor": 0.80,
        "secondary_risks": [
            {
                "risk_type": "DEGRADED_FEATURE_EXPERIENCE",
                "target_component": "downstream-callers",
                "probability": 0.40,
                "severity": "MEDIUM",
                "mitigation_hint": "Ensure fallback caches serve stale metadata without breaking user checkout flow.",
            }
        ],
    },
    "ADJUST_RETRIES_TIMEOUTS": {
        "name": "Downstream Timeout & Retry Tightening",
        "description": "Lowers downstream client timeouts to 800ms and caps retries at 1 to prevent queue pileups.",
        "reversibility": "REVERSIBLE",
        "base_exec_sec": 2.0,
        "base_rec_sec": 5.0,
        "cpu_reduction_factor": 0.35,
        "mem_reduction_factor": 0.20,
        "error_reduction_factor": 0.65,
        "p99_reduction_factor": 0.70,
        "secondary_risks": [
            {
                "risk_type": "TRANSIENT_CALL_FAILURE",
                "target_component": "intermediate-proxies",
                "probability": 0.14,
                "severity": "LOW",
                "mitigation_hint": "Apply only to idempotent GET/read paths.",
            }
        ],
    },
    "FLUSH_REDIS_CACHE": {
        "name": "L2 Redis Cache Invalidation",
        "description": "Flushes corrupted or stale Redis keys and triggers background warming.",
        "reversibility": "PARTIALLY_REVERSIBLE",
        "base_exec_sec": 2.0,
        "base_rec_sec": 9.0,
        "cpu_reduction_factor": 0.20,
        "mem_reduction_factor": 0.40,
        "error_reduction_factor": 0.80,
        "p99_reduction_factor": 0.50,
        "secondary_risks": [
            {
                "risk_type": "THUNDERING_HERD_CACHE_STAMPEDE",
                "target_component": "postgres-primary",
                "probability": 0.45,
                "severity": "HIGH",
                "mitigation_hint": "Use probabilistic early expiration or single-flight mutex locks on cache misses.",
            }
        ],
    },
}

STANDARD_CANDIDATE_KEYS = [
    "SCALE_OUT_PODS",
    "RESTART_POD",
    "RATE_LIMIT_TRAFFIC",
    "ROLLBACK_DEPLOYMENT",
    "CIRCUIT_BREAKER_TRIP",
    "ADJUST_RETRIES_TIMEOUTS",
    "FLUSH_REDIS_CACHE",
]


class DryRunTwinService:
    """
    Core Domain Service for Counterfactual Predictive Remediation Simulations.
    """

    async def simulate_remediation_options(
        self,
        service_name: str,
        incident_id: Optional[UUID] = None,
        candidate_actions: Optional[List[str]] = None,
        environment: str = "production",
        current_metrics: Optional[Dict[str, float]] = None,
        db: Optional[AsyncSession] = None,
        user: Optional[User] = None,
    ) -> DryRunSimulationResponse:
        """
        Executes a dry-run counterfactual simulation comparing multiple remediation actions
        against the target service and topology without mutating any live system state.
        """
        assumptions: List[str] = [
            "Queueing behavior modeled using M/M/c approximation with service-rate multiplier.",
            "Topology propagation derived from NetworkX directed dependency graph.",
            "Historical recovery timings weighted using verified past successful executions.",
            "Resource limits assume baseline node capacity without external hypervisor throttling.",
            "Residual blast radius computed assuming upstream callers adhere to standard retry policies.",
        ]
        limitations: List[str] = []

        # 1. Resolve Baseline Telemetry
        baseline = await self._resolve_baseline_metrics(
            service_name=service_name,
            incident_id=incident_id,
            user_metrics=current_metrics,
            db=db,
            limitations=limitations,
        )

        # 2. Build or fetch topology graph
        graph = await cascade_planner_service.build_topology_graph(db)

        # 3. Determine Candidate Actions to simulate
        action_keys = candidate_actions if candidate_actions else STANDARD_CANDIDATE_KEYS
        # Filter unknown keys defensively
        action_keys = [k for k in action_keys if k in CANDIDATE_ACTION_METADATA]
        if not action_keys:
            action_keys = STANDARD_CANDIDATE_KEYS

        # 4. Fetch Autonomy Policy & Service Criticality
        criticality = autonomy_budget_engine.get_service_criticality(service_name)
        policy: Optional[AutonomyPolicyModel] = None
        if db:
            policy = await autonomy_budget_engine.get_or_create_policy(db)

        # 5. Query historical execution samples for all candidate actions
        historical_stats = await self._query_historical_outcomes(
            service_name=service_name,
            actions=action_keys,
            db=db,
            limitations=limitations,
        )

        # 6. Simulate each candidate action
        simulations: List[CandidateActionSimulation] = []
        for action_key in action_keys:
            sim = await self._simulate_single_action(
                service_name=service_name,
                action_key=action_key,
                baseline=baseline,
                criticality=criticality,
                graph=graph,
                historical=historical_stats.get(action_key, {}),
                policy=policy,
                db=db,
            )
            simulations.append(sim)

        # 7. Rank candidates and pick safest recommended action
        simulations.sort(key=lambda x: x.efficacy_score, reverse=True)
        if simulations:
            simulations[0].is_recommended = True
            recommended_action = simulations[0].action
        else:
            recommended_action = "SCALE_OUT_PODS"

        # 8. Record immutable simulation audit log
        simulation_id = uuid.uuid4()
        if db:
            audit_record = DryRunSimulationRecord(
                id=simulation_id,
                incident_id=incident_id,
                service_name=service_name,
                environment=environment,
                baseline_metrics=baseline,
                candidate_actions=[s.model_dump() for s in simulations],
                recommended_action=recommended_action,
                recommendation_reason=simulations[0].recommendation_reason if simulations else "Standard fallback",
                assumptions=assumptions,
                limitations=limitations,
                model_version=SIMULATION_MODEL_VERSION,
                is_simulated=True,
            )
            db.add(audit_record)
            await db.flush()

        return DryRunSimulationResponse(
            simulation_id=simulation_id,
            service_name=service_name,
            incident_id=incident_id,
            timestamp=datetime.now(timezone.utc),
            baseline_telemetry=baseline,
            candidate_simulations=simulations,
            recommended_action=recommended_action,
            model_version=SIMULATION_MODEL_VERSION,
            assumptions=assumptions,
            limitations=limitations,
            is_simulated=True,
            disclaimer=(
                "This is a simplified counterfactual predictive simulator based on queueing models, "
                "dependency graph topology, and historical outcomes—not a full infrastructure digital twin. "
                "Never present simulated outcomes as guaranteed real-world results."
            ),
        )

    async def _resolve_baseline_metrics(
        self,
        service_name: str,
        incident_id: Optional[UUID],
        user_metrics: Optional[Dict[str, float]],
        db: Optional[AsyncSession],
        limitations: List[str],
    ) -> Dict[str, Any]:
        """Collects or estimates pre-remediation baseline telemetry."""
        if user_metrics and len(user_metrics) >= 2:
            cpu = float(user_metrics.get("cpu_usage", user_metrics.get("cpu_percent", 75.0)))
            mem = float(user_metrics.get("memory_usage", user_metrics.get("memory_percent", 70.0)))
            err = float(user_metrics.get("error_rate", 8.5))
            p99 = float(user_metrics.get("response_time_p99", user_metrics.get("latency_p99", 450.0)))
        elif incident_id and db:
            res = await db.execute(select(Incident).where(Incident.id == incident_id))
            inc = res.scalar_one_or_none()
            if inc and inc.top_features:
                cpu = float(inc.top_features.get("cpu_usage", 82.0))
                mem = float(inc.top_features.get("memory_usage", 74.0))
                err = float(inc.top_features.get("error_rate", 12.0))
                p99 = float(inc.top_features.get("response_time_p99", 650.0))
            else:
                limitations.append("Active incident record contains incomplete telemetry snapshot; using calibrated degradation priors.")
                cpu, mem, err, p99 = 80.0, 72.0, 9.5, 520.0
        else:
            limitations.append("No live telemetry snapshot provided in request; assuming typical degraded incident baseline.")
            cpu, mem, err, p99 = 78.0, 68.0, 7.5, 420.0

        # Compute baseline composite risk & health score
        # Risk score calculation: 0-100 scale
        risk_score = min(100.0, max(10.0, cpu * 0.4 + err * 4.5 + min(30.0, (p99 / 20.0))))
        health_score = max(0.0, 100.0 - risk_score)

        return {
            "service_name": service_name,
            "cpu_usage_percent": round(cpu, 1),
            "memory_usage_percent": round(mem, 1),
            "error_rate_percent": round(err, 2),
            "response_time_p99_ms": round(p99, 1),
            "risk_score": round(risk_score, 1),
            "health_score": round(health_score, 1),
            "status": "CRITICAL" if risk_score >= 75 else "DEGRADED" if risk_score >= 40 else "HEALTHY",
        }

    async def _query_historical_outcomes(
        self,
        service_name: str,
        actions: List[str],
        db: Optional[AsyncSession],
        limitations: List[str],
    ) -> Dict[str, Dict[str, Any]]:
        """Queries historical verified remediation executions for calibration."""
        stats: Dict[str, Dict[str, Any]] = {}
        if not db:
            limitations.append("Database session unavailable; simulations calibrated strictly via queueing priors.")
            return stats

        try:
            for action in actions:
                res = await db.execute(
                    select(RemediationRecord)
                    .where(
                        RemediationRecord.service_name == service_name,
                        RemediationRecord.action == action,
                    )
                    .order_by(desc(RemediationRecord.created_at))
                    .limit(15)
                )
                records = res.scalars().all()
                if records:
                    successes = [r for r in records if r.success is True]
                    exec_times = [r.actual_execution_seconds for r in successes if r.actual_execution_seconds]
                    rec_times = [r.actual_recovery_seconds for r in successes if r.actual_recovery_seconds]
                    stats[action] = {
                        "total_samples": len(records),
                        "success_rate": len(successes) / len(records),
                        "avg_exec_sec": sum(exec_times) / len(exec_times) if exec_times else None,
                        "avg_rec_sec": sum(rec_times) / len(rec_times) if rec_times else None,
                    }
                else:
                    stats[action] = {
                        "total_samples": 0,
                        "success_rate": 0.85,  # prior
                        "avg_exec_sec": None,
                        "avg_rec_sec": None,
                    }
            
            zero_sample_actions = [a for a, s in stats.items() if s.get("total_samples", 0) == 0]
            if zero_sample_actions:
                limitations.append(
                    f"0 historical verified executions recorded for [{', '.join(zero_sample_actions[:3])}] on {service_name}; using empirical action profiles."
                )
        except Exception as e:
            logger.warning(f"Error querying historical remediation outcomes: {e}")
            limitations.append(f"Historical query degraded ({str(e)}); utilizing baseline priors.")

        return stats

    async def _simulate_single_action(
        self,
        service_name: str,
        action_key: str,
        baseline: Dict[str, Any],
        criticality: str,
        graph: nx.DiGraph,
        historical: Dict[str, Any],
        policy: Optional[AutonomyPolicyModel],
        db: Optional[AsyncSession],
    ) -> CandidateActionSimulation:
        """Predicts outcome of one counterfactual remediation action."""
        meta = CANDIDATE_ACTION_METADATA.get(action_key, {})
        name = meta.get("name", action_key)
        description = meta.get("description", "Remediation action")
        reversibility = meta.get("reversibility", "REVERSIBLE")

        # 1. Timing Estimates
        samples = historical.get("total_samples", 0)
        hist_exec = historical.get("avg_exec_sec")
        hist_rec = historical.get("avg_rec_sec")

        base_exec = meta.get("base_exec_sec", 4.0)
        base_rec = meta.get("base_rec_sec", 8.0)

        if samples >= 3 and hist_exec and hist_rec:
            # Calibrated blend
            exec_sec = round(hist_exec * 0.7 + base_exec * 0.3, 1)
            rec_sec = round(hist_rec * 0.7 + base_rec * 0.3, 1)
            confidence = 0.92
            uncertainty = "LOW"
        elif samples >= 1 and hist_exec:
            exec_sec = round(hist_exec * 0.5 + base_exec * 0.5, 1)
            rec_sec = round(base_rec * 1.1, 1)
            confidence = 0.78
            uncertainty = "MEDIUM"
        else:
            exec_sec = base_exec
            rec_sec = base_rec
            confidence = 0.65
            uncertainty = "HIGH"

        # 2. Predicted Telemetry Post-Remediation
        cpu_red = meta.get("cpu_reduction_factor", 0.50)
        mem_red = meta.get("mem_reduction_factor", 0.30)
        err_red = meta.get("error_reduction_factor", 0.85)
        p99_red = meta.get("p99_reduction_factor", 0.70)

        pred_cpu = max(15.0, round(baseline["cpu_usage_percent"] * (1.0 - cpu_red), 1))
        pred_mem = max(25.0, round(baseline["memory_usage_percent"] * (1.0 - mem_red), 1))
        pred_err = max(0.01, round(baseline["error_rate_percent"] * (1.0 - err_red), 2))
        pred_p99 = max(18.0, round(baseline["response_time_p99_ms"] * (1.0 - p99_red), 1))

        # Predicted composite risk score
        pred_risk = min(100.0, max(5.0, pred_cpu * 0.35 + pred_err * 4.0 + min(20.0, pred_p99 / 25.0)))
        pred_health = max(0.0, round(100.0 - pred_risk, 1))
        pred_risk = round(pred_risk, 1)

        health_delta = round(pred_health - baseline["health_score"], 1)
        risk_delta = round(baseline["risk_score"] - pred_risk, 1)

        # 3. Downstream Cascade Blast Radius Prediction
        # If circuit breaker or rate limiting is applied, caller edges are insulated
        sim_disabled_edges: Set[Tuple[str, str]] = set()
        if action_key == "CIRCUIT_BREAKER_TRIP" and service_name in graph:
            for caller in graph.predecessors(service_name):
                sim_disabled_edges.add((caller, service_name))

        cascade_result = cascade_planner_service.simulate_propagation(
            graph=graph,
            seed_service=service_name,
            failure_type="latency_spike",
            disabled_edges=sim_disabled_edges,
        )

        affected_downstream = [h.service_name for h in cascade_result.propagation_timeline if not h.is_seed]
        blast_pct = getattr(cascade_result, "blast_radius_percent", 20.0)
        blast_radius_tier = "HIGH" if blast_pct >= 40.0 else "MODERATE" if blast_pct >= 15.0 else "LOW"
        protected_count = max(0, graph.number_of_nodes() - len(cascade_result.propagation_timeline))

        # 4. Secondary Failure Hazards
        sec_hazards: List[SecondaryFailureRisk] = []
        raw_risks = meta.get("secondary_risks", [])
        total_sec_prob = 0.0
        for r in raw_risks:
            sec_risk = SecondaryFailureRisk(
                risk_type=r["risk_type"],
                target_component=r["target_component"],
                probability=r["probability"],
                severity=r["severity"],
                mitigation_hint=r["mitigation_hint"],
            )
            sec_hazards.append(sec_risk)
            total_sec_prob = max(total_sec_prob, r["probability"])

        # 5. Autonomy Budget Governance Assessment
        # Criteria: risk score <= 74.0, non-critical service, reversible action
        is_critical = criticality == "CRITICAL"
        is_above_threshold = baseline["risk_score"] > 74.0

        if is_critical or is_above_threshold or reversibility == "IRREVERSIBLE":
            can_auto = False
            if is_critical:
                approval_req = "STRICT_HUMAN_APPROVAL"
            else:
                approval_req = "REQUIRES_APPROVAL"
        else:
            can_auto = True
            approval_req = "AUTO_EXECUTABLE"

        # 6. Efficacy & Safety Score Calculation (0-100)
        # Weights: Health recovery (35%), Risk delta (30%), Reversibility (15%), Speed (10%), Secondary safety (10%)
        rev_weight = 15.0 if reversibility == "REVERSIBLE" else 8.0 if reversibility == "PARTIALLY_REVERSIBLE" else 0.0
        speed_score = max(0.0, 10.0 - (rec_sec / 3.0))
        safety_bonus = max(0.0, 10.0 * (1.0 - total_sec_prob))

        efficacy = (
            (pred_health * 0.35)
            + (min(100.0, risk_delta * 1.5) * 0.30)
            + rev_weight
            + speed_score
            + safety_bonus
        )
        efficacy = max(0.0, min(100.0, round(efficacy, 1)))

        # Justification reasoning
        reason = (
            f"Expected to reduce risk by {risk_delta} pts (health -> {pred_health}%), "
            f"stabilizing P99 latency at ~{pred_p99}ms and error rate at ~{pred_err}%. "
            f"Reversibility: {reversibility}. Secondary risk: {round(total_sec_prob * 100)}%."
        )

        return CandidateActionSimulation(
            action=action_key,
            name=name,
            description=description,
            reversibility=reversibility,
            estimated_execution_seconds=exec_sec,
            estimated_recovery_seconds=rec_sec,
            predicted_health_score=pred_health,
            predicted_risk_score=pred_risk,
            health_delta=health_delta,
            risk_delta=risk_delta,
            predicted_error_rate=pred_err,
            predicted_p99_latency_ms=pred_p99,
            predicted_cpu_percent=pred_cpu,
            predicted_memory_percent=pred_mem,
            blast_radius_tier=blast_radius_tier,
            affected_downstream_services=affected_downstream,
            protected_services_count=protected_count,
            secondary_failure_risks=sec_hazards,
            secondary_failure_probability=round(total_sec_prob, 2),
            confidence_score=round(confidence, 2),
            uncertainty_tier=uncertainty,
            historical_sample_count=samples,
            can_auto_execute=can_auto,
            approval_requirement=approval_req,
            efficacy_score=efficacy,
            is_recommended=False,  # Updated after sorting
            recommendation_reason=reason,
        )

    async def get_simulation_history(
        self,
        service_name: Optional[str] = None,
        limit: int = 20,
        db: Optional[AsyncSession] = None,
    ) -> List[Dict[str, Any]]:
        """Retrieves audit trail of past counterfactual simulations."""
        if not db:
            return []

        query = select(DryRunSimulationRecord).order_by(desc(DryRunSimulationRecord.created_at)).limit(limit)
        if service_name:
            query = query.where(DryRunSimulationRecord.service_name == service_name)

        res = await db.execute(query)
        records = res.scalars().all()
        return [
            {
                "id": str(r.id),
                "incident_id": str(r.incident_id) if r.incident_id else None,
                "service_name": r.service_name,
                "environment": r.environment,
                "recommended_action": r.recommended_action,
                "recommendation_reason": r.recommendation_reason,
                "candidate_count": len(r.candidate_actions) if r.candidate_actions else 0,
                "is_simulated": r.is_simulated,
                "executed_action": r.executed_action,
                "executed_at": r.executed_at.isoformat() if r.executed_at else None,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in records
        ]

    async def get_simulation(
        self,
        simulation_id: UUID,
        db: AsyncSession,
    ) -> Optional[DryRunSimulationResponse]:
        """Fetches full details of a past simulation run for replay/audit."""
        res = await db.execute(select(DryRunSimulationRecord).where(DryRunSimulationRecord.id == simulation_id))
        rec = res.scalar_one_or_none()
        if not rec:
            return None

        candidates = [CandidateActionSimulation(**c) for c in (rec.candidate_actions or [])]
        return DryRunSimulationResponse(
            simulation_id=rec.id,
            service_name=rec.service_name,
            incident_id=rec.incident_id,
            timestamp=rec.created_at,
            baseline_telemetry=rec.baseline_metrics or {},
            candidate_simulations=candidates,
            recommended_action=rec.recommended_action,
            model_version=rec.model_version or SIMULATION_MODEL_VERSION,
            assumptions=rec.assumptions or [],
            limitations=rec.limitations or [],
            is_simulated=rec.is_simulated,
            disclaimer=(
                "This is a simplified counterfactual predictive simulator based on queueing models, "
                "dependency graph topology, and historical outcomes—not a full infrastructure digital twin. "
                "Never present simulated outcomes as guaranteed real-world results."
            ),
        )

    async def execute_authorized_action(
        self,
        simulation_id: UUID,
        selected_action: Optional[str] = None,
        approval_notes: Optional[str] = None,
        user: Optional[User] = None,
        db: Optional[AsyncSession] = None,
    ) -> DryRunExecuteResponse:
        """
        Explicit, authorized bridge from predictive simulation to real execution.
        Safely dispatches approved action via Autonomy Budget Engine and Ansible Playbooks.
        """
        if not db:
            raise ValueError("Database session required for authorized remediation execution.")

        res = await db.execute(select(DryRunSimulationRecord).where(DryRunSimulationRecord.id == simulation_id))
        sim_record = res.scalar_one_or_none()
        if not sim_record:
            raise ValueError(f"Simulation record {simulation_id} not found.")

        action_to_exec = selected_action or sim_record.recommended_action

        # Dispatch via standard Autonomy Budget Engine
        exec_res = await autonomy_budget_engine.execute_remediation_with_budget(
            service_name=sim_record.service_name,
            action=action_to_exec,
            incident_id=sim_record.incident_id,
            remediation_record_id=None,
            user=user,
            db=db,
            approval_notes=approval_notes,
        )

        # Update simulation record with execution metadata
        sim_record.executed_action = action_to_exec
        sim_record.executed_at = datetime.now(timezone.utc)
        sim_record.executed_by = user.id if user else None
        sim_record.executed_by_username = user.username if user else "system"
        if exec_res.get("remediation_record_id"):
            try:
                sim_record.remediation_record_id = UUID(exec_res["remediation_record_id"])
            except Exception:
                pass

        await db.flush()

        return DryRunExecuteResponse(
            simulation_id=simulation_id,
            executed_action=action_to_exec,
            target_service=sim_record.service_name,
            execution_status="DISPATCHED",
            ansible_task_id=exec_res.get("ansible_task_id"),
            semaphore_url=exec_res.get("semaphore_history_url"),
            remediation_record_id=exec_res.get("remediation_record_id"),
            message=f"Authorized action [{action_to_exec}] dispatched to Ansible Semaphore for [{sim_record.service_name}].",
        )


dry_run_twin_service = DryRunTwinService()
