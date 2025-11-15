# tests/test_weekly_summary_service.py
from datetime import date

import pytest
from sqlalchemy import select

from app.db.session import AsyncSessionLocal, init_db
from app.models.project import Project
from app.models.daily_standup_log import DailyStandupLog
from app.schemas.daily_standup_log import DailyStandupStatus
from app.services.weekly_summary import compute_weekly_summary


@pytest.mark.asyncio
async def test_compute_weekly_summary_grouping_and_compliance():
    """
    Verify that compute_weekly_summary correctly groups logs by project,
    counts statuses, and computes compliance percentage.
    """
    await init_db()

    async with AsyncSessionLocal() as session:
        # Create two projects
        p1 = Project(
            name="OCS Platform",
            project_key="OCS",
            meeting_id="m-ocs",
            standup_time="10:30:00",
            is_active=True,
        )
        p2 = Project(
            name="Voice AI",
            project_key="VOICE_AI",
            meeting_id="m-voice",
            standup_time="11:00:00",
            is_active=True,
        )
        session.add_all([p1, p2])
        await session.commit()
        await session.refresh(p1)
        await session.refresh(p2)

        # Create logs for a 5-day window for p1:
        # Day1: HAPPENED
        # Day2: MISSED
        # Day3: HAPPENED
        # Day4: ERROR
        # Day5: NO_DATA
        base = date(2025, 11, 10)
        statuses_p1 = [
            DailyStandupStatus.HAPPENED,
            DailyStandupStatus.MISSED,
            DailyStandupStatus.HAPPENED,
            DailyStandupStatus.ERROR,
            DailyStandupStatus.NO_DATA,
        ]

        logs = []
        for idx, st in enumerate(statuses_p1):
            logs.append(
                DailyStandupLog(
                    project_id=p1.id,
                    standup_date=base.replace(day=base.day + idx),
                    scheduled_time="10:30:00",
                    status=st.value,
                    attendance_count=0,
                    duration_minutes=0.0,
                )
            )

        # For p2, only 2 days: one HAPPENED, one MISSED
        logs.append(
            DailyStandupLog(
                project_id=p2.id,
                standup_date=base,
                scheduled_time="11:00:00",
                status=DailyStandupStatus.HAPPENED.value,
                attendance_count=0,
                duration_minutes=0.0,
            )
        )
        logs.append(
            DailyStandupLog(
                project_id=p2.id,
                standup_date=base.replace(day=base.day + 1),
                scheduled_time="11:00:00",
                status=DailyStandupStatus.MISSED.value,
                attendance_count=0,
                duration_minutes=0.0,
            )
        )

        session.add_all(logs)
        await session.commit()

        # Compute weekly summary for the full range
        start = base
        end = base.replace(day=base.day + 4)

        summary = await compute_weekly_summary(session, start_date=start, end_date=end)

        assert summary.start_date == start
        assert summary.end_date == end
        assert len(summary.projects) == 2

        # Map by project_key for easier assertions
        by_key = {p.project_key: p for p in summary.projects}

        p1_summary = by_key["OCS"]
        assert p1_summary.total_days == 5
        assert p1_summary.happened_count == 2
        assert p1_summary.missed_count == 1
        assert p1_summary.error_count == 1
        assert p1_summary.no_data_count == 1
        assert p1_summary.cancelled_count == 0
        # Compliance: 2 / 5 = 40%
        assert 39.9 <= p1_summary.compliance_pct <= 40.1

        p2_summary = by_key["VOICE_AI"]
        assert p2_summary.total_days == 2
        assert p2_summary.happened_count == 1
        assert p2_summary.missed_count == 1
        assert p2_summary.error_count == 0
        assert p2_summary.no_data_count == 0
        assert p2_summary.cancelled_count == 0
        # Compliance: 1 / 2 = 50%
        assert 49.9 <= p2_summary.compliance_pct <= 50.1


@pytest.mark.asyncio
async def test_compute_weekly_summary_empty_range():
    """
    When there are no logs in the given range, the summary should contain
    an empty projects list.
    """
    await init_db()

    async with AsyncSessionLocal() as session:
        start = date(2025, 1, 1)
        end = date(2025, 1, 7)

        summary = await compute_weekly_summary(session, start_date=start, end_date=end)

        assert summary.start_date == start
        assert summary.end_date == end
        assert summary.projects == []


@pytest.mark.asyncio
async def test_compute_weekly_summary_invalid_dates():
    """
    If end_date < start_date, a ValueError should be raised.
    """
    await init_db()

    async with AsyncSessionLocal() as session:
        with pytest.raises(ValueError):
            await compute_weekly_summary(
                session,
                start_date=date(2025, 11, 20),
                end_date=date(2025, 11, 10),
            )