# app/models/daily_standup_log.py
from datetime import date, time

from sqlalchemy import (
    Column,
    Date,
    Float,
    ForeignKey,
    Integer,
    String,
    Time,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.db.base import Base


class DailyStandupLog(Base):
    """
    Captures the outcome of the daily standup compliance check for a single project
    on a specific date.
    """

    __tablename__ = "daily_standup_logs"

    id = Column(Integer, primary_key=True, index=True)

    project_id = Column(
        Integer,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    standup_date = Column(Date, nullable=False, index=True)
    scheduled_time = Column(Time, nullable=False)

    status = Column(
        String(32),
        nullable=False,
        default="NO_DATA",
    )

    attendance_count = Column(
        Integer,
        nullable=False,
        default=0,
    )

    duration_minutes = Column(
        Float,
        nullable=False,
        default=0.0,
    )

    raw_metadata = Column(
        Text,
        nullable=True,
    )

    project = relationship("Project", backref="standup_logs")

    __table_args__ = (
        UniqueConstraint(
            "project_id",
            "standup_date",
            name="uq_daily_standup_logs_project_date",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<DailyStandupLog id={self.id} project_id={self.project_id} "
            f"date={self.standup_date} status={self.status}>"
        )