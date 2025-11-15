# app/api/routes/reports.py
from datetime import date as date_type

from fastapi import APIRouter, Depends, Query
from http import HTTPStatus
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.weekly_report import WeeklySummary
from app.services.weekly_summary import compute_weekly_summary

router = APIRouter(
    prefix="/reports",
    tags=["Reports"],
)


@router.get(
    "/weekly",
    response_model=WeeklySummary,
    status_code=HTTPStatus.OK,
    summary="Get weekly standup compliance summary for all projects",
    description=(
        "Return a weekly (or arbitrary date range) standup compliance summary "
        "for all projects that have standup logs in the given window.\n\n"
        "The range is **inclusive** of both `start_date` and `end_date`.\n\n"
        "For each project, the report includes:\n"
        "- Total number of days with logs in the range\n"
        "- Count of days with status: HAPPENED, MISSED, CANCELLED, NO_DATA, ERROR\n"
        "- Compliance percentage = HAPPENED / total_days * 100\n\n"
        "This endpoint is read-only and intended for dashboards, admin views, "
        "and process/leadership reporting."
    ),
    responses={
        200: {
            "description": "Weekly summary successfully computed.",
            "content": {
                "application/json": {
                    "example": {
                        "start_date": "2025-11-10",
                        "end_date": "2025-11-16",
                        "projects": [
                            {
                                "project_id": 1,
                                "project_key": "OCS",
                                "project_name": "OCS Platform",
                                "start_date": "2025-11-10",
                                "end_date": "2025-11-16",
                                "total_days": 5,
                                "happened_count": 3,
                                "missed_count": 1,
                                "cancelled_count": 0,
                                "no_data_count": 1,
                                "error_count": 0,
                                "compliance_pct": 60.0,
                            }
                        ],
                    }
                }
            },
        },
        422: {
            "description": "Validation error (e.g. missing or invalid dates).",
        },
    },
)
async def get_weekly_report(
    start_date: date_type = Query(
        ...,
        description=(
            "Start date (inclusive) of the reporting window, in ISO format "
            "(YYYY-MM-DD)."
        ),
        example="2025-11-10",
    ),
    end_date: date_type = Query(
        ...,
        description=(
            "End date (inclusive) of the reporting window, in ISO format "
            "(YYYY-MM-DD). Must be greater than or equal to start_date."
        ),
        example="2025-11-16",
    ),
    db: AsyncSession = Depends(get_db),
) -> WeeklySummary:
    """
    Compute and return a weekly (or arbitrary range) standup summary.

    The summary is based on `DailyStandupLog` entries in the given date range.
    Projects without any logs in the range will not appear in the result.
    """
    summary = await compute_weekly_summary(db, start_date=start_date, end_date=end_date)
    return summary