# tests/test_daily_check_evaluation.py
from http import HTTPStatus
from datetime import datetime, timezone, date

import pytest


def _create_project(client, key: str = "EVAL_KEY") -> int:
    payload = {
        "name": "Eval Project",
        "project_key": key,
        "meeting_id": "meeting-eval-123",
        "standup_time": "10:30:00",
        "is_active": True,
    }
    response = client.post("/projects", json=payload)
    assert response.status_code in (HTTPStatus.CREATED, HTTPStatus.BAD_REQUEST)

    if response.status_code == HTTPStatus.CREATED:
        return response.json()["id"]

    # If already exists (from previous tests), find it
    list_resp = client.get("/projects")
    assert list_resp.status_code == HTTPStatus.OK
    for proj in list_resp.json():
        if proj["project_key"] == key:
            return proj["id"]
    raise AssertionError("Eval project could not be created or found.")


@pytest.mark.asyncio
async def test_daily_check_uses_evaluation_rules(monkeypatch, client):
    """
    When Graph is 'configured' and resolvers return a non-cancelled meeting
    with >= 2 non-organizer attendees and duration > 3 minutes, the final
    status should be HAPPENED and the log should reflect the attendance
    metrics and duration.
    """
    from app.services import daily_check as dc
    from app.schemas.meeting import MeetingOccurrence
    from app.schemas.attendance import AttendanceSummary
    from app.schemas.meeting_evaluation import MeetingSnapshot

    # 1) Ensure we have at least one active project.
    _create_project(client, key="EVAL_KEY_HAPPENED")

    # 2) Monkeypatch get_settings in the daily_check module so that
    #    Graph is considered "configured" (resolvers will be created).
    class _DummySettings:
        GRAPH_TENANT_ID = "tenant"
        GRAPH_CLIENT_ID = "client"
        GRAPH_CLIENT_SECRET = "secret"
        GRAPH_ORGANIZER_USER_ID = "organizer@test.com"
        GRAPH_BASE_URL = "https://graph.microsoft.com"

    monkeypatch.setattr(dc, "get_settings", lambda: _DummySettings())

    # 3) Monkeypatch resolvers to avoid real Graph calls and return
    #    deterministic data which should lead to HAPPENED.
    async def fake_resolve_meeting_occurrence(self, meeting_id, standup_date):
        # Non-cancelled occurrence with valid times
        return MeetingOccurrence(
            meeting_id=meeting_id,
            start_time_utc=datetime(2025, 1, 10, 10, 30, tzinfo=timezone.utc),
            end_time_utc=datetime(2025, 1, 10, 10, 45, tzinfo=timezone.utc),
            is_cancelled=False,
            raw={"fake_occurrence": True},
        )

    async def fake_resolve_attendance(self, meeting_id):
        # 3 non-organizer attendees, 10 minute duration
        return AttendanceSummary(
            meeting_id=meeting_id,
            non_organizer_count=3,
            duration_minutes=10.0,
            has_data=True,
            raw={"fake_attendance": True},
        )

    monkeypatch.setattr(
        dc.GraphMeetingResolver,
        "resolve_meeting_occurrence",
        fake_resolve_meeting_occurrence,
    )
    monkeypatch.setattr(
        dc.AttendanceResolver,
        "resolve_attendance",
        fake_resolve_attendance,
    )

    # 4) Trigger the daily check through the internal API.
    target_date = "2025-11-14"
    response = client.post(f"/internal/run-daily-check?standup_date={target_date}")
    assert response.status_code == HTTPStatus.OK

    data = response.json()
    assert data["standup_date"] == target_date
    assert data["logs_created"] >= 1

    entry = data["entries"][0]

    # Status should be HAPPENED according to rules:
    # - cancelled=False
    # - non_organizer_count=3 (>=2)
    # - duration_minutes=10 (>3)
    assert entry["status"] == "HAPPENED"

    # Attendance metrics must be propagated
    assert entry["attendance_count"] == 3
    assert 9.9 <= entry["duration_minutes"] <= 10.1

    # raw_metadata should be present and JSON-serialized
    # We don't parse JSON here, just ensure it's non-null and string-like.
    assert "id" in entry
    # The raw_metadata field is not exposed in DailyStandupLogRead schema;
    # it is stored in the DB but not returned directly. If you later expose
    # it, you can assert on it here as well.

@pytest.mark.asyncio
async def test_daily_check_marks_error_when_resolvers_embed_error(monkeypatch, client):
    """
    If resolvers return snapshots whose raw payloads contain error information,
    the evaluator should mark the status as ERROR and the log should store
    the raw error in raw_metadata.
    """
    from app.services import daily_check as dc
    from app.schemas.meeting import MeetingOccurrence
    from app.schemas.attendance import AttendanceSummary
    from app.schemas.meeting_evaluation import MeetingSnapshot

    _create_project(client, key="EVAL_KEY_ERROR")

    class _DummySettings:
        GRAPH_TENANT_ID = "tenant"
        GRAPH_CLIENT_ID = "client"
        GRAPH_CLIENT_SECRET = "secret"
        GRAPH_ORGANIZER_USER_ID = "organizer@test.com"
        GRAPH_BASE_URL = "https://graph.microsoft.com"

    monkeypatch.setattr(dc, "get_settings", lambda: _DummySettings())

    async def fake_resolve_meeting_occurrence(self, meeting_id, standup_date):
        return MeetingOccurrence(
            meeting_id=meeting_id,
            start_time_utc=None,
            end_time_utc=None,
            is_cancelled=False,
            raw={"error": "Simulated occurrence error"},
        )

    async def fake_resolve_attendance(self, meeting_id):
        return AttendanceSummary(
            meeting_id=meeting_id,
            non_organizer_count=0,
            duration_minutes=0.0,
            has_data=False,
            raw={"error": "Simulated attendance error"},
        )

    monkeypatch.setattr(
        dc.GraphMeetingResolver,
        "resolve_meeting_occurrence",
        fake_resolve_meeting_occurrence,
    )
    monkeypatch.setattr(
        dc.AttendanceResolver,
        "resolve_attendance",
        fake_resolve_attendance,
    )

    response = client.post("/internal/run-daily-check?standup_date=2025-11-15")
    assert response.status_code == HTTPStatus.OK
    data = response.json()

    entry = data["entries"][0]
    assert entry["status"] == "ERROR"
    # raw_metadata is stored in DB and not exposed by the current schema.
    # If you later expose it, you can assert it contains 'Simulated' etc.