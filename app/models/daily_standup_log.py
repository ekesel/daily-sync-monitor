# app/models/daily_standup_log.py
from datetime import date, time

from sqlalchemy import Column, Date, Float, ForeignKey, Integer, String, Time, Text
from sqlalchemy.orm import relationship

from app.db.base import Base


class DailyStandupLog(Base):
    """
    Captures the outcome of the daily standup compliance check for a single project
    on a specific date.

    This model will later be enriched with real meeting data coming from
    Microsoft Graph (attendance, duration, etc.).
    """

    __tablename__ = "daily_standup_logs"

    id = Column(Integer, primary_key=True, index=True)

    project_id = Column(
        Integer,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # The date for which the standup check was performed (business date).
    standup_date = Column(Date, nullable=False, index=True)

    # Time of day the standup is expected to occur (copied from project.standup_time at check time).
    scheduled_time = Column(Time, nullable=False)

    # Current evaluation status for the given project and date.
    # For now: HAPPENED, MISSED, CANCELLED, NO_DATA, ERROR (string values).
    status = Column(
        String(32),
        nullable=False,
        default="NO_DATA",
        doc="Outcome of the check: HAPPENED/MISSED/CANCELLED/NO_DATA/ERROR.",
    )

    # Number of non-organizer attendees observed (when integrated with Graph).
    attendance_count = Column(
        Integer,
        nullable=False,
        default=0,
        doc="Number of non-organizer attendees present in the meeting.",
    )

    # Duration of the meeting in minutes, based on join/leave times.
    duration_minutes = Column(
        Float,
        nullable=False,
        default=0.0,
        doc="Observed meeting duration in minutes.",
    )

    # Optional JSON/serialized debug information from the Graph API response.
    raw_metadata = Column(
        Text,
        nullable=True,
        doc="Serialized metadata or debug information for this check.",
    )

    project = relationship("Project", backref="standup_logs")

    def __repr__(self) -> str:
        return (
            f"<DailyStandupLog id={self.id} project_id={self.project_id} "
            f"date={self.standup_date} status={self.status}>"
        )