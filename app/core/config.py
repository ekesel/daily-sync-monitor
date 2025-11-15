# app/core/config.py
from functools import lru_cache
from pydantic import BaseSettings, AnyHttpUrl, Field


class Settings(BaseSettings):
    """
    Global application configuration.

    Values are loaded from environment variables at runtime.

    These settings will be used later for:
    - DB connection
    - Graph API client credentials
    - Internal API key
    - Report recipients
    """

    APP_NAME: str = "DailySync Monitor"
    APP_ENV: str = Field("local", description="Environment name: local/dev/stage/prod")

    # Placeholder for future use (we'll wire these later)
    GRAPH_TENANT_ID: str | None = None
    GRAPH_CLIENT_ID: str | None = None
    GRAPH_CLIENT_SECRET: str | None = None
    GRAPH_BASE_URL: AnyHttpUrl | None = None

    DB_URL: str = Field(
        "sqlite+aiosqlite:///./daily_sync.db",
        description="SQLAlchemy-compatible database URL",
    )

    INTERNAL_API_KEY: str | None = Field(
        default=None,
        description="API key required for hitting /internal endpoints",
    )

    REPORT_EMAIL_RECIPIENTS: str | None = Field(
        default=None,
        description="Comma-separated list of email addresses for weekly reports.",
    )

    # --- SMTP / Email configuration ---
    SMTP_HOST: str | None = Field(
        default=None,
        description="SMTP server hostname for sending emails.",
    )
    SMTP_PORT: int = Field(
        default=587,
        description="SMTP server port (usually 587 for TLS).",
    )
    SMTP_USERNAME: str | None = Field(
        default=None,
        description="SMTP username (if authentication is required).",
    )
    SMTP_PASSWORD: str | None = Field(
        default=None,
        description="SMTP password (if authentication is required).",
    )
    SMTP_USE_TLS: bool = Field(
        default=True,
        description="Whether to use STARTTLS when connecting to SMTP.",
    )
    SMTP_FROM_ADDRESS: str | None = Field(
        default=None,
        description="From address used in weekly report emails.",
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """
    Cached accessor for application settings.

    Using LRU cache ensures settings are read and validated only once,
    while still being easily importable across the app.
    """
    return Settings()

GRAPH_ORGANIZER_USER_ID: str | None = Field(
        default=None,
        description=(
            "Default organizer user ID/email whose calendar will be queried "
            "for standup events when resolving meeting occurrences. "
            "This can later be moved to per-project configuration if needed."
        ),
    )