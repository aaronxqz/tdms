"""
tests/test_goals.py

Tests for the Goal API endpoints.
Each test function is independent — it gets its own clean database.

Reading these tests is also documentation: they show exactly what the
API is supposed to do and what it returns.
"""


def test_create_goal(client):
    """Creating a goal returns 201 with the correct fields."""
    response = client.post("/goals/", json={"title": "Complete CS344"})
    assert response.status_code == 201

    data = response.json()
    assert data["title"] == "Complete CS344"
    assert data["goal_id"].startswith("GOAL-")
    assert "created_at" in data


def test_create_goal_with_description(client):
    response = client.post("/goals/", json={
        "title": "Complete CS417",
        "description": "Numerical methods course",
    })
    assert response.status_code == 201
    assert response.json()["description"] == "Numerical methods course"


def test_list_goals_empty(client):
    """With no goals created, list returns an empty array."""
    response = client.get("/goals/")
    assert response.status_code == 200
    assert response.json() == []


def test_list_goals(client):
    """After creating two goals, list returns both."""
    client.post("/goals/", json={"title": "Goal A"})
    client.post("/goals/", json={"title": "Goal B"})

    response = client.get("/goals/")
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_get_goal_not_found(client):
    """Requesting a non-existent goal returns 404."""
    response = client.get("/goals/GOAL-999")
    assert response.status_code == 404


def test_goal_ids_are_sequential(client):
    """Goal IDs auto-increment correctly."""
    r1 = client.post("/goals/", json={"title": "First"})
    r2 = client.post("/goals/", json={"title": "Second"})
    assert r1.json()["goal_id"] == "GOAL-001"
    assert r2.json()["goal_id"] == "GOAL-002"
