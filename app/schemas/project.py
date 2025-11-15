# app/schemas/project.py

from __future__ import annotations

from datetime import time, datetime
from pydantic import BaseModel, Field, validator


# --------------------------------------------------------------------------
# Base schema shared by create/update/read
# --------------------------------------------------------------------------

class ProjectBase(BaseModel):
    """
    Shared fields used by ProjectCreate and ProjectUpdate.
    """
    name: str = Field(
        ...,
        description="Human-readable project name.",
        example="OCS Platform",
    )

    project_key: str = Field(
        ...,
        description="Short unique key for the project (used in reports and URLs).",
        example="OCS",
    )

    meeting_id: str = Field(
        ...,
        description="Microsoft Graph Meeting ID for this project's daily standup.",
        example="meeting-12345@tenant.onmicrosoft.com",
    )

    standup_time: time = Field(
        ...,
        description="Scheduled daily standup time (HH:MM:SS).",
        example="10:30:00",
    )

    is_active: bool = Field(
        default=True,
        description="Whether the project is active and included in standup checks.",
    )


# --------------------------------------------------------------------------
# Create schema (POST /projects)
# --------------------------------------------------------------------------

class ProjectCreate(ProjectBase):
    """
    Schema for creating a new project.
    All fields except is_active must be provided by the client.
    """
    pass


# --------------------------------------------------------------------------
# Update schema (PATCH /projects/{id})
# --------------------------------------------------------------------------

class ProjectUpdate(BaseModel):
    """
    Schema for updating a project.
    All fields are optional; only provided fields are updated.
    """
    name: str | None = Field(default=None)
    project_key: str | None = Field(default=None)
    meeting_id: str | None = Field(default=None)
    standup_time: time | None = Field(default=None)
    is_active: bool | None = Field(default=None)


# --------------------------------------------------------------------------
# Read schema (GET /projects, GET /projects/{id})
# --------------------------------------------------------------------------

class ProjectRead(ProjectBase):
    """
    Response schema for reading a project.
    Includes the DB-generated fields.
    """

    id: int = Field(
        ...,
        description="Auto-incremented project ID.",
        example=12,
    )

    created_at: datetime | None = Field(
        None,
        description="Timestamp when the project record was created (if available).",
    )

    updated_at: datetime | None = Field(
        None,
        description="Timestamp when the project record was last updated (if available).",
    )

    class Config:
        orm_mode = True