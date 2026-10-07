# Synapse RiskOps — Live Environment Architecture Proposal

> **Status:** Proposal — awaiting approval before implementation
> **Goal:** Replace synthetic CSV data with real, continuously-running microservices that generate live telemetry consumed by Synapse RiskOps.

---

## Table of Contents

1. [Current Architecture Analysis](#1-current-architecture-analysis)
2. [What Already Exists (Category A)](#2-what-already-exists-category-a)
3. [What Should Be Added (Category B)](#3-what-should-be-added-category-b)
4. [What Is Unnecessary (Category C)](#4-what-is-unnecessary-category-c)
5. [Service Dependency Graph](#5-service-dependency-graph)
6. [Telemetry Specification per Service](#6-telemetry-specification-per-service)
7. [Complete Data Flow into Synapse](#7-complete-data-flow-into-synapse)
8. [Failure Injection Design](#8-failure-injection-design)
9. [Traffic Generator](#9-traffic-generator)
10. [Docker Compose Changes](#10-docker-compose-changes)
11. [Integration Bridge — Connecting Live Telemetry to Synapse](#11-integration-bridge)
12. [Summary of All Changes](#12-summary-of-all-changes)

---

## 1. Current Architecture Analysis

### Current Data Flow (Static/Synthetic)

```mermaid
graph LR
    A["generate_synthetic_metrics.py"] -->|CSV| B["sample_metrics.csv<br/>(48,384 rows)"]
    B -->|Loaded at startup| C["ml-engine CSVLoader"]
    C --> D["RiskEngine.train()"]
    D --> E["Isolation Forest +<br/>Failure Forecaster"]
    E -->|POST /api/risk-score| F["GenAI Agent<br/>/diagnose"]
    F --> G["LangGraph Pipeline"]
    G --> H["n8n / Activepieces<br/>Automation"]
```

### Current Services Inventory

| Service | Port | Purpose | Generates Live Telemetry? |
|---|---|---|---|
| `postgres` | 5432 | Synapse DB (incidents, services, users) | ❌ Not application-level |
| `backend` | 8080 | FastAPI core API (incidents, auth, SSE) | ❌ No /metrics endpoint |
| `ml-engine` | 8000 | Risk scoring, anomaly detection, graph | ✅ OTel traces + /metrics via Prometheus |
| `genai-agent` | 8001 | LangGraph RCA pipeline, chatbot | ✅ OTel traces + /metrics via Prometheus |
| `frontend` | 5173 | React dashboard (Vite) | ❌ Client-side only |
| `n8n` | 5678 | Workflow automation | ❌ No Prometheus scrape |
| `redis` | 6379 | Cache/message queue | ❌ No exporter configured |
| `semaphore` | 3000 | Ansible UI/API control plane | ❌ Infra tool |
| `activepieces` | 8888 | Workflow & notification engine | ❌ Infra tool |
| `prometheus` | 9090 | Metrics collector | ✅ Self-metrics |
| `otel-collector` | 4317/4318 | Trace/metric/log pipeline | ✅ Pipeline metrics |
| `alertmanager` | 9093 | Alert routing | ✅ Self-metrics |
| `cadvisor` | 8082 | Container resource metrics | ✅ CPU/mem/net/disk for all containers |
| `node-exporter` | 9100 | Host-level metrics | ✅ Host CPU/mem/disk |
| `jaeger` | 16686 | Distributed trace visualization | ✅ Trace storage |

### Key Gap Identified

The 12 services in the synthetic data (`api-gateway`, `auth-service`, `user-service`, `order-service`, `payment-service`, `inventory-service`, `notification-svc`, `search-service`, `cache-layer`, `message-queue`, `postgres-primary`, `postgres-replica`) **do not exist as actual running processes**. They are only names in:
- [sample_metrics.csv](file:///e:/Users/Jayraj/synapse-riskops/sample-data/sample_metrics.csv)
- [sample_dependencies.csv](file:///e:/Users/Jayraj/synapse-riskops/sample-data/sample_dependencies.csv)
- [init.sql](file:///e:/Users/Jayraj/synapse-riskops/docker/postgres/init.sql) seed data

The ML engine currently trains on this CSV at startup via [CSVLoader](file:///e:/Users/Jayraj/synapse-riskops/ml-engine/app/services/csv_loader.py) and scores against it. There are no real processes backing these service names.

---

## 2. What Already Exists (Category A)

> [!IMPORTANT]
> These components must **NOT** be duplicated. The new live services integrate into this existing infrastructure.

### A1. Synapse Core Services (Keep As-Is)

| Component | Role | Integration Point |
|---|---|---|
| **ml-engine** | Risk scoring (Isolation Forest + Statsmodels), graph traversal, RCA | Will consume live metrics instead of CSV |
| **genai-agent** | LangGraph RCA pipeline (Gemini), chatbot, routing | Will receive real /diagnose calls |
| **backend** | Incident persistence, SSE, auth, orchestration | Will persist real incidents from live detection |
| **frontend** | React dashboard | Will display live data (no changes needed) |
| **postgres** | Synapse database | Already stores services + dependencies; will also serve as the live environment's DB |

### A2. Observability Stack (Keep As-Is, Extend Config)

| Component | Role | Needed Change |
|---|---|---|
| **Prometheus** | Scrape metrics | Add scrape targets for new live services |
| **OTel Collector** | Receive OTLP traces/metrics/logs | No changes — already listens on 4317/4318 |
| **Alertmanager** | Route alerts | No changes — rules already reference `synapse-.*` containers |
| **cAdvisor** | Container metrics | No changes — automatically discovers all containers |
| **Node Exporter** | Host metrics | No changes |
| **Jaeger** | Trace visualization | No changes |

### A3. Alert Rules (Keep As-Is)

The existing [riskops_alerts.yml](file:///e:/Users/Jayraj/synapse-riskops/docker/prometheus/rules/riskops_alerts.yml) already defines alerts for:
- `HighCpuUsage`, `CriticalCpuUsage` (container CPU via cAdvisor)
- `HighMemoryUsage`, `CriticalMemoryUsage` (container memory)
- `ContainerRestarting`, `ContainerOOMKilled` (stability)
- `HighErrorRate`, `HighLatencyP99`, `RequestSpikeDetected` (SLI)
- `HighRiskScore`, `ElevatedRiskScore` (ML-computed risk)

These rules will fire against the real container metrics from the new live services automatically — **no changes needed**.

### A4. Automation Pipeline (Keep As-Is)

| Component | Role |
|---|---|
| **n8n** | Receives webhook from Alertmanager + GenAI agent |
| **Activepieces** | Receives webhook from GenAI agent |
| **Semaphore** | Ansible playbook execution |
| **Redis** | Shared by Activepieces |

---

## 3. What Should Be Added (Category B)

### Design Principle

Each new service must:
1. Be a **real continuously-running process** (FastAPI/Python)
2. **Match a service name** already in the Synapse dependency graph (init.sql + sample_dependencies.csv)
3. Expose a `/metrics` endpoint (Prometheus format) with application-level metrics
4. Send **OTLP traces** to the OTel Collector
5. Support a **`/chaos` endpoint** for controlled failure injection
6. Perform **real work** (HTTP calls, DB queries, cache reads) to generate genuine telemetry

### New Live Services

| # | Service Name | Container | Port | Why It's Needed |
|---|---|---|---|---|
| B1 | `api-gateway` | `synapse-live-gateway` | 9001 | Entry point for all traffic; highest fan-out in dependency graph. Must exist to test cascading failures and blast radius. |
| B2 | `auth-service` | `synapse-live-auth` | 9002 | Critical-path dependency for gateway; exercises DB + cache. Tests auth-related cascading failures. |
| B3 | `order-service` | `synapse-live-orders` | 9003 | Core business service with complex dependencies (payment, inventory, DB, message queue). Richest cascading failure surface. |
| B4 | `payment-service` | `synapse-live-payments` | 9004 | Downstream of orders; exercises DB + async messaging. Tests payment-failure scenarios. |
| B5 | `inventory-service` | `synapse-live-inventory` | 9005 | Downstream of orders; exercises DB + cache. Tests stock-check failures. |
| B6 | `notification-svc` | `synapse-live-notifications` | 9006 | Async consumer from message queue. Tests async failure propagation. |

### Infrastructure Services (Reuse or Add)

| # | Service Name | Container | Port | Notes |
|---|---|---|---|---|
| B7 | `cache-layer` | `synapse-live-redis` | 6380 | **Separate Redis instance** for the live environment (keep existing `redis:6379` for Activepieces). The live services use this as their cache. |
| B8 | `message-queue` | `synapse-live-rabbitmq` | 5672/15672 | RabbitMQ for async messaging between order→payment→notification. The dependency graph specifies AMQP. |
| B9 | `postgres-primary` | (reuse `synapse-postgres`) | 5432 | **Reuse the existing PostgreSQL** — add a separate `live_services` schema so the live environment's order/user/payment tables don't interfere with Synapse's tables. |
| B10 | `postgres-replica` | `synapse-live-pg-replica` | 5433 | PostgreSQL streaming replica of the primary. Tests replication lag and replica failure scenarios. |

### Supporting Components

| # | Component | Container | Port | Purpose |
|---|---|---|---|---|
| B11 | `traffic-generator` | `synapse-traffic-gen` | — | Continuously sends realistic HTTP requests to the api-gateway. Generates steady-state telemetry. |
| B12 | `telemetry-bridge` | `synapse-telemetry-bridge` | 9010 | **Critical new component.** Periodically collects live Prometheus metrics from all live services, transforms them into the `ServiceMetricsInput` schema, and pushes them to ml-engine's `POST /api/risk-score` or the backend's `POST /api/pipeline/diagnose-and-route`. This bridges live telemetry into Synapse's existing ML pipeline. |

### Services NOT Added (Category C)

| Service | Why Unnecessary |
|---|---|
| `user-service` | Auth-service already exercises DB + cache on the same dependency path. Adding a separate user service would duplicate the same telemetry patterns without new failure surfaces. If needed later, it can be added as a thin proxy. |
| `search-service` | Only depends on cache-layer. The cache failure scenario is already covered by auth/inventory services reading from cache. Low marginal value. |

> [!NOTE]
> `user-service` and `search-service` are kept in the dependency graph metadata but don't need to be actual running services for the current testing scope. The telemetry-bridge can generate synthetic baseline metrics for them if needed to keep the graph complete.

---

## 4. What Is Unnecessary (Category C)

These should **NOT** be built:

| Candidate | Reason to Skip |
|---|---|
| Grafana | Prometheus + Jaeger UI already provide visualization. Not in current project. |
| Loki / ELK | Logs are already handled via OTel Collector debug exporter + Loguru. Not needed for MVP. |
| Service Mesh (Istio/Linkerd) | Overkill for a local test environment. Direct HTTP + OTel is sufficient. |
| Kubernetes | The project uses Docker Compose. K8s adds unnecessary complexity for local testing. |
| Custom Prometheus exporters | Each live service exposes `/metrics` natively via `prometheus_client`. No separate exporter needed. |
| Separate monitoring DB | Prometheus already stores time-series. No need for InfluxDB/TimescaleDB. |

---

## 5. Service Dependency Graph

This matches the existing [init.sql](file:///e:/Users/Jayraj/synapse-riskops/docker/postgres/init.sql#L151-L176) and [sample_dependencies.csv](file:///e:/Users/Jayraj/synapse-riskops/sample-data/sample_dependencies.csv) exactly:

```mermaid
graph TD
    CLIENT["Traffic Generator<br/>(synapse-traffic-gen)"] -->|HTTP| GW["api-gateway<br/>:9001"]
    
    GW -->|"SYNC / HTTP"| AUTH["auth-service<br/>:9002"]
    GW -->|"SYNC / HTTP"| ORDERS["order-service<br/>:9003"]
    
    AUTH -->|"SYNC / TCP"| PG["postgres-primary<br/>:5432"]
    AUTH -->|"SYNC / TCP"| CACHE["cache-layer (Redis)<br/>:6380"]
    
    ORDERS -->|"SYNC / HTTP"| PAY["payment-service<br/>:9004"]
    ORDERS -->|"SYNC / HTTP"| INV["inventory-service<br/>:9005"]
    ORDERS -->|"SYNC / TCP"| PG
    ORDERS -->|"ASYNC / AMQP"| MQ["message-queue (RabbitMQ)<br/>:5672"]
    
    PAY -->|"SYNC / TCP"| PG
    PAY -->|"ASYNC / AMQP"| MQ
    
    INV -->|"SYNC / TCP"| PG
    INV -->|"SYNC / TCP"| CACHE
    
    NOTIF["notification-svc<br/>:9006"] -->|"ASYNC / AMQP"| MQ
    
    REPLICA["postgres-replica<br/>:5433"] -->|"REPLICATION"| PG
    
    style GW fill:#FF6B6B,stroke:#333,color:#fff
    style PG fill:#4ECDC4,stroke:#333,color:#fff
    style MQ fill:#45B7D1,stroke:#333,color:#fff
    style CACHE fill:#FFA07A,stroke:#333,color:#fff
    style REPLICA fill:#98D8C8,stroke:#333,color:#fff
```

### Failure Propagation Paths

| Failing Component | Cascading Impact |
|---|---|
| **postgres-primary** fails | → auth-service (can't authenticate) → gateway (auth fails, all requests fail) → order, payment, inventory (DB writes fail) → replica (replication breaks) |
| **cache-layer** fails | → auth-service (session cache miss, falls back to DB) → inventory-service (cache miss, increased DB load) |
| **message-queue** fails | → order-service (can't queue async events) → payment-service (can't emit payment events) → notification-svc (no messages to consume, appears idle) |
| **payment-service** fails | → order-service (payment step fails, orders rejected) → gateway (order endpoint returns errors) |
| **api-gateway** fails | → all downstream services appear healthy but receive no traffic (request_count drops to 0) |
| **order-service** fails | → gateway returns 5xx for /orders → payment/inventory stop receiving calls → notification-svc receives no order events |

---

## 6. Telemetry Specification per Service

Every live service exposes a `/metrics` endpoint (Prometheus format) and sends OTLP traces to the OTel Collector.

### Application-Level Metrics (all services)

| Metric Name | Type | Labels | Description |
|---|---|---|---|
| `http_requests_total` | Counter | `method`, `endpoint`, `status` | Total HTTP requests processed |
| `http_request_duration_seconds` | Histogram | `method`, `endpoint` | Request latency distribution (buckets: 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2, 5, 10) |
| `http_requests_in_progress` | Gauge | `method` | Currently processing requests |
| `app_error_rate` | Gauge | `service` | Rolling error rate percentage |
| `app_active_connections` | Gauge | `service` | Current active connections |
| `app_thread_count` | Gauge | `service` | Active thread/coroutine count |
| `app_gc_pause_seconds` | Summary | `service` | GC pause duration |

### Service-Specific Metrics

| Service | Additional Metrics |
|---|---|
| **api-gateway** | `gateway_upstream_duration_seconds{target}`, `gateway_circuit_breaker_state{target}` |
| **auth-service** | `auth_token_validations_total`, `auth_cache_hits_total`, `auth_cache_misses_total` |
| **order-service** | `orders_created_total`, `orders_failed_total`, `order_processing_duration_seconds` |
| **payment-service** | `payments_processed_total{status}`, `payment_processing_duration_seconds` |
| **inventory-service** | `inventory_checks_total`, `inventory_cache_hit_ratio` |
| **notification-svc** | `notifications_sent_total{channel}`, `queue_messages_consumed_total`, `queue_consumer_lag` |
| **cache-layer** | Standard Redis metrics via `redis_exporter` sidecar or built-in INFO scraping |
| **message-queue** | RabbitMQ management plugin metrics (`rabbitmq_queue_messages`, `rabbitmq_queue_consumers`, etc.) |
| **postgres-primary** | `pg_stat_activity` connection count, query duration (via pg_stat_statements or application-level) |
| **postgres-replica** | Replication lag (`pg_stat_replication`), read query latency |

### Mapping to Synapse's ServiceMetricsInput Schema

The telemetry-bridge translates live Prometheus metrics into the [ServiceMetricsInput](file:///e:/Users/Jayraj/synapse-riskops/ml-engine/app/schemas/prediction.py#L44-L78) format:

| ServiceMetricsInput Field | Source |
|---|---|
| `cpu_usage` | cAdvisor: `rate(container_cpu_usage_seconds_total{name="synapse-live-*"}[1m]) * 100` |
| `memory_usage` | cAdvisor: `container_memory_usage_bytes / container_spec_memory_limit_bytes * 100` |
| `disk_io` | cAdvisor: `rate(container_fs_io_time_seconds_total[1m])` |
| `network_latency_ms` | Application: `histogram_quantile(0.5, http_request_duration_seconds) * 1000` |
| `request_count` | Application: `increase(http_requests_total[5m])` |
| `error_rate` | Application: `rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m]) * 100` |
| `response_time_p99` | Application: `histogram_quantile(0.99, http_request_duration_seconds) * 1000` |
| `active_connections` | Application: `app_active_connections` gauge |
| `gc_pause_ms` | Application: `app_gc_pause_seconds * 1000` (or Python GC stats) |
| `thread_count` | Application: `app_thread_count` gauge |

---

## 7. Complete Data Flow into Synapse

```mermaid
graph TD
    subgraph "Live Microservice Environment"
        TG["Traffic Generator"] -->|HTTP| GW["api-gateway"]
        GW --> AUTH["auth-service"]
        GW --> ORD["order-service"]
        ORD --> PAY["payment-service"]
        ORD --> INV["inventory-service"]
        ORD --> MQ["message-queue"]
        PAY --> MQ
        NOTIF["notification-svc"] --> MQ
        AUTH --> PG["postgres-primary"]
        AUTH --> CACHE["cache-layer"]
        ORD --> PG
        PAY --> PG
        INV --> PG
        INV --> CACHE
    end

    subgraph "Telemetry Collection"
        GW -.->|"/metrics"| PROM["Prometheus"]
        AUTH -.->|"/metrics"| PROM
        ORD -.->|"/metrics"| PROM
        PAY -.->|"/metrics"| PROM
        INV -.->|"/metrics"| PROM
        NOTIF -.->|"/metrics"| PROM
        
        GW -.->|"OTLP"| OTEL["OTel Collector"]
        AUTH -.->|"OTLP"| OTEL
        ORD -.->|"OTLP"| OTEL
        PAY -.->|"OTLP"| OTEL
        INV -.->|"OTLP"| OTEL
        NOTIF -.->|"OTLP"| OTEL
        
        CAD["cAdvisor"] -.->|"container metrics"| PROM
    end

    subgraph "Synapse RiskOps Pipeline"
        BRIDGE["Telemetry Bridge<br/>(every 30s)"] -->|"PromQL queries"| PROM
        BRIDGE -->|"POST ServiceMetricsInput"| ML["ml-engine<br/>RiskEngine.score()"]
        ML -->|"PredictionResponse"| GENAI["genai-agent<br/>/diagnose"]
        GENAI -->|"LangGraph Pipeline"| RCA["Root Cause<br/>Analysis"]
        RCA -->|"Guidance"| ROUTER["Confidence<br/>Router"]
        ROUTER -->|"auto_remediate"| REMEDIATION["Remediation<br/>(Docker/Ansible)"]
        ROUTER -->|"escalate"| HUMAN["Human Engineer"]
        
        BRIDGE -->|"POST /api/pipeline/<br/>diagnose-and-route"| BACKEND["Backend<br/>(Incident Persistence)"]
        BACKEND -->|"SSE"| DASHBOARD["React Dashboard"]
    end

    PROM -.->|"alerts"| AM["Alertmanager"]
    AM -->|"webhook"| N8N["n8n"]
    AM -->|"webhook"| GENAI

    style BRIDGE fill:#FF6B6B,stroke:#333,color:#fff
    style ML fill:#4ECDC4,stroke:#333,color:#fff
    style GENAI fill:#45B7D1,stroke:#333,color:#fff
```

### Step-by-Step Flow

1. **Traffic Generator** continuously sends HTTP requests to `api-gateway`
2. **api-gateway** fans out to `auth-service` and `order-service`
3. Each service performs real work (DB queries, cache lookups, queue publishes)
4. Each service exposes **`/metrics`** (Prometheus format) and sends **OTLP traces** to the OTel Collector
5. **cAdvisor** automatically collects container CPU/memory/disk/network for all `synapse-live-*` containers
6. **Prometheus** scrapes all `/metrics` endpoints every 15 seconds
7. **Telemetry Bridge** runs every 30 seconds:
   - Queries Prometheus for each live service's metrics
   - Transforms PromQL results into `ServiceMetricsInput` dictionaries
   - Sends each service's snapshot to `POST /api/risk-score` on the ML engine
   - If risk_tier is `CRITICAL` or `WATCH`, triggers `POST /api/pipeline/diagnose-and-route` on the backend
8. **ML Engine** scores each service using the already-trained models
9. **GenAI Agent** runs the full LangGraph RCA pipeline for flagged services
10. **Backend** persists incidents, broadcasts SSE events to the dashboard
11. **Alertmanager** independently fires alerts based on Prometheus rules, sending webhooks to n8n and genai-agent

---

## 8. Failure Injection Design

Every live service exposes a `POST /chaos` endpoint for controlled failure injection.

### Chaos API Contract

```json
POST /chaos
{
  "fault_type": "cpu_spike | memory_leak | latency | error_rate | crash | dependency_timeout",
  "duration_seconds": 120,
  "intensity": 0.8
}

DELETE /chaos  → clears all active faults
GET /chaos     → returns current fault status
```

### Failure Scenarios & Detection

| # | Failure Type | How It's Injected | Telemetry Change | Prometheus Alert | ML Engine Detection |
|---|---|---|---|---|---|
| F1 | **CPU Spike** | Spin-up busy loops in background threads | `container_cpu_usage_seconds_total` rises, `http_request_duration_seconds` increases | `HighCpuUsage` / `CriticalCpuUsage` | `cpu_usage` anomaly, `predicted_failure_type: cpu_saturation` |
| F2 | **Memory Exhaustion** | Allocate and hold large byte arrays | `container_memory_usage_bytes` rises toward limit | `HighMemoryUsage` / `CriticalMemoryUsage` / `ContainerOOMKilled` | `memory_usage` anomaly, `predicted_failure_type: memory_exhaustion` |
| F3 | **Increased Latency** | Add `asyncio.sleep(intensity * 5)` to request handlers | `http_request_duration_seconds` P50/P99 spike, `http_requests_in_progress` rises | `HighLatencyP99` | `network_latency_ms` / `response_time_p99` anomaly, `predicted_failure_type: latency_degradation` |
| F4 | **HTTP 5xx Errors** | Return 500 for `intensity%` of requests | `http_requests_total{status="500"}` spikes, `app_error_rate` rises | `HighErrorRate` | `error_rate` anomaly, `predicted_failure_type: error_rate_spike` |
| F5 | **Service Crash** | `os.kill(os.getpid(), signal.SIGKILL)` | `up == 0` in Prometheus, container restarts (Docker restart policy) | `ServiceDown` / `ContainerRestarting` | Service disappears from metrics, then reappears |
| F6 | **Database Slowdown** | Add `pg_sleep(intensity * 3)` to a PG function, or inject app-side delay before DB calls | DB query latency rises, `active_connections` grows (connections waiting) | `HighLatencyP99` on affected services | `active_connections` anomaly, `predicted_failure_type: connection_pool_exhaustion` |
| F7 | **Database Connection Failure** | Temporarily change DB credentials or block port via iptables | All DB-dependent services start returning 5xx, `error_rate` spikes across multiple services simultaneously | `HighErrorRate` on multiple services | Correlated anomalies across auth, orders, payment, inventory → graph RCA identifies `postgres-primary` |
| F8 | **Cascading Failure** | Inject latency into `payment-service` → causes order-service timeouts → causes gateway 5xx | Progressive telemetry degradation: payment latency → order error rate → gateway error rate | Alerts fire in sequence: payment → order → gateway | Graph-based root cause analysis traces back to `payment-service` as origin |
| F9 | **Dependency Timeout** | One service's outgoing HTTP calls to another service time out (inject via `/chaos` on the *downstream* service adding latency > caller's timeout) | Upstream service sees timeout errors, downstream appears slow | `HighErrorRate` on upstream, `HighLatencyP99` on downstream | Dependency graph shows propagation path |
| F10 | **Cache Failure** | Stop or pause the live Redis container, or inject errors on cache reads | Cache-dependent services (auth, inventory) see cache misses, fall back to DB, DB load increases | Indirect: DB-related alerts as load shifts | `active_connections` on postgres rises, latency on cache-dependent services rises |
| F11 | **Queue Failure** | Stop or pause RabbitMQ container | Order and payment services can't publish; notification-svc stops consuming | Queue-dependent services log errors, notification throughput drops to 0 | `error_rate` spike on queue-dependent services, `request_count` drops on notification-svc |

### Compound Failure Scenarios (with Ground Truth)

These map directly to the existing [simulated_incidents](file:///e:/Users/Jayraj/synapse-riskops/sample-data/simulated_incidents) scenarios:

| Scenario | Ground Truth | Injection Steps |
|---|---|---|
| **Scenario 1: Order & Payment CPU Cascade** | Root cause: `order-service` CPU saturation | 1. Inject `cpu_spike` on `order-service` → 2. After 2 min, `payment-service` CPU rises from backed-up requests → 3. Gateway latency increases |
| **Scenario 2: PostgreSQL Memory Leak** | Root cause: `postgres-primary` memory exhaustion | 1. Inject `memory_leak` on postgres (via heavy query load) → 2. `auth-service` and `user-service` start timing out → 3. Replica replication lag increases |
| **Scenario 3: Cache Failure Latency Storm** | Root cause: `cache-layer` failure | 1. Pause `synapse-live-redis` → 2. `auth-service` and `inventory-service` see cache misses → 3. Gateway P99 spikes from increased DB load |

---

## 9. Traffic Generator

### Design

A Python script (`traffic_generator.py`) running as a Docker service that continuously sends realistic HTTP traffic patterns to the api-gateway.

### Traffic Patterns

| Pattern | Behavior |
|---|---|
| **Steady state** | 5-15 requests/second spread across endpoints |
| **Diurnal cycle** | Traffic multiplier follows `sin(hour)` curve (low at night, peak during business hours) |
| **Endpoint mix** | 40% GET /orders, 20% POST /orders, 15% GET /auth/verify, 10% GET /inventory, 10% POST /payments, 5% GET /notifications |
| **Realistic variance** | Add Gaussian noise to request timing, occasional bursts |

### Endpoints Hit

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/auth/verify` | Authenticates a session |
| `GET` | `/orders` | Lists recent orders |
| `POST` | `/orders` | Creates a new order (triggers payment + inventory check) |
| `GET` | `/inventory/{sku}` | Checks stock level |
| `GET` | `/notifications` | Lists recent notifications |

---

## 10. Docker Compose Changes

> [!IMPORTANT]
> All new services are **added** to the existing [docker-compose.yml](file:///e:/Users/Jayraj/synapse-riskops/docker-compose.yml). No existing services are modified or removed.

### New Services Block

```yaml
  # ===================================================
  # LIVE ENVIRONMENT: API Gateway
  # ===================================================
  live-gateway:
    build:
      context: ./live-services/gateway
      dockerfile: Dockerfile
    container_name: synapse-live-gateway
    restart: unless-stopped
    ports:
      - "9001:9001"
    environment:
      SERVICE_NAME: api-gateway
      AUTH_SERVICE_URL: http://live-auth:9002
      ORDER_SERVICE_URL: http://live-orders:9003
      OTEL_EXPORTER_OTLP_ENDPOINT: http://otel-collector:4317
      OTEL_SERVICE_NAME: api-gateway
    depends_on:
      - live-auth
      - live-orders
    deploy:
      resources:
        limits:
          memory: 256M
          cpus: '0.5'
    networks:
      - synapse-network

  # ===================================================
  # LIVE ENVIRONMENT: Auth Service
  # ===================================================
  live-auth:
    build:
      context: ./live-services/auth
      dockerfile: Dockerfile
    container_name: synapse-live-auth
    restart: unless-stopped
    ports:
      - "9002:9002"
    environment:
      SERVICE_NAME: auth-service
      DATABASE_URL: postgresql://synapse_admin:synapse_dev_2026@postgres:5432/synapse_riskops
      REDIS_URL: redis://live-redis:6379/0
      OTEL_EXPORTER_OTLP_ENDPOINT: http://otel-collector:4317
      OTEL_SERVICE_NAME: auth-service
    depends_on:
      postgres:
        condition: service_healthy
      live-redis:
        condition: service_started
    deploy:
      resources:
        limits:
          memory: 256M
          cpus: '0.5'
    networks:
      - synapse-network

  # ===================================================
  # LIVE ENVIRONMENT: Order Service
  # ===================================================
  live-orders:
    build:
      context: ./live-services/orders
      dockerfile: Dockerfile
    container_name: synapse-live-orders
    restart: unless-stopped
    ports:
      - "9003:9003"
    environment:
      SERVICE_NAME: order-service
      DATABASE_URL: postgresql://synapse_admin:synapse_dev_2026@postgres:5432/synapse_riskops
      PAYMENT_SERVICE_URL: http://live-payments:9004
      INVENTORY_SERVICE_URL: http://live-inventory:9005
      RABBITMQ_URL: amqp://guest:guest@live-rabbitmq:5672/
      OTEL_EXPORTER_OTLP_ENDPOINT: http://otel-collector:4317
      OTEL_SERVICE_NAME: order-service
    depends_on:
      postgres:
        condition: service_healthy
      live-payments:
        condition: service_started
      live-inventory:
        condition: service_started
      live-rabbitmq:
        condition: service_started
    deploy:
      resources:
        limits:
          memory: 256M
          cpus: '0.5'
    networks:
      - synapse-network

  # ===================================================
  # LIVE ENVIRONMENT: Payment Service
  # ===================================================
  live-payments:
    build:
      context: ./live-services/payments
      dockerfile: Dockerfile
    container_name: synapse-live-payments
    restart: unless-stopped
    ports:
      - "9004:9004"
    environment:
      SERVICE_NAME: payment-service
      DATABASE_URL: postgresql://synapse_admin:synapse_dev_2026@postgres:5432/synapse_riskops
      RABBITMQ_URL: amqp://guest:guest@live-rabbitmq:5672/
      OTEL_EXPORTER_OTLP_ENDPOINT: http://otel-collector:4317
      OTEL_SERVICE_NAME: payment-service
    depends_on:
      postgres:
        condition: service_healthy
      live-rabbitmq:
        condition: service_started
    deploy:
      resources:
        limits:
          memory: 256M
          cpus: '0.5'
    networks:
      - synapse-network

  # ===================================================
  # LIVE ENVIRONMENT: Inventory Service
  # ===================================================
  live-inventory:
    build:
      context: ./live-services/inventory
      dockerfile: Dockerfile
    container_name: synapse-live-inventory
    restart: unless-stopped
    ports:
      - "9005:9005"
    environment:
      SERVICE_NAME: inventory-service
      DATABASE_URL: postgresql://synapse_admin:synapse_dev_2026@postgres:5432/synapse_riskops
      REDIS_URL: redis://live-redis:6379/1
      OTEL_EXPORTER_OTLP_ENDPOINT: http://otel-collector:4317
      OTEL_SERVICE_NAME: inventory-service
    depends_on:
      postgres:
        condition: service_healthy
      live-redis:
        condition: service_started
    deploy:
      resources:
        limits:
          memory: 256M
          cpus: '0.5'
    networks:
      - synapse-network

  # ===================================================
  # LIVE ENVIRONMENT: Notification Service
  # ===================================================
  live-notifications:
    build:
      context: ./live-services/notifications
      dockerfile: Dockerfile
    container_name: synapse-live-notifications
    restart: unless-stopped
    ports:
      - "9006:9006"
    environment:
      SERVICE_NAME: notification-svc
      RABBITMQ_URL: amqp://guest:guest@live-rabbitmq:5672/
      OTEL_EXPORTER_OTLP_ENDPOINT: http://otel-collector:4317
      OTEL_SERVICE_NAME: notification-svc
    depends_on:
      live-rabbitmq:
        condition: service_started
    deploy:
      resources:
        limits:
          memory: 128M
          cpus: '0.25'
    networks:
      - synapse-network

  # ===================================================
  # LIVE ENVIRONMENT: Redis (Cache Layer)
  # ===================================================
  live-redis:
    image: redis:7-alpine
    container_name: synapse-live-redis
    restart: unless-stopped
    ports:
      - "6380:6379"
    deploy:
      resources:
        limits:
          memory: 128M
          cpus: '0.25'
    networks:
      - synapse-network

  # ===================================================
  # LIVE ENVIRONMENT: RabbitMQ (Message Queue)
  # ===================================================
  live-rabbitmq:
    image: rabbitmq:3-management-alpine
    container_name: synapse-live-rabbitmq
    restart: unless-stopped
    ports:
      - "5673:5672"    # AMQP (offset from any host RabbitMQ)
      - "15673:15672"  # Management UI
    environment:
      RABBITMQ_DEFAULT_USER: guest
      RABBITMQ_DEFAULT_PASS: guest
    deploy:
      resources:
        limits:
          memory: 256M
          cpus: '0.5'
    networks:
      - synapse-network

  # ===================================================
  # LIVE ENVIRONMENT: PostgreSQL Replica
  # ===================================================
  live-pg-replica:
    image: postgres:16-alpine
    container_name: synapse-live-pg-replica
    restart: unless-stopped
    ports:
      - "5433:5432"
    environment:
      POSTGRES_DB: synapse_riskops
      POSTGRES_USER: synapse_admin
      POSTGRES_PASSWORD: synapse_dev_2026
    depends_on:
      postgres:
        condition: service_healthy
    deploy:
      resources:
        limits:
          memory: 256M
          cpus: '0.5'
    networks:
      - synapse-network

  # ===================================================
  # LIVE ENVIRONMENT: Traffic Generator
  # ===================================================
  traffic-generator:
    build:
      context: ./live-services/traffic-generator
      dockerfile: Dockerfile
    container_name: synapse-traffic-gen
    restart: unless-stopped
    environment:
      GATEWAY_URL: http://live-gateway:9001
      REQUESTS_PER_SECOND: 10
      DIURNAL_ENABLED: "true"
    depends_on:
      - live-gateway
    networks:
      - synapse-network

  # ===================================================
  # LIVE ENVIRONMENT: Telemetry Bridge
  # ===================================================
  telemetry-bridge:
    build:
      context: ./live-services/telemetry-bridge
      dockerfile: Dockerfile
    container_name: synapse-telemetry-bridge
    restart: unless-stopped
    ports:
      - "9010:9010"
    environment:
      PROMETHEUS_URL: http://prometheus:9090
      ML_ENGINE_URL: http://ml-engine:8000
      BACKEND_URL: http://backend:8080
      POLL_INTERVAL_SECONDS: 30
      SERVICES: "api-gateway,auth-service,order-service,payment-service,inventory-service,notification-svc"
      CONTAINER_PREFIX: "synapse-live"
    depends_on:
      - prometheus
      - ml-engine
    networks:
      - synapse-network
```

### Prometheus Config Addition

Add to [docker/prometheus/prometheus.yml](file:///e:/Users/Jayraj/synapse-riskops/docker/prometheus/prometheus.yml):

```yaml
  # ----- Live Environment Services -----
  - job_name: 'live-api-gateway'
    static_configs:
      - targets: ['live-gateway:9001']
    metrics_path: /metrics

  - job_name: 'live-auth-service'
    static_configs:
      - targets: ['live-auth:9002']
    metrics_path: /metrics

  - job_name: 'live-order-service'
    static_configs:
      - targets: ['live-orders:9003']
    metrics_path: /metrics

  - job_name: 'live-payment-service'
    static_configs:
      - targets: ['live-payments:9004']
    metrics_path: /metrics

  - job_name: 'live-inventory-service'
    static_configs:
      - targets: ['live-inventory:9005']
    metrics_path: /metrics

  - job_name: 'live-notification-svc'
    static_configs:
      - targets: ['live-notifications:9006']
    metrics_path: /metrics

  - job_name: 'live-rabbitmq'
    static_configs:
      - targets: ['live-rabbitmq:15672']
    metrics_path: /api/metrics

  - job_name: 'live-telemetry-bridge'
    static_configs:
      - targets: ['telemetry-bridge:9010']
    metrics_path: /metrics
```

---

## 11. Integration Bridge — Connecting Live Telemetry to Synapse {#integration-bridge}

### The Critical Gap

The existing ML engine trains on CSV data and scores individual `ServiceMetricsInput` payloads via `POST /api/risk-score`. The new live services generate **Prometheus metrics + OTel traces** — but nothing automatically converts those into `ServiceMetricsInput` calls.

The **Telemetry Bridge** solves this.

### Telemetry Bridge Architecture

```mermaid
sequenceDiagram
    participant P as Prometheus
    participant B as Telemetry Bridge
    participant ML as ML Engine
    participant GA as GenAI Agent
    participant BE as Backend
    participant DB as PostgreSQL
    
    loop Every 30 seconds
        B->>P: PromQL: cpu, mem, latency,<br/>error_rate, etc. per service
        P-->>B: Metric values
        B->>B: Transform to ServiceMetricsInput
        B->>ML: POST /api/risk-score (per service)
        ML-->>B: PredictionResponse (risk_score, tier)
        
        alt risk_tier == CRITICAL
            B->>BE: POST /api/pipeline/diagnose-and-route
            BE->>ML: Forward to ML Engine
            BE->>GA: Forward to GenAI Agent
            GA-->>BE: DiagnoseResponse (RCA + guidance)
            BE->>DB: Persist incident
            BE-->>B: UnifiedIncidentRecord
        end
    end
```

### Two Operating Modes

| Mode | When to Use | ML Engine Behavior |
|---|---|---|
| **Initial Training** | First-time setup, or when models need retraining | Use existing synthetic CSV for training (it covers 14 days of diverse patterns). Then switch to live scoring. |
| **Live Scoring** | Steady state | Telemetry bridge pushes real `ServiceMetricsInput` snapshots every 30s. ML engine scores them against the trained models. |
| **Continuous Retraining** (future) | After accumulating enough live data | Periodically retrain models with a mix of historical + live data. Not needed for MVP. |

> [!TIP]
> The trained models from synthetic data actually provide a **strong baseline** because the synthetic data covers the same 12 service names with realistic ranges. When live services generate metrics in similar ranges, the anomaly detector will correctly flag deviations. This is a feature, not a limitation — it means the system works from day one.

---

## 12. Summary of All Changes

### New Files/Directories to Create

```
live-services/
├── shared/                          # Shared code for all live services
│   ├── base_service.py             # Base FastAPI app with /metrics, /health, /chaos
│   ├── telemetry.py                # OTel setup (traces + metrics)
│   ├── chaos.py                    # Chaos engineering fault injection engine
│   └── requirements.txt           # Shared Python dependencies
├── gateway/
│   ├── Dockerfile
│   ├── main.py                    # FastAPI: proxy to auth + orders
│   └── requirements.txt
├── auth/
│   ├── Dockerfile
│   ├── main.py                    # FastAPI: JWT validation, DB + cache
│   └── requirements.txt
├── orders/
│   ├── Dockerfile
│   ├── main.py                    # FastAPI: CRUD orders, calls payment + inventory
│   └── requirements.txt
├── payments/
│   ├── Dockerfile
│   ├── main.py                    # FastAPI: process payments, DB + queue
│   └── requirements.txt
├── inventory/
│   ├── Dockerfile
│   ├── main.py                    # FastAPI: stock checks, DB + cache
│   └── requirements.txt
├── notifications/
│   ├── Dockerfile
│   ├── main.py                    # FastAPI: consume queue, send notifications
│   └── requirements.txt
├── traffic-generator/
│   ├── Dockerfile
│   ├── main.py                    # Continuous traffic generation
│   └── requirements.txt
└── telemetry-bridge/
    ├── Dockerfile
    ├── main.py                    # PromQL → ServiceMetricsInput → ML Engine
    └── requirements.txt
```

### Existing Files to Modify

| File | Change | Why |
|---|---|---|
| [docker-compose.yml](file:///e:/Users/Jayraj/synapse-riskops/docker-compose.yml) | Add all new service definitions | Orchestrate the live environment alongside Synapse |
| [docker/prometheus/prometheus.yml](file:///e:/Users/Jayraj/synapse-riskops/docker/prometheus/prometheus.yml) | Add scrape targets for live services | Enable Prometheus to collect application metrics |
| [docker/postgres/init.sql](file:///e:/Users/Jayraj/synapse-riskops/docker/postgres/init.sql) | Add `live_services` schema with orders/payments/inventory tables | Give live services real DB tables to operate on |

### Existing Files That Do NOT Change

| File | Why |
|---|---|
| `ml-engine/*` | Already accepts `POST /api/risk-score` with `ServiceMetricsInput`. No changes needed. |
| `genai-agent/*` | Already has `/diagnose` endpoint. The telemetry bridge triggers it through the backend. |
| `backend/*` | Already has `POST /api/pipeline/diagnose-and-route`. No changes needed. |
| `frontend/*` | Already displays incidents from the backend API. Will show real incidents automatically. |
| `docker/alertmanager/*` | Rules already match `synapse-.*` containers. New containers automatically match. |
| `docker/otel-collector/*` | Already accepts OTLP on 4317/4318. No changes needed. |
| `docker/prometheus/rules/*` | Alert rules use `name=~"synapse-.*"` which matches new containers. No changes needed. |

### Resource Estimates

| Category | Containers | Estimated RAM | Estimated CPU |
|---|---|---|---|
| Existing Synapse Core | 5 (postgres, backend, ml-engine, genai-agent, frontend) | ~2 GB | ~2 cores |
| Existing Observability | 6 (prometheus, otel, alertmanager, cadvisor, node-exporter, jaeger) | ~1.5 GB | ~1 core |
| Existing Automation | 4 (n8n, activepieces, semaphore, redis) | ~1.5 GB | ~1 core |
| **New Live Services** | **10** (6 app services + redis + rabbitmq + traffic-gen + telemetry-bridge) | **~2 GB** | **~2 cores** |
| **Total** | **25 containers** | **~7 GB** | **~6 cores** |

> [!WARNING]
> A machine with at least **16 GB RAM** and **8 CPU cores** is recommended. The `deploy.resources.limits` in docker-compose ensure each live service stays within its allocation. If resources are tight, the postgres-replica can be omitted.

---

## End-to-End Validation Scenario

Once implemented, the following sequence validates the complete pipeline:

```
1. Start: docker compose up -d
2. Wait: ~2 minutes for all services to become healthy
3. Observe: Dashboard shows live telemetry for all services (HEALTHY state)
4. Inject: POST http://localhost:9004/chaos {"fault_type": "latency", "duration_seconds": 180, "intensity": 0.8}
   → payment-service adds 4s delay to all responses
5. Propagate: order-service starts timing out on payment calls → error_rate rises
6. Detect: Telemetry Bridge picks up elevated metrics → sends to ML Engine
7. Score: ML Engine returns risk_tier: CRITICAL for payment-service and order-service  
8. Alert: Prometheus fires HighLatencyP99 + HighErrorRate alerts
9. Diagnose: GenAI Agent runs LangGraph pipeline:
   - ML Node: confirms CRITICAL risk
   - Log Analyzer: detects timeout errors in order-service logs
   - Root Cause Identifier: traces dependency graph → payment-service is upstream of failures
   - Guidance Generator: recommends scaling payment-service or investigating latency source
   - Confidence Router: decides auto_remediate vs escalate
10. Respond: Remediation node executes Docker restart or Ansible playbook
11. Recover: POST http://localhost:9004/chaos (DELETE) → fault cleared
12. Verify: Dashboard shows services returning to HEALTHY
```

**This is the "known ground truth" loop you asked for.**
