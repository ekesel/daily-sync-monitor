# app/schemas/meeting_evaluation.py
from pydantic import BaseModel, Field


class MeetingSnapshot(BaseModel):
    """
    Normalized snapshot of a single meeting occurrence combining:
    - cancellation status
    - attendance metrics
    - optional raw data for debugging

    This is the primary input for the daily standup evaluation logic.
    """

    cancelled: bool = Field(
        ...,
        description="True if the meeting occurrence was cancelled in the calendar.",
        example=False,
    )
    non_organizer_count: int = Field(
        ...,
        description=(
            "Number of unique non-organizer participants with non-zero attendance "
            "duration."
        ),
        example=2,
    )
    duration_minutes: float = Field(
        ...,
        description=(
            "Effective meeting duration in minutes, based on earliest join and "
            "latest leave among participants."
        ),
        example=12.5,
    )
    raw: dict | None = Field(
        None,
        description=(
            "Optional combined raw payload from underlying Graph calls "
            "(occurrence + attendance) for debugging/troubleshooting."
        ),
    )