"""
Synapse RiskOps - In-Memory Demo Store & Standalone Fallback
============================================================
Provides rich, realistic telemetry, services, topology, incidents,
and risk assessments when PostgreSQL is offline or unseeded in local dev.
Mirrors the exact dataset defined in docker/postgres/init.sql.
"""

import uuid
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import List, Optional, Dict, Any

# Fixed UUIDs for consistency across restarts
SERVICE_IDS = {
    "api-gateway": uuid.UUID("10000000-0000-0000-0000-000000000001"),
    "auth-service": uuid.UUID("10000000-0000-0000-0000-000000000002"),
    "user-service": uuid.UUID("10000000-0000-0000-0000-000000000003"),
    "order-service": uuid.UUID("10000000-0000-0000-0000-000000000004"),
    "payment-service": uuid.UUID("10000000-0000-0000-0000-000000000005"),
    "inventory-service": uuid.UUID("10000000-0000-0000-0000-000000000006"),
    "notification-svc": uuid.UUID("10000000-0000-0000-0000-000000000007"),
    "search-service": uuid.UUID("10000000-0000-0000-0000-000000000008"),
    "cache-layer": uuid.UUID("10000000-0000-0000-0000-000000000009"),
    "message-queue": uuid.UUID("10000000-0000-0000-0000-000000000010"),
    "postgres-primary": uuid.UUID("10000000-0000-0000-0000-000000000011"),
    "postgres-replica": uuid.UUID("10000000-0000-0000-0000-000000000012"),
}

# 12 Core Microservices (matching init.sql)
RAW_SERVICES = [
    {
        "id": SERVICE_IDS["api-gateway"],
        "service_name": "api-gateway",
        "service_type": "GATEWAY",
        "description": "Main API gateway and reverse proxy load balancer",
        "owner": "Platform Team",
        "criticality": "CRITICAL",
        "is_active": True,
        "created_at": datetime.now(timezone.utc) - timedelta(days=30),
        "updated_at": datetime.now(timezone.utc),
    },
    {
        "id": SERVICE_IDS["auth-service"],
        "service_name": "auth-service",
        "service_type": "MICROSERVICE",
        "description": "Authentication, JWT tokens, and RBAC authorization",
        "owner": "Security Team",
        "criticality": "CRITICAL",
        "is_active": True,
        "created_at": datetime.now(timezone.utc) - timedelta(days=30),
        "updated_at": datetime.now(timezone.utc),
    },
    {
        "id": SERVICE_IDS["user-service"],
        "service_name": "user-service",
        "service_type": "MICROSERVICE",
        "description": "User profile management and account metadata",
        "owner": "Backend Team",
        "criticality": "HIGH",
        "is_active": True,
        "created_at": datetime.now(timezone.utc) - timedelta(days=30),
        "updated_at": datetime.now(timezone.utc),
    },
    {
        "id": SERVICE_IDS["order-service"],
        "service_name": "order-service",
        "service_type": "MICROSERVICE",
        "description": "Order processing, checkout workflow, and fulfillment",
        "owner": "Commerce Team",
        "criticality": "HIGH",
        "is_active": True,
        "created_at": datetime.now(timezone.utc) - timedelta(days=30),
        "updated_at": datetime.now(timezone.utc),
    },
    {
        "id": SERVICE_IDS["payment-service"],
        "service_name": "payment-service",
        "service_type": "MICROSERVICE",
        "description": "Payment gateway processing, cards, and settlement",
        "owner": "Payments Team",
        "criticality": "CRITICAL",
        "is_active": True,
        "created_at": datetime.now(timezone.utc) - timedelta(days=30),
        "updated_at": datetime.now(timezone.utc),
    },
    {
        "id": SERVICE_IDS["inventory-service"],
        "service_name": "inventory-service",
        "service_type": "MICROSERVICE",
        "description": "Stock inventory tracking and warehouse allocations",
        "owner": "Supply Team",
        "criticality": "HIGH",
        "is_active": True,
        "created_at": datetime.now(timezone.utc) - timedelta(days=30),
        "updated_at": datetime.now(timezone.utc),
    },
    {
        "id": SERVICE_IDS["notification-svc"],
        "service_name": "notification-svc",
        "service_type": "MICROSERVICE",
        "description": "Transactional email, SMS alerts, and webhooks",
        "owner": "Platform Team",
        "criticality": "MEDIUM",
        "is_active": True,
        "created_at": datetime.now(timezone.utc) - timedelta(days=30),
        "updated_at": datetime.now(timezone.utc),
    },
    {
        "id": SERVICE_IDS["search-service"],
        "service_name": "search-service",
        "service_type": "MICROSERVICE",
        "description": "Catalog full-text search and indexing cluster",
        "owner": "Search Team",
        "criticality": "MEDIUM",
        "is_active": True,
        "created_at": datetime.now(timezone.utc) - timedelta(days=30),
        "updated_at": datetime.now(timezone.utc),
    },
    {
        "id": SERVICE_IDS["cache-layer"],
        "service_name": "cache-layer",
        "service_type": "INFRASTRUCTURE",
        "description": "Redis in-memory caching cluster and session storage",
        "owner": "Platform Team",
        "criticality": "HIGH",
        "is_active": True,
        "created_at": datetime.now(timezone.utc) - timedelta(days=30),
        "updated_at": datetime.now(timezone.utc),
    },
    {
        "id": SERVICE_IDS["message-queue"],
        "service_name": "message-queue",
        "service_type": "INFRASTRUCTURE",
        "description": "RabbitMQ distributed event streaming message broker",
        "owner": "Platform Team",
        "criticality": "CRITICAL",
        "is_active": True,
        "created_at": datetime.now(timezone.utc) - timedelta(days=30),
        "updated_at": datetime.now(timezone.utc),
    },
    {
        "id": SERVICE_IDS["postgres-primary"],
        "service_name": "postgres-primary",
        "service_type": "DATABASE",
        "description": "Primary transactional PostgreSQL database cluster",
        "owner": "DBA Team",
        "criticality": "CRITICAL",
        "is_active": True,
        "created_at": datetime.now(timezone.utc) - timedelta(days=30),
        "updated_at": datetime.now(timezone.utc),
    },
    {
        "id": SERVICE_IDS["postgres-replica"],
        "service_name": "postgres-replica",
        "service_type": "DATABASE",
        "description": "Read-replica PostgreSQL node for reporting and analytical reads",
        "owner": "DBA Team",
        "criticality": "HIGH",
        "is_active": True,
        "created_at": datetime.now(timezone.utc) - timedelta(days=30),
        "updated_at": datetime.now(timezone.utc),
    },
]

# 19 Directed Service Dependencies (matching init.sql)
RAW_DEPENDENCIES = [
    ("api-gateway", "auth-service", "SYNC"),
    ("api-gateway", "user-service", "SYNC"),
    ("api-gateway", "order-service", "SYNC"),
    ("api-gateway", "search-service", "SYNC"),
    ("auth-service", "postgres-primary", "SYNC"),
    ("auth-service", "cache-layer", "SYNC"),
    ("user-service", "postgres-primary", "SYNC"),
    ("user-service", "cache-layer", "SYNC"),
    ("order-service", "payment-service", "SYNC"),
    ("order-service", "inventory-service", "SYNC"),
    ("order-service", "postgres-primary", "SYNC"),
    ("order-service", "message-queue", "ASYNC"),
    ("payment-service", "postgres-primary", "SYNC"),
    ("payment-service", "message-queue", "ASYNC"),
    ("inventory-service", "postgres-primary", "SYNC"),
    ("inventory-service", "cache-layer", "SYNC"),
    ("notification-svc", "message-queue", "ASYNC"),
    ("search-service", "cache-layer", "SYNC"),
    ("postgres-replica", "postgres-primary", "REPLICATION"),
]

# Generate dependency objects
DEPENDENCIES_LIST = []
for idx, (src, tgt, dep_type) in enumerate(RAW_DEPENDENCIES):
    DEPENDENCIES_LIST.append({
        "id": uuid.UUID(f"20000000-0000-0000-0000-{idx+1:012d}"),
        "source_service_id": SERVICE_IDS[src],
        "target_service_id": SERVICE_IDS[tgt],
        "source_service_name": src,
        "target_service_name": tgt,
        "dependency_type": dep_type,
        "created_at": datetime.now(timezone.utc) - timedelta(days=30),
    })

# Sample Active & Historical Incidents
RAW_INCIDENTS = [
    {
        "id": uuid.UUID("30000000-0000-0000-0000-000000000891"),
        "title": "High Latency & Connection Pool Exhaustion on postgres-primary",
        "description": "Database active connections exceeded 95% threshold causing query queueing and downstream timeouts in payment-service and order-service.",
        "severity": "CRITICAL",
        "status": "INVESTIGATING",
        "service_id": SERVICE_IDS["postgres-primary"],
        "risk_score": Decimal("0.89"),
        "confidence": Decimal("0.94"),
        "predicted_failure": datetime.now(timezone.utc) + timedelta(minutes=45),
        "detected_at": datetime.now(timezone.utc) - timedelta(minutes=24),
        "resolved_at": None,
        "assigned_to": None,
        "created_by": uuid.UUID("00000000-0000-0000-0000-000000000001"),
        "created_at": datetime.now(timezone.utc) - timedelta(minutes=24),
        "updated_at": datetime.now(timezone.utc) - timedelta(minutes=2),
    },
    {
        "id": uuid.UUID("30000000-0000-0000-0000-000000000892"),
        "title": "Payment gateway HTTP 504 gateway timeout spike",
        "description": "Downstream payment processing responses degraded by 340ms, causing cascading retry storm to auth and order services.",
        "severity": "HIGH",
        "status": "OPEN",
        "service_id": SERVICE_IDS["payment-service"],
        "risk_score": Decimal("0.76"),
        "confidence": Decimal("0.88"),
        "predicted_failure": datetime.now(timezone.utc) + timedelta(minutes=60),
        "detected_at": datetime.now(timezone.utc) - timedelta(minutes=15),
        "resolved_at": None,
        "assigned_to": None,
        "created_by": uuid.UUID("00000000-0000-0000-0000-000000000001"),
        "created_at": datetime.now(timezone.utc) - timedelta(minutes=15),
        "updated_at": datetime.now(timezone.utc) - timedelta(minutes=5),
    },
    {
        "id": uuid.UUID("30000000-0000-0000-0000-000000000890"),
        "title": "Inventory sync lag spike during batch settlement",
        "description": "Cache synchronization between Redis cache-layer and inventory-service dropped consistency during flash sale peak.",
        "severity": "MEDIUM",
        "status": "RESOLVED",
        "service_id": SERVICE_IDS["inventory-service"],
        "risk_score": Decimal("0.42"),
        "confidence": Decimal("0.91"),
        "predicted_failure": None,
        "detected_at": datetime.now(timezone.utc) - timedelta(hours=3),
        "resolved_at": datetime.now(timezone.utc) - timedelta(hours=1),
        "assigned_to": None,
        "created_by": uuid.UUID("00000000-0000-0000-0000-000000000001"),
        "created_at": datetime.now(timezone.utc) - timedelta(hours=3),
        "updated_at": datetime.now(timezone.utc) - timedelta(hours=1),
    },
]

# Latest Risk Assessment Snapshots
RAW_RISK_ASSESSMENTS = [
    {
        "id": uuid.UUID("40000000-0000-0000-0000-000000000001"),
        "service_id": SERVICE_IDS["postgres-primary"],
        "service_name": "postgres-primary",
        "risk_score": Decimal("88.5"),
        "confidence": Decimal("0.94"),
        "anomaly_score": Decimal("0.89"),
        "predicted_failure_time": datetime.now(timezone.utc) + timedelta(minutes=45),
        "affected_services": ["payment-service", "order-service", "auth-service"],
        "features_used": {"connection_pool_usage": 0.96, "cpu_iowait": 48.2, "active_locks": 142},
        "model_version": "v1.2.0-catboost",
        "assessed_at": datetime.now(timezone.utc) - timedelta(minutes=2),
    },
    {
        "id": uuid.UUID("40000000-0000-0000-0000-000000000002"),
        "service_id": SERVICE_IDS["payment-service"],
        "service_name": "payment-service",
        "risk_score": Decimal("76.0"),
        "confidence": Decimal("0.88"),
        "anomaly_score": Decimal("0.78"),
        "predicted_failure_time": datetime.now(timezone.utc) + timedelta(minutes=60),
        "affected_services": ["order-service", "api-gateway"],
        "features_used": {"http_5xx_rate": 0.084, "p99_latency_ms": 1420},
        "model_version": "v1.2.0-catboost",
        "assessed_at": datetime.now(timezone.utc) - timedelta(minutes=3),
    },
    {
        "id": uuid.UUID("40000000-0000-0000-0000-000000000003"),
        "service_id": SERVICE_IDS["order-service"],
        "service_name": "order-service",
        "risk_score": Decimal("64.2"),
        "confidence": Decimal("0.86"),
        "anomaly_score": Decimal("0.62"),
        "predicted_failure_time": None,
        "affected_services": ["api-gateway"],
        "features_used": {"circuit_breaker_trips": 12, "queue_depth": 340},
        "model_version": "v1.2.0-catboost",
        "assessed_at": datetime.now(timezone.utc) - timedelta(minutes=4),
    },
    {
        "id": uuid.UUID("40000000-0000-0000-0000-000000000004"),
        "service_id": SERVICE_IDS["api-gateway"],
        "service_name": "api-gateway",
        "risk_score": Decimal("48.0"),
        "confidence": Decimal("0.90"),
        "anomaly_score": Decimal("0.45"),
        "predicted_failure_time": None,
        "affected_services": [],
        "features_used": {"request_rps": 4200, "error_budget_burn": 0.12},
        "model_version": "v1.2.0-catboost",
        "assessed_at": datetime.now(timezone.utc) - timedelta(minutes=5),
    },
    {
        "id": uuid.UUID("40000000-0000-0000-0000-000000000005"),
        "service_id": SERVICE_IDS["auth-service"],
        "service_name": "auth-service",
        "risk_score": Decimal("38.5"),
        "confidence": Decimal("0.93"),
        "anomaly_score": Decimal("0.35"),
        "predicted_failure_time": None,
        "affected_services": [],
        "features_used": {"jwt_verify_latency_ms": 12.4},
        "model_version": "v1.2.0-catboost",
        "assessed_at": datetime.now(timezone.utc) - timedelta(minutes=5),
    },
    {
        "id": uuid.UUID("40000000-0000-0000-0000-000000000006"),
        "service_id": SERVICE_IDS["inventory-service"],
        "service_name": "inventory-service",
        "risk_score": Decimal("24.0"),
        "confidence": Decimal("0.95"),
        "anomaly_score": Decimal("0.20"),
        "predicted_failure_time": None,
        "affected_services": [],
        "features_used": {"sync_delay_ms": 45},
        "model_version": "v1.2.0-catboost",
        "assessed_at": datetime.now(timezone.utc) - timedelta(minutes=6),
    },
]

# In-Memory Stateful Collections
_services: List[Dict[str, Any]] = list(RAW_SERVICES)
_dependencies: List[Dict[str, Any]] = list(DEPENDENCIES_LIST)
_incidents: List[Dict[str, Any]] = list(RAW_INCIDENTS)
_risk_assessments: List[Dict[str, Any]] = list(RAW_RISK_ASSESSMENTS)


def get_demo_services(is_active: Optional[bool] = None, criticality: Optional[str] = None):
    res = _services
    if is_active is not None:
        res = [s for s in res if s["is_active"] == is_active]
    if criticality is not None:
        res = [s for s in res if s["criticality"].upper() == criticality.upper()]
    return res


def get_demo_topology():
    return {
        "services": _services,
        "dependencies": _dependencies,
        "total_services": len(_services),
        "total_dependencies": len(_dependencies),
    }


def get_demo_incidents(status: Optional[str] = None, severity: Optional[str] = None, service_id: Optional[uuid.UUID] = None):
    res = _incidents
    if status:
        res = [i for i in res if i["status"].upper() == status.upper()]
    if severity:
        res = [i for i in res if i["severity"].upper() == severity.upper()]
    if service_id:
        res = [i for i in res if i["service_id"] == service_id]
    return res


def get_demo_incident(incident_id: uuid.UUID):
    for i in _incidents:
        if i["id"] == incident_id:
            return i
    return None


def update_demo_incident_status(incident_id: uuid.UUID, new_status: str):
    for i in _incidents:
        if i["id"] == incident_id:
            i["status"] = new_status
            i["updated_at"] = datetime.now(timezone.utc)
            if new_status.upper() in ("RESOLVED", "MITIGATED"):
                i["resolved_at"] = datetime.now(timezone.utc)
            return i
    return None


def get_demo_risk_assessments(service_id: Optional[uuid.UUID] = None):
    res = _risk_assessments
    if service_id:
        res = [r for r in res if r["service_id"] == service_id]
    return res
