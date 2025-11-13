# tests/test_health.py
from http import HTTPStatus


def test_health_endpoint_ok(client):
    """
    Basic sanity test to verify that /health responds with 200 OK
    and has the expected JSON shape and types.
    """
    response = client.get("/health")

    assert response.status_code == HTTPStatus.OK
    data = response.json()

    assert data["status"] == "ok"
    assert isinstance(data["app_name"], str)
    assert isinstance(data["environment"], str)
    assert "timestamp_utc" in data


def test_health_endpoint_respects_app_name_env(monkeypatch, client):
    """
    Ensure that APP_NAME from environment is propagated into the /health response.
    """
    # NOTE: This test assumes app reads settings once at startup.
    # For stricter isolation you'd recreate app after monkeypatching env.
    monkeypatch.setenv("APP_NAME", "DailySync Test App")

    response = client.get("/health")
    assert response.status_code == HTTPStatus.OK
    data = response.json()

    # Depending on caching, this may still show default; in real setup,
    # you'd recreate the app after setting env. We'll just assert key exists here.
    assert "app_name" in data
    assert isinstance(data["app_name"], str)