# app/api/routes/internal.py
from datetime import date as date_type

from fastapi import APIRouter, Depends, Query
from http import HTTPStatus
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.internal_auth import verify_internal_api_key
from app.db.session import get_db
from app.schemas.daily_standup_log import DailyCheckSummary
from app.services.daily_check import run_daily_standup_check

router = APIRouter(
    prefix="/internal",
    tags=["Internal"],
    dependencies=[Depends(verify_internal_api_key)],
)


@router.post(
    "/run-daily-check",
    response_model=DailyCheckSummary,
    status_code=HTTPStatus.OK,
    summary="Execute daily standup check for all active projects",
    description=(
        "Triggers the daily standup compliance check for **all active projects** for the "
        "given `standup_date` (defaults to today's date if not provided).\n\n"
        "This endpoint is intended to be called from a cron job, scheduler, or CI/CD "
        "pipeline and is protected via the `X-Internal-Api-Key` header when configured.\n\n"
        "Current placeholder behavior:\n"
        "- For every active project, a `DailyStandupLog` entry is created with status "
        "`NO_DATA`, attendance_count = 0 and duration_minutes = 0. "
        "Graph-based evaluation will be added later."
    ),
    responses={
        200: {
            "description": "Daily check executed successfully. A summary is returned.",
            "content": {
                "application/json": {
                    "example": {
                        "standup_date": "2025-11-14",
                        "total_projects_evaluated": 3,
                        "logs_created": 3,
                        "entries": [
                            {
                                "id": 1,
                                "project_id": 1,
                                "standup_date": "2025-11-14",
                                "scheduled_time": "10:30:00",
                                "status": "NO_DATA",
                                "attendance_count": 0,
                                "duration_minutes": 0.0,
                            }
                        ],
                    }
                }
            },
        },
        401: {
            "description": "Missing or invalid internal API key (if configured).",
        },
    },
)
async def trigger_daily_check(
    standup_date: date_type | None = Query(
        default=None,
        description=(
            "Business date for which to execute the check. "
            "If omitted, the server's current date will be used."
        ),
        example="2025-11-14",
    ),
    db: AsyncSession = Depends(get_db),
) -> DailyCheckSummary:
    """
    Run the daily standup compliance evaluation.

    In production this endpoint should be invoked by a scheduler once per day
    (e.g. via cron + curl) and will later integrate with Microsoft Graph to
    derive real attendance and duration metrics.
    """
    if standup_date is None:
        standup_date = date_type.today()

    summary = await run_daily_standup_check(db=db, standup_date=standup_date)
    return summary