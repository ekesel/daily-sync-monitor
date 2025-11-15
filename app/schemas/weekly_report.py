# app/schemas/weekly_report.py
from datetime import date
from pydantic import BaseModel, Field

from app.schemas.daily_standup_log import DailyStandupStatus


class WeeklyProjectSummary(BaseModel):
    """
    Per-project summary of standup outcomes over a given date range.
    """

    project_id: int = Field(
        ...,
        description="Numeric identifier of the project.",
        example=1,
    )
    project_key: str = Field(
        ...,
        description="Short unique key for the project (e.g. 'OCS').",
        example="OCS",
    )
    project_name: str = Field(
        ...,
        description="Human-friendly project name.",
        example="OCS Platform",
    )

    start_date: date = Field(
        ...,
        description="Start date (inclusive) of the reporting window.",
        example="2025-11-10",
    )
    end_date: date = Field(
        ...,
        description="End date (inclusive) of the reporting window.",
        example="2025-11-16",
    )

    total_days: int = Field(
        ...,
        description=(
            "Number of days in the range for which standup logs exist "
            "for this project."
        ),
        example=5,
    )

    happened_count: int = Field(
        ...,
        description="Number of days where the standup status was HAPPENED.",
        example=4,
    )
    missed_count: int = Field(
        ...,
        description="Number of days where the standup status was MISSED.",
        example=1,
    )
    cancelled_count: int = Field(
        ...,
        description="Number of days where the standup was CANCELLED.",
        example=0,
    )
    no_data_count: int = Field(
        ...,
        description="Number of days where we could not determine any data (NO_DATA).",
        example=0,
    )
    error_count: int = Field(
        ...,
        description="Number of days where Graph or evaluation failed (ERROR).",
        example=0,
    )

    compliance_pct: float = Field(
        ...,
        description=(
            "Compliance percentage, computed as: "
            "HAPPENED / (HAPPENED + MISSED + CANCELLED + NO_DATA + ERROR) * 100. "
            "If total_days is zero, this will be 0.0."
        ),
        example=80.0,
    )


class WeeklySummary(BaseModel):
    """
    Aggregated weekly (or arbitrary range) summary across all projects.
    """

    start_date: date = Field(
        ...,
        description="Start date (inclusive) of the reporting window.",
    )
    end_date: date = Field(
        ...,
        description="End date (inclusive) of the reporting window.",
    )

    projects: list[WeeklyProjectSummary] = Field(
        ...,
        description="Per-project summaries for the given date range.",
    )