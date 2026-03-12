from __future__ import annotations

from datetime import datetime, timezone

from flask import request
from werkzeug.exceptions import BadRequest


def get_json_object() -> dict[str, object]:
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        raise BadRequest("Request body must be a valid JSON object.")
    return payload


def read_required_string(
    payload: dict[str, object],
    field_name: str,
    *,
    max_length: int | None = None,
) -> str:
    value = payload.get(field_name)
    if not isinstance(value, str):
        raise BadRequest(f"Field {field_name!r} must be a string.")

    normalized = value.strip()
    if not normalized:
        raise BadRequest(f"Field {field_name!r} must not be empty.")

    if max_length is not None and len(normalized) > max_length:
        raise BadRequest(
            f"Field {field_name!r} must be at most {max_length} characters long."
        )

    return normalized


def read_optional_string(
    payload: dict[str, object],
    field_name: str,
    *,
    max_length: int | None = None,
) -> str | None:
    value = payload.get(field_name)
    if value is None:
        return None

    if not isinstance(value, str):
        raise BadRequest(f"Field {field_name!r} must be a string or null.")

    normalized = value.strip()
    if not normalized:
        return None

    if max_length is not None and len(normalized) > max_length:
        raise BadRequest(
            f"Field {field_name!r} must be at most {max_length} characters long."
        )

    return normalized


def read_required_int(
    payload: dict[str, object],
    field_name: str,
    *,
    min_value: int | None = None,
    max_value: int | None = None,
) -> int:
    value = payload.get(field_name)
    if isinstance(value, bool) or not isinstance(value, int):
        raise BadRequest(f"Field {field_name!r} must be an integer.")

    if min_value is not None and value < min_value:
        raise BadRequest(
            f"Field {field_name!r} must be greater than or equal to {min_value}."
        )

    if max_value is not None and value > max_value:
        raise BadRequest(
            f"Field {field_name!r} must be less than or equal to {max_value}."
        )

    return value


def read_optional_int(
    payload: dict[str, object],
    field_name: str,
    *,
    min_value: int | None = None,
    max_value: int | None = None,
) -> int | None:
    value = payload.get(field_name)
    if value is None:
        return None

    if isinstance(value, bool) or not isinstance(value, int):
        raise BadRequest(f"Field {field_name!r} must be an integer or null.")

    if min_value is not None and value < min_value:
        raise BadRequest(
            f"Field {field_name!r} must be greater than or equal to {min_value}."
        )

    if max_value is not None and value > max_value:
        raise BadRequest(
            f"Field {field_name!r} must be less than or equal to {max_value}."
        )

    return value


def read_optional_bool(payload: dict[str, object], field_name: str) -> bool | None:
    value = payload.get(field_name)
    if value is None:
        return None

    if not isinstance(value, bool):
        raise BadRequest(f"Field {field_name!r} must be a boolean or null.")

    return value


def read_optional_datetime(
    payload: dict[str, object],
    field_name: str,
) -> datetime | None:
    value = payload.get(field_name)
    if value is None:
        return None

    if not isinstance(value, str):
        raise BadRequest(f"Field {field_name!r} must be an ISO 8601 string or null.")

    normalized = value.strip()
    if not normalized:
        return None

    try:
        parsed = datetime.fromisoformat(normalized.replace("Z", "+00:00"))
    except ValueError as error:
        raise BadRequest(
            f"Field {field_name!r} must be a valid ISO 8601 datetime."
        ) from error

    if parsed.tzinfo is None:
        raise BadRequest(f"Field {field_name!r} must include timezone information.")

    return parsed.astimezone(timezone.utc)