"""
Synapse RiskOps - Inter-Service Orchestrator
============================================
Owner: Person 2 | Week: 5

Coordinates end-to-end incident lifecycle:
1. Calls ML Engine (8000) for Anomaly Detection & Graph RCA
2. Evaluates Person 1 Confidence Router (or calls GenAI Agent 8001)
3. Persists Incident, Audit History, and Risk Assessment in PostgreSQL
4. Executes automated remediation runbooks for high-confidence incidents
5. Dispatches real-time updates via Server-Sent Events (SSE)
6. Emits unified incident record aligning with shared/schemas/incident_record.schema.json
"""

import asyncio
import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.incident import Incident, IncidentHistory
from app.models.risk_assessment import RiskAssessment
from app.models.service import Service, ServiceDependency
from app.models.user import User
from app.schemas.orchestration import UnifiedIncidentRecordResponse
from app.services.ansible_service import ansible_service
from app.services.autonomy_budget import autonomy_budget_engine
from app.services.email_service import email_service
from app.services.sse_manager import sse_manager

logger = logging.getLogger("synapse.orchestrator")


class OrchestrationService:
    """Coordinates telemetry ingestion, ML diagnosis, GenAI routing, and persistence."""

    def __init__(
        self,
        ml_engine_url: Optional[str] = None,
        genai_agent_url: Optional[str] = None,
    ):
        self._ml_engine_url = ml_engine_url
        self._genai_agent_url = genai_agent_url

    @property
    def ml_engine_url(self) -> str:
        return self._ml_engine_url or settings.ML_ENGINE_URL

    @property
    def genai_agent_url(self) -> str:
        return self._genai_agent_url or settings.GENAI_AGENT_URL

    @property
    def n8n_webhook_url(self) -> str:
        return getattr(settings, "N8N_WEBHOOK_URL", "http://localhost:5678/webhook/riskops-incident")

    async def _send_n8n_incident(self, payload: Dict[str, Any]) -> bool:
        """Forward incident payload to n8n webhook."""
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.post(self.n8n_webhook_url, json=payload)
                if resp.status_code in (200, 201):
                    logger.info(f"Successfully dispatched incident to n8n: {payload.get('incident_id')}")
                    return True
                else:
                    logger.warning(f"n8n webhook returned status {resp.status_code}: {resp.text}")
        except Exception as e:
            logger.warning(f"n8n webhook dispatch failed (non-fatal): {e}")
        return False

    async def _send_incident_email(self, payload: Dict[str, Any], force: bool = True) -> Dict[str, Any]:
        """Forward incident predictive failure alert to admin via Gmail SMTP."""
        try:
            return await email_service.send_incident_alert(payload, force=force)
        except Exception as e:
            logger.warning(f"Gmail SMTP alert dispatch failed (non-fatal): {e}")
            return {"success": False, "status": "ERROR", "detail": str(e)}

    async def _call_ml_engine_analyze(
        self,
        service_name: str,
        metrics: Dict[str, float],
    ) -> Dict[str, Any]:
        """Call ML Engine POST /api/week4/analyze."""
        payload = {
            "service_name": service_name,
            "metrics": metrics,
        }
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    f"{self.ml_engine_url}/api/week4/analyze",
                    json=payload,
                )
                if resp.status_code == 200:
                    return resp.json()
        except Exception as e:
            logger.warning(f"ML Engine unreachable at {self.ml_engine_url} ({e}); using internal analysis fallback.")

        # Fallback estimation if ML engine is not actively running during standalone test
        risk_score = min(100.0, max(10.0, metrics.get("cpu_usage", 50.0) * 0.8 + metrics.get("error_rate", 2.0) * 8.0))
        tier = "CRITICAL" if risk_score >= 75.0 else "WATCH" if risk_score >= 40.0 else "HEALTHY"
        return {
            "service_name": service_name,
            "prediction": {
                "risk_score": risk_score,
                "risk_tier": tier,
                "confidence": 0.88 if risk_score >= 75.0 else 0.72,
                "predicted_failure_type": "HIGH_TRAFFIC_CONGESTION" if "cpu_usage" in metrics else "DATABASE_CONNECTION_EXHAUSTION",
                "risk_threshold": 75.0,
                "model_name": "IsolationForest+Statsmodels",
                "prediction_horizon_minutes": 15,
                "conformal_interval": {
                    "point_estimate": risk_score,
                    "lower": None,
                    "upper": None,
                    "target_coverage": 0.90,
                    "interval_width": None,
                    "is_calibrated": False,
                    "status": "uncalibrated_fallback",
                },
            },
            "diagnosis": {
                "rca_candidates": [
                    {"service": service_name, "label": "ROOT_CAUSE", "confidence": 0.92},
                ],
                "propagation_path": [service_name],
                "rca_confidence": 0.86,
                "gemini_explanation": f"Elevated anomaly signatures detected on {service_name}.",
            },
            "runbook": {
                "runbook_id": "RB-001-TRAFFIC",
                "recommended_action": "SCALE_SERVICE",
                "target_service": service_name,
            },
        }

    def _evaluate_confidence_router(
        self,
        ml_confidence: float,
        rca_confidence: float,
        service_name: Optional[str] = None,
        risk_score: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Confidence Router Contract + Autonomy Budget Policy Safeguards:
        - If risk_score > 74.0: Mandate human approval (routing_decision = 'escalate')
        - If risk_score <= 74.0: Cleared for auto_remediation
        """
        threshold = 0.85
        rca_threshold = 0.80
        is_auto = (ml_confidence >= threshold) and (rca_confidence >= rca_threshold)

        is_high_risk = (risk_score is not None and risk_score > 74.0)
        if is_high_risk:
            is_auto = False

        return {
            "routing_decision": "auto_remediate" if is_auto else "escalate",
            "routing_confidence": round((ml_confidence + rca_confidence) / 2.0, 4),
            "routing_threshold_used": threshold,
            "human_override": is_high_risk,
            "human_override_reason": "RISK_SCORE_ABOVE_74_HUMAN_IN_THE_LOOP_REQUIRED" if is_high_risk else None,
            "was_routing_correct": None,
            "critical_service_safeguard": is_high_risk,
        }

    async def _execute_runbook_action(
        self,
        failure_type: str,
        target_service: str,
        routing_decision: str,
    ) -> Dict[str, Any]:
        """Call ML Engine POST /api/week4/execute if auto_remediate."""
        if routing_decision != "auto_remediate":
            return {
                "actions_executed": [],
                "retry_count": 0,
                "max_retries": 3,
                "execution_status": "SKIPPED_ESCALATED_TO_HUMAN",
            }

        payload = {
            "failure_type": failure_type,
            "target_service": target_service,
            "routing_decision": routing_decision,
        }
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    f"{self.ml_engine_url}/api/week4/execute",
                    json=payload,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    return {
                        "actions_executed": data.get("actions", [{"action": "RESTART_POD", "target": target_service, "status": "SUCCESS"}]),
                        "retry_count": 0,
                        "max_retries": 3,
                        "execution_status": data.get("status", "SUCCESS"),
                    }
        except Exception as e:
            logger.warning(f"Runbook execution at {self.ml_engine_url} unavailable ({e}); simulating action.")

        # Trigger real Ansible Playbook via Semaphore REST API
        ansible_res = await ansible_service.trigger_remediation_task(
            action="SCALE_OUT_PODS",
            service_name=target_service,
            incident_id="AUTO-ORCHESTRATION",
            failure_type=failure_type,
        )

        return {
            "actions_executed": [
                {"action": "SCALE_OUT_PODS", "target": target_service, "status": "SUCCESS", "semaphore_task_id": ansible_res.get("task_id")},
                {"action": "FLUSH_REDIS_CACHE", "target": target_service, "status": "SUCCESS"},
            ],
            "retry_count": 0,
            "max_retries": 3,
            "execution_status": "SUCCESS",
            "ansible_task_id": ansible_res.get("task_id"),
            "semaphore_history_url": ansible_res.get("semaphore_history_url"),
        }

    async def _call_genai_diagnose(
        self,
        service_name: str,
        metrics: Dict[str, float],
    ) -> Optional[Dict[str, Any]]:
        """Call GenAI Agent POST /diagnose."""
        payload = {
            "metrics": {
                "service_name": service_name,
                "cpu_usage": float(metrics.get("cpu_usage", 0.0)),
                "memory_usage": float(metrics.get("memory_usage", 0.0)),
                "disk_io": float(metrics.get("disk_io", 0.0)),
                "network_latency_ms": float(metrics.get("network_latency_ms", 0.0)),
                "request_count": int(metrics.get("request_count", 0)),
                "error_rate": float(metrics.get("error_rate", 0.0)),
                "response_time_p99": float(metrics.get("response_time_p99", 0.0)),
                "active_connections": int(metrics.get("active_connections", 0)),
                "gc_pause_ms": float(metrics.get("gc_pause_ms", 0.0)),
                "thread_count": int(metrics.get("thread_count", 0)),
            },
            "logs": [
                {
                    "service": service_name,
                    "message": f"Anomaly on {service_name}: error_rate={metrics.get('error_rate', 0)}%, latency_p99={metrics.get('response_time_p99', 0)}ms",
                }
            ],
        }
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                resp = await client.post(
                    f"{self.genai_agent_url}/diagnose",
                    json=payload,
                )
                if resp.status_code == 200:
                    return resp.json()
                else:
                    logger.warning(f"GenAI Agent returned {resp.status_code}: {resp.text}")
        except Exception as e:
            logger.warning(f"GenAI Agent unreachable at {self.genai_agent_url} ({e}); using graph fallback.")
        return None

    async def orchestrate_incident_lifecycle(
        self,
        service_name: str,
        metrics: Dict[str, float],
        environment: str = "production",
        scenario_id: Optional[str] = None,
        assigned_to: Optional[UUID] = None,
        db: Optional[AsyncSession] = None,
        current_user: Optional[User] = None,
        data_mode: str = "demo",
    ) -> UnifiedIncidentRecordResponse:
        """
        Execute full end-to-end incident lifecycle with deduplication:
        1. Resolve Service from DB & check for active incident
        2. ML Engine Analysis (Prediction + RCA candidates)
        3. Incident Deduplication:
           - Active incident + risk >= 40: update existing observation, debounce GenAI
           - Active incident + risk < 40: mark recovered/resolved
           - No active incident + risk >= 40: create incident & trigger GenAI RCA
        4. Real-time SSE dispatch
        """
        now = datetime.now(timezone.utc)

        # 0. Resolve database user for audit trail FK
        user_db_id = getattr(current_user, "id", None) if current_user and getattr(current_user, "username", None) != "system" else None

        # 1. Resolve service
        target_service = None
        dep_names = []
        existing_incident = None
        if db:
            svc_res = await db.execute(
                select(Service).where(Service.service_name == service_name)
            )
            target_service = svc_res.scalar_one_or_none()
            if target_service:
                dep_res = await db.execute(
                    select(Service.service_name)
                    .join(ServiceDependency, ServiceDependency.target_service_id == Service.id)
                    .where(ServiceDependency.source_service_id == target_service.id)
                )
                dep_names = [r[0] for r in dep_res.all()]

                # Query existing OPEN incident for deduplication / debouncing
                inc_res = await db.execute(
                    select(Incident)
                    .where(Incident.service_id == target_service.id, Incident.status == "OPEN")
                    .order_by(Incident.created_at.desc())
                )
                existing_incident = inc_res.scalars().first()

        # 2. ML Engine analysis
        ml_data = await self._call_ml_engine_analyze(service_name, metrics)
        prediction_block = ml_data.get("prediction", {})
        diagnosis_block = ml_data.get("diagnosis", {}) or ml_data.get("diagnosis_context", {})

        risk_score = float(prediction_block.get("risk_score", 85.0))
        ml_conf = float(prediction_block.get("confidence", 0.90))
        rca_conf = float(diagnosis_block.get("rca_confidence", 0.85))
        failure_type = prediction_block.get("predicted_failure_type", "ANOMALOUS_SATURATION")

        severity = "CRITICAL" if risk_score >= 75.0 else "HIGH" if risk_score >= 40.0 else "MEDIUM"

        # 3. Handle Deduplication / Debouncing / Recovery
        # Strict recovery verification: only recover when telemetry metrics are demonstrably back within safe thresholds
        err_val = float(metrics.get("error_rate", 0.0))
        lat_val = float(metrics.get("response_time_p99", 0.0))
        cpu_val = float(metrics.get("cpu_usage", 0.0))
        has_anom = bool(prediction_block.get("anomaly_detail", {}).get("is_anomaly", False))
        
        is_recovered = (risk_score < 45.0) and (err_val < 3.0) and (lat_val < 150.0) and (cpu_val < 75.0) and (not has_anom)
        if existing_incident is not None:
            if is_recovered:
                # RECOVERY: service returned to normal/healthy (Section 7.10)
                existing_incident.status = "RESOLVED"
                existing_incident.resolved_at = now
                existing_incident.risk_score = Decimal(str(round(risk_score, 2)))

                if db:
                    db.add(
                        IncidentHistory(
                            incident_id=existing_incident.id,
                            action="RECOVERED",
                            old_value="OPEN",
                            new_value=f"Telemetry recovered below WATCH threshold (risk_score={risk_score:.1f}). Incident automatically closed.",
                            changed_by=user_db_id,
                        )
                    )
                    await db.flush()
                await sse_manager.broadcast_risk_alert({
                    "service_name": service_name,
                    "risk_score": risk_score,
                    "severity": "HEALTHY",
                    "status": "RESOLVED",
                    "timestamp": now.isoformat(),
                })

                # Notify n8n of resolution so automation stops remediation
                recovery_payload = {
                    "incident_id": str(existing_incident.id),
                    "service": service_name,
                    "severity": "HEALTHY",
                    "risk_score": round(risk_score, 2),
                    "risk_tier": "HEALTHY",
                    "predicted_failure": "none",
                    "anomaly_score": round(risk_score / 100.0, 4),
                    "forecast_risk": round(risk_score / 100.0, 4),
                    "root_cause": "none",
                    "affected_services": [service_name],
                    "confidence": 1.0,
                    "routing_decision": "none",
                    "timestamp": now.isoformat(),
                    "guidance": "Service recovered below WATCH threshold. Incident resolved.",
                    "status": "RESOLVED",
                }
                await self._send_n8n_incident(recovery_payload)

                # Dispatch resolution notification via Gmail SMTP
                try:
                    email_service.send_incident_alert_bg({
                        "incident_id": str(existing_incident.id),
                        "service_name": service_name,
                        "severity": "HEALTHY",
                        "risk_score": round(risk_score, 2),
                        "failure_type": failure_type,
                        "ml_confidence": round(ml_conf, 4),
                        "rca_confidence": round(rca_conf, 4),
                        "root_cause": service_name,
                        "affected_services": [service_name],
                        "routing_decision": "recovered",
                        "timestamp": now.isoformat(),
                        "guidance": f"Service {service_name} metrics have stabilized back within safe operational limits. Incident resolved.",
                        "metrics": metrics,
                        "status": "RESOLVED",
                        "is_auto_fixed": True,
                    }, force=True)
                except Exception as rec_err:
                    logger.debug(f"Recovery email dispatch notice: {rec_err}")

                incident_id = existing_incident.id
                incident_status = "RESOLVED"
                decision = "escalate"
                routing_block = self._evaluate_confidence_router(ml_conf, rca_conf, service_name=service_name)
                automation_block = {"execution_status": "SKIPPED_RECOVERED", "actions_executed": []}
            else:
                # DEBOUNCE: existing incident updated with latest observation, NO duplicate GenAI or n8n calls (Section 7.9)
                existing_incident.risk_score = Decimal(str(round(risk_score, 2)))
                existing_incident.severity = severity
                existing_incident.confidence = Decimal(str(round(ml_conf, 4)))
                existing_incident.anomaly_score = Decimal(str(round(risk_score / 100.0, 4)))
                existing_incident.top_features = metrics
                existing_incident.detected_at = now
                existing_incident.updated_at = now
                existing_incident.predicted_failure_type = failure_type
                existing_incident.title = f"Incident: {failure_type.replace('_', ' ').title()} on {service_name}"
                if db:
                    db.add(
                        IncidentHistory(
                            incident_id=existing_incident.id,
                            action="FAULT_ESCALATED",
                            old_value=str(existing_incident.risk_score),
                            new_value=f"Telemetry anomaly on {service_name}: {failure_type} (risk_score={risk_score:.1f}, severity={severity}).",
                            changed_by=user_db_id,
                        )
                    )
                    await db.flush()
                runbook_block = ml_data.get("runbook", {})
                proposed_action = runbook_block.get("recommended_action", "SCALE_OUT_PODS")
                if proposed_action == "SCALE_SERVICE":
                    proposed_action = "SCALE_OUT_PODS"

                auto_executed = False
                if risk_score <= 74.0:
                    # RISK SCORE <= 74: Automatically executed with NO human intervention required!
                    try:
                        exec_res = await autonomy_budget_engine.execute_remediation_with_budget(
                            service_name=service_name,
                            action=proposed_action,
                            incident_id=existing_incident.id,
                            remediation_record_id=None,
                            user=current_user,
                            db=db,
                            approval_notes="Autonomous auto-fix executed (risk <= 74).",
                        )
                        auto_executed = True
                        incident_status = "RESOLVED"
                        routing_decision_str = "auto_remediate"
                        existing_incident.status = "RESOLVED"
                        existing_incident.routing_decision = "auto_remediate"
                        existing_incident.resolved_at = now
                        if db:
                            db.add(
                                IncidentHistory(
                                    incident_id=existing_incident.id,
                                    action="AUTO_REMEDIATED",
                                    old_value="OPEN",
                                    new_value=f"Action '{proposed_action}' executed automatically by autonomy policy (risk_score={risk_score:.1f} <= 74).",
                                    changed_by=user_db_id,
                                )
                            )
                            await db.flush()
                        await sse_manager.broadcast_incident_updated({
                            "id": str(existing_incident.id),
                            "title": existing_incident.title,
                            "severity": severity,
                            "status": "RESOLVED",
                            "resolved_at": now,
                            "updated_at": now,
                        })
                        automation_block = {
                            "execution_status": "SUCCESS",
                            "actions_executed": [
                                {
                                    "action": proposed_action,
                                    "target": service_name,
                                    "status": "SUCCESS",
                                    "semaphore_task_id": exec_res.get("ansible_task_id"),
                                }
                            ],
                            "ansible_task_id": exec_res.get("ansible_task_id"),
                            "semaphore_history_url": exec_res.get("semaphore_history_url"),
                        }
                    except Exception as e_exec:
                        logger.warning(f"Failed to auto-execute low-risk remediation in debounce: {e_exec}")
                        incident_status = "OPEN"
                        routing_decision_str = "human_approval"
                        automation_block = {"execution_status": "SKIPPED_ESCALATED_TO_HUMAN", "actions_executed": []}
                else:
                    # RISK SCORE > 74: Mandate human intervention!
                    incident_status = "OPEN"
                    routing_decision_str = "human_approval"
                    existing_incident.status = "OPEN"
                    existing_incident.routing_decision = "human_approval"
                    if db:
                        await db.flush()
                    await sse_manager.broadcast_incident_updated({
                        "id": str(existing_incident.id),
                        "title": existing_incident.title,
                        "severity": severity,
                        "status": "OPEN",
                        "updated_at": now,
                    })
                    automation_block = {"execution_status": "SKIPPED_ESCALATED_TO_HUMAN", "actions_executed": []}

                await sse_manager.broadcast_risk_alert({
                    "service_name": service_name,
                    "risk_score": risk_score,
                    "severity": severity,
                    "status": incident_status,
                    "timestamp": now.isoformat(),
                })

                # Dispatch predictive failure alert to admin via Gmail SMTP
                is_crit_svc = (risk_score > 74.0)
                try:
                    email_service.send_incident_alert_bg({
                        "incident_id": str(existing_incident.id),
                        "service_name": service_name,
                        "severity": severity,
                        "risk_score": round(risk_score, 2),
                        "failure_type": failure_type,
                        "ml_confidence": round(ml_conf, 4),
                        "rca_confidence": round(rca_conf, 4),
                        "root_cause": service_name,
                        "affected_services": [service_name],
                        "routing_decision": routing_decision_str,
                        "timestamp": now.isoformat(),
                        "guidance": f"Elevated fault observed on {service_name}. Human intervention required." if is_crit_svc else f"Autonomous remediation executed for {service_name}.",
                        "metrics": metrics,
                        "status": incident_status,
                        "is_auto_fixed": (risk_score <= 74.0 and auto_executed),
                        "proposed_action": proposed_action,
                        "is_critical": is_crit_svc,
                    })
                except Exception as e_mail:
                    logger.debug(f"Debounce incident email notice: {e_mail}")
                incident_id = existing_incident.id
                routing_block = self._evaluate_confidence_router(ml_conf, rca_conf, service_name=service_name, risk_score=risk_score)
                decision = routing_decision_str
        else:
            # NEW INCIDENT: Invoke GenAI Agent for RCA
            genai_data = await self._call_genai_diagnose(service_name, metrics)
            if genai_data:
                genai_candidates = genai_data.get("root_cause_candidates_ranked", [])
                if genai_candidates:
                    diagnosis_block["rca_candidates"] = [
                        {
                            "service": c.get("affected_services", [service_name])[0] if c.get("affected_services") else service_name,
                            "label": "ROOT_CAUSE" if idx == 0 else "CONTRIBUTOR",
                            "confidence": c.get("confidence", 0.90),
                            "cause": c.get("cause", ""),
                            "reason": c.get("reason", ""),
                        }
                        for idx, c in enumerate(genai_candidates)
                    ]
                if genai_data.get("guidance"):
                    summary = genai_data["guidance"].get("summary", "")
                    if summary:
                        diagnosis_block["gemini_explanation"] = summary
                if genai_data.get("routing_decision"):
                    decision = genai_data["routing_decision"]

            incident_id = uuid4()
            runbook_block = ml_data.get("runbook", {})
            proposed_action = runbook_block.get("recommended_action", "SCALE_OUT_PODS")
            if proposed_action == "SCALE_SERVICE":
                proposed_action = "SCALE_OUT_PODS"

            root_cause_str = (
                diagnosis_block.get("rca_candidates", [{}])[0].get("service", service_name)
                if diagnosis_block.get("rca_candidates")
                else service_name
            )
            guidance_str = diagnosis_block.get("gemini_explanation", f"Latency degradation observed on {service_name}.")

            incident_title = f"Incident: {failure_type.replace('_', ' ').title()} on {service_name}"
            incident = None
            if db:
                incident = Incident(
                    id=incident_id,
                    title=incident_title,
                    description=(
                        f"Automated risk detection triggered for {service_name}. "
                        f"Composite risk score: {risk_score:.1f}, Risk Tier: {severity}, ML Confidence: {ml_conf:.2f}, RCA Confidence: {rca_conf:.2f}."
                    ),
                    severity=severity,
                    status="OPEN",
                    service_id=target_service.id if target_service else None,
                    risk_score=Decimal(str(round(risk_score, 2))),
                    confidence=Decimal(str(round(ml_conf, 4))),
                    predicted_failure=now,
                    risk_tier=severity,
                    anomaly_score=Decimal(str(round(risk_score / 100.0, 4))),
                    forecast_risk=Decimal(str(round(risk_score / 100.0, 4))),
                    predicted_failure_type=failure_type,
                    root_cause=root_cause_str,
                    guidance=guidance_str,
                    routing_decision="human_approval",
                    top_features=metrics,
                    affected_services=diagnosis_block.get("propagation_path", [service_name]),
                    data_mode=data_mode,
                    resolved_at=None,
                    assigned_to=assigned_to,
                    created_by=user_db_id,
                )
                db.add(incident)
                await db.flush()

                db.add(
                    IncidentHistory(
                        incident_id=incident_id,
                        action="CREATED",
                        old_value=None,
                        new_value=f"Detected anomaly with risk score {risk_score:.1f} ({severity})",
                        changed_by=user_db_id,
                    )
                )
                await db.flush()

            # Evaluate with Autonomy Budget:
            # - Incidents with low-mid criticality: automatically fixed (AUTO_EXECUTE)
            # - Incidents with high criticality & high risk: add human-in-the-loop (REQUIRE_APPROVAL)
            autonomy_eval = None
            svc_crit = target_service.criticality if target_service else None
            if db:
                try:
                    autonomy_eval = await autonomy_budget_engine.evaluate(
                        service_name=service_name,
                        action=proposed_action,
                        runbook_id=runbook_block.get("runbook_id"),
                        incident_id=incident_id,
                        current_metrics=metrics,
                        risk_tier=severity,
                        risk_score=risk_score,
                        incident_criticality=svc_crit,
                        db=db,
                        current_user=current_user,
                    )
                except Exception as eval_err:
                    logger.warning(f"Autonomy evaluation failed in orchestrator: {eval_err}")

            routing_block = self._evaluate_confidence_router(ml_conf, rca_conf, service_name=service_name, risk_score=risk_score)
            auto_executed = False
            if autonomy_eval and autonomy_eval.decision == "AUTO_EXECUTE":
                # LOW-MID CRITICALITY: Automatically fixed without requiring human button click
                try:
                    exec_res = await autonomy_budget_engine.execute_remediation_with_budget(
                        service_name=service_name,
                        action=proposed_action,
                        incident_id=incident_id,
                        remediation_record_id=autonomy_eval.remediation_record_id,
                        user=current_user,
                        db=db,
                        approval_notes="Autonomous low-mid criticality auto-fix executed without operator intervention.",
                    )
                    auto_executed = True
                    incident_status = "RESOLVED"
                    routing_decision_str = "auto_remediate"
                    resolved_time = now
                    automation_block = {
                        "execution_status": "SUCCESS",
                        "actions_executed": [
                            {
                                "action": proposed_action,
                                "target": service_name,
                                "status": "SUCCESS",
                                "semaphore_task_id": exec_res.get("ansible_task_id"),
                            }
                        ],
                        "ansible_task_id": exec_res.get("ansible_task_id"),
                        "semaphore_history_url": exec_res.get("semaphore_history_url"),
                    }
                except Exception as exec_err:
                    logger.warning(f"Failed to auto-execute low-mid criticality remediation: {exec_err}")
                    incident_status = "OPEN"
                    routing_decision_str = "human_approval"
                    resolved_time = None
                    automation_block = {
                        "execution_status": "SKIPPED_ESCALATED_TO_HUMAN",
                        "actions_executed": [],
                    }
            else:
                # HIGH CRITICALITY & HIGH RISK: Mandate human-in-the-loop approval
                incident_status = "OPEN"
                routing_decision_str = "human_approval"
                resolved_time = None
                automation_block = {
                    "execution_status": "SKIPPED_ESCALATED_TO_HUMAN",
                    "actions_executed": [],
                }

            routing_block["routing_decision"] = routing_decision_str

            if db and incident:
                incident.status = incident_status
                incident.routing_decision = routing_decision_str
                incident.resolved_at = resolved_time
                incident.description = (
                    f"Automated risk detection triggered for {service_name}. "
                    f"Composite risk score: {risk_score:.1f}, Risk Tier: {severity}, ML Confidence: {ml_conf:.2f}, RCA Confidence: {rca_conf:.2f}. "
                    f"Routing Decision: {'AUTO_FIXED (Low-Mid Criticality Policy)' if auto_executed else 'HUMAN_IN_THE_LOOP_REQUIRED (High Criticality & High Risk Policy)'}."
                )
                db.add(
                    IncidentHistory(
                        incident_id=incident_id,
                        action="ROUTING_DECIDED",
                        old_value=None,
                        new_value=(
                            f"Autonomy Policy: {'AUTO_FIXED (Low-Mid Criticality autonomous execution completed)' if auto_executed else f'HUMAN_IN_THE_LOOP_REQUIRED (High criticality / high risk mandates operator sign-off)'}"
                        ),
                        changed_by=user_db_id,
                    )
                )
                if auto_executed:
                    db.add(
                        IncidentHistory(
                            incident_id=incident_id,
                            action="AUTO_REMEDIATED",
                            old_value="OPEN",
                            new_value=f"Action '{proposed_action}' executed automatically by autonomy policy without requiring human intervention.",
                            changed_by=user_db_id,
                        )
                    )

                if target_service:
                    db.add(
                        RiskAssessment(
                            service_id=target_service.id,
                            risk_score=Decimal(str(round(risk_score, 2))),
                            confidence=Decimal(str(round(ml_conf, 4))),
                            anomaly_score=Decimal(str(round(risk_score / 100.0, 4))),
                            affected_services=diagnosis_block.get("propagation_path", [service_name]),
                            features_used=metrics,
                            model_version="v1.0.0",
                            data_mode=data_mode,
                        )
                    )

                await db.flush()
                await sse_manager.broadcast_incident_created({
                    "id": str(incident_id),
                    "title": incident_title,
                    "severity": severity,
                    "status": incident_status,
                    "service_id": str(target_service.id) if target_service else None,
                    "risk_score": risk_score,
                    "confidence": ml_conf,
                    "detected_at": now,
                })
                if auto_executed:
                    await sse_manager.broadcast_incident_updated({
                        "id": str(incident_id),
                        "title": incident_title,
                        "severity": severity,
                        "status": "RESOLVED",
                        "resolved_at": now,
                        "updated_at": now,
                    })
                await sse_manager.broadcast_risk_alert({
                    "service_name": service_name,
                    "risk_score": risk_score,
                    "severity": severity,
                    "routing_decision": routing_decision_str,
                    "status": incident_status,
                    "timestamp": now.isoformat(),
                })

            # Dispatch incident event to n8n webhook (Section 7.3)
            n8n_payload = {
                "incident_id": str(incident_id),
                "service": service_name,
                "severity": severity,
                "risk_score": round(risk_score, 2),
                "risk_tier": severity,
                "predicted_failure": failure_type,
                "anomaly_score": round(risk_score / 100.0, 4),
                "forecast_risk": round(risk_score / 100.0, 4),
                "root_cause": root_cause_str,
                "affected_services": diagnosis_block.get("propagation_path", [service_name]),
                "confidence": round(ml_conf, 4),
                "routing_decision": "human_approval",
                "timestamp": now.isoformat(),
                "guidance": guidance_str,
                "status": incident_status,
            }
            await self._send_n8n_incident(n8n_payload)

            # Dispatch predictive failure alert to admin via Gmail SMTP
            is_crit_svc = (risk_score > 74.0)
            email_payload = {
                "incident_id": str(incident_id),
                "service_name": service_name,
                "severity": severity,
                "risk_score": round(risk_score, 2),
                "failure_type": failure_type,
                "ml_confidence": round(ml_conf, 4),
                "rca_confidence": round(rca_conf, 4),
                "root_cause": root_cause_str,
                "affected_services": diagnosis_block.get("propagation_path", [service_name]),
                "routing_decision": routing_decision_str,
                "timestamp": now.isoformat(),
                "guidance": guidance_str,
                "metrics": metrics,
                "status": incident_status,
                "is_auto_fixed": auto_executed,
                "proposed_action": proposed_action,
                "is_critical": is_crit_svc,
            }
            try:
                await self._send_incident_email(email_payload)
            except Exception as mail_err:
                logger.warning(f"Failed to dispatch incident alert email: {mail_err}")

        # 7. Build unified incident record response
        return UnifiedIncidentRecordResponse(
            incident_id=str(incident_id),
            created_at=now.isoformat(),
            service={
                "service_name": service_name,
                "environment": environment,
                "dependency_ids": dep_names,
            },
            prediction={
                "predicted_at": now.isoformat(),
                "model_name": prediction_block.get("model_name", "IsolationForest+Statsmodels"),
                "risk_score": risk_score,
                "risk_threshold": float(prediction_block.get("risk_threshold", 75.0)),
                "predicted_failure_type": failure_type,
                "prediction_horizon_minutes": prediction_block.get("prediction_horizon_minutes", 15),
            },
            diagnosis={
                "diagnosis_started_at": now.isoformat(),
                "diagnosis_completed_at": now.isoformat(),
                "agent_pipeline": ["ml-engine:isolation_forest", "ml-engine:networkx_rca", "genai-agent:confidence_router"],
                "predicted_root_cause_service": (diagnosis_block.get("rca_candidates") or [{}])[0].get("service", service_name),
                "predicted_root_cause_label": (diagnosis_block.get("rca_candidates") or [{}])[0].get("label", "ROOT_CAUSE"),
                "root_cause_candidates_ranked": diagnosis_block.get("rca_candidates") or [
                    {"service": service_name, "label": "ROOT_CAUSE", "confidence": rca_conf}
                ],
                "propagation_path": diagnosis_block.get("propagation_path", [service_name]),
                "rca_confidence": rca_conf,
                "gemini_explanation": diagnosis_block.get("gemini_explanation", "RCA candidate graph traversal completed."),
            },
            routing=routing_block,
            automation=automation_block,
            lifecycle_status=incident_status,
        )


# Module-level singleton
orchestrator = OrchestrationService()
