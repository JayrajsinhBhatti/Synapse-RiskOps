# Automation (n8n)

Owner: Person 1 | Week 5

Exported n8n workflow JSON files, not runnable code.
- alert_routing.json  — routes alerts based on risk score / routing decision
- slack_notify.json   — Slack/email notifications
- auto_ticket.json    — automatic ticket creation for escalated incidents

Triggered via webhooks called from genai-agent/app/routing/confidence_router.py
once a routing decision is made. Import into a running n8n instance
(add an n8n service to docker-compose.yml when this is built) to reproduce.
