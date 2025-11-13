# app/db/base.py
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """
    Base class for all SQLAlchemy ORM models in the DailySync Monitor service.
    """
    pass


# Import ORM models so that Base.metadata is aware of them
# This import should stay at the bottom to avoid circular dependencies.
from app.models.project import Project  # noqa: E402,F401
from app.models.daily_standup_log import DailyStandupLog  # noqa: E402,F401