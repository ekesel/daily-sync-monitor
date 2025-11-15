# app/services/daily_check.py
from __future__ import annotations

import json
from datetime import date as date_type

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.daily_standup_log import DailyStandupLog
from app.models.project import Project
from app.schemas.daily_standup_log import (
    DailyCheckSummary,
    DailyStandupLogRead,
    DailyStandupStatus,
)
from app.schemas.meeting_evaluation import MeetingSnapshot
from app.services.attendance_resolver import AttendanceResolver
from app.services.graph_client import GraphClientError, get_graph_client
from app.services.meeting_normalizer import MeetingNormalizer
from app.services.meeting_resolver import GraphMeetingResolver
from app.services.standup_evaluator import StandupEvaluator


async def run_daily_standup_check(
    db: AsyncSession,
    standup_date: date_type,
) -> DailyCheckSummary:
    """
    Execute the daily standup compliance check for all active projects.

    Behavior
    --------
    - If Graph credentials and organizer id are properly configured:
        1) Resolve meeting occurrence for each project & date.
        2) Resolve attendance for each meeting.
        3) Normalize into MeetingSnapshot.
        4) Evaluate using business rules to derive final status.
        5) Persist DailyStandupLog with:
            - status
            - attendance_count
            - duration_minutes
            - raw_metadata (combined Graph payload as JSON string)
    - If Graph is not configured or fails:
        - Falls back to a NO_DATA status with zero counts and no raw metadata.

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

    settings = get_settings()

    # Try to construct Graph client & resolvers; if anything is misconfigured,
    # we gracefully fall back to NO_DATA.
    meeting_resolver: GraphMeetingResolver | None = None
    attendance_resolver: AttendanceResolver | None = None

    try:
        if (
            settings.GRAPH_TENANT_ID
            and settings.GRAPH_CLIENT_ID
            and settings.GRAPH_CLIENT_SECRET
            and settings.GRAPH_ORGANIZER_USER_ID
        ):
            graph_client = get_graph_client()
            meeting_resolver = GraphMeetingResolver(
                graph_client=graph_client,
                organizer_user_id=settings.GRAPH_ORGANIZER_USER_ID,
            )
            attendance_resolver = AttendanceResolver(graph_client=graph_client)
    except GraphClientError:
        # If we cannot construct a usable Graph client, resolvers remain None
        meeting_resolver = None
        attendance_resolver = None

    log_entries: list[DailyStandupLog] = []

    for project in active_projects:
        snapshot: MeetingSnapshot | None = None

        if meeting_resolver is not None and attendance_resolver is not None:
            try:
                occurrence = await meeting_resolver.resolve_meeting_occurrence(
                    meeting_id=project.meeting_id,
                    standup_date=standup_date,
                )
                attendance = await attendance_resolver.resolve_attendance(
                    meeting_id=project.meeting_id
                )
                snapshot = MeetingNormalizer.build_snapshot(
                    occurrence=occurrence,
                    attendance=attendance,
                )
            except GraphClientError:
                # On per-project Graph failures, snapshot remains None,
                # which will be evaluated as NO_DATA below.
                snapshot = None

        # Evaluate final status from snapshot (or NO_DATA if None)
        status_enum = StandupEvaluator.evaluate(snapshot)
        status_value = (
            status_enum.value
            if isinstance(status_enum, DailyStandupStatus)
            else str(status_enum)
        )

        attendance_count = snapshot.non_organizer_count if snapshot else 0
        duration_minutes = snapshot.duration_minutes if snapshot else 0.0
        raw_metadata = json.dumps(snapshot.raw) if snapshot and snapshot.raw else None

        # Idempotent behavior:
        # Check if a log already exists for (project_id, standup_date).
        existing_stmt = select(DailyStandupLog).where(
            DailyStandupLog.project_id == project.id,
            DailyStandupLog.standup_date == standup_date,
        )
        existing_result = await db.execute(existing_stmt)
        log = existing_result.scalar_one_or_none()

        if log is None:
            # Create new log
            log = DailyStandupLog(
                project_id=project.id,
                standup_date=standup_date,
                scheduled_time=project.standup_time,
            )
            db.add(log)

        # Update fields (both for new + existing logs)
        log.status = status_value
        log.attendance_count = attendance_count
        log.duration_minutes = duration_minutes
        log.raw_metadata = raw_metadata
        log.scheduled_time = project.standup_time  # in case time was changed

        log_entries.append(log)

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