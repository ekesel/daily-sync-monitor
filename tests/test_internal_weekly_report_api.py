# tests/test_internal_weekly_report_api.py
from datetime import date, timedelta
from http import HTTPStatus

import pytest


@pytest.mark.asyncio
async def test_internal_run_weekly_report_uses_last_7_days(monkeypatch, client):
    """
    Verify that /internal/run-weekly-report:
    - Computes start_date = today - 6 days, end_date = today
    - Delegates to compute_weekly_summary with those dates
    - Returns the WeeklySummary payload from the service
    """
    from app.services import weekly_summary as ws_module
    from app.schemas.weekly_report import WeeklySummary, WeeklyProjectSummary

    today = date.today()
    expected_end = today
    expected_start = today - timedelta(days=6)

    captured_args = {}

    async def fake_compute_weekly_summary(db, start_date, end_date):
        # Capture the arguments for assertions after the call
        captured_args["start_date"] = start_date
        captured_args["end_date"] = end_date

        # Return a simple, deterministic WeeklySummary
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
                    total_days=3,
                    happened_count=2,
                    missed_count=1,
                    cancelled_count=0,
                    no_data_count=0,
                    error_count=0,
                    compliance_pct=66.67,
                )
            ],
        )

    monkeypatch.setattr(ws_module, "compute_weekly_summary", fake_compute_weekly_summary)

    # Call the endpoint (no body, no query params)
    resp = client.post("/internal/run-weekly-report")
    assert resp.status_code == HTTPStatus.OK

    # Verify date arguments passed into the service
    assert captured_args["start_date"] == expected_start
    assert captured_args["end_date"] == expected_end

    data = resp.json()
    assert data["start_date"] == expected_start.isoformat()
    assert data["end_date"] == expected_end.isoformat()

    assert len(data["projects"]) == 1
    proj = data["projects"][0]
    assert proj["project_key"] == "TEST"
    assert proj["total_days"] == 3
    assert 66.6 <= proj["compliance_pct"] <= 66.8