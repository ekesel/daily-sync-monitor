# app/api/routes/health.py
from datetime import datetime, timezone

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.core.config import get_settings


router = APIRouter(tags=["Health"])


class HealthResponse(BaseModel):
    """
    Response schema for the health check endpoint.
    """

    status: str = Field(
        ...,
        description="Overall health status of the DailySync Monitor service.",
        example="ok",
    )
    app_name: str = Field(
        ...,
        description="Human-friendly name of the running application.",
        example="DailySync Monitor",
    )
    environment: str = Field(
        ...,
        description="Current deployment environment (local/dev/stage/prod).",
        example="local",
    )
    timestamp_utc: datetime = Field(
        ...,
        description="Server-side timestamp (UTC) at which this health check was generated.",
        example="2025-01-01T10:30:00Z",
    )


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check for DailySync Monitor service",
    description=(
        "Lightweight endpoint to verify that the DailySync Monitor backend is "
        "up and responding.\n\n"
        "Typical use-cases:\n"
        "- Kubernetes / Docker / VM health probes\n"
        "- Uptime monitoring & alerting\n"
        "- Quick smoke-test after deployments\n"
    ),
    responses={
        200: {
            "description": "Service is healthy and responding as expected.",
            "content": {
                "application/json": {
                    "example": {
                        "status": "ok",
                        "app_name": "DailySync Monitor",
                        "environment": "local",
                        "timestamp_utc": "2025-01-01T10:30:00Z",
                    }
                }
            },
        }
    },
)
async def health_check() -> HealthResponse:
    """
    Returns the current health status of the service.

    This endpoint is intentionally simple and does **not** depend on external
    systems (DB, Graph API, etc.) so that it remains reliable even when
    downstream components are degraded.
    """
    settings = get_settings()
    return HealthResponse(
        status="ok",
        app_name=settings.APP_NAME,
        environment=settings.APP_ENV,
        timestamp_utc=datetime.now(tz=timezone.utc),
    )