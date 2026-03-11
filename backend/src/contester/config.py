from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy.pool import StaticPool

BACKEND_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(BACKEND_ROOT / ".env")

VALID_ENVIRONMENTS = {"development", "testing", "production"}


def _read_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default

    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(slots=True)
class Settings:
    app_name: str
    environment: str
    api_prefix: str
    debug: bool
    testing: bool
    secret_key: str
    database_uri: str
    sqlalchemy_engine_options: dict[str, object]
    session_cookie_secure: bool
    session_lifetime: timedelta
    json_sort_keys: bool = False

    def to_mapping(self) -> dict[str, object]:
        return {
            "APP_NAME": self.app_name,
            "APP_ENV": self.environment,
            "API_PREFIX": self.api_prefix,
            "DEBUG": self.debug,
            "TESTING": self.testing,
            "SECRET_KEY": self.secret_key,
            "JSON_SORT_KEYS": self.json_sort_keys,
            "SQLALCHEMY_DATABASE_URI": self.database_uri,
            "SQLALCHEMY_TRACK_MODIFICATIONS": False,
            "SQLALCHEMY_ENGINE_OPTIONS": self.sqlalchemy_engine_options,
            "SESSION_COOKIE_HTTPONLY": True,
            "SESSION_COOKIE_SAMESITE": "Lax",
            "SESSION_COOKIE_SECURE": self.session_cookie_secure,
            "PERMANENT_SESSION_LIFETIME": self.session_lifetime,
        }


def get_settings(environment: str | None = None) -> Settings:
    resolved_environment = (environment or os.getenv("APP_ENV", "development")).strip().lower()

    if resolved_environment not in VALID_ENVIRONMENTS:
        supported = ", ".join(sorted(VALID_ENVIRONMENTS))
        raise ValueError(
            f"Unsupported APP_ENV={resolved_environment!r}. Supported values: {supported}."
        )

    secret_key = os.getenv("SECRET_KEY")
    if not secret_key:
        if resolved_environment == "production":
            raise ValueError("SECRET_KEY must be set in production environment.")
        secret_key = "local-dev-secret-key"

    is_testing = resolved_environment == "testing"
    debug_default = resolved_environment == "development"

    if is_testing:
        database_uri = "sqlite+pysqlite:///:memory:"
        sqlalchemy_engine_options: dict[str, object] = {
            "poolclass": StaticPool,
            "connect_args": {
                "check_same_thread": False,
            },
        }
    else:
        database_uri = os.getenv(
            "DATABASE_URL",
            "postgresql+psycopg://contester:contester@127.0.0.1:55432/contester",
        )
        sqlalchemy_engine_options = {
            "pool_pre_ping": True,
        }

    return Settings(
        app_name=os.getenv("APP_NAME", "contester-backend"),
        environment=resolved_environment,
        api_prefix="/api/v1",
        debug=False if is_testing else _read_bool("APP_DEBUG", debug_default),
        testing=is_testing,
        secret_key=secret_key,
        database_uri=database_uri,
        sqlalchemy_engine_options=sqlalchemy_engine_options,
        session_cookie_secure=resolved_environment == "production",
        session_lifetime=timedelta(hours=12),
    )