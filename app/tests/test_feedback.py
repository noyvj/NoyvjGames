"""Site-wide feedback (ACCOUNTS-AND-FEEDBACK-DESIGN.md): usable both
attached to a game and as general site feedback. Runs against the
in-memory sqlite DB substituted in conftest.py, never the real Neon
database.
"""

import threading

import pytest
from fastapi.testclient import TestClient

import main
from main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_rate_limit():
    """The rate limiter's log is an in-process module-level dict (see
    main.py) so it persists across tests in the same run unless cleared —
    without this, later tests would start already partway through (or
    over) the 5/hour limit from earlier tests hitting the same TestClient
    host."""
    main._feedback_submission_log.clear()
    yield
    main._feedback_submission_log.clear()


def test_create_game_feedback_requires_rating_or_comment():
    resp = client.post("/feedback", json={"game_id": "sol"})
    assert resp.status_code == 422


def test_create_game_feedback_with_rating_only():
    resp = client.post("/feedback", json={"game_id": "sol", "rating": 4})
    assert resp.status_code == 200
    body = resp.json()
    assert body["game_id"] == "sol"
    assert body["rating"] == 4
    assert body["user_id"] is None


def test_create_general_feedback_with_comment_only():
    resp = client.post("/feedback", json={"comment": "the save system is confusing"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["game_id"] is None
    assert body["comment"] == "the save system is confusing"


def test_rating_out_of_range_is_rejected():
    resp = client.post("/feedback", json={"game_id": "sol", "rating": 6})
    assert resp.status_code == 422


def test_list_feedback_with_game_id_filters_to_that_game():
    client.post("/feedback", json={"game_id": "canopy", "rating": 5})
    client.post("/feedback", json={"game_id": "grid", "rating": 3})

    resp = client.get("/feedback", params={"game_id": "canopy"})
    assert resp.status_code == 200
    assert all(row["game_id"] == "canopy" for row in resp.json())
    assert len(resp.json()) >= 1


def test_list_feedback_without_game_id_returns_only_general():
    client.post("/feedback", json={"comment": "general note one"})
    client.post("/feedback", json={"game_id": "tide", "rating": 2})

    resp = client.get("/feedback")
    assert resp.status_code == 200
    assert all(row["game_id"] is None for row in resp.json())


def test_hidden_feedback_is_excluded_from_listings():
    created = client.post("/feedback", json={"comment": "should be hidden later"}).json()

    # No admin endpoint exists yet (deliberately — direct DB edit per the
    # design doc's MVP moderation approach), so flip it via the ORM
    # directly, same as a human would via a DB console.
    from database import SessionLocal

    db = SessionLocal()
    row = db.query(main.Feedback).filter(main.Feedback.id == created["id"]).first()
    row.is_hidden = True
    db.commit()
    db.close()

    resp = client.get("/feedback")
    ids = [row["id"] for row in resp.json()]
    assert created["id"] not in ids


def test_anonymous_feedback_allowed():
    resp = client.post("/feedback", json={"game_id": "loop", "rating": 5})
    assert resp.status_code == 200
    assert resp.json()["user_id"] is None


def test_authenticated_feedback_records_user_id():
    bearer = client.post(
        "/auth/signup", json={"username": "feedback-user", "password": "pw"}
    ).json()["bearer_token"]

    resp = client.post(
        "/feedback",
        json={"game_id": "drift", "comment": "loved the coda"},
        headers={"Authorization": f"Bearer {bearer}"},
    )
    assert resp.status_code == 200
    assert resp.json()["user_id"] is not None


def test_feedback_rate_limit_blocks_after_five_per_hour():
    for _ in range(5):
        resp = client.post("/feedback", json={"comment": "spam-ish"})
        assert resp.status_code == 200

    resp = client.post("/feedback", json={"comment": "one too many"})
    assert resp.status_code == 429


def test_feedback_rate_limit_is_atomic_under_concurrent_requests():
    # PR #1 review finding: the read-check-append in
    # _check_feedback_rate_limit wasn't atomic, so concurrent requests from
    # the same IP on separate threadpool threads could each read the same
    # `recent` list before any of them wrote it back, letting more than
    # FEEDBACK_RATE_LIMIT_PER_HOUR through under a burst. Fires this many
    # times more than the limit, all at once via a barrier so they actually
    # overlap, directly against the checker (not the HTTP client, so this
    # isolates the race from any DB-layer serialization) and asserts exactly
    # the limit gets through — not "at most", which a flaky race could pass
    # by accident even when broken.
    attempts = main.FEEDBACK_RATE_LIMIT_PER_HOUR * 4
    client_ip = "203.0.113.1"  # TEST-NET-3 (RFC 5737), never a real caller
    barrier = threading.Barrier(attempts)
    allowed = []
    lock = threading.Lock()

    def attempt():
        barrier.wait()
        try:
            main._check_feedback_rate_limit(client_ip)
        except Exception:
            return
        with lock:
            allowed.append(1)

    threads = [threading.Thread(target=attempt) for _ in range(attempts)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(allowed) == main.FEEDBACK_RATE_LIMIT_PER_HOUR
