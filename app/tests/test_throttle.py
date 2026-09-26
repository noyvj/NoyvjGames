"""Online-guessing brakes on login and save-code lookup; no account ids in public feedback."""

import main
from fastapi.testclient import TestClient
from main import app
from throttle import FailureLimiter

client = TestClient(app)


def setup_function():
    main.LOGIN_FAILURE_LIMITER.reset()
    main.LOGIN_IP_FAILURE_LIMITER.reset()
    main.SAVE_CODE_MISS_LIMITER.reset()


def test_limiter_counts_a_sliding_window():
    lim = FailureLimiter(max_failures=3, window_seconds=100)
    for t in (0, 10, 20):
        assert lim.blocked("k", now=t) is False
        lim.record_failure("k", now=t)
    assert lim.blocked("k", now=30) is True
    assert lim.blocked("other", now=30) is False
    assert lim.blocked("k", now=125) is False  # the early failures aged out (only t=20 left)
    lim.clear("k")
    assert lim.blocked("k", now=30) is False


def test_repeated_wrong_passwords_lock_that_username_out_for_a_while():
    client.post("/auth/signup", json={"username": "throttled1", "password": "correct-horse"})
    for _ in range(8):
        assert client.post("/auth/login", json={"username": "throttled1", "password": "nope"}).status_code == 401
    blocked = client.post("/auth/login", json={"username": "throttled1", "password": "correct-horse"})
    assert blocked.status_code == 429


def test_a_success_clears_the_counter():
    client.post("/auth/signup", json={"username": "throttled2", "password": "correct-horse"})
    for _ in range(5):
        client.post("/auth/login", json={"username": "throttled2", "password": "nope"})
    assert client.post("/auth/login", json={"username": "throttled2", "password": "correct-horse"}).status_code == 200
    for _ in range(7):
        client.post("/auth/login", json={"username": "throttled2", "password": "nope"})
    assert client.post("/auth/login", json={"username": "throttled2", "password": "correct-horse"}).status_code == 200


def test_one_machine_guessing_many_usernames_is_stopped_by_the_address_limit():
    for i in range(40):
        assert client.post("/auth/login", json={"username": f"ghost{i}", "password": "x"}).status_code == 401
    assert client.post("/auth/login", json={"username": "ghost-final", "password": "x"}).status_code == 429


def test_guessing_save_codes_is_stopped_but_a_real_code_is_not_counted():
    created = client.post("/saves", json={"game_id": "sol", "save_data": {"a": 1}}).json()
    for _ in range(3):
        assert client.get(f"/saves/{created['save_code']}").status_code == 200
    for i in range(40):
        assert client.get(f"/saves/ZZZZ-{i:04d}").status_code == 404
    assert client.get("/saves/ZZZZ-9999").status_code == 429
    assert client.get(f"/saves/{created['save_code']}").status_code == 429  # blocked address, even for a real code


def test_forwarded_header_picks_the_client_and_separates_buckets():
    for _ in range(40):
        client.get("/saves/NOPE-0000", headers={"X-Forwarded-For": "203.0.113.9"})
    assert client.get("/saves/NOPE-0000", headers={"X-Forwarded-For": "203.0.113.9"}).status_code == 429
    assert client.get("/saves/NOPE-0000", headers={"X-Forwarded-For": "203.0.113.10"}).status_code == 404


def test_public_feedback_listing_has_no_account_identifier():
    auth = client.post("/auth/signup", json={"username": "fbuser", "password": "correct-horse"}).json()
    headers = {"Authorization": f"Bearer {auth['bearer_token']}"}
    posted = client.post("/feedback", json={"game_id": "sol", "rating": 4, "comment": "fun"}, headers=headers)
    assert posted.status_code == 200
    rows = client.get("/feedback?game_id=sol").json()
    assert rows and all("user_id" not in row for row in rows)
