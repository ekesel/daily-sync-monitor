# tests/test_project_summary_api.py
from datetime import date, timedelta
from http import HTTPStatus

import pytest

from sqlalchemy import select

from app.db.session import AsyncSessionLocal, init_db
from app.models.project import Project
from app.models.daily_standup_log import DailyStandupLog
from app.schemas.daily_standup_log import DailyStandupStatus


def _create_project_via_api(client, key: str) -> int:
    payload = {
        "name": f"Summary Project {key}",
        "project_key": key,
        "meeting_id": f"meeting-{key}",
        "standup_time": "10:30:00",
        "is_active": True,
    }
    resp = client.post("/projects", json=payload)
    assert resp.status_code in (HTTPStatus.CREATED, HTTPStatus.BAD_REQUEST)

    if resp.status_code == HTTPStatus.CREATED:
        return resp.json()["id"]

    # Already exists: find it
    list_resp = client.get("/projects")
    assert list_resp.status_code == HTTPStatus.OK
    for proj in list_resp.json():
        if proj["project_key"] == key:
            return proj["id"]

    raise AssertionError("Could not create or find project for summary test.")


@pytest.mark.asyncio
async def test_project_summary_with_logs(client):
    """
    Verify that /projects/{id}/summary correctly aggregates counts and compliance.
    """
    await init_db()

    project_id = _create_project_via_api(client, key="SUMM_BASIC")

    # Insert logs for specific dates
    async with AsyncSessionLocal() as session:
        base = date(2025, 11, 10)
        statuses = [
            DailyStandupStatus.HAPPENED,
            DailyStandupStatus.MISSED,
            DailyStandupStatus.HAPPENED,
            DailyStandupStatus.ERROR,
        ]  # total 4 days

        logs = []
        for offset, st in enumerate(statuses):
            logs.append(
                DailyStandupLog(
                    project_id=project_id,
                    standup_date=base + timedelta(days=offset),
                    scheduled_time="10:30:00",
                    status=st.value,
                    attendance_count=0,
                    duration_minutes=0.0,
                )
            )

        session.add_all(logs)
        await session.commit()

    from_date = "2025-11-10"
    to_date = "2025-11-13"

    resp = client.get(
        f"/projects/{project_id}/summary?from_date={from_date}&to_date={to_date}"
    )
    assert resp.status_code == HTTPStatus.OK

    data = resp.json()
    assert data["project_id"] == project_id
    assert data["total_days"] == 4

    assert data["happened_count"] == 2
    assert data["missed_count"] == 1
    assert data["error_count"] == 1
    assert data["cancelled_count"] == 0
    assert data["no_data_count"] == 0

    # Compliance = 2 / 4 = 50%
    assert 49.9 <= data["compliance_pct"] <= 50.1


@pytest.mark.asyncio
async def test_project_summary_no_logs_returns_zeroes(client):
    """
    If a project exists but has no logs in the range, the summary should
    return total_days = 0 and all counts = 0, not 404.
    """
    await init_db()

    project_id = _create_project_via_api(client, key="SUMM_NO_LOGS")

    from_date = "2030-01-01"
    to_date = "2030-01-07"

    resp = client.get(
        f"/projects/{project_id}/summary?from_date={from_date}&to_date={to_date}"
    )
    assert resp.status_code == HTTPStatus.OK

    data = resp.json()
    assert data["project_id"] == project_id
    assert data["total_days"] == 0
    assert data["happened_count"] == 0
    assert data["missed_count"] == 0
    assert data["cancelled_count"] == 0
    assert data["no_data_count"] == 0
    assert data["error_count"] == 0
    assert data["compliance_pct"] == 0.0


def test_project_summary_404_for_missing_project(client):
    resp = client.get(
        "/projects/999999/summary?from_date=2025-11-10&to_date=2025-11-16"
    )
    assert resp.status_code == HTTPStatus.NOT_FOUND
    assert "not found" in resp.json()["detail"].lower()


def test_project_summary_400_for_invalid_date_range(client):
    # Need an existing project id
    project_id = _create_project_via_api(client, key="SUMM_BAD_RANGE")

    # end < from
    resp = client.get(
        f"/projects/{project_id}/summary?from_date=2025-11-16&to_date=2025-11-10"
    )
    assert resp.status_code == HTTPStatus.BAD_REQUEST
    assert "end_date must be greater than or equal to start_date" in resp.json()[
        "detail"
    ]