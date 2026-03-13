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
VALID_JUDGE_EXECUTION_BACKENDS = {"local", "docker"}


def _read_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default

    return value.strip().lower() in {"1", "true", "yes", "on"}


def _read_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default

    try:
        return int(value)
    except ValueError as error:
        raise ValueError(f"Environment variable {name!r} must be an integer.") from error


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
    judge_workspace_dir: Path
    max_source_code_length: int
    cxx_compiler: str
    cpp_compile_timeout_sec: int
    judge_execution_backend: str
    judge_docker_binary: str
    judge_docker_image: str
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
            "JUDGE_WORKSPACE_DIR": self.judge_workspace_dir,
            "MAX_SOURCE_CODE_LENGTH": self.max_source_code_length,
            "CXX_COMPILER": self.cxx_compiler,
            "CPP_COMPILE_TIMEOUT_SEC": self.cpp_compile_timeout_sec,
            "JUDGE_EXECUTION_BACKEND": self.judge_execution_backend,
            "JUDGE_DOCKER_BINARY": self.judge_docker_binary,
            "JUDGE_DOCKER_IMAGE": self.judge_docker_image,
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
        judge_workspace_dir = BACKEND_ROOT / ".runtime" / "judge-testing"
    else:
        database_uri = os.getenv(
            "DATABASE_URL",
            "postgresql+psycopg://contester:contester@127.0.0.1:55432/contester",
        )
        sqlalchemy_engine_options = {
            "pool_pre_ping": True,
        }
        workspace_from_env = os.getenv("JUDGE_WORKSPACE_DIR", "").strip()
        judge_workspace_dir = (
            Path(workspace_from_env)
            if workspace_from_env
            else BACKEND_ROOT / ".runtime" / "judge"
        )

    max_source_code_length = _read_int("MAX_SOURCE_CODE_LENGTH", 100000)
    if max_source_code_length < 1000:
        raise ValueError("MAX_SOURCE_CODE_LENGTH must be at least 1000.")

    cpp_compile_timeout_sec = _read_int("CPP_COMPILE_TIMEOUT_SEC", 15)
    if cpp_compile_timeout_sec < 1:
        raise ValueError("CPP_COMPILE_TIMEOUT_SEC must be at least 1.")

    cxx_compiler = os.getenv("CXX_COMPILER", "g++").strip()
    if not cxx_compiler:
        raise ValueError("CXX_COMPILER must not be empty.")

    judge_execution_backend = os.getenv("JUDGE_EXECUTION_BACKEND", "local").strip().lower()
    if judge_execution_backend not in VALID_JUDGE_EXECUTION_BACKENDS:
        supported = ", ".join(sorted(VALID_JUDGE_EXECUTION_BACKENDS))
        raise ValueError(
            "Unsupported JUDGE_EXECUTION_BACKEND="
            f"{judge_execution_backend!r}. Supported values: {supported}."
        )

    judge_docker_binary = os.getenv("JUDGE_DOCKER_BINARY", "docker").strip()
    if not judge_docker_binary:
        raise ValueError("JUDGE_DOCKER_BINARY must not be empty.")

    judge_docker_image = os.getenv("JUDGE_DOCKER_IMAGE", "contester-judge:local").strip()
    if not judge_docker_image:
        raise ValueError("JUDGE_DOCKER_IMAGE must not be empty.")

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
        judge_workspace_dir=judge_workspace_dir,
        max_source_code_length=max_source_code_length,
        cxx_compiler=cxx_compiler,
        cpp_compile_timeout_sec=cpp_compile_timeout_sec,
        judge_execution_backend=judge_execution_backend,
        judge_docker_binary=judge_docker_binary,
        judge_docker_image=judge_docker_image,
    )