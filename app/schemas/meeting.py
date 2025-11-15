# app/schemas/meeting.py
from datetime import datetime
from pydantic import BaseModel, Field


class MeetingOccurrence(BaseModel):
    """
    Represents a single resolved occurrence of a recurring meeting for
    a specific business date.

    Does not include attendance data – that belongs to Step 3.
    """

    meeting_id: str = Field(..., description="Original meeting ID configured on the project.")
    start_time_utc: datetime | None = Field(
        None, description="UTC start time of this meeting occurrence."
    )
    end_time_utc: datetime | None = Field(
        None, description="UTC end time of this meeting occurrence."
    )
    is_cancelled: bool = Field(
        False,
        description=(
            "True if Graph API indicates the occurrence was cancelled or deleted "
            "for this date."
        ),
    )
    raw: dict | None = Field(
        None,
        description="Raw Graph API JSON for debugging purposes.",
    )