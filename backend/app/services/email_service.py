"""
Synapse RiskOps - Gmail SMTP Email Notification Service
========================================================
Handles automated email dispatching to administrators and on-call engineers
via Gmail SMTP (smtp.gmail.com) when service failure incidents occur.

Default Sender: spareid9687@gmail.com
Default Admin / Recipient: jayrajsinhbhatti9687@gmail.com
"""

import asyncio
import logging
import os
import smtplib
import ssl
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate, make_msgid
from typing import Any, Dict, Optional

from app.core.config import settings

logger = logging.getLogger("synapse.email")


class EmailService:
    """Manages SMTP connection to Gmail and formatting of incident alert emails."""

    def __init__(
        self,
        smtp_host: Optional[str] = None,
        smtp_port: Optional[int] = None,
        sender_email: Optional[str] = None,
        sender_password: Optional[str] = None,
        admin_email: Optional[str] = None,
        use_tls: Optional[bool] = None,
        enabled: Optional[bool] = None,
    ):
        self._smtp_host = smtp_host
        self._smtp_port = smtp_port
        self._sender_email = sender_email
        self._sender_password = sender_password
        self._admin_email = admin_email
        self._use_tls = use_tls
        self._enabled = enabled

    @property
    def smtp_host(self) -> str:
        return self._smtp_host or getattr(settings, "SMTP_HOST", "smtp.gmail.com")

    @property
    def smtp_port(self) -> int:
        return self._smtp_port or getattr(settings, "SMTP_PORT", 587)

    @property
    def sender_email(self) -> str:
        if self._sender_email is not None:
            return self._sender_email
        return (
            getattr(settings, "SMTP_USER", None)
            or os.getenv("SMTP_USER")
            or "spareid9687@gmail.com"
        )

    @property
    def sender_password(self) -> str:
        if self._sender_password is not None:
            raw = self._sender_password
        else:
            raw = (
                getattr(settings, "SMTP_PASSWORD", None)
                or getattr(settings, "GMAIL_APP_PASSWORD", None)
                or os.getenv("SMTP_PASSWORD")
                or os.getenv("GMAIL_APP_PASSWORD")
                or ""
            )
        return raw.replace(" ", "").strip() if raw else ""

    @property
    def admin_email(self) -> str:
        if self._admin_email is not None:
            return self._admin_email
        return (
            getattr(settings, "ADMIN_EMAIL", None)
            or os.getenv("ADMIN_EMAIL")
            or "jayrajsinhbhatti9687@gmail.com"
        )

    @property
    def use_tls(self) -> bool:
        if self._use_tls is not None:
            return self._use_tls
        return getattr(settings, "SMTP_USE_TLS", True)

    @property
    def enabled(self) -> bool:
        if self._enabled is not None:
            return self._enabled
        return getattr(settings, "EMAIL_NOTIFICATIONS_ENABLED", True)

    def is_configured(self) -> bool:
        """Returns True if sender credentials and recipient are configured."""
        return bool(self.sender_email and self.sender_password and self.admin_email)

    def _build_incident_html(self, data: Dict[str, Any]) -> str:
        """Construct a responsive, sleek HTML email template for incident alerting."""
        service_name = data.get("service_name", "Unknown Service")
        incident_id = data.get("incident_id", "N/A")
        severity = data.get("severity", "CRITICAL").upper()
        risk_score = float(data.get("risk_score", 0.0))
        failure_type = str(data.get("failure_type", "latency_degradation")).replace("_", " ").title()
        root_cause = data.get("root_cause", service_name)
        ml_confidence = float(data.get("ml_confidence", 0.0)) * 100.0 if float(data.get("ml_confidence", 0.0)) <= 1.0 else float(data.get("ml_confidence", 0.0))
        rca_confidence = float(data.get("rca_confidence", 0.0)) * 100.0 if float(data.get("rca_confidence", 0.0)) <= 1.0 else float(data.get("rca_confidence", 0.0))
        guidance = data.get("guidance", "Telemetry anomalies detected. Immediate triage recommended.")
        routing_decision = str(data.get("routing_decision", "human_approval")).replace("_", " ").title()
        timestamp = data.get("timestamp", datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"))
        metrics = data.get("metrics", {})

        # Color mapping by severity
        sev_color = "#ef4444" if severity == "CRITICAL" else "#f97316" if severity == "HIGH" else "#eab308"
        bg_accent = "#1e1b4b" if severity == "CRITICAL" else "#311802" if severity == "HIGH" else "#2e2103"

        metrics_rows = ""
        if isinstance(metrics, dict) and metrics:
            for k, v in list(metrics.items())[:8]:
                formatted_v = f"{v:.2f}" if isinstance(v, (float, int)) else str(v)
                metrics_rows += f"""
                <tr>
                    <td style="padding: 6px 12px; font-family: monospace; font-size: 13px; color: #94a3b8; border-bottom: 1px solid #334155;">{k}</td>
                    <td style="padding: 6px 12px; font-family: monospace; font-size: 13px; font-weight: bold; color: #f8fafc; text-align: right; border-bottom: 1px solid #334155;">{formatted_v}</td>
                </tr>
                """
        else:
            metrics_rows = """
            <tr>
                <td colspan="2" style="padding: 8px 12px; font-size: 13px; color: #94a3b8; text-align: center;">No specific telemetry metrics attached.</td>
            </tr>
            """

        dashboard_url = f"http://localhost:5173/dashboard?incident_id={incident_id}"

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Incident Alert: {service_name}</title>
</head>
<body style="margin: 0; padding: 0; background-color: #0b0f19; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #f1f5f9;">
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background-color: #0b0f19; padding: 24px 0;">
        <tr>
            <td align="center">
                <table role="presentation" width="100%" style="max-width: 620px; background: #131b2e; border: 1px solid #28354f; border-radius: 14px; overflow: hidden; box-shadow: 0 10px 30px rgba(0,0,0,0.5);" cellspacing="0" cellpadding="0">
                    
                    <!-- Header Banner -->
                    <tr>
                        <td style="background: linear-gradient(135deg, {bg_accent} 0%, #0f172a 100%); padding: 24px 30px; border-bottom: 2px solid {sev_color};">
                            <table width="100%" cellspacing="0" cellpadding="0">
                                <tr>
                                    <td>
                                        <div style="font-size: 11px; letter-spacing: 1.5px; text-transform: uppercase; font-weight: bold; color: {sev_color}; margin-bottom: 4px;">
                                            SYNAPSE RISKOPS • PREDICTIVE ALERT
                                        </div>
                                        <h1 style="margin: 0; font-size: 22px; font-weight: 800; color: #ffffff;">
                                            Service Failure Predicted: <span style="color: #38bdf8;">{service_name}</span>
                                        </h1>
                                    </td>
                                    <td align="right" valign="top">
                                        <span style="display: inline-block; padding: 6px 14px; background: {sev_color}; color: #ffffff; font-size: 12px; font-weight: 800; border-radius: 9999px; letter-spacing: 0.5px;">
                                            {severity}
                                        </span>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>

                    <!-- Body Content -->
                    <tr>
                        <td style="padding: 24px 30px;">
                            
                            <!-- Key Incident Snapshot -->
                            <table width="100%" cellspacing="0" cellpadding="0" style="margin-bottom: 20px; background: #1a243b; border-radius: 10px; border: 1px solid #2d3b5b; padding: 16px;">
                                <tr>
                                    <td width="50%" style="padding: 8px 12px; vertical-align: top;">
                                        <div style="font-size: 11px; color: #94a3b8; text-transform: uppercase; font-weight: 600;">Predicted Failure Type</div>
                                        <div style="font-size: 15px; font-weight: 700; color: #f8fafc; margin-top: 2px;">{failure_type}</div>
                                    </td>
                                    <td width="50%" style="padding: 8px 12px; vertical-align: top;">
                                        <div style="font-size: 11px; color: #94a3b8; text-transform: uppercase; font-weight: 600;">Composite Risk Score</div>
                                        <div style="font-size: 16px; font-weight: 800; color: {sev_color}; margin-top: 2px;">{risk_score:.1f}%</div>
                                    </td>
                                </tr>
                                <tr>
                                    <td width="50%" style="padding: 8px 12px; vertical-align: top;">
                                        <div style="font-size: 11px; color: #94a3b8; text-transform: uppercase; font-weight: 600;">Root Cause Service</div>
                                        <div style="font-size: 14px; font-weight: 600; color: #38bdf8; margin-top: 2px;">{root_cause}</div>
                                    </td>
                                    <td width="50%" style="padding: 8px 12px; vertical-align: top;">
                                        <div style="font-size: 11px; color: #94a3b8; text-transform: uppercase; font-weight: 600;">ML / RCA Confidence</div>
                                        <div style="font-size: 14px; font-weight: 600; color: #f8fafc; margin-top: 2px;">{ml_confidence:.1f}% / {rca_confidence:.1f}%</div>
                                    </td>
                                </tr>
                                <tr>
                                    <td width="50%" style="padding: 8px 12px; vertical-align: top;">
                                        <div style="font-size: 11px; color: #94a3b8; text-transform: uppercase; font-weight: 600;">Routing Decision</div>
                                        <div style="font-size: 13px; font-weight: 600; color: #a7f3d0; margin-top: 2px;">{routing_decision}</div>
                                    </td>
                                    <td width="50%" style="padding: 8px 12px; vertical-align: top;">
                                        <div style="font-size: 11px; color: #94a3b8; text-transform: uppercase; font-weight: 600;">Detection Time</div>
                                        <div style="font-size: 12px; font-weight: 500; color: #cbd5e1; margin-top: 2px;">{timestamp}</div>
                                    </td>
                                </tr>
                            </table>

                            <!-- AI RCA & Guidance -->
                            <div style="margin-bottom: 20px; background: #0f172a; border-left: 4px solid #6366f1; border-radius: 4px; padding: 14px 18px;">
                                <div style="font-size: 12px; font-weight: 700; color: #818cf8; text-transform: uppercase; margin-bottom: 4px;">
                                    AI Root Cause Guidance
                                </div>
                                <div style="font-size: 13px; line-height: 1.5; color: #e2e8f0;">
                                    {guidance}
                                </div>
                            </div>

                            <!-- Telemetry Metrics Snapshot -->
                            <div style="font-size: 12px; font-weight: 700; color: #94a3b8; text-transform: uppercase; margin-bottom: 8px; letter-spacing: 0.5px;">
                                Telemetry Metrics Snapshot
                            </div>
                            <table width="100%" cellspacing="0" cellpadding="0" style="margin-bottom: 24px; background: #0f172a; border-radius: 8px; border: 1px solid #1e293b; border-collapse: collapse;">
                                {metrics_rows}
                            </table>

                            <!-- Primary CTA Button -->
                            <table width="100%" cellspacing="0" cellpadding="0">
                                <tr>
                                    <td align="center" style="padding: 8px 0 16px 0;">
                                        <a href="{dashboard_url}" target="_blank" style="display: inline-block; background: linear-gradient(135deg, #4f46e5 0%, #2563eb 100%); color: #ffffff; text-decoration: none; font-size: 14px; font-weight: 700; padding: 12px 28px; border-radius: 8px; box-shadow: 0 4px 14px rgba(79, 70, 229, 0.4);">
                                            Open Incident in RiskOps Dashboard &rarr;
                                        </a>
                                    </td>
                                </tr>
                            </table>

                            <div style="font-size: 11px; color: #64748b; text-align: center; margin-top: 8px;">
                                Incident ID: <span style="font-family: monospace;">{incident_id}</span>
                            </div>

                        </td>
                    </tr>

                    <!-- Footer -->
                    <tr>
                        <td style="padding: 16px 30px; background: #0c1220; border-top: 1px solid #1e293b; text-align: center;">
                            <div style="font-size: 11px; color: #64748b; line-height: 1.5;">
                                This is an automated priority alert sent by <strong>Synapse RiskOps</strong>.<br>
                                Sender: <span style="font-family: monospace; color: #94a3b8;">{self.sender_email}</span> &bull; 
                                Admin: <span style="font-family: monospace; color: #94a3b8;">{self.admin_email}</span>
                            </div>
                        </td>
                    </tr>

                </table>
            </td>
        </tr>
    </table>
</body>
</html>
"""

    def _build_incident_text(self, data: Dict[str, Any]) -> str:
        """Construct a clean plain text fallback for email clients without HTML."""
        service_name = data.get("service_name", "Unknown Service")
        incident_id = data.get("incident_id", "N/A")
        severity = data.get("severity", "CRITICAL").upper()
        risk_score = float(data.get("risk_score", 0.0))
        failure_type = str(data.get("failure_type", "latency_degradation")).replace("_", " ").title()
        root_cause = data.get("root_cause", service_name)
        ml_confidence = float(data.get("ml_confidence", 0.0)) * 100.0 if float(data.get("ml_confidence", 0.0)) <= 1.0 else float(data.get("ml_confidence", 0.0))
        rca_confidence = float(data.get("rca_confidence", 0.0)) * 100.0 if float(data.get("rca_confidence", 0.0)) <= 1.0 else float(data.get("rca_confidence", 0.0))
        guidance = data.get("guidance", "Telemetry anomalies detected. Immediate triage recommended.")
        routing_decision = str(data.get("routing_decision", "human_approval")).replace("_", " ").title()
        timestamp = data.get("timestamp", datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"))
        metrics = data.get("metrics", {})

        metrics_str = ""
        if isinstance(metrics, dict) and metrics:
            for k, v in list(metrics.items())[:8]:
                metrics_str += f"  - {k}: {v}\n"
        else:
            metrics_str = "  None provided\n"

        return f"""=======================================================
SYNAPSE RISKOPS • PREDICTIVE INCIDENT ALERT
=======================================================

SERVICE PREDICTED TO FAIL: {service_name}
Severity: {severity}
Incident ID: {incident_id}
Risk Score: {risk_score:.1f}%
Predicted Failure: {failure_type}
Root Cause Service: {root_cause}
Confidence (ML / RCA): {ml_confidence:.1f}% / {rca_confidence:.1f}%
Routing Decision: {routing_decision}
Timestamp: {timestamp}

AI GUIDANCE:
{guidance}

TELEMETRY SNAPSHOT:
{metrics_str}

ACTION REQUIRED:
Review incident details and execute or approve remediation:
http://localhost:5173/dashboard?incident_id={incident_id}

-------------------------------------------------------
Sent via Gmail SMTP ({self.sender_email}) to Admin ({self.admin_email}).
"""

    def _send_smtp_sync(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: str,
    ) -> Dict[str, Any]:
        """Synchronously dispatch email through smtp.gmail.com with STARTTLS."""
        if not self.enabled:
            logger.info("Email notifications are disabled in settings (EMAIL_NOTIFICATIONS_ENABLED=False).")
            return {
                "success": False,
                "status": "DISABLED",
                "detail": "Email notifications are disabled in settings.",
            }

        password = self.sender_password
        if not password:
            msg = (
                f"Gmail SMTP dispatch skipped: No SMTP_PASSWORD or GMAIL_APP_PASSWORD found. "
                f"To send emails from '{self.sender_email}' to '{to_email}', generate a 16-character "
                f"Google App Password at https://myaccount.google.com/apppasswords and set SMTP_PASSWORD in .env."
            )
            logger.warning(msg)
            return {
                "success": False,
                "status": "NO_CREDENTIALS",
                "detail": msg,
            }

        msg = MIMEMultipart("alternative")
        msg["From"] = f"Synapse RiskOps Alerting <{self.sender_email}>"
        msg["To"] = to_email
        msg["Subject"] = subject
        msg["Date"] = formatdate(localtime=True)
        msg["Message-ID"] = make_msgid(domain="synapse-riskops.local")

        # Attach plain text and HTML alternatives
        msg.attach(MIMEText(text_content, "plain", "utf-8"))
        msg.attach(MIMEText(html_content, "html", "utf-8"))

        try:
            logger.info(f"Connecting to Gmail SMTP server {self.smtp_host}:{self.smtp_port} for {self.sender_email} -> {to_email}...")
            context = ssl.create_default_context()
            if self.smtp_port == 465:
                server = smtplib.SMTP_SSL(self.smtp_host, self.smtp_port, timeout=12.0, context=context)
                server.ehlo()
            else:
                server = smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=12.0)
                server.ehlo()
                if self.use_tls:
                    server.starttls(context=context)
                    server.ehlo()

            server.login(self.sender_email, password)
            server.sendmail(self.sender_email, [to_email], msg.as_string())
            server.quit()

            logger.info(f"Successfully delivered incident alert email to admin ({to_email}) via Gmail SMTP.")
            return {
                "success": True,
                "status": "SENT",
                "recipient": to_email,
                "sender": self.sender_email,
                "subject": subject,
                "detail": "Email successfully delivered via Gmail SMTP.",
            }

        except smtplib.SMTPAuthenticationError as auth_err:
            error_detail = (
                f"Gmail SMTP authentication failed for '{self.sender_email}'. "
                f"Google requires a 16-character App Password (not your standard account password). "
                f"Enable 2-Step Verification on {self.sender_email} and generate an App Password at "
                f"https://myaccount.google.com/apppasswords. SMTP Error: {auth_err}"
            )
            logger.error(error_detail)
            return {
                "success": False,
                "status": "AUTH_FAILED",
                "detail": error_detail,
            }

        except smtplib.SMTPServerDisconnected as disc_err:
            error_detail = (
                f"Gmail unexpectedly disconnected connection for '{self.sender_email}'. "
                f"Google's SMTP servers reject plain account passwords and immediately terminate the connection. "
                f"You must generate a 16-character App Password at https://myaccount.google.com/apppasswords."
            )
            logger.error(error_detail)
            return {
                "success": False,
                "status": "AUTH_FAILED",
                "detail": error_detail,
            }

        except (smtplib.SMTPConnectError, TimeoutError) as net_err:
            error_detail = f"Network/Connection error connecting to {self.smtp_host}:{self.smtp_port}: {net_err}"
            logger.error(error_detail)
            return {
                "success": False,
                "status": "CONNECTION_ERROR",
                "detail": error_detail,
            }

        except Exception as e:
            error_detail = f"Unexpected error during Gmail SMTP dispatch: {e}"
            logger.exception(error_detail)
            return {
                "success": False,
                "status": "ERROR",
                "detail": error_detail,
            }

    async def send_email(
        self,
        to_email: Optional[str] = None,
        subject: str = "",
        html_content: str = "",
        text_content: str = "",
    ) -> Dict[str, Any]:
        """Asynchronously send an email using Python's standard library smtplib in a worker thread."""
        recipient = to_email or self.admin_email
        return await asyncio.to_thread(
            self._send_smtp_sync,
            recipient,
            subject,
            html_content,
            text_content,
        )

    async def send_incident_alert(
        self,
        incident_data: Dict[str, Any],
        recipient: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Send a formatted predictive failure incident alert email to the admin.
        
        Args:
            incident_data: Dictionary containing service_name, incident_id, risk_score,
                           severity, failure_type, root_cause, guidance, metrics, etc.
            recipient: Optional override recipient (defaults to admin_email).
        """
        service_name = incident_data.get("service_name", "Unknown Service")
        severity = incident_data.get("severity", "CRITICAL").upper()
        risk_score = float(incident_data.get("risk_score", 0.0))
        failure_type = str(incident_data.get("failure_type", "latency_degradation")).replace("_", " ").title()

        subject = f"🚨 [{severity}] Predicted Failure on {service_name}: {failure_type} ({risk_score:.1f}% Risk)"
        html_content = self._build_incident_html(incident_data)
        text_content = self._build_incident_text(incident_data)

        target_recipient = recipient or self.admin_email
        return await self.send_email(
            to_email=target_recipient,
            subject=subject,
            html_content=html_content,
            text_content=text_content,
        )

    async def send_test_email(self, to_email: Optional[str] = None) -> Dict[str, Any]:
        """Send a test verification email to confirm Gmail SMTP integration."""
        target_recipient = to_email or self.admin_email
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

        test_data = {
            "service_name": "payment-service (Test Simulation)",
            "incident_id": "TEST-SIM-001",
            "severity": "HIGH",
            "risk_score": 82.5,
            "failure_type": "database_connection_exhaustion",
            "root_cause": "postgres-primary-pool",
            "ml_confidence": 0.89,
            "rca_confidence": 0.84,
            "guidance": "This is a verified test email confirming that Gmail SMTP integration is active and operating normally.",
            "routing_decision": "human_approval",
            "timestamp": now_str,
            "metrics": {
                "cpu_usage": 74.2,
                "memory_usage": 83.1,
                "active_connections": 98,
                "response_time_p99": 240.5,
                "error_rate": 4.8,
            },
        }

        subject = f"✅ [Synapse RiskOps] Gmail SMTP Connectivity Verification ({now_str})"
        html_content = self._build_incident_html(test_data)
        text_content = self._build_incident_text(test_data)

        return await self.send_email(
            to_email=target_recipient,
            subject=subject,
            html_content=html_content,
            text_content=text_content,
        )


# Module-level singleton
email_service = EmailService()
