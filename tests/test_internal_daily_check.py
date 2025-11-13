# tests/test_internal_daily_check.py
from http import HTTPStatus


def _create_project(client, key: str = "INT_CHECK_KEY") -> int:
    payload = {
        "name": "Internal Check Project",
        "project_key": key,
        "meeting_id": "test-meeting-id-internal-check",
        "standup_time": "10:30:00",
        "is_active": True,
    }
    response = client.post("/projects", json=payload)
    assert response.status_code in (HTTPStatus.CREATED, HTTPStatus.BAD_REQUEST)
    # If project already exists, fetch list and return first matching id
    if response.status_code == HTTPStatus.CREATED:
        return response.json()["id"]

    list_resp = client.get("/projects")
    assert list_resp.status_code == HTTPStatus.OK
    for proj in list_resp.json():
        if proj["project_key"] == key:
            return proj["id"]
    raise AssertionError("Project for internal check not found or created.")


def test_run_daily_check_creates_logs_for_active_projects(client):
    """
    Running /internal/run-daily-check should evaluate all active projects and
    create at least one DailyStandupLog entry, returning a summary payload.
    """
    _create_project(client, key="INT_CHECK_KEY_1")

    response = client.post("/internal/run-daily-check")
    assert response.status_code == HTTPStatus.OK

    data = response.json()
    assert "standup_date" in data
    assert data["total_projects_evaluated"] >= 1
    assert data["logs_created"] >= 1

    entries = data["entries"]
    assert isinstance(entries, list)
    assert len(entries) == data["logs_created"]

    sample = entries[0]
    assert "id" in sample
    assert "project_id" in sample
    assert "standup_date" in sample
    assert "scheduled_time" in sample
    assert "status" in sample
    # Placeholder logic always uses NO_DATA for now
    assert sample["status"] in ("NO_DATA", "HAPPENED", "MISSED", "CANCELLED", "ERROR")


def test_run_daily_check_respects_optional_date_param(client):
    """
    Verify that providing a standup_date query parameter is accepted and returned
    in the summary.
    """
    _create_project(client, key="INT_CHECK_KEY_2")

    response = client.post("/internal/run-daily-check?standup_date=2025-11-14")
    assert response.status_code == HTTPStatus.OK

    data = response.json()
    assert data["standup_date"] == "2025-11-14"