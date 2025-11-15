# app/services/standup_evaluator.py
from __future__ import annotations

from app.schemas.meeting_evaluation import MeetingSnapshot
from app.schemas.daily_standup_log import DailyStandupStatus


class StandupEvaluator:
    """
    Applies business rules on top of a normalized MeetingSnapshot to derive
    the final standup status for a given project and date.

    Rules
    -----
    1) If meeting is cancelled           => CANCELLED
    2) Else if non_organizer_count < 2   => MISSED
    3) Else if duration_minutes <= 3     => MISSED
    4) Else                              => HAPPENED

    Note
    ----
    - If `snapshot` is None, evaluator returns NO_DATA.
    - NO_DATA and ERROR are reserved for cases where we cannot obtain
      reliable Graph data or the pipeline failed before evaluation.
    """

    @staticmethod
    def evaluate(snapshot: MeetingSnapshot | None) -> DailyStandupStatus:
        """
        Determine the DailyStandupStatus for the given snapshot.
        """
        if snapshot is None:
            return DailyStandupStatus.NO_DATA

        # First: check if snapshot.raw carries any error marker
        raw = snapshot.raw or {}
        error_present = False
        if isinstance(raw, dict):
            if "error" in raw:
                error_present = True
            else:
                # Check nested dicts e.g. raw["occurrence"]["error"]
                for value in raw.values():
                    if isinstance(value, dict) and "error" in value:
                        error_present = True
                        break

        if error_present:
            return DailyStandupStatus.ERROR

        # Rule 1: Cancelled wins immediately
        if snapshot.cancelled:
            return DailyStandupStatus.CANCELLED

        # Rule 2: Not enough attendees
        if snapshot.non_organizer_count < 2:
            return DailyStandupStatus.MISSED

        # Rule 3: Duration too short
        if snapshot.duration_minutes <= 3.0:
            return DailyStandupStatus.MISSED

        # Rule 4: Everything looks good
        return DailyStandupStatus.HAPPENED