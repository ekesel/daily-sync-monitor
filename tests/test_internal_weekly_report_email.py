# tests/test_internal_weekly_report_email.py
from datetime import date, timedelta
from http import HTTPStatus

import pytest


@pytest.mark.asyncio
async def test_internal_run_weekly_report_triggers_email(monkeypatch, client):
    """
    Ensure that /internal/run-weekly-report calls send_weekly_summary_email
    after computing the summary.
    """
    from app.api.routes import internal as internal_module
    from app.schemas.weekly_report import WeeklySummary, WeeklyProjectSummary

    today = date.today()
    start = today - timedelta(days=6)

    # Fake compute_weekly_summary so we don't care about DB state here
    async def fake_compute_weekly_summary(db, start_date, end_date):
        return WeeklySummary(
            start_date=start_date,
            end_date=end_date,
            projects=[
                WeeklyProjectSummary(
                    project_id=1,
                    project_key="TEST",
                    project_name="Test Project",
                    start_date=start_date,
                    end_date=end_date,
                    total_days=1,
                    happened_count=1,
                    missed_count=0,
                    cancelled_count=0,
                    no_data_count=0,
                    error_count=0,
                    compliance_pct=100.0,
                )
            ],
        )

    email_called = {"value": False}
    last_summary = {"value": None}

    def fake_send_weekly_summary_email(summary):
        email_called["value"] = True
        last_summary["value"] = summary
        return True

    monkeypatch.setattr(
        internal_module, "compute_weekly_summary", fake_compute_weekly_summary
    )
    monkeypatch.setattr(
        internal_module, "send_weekly_summary_email", fake_send_weekly_summary_email
    )

    resp = client.post("/internal/run-weekly-report")
    assert resp.status_code == HTTPStatus.OK

    assert email_called["value"] is True
    assert last_summary["value"] is not None

    data = resp.json()
    assert data["start_date"] == start.isoformat()
    assert data["end_date"] == today.isoformat()