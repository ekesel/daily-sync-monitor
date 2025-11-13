# app/db/base.py
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """
    Base class for all SQLAlchemy ORM models in the DailySync Monitor service.

    Every ORM model should inherit from this Base to ensure they are included
    when creating database tables.
    """
    pass