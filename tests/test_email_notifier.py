# tests/test_email_notifier.py
from datetime import date

import pytest

from app.schemas.weekly_report import WeeklySummary, WeeklyProjectSummary
from app.services import email_notifier as notifier_module


def _dummy_summary() -> WeeklySummary:
    start = date(2025, 11, 10)
    end = date(2025, 11, 16)
    proj = WeeklyProjectSummary(
        project_id=1,
        project_key="OCS",
        project_name="OCS Platform",
        start_date=start,
        end_date=end,
        total_days=5,
        happened_count=3,
        missed_count=1,
        cancelled_count=0,
        no_data_count=1,
        error_count=0,
        compliance_pct=60.0,
    )
    return WeeklySummary(
        start_date=start,
        end_date=end,
        projects=[proj],
    )


def test_send_weekly_summary_email_returns_false_when_not_configured(monkeypatch):
    """
    If REPORT_EMAIL_RECIPIENTS or SMTP_HOST/SMTP_FROM_ADDRESS are missing,
    the function should return False and not attempt SMTP.
    """
    class DummySettings:
        APP_NAME = "DailySync Monitor"
        REPORT_EMAIL_RECIPIENTS = None
        SMTP_HOST = None
        SMTP_PORT = 587
        SMTP_USERNAME = None
        SMTP_PASSWORD = None
        SMTP_USE_TLS = True
        SMTP_FROM_ADDRESS = None

    monkeypatch.setattr(notifier_module, "get_settings", lambda: DummySettings())

    summary = _dummy_summary()
    sent = notifier_module.send_weekly_summary_email(summary)
    assert sent is False


def test_send_weekly_summary_email_uses_smtp_when_configured(monkeypatch):
    """
    When SMTP and recipients are configured, send_weekly_summary_email should
    call smtplib.SMTP and return True.
    """
    sent_messages = []

    class DummySMTP:
        def __init__(self, host, port):
            self.host = host
            self.port = port

        def starttls(self):
            pass

        def login(self, username, password):
            # login may or may not be used depending on config
            pass

        def send_message(self, msg):
            sent_messages.append(msg)

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    class DummySettings:
        APP_NAME = "DailySync Monitor"
        REPORT_EMAIL_RECIPIENTS = "process@example.com,cto@example.com"
        SMTP_HOST = "smtp.example.com"
        SMTP_PORT = 587
        SMTP_USERNAME = "user"
        SMTP_PASSWORD = "pass"
        SMTP_USE_TLS = True
        SMTP_FROM_ADDRESS = "noreply@example.com"

    monkeypatch.setattr(notifier_module, "get_settings", lambda: DummySettings())
    monkeypatch.setattr(notifier_module.smtplib, "SMTP", DummySMTP)

    summary = _dummy_summary()
    sent = notifier_module.send_weekly_summary_email(summary)

    assert sent is True
    assert len(sent_messages) == 1
    msg = sent_messages[0]
    assert "Weekly Standup Summary" in msg["Subject"]
    assert "process@example.com" in msg["To"]
    assert "cto@example.com" in msg["To"]