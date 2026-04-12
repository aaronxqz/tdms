"""
tests/test_tasks.py

Tests for task chunk lifecycle: creation, assignment, ACK, completion,
dashboard counters, and search. This covers the core business logic
from Sections 3–7 of the spec.
"""


def _create_chunk(client, content="Study graphs", urgency="Low", time_period=3):
    return client.post("/tasks/", json={
        "content": content,
        "time_period": time_period,
        "urgency_label": urgency,
    })


# ── Creation ─────────────────────────────────────────────────────────────────

def test_create_task_chunk(client):
    """Basic creation returns 201 with REF-XXXX id and correct defaults."""
    r = _create_chunk(client)
    assert r.status_code == 201

    data = r.json()
    assert data["chunk_id"] == "REF-0001"
    assert data["status"] == "OK"
    assert data["urgency_label"] == "Low"
    assert data["urgency_level"] == 4
    assert len(data["status_history"]) == 1
    assert data["status_history"][0]["trigger"] == "CREATED"


def test_chunk_ids_are_sequential(client):
    r1 = _create_chunk(client, "First")
    r2 = _create_chunk(client, "Second")
    assert r1.json()["chunk_id"] == "REF-0001"
    assert r2.json()["chunk_id"] == "REF-0002"


def test_very_high_urgency_skips_waiting_list(client):
    """
    A Very High urgency chunk immediately becomes IN_PROGRESS,
    not waiting in the To-Be-Assigned list.
    """
    r = _create_chunk(client, urgency="Very High")
    assert r.status_code == 201
    assert r.json()["status"] == "IN_PROGRESS"


def test_create_chunk_invalid_urgency(client):
    """Sending an invalid urgency label returns 422 Unprocessable Entity."""
    r = client.post("/tasks/", json={
        "content": "Test",
        "time_period": 2,
        "urgency_label": "Ultra Mega High",
    })
    assert r.status_code == 422


def test_create_chunk_missing_content(client):
    r = client.post("/tasks/", json={"time_period": 2})
    assert r.status_code == 422


# ── Waiting list ──────────────────────────────────────────────────────────────

def test_waiting_list_sort_order(client):
    """
    Waiting list must be sorted: highest urgency first,
    then earliest creation time within the same urgency.
    """
    _create_chunk(client, "Low task A",    urgency="Low")
    _create_chunk(client, "High task",     urgency="High")
    _create_chunk(client, "Low task B",    urgency="Low")
    _create_chunk(client, "Medium task",   urgency="Medium")

    r = client.get("/tasks/waiting")
    assert r.status_code == 200
    items = r.json()

    labels = [i["urgency_label"] for i in items]
    # High should come first, then Medium, then Low A, Low B
    assert labels[0] == "High"
    assert labels[1] == "Medium"
    assert labels[2] == "Low"   # Low task A (created first)
    assert labels[3] == "Low"   # Low task B


def test_very_high_not_in_waiting_list(client):
    """Very High chunks must not appear in the waiting list."""
    _create_chunk(client, urgency="Very High")
    _create_chunk(client, urgency="Low")

    r = client.get("/tasks/waiting")
    items = r.json()
    for item in items:
        assert item["urgency_label"] != "Very High"


# ── Assignment ────────────────────────────────────────────────────────────────

def test_assign_task_chunk(client):
    """Assigning a chunk moves it to IN_PROGRESS with date and time set."""
    chunk_id = _create_chunk(client).json()["chunk_id"]

    r = client.post(f"/tasks/{chunk_id}/assign", json={
        "assigned_date": "2026-05-01T09:00:00",
        "start_time": "09:00",
    })
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "IN_PROGRESS"
    assert data["start_time"] == "09:00"

    # Should now appear in assigned list, not waiting list
    waiting = client.get("/tasks/waiting").json()
    assigned = client.get("/tasks/assigned").json()
    assert not any(c["chunk_id"] == chunk_id for c in waiting)
    assert any(c["chunk_id"] == chunk_id for c in assigned)


def test_assign_nonexistent_chunk(client):
    r = client.post("/tasks/REF-9999/assign", json={
        "assigned_date": "2026-05-01T09:00:00",
        "start_time": "09:00",
    })
    assert r.status_code == 404


# ── Breach ACK ────────────────────────────────────────────────────────────────

def test_ack_non_breach_chunk_returns_400(client):
    """Acknowledging a non-breached chunk (status OK) should return 400."""
    chunk_id = _create_chunk(client).json()["chunk_id"]
    r = client.post(f"/tasks/{chunk_id}/ack")
    assert r.status_code == 400


def test_ack_degrades_urgency(client):
    """
    Force a chunk into BREACH status by directly updating it,
    then ACK it — urgency should degrade from Medium (3) to Low (4).
    """
    chunk_id = _create_chunk(client, urgency="Medium").json()["chunk_id"]

    # Force into BREACH (simulating what the timer does)
    client.patch(f"/tasks/{chunk_id}", json={"status": "BREACH"})

    r = client.post(f"/tasks/{chunk_id}/ack")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "OK"
    assert data["urgency_label"] == "Low"    # degraded from Medium
    assert data["urgency_level"] == 4


def test_ack_at_very_low_stays_at_very_low(client):
    """
    A Very Low (level 5) chunk is already at the terminal level.
    Acknowledging should not push it past level 5.
    """
    chunk_id = _create_chunk(client, urgency="Very Low").json()["chunk_id"]
    client.patch(f"/tasks/{chunk_id}", json={"status": "BREACH"})

    r = client.post(f"/tasks/{chunk_id}/ack")
    assert r.status_code == 200
    assert r.json()["urgency_level"] == 5


# ── Completion / Failure ──────────────────────────────────────────────────────

def test_complete_task_chunk(client):
    chunk_id = _create_chunk(client).json()["chunk_id"]
    client.post(f"/tasks/{chunk_id}/assign", json={
        "assigned_date": "2026-05-01T09:00:00",
        "start_time": "09:00",
    })

    r = client.post(f"/tasks/{chunk_id}/complete")
    assert r.status_code == 200
    assert r.json()["status"] == "COMPLETED"


def test_fail_task_chunk(client):
    chunk_id = _create_chunk(client).json()["chunk_id"]
    r = client.post(f"/tasks/{chunk_id}/fail")
    assert r.status_code == 200
    assert r.json()["status"] == "FAILED"


# ── Dashboard counters ────────────────────────────────────────────────────────

def test_dashboard_counters(client):
    """
    Creates chunks in various states and verifies dashboard totals.
    This is an integration test — it exercises the full lifecycle.
    """
    # Create 3 waiting chunks
    ids = [_create_chunk(client, f"Task {i}").json()["chunk_id"] for i in range(3)]

    # Assign one
    client.post(f"/tasks/{ids[0]}/assign", json={
        "assigned_date": "2026-05-01T09:00:00",
        "start_time": "09:00",
    })

    # Complete one
    client.post(f"/tasks/{ids[1]}/assign", json={
        "assigned_date": "2026-05-01T10:00:00",
        "start_time": "10:00",
    })
    client.post(f"/tasks/{ids[1]}/complete")

    # Fail one
    client.post(f"/tasks/{ids[2]}/fail")

    r = client.get("/tasks/dashboard")
    assert r.status_code == 200
    data = r.json()
    assert data["waiting"] == 0        # all 3 moved out of waiting
    assert data["in_progress"] == 1
    assert data["completed"] == 1
    assert data["failed"] == 1
    assert data["breached"] == 0


# ── Search ────────────────────────────────────────────────────────────────────

def test_search_by_keyword(client):
    _create_chunk(client, "Study graph algorithms")
    _create_chunk(client, "Review dynamic programming")

    r = client.get("/tasks/search?keyword=graph")
    assert r.status_code == 200
    results = r.json()
    assert len(results) == 1
    assert "graph" in results[0]["content"].lower()


def test_search_by_status(client):
    ids = [_create_chunk(client, f"T{i}").json()["chunk_id"] for i in range(2)]
    client.post(f"/tasks/{ids[0]}/fail")

    r = client.get("/tasks/search?status=FAILED")
    assert r.status_code == 200
    assert len(r.json()) == 1


def test_search_returns_all_statuses(client):
    """Search must return completed/failed chunks too, not just waiting ones."""
    chunk_id = _create_chunk(client).json()["chunk_id"]
    client.post(f"/tasks/{chunk_id}/complete")

    r = client.get("/tasks/search?keyword=Study")
    assert r.status_code == 200
    assert len(r.json()) == 1
    assert r.json()[0]["status"] == "COMPLETED"


# ── Status history ────────────────────────────────────────────────────────────

def test_status_history_recorded(client):
    """
    History must grow with every state change.
    Create → Assign → Complete = 3 history entries.
    """
    chunk_id = _create_chunk(client).json()["chunk_id"]
    client.post(f"/tasks/{chunk_id}/assign", json={
        "assigned_date": "2026-05-01T09:00:00",
        "start_time": "09:00",
    })
    client.post(f"/tasks/{chunk_id}/complete")

    r = client.get(f"/tasks/{chunk_id}")
    history = r.json()["status_history"]

    assert len(history) == 3
    triggers = [h["trigger"] for h in history]
    assert triggers == ["CREATED", "MANUAL_ASSIGN", "COMPLETED"]
