# tests/test_attendance_resolver.py
import pytest
from datetime import datetime, timezone

from app.schemas.attendance import AttendanceSummary
from app.services.attendance_resolver import AttendanceResolver


class FakeGraphClient:
    """
    Simple stub to emulate GraphClient for attendance tests.
    """

    def __init__(self, payload, raise_error: bool = False):
        self.payload = payload
        self.raise_error = raise_error
        self.called = False
        self.last_path = None

    async def get_json(self, path: str, params=None):
        self.called = True
        self.last_path = path
        if self.raise_error:
            from app.services.graph_client import GraphClientError

            raise GraphClientError("Simulated Graph failure")
        return self.payload


@pytest.mark.asyncio
async def test_attendance_resolver_no_reports_returns_has_data_false():
    """
    When Graph returns an empty `value` list, has_data should be False
    and counts should be zero.
    """
    payload = {"value": []}
    fake_client = FakeGraphClient(payload)
    resolver = AttendanceResolver(fake_client)

    summary = await resolver.resolve_attendance("meeting-123")

    assert isinstance(summary, AttendanceSummary)
    assert summary.meeting_id == "meeting-123"
    assert summary.has_data is False
    assert summary.non_organizer_count == 0
    assert summary.duration_minutes == 0.0
    assert summary.raw == payload


@pytest.mark.asyncio
async def test_attendance_resolver_counts_non_organizers_and_duration():
    """
    Non-organizer attendees with non-zero attendance should be counted,
    and duration should be computed from earliest join to latest leave.
    """
    payload = {
        "value": [
            {
                "id": "report-1",
                "attendanceRecords": [
                    {
                        "role": "Organizer",
                        "totalAttendanceInSeconds": 900,
                        "joinDateTime": "2025-01-10T10:00:00Z",
                        "leaveDateTime": "2025-01-10T10:30:00Z",
                    },
                    {
                        "role": "Attendee",
                        "totalAttendanceInSeconds": 600,
                        "joinDateTime": "2025-01-10T10:05:00Z",
                        "leaveDateTime": "2025-01-10T10:25:00Z",
                    },
                    {
                        "role": "Presenter",
                        "totalAttendanceInSeconds": 300,
                        "joinDateTime": "2025-01-10T10:10:00Z",
                        "leaveDateTime": "2025-01-10T10:20:00Z",
                    },
                    {
                        "role": "Attendee",
                        "totalAttendanceInSeconds": 0,
                        "joinDateTime": None,
                        "leaveDateTime": None,
                    },
                ],
            }
        ]
    }

    fake_client = FakeGraphClient(payload)
    resolver = AttendanceResolver(fake_client)

    summary = await resolver.resolve_attendance("meeting-xyz")

    assert summary.meeting_id == "meeting-xyz"
    # Two non-organizers with > 0 seconds (Attendee + Presenter)
    assert summary.non_organizer_count == 2
    assert summary.has_data is True
    # Duration from 10:00 to 10:30 = 30 minutes
    assert 29.9 <= summary.duration_minutes <= 30.1


@pytest.mark.asyncio
async def test_attendance_resolver_handles_graph_failure_gracefully():
    """
    If GraphClient raises an error, the resolver should not propagate the exception
    but instead return has_data=False with an embedded error message in `raw`.
    """
    fake_client = FakeGraphClient(payload={}, raise_error=True)
    resolver = AttendanceResolver(fake_client)

    summary = await resolver.resolve_attendance("meeting-error")

    assert summary.has_data is False
    assert summary.non_organizer_count == 0
    assert summary.duration_minutes == 0.0
    assert isinstance(summary.raw, dict)
    assert "error" in summary.raw
    assert "Simulated Graph failure" in summary.raw["error"]