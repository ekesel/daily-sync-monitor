# app/schemas/daily_standup_log.py
from datetime import date, time
from enum import Enum

from pydantic import BaseModel, Field


class DailyStandupStatus(str, Enum):
    """
    Enum representing the possible outcomes of a daily standup check.
    """

    HAPPENED = "HAPPENED"
    MISSED = "MISSED"
    CANCELLED = "CANCELLED"
    NO_DATA = "NO_DATA"
    ERROR = "ERROR"


class DailyStandupLogRead(BaseModel):
    """
    Public representation of a DailyStandupLog entry.
    """

    id: int = Field(..., example=1, description="Database identifier of the log entry.")
    project_id: int = Field(
        ...,
        example=1,
        description="Identifier of the project to which this log belongs.",
    )
    standup_date: date = Field(
        ...,
        description="Business date for which the standup check was executed.",
        example="2025-11-14",
    )
    scheduled_time: time = Field(
        ...,
        description="Configured local time at which the standup is expected.",
        example="10:30:00",
    )
    status: DailyStandupStatus = Field(
        ...,
        description="Outcome of the check for the given project and date.",
        example="NO_DATA",
    )
    attendance_count: int = Field(
        ...,
        description="Number of non-organizer attendees observed in the meeting.",
        example=0,
    )
    duration_minutes: float = Field(
        ...,
        description="Observed meeting duration in minutes.",
        example=0.0,
    )

    class Config:
        from_attributes = True


class DailyCheckSummary(BaseModel):
    """
    Summary payload returned by the /internal/run-daily-check endpoint.
    """

    standup_date: date = Field(
        ...,
        description="The date for which the check was executed.",
        example="2025-11-14",
    )
    total_projects_evaluated: int = Field(
        ...,
        description="Number of active projects that were part of this run.",
        example=5,
    )
    logs_created: int = Field(
        ...,
        description="Number of DailyStandupLog entries generated in this run.",
        example=5,
    )
    entries: list[DailyStandupLogRead] = Field(
        ...,
        description="Per-project results for this daily check execution.",
    )