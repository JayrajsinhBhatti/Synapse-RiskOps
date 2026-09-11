# 🔧 Synapse RiskOps — Automation & Observability Integration Guide

> **Scope:** This guide explains **what each tool is**, **why it belongs in this project**, and **how to implement it** — covering n8n, Ansible, Alertmanager, Prometheus, and Activepieces.

---

## 📋 Table of Contents

1. [Tool Overview & Role in This Project](#1-tool-overview--role-in-this-project)
2. [Architecture: How the Tools Connect](#2-architecture-how-the-tools-connect)
3. [n8n — Workflow Automation Hub](#3-n8n--workflow-automation-hub)
4. [Prometheus — Metrics Collection & Scraping](#4-prometheus--metrics-collection--scraping)
5. [Alertmanager — Alert Routing & Deduplication](#5-alertmanager--alert-routing--deduplication)
6. [Ansible — Infrastructure Remediation Automation](#6-ansible--infrastructure-remediation-automation)
7. [Activepieces — No-Code Notification & Ticketing Glue](#7-activepieces--no-code-notification--ticketing-glue)
8. [Implementation Roadmap (Week by Week)](#8-implementation-roadmap-week-by-week)
9. [Docker Compose Changes Required](#9-docker-compose-changes-required)
10. [Environment Variables Reference](#10-environment-variables-reference)

---

## 1. Tool Overview & Role in This Project

| Tool | Category | Role in Synapse RiskOps |
|---|---|---|
| **n8n** | Workflow automation (self-hosted) | Receives routing decisions from `confidence_router.py` via webhook → triggers Ansible playbooks OR sends escalation alerts |
| **Prometheus** | Metrics scraping & storage | Scrapes metrics from all services (ml-engine, genai-agent, backend) and generates firing alerts |
| **Alertmanager** | Alert routing & deduplication | Receives Prometheus alerts → routes them into n8n's webhook endpoint for processing |
| **Ansible** | Configuration management / remediation | Executes automated remediation playbooks when the confidence router decides `auto_remediate` |
| **Activepieces** | No-code integration platform | Sends Slack DMs, creates Jira/Linear tickets, and emails the on-call engineer when routing decision is `escalate` |

> **Mental model:** `ML Engine → GenAI Agent → confidence_router → n8n → [Ansible OR Activepieces]`

---

## 2. Architecture: How the Tools Connect

```
┌──────────────────────────────────────────────────────────────────────────┐
│                        Synapse RiskOps Pipeline                          │
│                                                                          │
│  ┌─────────────┐    POST /api/risk-score    ┌──────────────────────┐     │
│  │  ml-engine  │ ◄────────────────────────► │    genai-agent       │     │
│  │  :8000      │    GET /api/graph/traverse  │    :8001             │     │
│  └─────────────┘                            │                      │     │
│         │                                   │  confidence_router   │     │
│         │ metrics exposed                   │  → routing_decision  │     │
│         ▼                                   └──────────┬───────────┘     │
│  ┌─────────────┐                                       │ POST webhook    │
│  │ Prometheus  │                                       ▼                 │
│  │  :9090      │ ─── fires alert ──► ┌─────────────────────────────┐    │
│  └─────────────┘                     │          n8n  :5678          │    │
│         │                            │                              │    │
│         ▼                            │  [IF auto_remediate]         │    │
│  ┌─────────────┐                     │    → trigger Ansible         │    │
│  │Alertmanager │ ── webhook ────────►│  [IF escalate]               │    │
│  │  :9093      │                     │    → call Activepieces        │    │
│  └─────────────┘                     └──────────────────────────────┘    │
│                                             │            │               │
│                                             ▼            ▼               │
│                                      ┌──────────┐  ┌───────────┐        │
│                                      │ Ansible  │  │Activepieces│       │
│                                      │playbooks │  │  :8888     │       │
│                                      └──────────┘  └───────────┘        │
│                                                           │              │
│                                                    Slack / Jira / Email  │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 3. n8n — Workflow Automation Hub

### What is n8n?

n8n is a **self-hostable workflow automation platform** — think Zapier but open-source and capable of running custom code. In Synapse RiskOps, n8n is the **central decision router** that bridges the AI agent's output to real-world actions.

### Why n8n in this project?

- The `confidence_router.py` already decides `auto_remediate` vs `escalate` — n8n **acts on that decision**
- The existing `automation/workflows/alert_routing.json` is the n8n workflow export placeholder (Week 5)
- n8n already has a placeholder in `docker-compose.yml` (commented out, lines 148–155)

### How to implement

#### Step 1: Uncomment n8n in docker-compose.yml

```yaml
# docker-compose.yml — add this service block
n8n:
  image: n8nio/n8n:latest
  container_name: synapse-n8n
  restart: unless-stopped
  ports:
    - "${N8N_PORT:-5678}:5678"
  environment:
    N8N_BASIC_AUTH_ACTIVE: "true"
    N8N_BASIC_AUTH_USER: ${N8N_USER:-admin}
    N8N_BASIC_AUTH_PASSWORD: ${N8N_PASSWORD:-synapse_n8n_2026}
    WEBHOOK_URL: "http://n8n:5678"
    GENERIC_TIMEZONE: "Asia/Kolkata"
  volumes:
    - n8n_data:/home/node/.n8n
    - ./automation/workflows:/home/node/workflows:ro
  networks:
    - synapse-network
```

Add `n8n_data:` under the `volumes:` section.

#### Step 2: Build the 3 core n8n workflows

These map to the existing JSON placeholders in `automation/workflows/`:

**`alert_routing.json` — Main dispatch workflow**
- **Trigger:** Webhook node at `POST /webhook/alert`
- **Input:** JSON body from `confidence_router.py` containing `routing_decision`, `risk_score`, `root_cause_candidates_ranked`
- **Logic:** IF node — check `routing_decision`
  - `auto_remediate` → HTTP Request node → Ansible AWX/Semaphore API to run playbook
  - `escalate` → HTTP Request node → Activepieces webhook

**`auto_ticket.json` — Ticket creation on escalation**
- **Trigger:** Called by `alert_routing.json` via sub-workflow or direct webhook
- **Logic:** Format incident data → POST to Jira or Linear via Activepieces
- **Data:** Uses `root_cause_candidates_ranked[0].cause` as ticket title

**`slack_notify.json` — Slack notification on escalation**
- **Trigger:** Called when routing = `escalate`
- **Logic:** Format a Slack Block Kit message with risk score, failure type, on-call link
- **Node:** Slack node or HTTP Request to Activepieces Slack flow

#### Step 3: Wire genai-agent to post to n8n

In `genai-agent/app/main.py`, after the pipeline resolves, add a background HTTP POST to n8n:

```python
import httpx, os

N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL", "http://n8n:5678/webhook/alert")

@app.post("/diagnose", response_model=DiagnoseResponse)
async def diagnose(request: DiagnoseRequest):
    # ... existing pipeline code ...
    response = DiagnoseResponse(...)

    # Fire-and-forget to n8n
    async with httpx.AsyncClient() as client:
        await client.post(N8N_WEBHOOK_URL, json=response.model_dump(), timeout=5)

    return response
```

#### Step 4: Export workflows into JSON files

Once you build the workflows in the n8n UI:
1. Open each workflow → `⋮` menu → **Download**
2. Save the JSON to `automation/workflows/alert_routing.json` etc.
3. This makes them version-controlled alongside the codebase

---

## 4. Prometheus — Metrics Collection & Scraping

### What is Prometheus?

Prometheus is a **time-series metrics database** that scrapes HTTP `/metrics` endpoints from services at a regular interval. When a metric breaches a threshold, it fires an **alert** to Alertmanager.

### Why Prometheus in this project?

- The ML Engine uses `Isolation Forest` and `Prophet` to detect anomalies from metrics — Prometheus is what **collects those metrics in production** from real services
- Provides the real-time data that drives the risk scoring pipeline
- Pairs with Alertmanager to create a production-grade observability stack

### How to implement

#### Step 1: Add Prometheus to docker-compose.yml

```yaml
prometheus:
  image: prom/prometheus:latest
  container_name: synapse-prometheus
  restart: unless-stopped
  ports:
    - "${PROMETHEUS_PORT:-9090}:9090"
  volumes:
    - ./docker/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml:ro
    - prometheus_data:/prometheus
  command:
    - '--config.file=/etc/prometheus/prometheus.yml'
    - '--storage.tsdb.retention.time=15d'
  networks:
    - synapse-network
```

#### Step 2: Create `docker/prometheus/prometheus.yml`

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

alerting:
  alertmanagers:
    - static_configs:
        - targets: ['alertmanager:9093']

rule_files:
  - /etc/prometheus/rules/*.yml

scrape_configs:
  - job_name: 'synapse-ml-engine'
    static_configs:
      - targets: ['ml-engine:8000']
    metrics_path: /metrics

  - job_name: 'synapse-genai-agent'
    static_configs:
      - targets: ['genai-agent:8001']
    metrics_path: /metrics

  - job_name: 'synapse-backend'
    static_configs:
      - targets: ['backend:8080']
    metrics_path: /actuator/prometheus

  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']
```

#### Step 3: Expose `/metrics` from Python services

Add `prometheus-fastapi-instrumentator` to `genai-agent/requirements.txt` and `ml-engine/requirements.txt`:

```python
# In app/main.py for both genai-agent and ml-engine
from prometheus_fastapi_instrumentator import Instrumentator

Instrumentator().instrument(app).expose(app)
```

#### Step 4: Create alert rules

Create `docker/prometheus/rules/riskops_alerts.yml`:

```yaml
groups:
  - name: synapse_riskops
    rules:
      - alert: HighRiskScore
        expr: synapse_risk_score > 0.85
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "High risk score detected on {{ $labels.service }}"
          description: "Risk score {{ $value }} exceeds threshold"

      - alert: MLEngineDown
        expr: up{job="synapse-ml-engine"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "ML Engine is unreachable"
```

---

## 5. Alertmanager — Alert Routing & Deduplication

### What is Alertmanager?

Alertmanager handles alerts sent by Prometheus. It **deduplicates**, **groups**, and **routes** them to the right receiver (webhook, Slack, PagerDuty, etc.). In Synapse RiskOps, its receiver is **n8n's webhook**.

### How to implement

#### Step 1: Add Alertmanager to docker-compose.yml

```yaml
alertmanager:
  image: prom/alertmanager:latest
  container_name: synapse-alertmanager
  restart: unless-stopped
  ports:
    - "${ALERTMANAGER_PORT:-9093}:9093"
  volumes:
    - ./docker/alertmanager/alertmanager.yml:/etc/alertmanager/alertmanager.yml:ro
  networks:
    - synapse-network
```

#### Step 2: Create `docker/alertmanager/alertmanager.yml`

```yaml
global:
  resolve_timeout: 5m

route:
  receiver: 'n8n-webhook'
  group_by: ['alertname', 'service']
  group_wait: 10s
  group_interval: 5m
  repeat_interval: 1h

  routes:
    - match:
        severity: critical
      receiver: 'n8n-webhook'
      continue: true

receivers:
  - name: 'n8n-webhook'
    webhook_configs:
      - url: 'http://n8n:5678/webhook/prometheus-alert'
        send_resolved: true

inhibit_rules:
  - source_match:
      severity: 'critical'
    target_match:
      severity: 'warning'
    equal: ['alertname', 'service']
```

#### Step 3: Add a second n8n workflow for Prometheus alerts

Create a new workflow in n8n:
- **Trigger:** Webhook at `POST /webhook/prometheus-alert`
- **Logic:** Parse Prometheus alert payload → transform into the same format as `DiagnoseResponse` → hand off to `alert_routing.json` sub-workflow

> **Note:** This is distinct from the genai-agent webhook — Prometheus alerts are raw metric threshold breaches, not AI-diagnosed incidents.

---

## 6. Ansible — Infrastructure Remediation Automation

### What is Ansible?

Ansible is an **agentless IT automation tool** that executes YAML "playbooks" over SSH. In Synapse RiskOps, Ansible is triggered by n8n when the confidence router decides `auto_remediate` — it actually **fixes the problem** on the target server.

### How to implement

#### Step 1: Choose an Ansible control plane

For a dockerized setup, use **Ansible Semaphore** (open-source Ansible UI with an API):

```yaml
# Add to docker-compose.yml
semaphore:
  image: semaphoreui/semaphore:latest
  container_name: synapse-semaphore
  restart: unless-stopped
  ports:
    - "${SEMAPHORE_PORT:-3000}:3000"
  environment:
    SEMAPHORE_DB_DIALECT: bolt
    SEMAPHORE_ADMIN: ${SEMAPHORE_ADMIN:-admin}
    SEMAPHORE_ADMIN_PASSWORD: ${SEMAPHORE_ADMIN_PASSWORD:-synapse_semaphore_2026}
    SEMAPHORE_ADMIN_EMAIL: ${SEMAPHORE_ADMIN_EMAIL:-admin@synapse.local}
  volumes:
    - semaphore_data:/var/lib/semaphore
    - ./ansible/playbooks:/home/semaphore/playbooks:ro
  networks:
    - synapse-network
```

#### Step 2: Create remediation playbooks

Create the `ansible/playbooks/` directory:

**`ansible/playbooks/restart_service.yml`** — Restart a failing service
```yaml
---
- name: Restart failing service
  hosts: "{{ target_host }}"
  become: yes
  vars:
    service_name: "{{ failing_service }}"
  tasks:
    - name: Restart systemd service
      ansible.builtin.systemd:
        name: "{{ service_name }}"
        state: restarted

    - name: Verify service is running
      ansible.builtin.systemd:
        name: "{{ service_name }}"
      register: service_status
      failed_when: service_status.status.ActiveState != "active"
```

**`ansible/playbooks/scale_resources.yml`** — Scale container resources
```yaml
---
- name: Scale container CPU/memory limits
  hosts: "{{ target_host }}"
  become: yes
  tasks:
    - name: Update docker-compose resource limits
      community.docker.docker_compose_v2:
        project_src: /opt/synapse-riskops
        services: ["{{ failing_service }}"]
      environment:
        COMPOSE_MEMORY_LIMIT: "{{ new_memory_limit }}"
```

**`ansible/playbooks/clear_disk.yml`** — Clear disk space
```yaml
---
- name: Free disk space on target host
  hosts: "{{ target_host }}"
  become: yes
  tasks:
    - name: Remove old Docker images
      community.docker.docker_prune:
        images: yes
        images_filters:
          dangling: false
          until: 24h

    - name: Truncate old log files
      ansible.builtin.shell: find /var/log -name "*.log" -mtime +7 -exec truncate -s 0 {} \;
```

#### Step 3: Wire n8n to trigger Ansible via Semaphore API

In the n8n `alert_routing.json` workflow, add an **HTTP Request node** for `auto_remediate` path:

```
POST http://semaphore:3000/api/project/{project_id}/tasks
Authorization: Bearer {SEMAPHORE_API_TOKEN}
Content-Type: application/json

{
  "template_id": 1,
  "extra_vars": {
    "target_host": "{{ $json.service_name }}",
    "failing_service": "{{ $json.predicted_failure_type }}"
  }
}
```

#### Step 4: Map failure types to playbooks

Create a lookup in n8n using a **Switch node** based on `predicted_failure_type` from `confidence_router.py`:

| `predicted_failure_type` | Ansible Playbook Template |
|---|---|
| `memory_leak` | `scale_resources.yml` |
| `service_crash` | `restart_service.yml` |
| `disk_exhaustion` | `clear_disk.yml` |
| `network_degradation` | `restart_service.yml` |

---

## 7. Activepieces — No-Code Notification & Ticketing Glue

### What is Activepieces?

Activepieces is an **open-source no-code automation platform** (similar to Make.com / Zapier) that can be self-hosted. In Synapse RiskOps, it handles the **human-facing notifications** when the confidence router decides `escalate` — creating Jira tickets, sending Slack DMs, and emailing on-call engineers.

### How to implement

#### Step 1: Add Activepieces to docker-compose.yml

```yaml
activepieces:
  image: activepieces/activepieces:latest
  container_name: synapse-activepieces
  restart: unless-stopped
  ports:
    - "${ACTIVEPIECES_PORT:-8888}:80"
  environment:
    AP_POSTGRES_DATABASE: activepieces
    AP_POSTGRES_HOST: postgres
    AP_POSTGRES_PORT: 5432
    AP_POSTGRES_USERNAME: ${POSTGRES_USER:-synapse_admin}
    AP_POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-synapse_dev_2026}
    AP_JWT_SECRET: ${AP_JWT_SECRET:-activepieces_jwt_secret_change_me}
    AP_FRONTEND_URL: "http://localhost:8888"
  depends_on:
    - postgres
  networks:
    - synapse-network
```

#### Step 2: Create flows in the Activepieces UI

**Flow 1: Escalation Slack Alert**
```
Trigger: Webhook (n8n posts here when routing_decision = escalate)
  ↓
Step 1: Format message
  — service_name, risk_score, routing_reason, top RCA candidate
  ↓
Step 2: Slack → Send Message to #incidents channel
  — "🚨 Escalation: {{ service_name }} | Risk: {{ risk_score }}
     RCA: {{ root_cause }} ({{ confidence }}% confidence)
     Reason: {{ routing_reason }}"
  ↓
Step 3: Slack → Send DM to on-call engineer
```

**Flow 2: Jira Ticket Creation**
```
Trigger: Webhook (same trigger as Flow 1, or sub-flow from n8n)
  ↓
Step 1: Jira → Create Issue
  — Project: OPS
  — Summary: "[SYNAPSE] {{ predicted_failure_type }} on {{ service_name }}"
  — Description: Full DiagnoseResponse JSON formatted as table
  — Priority: based on risk_tier (critical/high → P1, medium → P2)
  — Labels: auto-remediation-declined, synapse-riskops
  ↓
Step 2: HTTP Request → POST to backend /api/incidents
  — Create incident record in PostgreSQL via Spring Boot API
```

**Flow 3: Email On-Call**
```
Trigger: Webhook (for high-severity escalations only)
  ↓
Step 1: Filter — risk_score >= 0.9 only
  ↓
Step 2: Gmail / SMTP → Send Email
  — To: on-call engineer email
  — Subject: "🔴 CRITICAL: {{ service_name }} failure predicted in {{ prediction_horizon_minutes }}min"
  — Body: HTML-formatted incident report
```

#### Step 3: Get the Activepieces webhook URLs and add them to n8n

After creating each flow in Activepieces UI:
1. Click on the Webhook trigger → copy the webhook URL
2. In n8n's `slack_notify.json` and `auto_ticket.json` workflows, replace the placeholder URLs with the real Activepieces webhook URLs

---

## 8. Implementation Roadmap (Week by Week)

| Week | Work |
|---|---|
| **Week 4** (current) | Confidence router is working (`confidence_router.py`) — this is the prerequisite |
| **Week 5** | Add n8n to docker-compose; build `alert_routing.json` workflow; wire `genai-agent/app/main.py` to POST to n8n webhook |
| **Week 5** | Add Prometheus + Alertmanager; expose `/metrics` from `ml-engine` and `genai-agent` |
| **Week 6** | Set up Activepieces; build Slack alert and Jira ticket flows; wire from n8n |
| **Week 6** | Set up Ansible Semaphore; create 3 core remediation playbooks; map failure types to playbooks in n8n |
| **Week 7** | End-to-end test: submit a high-confidence incident → verify Ansible runs OR Activepieces fires |
| **Week 7** | Tune confidence thresholds using `evaluation/backtest.py` |

---

## 9. Docker Compose Changes Required

Add these volumes to the existing `volumes:` block in `docker-compose.yml`:

```yaml
volumes:
  postgres_data:
    driver: local
  ml_model_data:
    driver: local
  # --- NEW ---
  n8n_data:
    driver: local
  prometheus_data:
    driver: local
  semaphore_data:
    driver: local
```

New directories to add to the repo:

```
synapse-riskops/
├── docker/
│   ├── postgres/init.sql           (exists)
│   ├── prometheus/
│   │   ├── prometheus.yml          ← NEW
│   │   └── rules/
│   │       └── riskops_alerts.yml  ← NEW
│   └── alertmanager/
│       └── alertmanager.yml        ← NEW
├── ansible/
│   ├── playbooks/
│   │   ├── restart_service.yml     ← NEW
│   │   ├── scale_resources.yml     ← NEW
│   │   └── clear_disk.yml          ← NEW
│   └── inventory/
│       └── hosts.yml               ← NEW
└── automation/
    └── workflows/
        ├── alert_routing.json      (exists — placeholder, fill in)
        ├── auto_ticket.json        (exists — placeholder, fill in)
        └── slack_notify.json       (exists — placeholder, fill in)
```

---

## 10. Environment Variables Reference

Add these to your `.env` file:

```bash
# n8n
N8N_PORT=5678
N8N_USER=admin
N8N_PASSWORD=synapse_n8n_2026
N8N_WEBHOOK_URL=http://n8n:5678/webhook/alert

# Prometheus
PROMETHEUS_PORT=9090

# Alertmanager
ALERTMANAGER_PORT=9093

# Ansible Semaphore
SEMAPHORE_PORT=3000
SEMAPHORE_ADMIN=admin
SEMAPHORE_ADMIN_PASSWORD=synapse_semaphore_2026
SEMAPHORE_ADMIN_EMAIL=admin@synapse.local
SEMAPHORE_API_TOKEN=   # get this from the Semaphore UI after first login

# Activepieces
ACTIVEPIECES_PORT=8888
AP_JWT_SECRET=activepieces_jwt_secret_change_me_64chars

# Notification targets (used in Activepieces flows)
SLACK_BOT_TOKEN=
SLACK_INCIDENTS_CHANNEL=#incidents
ONCALL_EMAIL=
JIRA_PROJECT_KEY=OPS
JIRA_URL=
JIRA_EMAIL=
JIRA_API_TOKEN=
```

---

## 🔗 Quick Reference: Port Map

| Service | Port | UI / Docs |
|---|---|---|
| React Dashboard | 5173 | http://localhost:5173 |
| Spring Boot API | 8080 | http://localhost:8080/swagger-ui.html |
| ML Engine | 8000 | http://localhost:8000/docs |
| GenAI Agent | 8001 | http://localhost:8001/docs |
| **n8n** | **5678** | **http://localhost:5678** |
| **Prometheus** | **9090** | **http://localhost:9090** |
| **Alertmanager** | **9093** | **http://localhost:9093** |
| **Semaphore (Ansible)** | **3000** | **http://localhost:3000** |
| **Activepieces** | **8888** | **http://localhost:8888** |

---

*Last updated: Week 4 / Sept 2026 — Synapse RiskOps Person 1 implementation guide*
