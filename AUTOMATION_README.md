# 🔧 Synapse RiskOps — Automation & Tool Integration Guide

> **What is this?** A comprehensive reference for every automation tool integrated
> into Synapse RiskOps — what it does, where the code lives, how to verify it's running,
> and how data flows between components.

---

## 📋 Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Tool #1: Ansible (Server Fixes)](#1-ansible--semaphore-server-fixes)
3. [Tool #2: Prometheus (Metrics & CPU Tracking)](#2-prometheus-metrics--cpu-tracking)
4. [Tool #3: Alertmanager (Alert Routing)](#3-alertmanager-alert-routing)
5. [Tool #4: Kubernetes (Self-Healing Infrastructure)](#4-kubernetes-self-healing-infrastructure)
6. [Tool #5: OpenTelemetry (Distributed Tracing)](#5-opentelemetry-distributed-tracing)
7. [Tool #6: Docker SDK (Programmatic Container Fixes)](#6-docker-python-sdk-programmatic-fixes)
8. [Tool #7: Activepieces (Workflow Automation)](#7-activepieces-workflow-automation)
9. [Tool #8: Runbook Engine (Formal Remediation)](#8-runbook-engine-formal-remediation)
10. [Tool #9: NetworkX (Root Cause Graph Analysis)](#9-networkx-root-cause-graph-analysis)
11. [Tool #10: Statsmodels (Predictive Analytics)](#10-statsmodels-predictive-analytics)
12. [Tool #11: n8n (Alert Orchestration)](#11-n8n-alert-orchestration)
13. [Tool #12: Slack (Notifications)](#12-slack-notifications)
14. [Full Pipeline Flow](#full-pipeline-flow)
15. [Running Verification Checks](#running-verification-checks)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        SYNAPSE RISKOPS                              │
│                                                                     │
│  ┌────────────┐     ┌────────────┐     ┌──────────────┐            │
│  │ Prometheus  │────▶│Alertmanager│────▶│  n8n / AP    │            │
│  │  + cAdvisor │     │            │     │  Automation  │            │
│  │  + Node Exp │     └─────┬──────┘     └──────┬───────┘            │
│  └──────┬─────┘           │                    │                    │
│         │                  │                    ▼                    │
│         │                  │           ┌──────────────┐             │
│         │                  └──────────▶│  GenAI Agent  │             │
│         │                              │  (LangGraph)  │             │
│         ▼                              │               │             │
│  ┌────────────┐                        │ 1. ML Node    │             │
│  │ OTel       │                        │ 2. Log Analyze│             │
│  │ Collector  │───▶ Jaeger (Traces)    │ 3. Root Cause │             │
│  └────────────┘                        │ 4. Guidance   │             │
│                                        │ 5. Router     │             │
│                                        │ 6. Remediate  │             │
│                                        └───────┬───────┘             │
│                                                │                     │
│                     ┌──────────────────────────┼───────────────┐     │
│                     │              │           │               │     │
│                     ▼              ▼           ▼               ▼     │
│              ┌───────────┐  ┌──────────┐ ┌─────────┐  ┌───────────┐ │
│              │Docker SDK │  │ Ansible  │ │   K8s   │  │  Runbook  │ │
│              │  Healer   │  │ Semaphore│ │  Healer │  │  Engine   │ │
│              └───────────┘  └──────────┘ └─────────┘  └───────────┘ │
│                                                                     │
│  ┌────────────┐     ┌────────────┐     ┌──────────────┐            │
│  │  ML Engine  │     │  NetworkX  │     │  Statsmodels │            │
│  │  Risk Score │     │  Graph     │     │  Forecasting │            │
│  └────────────┘     └────────────┘     └──────────────┘            │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 1. Ansible / Semaphore (Server Fixes)

### What It Does
Executes server-level remediation playbooks (restart services, scale resources,
clear disk, reset network) triggered autonomously by the GenAI Agent pipeline.

### Where The Code Lives

| File | Purpose |
|------|---------|
| `ansible/playbooks/restart_service.yml` | Restart a Docker container |
| `ansible/playbooks/scale_resources.yml` | Scale container memory/CPU |
| `ansible/playbooks/clear_disk.yml` | Prune Docker images/volumes |
| `ansible/playbooks/reset_network.yml` | Reconnect container to network |
| `ansible/playbooks/health_check.yml` | **[NEW]** Post-remediation validation |
| `genai-agent/app/remediation/ansible_executor.py` | **[NEW]** Python → Semaphore API bridge |

### How It's Triggered
1. GenAI Agent pipeline → `confidence_router` decides `auto_remediate`
2. `remediation_node` in LangGraph → calls `ansible_executor.py`
3. `ansible_executor.py` → POST to Semaphore API → triggers playbook

### Verify It's Running
```bash
curl http://localhost:3000/api/ping  # Semaphore health check
```

---

## 2. Prometheus (Metrics & CPU Tracking)

### What It Does
Netflix-style resource monitoring: scrapes CPU, memory, disk, network metrics
from all containers (via cAdvisor) and host (via node-exporter). Evaluates
22 alert rules and fires alerts to Alertmanager.

### Where The Code Lives

| File | Purpose |
|------|---------|
| `docker/prometheus/prometheus.yml` | Scrape config (6 targets) |
| `docker/prometheus/rules/riskops_alerts.yml` | **[EXPANDED]** 22 alert rules |
| `docker-compose.yml` (prometheus service) | Container definition |
| `docker-compose.yml` (cadvisor service) | **[NEW]** Container metrics |
| `docker-compose.yml` (node-exporter service) | **[NEW]** Host metrics |

### Alert Rule Categories
- **Service Health**: ServiceDown, MLEngineDown, GenAIAgentDown, BackendDown
- **CPU**: HighCpuUsage (>80%), CriticalCpuUsage (>95%)
- **Memory**: HighMemoryUsage (>85%), CriticalMemoryUsage (>95%), OOMKilled
- **Disk**: DiskSpaceLow (<10%), DiskSpaceWarning (<20%)
- **Network**: HighNetworkLatency, NetworkErrorsHigh
- **Stability**: ContainerRestarting (>3 in 15m)
- **Risk Score**: HighRiskScore (>0.85), ElevatedRiskScore (>0.65)
- **SLI/SLO**: HighErrorRate (>5%), HighLatencyP99 (>2s), RequestSpikeDetected
- **Host**: HostHighCpuLoad, HostHighMemoryUsage, HostSwapUsageHigh

### Verify It's Running
```bash
curl http://localhost:9090/-/healthy       # Prometheus health
curl http://localhost:9090/api/v1/rules    # List loaded alert rules
curl http://localhost:8082/metrics         # cAdvisor container metrics
curl http://localhost:9100/metrics         # Node exporter host metrics
```

---

## 3. Alertmanager (Alert Routing)

### What It Does
Routes alerts from Prometheus to the right receiver based on severity:
- **Critical** → n8n auto-remediation webhook + GenAI Agent RCA
- **Warning** → Slack notification only
- **Info** → Logged and discarded

### Where The Code Lives

| File | Purpose |
|------|---------|
| `docker/alertmanager/alertmanager.yml` | **[ENHANCED]** Multi-receiver routing |

### Key Features
- 4 receivers: n8n-auto-remediation, genai-agent-webhook, default-slack, null-receiver
- Inhibition rules: critical suppresses warning for same service
- ServiceDown suppresses all other alerts for same service

### Verify It's Running
```bash
curl http://localhost:9093/-/healthy       # Alertmanager health
curl http://localhost:9093/api/v2/status   # Full config status
```

---

## 4. Kubernetes (Self-Healing Infrastructure)

### What It Does
Provides Kubernetes-native self-healing: pod restarts, deployment scaling,
rollbacks, and node cordoning. Activated when infrastructure is K8s-based.

### Where The Code Lives

| File | Purpose |
|------|---------|
| `kubernetes/namespace.yml` | Synapse namespace |
| `kubernetes/deployments.yml` | Deployment manifests (genai-agent, ml-engine, backend) |
| `kubernetes/services.yml` | ClusterIP/NodePort services |
| `kubernetes/hpa.yml` | **[NEW]** HorizontalPodAutoscalers |
| `kubernetes/rbac.yml` | **[NEW]** ServiceAccount + ClusterRole for healer |
| `genai-agent/app/remediation/k8s_healer.py` | **[NEW]** Python K8s client |

### Capabilities
- `restart_pod()` — Delete pod for recreation
- `scale_deployment()` — Adjust replicas
- `rollback_deployment()` — Rolling restart to last known good
- `get_crashing_pods()` — Detect CrashLoopBackOff
- `cordon_node()` — Mark node unschedulable

### Verify It's Running
```bash
kubectl get pods -n synapse              # List pods
kubectl get hpa -n synapse               # Check autoscalers
kubectl get sa synapse-healer -n synapse # Verify service account
```

---

## 5. OpenTelemetry (Distributed Tracing)

### What It Does
Instruments the GenAI Agent and ML Engine with OpenTelemetry to capture
distributed traces across the entire RCA pipeline. Visualized in Jaeger.

### Where The Code Lives

| File | Purpose |
|------|---------|
| `genai-agent/app/telemetry.py` | **[NEW]** OTel setup + pipeline node tracing |
| `ml-engine/app/telemetry.py` | **[NEW]** OTel setup + ML operation tracing |
| `docker/otel-collector/otel-collector-config.yml` | **[ENHANCED]** Jaeger export + resource attributes |
| `docker-compose.yml` (jaeger service) | **[NEW]** Trace visualization UI |

### Trace Flow
```
[GenAI Agent]                          [ML Engine]
  POST /diagnose                         POST /api/risk-score
    ├─ pipeline.ml_node ─────────────────► ml.risk_scoring
    ├─ pipeline.log_analyzer               ml.graph_traversal
    ├─ pipeline.root_cause_identifier
    ├─ pipeline.proactive_guidance
    ├─ pipeline.confidence_router
    └─ pipeline.remediation_node
```

### Verify It's Running
```bash
curl http://localhost:16686              # Jaeger UI
curl http://localhost:8889/metrics       # OTel collector metrics
curl http://localhost:4318/v1/traces     # OTel HTTP receiver
```

---

## 6. Docker Python SDK (Programmatic Fixes)

### What It Does
Fast, in-process container remediation without shelling out to Ansible.
Restarts containers, updates resource limits, fixes networking, and prunes
unused resources — all via the Docker daemon socket.

### Where The Code Lives

| File | Purpose |
|------|---------|
| `genai-agent/app/remediation/docker_healer.py` | **[NEW]** Docker SDK operations |

### Capabilities
- `restart_container()` — Restart via Docker API
- `update_resources()` — Update memory/CPU limits live
- `fix_network()` — Disconnect/reconnect to Docker network
- `prune_system()` — Clean unused images/volumes/containers
- `inspect_health()` — Read container health status
- `get_container_logs()` — Fetch recent logs
- `remediate()` — Auto-select action by failure type

### Verify It's Running
```python
python -c "import docker; print(docker.from_env().ping())"  # True
```

---

## 7. Activepieces (Workflow Automation)

### What It Does
Complements n8n with ticket creation, daily incident digests, and
post-remediation validation workflows.

### Where The Code Lives

| File | Purpose |
|------|---------|
| `automation/activepieces/setup_guide.md` | **[NEW]** Integration guide |
| `docker-compose.yml` (activepieces service) | Container definition |

### Verify It's Running
```bash
curl http://localhost:8888              # Activepieces UI
```

---

## 8. Runbook Engine (Formal Remediation)

### What It Does
Formal runbook definitions (YAML) that define step-by-step remediation
procedures. The engine loads these and executes steps using Docker SDK,
Ansible, or Kubernetes healers.

### Where The Code Lives

| File | Purpose |
|------|---------|
| `runbooks/engine.py` | **[NEW]** Runbook execution engine |
| `runbooks/schema.yml` | **[NEW]** YAML schema for validation |
| `runbooks/definitions/memory_leak.yml` | **[NEW]** 7-step memory leak fix |
| `runbooks/definitions/service_crash.yml` | **[NEW]** 6-step crash recovery |
| `runbooks/definitions/disk_exhaustion.yml` | **[NEW]** 3-step disk cleanup |
| `runbooks/definitions/network_degradation.yml` | **[NEW]** 3-step network fix |
| `runbooks/definitions/high_cpu.yml` | **[NEW]** 5-step CPU remediation |
| `runbooks/definitions/cascading_failure.yml` | **[NEW]** 5-step cascade fix |
| `runbooks/definitions/database_overload.yml` | **[NEW]** 6-step DB recovery |

### Verify It's Running
```bash
python runbooks/engine.py --validate    # Validate all YAML definitions
python runbooks/engine.py               # List loaded runbooks
```

---

## 9. NetworkX (Root Cause Graph Analysis)

### What It Does
Builds a directed service dependency graph and uses PageRank, betweenness
centrality, and BFS cascade simulation to identify the true root cause
when multiple services are failing simultaneously.

### Where The Code Lives

| File | Purpose |
|------|---------|
| `ml-engine/app/services/graph_builder.py` | **[ENHANCED]** Core graph engine |
| `ml-engine/app/api/graph_analysis.py` | **[NEW]** Advanced analysis endpoints |
| `ml-engine/app/api/graph_traversal.py` | Basic traversal endpoints |

### API Endpoints
- `GET /api/graph/root-cause-analysis?services=svc1,svc2` — PageRank-based root cause
- `GET /api/graph/critical-paths` — Bottleneck detection (betweenness centrality)
- `GET /api/graph/cascade-simulation?failing_service=X` — Cascading failure simulation
- `GET /api/graph/traverse?service=X` — Basic upstream/downstream traversal
- `GET /api/graph/blast-radius?service=X` — Blast radius calculation

### Verify It's Running
```bash
curl http://localhost:8000/api/graph/critical-paths
curl "http://localhost:8000/api/graph/root-cause-analysis?services=order-service"
curl "http://localhost:8000/api/graph/cascade-simulation?failing_service=postgres-primary"
```

---

## 10. Statsmodels (Predictive Analytics)

### What It Does
Advanced time-series analysis: STL decomposition, Holt-Winters seasonal
forecasting with confidence intervals, multi-variate correlation, and
change-point detection.

### Where The Code Lives

| File | Purpose |
|------|---------|
| `ml-engine/app/models/trend_analyzer.py` | **[NEW]** Statsmodels analysis engine |
| `ml-engine/app/services/risk_engine.py` | Composite risk scoring (Isolation Forest + Statsmodels) |

### Capabilities
- `decompose()` — STL trend/seasonal/residual decomposition
- `forecast_holt_winters()` — Seasonal forecasting with 95% confidence intervals
- `correlate_metrics()` — Find which metrics drive error rate
- `detect_change_points()` — Identify sudden regime changes
- `test_stationarity()` — ADF test for trend detection

### Verify It's Running
```bash
curl -X POST http://localhost:8000/api/risk-score -H "Content-Type: application/json" \
  -d '{"metrics": {...}}'  # Returns risk_score + confidence
```

---

## 11. n8n (Alert Orchestration)

### What It Does
Primary automation engine that receives alerts from Prometheus/Alertmanager
and the GenAI Agent, routes them to Ansible/Semaphore for remediation, and
sends Slack notifications.

### Where The Code Lives

| File | Purpose |
|------|---------|
| `automation/workflows/alert_routing.json` | Main alert routing workflow |
| `automation/workflows/prometheus_alert_ingest.json` | Prometheus → n8n bridge |
| `automation/workflows/auto_ticket.json` | Ticket creation workflow |
| `automation/workflows/slack_notify.json` | Slack notification workflow |

### Verify It's Running
```bash
curl http://localhost:5678/healthz       # n8n health
```

---

## 12. Slack (Notifications)

### What It Does
Receives escalation alerts and remediation status updates from n8n.
Posts formatted incident cards to the engineering channel.

### Where It's Configured
- Inside `automation/workflows/alert_routing.json` (Slack node)
- Channel ID configured in n8n Slack credentials

---

## Full Pipeline Flow

```
1. Prometheus scrapes metrics from all services (every 15s)
           │
2. Alert rules evaluate → fire if threshold breached
           │
3. Alertmanager routes alert by severity
           │
    ┌──────┴──────────────────────────────┐
    │                                      │
    ▼ (critical)                           ▼ (warning)
4a. n8n webhook receives alert           4b. Slack notification sent
    │
5. n8n normalizes payload → forwards to GenAI Agent POST /diagnose
    │
6. LangGraph Pipeline executes:
    ├── Step 1: ML Node → calls ML Engine /api/risk-score
    ├── Step 2: Log Analyzer → extracts observations from logs
    ├── Step 3: Root Cause Identifier → Gemini LLM + NetworkX graph
    ├── Step 4: Proactive Guidance → Gemini generates preventive actions
    ├── Step 5: Confidence Router → auto_remediate vs escalate
    └── Step 6: Remediation Node →
         ├── Docker SDK (fast container fix)
         ├── Runbook Engine (multi-step orchestration)
         └── Ansible/Semaphore (complex server ops)
              │
7. Post-remediation health check validates fix
              │
    ┌─────────┴───────────┐
    │                      │
    ▼ (success)            ▼ (failure)
8a. Log success          8b. Escalate to engineer
    → Slack ✅                → Slack 🚨 + Jira ticket
```

---

## Running Verification Checks

Run this checklist after deployment to confirm every tool is operational:

```bash
# ===== Infrastructure Services =====
curl -sf http://localhost:9090/-/healthy && echo "✅ Prometheus" || echo "❌ Prometheus"
curl -sf http://localhost:9093/-/healthy && echo "✅ Alertmanager" || echo "❌ Alertmanager"
curl -sf http://localhost:8082/metrics | head -1 && echo "✅ cAdvisor" || echo "❌ cAdvisor"
curl -sf http://localhost:9100/metrics | head -1 && echo "✅ Node Exporter" || echo "❌ Node Exporter"
curl -sf http://localhost:16686 && echo "✅ Jaeger" || echo "❌ Jaeger"
curl -sf http://localhost:8889/metrics | head -1 && echo "✅ OTel Collector" || echo "❌ OTel Collector"

# ===== Application Services =====
curl -sf http://localhost:8001/health && echo "✅ GenAI Agent" || echo "❌ GenAI Agent"
curl -sf http://localhost:8000/health && echo "✅ ML Engine" || echo "❌ ML Engine"
curl -sf http://localhost:8080/actuator/health && echo "✅ Backend" || echo "❌ Backend"

# ===== Automation Services =====
curl -sf http://localhost:5678/healthz && echo "✅ n8n" || echo "❌ n8n"
curl -sf http://localhost:8888 && echo "✅ Activepieces" || echo "❌ Activepieces"
curl -sf http://localhost:3000/api/ping && echo "✅ Semaphore/Ansible" || echo "❌ Semaphore"

# ===== Docker SDK =====
python -c "import docker; print('✅ Docker SDK' if docker.from_env().ping() else '❌ Docker SDK')"

# ===== Runbook Engine =====
python runbooks/engine.py --validate && echo "✅ Runbooks" || echo "❌ Runbooks"

# ===== NetworkX Graph Analysis =====
curl -sf http://localhost:8000/api/graph/critical-paths && echo "✅ NetworkX" || echo "❌ NetworkX"

# ===== Alert Rules Loaded =====
RULE_COUNT=$(curl -s http://localhost:9090/api/v1/rules | python -c "import sys,json; rules=json.load(sys.stdin)['data']['groups']; print(sum(len(g['rules']) for g in rules))" 2>/dev/null)
echo "📊 Prometheus alert rules loaded: ${RULE_COUNT:-0}"
```

---

## File Index (All New & Modified Files)

### New Files Created
| # | File | Tool |
|---|------|------|
| 1 | `genai-agent/app/remediation/__init__.py` | Remediation package |
| 2 | `genai-agent/app/remediation/ansible_executor.py` | Ansible |
| 3 | `genai-agent/app/remediation/docker_healer.py` | Docker SDK |
| 4 | `genai-agent/app/remediation/k8s_healer.py` | Kubernetes |
| 5 | `genai-agent/app/telemetry.py` | OpenTelemetry |
| 6 | `ml-engine/app/telemetry.py` | OpenTelemetry |
| 7 | `ml-engine/app/api/graph_analysis.py` | NetworkX |
| 8 | `ml-engine/app/models/trend_analyzer.py` | Statsmodels |
| 9 | `ansible/playbooks/health_check.yml` | Ansible |
| 10 | `runbooks/engine.py` | Runbook Engine |
| 11 | `runbooks/schema.yml` | Runbook Engine |
| 12 | `runbooks/definitions/memory_leak.yml` | Runbook |
| 13 | `runbooks/definitions/service_crash.yml` | Runbook |
| 14 | `runbooks/definitions/disk_exhaustion.yml` | Runbook |
| 15 | `runbooks/definitions/network_degradation.yml` | Runbook |
| 16 | `runbooks/definitions/high_cpu.yml` | Runbook |
| 17 | `runbooks/definitions/cascading_failure.yml` | Runbook |
| 18 | `runbooks/definitions/database_overload.yml` | Runbook |
| 19 | `kubernetes/namespace.yml` | Kubernetes |
| 20 | `kubernetes/deployments.yml` | Kubernetes |
| 21 | `kubernetes/services.yml` | Kubernetes |
| 22 | `kubernetes/hpa.yml` | Kubernetes |
| 23 | `kubernetes/rbac.yml` | Kubernetes |
| 24 | `automation/activepieces/setup_guide.md` | Activepieces |
| 25 | `AUTOMATION_README.md` | Documentation |

### Modified Files
| # | File | Changes |
|---|------|---------|
| 1 | `genai-agent/app/graph/state_graph.py` | Added `remediation_node` to pipeline |
| 2 | `genai-agent/app/main.py` | OTel init + Activepieces webhook |
| 3 | `genai-agent/app/schemas/incident.py` | Added `remediation_result` field |
| 4 | `genai-agent/requirements.txt` | Added docker, kubernetes, OTel, PyYAML |
| 5 | `ml-engine/app/main.py` | OTel init + graph_analysis router |
| 6 | `ml-engine/requirements.txt` | Added OTel packages |
| 7 | `docker-compose.yml` | Added cadvisor, node-exporter, jaeger |
| 8 | `docker/prometheus/prometheus.yml` | Added cAdvisor + node-exporter scrape targets |
| 9 | `docker/prometheus/rules/riskops_alerts.yml` | Expanded from 2 → 22 alert rules |
| 10 | `docker/alertmanager/alertmanager.yml` | Multi-receiver severity routing |
| 11 | `docker/otel-collector/otel-collector-config.yml` | Jaeger exporter + resource attributes |
