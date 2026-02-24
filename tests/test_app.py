"""
Tests for the Mergington High School FastAPI application.
"""

import pytest
from fastapi.testclient import TestClient
from src.app import app, activities


ALL_ACTIVITY_NAMES = [
    "Chess Club",
    "Programming Class",
    "Gym Class",
    "Soccer Team",
    "Swimming Club",
    "Art Studio",
    "Drama Club",
    "Debate Team",
    "Science Olympiad",
]


@pytest.fixture(autouse=True)
def reset_activities():
    """Reset activity participants to their original state before each test."""
    original_state = {name: list(data["participants"]) for name, data in activities.items()}
    yield
    for name, original_participants in original_state.items():
        activities[name]["participants"] = original_participants


@pytest.fixture
def client():
    return TestClient(app)


# ── GET /activities ────────────────────────────────────────────────────────────

class TestGetActivities:
    def test_returns_200(self, client):
        response = client.get("/activities")
        assert response.status_code == 200

    def test_returns_json_content_type(self, client):
        response = client.get("/activities")
        assert "application/json" in response.headers["content-type"]

    def test_returns_dict(self, client):
        response = client.get("/activities")
        data = response.json()
        assert isinstance(data, dict)

    def test_contains_all_nine_activities(self, client):
        response = client.get("/activities")
        data = response.json()
        for name in ALL_ACTIVITY_NAMES:
            assert name in data, f"Missing activity: {name}"
        assert len(data) == 9

    def test_activity_has_required_fields(self, client):
        response = client.get("/activities")
        for name, details in response.json().items():
            assert "description" in details, f"{name} missing description"
            assert "schedule" in details, f"{name} missing schedule"
            assert "max_participants" in details, f"{name} missing max_participants"
            assert "participants" in details, f"{name} missing participants"

    def test_participants_is_list(self, client):
        response = client.get("/activities")
        for name, details in response.json().items():
            assert isinstance(details["participants"], list), f"{name} participants is not a list"

    def test_max_participants_is_positive_int(self, client):
        response = client.get("/activities")
        for name, details in response.json().items():
            assert isinstance(details["max_participants"], int)
            assert details["max_participants"] > 0


# ── POST /activities/{activity_name}/signup ────────────────────────────────────

class TestSignup:
    def test_successful_signup(self, client):
        response = client.post(
            "/activities/Chess Club/signup",
            params={"email": "newstudent@mergington.edu"},
        )
        assert response.status_code == 200
        assert "newstudent@mergington.edu" in response.json()["message"]

    def test_signup_adds_participant(self, client):
        email = "newstudent@mergington.edu"
        client.post("/activities/Chess Club/signup", params={"email": email})
        participants = client.get("/activities").json()["Chess Club"]["participants"]
        assert email in participants

    def test_signup_preserves_existing_participants(self, client):
        existing = list(activities["Chess Club"]["participants"])
        client.post("/activities/Chess Club/signup", params={"email": "new@mergington.edu"})
        participants = client.get("/activities").json()["Chess Club"]["participants"]
        for e in existing:
            assert e in participants

    def test_signup_nonexistent_activity_returns_404(self, client):
        response = client.post(
            "/activities/Nonexistent Activity/signup",
            params={"email": "student@mergington.edu"},
        )
        assert response.status_code == 404
        assert response.json()["detail"] == "Activity not found"

    def test_duplicate_signup_returns_400(self, client):
        email = "michael@mergington.edu"  # already in Chess Club
        response = client.post(
            "/activities/Chess Club/signup",
            params={"email": email},
        )
        assert response.status_code == 400
        assert response.json()["detail"] == "Student already signed up for this activity"

    def test_signup_missing_email_returns_422(self, client):
        response = client.post("/activities/Chess Club/signup")
        assert response.status_code == 422

    def test_signup_to_multiple_activities(self, client):
        email = "multisport@mergington.edu"
        client.post("/activities/Chess Club/signup", params={"email": email})
        client.post("/activities/Soccer Team/signup", params={"email": email})
        data = client.get("/activities").json()
        assert email in data["Chess Club"]["participants"]
        assert email in data["Soccer Team"]["participants"]

    def test_signup_activity_with_url_encoded_name(self, client):
        """Activities with spaces should be accessible via URL encoding."""
        response = client.post(
            "/activities/Programming%20Class/signup",
            params={"email": "urltest@mergington.edu"},
        )
        assert response.status_code == 200


# ── DELETE /activities/{activity_name}/signup ──────────────────────────────────

class TestUnregister:
    def test_successful_unregister(self, client):
        email = "michael@mergington.edu"  # pre-existing participant
        response = client.delete(
            "/activities/Chess Club/signup",
            params={"email": email},
        )
        assert response.status_code == 200
        assert email in response.json()["message"]

    def test_unregister_removes_participant(self, client):
        email = "michael@mergington.edu"
        client.delete("/activities/Chess Club/signup", params={"email": email})
        participants = client.get("/activities").json()["Chess Club"]["participants"]
        assert email not in participants

    def test_unregister_preserves_other_participants(self, client):
        client.delete(
            "/activities/Chess Club/signup",
            params={"email": "michael@mergington.edu"},
        )
        participants = client.get("/activities").json()["Chess Club"]["participants"]
        assert "daniel@mergington.edu" in participants

    def test_unregister_nonexistent_activity_returns_404(self, client):
        response = client.delete(
            "/activities/Nonexistent Activity/signup",
            params={"email": "student@mergington.edu"},
        )
        assert response.status_code == 404
        assert response.json()["detail"] == "Activity not found"

    def test_unregister_not_signed_up_returns_404(self, client):
        response = client.delete(
            "/activities/Chess Club/signup",
            params={"email": "notregistered@mergington.edu"},
        )
        assert response.status_code == 404
        assert response.json()["detail"] == "Student not signed up for this activity"

    def test_unregister_missing_email_returns_422(self, client):
        response = client.delete("/activities/Chess Club/signup")
        assert response.status_code == 422


# ── Integration / workflow tests ──────────────────────────────────────────────

class TestWorkflows:
    def test_signup_then_unregister(self, client):
        email = "workflow@mergington.edu"
        client.post("/activities/Chess Club/signup", params={"email": email})
        assert email in client.get("/activities").json()["Chess Club"]["participants"]

        client.delete("/activities/Chess Club/signup", params={"email": email})
        assert email not in client.get("/activities").json()["Chess Club"]["participants"]

    def test_signup_unregister_then_re_signup(self, client):
        email = "comeback@mergington.edu"
        client.post("/activities/Chess Club/signup", params={"email": email})
        client.delete("/activities/Chess Club/signup", params={"email": email})
        response = client.post("/activities/Chess Club/signup", params={"email": email})
        assert response.status_code == 200
        assert email in client.get("/activities").json()["Chess Club"]["participants"]

    def test_duplicate_signup_does_not_add_extra_entry(self, client):
        email = "michael@mergington.edu"
        count_before = client.get("/activities").json()["Chess Club"]["participants"].count(email)
        client.post("/activities/Chess Club/signup", params={"email": email})
        count_after = client.get("/activities").json()["Chess Club"]["participants"].count(email)
        assert count_after == count_before


# ── GET / (redirect) ──────────────────────────────────────────────────────────

class TestRoot:
    def test_root_redirects(self, client):
        response = client.get("/", follow_redirects=False)
        assert response.status_code in (301, 302, 307, 308)
        assert "/static/index.html" in response.headers["location"]

    def test_root_follow_redirect_serves_html(self, client):
        response = client.get("/", follow_redirects=True)
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]


# ── Static files ──────────────────────────────────────────────────────────────

class TestStaticFiles:
    def test_index_html_served(self, client):
        response = client.get("/static/index.html")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_app_js_served(self, client):
        response = client.get("/static/app.js")
        assert response.status_code == 200

    def test_styles_css_served(self, client):
        response = client.get("/static/styles.css")
        assert response.status_code == 200

    def test_nonexistent_static_returns_404(self, client):
        response = client.get("/static/does_not_exist.txt")
        assert response.status_code == 404


# ── Invalid routes / methods ──────────────────────────────────────────────────

class TestInvalidRoutes:
    def test_unknown_route_returns_404(self, client):
        response = client.get("/nonexistent")
        assert response.status_code == 404

    def test_put_on_signup_not_allowed(self, client):
        response = client.put(
            "/activities/Chess Club/signup",
            params={"email": "test@mergington.edu"},
        )
        assert response.status_code == 405

    def test_patch_on_activities_not_allowed(self, client):
        response = client.patch("/activities")
        assert response.status_code == 405
