# app/services/daily_check.py
from datetime import date as date_type

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.daily_standup_log import DailyStandupLog
from app.models.project import Project
from app.schemas.daily_standup_log import DailyCheckSummary, DailyStandupLogRead, DailyStandupStatus


async def run_daily_standup_check(
    db: AsyncSession,
    standup_date: date_type,
) -> DailyCheckSummary:
    """
    Execute the daily standup compliance check for all active projects.

    Current behavior (placeholder):
    - For each active project, create a DailyStandupLog with:
        - status = NO_DATA
        - attendance_count = 0
        - duration_minutes = 0
    - This will later be replaced with real evaluation logic using Graph meeting data.

    Parameters
    ----------
    db:
        Open AsyncSession used for queries and persistence.
    standup_date:
        Date for which the check is being executed.

    Returns
    -------
    DailyCheckSummary:
        Summary of logs created during this run.
    """
    # Fetch all active projects
    stmt = select(Project).where(Project.is_active.is_(True))
    result = await db.execute(stmt)
    active_projects = list(result.scalars().all())

    log_entries: list[DailyStandupLog] = []

    for project in active_projects:
        log = DailyStandupLog(
            project_id=project.id,
            standup_date=standup_date,
            scheduled_time=project.standup_time,
            status=DailyStandupStatus.NO_DATA.value,
            attendance_count=0,
            duration_minutes=0.0,
            raw_metadata=None,
        )
        db.add(log)
        log_entries.append(log)

    # Assign primary keys without requiring a re-query
    await db.flush()
    await db.commit()

    read_entries = [
        DailyStandupLogRead.model_validate(log) for log in log_entries
    ]

    summary = DailyCheckSummary(
        standup_date=standup_date,
        total_projects_evaluated=len(active_projects),
        logs_created=len(read_entries),
        entries=read_entries,
    )
    return summary