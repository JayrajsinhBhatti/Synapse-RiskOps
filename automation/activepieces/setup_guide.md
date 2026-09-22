# Activepieces Integration Guide — Synapse RiskOps

## Overview

Activepieces complements n8n by providing additional automation workflows
focused on **ticketing**, **notifications**, and **post-remediation validation**.

| Workflow | Purpose | Trigger |
|----------|---------|---------|
| Escalation Ticket Creator | Creates Jira/Linear tickets for escalated incidents | Webhook from GenAI Agent |
| Daily Incident Digest | Summarizes last 24h incidents → Slack | Cron (daily 9 AM) |
| Post-Remediation Validator | Polls health after auto-fix, re-escalates on failure | Webhook from remediation node |
| SLA Breach Alert | Alerts when incident response time exceeds threshold | Cron (every 5 min) |

## Access

- **URL**: `http://localhost:8888`
- **Setup**: On first launch, create an admin account through the UI

## Creating the Escalation Ticket Flow

### Step 1: Create a Webhook Trigger
1. Open Activepieces → "Create Flow"
2. Add trigger: **Webhook** → copy the webhook URL
3. Set the webhook URL as `ACTIVEPIECES_WEBHOOK_URL` in `.env`

### Step 2: Add a Filter
1. Add a **Branch** piece
2. Condition: `{{trigger.body.routing_decision}}` == `escalate`

### Step 3: Add Ticket Creation
1. Add **HTTP Request** piece (or Jira/Linear piece if using their connectors)
2. Configure to POST to your ticket system's API
3. Map fields:
   - Title: `[SYNAPSE] {{trigger.body.service_name}} — {{trigger.body.predicted_failure_type}}`
   - Description: Include risk score, root cause candidates, guidance
   - Priority: Map from risk_score (>85 = Critical, >65 = High, else Medium)

### Step 4: Add Slack Notification
1. Add **Slack** piece
2. Post a summary to your incident channel

## Webhook Payload Format

The GenAI Agent sends the full `DiagnoseResponse` payload:

```json
{
  "service_name": "order-service",
  "risk_score": 87.5,
  "risk_tier": "CRITICAL",
  "prediction_confidence": 0.92,
  "predicted_failure_type": "memory_leak",
  "root_cause_candidates_ranked": [...],
  "guidance": {...},
  "routing_decision": "escalate",
  "routing_reason": "...",
  "remediation_result": null
}
```

## Environment Variable

Add to your `.env`:
```
ACTIVEPIECES_WEBHOOK_URL=http://activepieces:80/api/v1/webhooks/<your-webhook-id>
```
