# app/schemas/attendance.py
from datetime import datetime
from pydantic import BaseModel, Field


class AttendanceSummary(BaseModel):
    """
    Normalized view of a meeting's attendance data, derived from
    Microsoft Graph attendance reports.

    This abstraction is intentionally small so the evaluation logic
    can stay simple and testable.
    """

    meeting_id: str = Field(
        ...,
        description="Identifier of the meeting (id or onlineMeetingId) used for lookup.",
        example="9f4e7d5b-1234-5678-90ab-6a2dfb9d1ce1",
    )
    non_organizer_count: int = Field(
        ...,
        description=(
            "Number of unique participants that are not marked as 'Organizer' "
            "and have non-zero attendance duration."
        ),
        example=3,
    )
    duration_minutes: float = Field(
        ...,
        description=(
            "Estimated effective meeting duration in minutes, based on earliest "
            "join and latest leave times across all participants with activity. "
            "If join/leave times are unavailable, falls back to 0.0."
        ),
        example=12.5,
    )
    has_data: bool = Field(
        ...,
        description=(
            "Indicates whether any usable attendance data was found. When false, "
            "both non_organizer_count and duration_minutes will typically be 0."
        ),
        example=True,
    )
    raw: dict | None = Field(
        None,
        description="Raw Graph attendanceReports payload for debugging/troubleshooting.",
    )