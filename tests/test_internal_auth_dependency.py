# tests/test_internal_auth_dependency.py
from http import HTTPStatus

from app.api.dependencies import internal_auth as auth_module


class DummySettingsProd:
    APP_ENV = "prod"
    INTERNAL_API_KEY = "supersecret"


def test_internal_endpoint_401_when_key_missing_in_prod(monkeypatch, client):
    """
    In non-local env (APP_ENV='prod') with INTERNAL_API_KEY set, calling an
    /internal endpoint without the X-Internal-Api-Key header should return 401.
    """
    monkeypatch.setattr(auth_module, "get_settings", lambda: DummySettingsProd())

    resp = client.post("/internal/run-daily-check?standup_date=2025-11-10")
    assert resp.status_code == HTTPStatus.UNAUTHORIZED
    body = resp.json()
    assert "invalid or missing" in body["detail"].lower()


def test_internal_endpoint_401_when_key_wrong_in_prod(monkeypatch, client):
    """
    Wrong key => 401.
    """
    monkeypatch.setattr(auth_module, "get_settings", lambda: DummySettingsProd())

    resp = client.post(
        "/internal/run-daily-check?standup_date=2025-11-10",
        headers={"X-Internal-Api-Key": "wrong-key"},
    )
    assert resp.status_code == HTTPStatus.UNAUTHORIZED
    body = resp.json()
    assert "invalid or missing" in body["detail"].lower()


def test_internal_endpoint_200_when_key_correct_in_prod(monkeypatch, client):
    """
    Correct key => request goes through (200).
    """
    monkeypatch.setattr(auth_module, "get_settings", lambda: DummySettingsProd())

    resp = client.post(
        "/internal/run-daily-check?standup_date=2025-11-10",
        headers={"X-Internal-Api-Key": "supersecret"},
    )
    assert resp.status_code == HTTPStatus.OK
    data = resp.json()
    # Basic sanity check on payload shape
    assert "standup_date" in data
    assert data["standup_date"] == "2025-11-10"