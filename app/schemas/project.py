# app/models/project.py
from datetime import time

from sqlalchemy import Boolean, Column, Integer, String, Time, UniqueConstraint

from app.db.base import Base


class Project(Base):
    """
    Represents a single project being monitored by the DailySync Monitor service.

    Each project is linked to exactly one recurring daily standup meeting
    in Microsoft Graph, identified via `meeting_id`.
    """

    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    project_key = Column(
        String(100),
        nullable=False,
        unique=True,
        index=True,
        doc="Short identifier used in logs/reports, e.g. 'OCS', 'TATVA'.",
    )
    meeting_id = Column(
        String(512),
        nullable=False,
        doc="Graph meeting ID or join URL used to look up the recurring event.",
    )
    standup_time = Column(
        Time,
        nullable=False,
        doc="Configured local time of day when the daily standup normally occurs.",
    )
    is_active = Column(
        Boolean,
        nullable=False,
        default=True,
        doc="If False, the project is ignored during daily compliance checks.",
    )

    __table_args__ = (
        UniqueConstraint(
            "project_key",
            name="uq_projects_project_key",
        ),
    )

    def __repr__(self) -> str:
        return f"<Project id={self.id} key={self.project_key} name={self.name}>"