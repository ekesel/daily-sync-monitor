# tests/test_meeting_normalizer.py
from datetime import datetime, timezone

from app.schemas.attendance import AttendanceSummary
from app.schemas.meeting import MeetingOccurrence
from app.schemas.meeting_evaluation import MeetingSnapshot
from app.schemas.meeting_evaluation import MeetingSnapshot
from app.services.meeting_normalizer import MeetingNormalizer


def _occurrence(
    cancelled: bool = False,
    with_raw: bool = True,
) -> MeetingOccurrence:
    return MeetingOccurrence(
        meeting_id="m123",
        start_time_utc=datetime(2025, 1, 10, 10, 30, tzinfo=timezone.utc),
        end_time_utc=datetime(2025, 1, 10, 10, 45, tzinfo=timezone.utc),
        is_cancelled=cancelled,
        raw={"occ": "data"} if with_raw else None,
    )


def _attendance(
    non_org: int = 2,
    duration: float = 15.0,
    has_data: bool = True,
    with_raw: bool = True,
) -> AttendanceSummary:
    return AttendanceSummary(
        meeting_id="m123",
        non_organizer_count=non_org,
        duration_minutes=duration,
        has_data=has_data,
        raw={"att": "data"} if with_raw else None,
    )


def test_normalizer_combines_occurrence_and_attendance():
    """
    When both occurrence and attendance are present and valid, the snapshot
    should reflect cancellation, counts, duration, and combined raw payload.
    """
    occurrence = _occurrence(cancelled=False)
    attendance = _attendance(non_org=3, duration=20.0)

    snapshot = MeetingNormalizer.build_snapshot(occurrence, attendance)

    assert isinstance(snapshot, MeetingSnapshot)
    assert snapshot.cancelled is False
    assert snapshot.non_organizer_count == 3
    assert 19.9 <= snapshot.duration_minutes <= 20.1
    assert snapshot.raw is not None
    assert "occurrence" in snapshot.raw
    assert "attendance" in snapshot.raw


def test_normalizer_handles_missing_attendance():
    """
    If attendance is missing, counts and duration default to zero but
    cancellation status and raw occurrence data should still be preserved.
    """
    occurrence = _occurrence(cancelled=True)

    snapshot = MeetingNormalizer.build_snapshot(occurrence, None)

    assert snapshot.cancelled is True
    assert snapshot.non_organizer_count == 0
    assert snapshot.duration_minutes == 0.0
    assert snapshot.raw is not None
    assert "occurrence" in snapshot.raw
    assert "attendance" not in snapshot.raw


def test_normalizer_handles_attendance_without_data():
    """
    If attendance.has_data is False, it should behave similar to missing
    attendance: no counts or duration, but raw occurrence (if present)
    remains included.
    """
    occurrence = _occurrence(cancelled=False)
    attendance = _attendance(has_data=False)

    snapshot = MeetingNormalizer.build_snapshot(occurrence, attendance)

    assert snapshot.cancelled is False
    assert snapshot.non_organizer_count == 0
    assert snapshot.duration_minutes == 0.0
    # attendance.raw may still be present if provided, we don't discard it.
    assert snapshot.raw is not None
    assert "occurrence" in snapshot.raw
    assert "attendance" in snapshot.raw


def test_normalizer_handles_missing_everything():
    """
    If both occurrence and attendance are None, the snapshot should gracefully
    fall back to a fully neutral state.
    """
    snapshot = MeetingNormalizer.build_snapshot(None, None)

    assert snapshot.cancelled is False
    assert snapshot.non_organizer_count == 0
    assert snapshot.duration_minutes == 0.0
    assert snapshot.raw is None