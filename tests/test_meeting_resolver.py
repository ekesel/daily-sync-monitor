# tests/test_meeting_resolver.py
import pytest
from datetime import datetime, timezone, date

from app.schemas.meeting import MeetingOccurrence
from app.services.meeting_resolver import GraphMeetingResolver


class FakeGraphClient:
    """
    Simple stub for GraphClient used in resolver tests.
    """

    def __init__(self, payload):
        self.payload = payload
        self.called = False

    async def get_json(self, path, params=None):
        self.called = True
        return self.payload


@pytest.mark.asyncio
async def test_resolver_returns_no_data_if_no_events():
    fake_client = FakeGraphClient({"value": []})
    resolver = GraphMeetingResolver(fake_client, organizer_user_id="org@test.com")

    result = await resolver.resolve_meeting_occurrence(
        meeting_id="m123",
        standup_date=date(2025, 1, 10),
    )

    assert isinstance(result, MeetingOccurrence)
    assert result.start_time_utc is None
    assert result.end_time_utc is None
    assert result.is_cancelled is False


@pytest.mark.asyncio
async def test_resolver_matches_by_event_id():
    fake_event = {
        "id": "m123",
        "isCancelled": False,
        "start": {"dateTime": "2025-01-10T10:30:00", "timeZone": "UTC"},
        "end": {"dateTime": "2025-01-10T10:45:00", "timeZone": "UTC"},
    }

    fake_client = FakeGraphClient({"value": [fake_event]})
    resolver = GraphMeetingResolver(fake_client, "org@test.com")

    result = await resolver.resolve_meeting_occurrence("m123", date(2025, 1, 10))

    assert result.start_time_utc == datetime(2025, 1, 10, 10, 30, tzinfo=timezone.utc)
    assert result.end_time_utc == datetime(2025, 1, 10, 10, 45, tzinfo=timezone.utc)
    assert result.is_cancelled is False


@pytest.mark.asyncio
async def test_resolver_detects_cancellation():
    fake_event = {
        "id": "m123",
        "isCancelled": True,
        "start": {"dateTime": "2025-01-10T10:30:00", "timeZone": "UTC"},
        "end": {"dateTime": "2025-01-10T10:45:00", "timeZone": "UTC"},
    }

    fake_client = FakeGraphClient({"value": [fake_event]})
    resolver = GraphMeetingResolver(fake_client, "org@test.com")

    result = await resolver.resolve_meeting_occurrence("m123", date(2025, 1, 10))

    assert result.is_cancelled is True


@pytest.mark.asyncio
async def test_resolver_matches_by_onlineMeetingId():
    fake_event = {
        "id": "XYZ",
        "onlineMeetingId": "m123",
        "isCancelled": False,
        "start": {"dateTime": "2025-01-10T10:00:00", "timeZone": "UTC"},
        "end": {"dateTime": "2025-01-10T10:30:00", "timeZone": "UTC"},
    }

    fake_client = FakeGraphClient({"value": [fake_event]})
    resolver = GraphMeetingResolver(fake_client, "org@test.com")

    result = await resolver.resolve_meeting_occurrence("m123", date(2025, 1, 10))

    assert result.start_time_utc is not None
    assert result.end_time_utc is not None