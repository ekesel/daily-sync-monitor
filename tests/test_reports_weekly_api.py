# tests/test_reports_weekly_api.py
from http import HTTPStatus


def _create_project(client, key: str = "WEEKLY_REPORT_KEY") -> int:
    payload = {
        "name": "Weekly Report Project",
        "project_key": key,
        "meeting_id": "weekly-meeting-id-123",
        "standup_time": "10:30:00",
        "is_active": True,
    }
    response = client.post("/projects", json=payload)
    assert response.status_code in (HTTPStatus.CREATED, HTTPStatus.BAD_REQUEST)

    if response.status_code == HTTPStatus.CREATED:
        return response.json()["id"]

    # If already exists, locate it
    list_resp = client.get("/projects")
    assert list_resp.status_code == HTTPStatus.OK
    for proj in list_resp.json():
        if proj["project_key"] == key:
            return proj["id"]
    raise AssertionError("Project for weekly report not found.")


def test_weekly_report_returns_project_summary(client):
    """
    End-to-end test:
    1) Create a project.
    2) Run daily check for a specific date (which creates a log).
    3) Call /reports/weekly for that same date range.
    4) Verify that the project appears in the summary with total_days=1.
    """
    _create_project(client, key="WEEKLY_REP_KEY_1")

    target_date = "2025-11-10"

    # Run the daily check to generate at least one DailyStandupLog
    resp_dc = client.post(f"/internal/run-daily-check?standup_date={target_date}")
    assert resp_dc.status_code == HTTPStatus.OK

    # Now call weekly report for exactly this one day
    resp_report = client.get(
        f"/reports/weekly?start_date={target_date}&end_date={target_date}"
    )
    assert resp_report.status_code == HTTPStatus.OK

    data = resp_report.json()
    assert data["start_date"] == target_date
    assert data["end_date"] == target_date

    projects = data["projects"]
    assert isinstance(projects, list)
    assert len(projects) >= 1

    # Find our project by key
    proj = next((p for p in projects if p["project_key"] == "WEEKLY_REP_KEY_1"), None)
    assert proj is not None
    assert proj["total_days"] == 1
    # Since Graph is not configured in tests, status will typically be NO_DATA
    # but we only care that the project summary exists with the right total_days.
    assert proj["happened_count"] + proj["missed_count"] + proj["cancelled_count"] \
        + proj["no_data_count"] + proj["error_count"] == 1


def test_weekly_report_empty_range_returns_no_projects(client):
    """
    When there are no logs in the requested date range, the API should return
    an empty projects list.
    """
    start_date = "2030-01-01"
    end_date = "2030-01-07"

    resp = client.get(f"/reports/weekly?start_date={start_date}&end_date={end_date}")
    assert resp.status_code == HTTPStatus.OK

    data = resp.json()
    assert data["start_date"] == start_date
    assert data["end_date"] == end_date
    assert data["projects"] == []