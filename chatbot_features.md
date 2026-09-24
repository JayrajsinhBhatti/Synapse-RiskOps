# 🤖 Synapse RiskOps — Chatbot Feature Blueprint

> A chatbot for this project is an **Ops Control Plane interface** — the single pane of glass where an on-call engineer talks to the system in natural language instead of switching between dashboards, terminals, and runbooks.

---

## 🟢 Basic Features (Must-Have Core)

These are the table-stakes features that make the chatbot usable at all.

### 1. Service Health Query
> *"How is payment-service doing?"*

- Calls [ml-engine](file:///e:/Users/Jayraj/synapse-riskops/ml-engine) `POST /api/risk-score` for the requested service
- Returns: risk score, risk tier, predicted failure type, prediction horizon
- Renders the response in a clean, readable card format

### 2. On-Demand Diagnosis Trigger
> *"Diagnose auth-service"*

- Calls [genai-agent `/diagnose`](file:///e:/Users/Jayraj/synapse-riskops/genai-agent/app/main.py#L62-L123) with the service's current metrics + recent logs
- Returns the full `DiagnoseResponse`: RCA candidates, guidance, routing decision
- This is the chatbot's core action — everything else extends from it

### 3. Incident List & Lookup
> *"Show me open incidents"* / *"Details on INC-4821"*

- Queries the [Spring Boot backend](file:///e:/Users/Jayraj/synapse-riskops/backend) incident CRUD API
- Lists recent incidents with status, severity, assigned engineer
- Drill-down into a specific incident by ID

### 4. Alert Summary
> *"What alerts are firing right now?"*

- Queries Alertmanager (`GET /api/v2/alerts`) for currently active alerts
- Groups by severity, shows which services are affected
- Provides a count summary: *"3 critical, 7 warning, 2 info"*

### 5. Routing Decision Explanation
> *"Why was the last incident auto-remediated?"* / *"Why did it escalate?"*

- Retrieves the `routing_decision` and `routing_reason` from the most recent [confidence_router](file:///e:/Users/Jayraj/synapse-riskops/genai-agent/app/routing/confidence_router.py) output
- Explains the ML confidence vs. RCA confidence thresholds in plain English
- Helps engineers understand *why* the system acted the way it did

### 6. Guidance Retrieval
> *"What should I do about the disk_exhaustion on db-primary?"*

- Pulls the `guidance` block from [proactive_guidance_generator](file:///e:/Users/Jayraj/synapse-riskops/genai-agent/app/agents/proactive_guidance_generator.py) output
- Presents `immediate_actions` as a numbered checklist
- Shows `preventive_measures` separately for longer-term fixes

### 7. Conversation Memory (Session Context)
- Remembers which service/incident the user is talking about within a session
- Allows follow-up questions: *"What about its dependencies?"* without repeating service name
- Resets context on explicit *"new conversation"* or timeout

---

## 🟡 Intermediate Features (High-Value Differentiation)

These features make the chatbot genuinely useful for day-to-day ops beyond just being a query wrapper.

### 8. Dependency Graph Explorer
> *"What services depend on payment-service?"* / *"Show me the blast radius"*

- Calls ml-engine `GET /api/graph/traverse?service_name=...`
- Renders upstream/downstream dependencies as a text-based tree or graph
- Highlights services that are currently unhealthy (cross-references with risk scores)

### 9. Remediation Status Tracker
> *"Did the auto-remediation work?"* / *"What's the status of the restart?"*

- Queries the [remediation_result](file:///e:/Users/Jayraj/synapse-riskops/genai-agent/app/graph/state_graph.py#L71-L149) from the most recent pipeline run
- If [Docker healer](file:///e:/Users/Jayraj/synapse-riskops/genai-agent/app/remediation/docker_healer.py) was used → shows container restart status
- If [Ansible executor](file:///e:/Users/Jayraj/synapse-riskops/genai-agent/app/remediation/ansible_executor.py) was used → shows playbook execution status
- Shows SUCCESS / FAILED / SKIPPED with error details

### 10. Manual Remediation Trigger (with Confirmation)
> *"Restart the payment-service container"* / *"Run the clear_disk playbook on db-primary"*

- Parses the intent → maps to a specific [Ansible playbook](file:///e:/Users/Jayraj/synapse-riskops/ansible/playbooks) or Docker action
- **Always asks for confirmation before executing**: *"I'll restart payment-service via Docker. Confirm? [Yes/No]"*
- Logs the action with the engineer's identity for audit trail

### 11. Metric Snapshot & Comparison
> *"What are the current metrics for api-gateway?"* / *"Compare payment-service CPU now vs 1 hour ago"*

- Queries Prometheus `query` and `query_range` endpoints for service metrics
- Shows key vitals: CPU, memory, disk I/O, error rate, p99 latency
- Comparison mode: side-by-side current vs. historical values

### 12. Alert Silencing
> *"Silence the HighRiskScore alert for payment-service for 2 hours"*

- Creates an Alertmanager silence via `POST /api/v2/silences`
- Requires the user to provide a reason (audit compliance)
- Shows active silences on request: *"What silences are active?"*

### 13. Incident Timeline
> *"Show me the timeline for INC-4821"*

- Aggregates events from multiple sources for a single incident:
  - When the alert fired (Alertmanager)
  - When the diagnosis ran (genai-agent)
  - What routing decision was made (confidence_router)
  - Whether remediation ran (remediation_node)
  - Whether it was escalated (Activepieces/Slack/Jira)
- Presents as a chronological event log

### 14. Threshold Tuning Helper
> *"What happens if we lower the auto-remediation threshold to 0.75?"*

- Shows the current [ML_CONFIDENCE_THRESHOLD and RCA_CONFIDENCE_THRESHOLD](file:///e:/Users/Jayraj/synapse-riskops/genai-agent/app/routing/confidence_router.py#L15-L16)
- Runs a hypothetical: if the user's proposed thresholds were active, how many of the last N incidents would have been auto-remediated vs. escalated
- Uses [evaluation/backtest.py](file:///e:/Users/Jayraj/synapse-riskops/evaluation) data for this analysis

### 15. Runbook Lookup
> *"What's the runbook for memory_leak?"*

- Looks up the matching [runbook definition](file:///e:/Users/Jayraj/synapse-riskops/runbooks/definitions) for a given failure type
- Shows the step-by-step playbook that would be executed
- Indicates whether it would be auto-executed or needs manual approval

---

## 🔴 Advanced Features (Showcase / Differentiator)

These are the features that make the chatbot a **standout** in a capstone demo.

### 16. Natural Language Incident Creation
> *"Create a P1 incident for payment-service: database connection pool exhaustion causing 504s"*

- Parses severity, service, title, and description from free-form text
- Creates the incident in the [Spring Boot backend](file:///e:/Users/Jayraj/synapse-riskops/backend) via API
- Simultaneously creates a Jira ticket via Activepieces/n8n
- Responds with incident ID and Jira link

### 17. Multi-Service Diagnosis
> *"Something's wrong with the checkout flow — diagnose all services involved"*

- User describes a *symptom* rather than a specific service
- Chatbot identifies related services from the dependency graph
- Runs `/diagnose` against each service in the dependency chain
- Correlates results: *"payment-service (risk: 0.92, critical) is the root cause; api-gateway and frontend are downstream victims"*

### 18. Proactive Alert Digest
> *(Triggered on schedule or on-demand)* *"Give me the morning briefing"*

- Aggregates overnight activity:
  - Alerts that fired and resolved
  - Auto-remediations that ran (and their outcomes)
  - Incidents that were escalated and are still open
  - Services whose risk score has been trending upward
- Formatted as a concise executive summary

### 19. Post-Incident Review Generator
> *"Generate a post-mortem for INC-4821"*

- Pulls the full incident data: timeline, RCA, remediation actions, resolution
- Uses Gemini to generate a structured post-mortem document:
  - What happened
  - Root cause
  - Impact (services affected, duration)
  - What was done (auto-remediation + manual steps)
  - Action items to prevent recurrence
- Outputs as Markdown that can be pasted into Confluence/Notion

### 20. Feedback Loop Integration
> *"The RCA for INC-4821 was wrong — the actual cause was a DNS misconfiguration"*

- Feeds correction back into the [feedback_loop.py](file:///e:/Users/Jayraj/synapse-riskops/genai-agent/app/feedback/feedback_loop.py)
- Records the ground truth label against the pipeline's prediction
- Over time, this data feeds into threshold tuning and model retraining

### 21. What-If Scenario Simulation
> *"What would happen if db-primary goes down?"*

- Traverses the dependency graph starting from the specified service
- Lists all downstream services that would be impacted
- Estimates risk score escalation based on historical patterns
- Shows which remediation playbooks would trigger and for which services

### 22. On-Call Handoff Summary
> *"Generate a handoff summary for the next on-call"*

- Summarizes the current state of all services
- Lists open incidents with their current status
- Highlights anything that needs attention
- Formatted for pasting into Slack or email

### 23. Smart Escalation with Context Packaging
> *"Escalate this to the database team"*

- Packages the full context: diagnosis, RCA, metrics, logs, guidance
- Routes to the appropriate team's Slack channel / Jira project via Activepieces
- Includes a suggested priority based on risk score
- Avoids the "alert fatigue" problem by providing curated, actionable context rather than raw data

### 24. Conversational Workflow Orchestration
> *"Run the full incident response for api-gateway"*

- Orchestrates a multi-step workflow through conversation:
  1. Diagnose → show results
  2. *"Should I proceed with auto-remediation?"* → confirmation
  3. Execute remediation → show results
  4. *"Remediation succeeded. Should I close the incident?"*
  5. Close incident → update Jira
- Each step waits for user confirmation — the chatbot acts as a guided co-pilot

---

## 📊 Feature Map by Data Source

| Data Source | Features It Powers |
|---|---|
| [ml-engine `/api/risk-score`](file:///e:/Users/Jayraj/synapse-riskops/ml-engine) | #1, #11, #17, #18, #21 |
| [genai-agent `/diagnose`](file:///e:/Users/Jayraj/synapse-riskops/genai-agent/app/main.py) | #2, #5, #6, #17 |
| [confidence_router](file:///e:/Users/Jayraj/synapse-riskops/genai-agent/app/routing/confidence_router.py) | #5, #14 |
| [Spring Boot backend](file:///e:/Users/Jayraj/synapse-riskops/backend) | #3, #13, #16 |
| Prometheus | #4, #11, #18 |
| Alertmanager | #4, #12, #18 |
| [Dependency graph](file:///e:/Users/Jayraj/synapse-riskops/ml-engine) | #8, #17, #21 |
| [Remediation (Docker/Ansible)](file:///e:/Users/Jayraj/synapse-riskops/genai-agent/app/remediation) | #9, #10, #24 |
| [Runbooks](file:///e:/Users/Jayraj/synapse-riskops/runbooks) | #10, #15 |
| [Feedback loop](file:///e:/Users/Jayraj/synapse-riskops/genai-agent/app/feedback/feedback_loop.py) | #20 |
| Activepieces / n8n | #16, #23 |
| [Evaluation / backtest](file:///e:/Users/Jayraj/synapse-riskops/evaluation) | #14 |

---

## 🏗️ Recommended Implementation Priority

```
Phase 1 (MVP — get it working):
  #1 Service Health Query
  #2 On-Demand Diagnosis
  #3 Incident List & Lookup
  #4 Alert Summary
  #7 Conversation Memory

Phase 2 (Make it useful):
  #5 Routing Decision Explanation
  #6 Guidance Retrieval
  #8 Dependency Graph Explorer
  #9 Remediation Status Tracker
  #15 Runbook Lookup

Phase 3 (Demo-worthy):
  #10 Manual Remediation Trigger
  #13 Incident Timeline
  #17 Multi-Service Diagnosis
  #18 Proactive Alert Digest
  #24 Conversational Workflow Orchestration

Phase 4 (Wow factor):
  #16 Natural Language Incident Creation
  #19 Post-Incident Review Generator
  #20 Feedback Loop Integration
  #21 What-If Scenario Simulation
  #22 On-Call Handoff Summary
```
