# app/api/routes/projects.py
from http import HTTPStatus
from datetime import date as date_type
from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from operator import and_
from app.db.session import get_db
from app.models.project import Project
from app.models.daily_standup_log import DailyStandupLog
from app.schemas.project import ProjectCreate, ProjectRead, ProjectUpdate
from app.schemas.daily_standup_log import DailyStandupLogRead
from app.schemas.weekly_report import WeeklyProjectSummary
from app.services.weekly_summary import compute_project_summary

router = APIRouter(prefix="/projects", tags=["Projects"])


@router.post(
    "",
    response_model=ProjectRead,
    status_code=HTTPStatus.CREATED,
    summary="Create a new monitored project",
    description=(
        "Register a new project to be monitored by the DailySync Monitor.\n\n"
        "Each project must be linked to exactly one recurring daily standup meeting "
        "via the `meeting_id` field, and must define a `standup_time` at which the "
        "check is expected to occur.\n\n"
        "Typical usage:\n"
        "- Onboarding a new client/squad\n"
        "- Enabling monitoring for an existing project that recently adopted daily standups"
    ),
    responses={
        201: {
            "description": "Project successfully created.",
            "content": {
                "application/json": {
                    "example": {
                        "id": 1,
                        "name": "OCS Platform",
                        "project_key": "OCS",
                        "meeting_id": "9f4e7d5b-1234-5678-90ab-6a2dfb9d1ce1",
                        "standup_time": "10:30:00",
                        "is_active": True,
                    }
                }
            },
        },
        400: {
            "description": "A project with the same project_key already exists.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Project with key 'OCS' already exists.",
                    }
                }
            },
        },
    },
)
async def create_project(
    payload: ProjectCreate,
    db: AsyncSession = Depends(get_db),
) -> ProjectRead:
    """
    Create a new project configuration.

    Enforces uniqueness of `project_key` to avoid duplicate logical identifiers.
    """
    # Check uniqueness of project_key
    existing_stmt = select(Project).where(Project.project_key == payload.project_key)
    existing_result = await db.execute(existing_stmt)
    existing_project = existing_result.scalar_one_or_none()

    if existing_project is not None:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail=f"Project with key '{payload.project_key}' already exists.",
        )

    project = Project(
        name=payload.name,
        project_key=payload.project_key,
        meeting_id=payload.meeting_id,
        standup_time=payload.standup_time,
        is_active=payload.is_active,
    )
    db.add(project)
    await db.commit()
    await db.refresh(project)

    return ProjectRead.model_validate(project)


@router.get(
    "",
    response_model=list[ProjectRead],
    summary="List all monitored projects",
    description=(
        "Return all projects currently configured in the DailySync Monitor.\n\n"
        "Optional filters can be used to show only active or inactive projects."
    ),
    responses={
        200: {
            "description": "List of projects returned successfully.",
            "content": {
                "application/json": {
                    "example": [
                        {
                            "id": 1,
                            "name": "OCS Platform",
                            "project_key": "OCS",
                            "meeting_id": "9f4e7d5b-1234-5678-90ab-6a2dfb9d1ce1",
                            "standup_time": "10:30:00",
                            "is_active": True,
                        },
                        {
                            "id": 2,
                            "name": "Voice AI",
                            "project_key": "VOICE_AI",
                            "meeting_id": "https://teams.microsoft.com/l/meetup-join/...",
                            "standup_time": "11:00:00",
                            "is_active": False,
                        },
                    ]
                }
            },
        }
    },
)
async def list_projects(
    only_active: bool | None = Query(
        default=None,
        description=(
            "If true, returns only projects where `is_active` is true. "
            "If false, returns only inactive projects. If omitted, returns all."
        ),
        example=True,
    ),
    db: AsyncSession = Depends(get_db),
) -> list[ProjectRead]:
    """
    Fetch all projects, optionally filtered by active/inactive status.
    """
    stmt = select(Project)
    if only_active is True:
        stmt = stmt.where(Project.is_active.is_(True))
    elif only_active is False:
        stmt = stmt.where(Project.is_active.is_(False))

    result = await db.execute(stmt.order_by(Project.id.asc()))
    projects = result.scalars().all()

    return [ProjectRead.model_validate(p) for p in projects]


@router.get(
    "/{project_id}",
    response_model=ProjectRead,
    summary="Get project details by ID",
    description=(
        "Retrieve the configuration of a single project by its numeric identifier.\n\n"
        "This is typically used for admin/configuration screens or debugging."
    ),
    responses={
        200: {
            "description": "Project found and returned.",
        },
        404: {
            "description": "No project exists with the given ID.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Project with id 42 not found.",
                    }
                }
            },
        },
    },
)
async def get_project(
    project_id: int = Path(
        ...,
        description="Numeric ID of the project to retrieve.",
        ge=1,
        example=1,
    ),
    db: AsyncSession = Depends(get_db),
) -> ProjectRead:
    """
    Fetch a single project by its ID.
    """
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()

    if project is None:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=f"Project with id {project_id} not found.",
        )

    return ProjectRead.model_validate(project)


@router.patch(
    "/{project_id}",
    response_model=ProjectRead,
    summary="Partially update an existing project",
    description=(
        "Update project configuration fields such as `meeting_id`, `standup_time`, "
        "or `is_active` without recreating the project.\n\n"
        "Only fields provided in the request body will be modified."
    ),
    responses={
        200: {
            "description": "Project updated successfully.",
        },
        400: {
            "description": "Attempted to change `project_key` to a value that already exists.",
        },
        404: {
            "description": "No project exists with the given ID.",
        },
    },
)
async def update_project(
    project_id: int = Path(
        ...,
        description="Numeric ID of the project to update.",
        ge=1,
        example=1,
    ),
    payload: ProjectUpdate | None = None,
    db: AsyncSession = Depends(get_db),
) -> ProjectRead:
    """
    Apply partial updates to a project.

    If `project_key` is changed, uniqueness is enforced to avoid duplicates.
    """
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()

    if project is None:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=f"Project with id {project_id} not found.",
        )

    if payload is None:
        # Nothing to update; return current state
        return ProjectRead.model_validate(project)

    update_data = payload.model_dump(exclude_unset=True)

    # Handle project_key uniqueness if being updated
    new_project_key = update_data.get("project_key")
    if new_project_key and new_project_key != project.project_key:
        existing_stmt = select(Project).where(Project.project_key == new_project_key)
        existing_result = await db.execute(existing_stmt)
        existing = existing_result.scalar_one_or_none()
        if existing is not None:
            raise HTTPException(
                status_code=HTTPStatus.BAD_REQUEST,
                detail=f"Project with key '{new_project_key}' already exists.",
            )

    for field, value in update_data.items():
        setattr(project, field, value)

    await db.commit()
    await db.refresh(project)

    return ProjectRead.model_validate(project)


@router.get(
    "/{project_id}/logs",
    response_model=list[DailyStandupLogRead],
    status_code=HTTPStatus.OK,
    summary="List standup logs for a project",
    description=(
        "Return the day-wise standup logs for a given project, optionally filtered "
        "by a date range.\n\n"
        "Use this endpoint to debug why a project shows low compliance by "
        "inspecting daily statuses (HAPPENED, MISSED, CANCELLED, NO_DATA, ERROR) "
        "and associated metrics like attendance count and duration.\n\n"
        "- If `from_date` and `to_date` are both omitted, all logs for the project "
        "  are returned.\n"
        "- If only `from_date` is provided, logs from that date onwards are returned.\n"
        "- If only `to_date` is provided, logs up to that date are returned."
    ),
)
async def list_project_logs(
    project_id: int = Path(
        ...,
        description="Numeric ID of the project whose logs should be listed.",
        example=1,
    ),
    from_date: date_type | None = Query(
        default=None,
        description=(
            "Start date (inclusive) of the log window in ISO format (YYYY-MM-DD). "
            "If omitted, no lower bound is applied."
        ),
        example="2025-11-10",
    ),
    to_date: date_type | None = Query(
        default=None,
        description=(
            "End date (inclusive) of the log window in ISO format (YYYY-MM-DD). "
            "If omitted, no upper bound is applied."
        ),
        example="2025-11-16",
    ),
    db: AsyncSession = Depends(get_db),
) -> list[DailyStandupLogRead]:
    """
    List DailyStandupLog entries for a specific project with optional date filtering.
    """
    # Ensure project exists
    project_stmt = select(Project).where(Project.id == project_id)
    project_result = await db.execute(project_stmt)
    project = project_result.scalar_one_or_none()
    if project is None:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=f"Project with id={project_id} not found.",
        )

    # Build base query for logs
    conditions = [DailyStandupLog.project_id == project_id]

    if from_date is not None:
        conditions.append(DailyStandupLog.standup_date >= from_date)
    if to_date is not None:
        conditions.append(DailyStandupLog.standup_date <= to_date)

    logs_stmt = (
        select(DailyStandupLog)
        .where(and_(*conditions))
        .order_by(DailyStandupLog.standup_date.asc())
    )

    logs_result = await db.execute(logs_stmt)
    logs = list(logs_result.scalars().all())

    return [DailyStandupLogRead.model_validate(log) for log in logs]

@router.get(
    "/{project_id}/summary",
    response_model=WeeklyProjectSummary,
    status_code=HTTPStatus.OK,
    summary="Get aggregate standup summary for a project",
    description=(
        "Return an aggregate standup summary for a single project over a given "
        "date range.\n\n"
        "This is essentially the single-project version of `/reports/weekly`, "
        "and is useful for dashboards and tooling.\n\n"
        "The summary includes:\n"
        "- Total days with logs in the range\n"
        "- Count of HAPPENED / MISSED / CANCELLED / NO_DATA / ERROR\n"
        "- Compliance percentage (HAPPENED / total_days * 100)\n\n"
        "If the project exists but no logs are present in the range, a summary "
        "with `total_days = 0` and all counts = 0 will be returned."
    ),
)
async def get_project_summary(
    project_id: int = Path(
        ...,
        description="Numeric ID of the project.",
        example=1,
    ),
    from_date: date_type = Query(
        ...,
        description="Start date (inclusive) in ISO format (YYYY-MM-DD).",
        example="2025-11-10",
    ),
    to_date: date_type = Query(
        ...,
        description="End date (inclusive) in ISO format (YYYY-MM-DD).",
        example="2025-11-16",
    ),
    db: AsyncSession = Depends(get_db),
) -> WeeklyProjectSummary:
    """
    Aggregate view per project for dashboards/tools.
    """
    try:
        summary = await compute_project_summary(
            db=db,
            project_id=project_id,
            start_date=from_date,
            end_date=to_date,
        )
    except LookupError:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=f"Project with id={project_id} not found.",
        )
    except ValueError as exc:
        # e.g., end_date < from_date
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail=str(exc),
        )

    return summary