# app/services/weekly_summary.py
from __future__ import annotations

from collections import defaultdict
from datetime import date as date_type
from typing import Dict, List

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.daily_standup_log import DailyStandupLog
from app.models.project import Project
from app.schemas.daily_standup_log import DailyStandupStatus
from app.schemas.weekly_report import WeeklyProjectSummary, WeeklySummary


async def compute_weekly_summary(
    db: AsyncSession,
    start_date: date_type,
    end_date: date_type,
) -> WeeklySummary:
    """
    Compute weekly (or arbitrary range) standup summaries per project.

    Steps
    -----
    1) Fetch all DailyStandupLog entries within [start_date, end_date].
    2) Group them by project.
    3) For each project, count statuses:
        - HAPPENED
        - MISSED
        - CANCELLED
        - NO_DATA
        - ERROR
    4) Compute:
        - total_days = number of log entries in the range
        - compliance_pct = HAPPENED / total_days * 100 (0 if total_days == 0)

    Returns
    -------
    WeeklySummary
        Aggregated summary containing one WeeklyProjectSummary per project.
    """
    if end_date < start_date:
        raise ValueError("end_date must be greater than or equal to start_date")

    # Fetch logs joined with projects so we have names/keys in one go.
    stmt = (
        select(DailyStandupLog, Project)
        .join(Project, DailyStandupLog.project_id == Project.id)
        .where(
            and_(
                DailyStandupLog.standup_date >= start_date,
                DailyStandupLog.standup_date <= end_date,
            )
        )
        .order_by(Project.id, DailyStandupLog.standup_date)
    )

    result = await db.execute(stmt)
    rows: List[tuple[DailyStandupLog, Project]] = list(result.all())

    # Group logs by project
    logs_by_project: Dict[int, Dict[str, object]] = defaultdict(
        lambda: {
            "project": None,
            "logs": [],
        }
    )

    for log, project in rows:
        data = logs_by_project[project.id]
        data["project"] = project
        data["logs"].append(log)

    summaries: list[WeeklyProjectSummary] = []

    for project_id, data in logs_by_project.items():
        project: Project = data["project"]  # type: ignore[assignment]
        logs: List[DailyStandupLog] = data["logs"]  # type: ignore[assignment]

        total_days = len(logs)

        counts = {
            DailyStandupStatus.HAPPENED: 0,
            DailyStandupStatus.MISSED: 0,
            DailyStandupStatus.CANCELLED: 0,
            DailyStandupStatus.NO_DATA: 0,
            DailyStandupStatus.ERROR: 0,
        }

        for log in logs:
            # log.status is stored as string; normalize to enum if possible.
            try:
                status_enum = DailyStandupStatus(log.status)
            except ValueError:
                # Unknown status; treat as NO_DATA to be safe.
                status_enum = DailyStandupStatus.NO_DATA

            if status_enum in counts:
                counts[status_enum] += 1

        happened = counts[DailyStandupStatus.HAPPENED]
        missed = counts[DailyStandupStatus.MISSED]
        cancelled = counts[DailyStandupStatus.CANCELLED]
        no_data = counts[DailyStandupStatus.NO_DATA]
        error = counts[DailyStandupStatus.ERROR]

        if total_days > 0:
            compliance_pct = (happened / float(total_days)) * 100.0
        else:
            compliance_pct = 0.0

        summaries.append(
            WeeklyProjectSummary(
                project_id=project.id,
                project_key=project.project_key,
                project_name=project.name,
                start_date=start_date,
                end_date=end_date,
                total_days=total_days,
                happened_count=happened,
                missed_count=missed,
                cancelled_count=cancelled,
                no_data_count=no_data,
                error_count=error,
                compliance_pct=round(compliance_pct, 2),
            )
        )

    return WeeklySummary(
        start_date=start_date,
        end_date=end_date,
        projects=summaries,
    )

async def compute_project_summary(
    db: AsyncSession,
    project_id: int,
    start_date: date_type,
    end_date: date_type,
) -> WeeklyProjectSummary:
    """
    Compute an aggregate standup summary for a single project over a date range.

    This is essentially a single-project variant of `compute_weekly_summary`.
    If the project exists but has no logs in the given range, a summary with
    total_days = 0 and all counts = 0 will be returned.
    """
    if end_date < start_date:
        raise ValueError("end_date must be greater than or equal to start_date")

    # Ensure the project exists
    proj_stmt = select(Project).where(Project.id == project_id)
    proj_res = await db.execute(proj_stmt)
    project = proj_res.scalar_one_or_none()
    if project is None:
        raise LookupError(f"Project with id={project_id} not found")

    # Fetch logs for this project in the date range
    logs_stmt = (
        select(DailyStandupLog)
        .where(
            and_(
                DailyStandupLog.project_id == project_id,
                DailyStandupLog.standup_date >= start_date,
                DailyStandupLog.standup_date <= end_date,
            )
        )
        .order_by(DailyStandupLog.standup_date)
    )

    logs_res = await db.execute(logs_stmt)
    logs: List[DailyStandupLog] = list(logs_res.scalars().all())

    total_days = len(logs)

    counts = {
        DailyStandupStatus.HAPPENED: 0,
        DailyStandupStatus.MISSED: 0,
        DailyStandupStatus.CANCELLED: 0,
        DailyStandupStatus.NO_DATA: 0,
        DailyStandupStatus.ERROR: 0,
    }

    for log in logs:
        try:
            status_enum = DailyStandupStatus(log.status)
        except ValueError:
            status_enum = DailyStandupStatus.NO_DATA

        if status_enum in counts:
            counts[status_enum] += 1

    happened = counts[DailyStandupStatus.HAPPENED]
    missed = counts[DailyStandupStatus.MISSED]
    cancelled = counts[DailyStandupStatus.CANCELLED]
    no_data = counts[DailyStandupStatus.NO_DATA]
    error = counts[DailyStandupStatus.ERROR]

    if total_days > 0:
        compliance_pct = (happened / float(total_days)) * 100.0
    else:
        compliance_pct = 0.0

    return WeeklyProjectSummary(
        project_id=project.id,
        project_key=project.project_key,
        project_name=project.name,
        start_date=start_date,
        end_date=end_date,
        total_days=total_days,
        happened_count=happened,
        missed_count=missed,
        cancelled_count=cancelled,
        no_data_count=no_data,
        error_count=error,
        compliance_pct=round(compliance_pct, 2),
    )