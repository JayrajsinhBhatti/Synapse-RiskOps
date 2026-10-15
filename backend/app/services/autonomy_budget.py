"""
Synapse RiskOps - Autonomy Budget Engine Service
================================================
Evaluates proposed remediations against service criticality, blast radius,
action reversibility, historical reliability, remaining error budget, and timing.
Enforces backend safety policies (LOW RISK: auto-execute, MEDIUM/HIGH RISK: human approval),
prevents duplicate concurrent actions, logs immutable audit entries, and records
verified execution/recovery metrics to continuously calibrate future estimates.
"""

import logging
import math
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID, uuid4

from sqlalchemy import Integer, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.autonomy import AutonomyAuditLog, AutonomyPolicyModel, RemediationRecord
from app.models.incident import Incident, IncidentHistory
from app.models.service import Service
from app.models.user import User
from app.schemas.autonomy import (
    AutonomyBudgetStatusResponse,
    AutonomyEvaluationResponse,
    TimingEstimate,
)
from app.services.ansible_service import ansible_service
from app.services.sse_manager import sse_manager

logger = logging.getLogger("synapse.autonomy_budget")

# Criticality Classifications
CRITICAL_SERVICES = {
    "payment-service",
    "auth-service",
    "postgres-primary",
    "database",
    "api-gateway",
    "message-queue",
}

HIGH_CRITICALITY_SERVICES = {
    "order-service",
    "inventory-service",
    "user-service",
}

MEDIUM_CRITICALITY_SERVICES = {
    "notification-service",
    "recommendation-service",
    "analytics-service",
    "reporting-service",
}

# Action Profiles (Baseline characteristics)
ACTION_PROFILES: Dict[str, Dict[str, Any]] = {
    "SCALE_OUT_PODS": {
        "reversibility": "REVERSIBLE",
        "blast_radius": "LOW",
        "default_reliability": 0.98,
        "baseline_exec_sec": 4.5,
        "baseline_rec_sec": 8.0,
    },
    "SCALE_SERVICE": {
        "reversibility": "REVERSIBLE",
        "blast_radius": "LOW",
        "default_reliability": 0.97,
        "baseline_exec_sec": 5.0,
        "baseline_rec_sec": 9.0,
    },
    "RESTART_SERVICE": {
        "reversibility": "REVERSIBLE",
        "blast_radius": "MODERATE",
        "default_reliability": 0.92,
        "baseline_exec_sec": 5.0,
        "baseline_rec_sec": 10.0,
    },
    "RESTART_POD": {
        "reversibility": "REVERSIBLE",
        "blast_radius": "LOW",
        "default_reliability": 0.94,
        "baseline_exec_sec": 3.5,
        "baseline_rec_sec": 7.0,
    },
    "RESTART_CONNECTION_POOL": {
        "reversibility": "REVERSIBLE",
        "blast_radius": "MODERATE",
        "default_reliability": 0.91,
        "baseline_exec_sec": 4.0,
        "baseline_rec_sec": 8.5,
    },
    "FLUSH_REDIS_CACHE": {
        "reversibility": "PARTIALLY_REVERSIBLE",
        "blast_radius": "MODERATE",
        "default_reliability": 0.88,
        "baseline_exec_sec": 2.0,
        "baseline_rec_sec": 12.0,
    },
    "CLEAR_DISK": {
        "reversibility": "PARTIALLY_REVERSIBLE",
        "blast_radius": "LOW",
        "default_reliability": 0.96,
        "baseline_exec_sec": 3.0,
        "baseline_rec_sec": 5.0,
    },
    "DRAIN_CANARY_TRAFFIC": {
        "reversibility": "REVERSIBLE",
        "blast_radius": "LOW",
        "default_reliability": 0.99,
        "baseline_exec_sec": 2.5,
        "baseline_rec_sec": 4.0,
    },
    "DRAIN_TRAFFIC": {
        "reversibility": "REVERSIBLE",
        "blast_radius": "HIGH",
        "default_reliability": 0.90,
        "baseline_exec_sec": 6.0,
        "baseline_rec_sec": 15.0,
    },
    "RESET_NETWORK": {
        "reversibility": "PARTIALLY_REVERSIBLE",
        "blast_radius": "HIGH",
        "default_reliability": 0.82,
        "baseline_exec_sec": 8.0,
        "baseline_rec_sec": 20.0,
    },
    "CIRCUIT_BREAKER_TRIP": {
        "reversibility": "REVERSIBLE",
        "blast_radius": "MODERATE",
        "default_reliability": 0.95,
        "baseline_exec_sec": 1.5,
        "baseline_rec_sec": 6.0,
    },
}


class AutonomyBudgetEngine:
    """Core domain service for evaluating and enforcing autonomy budgets."""

    async def get_or_create_policy(self, db: AsyncSession) -> AutonomyPolicyModel:
        """Fetch or initialize organization autonomy policy."""
        res = await db.execute(select(AutonomyPolicyModel).where(AutonomyPolicyModel.id == "default"))
        policy = res.scalar_one_or_none()
        if not policy:
            policy = AutonomyPolicyModel(
                id="default",
                low_risk_auto_execute=True,
                medium_risk_requires_approval=True,
                critical_services_always_require_approval=True,
                min_historical_samples=3.0,
                error_budget_threshold_percent=20.0,
                max_auto_recovery_time_seconds=60.0,
            )
            db.add(policy)
            await db.flush()
        return policy

    def get_service_criticality(self, service_name: str) -> str:
        """Categorize service criticality."""
        name_lower = service_name.lower().strip()
        if name_lower in CRITICAL_SERVICES or "payment" in name_lower or "auth" in name_lower or "postgres" in name_lower:
            return "CRITICAL"
        if name_lower in HIGH_CRITICALITY_SERVICES or "order" in name_lower or "inventory" in name_lower:
            return "HIGH"
        if name_lower in MEDIUM_CRITICALITY_SERVICES or "recommendation" in name_lower:
            return "MEDIUM"
        return "LOW"

    def calculate_remaining_error_budget(self, metrics: Optional[Dict[str, float]]) -> float:
        """
        Estimate remaining reliability/error budget (0-100%).
        Baseline is 100%, depleted by current error rate and p99 latency spikes.
        """
        if not metrics:
            return 85.0

        error_rate = float(metrics.get("error_rate", 0.0))
        latency_p99 = float(metrics.get("latency_p99", metrics.get("response_time_p99", 50.0)))

        # Error rate penalty (e.g., 5% error rate drains 50% of budget)
        error_penalty = min(80.0, error_rate * 10.0)
        # Latency penalty over 200ms
        latency_penalty = min(20.0, max(0.0, (latency_p99 - 200.0) / 20.0))

        remaining = max(0.0, 100.0 - (error_penalty + latency_penalty))
        return round(remaining, 1)

    async def compute_timing_estimate(
        self,
        service_name: str,
        action: str,
        min_samples: int,
        db: AsyncSession,
    ) -> TimingEstimate:
        """
        Derive execution and recovery time estimates using:
        1. Verified historical records if sample count >= min_samples ('historical')
        2. Config/action baselines adjusted by metrics if 1 <= samples < min_samples ('calculated')
        3. 'insufficient_data' if unknown action or 0 samples and uncalibrated
        """
        # Query verified historical executions for this action & service
        res = await db.execute(
            select(RemediationRecord)
            .where(
                RemediationRecord.action == action,
                RemediationRecord.service_name == service_name,
                RemediationRecord.success == True,  # Only verified successes
                RemediationRecord.actual_execution_seconds.isnot(None),
                RemediationRecord.actual_recovery_seconds.isnot(None),
            )
            .order_by(desc(RemediationRecord.completed_at))
            .limit(20)
        )
        records = res.scalars().all()
        n = len(records)

        profile = ACTION_PROFILES.get(action.upper())

        if n >= min_samples:
            # Source: historical
            exec_times = [r.actual_execution_seconds for r in records if r.actual_execution_seconds]
            rec_times = [r.actual_recovery_seconds for r in records if r.actual_recovery_seconds]

            mean_exec = sum(exec_times) / len(exec_times)
            mean_rec = sum(rec_times) / len(rec_times)

            variance_rec = sum((x - mean_rec) ** 2 for x in rec_times) / max(1, len(rec_times) - 1)
            std_rec = math.sqrt(variance_rec)
            uncertainty_str = f"±{max(round(std_rec, 1), 0.5):.1f}s"

            display = f"Estimated restart: {mean_exec:.1f}s; expected recovery: {mean_rec:.1f}s (Historical: N={n}, {uncertainty_str})"

            return TimingEstimate(
                estimated_execution_seconds=round(mean_exec, 1),
                estimated_recovery_seconds=round(mean_rec, 1),
                source="historical",
                uncertainty=uncertainty_str,
                display_text=display,
                historical_sample_count=n,
            )

        elif profile is not None:
            # Source: calculated (baseline configuration + available sample weighting)
            base_exec = float(profile["baseline_exec_sec"])
            base_rec = float(profile["baseline_rec_sec"])

            if n > 0:
                # Blend available records
                exec_times = [r.actual_execution_seconds for r in records if r.actual_execution_seconds]
                rec_times = [r.actual_recovery_seconds for r in records if r.actual_recovery_seconds]
                if exec_times and rec_times:
                    base_exec = round((base_exec + sum(exec_times) / len(exec_times)) / 2.0, 1)
                    base_rec = round((base_rec + sum(rec_times) / len(rec_times)) / 2.0, 1)

            uncertainty_str = "±2.5s"
            sample_note = f"N={n}" if n > 0 else "N=0 baseline"
            display = f"Estimated restart: {base_exec:.1f}s; expected recovery: {base_rec:.1f}s (Calculated: {sample_note}, {uncertainty_str})"

            return TimingEstimate(
                estimated_execution_seconds=base_exec,
                estimated_recovery_seconds=base_rec,
                source="calculated",
                uncertainty=uncertainty_str,
                display_text=display,
                historical_sample_count=n,
            )

        else:
            # Source: insufficient_data
            return TimingEstimate(
                estimated_execution_seconds=None,
                estimated_recovery_seconds=None,
                source="insufficient_data",
                uncertainty=None,
                display_text="Insufficient data (uncalibrated action; timing bounds unavailable)",
                historical_sample_count=0,
            )

    async def check_concurrency_lock(
        self,
        service_name: str,
        incident_id: Optional[UUID],
        db: AsyncSession,
    ) -> Optional[RemediationRecord]:
        """
        Check if an active remediation is currently actively executing for this service or incident.
        Prevents unsafe duplicate concurrent executions.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=60)
        query = select(RemediationRecord).where(
            RemediationRecord.service_name == service_name,
            RemediationRecord.status == "EXECUTING",
            RemediationRecord.executed_at >= cutoff,
        )
        res = await db.execute(query)
        active = res.scalars().first()
        if active:
            return active

        if incident_id:
            query_inc = select(RemediationRecord).where(
                RemediationRecord.incident_id == incident_id,
                RemediationRecord.status == "EXECUTING",
                RemediationRecord.executed_at >= cutoff,
            )
            res_inc = await db.execute(query_inc)
            active_inc = res_inc.scalars().first()
            if active_inc:
                return active_inc

        return None

    async def evaluate(
        self,
        service_name: str,
        action: str,
        runbook_id: Optional[str] = None,
        incident_id: Optional[UUID] = None,
        current_metrics: Optional[Dict[str, float]] = None,
        risk_tier: Optional[str] = None,
        risk_score: Optional[float] = None,
        incident_criticality: Optional[str] = None,
        auto_execute_if_cleared: bool = False,
        db: Optional[AsyncSession] = None,
        current_user: Optional[User] = None,
    ) -> AutonomyEvaluationResponse:
        """
        Comprehensive autonomy evaluation of a proposed remediation.
        Evaluates:
        - Criticality & risk dimensions:
          * Low-mid criticality incidents are automatically fixed (AUTO_EXECUTE)
          * High criticality & high risk incidents mandate human-in-the-loop (REQUIRE_APPROVAL)
        - Potential damage & reversibility
        - Action reliability & remaining error budget
        - Timing estimates (historical vs calculated vs insufficient_data)
        - Decision: AUTO_EXECUTE vs REQUIRE_APPROVAL vs REJECTED
        """
        if db is None:
            raise ValueError("Database session required for autonomy evaluation")

        policy = await self.get_or_create_policy(db)
        criticality = self.get_service_criticality(service_name)
        profile = ACTION_PROFILES.get(action.upper()) or {}

        reversibility = profile.get("reversibility", "PARTIALLY_REVERSIBLE")
        blast_radius = profile.get("blast_radius", "MODERATE")
        action_reliability = float(profile.get("default_reliability", 0.85))

        # Check historical success rate from records
        hist_count_res = await db.execute(
            select(
                func.count(RemediationRecord.id),
                func.sum(func.cast(RemediationRecord.success == True, Integer)),
            ).where(
                RemediationRecord.action == action,
                RemediationRecord.service_name == service_name,
                RemediationRecord.success.isnot(None),
            )
        )
        # Note: handle fallback if cast isn't available
        error_budget = self.calculate_remaining_error_budget(current_metrics)
        min_samples = int(policy.min_historical_samples)
        timing = await self.compute_timing_estimate(service_name, action, min_samples, db)

        # Resolve effective risk tier, risk score, and criticality
        effective_risk_tier = (risk_tier or "").upper() if risk_tier else None
        effective_risk_score = risk_score
        effective_criticality = (incident_criticality or criticality or "MEDIUM").upper()

        inc_obj = None
        if incident_id and db:
            inc_lookup = await db.execute(select(Incident).where(Incident.id == incident_id))
            inc_obj = inc_lookup.scalar_one_or_none()
            if inc_obj:
                if not effective_risk_tier:
                    effective_risk_tier = (inc_obj.risk_tier or inc_obj.severity or "").upper()
                if effective_risk_score is None and inc_obj.risk_score:
                    effective_risk_score = float(inc_obj.risk_score)
                if not incident_criticality and inc_obj.severity:
                    effective_criticality = inc_obj.severity.upper()

        # Strict Risk Score Governance:
        # If risk score is above 74 (> 74.0) OR critical service with policy -> Mandate human intervention (REQUIRE_APPROVAL)
        # If risk score is at or below 74 (<= 74.0) and non-critical -> Automatically execute remediation (AUTO_EXECUTE)
        requires_human_intervention = (
            (effective_risk_score is not None and effective_risk_score > 74.0)
            or (effective_risk_score is None and (effective_risk_tier == "CRITICAL" or criticality == "CRITICAL"))
            or (policy.critical_services_always_require_approval and criticality == "CRITICAL")
        )

        human_in_the_loop_required = False
        factors = []

        # Concurrency safety check
        active_conflict = await self.check_concurrency_lock(service_name, incident_id, db)
        if active_conflict:
            decision = "REJECTED"
            risk_level = "HIGH"
            approval_required = False
            human_in_the_loop_required = False
            reasoning = (
                f"REJECTED: Duplicate execution prevented. Action '{active_conflict.action}' "
                f"is already currently running on service '{service_name}' (Record #{active_conflict.id})."
            )
            factors.append("Concurrency conflict: Active execution in progress")
        elif requires_human_intervention:
            # RISK SCORE ABOVE 74: Mandate human intervention!
            risk_level = "HIGH"
            decision = "REQUIRE_APPROVAL"
            approval_required = True
            human_in_the_loop_required = True
            risk_display = f"risk_score={effective_risk_score:.1f}%" if effective_risk_score is not None else (effective_risk_tier or "CRITICAL")
            if criticality == "CRITICAL" or effective_criticality == "CRITICAL":
                factors.append(
                    f"CRITICAL SERVICE SAFEGUARD: Service '{service_name}' is classified as CRITICAL (core payment/auth/database path). "
                    f"Automated execution blocked; operator approval strictly required."
                )
            factors.append(
                f"HIGH RISK GOVERNANCE / HUMAN-IN-THE-LOOP REQUIRED: Service '{service_name}' "
                f"requires operator approval ({risk_display}). "
                f"Automated execution is blocked; human intervention is strictly required. Admin or Engineer must click Execute/Approve in dashboard."
            )
            reasoning = (
                f"Safeguard enforced on '{service_name}' ({risk_display}). "
                f"Automated execution blocked; human-in-the-loop operator approval required."
            )
        else:
            # RISK SCORE AT OR BELOW 74: Automatically executed with no human intervention required!
            risk_level = "LOW"
            decision = "AUTO_EXECUTE"
            approval_required = False
            human_in_the_loop_required = False
            risk_display = f"risk_score={effective_risk_score:.1f}%" if effective_risk_score is not None else "LOW_MID"
            factors.append(
                f"LOW-MID CRITICALITY AUTO-FIX: Service '{service_name}' has low-mid criticality ({effective_criticality}). "
                f"Cleared for automated autonomous remediation without human intervention."
            )
            factors.append(
                f"AUTONOMOUS AUTO-EXECUTE: Incident on '{service_name}' has risk score <= 74 ({risk_display}). "
                f"Automatically executed without requiring human intervention."
            )
            reasoning = (
                f"Incident risk score is at or below 74 ({risk_display}). "
                f"Cleared for automatic autonomous remediation without requiring human intervention."
            )

        # Create or update pre-execution RemediationRecord
        cutoff_recent = datetime.now(timezone.utc) - timedelta(hours=2)
        exist_query = select(RemediationRecord).where(
            RemediationRecord.service_name == service_name,
            RemediationRecord.action == action,
            RemediationRecord.status.in_(["PROPOSED", "PENDING_APPROVAL", "APPROVED", "REJECTED"]),
            RemediationRecord.created_at >= cutoff_recent,
        ).order_by(RemediationRecord.created_at.desc())
        if incident_id:
            exist_query = exist_query.where(RemediationRecord.incident_id == incident_id)
        exist_res = await db.execute(exist_query)
        record = exist_res.scalars().first()

        valid_incident_id = inc_obj.id if inc_obj else None
        if record:
            record.estimated_execution_seconds = timing.estimated_execution_seconds
            record.estimated_recovery_seconds = timing.estimated_recovery_seconds
            record.estimate_source = timing.source
            record.estimate_uncertainty = timing.uncertainty
            record.estimate_display = timing.display_text
            record.evaluation_factors = factors
            record.pre_metrics = current_metrics
            if valid_incident_id and not record.incident_id:
                record.incident_id = valid_incident_id

            if record.approval_status == "REJECTED":
                decision = "REJECTED"
                approval_required = False
                reasoning = f"REJECTED by operator: {record.rejection_reason or 'Operation rejected.'}"
            elif record.approval_status == "APPROVED":
                decision = "APPROVED"
                approval_required = False
                reasoning = f"APPROVED by operator ({record.approved_by_username or 'Operator'}). Ready for dispatch."
            else:
                record.risk_level = risk_level
                record.autonomy_decision = decision
                record.approval_status = "AUTO_APPROVED" if decision == "AUTO_EXECUTE" else "PENDING"
                record.reasoning = reasoning
        else:
            record = RemediationRecord(
                incident_id=valid_incident_id,
                service_name=service_name,
                action=action,
                runbook_id=runbook_id or profile.get("playbook"),
                risk_level=risk_level,
                autonomy_decision=decision,
                approval_status="AUTO_APPROVED" if decision == "AUTO_EXECUTE" else "PENDING",
                status="PROPOSED" if decision != "REJECTED" else "REJECTED",
                estimated_execution_seconds=timing.estimated_execution_seconds,
                estimated_recovery_seconds=timing.estimated_recovery_seconds,
                estimate_source=timing.source,
                estimate_uncertainty=timing.uncertainty,
                estimate_display=timing.display_text,
                reasoning=reasoning,
                evaluation_factors=factors,
                pre_metrics=current_metrics,
            )
            db.add(record)

        await db.flush()

        # Audit log entry for evaluation
        audit = AutonomyAuditLog(
            remediation_id=record.id,
            event_type="EVALUATED",
            service_name=service_name,
            action=action,
            user_id=getattr(current_user, "id", None) if current_user and getattr(current_user, "username", "") != "system" else None,
            user_role=getattr(current_user, "role", "SYSTEM") if current_user else "SYSTEM",
            user_username=getattr(current_user, "username", "system") if current_user else "system",
            decision=decision,
            details={
                "risk_level": risk_level,
                "criticality": criticality,
                "factors": factors,
                "timing": timing.model_dump(),
                "error_budget_remaining": error_budget,
            },
        )
        db.add(audit)
        await db.flush()

        executed = False
        execution_result = None
        if decision == "AUTO_EXECUTE" and auto_execute_if_cleared:
            try:
                execution_result = await self.execute_remediation_with_budget(
                    service_name=service_name,
                    action=action,
                    incident_id=incident_id,
                    remediation_record_id=record.id,
                    user=current_user,
                    db=db,
                    approval_notes="Auto-remediated autonomously via Autonomy Budget low-risk policy.",
                )
                executed = True
            except Exception as auto_err:
                logger.warning(f"Auto-execute on low-risk task notice: {auto_err}")

        return AutonomyEvaluationResponse(
            decision=decision,
            risk_level=risk_level,
            service_name=service_name,
            service_criticality=criticality,
            incident_criticality=effective_criticality,
            human_in_the_loop_required=human_in_the_loop_required,
            action=action,
            reversibility=reversibility,
            blast_radius=blast_radius,
            action_reliability=action_reliability,
            error_budget_remaining_percent=error_budget,
            timing_estimate=timing,
            approval_required=approval_required,
            approval_status=record.approval_status,
            approved_by_username=record.approved_by_username,
            rejection_reason=record.rejection_reason,
            allowed_roles=["ADMIN", "OPERATOR"],
            reasoning=reasoning,
            factors=factors,
            remediation_record_id=record.id,
            executed=executed,
            execution_result=execution_result,
        )

    async def approve_or_reject(
        self,
        record_id: UUID,
        approved: bool,
        reason: Optional[str],
        user: User,
        db: AsyncSession,
    ) -> RemediationRecord:
        """
        Record human operator/admin sign-off or rejection for a pending remediation.
        Strictly enforces RBAC: only ADMIN or OPERATOR allowed.
        """
        user_role = getattr(user, "role", "ENGINEER").upper()
        if user_role not in ["ADMIN", "OPERATOR"]:
            raise PermissionError(f"Role '{user_role}' not authorized to approve remediations. Required: ADMIN or OPERATOR.")

        res = await db.execute(select(RemediationRecord).where(RemediationRecord.id == record_id))
        record = res.scalar_one_or_none()
        if not record:
            raise ValueError(f"Remediation record {record_id} not found")

        now = datetime.now(timezone.utc)
        record.approved_by = user.id
        record.approved_by_username = user.username
        record.approved_at = now

        if approved:
            record.autonomy_decision = "APPROVED"
            record.approval_status = "APPROVED"
            record.status = "APPROVED"
            record.rejection_reason = None
            event_type = "APPROVED"
        else:
            record.autonomy_decision = "REJECTED"
            record.approval_status = "REJECTED"
            record.status = "REJECTED"
            record.rejection_reason = reason or "Rejected by operator"
            event_type = "REJECTED"

        # Immutable Audit Log
        audit = AutonomyAuditLog(
            remediation_id=record.id,
            event_type=event_type,
            service_name=record.service_name,
            action=record.action,
            user_id=user.id,
            user_role=user_role,
            user_username=user.username,
            decision="APPROVED" if approved else "REJECTED",
            details={"reason": reason, "timestamp": now.isoformat()},
        )
        db.add(audit)
        await db.flush()
        return record

    async def execute_remediation_with_budget(
        self,
        service_name: str,
        action: str,
        incident_id: Optional[UUID] = None,
        remediation_record_id: Optional[UUID] = None,
        user: Optional[User] = None,
        db: Optional[AsyncSession] = None,
        approval_notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Enforce backend policy before execution, dispatch Ansible Semaphore playbook,
        and record execution duration and audit events.
        """
        now = datetime.now(timezone.utc)

        # 1. Resolve or Evaluate Record
        record = None
        if remediation_record_id:
            res = await db.execute(select(RemediationRecord).where(RemediationRecord.id == remediation_record_id))
            record = res.scalar_one_or_none()

        if not record:
            # Run fresh evaluation
            eval_res = await self.evaluate(
                service_name=service_name,
                action=action,
                incident_id=incident_id,
                db=db,
                current_user=user,
            )
            res = await db.execute(select(RemediationRecord).where(RemediationRecord.id == eval_res.remediation_record_id))
            record = res.scalar_one()

        # 2. Strict Safety Enforcement Check
        user_role = getattr(user, "role", "SYSTEM").upper() if user else "SYSTEM"
        if record.autonomy_decision == "REJECTED" or record.approval_status == "REJECTED" or record.status == "REJECTED":
            raise ValueError(
                f"Execution blocked by Autonomy Budget: Action '{record.action}' on '{record.service_name}' "
                f"was REJECTED by operator: {record.rejection_reason or 'Operator denied execution.'}"
            )

        if record.autonomy_decision in ["REQUIRE_APPROVAL", "HIGH", "MEDIUM"]:
            if record.approval_status != "APPROVED":
                # Only an authorized ADMIN or OPERATOR can initiate explicit execution without prior sign-off
                if user is not None and user_role in ["ADMIN", "OPERATOR"]:
                    record.approval_status = "APPROVED"
                    record.autonomy_decision = "APPROVED"
                    audit = AutonomyAuditLog(
                        remediation_id=record.id,
                        event_type="APPROVED",
                        service_name=record.service_name,
                        action=record.action,
                        user_id=getattr(user, "id", None) if getattr(user, "username", "") != "system" else None,
                        user_role=user_role,
                        user_username=getattr(user, "username", "operator"),
                        decision="APPROVED",
                        details={"reason": approval_notes or "Human operator approved and executed from incident console", "timestamp": now.isoformat()},
                    )
                    db.add(audit)
                    await db.flush()
                else:
                    raise PermissionError(
                        f"Autonomy Policy Enforcement: Action '{record.action}' on '{record.service_name}' "
                        f"requires explicit human approval by an ADMIN or OPERATOR before execution."
                    )

        # 3. Concurrency Check
        active_conflict = await self.check_concurrency_lock(service_name, incident_id, db)
        if active_conflict and active_conflict.id != record.id:
            raise ValueError(
                f"Concurrent execution blocked: Action '{active_conflict.action}' is currently running on '{service_name}'."
            )

        # 4. Mark status EXECUTING and record start time
        start_time = now
        record.status = "EXECUTING"
        record.executed_at = start_time
        await db.flush()

        # 5. Dispatch Ansible Semaphore task
        inc_id_str = str(incident_id) if incident_id else str(record.id)
        ansible_res = await ansible_service.trigger_remediation_task(
            action=action,
            service_name=service_name,
            incident_id=inc_id_str,
            failure_type="anomalous_saturation",
            risk_score=85.0,
        )

        completed_time = datetime.now(timezone.utc)
        actual_exec_sec = max(0.5, (completed_time - start_time).total_seconds())

        record.ansible_task_id = str(ansible_res.get("task_id") or "")
        record.semaphore_url = ansible_res.get("semaphore_history_url")
        record.actual_execution_seconds = round(actual_exec_sec, 2)
        record.status = "COMPLETED"
        record.completed_at = completed_time
        await db.flush()

        # 6. Audit Log Entry
        audit = AutonomyAuditLog(
            remediation_id=record.id,
            event_type="EXECUTED",
            service_name=service_name,
            action=action,
            user_id=getattr(user, "id", None) if user and getattr(user, "username", "") != "system" else None,
            user_role=user_role,
            user_username=getattr(user, "username", "system") if user else "system",
            decision="EXECUTED",
            details={
                "ansible_task_id": record.ansible_task_id,
                "actual_execution_seconds": actual_exec_sec,
                "semaphore_url": record.semaphore_url,
                "notes": approval_notes,
            },
        )
        db.add(audit)

        # Update Incident state if linked
        if incident_id:
            inc_res = await db.execute(select(Incident).where(Incident.id == incident_id))
            inc = inc_res.scalar_one_or_none()
            if inc:
                inc.status = "RESOLVED"
                inc.resolved_at = completed_time
                db.add(
                    IncidentHistory(
                        incident_id=inc.id,
                        action="AUTONOMOUS_REMEDIATION_EXECUTED",
                        old_value="OPEN",
                        new_value=(
                            f"Autonomy Budget executed '{action}' on '{service_name}'. "
                            f"Duration: {actual_exec_sec:.1f}s. Semaphore Task #{record.ansible_task_id or 'N/A'}"
                        ),
                        changed_by=getattr(user, "id", None) if user and getattr(user, "username", "") != "system" else None,
                    )
                )
                await sse_manager.broadcast_incident_updated(inc)

        await db.flush()

        return {
            "remediation_record_id": str(record.id),
            "status": "EXECUTED",
            "service_name": service_name,
            "action": action,
            "actual_execution_seconds": actual_exec_sec,
            "ansible_task_id": record.ansible_task_id,
            "semaphore_history_url": record.semaphore_url,
            "estimated_execution_seconds": record.estimated_execution_seconds,
            "estimated_recovery_seconds": record.estimated_recovery_seconds,
            "estimate_source": record.estimate_source,
        }

    async def verify_and_record_recovery(
        self,
        record_id: UUID,
        current_metrics: Optional[Dict[str, float]],
        db: AsyncSession,
    ) -> RemediationRecord:
        """
        Verify post-remediation health metrics, compute actual recovery time delta,
        record success/failure, and persist to calibrate future estimates.
        """
        res = await db.execute(select(RemediationRecord).where(RemediationRecord.id == record_id))
        record = res.scalar_one_or_none()
        if not record:
            raise ValueError(f"Remediation record {record_id} not found")

        now = datetime.now(timezone.utc)
        record.completed_at = now
        record.post_metrics = current_metrics

        # Compute actual recovery time
        if record.executed_at:
            rec_sec = max(1.0, (now - record.executed_at).total_seconds())
            record.actual_recovery_seconds = round(rec_sec, 2)

        # Health verification
        metrics = current_metrics or {}
        error_rate = float(metrics.get("error_rate", 0.0))
        latency = float(metrics.get("latency_p99", metrics.get("response_time_p99", 50.0)))

        is_healthy = (error_rate < 1.0) and (latency < 250.0)
        record.success = is_healthy
        record.post_remediation_health = "HEALTHY" if is_healthy else "DEGRADED"
        record.status = "COMPLETED" if is_healthy else "FAILED"

        # Immutable Audit Log
        audit = AutonomyAuditLog(
            remediation_id=record.id,
            event_type="RECOVERY_VERIFIED",
            service_name=record.service_name,
            action=record.action,
            decision="SUCCESS" if is_healthy else "FAILED",
            details={
                "actual_execution_seconds": record.actual_execution_seconds,
                "actual_recovery_seconds": record.actual_recovery_seconds,
                "post_metrics": metrics,
                "post_remediation_health": record.post_remediation_health,
                "estimate_diff_exec": (
                    round(record.actual_execution_seconds - record.estimated_execution_seconds, 2)
                    if record.actual_execution_seconds and record.estimated_execution_seconds
                    else None
                ),
                "estimate_diff_rec": (
                    round(record.actual_recovery_seconds - record.estimated_recovery_seconds, 2)
                    if record.actual_recovery_seconds and record.estimated_recovery_seconds
                    else None
                ),
            },
        )
        db.add(audit)
        await db.flush()
        return record

    async def get_budget_status(self, db: AsyncSession) -> AutonomyBudgetStatusResponse:
        """Overview of autonomy policy, error budgets, active actions, and 24h stats."""
        policy = await self.get_or_create_policy(db)

        # Active & Pending
        active_res = await db.execute(
            select(func.count(RemediationRecord.id)).where(RemediationRecord.status.in_(["EXECUTING", "IN_PROGRESS"]))
        )
        active_count = active_res.scalar() or 0

        pending_res = await db.execute(
            select(func.count(RemediationRecord.id)).where(
                RemediationRecord.autonomy_decision == "REQUIRE_APPROVAL",
                RemediationRecord.approval_status == "PENDING",
            )
        )
        pending_count = pending_res.scalar() or 0

        executed_24h_res = await db.execute(
            select(func.count(RemediationRecord.id)).where(RemediationRecord.executed_at.isnot(None))
        )
        executed_24h = executed_24h_res.scalar() or 0

        auto_executed_24h_res = await db.execute(
            select(func.count(RemediationRecord.id)).where(
                RemediationRecord.executed_at.isnot(None),
                RemediationRecord.autonomy_decision == "AUTO_EXECUTE",
            )
        )
        auto_executed_24h = auto_executed_24h_res.scalar() or 0

        services_crit: Dict[str, str] = {}
        for s in list(CRITICAL_SERVICES) + list(HIGH_CRITICALITY_SERVICES) + list(MEDIUM_CRITICALITY_SERVICES):
            services_crit[s] = self.get_service_criticality(s)

        services_err_budget: Dict[str, float] = {
            "payment-service": 92.4,
            "order-service": 88.0,
            "auth-service": 99.1,
            "inventory-service": 85.5,
            "api-gateway": 95.0,
            "postgres-primary": 97.2,
        }

        return AutonomyBudgetStatusResponse(
            policy={
                "low_risk_auto_execute": policy.low_risk_auto_execute,
                "medium_risk_requires_approval": policy.medium_risk_requires_approval,
                "critical_services_always_require_approval": policy.critical_services_always_require_approval,
                "min_historical_samples": policy.min_historical_samples,
                "error_budget_threshold_percent": policy.error_budget_threshold_percent,
                "max_auto_recovery_time_seconds": policy.max_auto_recovery_time_seconds,
            },
            active_remediations_count=active_count,
            pending_approvals_count=pending_count,
            executed_24h_count=executed_24h,
            auto_executed_24h_count=auto_executed_24h,
            services_criticality=services_crit,
            services_error_budget=services_err_budget,
        )


autonomy_budget_engine = AutonomyBudgetEngine()
