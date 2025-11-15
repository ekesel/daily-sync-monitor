# app/services/email_notifier.py
from __future__ import annotations

import smtplib
from email.message import EmailMessage
from typing import List

from app.core.config import get_settings
from app.schemas.weekly_report import WeeklySummary


def _parse_recipients(recipients: str | None) -> List[str]:
    if not recipients:
        return []
    return [r.strip() for r in recipients.split(",") if r.strip()]


def build_weekly_summary_email_body(summary: WeeklySummary) -> str:
    """
    Build a simple Markdown-style text body for the weekly summary email.
    """
    lines: list[str] = []

    lines.append(
        f"Weekly Standup Summary: {summary.start_date.isoformat()} → {summary.end_date.isoformat()}"
    )
    lines.append("")
    if not summary.projects:
        lines.append("No standup logs found for this period.")
        return "\n".join(lines)

    lines.append(
        "| Project | Days | Happened | Missed | Cancelled | NO_DATA | ERROR | Compliance % |"
    )
    lines.append(
        "|--------|------|----------|--------|-----------|---------|-------|-------------|"
    )

    for p in summary.projects:
        lines.append(
            f"| {p.project_key} ({p.project_name}) "
            f"| {p.total_days} "
            f"| {p.happened_count} "
            f"| {p.missed_count} "
            f"| {p.cancelled_count} "
            f"| {p.no_data_count} "
            f"| {p.error_count} "
            f"| {p.compliance_pct:.2f} |"
        )

    lines.append("")
    lines.append("Regards,")
    lines.append("DailySync Monitor")

    return "\n".join(lines)


def send_weekly_summary_email(summary: WeeklySummary, subject: str | None = None) -> bool:
    """
    Send the given WeeklySummary via SMTP to REPORT_EMAIL_RECIPIENTS.

    Returns
    -------
    bool
        True if an attempt to send was made and succeeded.
        False if email sending is disabled/misconfigured or fails.
    """
    settings = get_settings()

    recipients = _parse_recipients(settings.REPORT_EMAIL_RECIPIENTS)
    if not recipients:
        # No configured recipients => nothing to send
        return False

    if not settings.SMTP_HOST or not settings.SMTP_FROM_ADDRESS:
        # Email system not configured
        return False

    if subject is None:
        subject = (
            f"[{settings.APP_NAME}] Weekly Standup Summary "
            f"{summary.start_date.isoformat()} → {summary.end_date.isoformat()}"
        )

    body = build_weekly_summary_email_body(summary)

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = settings.SMTP_FROM_ADDRESS
    msg["To"] = ", ".join(recipients)
    msg.set_content(body)

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as smtp:
            if settings.SMTP_USE_TLS:
                smtp.starttls()
            if settings.SMTP_USERNAME and settings.SMTP_PASSWORD:
                smtp.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            smtp.send_message(msg)
        return True
    except Exception:
        # We intentionally swallow exceptions here so that the internal
        # weekly-report endpoint still returns JSON summary even if email fails.
        return False