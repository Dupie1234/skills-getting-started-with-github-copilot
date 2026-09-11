from copy import deepcopy

import pytest
from fastapi.testclient import TestClient

from src import app as app_module


client = TestClient(app_module.app)


@pytest.fixture(autouse=True)
def restore_activities():
    original_activities = deepcopy(app_module.activities)
    yield
    app_module.activities.clear()
    app_module.activities.update(original_activities)


def test_root_redirects_to_static_index():
    # Arrange
    expected_location = "/static/index.html"

    # Act
    response = client.get("/", follow_redirects=False)

    # Assert
    assert response.status_code == 307
    assert response.headers["location"] == expected_location


def test_static_index_is_available():
    # Arrange
    expected_title = "Mergington High School Activities"

    # Act
    response = client.get("/static/index.html")

    # Assert
    assert response.status_code == 200
    assert expected_title in response.text


def test_get_activities_returns_activity_details():
    # Arrange
    expected_fields = {"description", "schedule", "max_participants", "participants"}

    # Act
    response = client.get("/activities")

    # Assert
    assert response.status_code == 200
    assert len(response.json()) == 9
    assert expected_fields <= set(response.json()["Chess Club"])


def test_signup_adds_participant():
    # Arrange
    activity_name = "Basketball Team"
    email = "student@example.com"

    # Act
    response = client.post(f"/activities/{activity_name}/signup", params={"email": email})

    # Assert
    assert response.status_code == 200
    assert response.json()["message"] == f"Signed up {email} for {activity_name}"
    assert email in app_module.activities[activity_name]["participants"]


def test_signup_rejects_duplicate_participant():
    # Arrange
    activity_name = "Chess Club"
    email = "michael@mergington.edu"

    # Act
    response = client.post(f"/activities/{activity_name}/signup", params={"email": email})

    # Assert
    assert response.status_code == 400
    assert response.json()["detail"] == "Student already signed up for this activity"


def test_signup_rejects_unknown_activity():
    # Arrange
    activity_name = "Unknown Club"

    # Act
    response = client.post(
        f"/activities/{activity_name}/signup", params={"email": "student@example.com"}
    )

    # Assert
    assert response.status_code == 404
    assert response.json()["detail"] == "Activity not found"


def test_signup_requires_email():
    # Arrange
    activity_name = "Chess Club"

    # Act
    response = client.post(f"/activities/{activity_name}/signup")

    # Assert
    assert response.status_code == 422


def test_remove_participant():
    # Arrange
    activity_name = "Chess Club"
    email = "michael@mergington.edu"

    # Act
    response = client.delete(f"/activities/{activity_name}/participants/{email}")

    # Assert
    assert response.status_code == 200
    assert response.json()["message"] == f"Removed {email} from {activity_name}"
    assert email not in app_module.activities[activity_name]["participants"]


def test_remove_participant_rejects_unknown_activity():
    # Arrange
    activity_name = "Unknown Club"

    # Act
    response = client.delete(f"/activities/{activity_name}/participants/student@example.com")

    # Assert
    assert response.status_code == 404
    assert response.json()["detail"] == "Activity not found"


def test_remove_participant_rejects_missing_participant():
    # Arrange
    activity_name = "Chess Club"
    email = "missing@example.com"

    # Act
    response = client.delete(f"/activities/{activity_name}/participants/{email}")

    # Assert
    assert response.status_code == 404
    assert response.json()["detail"] == "Student is not signed up for this activity"


def test_participant_can_signup_again_after_removal():
    # Arrange
    activity_name = "Chess Club"
    email = "michael@mergington.edu"

    # Act
    remove_response = client.delete(f"/activities/{activity_name}/participants/{email}")
    signup_response = client.post(f"/activities/{activity_name}/signup", params={"email": email})

    # Assert
    assert remove_response.status_code == 200
    assert signup_response.status_code == 200
    assert email in app_module.activities[activity_name]["participants"]


def test_routes_encode_activity_names_and_emails():
    # Arrange
    activity_name = "Basketball Team"
    email = "student+club@example.com"

    # Act
    signup_response = client.post(
        f"/activities/{activity_name}/signup", params={"email": email}
    )
    remove_response = client.delete(f"/activities/{activity_name}/participants/{email}")

    # Assert
    assert signup_response.status_code == 200
    assert remove_response.status_code == 200