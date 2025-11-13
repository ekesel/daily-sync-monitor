# tests/test_projects_api.py
from http import HTTPStatus
from datetime import time


def _build_project_payload(
    name: str = "OCS Platform",
    project_key: str = "OCS",
    meeting_id: str = "9f4e7d5b-1234-5678-90ab-6a2dfb9d1ce1",
    standup_time: str = "10:30:00",
    is_active: bool = True,
) -> dict:
    return {
        "name": name,
        "project_key": project_key,
        "meeting_id": meeting_id,
        "standup_time": standup_time,
        "is_active": is_active,
    }


def test_create_project_success(client):
    """
    Creating a new project with a unique project_key should succeed
    and return a 201 with the created object.
    """
    payload = _build_project_payload(project_key="OCS_TEST")

    response = client.post("/projects", json=payload)
    assert response.status_code == HTTPStatus.CREATED

    data = response.json()
    assert data["name"] == payload["name"]
    assert data["project_key"] == payload["project_key"]
    assert data["meeting_id"] == payload["meeting_id"]
    assert data["standup_time"] == payload["standup_time"]
    assert data["is_active"] is True
    assert isinstance(data["id"], int)


def test_create_project_duplicate_key_rejected(client):
    """
    Creating two projects with the same project_key should result in
    a 400 Bad Request on the second attempt.
    """
    payload = _build_project_payload(project_key="DUPLICATE_KEY")

    first = client.post("/projects", json=payload)
    assert first.status_code == HTTPStatus.CREATED

    second = client.post("/projects", json=payload)
    assert second.status_code == HTTPStatus.BAD_REQUEST
    data = second.json()
    assert "already exists" in data["detail"]


def test_list_projects_returns_at_least_one(client):
    """
    Listing projects should return an array. After creating a project
    in previous tests, we expect at least one element.
    """
    response = client.get("/projects")
    assert response.status_code == HTTPStatus.OK

    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    # basic shape check
    sample = data[0]
    assert "id" in sample
    assert "name" in sample
    assert "project_key" in sample


def test_list_projects_filter_only_active(client):
    """
    Filtering with only_active=true should return projects where is_active is true.
    """
    # Create an inactive project for completeness
    payload_inactive = _build_project_payload(
        name="Inactive Project",
        project_key="INACTIVE_KEY",
        is_active=False,
    )
    client.post("/projects", json=payload_inactive)

    response = client.get("/projects?only_active=true")
    assert response.status_code == HTTPStatus.OK

    data = response.json()
    assert isinstance(data, list)
    for proj in data:
        assert proj["is_active"] is True


def test_get_project_by_id_and_update(client):
    """
    End-to-end test: create a project, fetch by ID, then patch some fields
    and verify they are updated.
    """
    payload = _build_project_payload(project_key="UPDATE_ME")
    create_resp = client.post("/projects", json=payload)
    assert create_resp.status_code == HTTPStatus.CREATED
    created = create_resp.json()
    project_id = created["id"]

    # Fetch by ID
    get_resp = client.get(f"/projects/{project_id}")
    assert get_resp.status_code == HTTPStatus.OK
    fetched = get_resp.json()
    assert fetched["project_key"] == "UPDATE_ME"

    # Patch update: change name and is_active
    patch_payload = {
        "name": "Updated OCS Platform",
        "is_active": False,
    }
    patch_resp = client.patch(f"/projects/{project_id}", json=patch_payload)
    assert patch_resp.status_code == HTTPStatus.OK
    updated = patch_resp.json()

    assert updated["name"] == "Updated OCS Platform"
    assert updated["is_active"] is False
    # project_key should be unchanged
    assert updated["project_key"] == "UPDATE_ME"


def test_update_project_conflicting_key_rejected(client):
    """
    Updating a project's project_key to a value already used by another
    project should be rejected with 400.
    """
    # Create two distinct projects
    first = client.post("/projects", json=_build_project_payload(project_key="KEY_A"))
    second = client.post("/projects", json=_build_project_payload(project_key="KEY_B"))
    assert first.status_code == HTTPStatus.CREATED
    assert second.status_code == HTTPStatus.CREATED

    second_id = second.json()["id"]

    # Attempt to update second project to use KEY_A
    patch_resp = client.patch(
        f"/projects/{second_id}",
        json={"project_key": "KEY_A"},
    )
    assert patch_resp.status_code == HTTPStatus.BAD_REQUEST
    data = patch_resp.json()
    assert "already exists" in data["detail"]