# tests/test_daily_check_idempotency.py
from datetime import date

import pytest
from sqlalchemy import select
from datetime import time
from app.db.session import AsyncSessionLocal
from app.models.project import Project
from app.models.daily_standup_log import DailyStandupLog
from app.services.daily_check import run_daily_standup_check
from sqlalchemy import delete


@pytest.mark.asyncio
async def test_run_daily_check_is_idempotent_per_project_date():
    """
    Calling run_daily_standup_check multiple times for the same date and project
    should not create duplicate DailyStandupLog rows. Instead, the existing row
    must be updated in-place.
    """

    async with AsyncSessionLocal() as session:

        await session.execute(
            delete(Project).where(Project.project_key == "IDEMP_TEST")
        )
        await session.commit()

        # 1) Create a single active project
        project = Project(
            name="Idempotency Test Project",
            project_key="IDEMP_TEST",
            meeting_id="meeting-idempotent-123",
            standup_time=time(10, 30),
            is_active=True,
        )
        session.add(project)
        await session.commit()
        await session.refresh(project)

        target_date = date(2025, 11, 15)

        # 2) First run: should create exactly one log row
        summary1 = await run_daily_standup_check(session, standup_date=target_date)
        assert summary1.total_projects_evaluated >= 1  # other active projects may exist

        # Check DB: exactly one log for (this project, this date)
        result1 = await session.execute(
            select(DailyStandupLog).where(
                DailyStandupLog.project_id == project.id,
                DailyStandupLog.standup_date == target_date,
            )
        )
        logs1 = result1.scalars().all()
        assert len(logs1) == 1
        first_log = logs1[0]

        # 3) Second run: must NOT create a second row for the same project/date
        summary2 = await run_daily_standup_check(session, standup_date=target_date)
        assert summary2.total_projects_evaluated >= 1

        result2 = await session.execute(
            select(DailyStandupLog).where(
                DailyStandupLog.project_id == project.id,
                DailyStandupLog.standup_date == target_date,
            )
        )
        logs2 = result2.scalars().all()
        assert len(logs2) == 1  # still only one row

        # Ensure it's the same row (updated in-place if anything changed)
        second_log = logs2[0]
        assert second_log.id == first_log.id

        # Status may remain the same (e.g. NO_DATA), but the key requirement
        # is that no duplicate rows were created.
        second_status = second_log.status
        assert second_status == first_log.status