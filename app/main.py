# app/main.py
from fastapi import FastAPI

from app.api.routes import health, projects, internal, reports
from app.core.config import get_settings
from app.db.session import init_db


def create_app() -> FastAPI:
    """
    Application factory for the DailySync Monitor service.
    """
    settings = get_settings()

    app = FastAPI(
        title=settings.APP_NAME,
        description=(
            "Backend service responsible for monitoring daily standups per project,\n"
            "evaluating compliance using Microsoft Graph meeting data, and generating\n"
            "weekly summary reports for the process team and leadership."
        ),
        version="0.1.0",
    )

    # Routers
    app.include_router(health.router)
    app.include_router(projects.router)
    app.include_router(internal.router)
    app.include_router(reports.router)

    @app.on_event("startup")
    async def on_startup() -> None:  # pragma: no cover
        await init_db()

    return app


app = create_app()