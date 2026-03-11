from __future__ import annotations

from http import HTTPStatus


def test_healthcheck_returns_expected_payload(client) -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == HTTPStatus.OK
    assert response.get_json() == {
        "status": "ok",
        "service": "contester-backend",
        "environment": "testing",
    }


def test_unknown_route_returns_json_error(client) -> None:
    response = client.get("/api/v1/does-not-exist")

    assert response.status_code == HTTPStatus.NOT_FOUND

    payload = response.get_json()
    assert payload is not None
    assert payload["error"]["code"] == "not_found"
    assert "not found" in payload["error"]["message"].lower()
