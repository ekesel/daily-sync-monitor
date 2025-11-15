# tests/test_daily_check_idempotency.py
from datetime import date

import pytest
from sqlalchemy import select

from app.db.session import AsyncSessionLocal, init_db
from app.models.project import Project
from app.models.daily_standup_log import DailyStandupLog
from app.services.daily_check import run_daily_standup_check


@pytest.mark.asyncio
async def test_run_daily_check_is_idempotent_per_project_date():
    """
    Calling run_daily_standup_check multiple times for the same date and project
    should not create duplicate DailyStandupLog rows. Instead, the existing row
    must be updated in-place.
    """
    await init_db()

    async with AsyncSessionLocal() as session:
        # 1) Create a single active project
        project = Project(
            name="Idempotency Test Project",
            project_key="IDEMP_TEST",
            meeting_id="meeting-idempotent-123",
            standup_time="10:30:00",
            is_active=True,
        )
        session.add(project)
        await session.commit()
        await session.refresh(project)

        target_date = date(2025, 11, 15)

        # 2) First run: should create exactly one log row
        summary1 = await run_daily_standup_check(session, standup_date=target_date)
        assert summary1.total_projects_evaluated == 1
        assert summary1.logs_created == 1

        res1 = await session.execute(
            select(DailyStandupLog).where(
                DailyStandupLog.project_id == project.id,
                DailyStandupLog.standup_date == target_date,
            )
        )
        logs_after_first = res1.scalars().all()
        assert len(logs_after_first) == 1

        # Capture first status for comparison later
        first_status = logs_after_first[0].status

        # 3) Second run for the same date: should UPDATE the same row,
        # not create a new one.
        summary2 = await run_daily_standup_check(session, standup_date=target_date)
        assert summary2.total_projects_evaluated == 1
        assert summary2.logs_created == 1  # one log processed (created or updated)

        res2 = await session.execute(
            select(DailyStandupLog).where(
                DailyStandupLog.project_id == project.id,
                DailyStandupLog.standup_date == target_date,
            )
        )
        logs_after_second = res2.scalars().all()
        assert len(logs_after_second) == 1

        # Status may remain the same (e.g. NO_DATA), but the key requirement
        # is that no duplicate rows were created.
        second_status = logs_after_second[0].status
        assert second_status == first_status