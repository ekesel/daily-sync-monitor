# tests/test_project_logs_api.py
from datetime import date, timedelta
from http import HTTPStatus

import pytest

from sqlalchemy import select

from app.db.session import AsyncSessionLocal, init_db
from app.models.daily_standup_log import DailyStandupLog
from app.models.project import Project
from app.schemas.daily_standup_log import DailyStandupStatus


def _create_project_via_api(client, key: str) -> int:
    payload = {
        "name": f"Logs Project {key}",
        "project_key": key,
        "meeting_id": f"meeting-{key}",
        "standup_time": "10:30:00",
        "is_active": True,
    }
    resp = client.post("/projects", json=payload)
    assert resp.status_code in (HTTPStatus.CREATED, HTTPStatus.BAD_REQUEST)

    if resp.status_code == HTTPStatus.CREATED:
        return resp.json()["id"]

    # If already exists (from previous tests), look it up
    list_resp = client.get("/projects")
    assert list_resp.status_code == HTTPStatus.OK
    for proj in list_resp.json():
        if proj["project_key"] == key:
            return proj["id"]

    raise AssertionError("Could not create or find project for logs test.")


@pytest.mark.asyncio
async def test_list_project_logs_basic(client):
    """
    Ensure /projects/{id}/logs returns all logs for a project when no
    from_date/to_date filters are provided.
    """
    await init_db()

    # Create project via API
    project_id = _create_project_via_api(client, key="LOGS_BASIC")

    # Insert some logs directly into DB for determinism
    async with AsyncSessionLocal() as session:
        base_date = date(2025, 11, 10)
        logs = []
        for offset, status in enumerate(
            [
                DailyStandupStatus.HAPPENED,
                DailyStandupStatus.MISSED,
                DailyStandupStatus.NO_DATA,
            ]
        ):
            logs.append(
                DailyStandupLog(
                    project_id=project_id,
                    standup_date=base_date + timedelta(days=offset),
                    scheduled_time="10:30:00",
                    status=status.value,
                    attendance_count=0,
                    duration_minutes=0.0,
                )
            )

        session.add_all(logs)
        await session.commit()

    # Call the logs endpoint without date filters
    resp = client.get(f"/projects/{project_id}/logs")
    assert resp.status_code == HTTPStatus.OK

    data = resp.json()
    assert isinstance(data, list)
    # We added 3 logs
    assert len(data) >= 3

    # Ensure ordering by standup_date ascending
    dates = [entry["standup_date"] for entry in data]
    assert dates == sorted(dates)


@pytest.mark.asyncio
async def test_list_project_logs_with_date_filters(client):
    """
    Ensure from_date/to_date filters are applied correctly to the logs list.
    """
    await init_db()

    project_id = _create_project_via_api(client, key="LOGS_FILTER")

    async with AsyncSessionLocal() as session:
        base_date = date(2025, 11, 10)
        statuses = [
            DailyStandupStatus.HAPPENED,
            DailyStandupStatus.MISSED,
            DailyStandupStatus.NO_DATA,
            DailyStandupStatus.ERROR,
        ]
        logs = []
        for offset, status in enumerate(statuses):
            logs.append(
                DailyStandupLog(
                    project_id=project_id,
                    standup_date=base_date + timedelta(days=offset),
                    scheduled_time="10:30:00",
                    status=status.value,
                    attendance_count=0,
                    duration_minutes=0.0,
                )
            )
        session.add_all(logs)
        await session.commit()

    # Filter for the middle 2 days
    from_date = "2025-11-11"
    to_date = "2025-11-12"

    resp = client.get(
        f"/projects/{project_id}/logs?from_date={from_date}&to_date={to_date}"
    )
    assert resp.status_code == HTTPStatus.OK

    data = resp.json()
    # Expect exactly 2 entries within this window
    assert len(data) == 2
    returned_dates = {entry["standup_date"] for entry in data}
    assert returned_dates == {"2025-11-11", "2025-11-12"}


def test_list_project_logs_404_when_project_missing(client):
    """
    If the project does not exist, the endpoint should return 404.
    """
    resp = client.get("/projects/999999/logs")
    assert resp.status_code == HTTPStatus.NOT_FOUND
    data = resp.json()
    assert "not found" in data["detail"].lower()