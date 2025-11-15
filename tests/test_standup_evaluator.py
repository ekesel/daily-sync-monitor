# tests/test_standup_evaluator.py
from app.schemas.meeting_evaluation import MeetingSnapshot
from app.services.standup_evaluator import StandupEvaluator
from app.schemas.daily_standup_log import DailyStandupStatus


def test_evaluator_returns_no_data_when_snapshot_is_none():
    status = StandupEvaluator.evaluate(None)
    assert status == DailyStandupStatus.NO_DATA


def test_evaluator_returns_cancelled_when_meeting_cancelled():
    snapshot = MeetingSnapshot(
        cancelled=True,
        non_organizer_count=10,
        duration_minutes=60.0,
        raw=None,
    )

    status = StandupEvaluator.evaluate(snapshot)
    assert status == DailyStandupStatus.CANCELLED


def test_evaluator_missed_when_not_enough_attendees():
    snapshot = MeetingSnapshot(
        cancelled=False,
        non_organizer_count=1,  # < 2
        duration_minutes=30.0,
        raw=None,
    )

    status = StandupEvaluator.evaluate(snapshot)
    assert status == DailyStandupStatus.MISSED


def test_evaluator_missed_when_duration_too_short():
    snapshot = MeetingSnapshot(
        cancelled=False,
        non_organizer_count=5,
        duration_minutes=3.0,  # <= 3
        raw=None,
    )

    status = StandupEvaluator.evaluate(snapshot)
    assert status == DailyStandupStatus.MISSED


def test_evaluator_happened_when_rules_satisfied():
    snapshot = MeetingSnapshot(
        cancelled=False,
        non_organizer_count=2,
        duration_minutes=10.0,
        raw=None,
    )

    status = StandupEvaluator.evaluate(snapshot)
    assert status == DailyStandupStatus.HAPPENED

def test_evaluator_returns_error_when_raw_has_top_level_error():
    snapshot = MeetingSnapshot(
        cancelled=False,
        non_organizer_count=5,
        duration_minutes=10.0,
        raw={"error": "some graph issue"},
    )

    status = StandupEvaluator.evaluate(snapshot)
    assert status == DailyStandupStatus.ERROR


def test_evaluator_returns_error_when_nested_error_present():
    snapshot = MeetingSnapshot(
        cancelled=False,
        non_organizer_count=5,
        duration_minutes=10.0,
        raw={
            "occurrence": {"error": "occurrence resolution failed"},
            "attendance": {"some": "data"},
        },
    )

    status = StandupEvaluator.evaluate(snapshot)
    assert status == DailyStandupStatus.ERROR