# app/services/meeting_normalizer.py
from __future__ import annotations

from typing import Optional, Dict, Any

from app.schemas.attendance import AttendanceSummary
from app.schemas.meeting import MeetingOccurrence
from app.schemas.meeting_evaluation import MeetingSnapshot


class MeetingNormalizer:
    """
    Combines meeting occurrence and attendance information into a single
    normalized structure (MeetingSnapshot).

    This keeps the evaluation logic simple and isolated from the raw Graph shapes.
    """

    @staticmethod
    def build_snapshot(
        occurrence: Optional[MeetingOccurrence],
        attendance: Optional[AttendanceSummary],
    ) -> MeetingSnapshot:
        """
        Build a MeetingSnapshot from the given occurrence and attendance.

        Rules
        -----
        - If `occurrence` is None, treat the meeting as NOT cancelled and with
          no timing information, but still allow attendance-based metrics.
        - If `attendance` is None or has_data=False, non_organizer_count and
          duration_minutes default to 0.
        - `cancelled` is taken from occurrence.is_cancelled when available,
          otherwise False.
        - `raw` is a combined dictionary with available underlying payloads.
        """
        cancelled = False
        raw: Dict[str, Any] = {}

        if occurrence is not None:
            cancelled = bool(occurrence.is_cancelled)
            if occurrence.raw is not None:
              raw["occurrence"] = occurrence.raw
            if attendance and attendance.raw is not None:
              raw["attendance"] = attendance.raw

        non_org_count = 0
        duration_minutes = 0.0

        if attendance is not None and attendance.has_data:
            non_org_count = attendance.non_organizer_count
            duration_minutes = attendance.duration_minutes
            if attendance.raw is not None:
                raw["attendance"] = attendance.raw

        # If nothing to put in raw, set it to None for cleaner output
        raw_output: dict | None = raw or None

        return MeetingSnapshot(
            cancelled=cancelled,
            non_organizer_count=non_org_count,
            duration_minutes=duration_minutes,
            raw=raw_output,
        )