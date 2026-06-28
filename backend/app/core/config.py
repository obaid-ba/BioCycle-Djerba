"""Typed application configuration.

All runtime configuration is read from environment variables (or a local `.env`
file) and validated by Pydantic. Import the singleton `settings` everywhere —
never read `os.environ` directly. This gives us one validated source of truth
and fail-fast behavior on misconfiguration.
"""

from functools import lru_cache

from pydantic import PostgresDsn, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # ---- Application ----
    PROJECT_NAME: str = "BioCycle Djerba"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    API_PREFIX: str = "/api"

    # ---- CORS ----
    BACKEND_CORS_ORIGINS: list[str] = ["http://localhost:5173"]

    # ---- PostgreSQL ----
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "biocycle"
    POSTGRES_PASSWORD: str = "biocycle"
    POSTGRES_DB: str = "biocycle"

    # ---- Auth (consumed from Phase 1) ----
    JWT_SECRET_KEY: str = "change-me"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ---- Initial admin (used by scripts/seed_admin.py) ----
    FIRST_SUPERUSER_EMAIL: str = "admin@biocycle.local"
    FIRST_SUPERUSER_PASSWORD: str = "changeme123"
    FIRST_SUPERUSER_NAME: str = "BioCycle Admin"

    # ---- MQTT (Phase 4) ----
    MQTT_ENABLED: bool = True
    MQTT_HOST: str = "localhost"
    MQTT_PORT: int = 1883
    MQTT_USERNAME: str = ""
    MQTT_PASSWORD: str = ""
    MQTT_TOPIC: str = "biocycle/+/telemetry"

    # ---- AI service (Phase 5) ----
    AI_SERVICE_BASE_URL: str = "http://localhost:9000"
    AI_SERVICE_TIMEOUT_SECONDS: int = 10

    # ---- Alert thresholds (Phase 6) ----
    ALERT_FILL_THRESHOLD: float = 85.0
    ALERT_FILL_CRITICAL: float = 95.0
    ALERT_BATTERY_THRESHOLD: float = 15.0

    @computed_field
    @property
    def DATABASE_URL(self) -> str:  # noqa: N802 (settings-style constant name)
        """Async SQLAlchemy URL (asyncpg driver)."""
        return str(
            PostgresDsn.build(
                scheme="postgresql+asyncpg",
                username=self.POSTGRES_USER,
                password=self.POSTGRES_PASSWORD,
                host=self.POSTGRES_HOST,
                port=self.POSTGRES_PORT,
                path=self.POSTGRES_DB,
            )
        )

    @computed_field
    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() in {"production", "prod"}


@lru_cache
def get_settings() -> Settings:
    """Cached accessor so the env is parsed exactly once per process."""
    return Settings()


settings = get_settings()
