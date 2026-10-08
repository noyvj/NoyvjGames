"""QA-1/QA-2 backend pass: body-size cap, text-length caps, write rate limits,
limiter memory bound, stats cache slimming, vote race."""

import main
import stats
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError

import account_data
from database import SessionLocal
from main import app
from models import HelpfulVote
from throttle import FailureLimiter

client = TestClient(app)


def test_oversized_body_is_refused_before_parsing():
    big = {"game_id": "bulk", "save_data": {"blob": "x" * (main.MAX_BODY_BYTES + 10)}}
    response = client.post("/saves", json=big)
    assert response.status_code == 413
    assert response.json()["detail"] == "Request body too large"


def test_413_carries_cors_headers_so_the_browser_can_read_it():
    response = client.post(
        "/saves", json={"game_id": "bulk", "save_data": {"blob": "x" * (main.MAX_BODY_BYTES + 10)}},
        headers={"Origin": "https://noyvj.github.io"},
    )
    assert response.status_code == 413
    assert response.headers.get("access-control-allow-origin") == "https://noyvj.github.io"


def test_a_normal_save_still_goes_through():
    response = client.post("/saves", json={"game_id": "bulk", "save_data": {"blob": "x" * 200_000}})
    assert response.status_code == 200


def test_bad_content_length_is_refused():
    response = client.post("/saves", content=b"{}", headers={"Content-Length": "abc", "Content-Type": "application/json"})
    assert response.status_code in (400, 413)


@pytest.mark.parametrize("path,body", [
    ("/ratings", {"game_slug": "g" * 65, "stars": 5}),
    ("/ratings", {"game_slug": "g", "stars": 5, "comment": "c" * 5001}),
    ("/ratings", {"game_slug": "g", "response": "r" * 5001}),
    ("/feedback", {"comment": "c" * 5001}),
    ("/feedback", {"game_id": "g" * 65, "comment": "hi"}),
    ("/saves", {"game_id": "g" * 65, "save_data": {}}),
    ("/answer-reports", {"item_id": "i", "submitted_answer": "a" * 501, "marked_correct_answer": ["x"]}),
    ("/answer-reports", {"item_id": "i" * 201, "submitted_answer": "a", "marked_correct_answer": ["x"]}),
    ("/answer-reports", {"item_id": "i", "submitted_answer": "a", "marked_correct_answer": ["x"] * 21}),
    ("/answer-reports", {"item_id": "i", "submitted_answer": "a", "marked_correct_answer": ["x" * 501]}),
    ("/auth/signup", {"username": "u" * 65, "password": "pw"}),
    ("/auth/signup", {"username": "okname-long-pw", "password": "p" * 1025}),
])
def test_oversized_fields_are_rejected_with_422(path, body):
    assert client.post(path, json=body).status_code == 422


def test_text_at_the_cap_is_accepted():
    assert client.post("/ratings", json={"game_slug": "g" * 64, "stars": 4, "comment": "c" * 5000}).status_code == 200


def test_slot_save_rejects_a_giant_game_id(token_for=None):
    client.post("/auth/signup", json={"username": "slotlen1", "password": "pw"})
    token = client.post("/auth/login", json={"username": "slotlen1", "password": "pw"}).json()["bearer_token"]
    response = client.put(
        f"/users/me/saves/{'g' * 65}/slots/1", json={"save_data": {}}, headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 422


@pytest.mark.parametrize("path,make_body,limiter,cap", [
    ("/ratings", lambda i: {"game_slug": "g", "stars": 3}, main.RATING_LIMITER, 60),
    ("/saves", lambda i: {"game_id": "g", "save_data": {}}, main.SAVE_CREATE_LIMITER, 60),
    ("/auth/signup", lambda i: {"username": f"flood{i}", "password": "pw"}, main.SIGNUP_LIMITER, 20),
])
def test_unauthenticated_writes_are_rate_limited_per_address(path, make_body, limiter, cap):
    headers = {"X-Forwarded-For": "198.51.100.77"}
    for i in range(cap):
        assert client.post(path, json=make_body(i), headers=headers).status_code == 200
    assert client.post(path, json=make_body(cap), headers=headers).status_code == 429
    # another address is unaffected
    assert client.post(path, json=make_body(cap + 1), headers={"X-Forwarded-For": "198.51.100.78"}).status_code == 200


def test_pageview_and_answer_reports_are_rate_limited():
    headers = {"X-Forwarded-For": "198.51.100.90"}
    for _ in range(120):
        assert client.post("/stats/pageview", headers=headers).status_code == 200
    assert client.post("/stats/pageview", headers=headers).status_code == 429
    report = {"item_id": "i", "submitted_answer": "a", "marked_correct_answer": ["x"]}
    for _ in range(120):
        assert client.post("/answer-reports", json=report, headers=headers).status_code == 200
    assert client.post("/answer-reports", json=report, headers=headers).status_code == 429


def test_failure_limiter_does_not_grow_without_bound():
    lim = FailureLimiter(max_failures=3, window_seconds=10)
    for i in range(FailureLimiter.MAX_KEYS + 50):
        lim.record_failure(f"k{i}", now=0)
    lim.record_failure("fresh", now=100)  # everything above has aged out
    assert len(lim._failures) < 10
    assert lim.blocked("fresh", now=100) is False


def test_slim_save_gives_the_same_stats_as_the_full_save():
    saves = [
        {"funds": 10 + i, "region": {"temperature": 1.5 + i, "junk": "x" * 1000, "round_number": True},
         "achievements_earned": ["a_one", "BAD ID", 7, "b_two"][: 2 + (i % 3)], "notes": "n" * 5000}
        for i in range(6)
    ]
    for game in ("grid", "thaw"):
        slim = [stats.slim_save(game, s) for s in saves]
        assert stats.summarize_game(game, slim) == stats.summarize_game(game, saves)
        for path in stats.STATS_FIELDS[game]:
            assert stats.field_values(slim, path) == stats.field_values(saves, path)
    assert "notes" not in stats.slim_save("grid", saves[0])
    assert stats.slim_save("grid", "not a dict") == {}


def test_concurrent_first_vote_retries_instead_of_500(monkeypatch):
    db = SessionLocal()
    entry = "site-2026-10-08-deadbeef"
    real_commit = db.commit
    state = {"raised": False}

    def racing_commit():
        if not state["raised"]:
            state["raised"] = True
            # another request's first vote lands just before ours commits
            other = SessionLocal()
            other.add(HelpfulVote(entry_id=entry, voter_key="a:race-voter-token-1234", helpful=False))
            other.commit()
            other.close()
            raise IntegrityError("insert", {}, Exception("unique"))
        return real_commit()

    monkeypatch.setattr(db, "commit", racing_commit)
    row = account_data.cast_vote(db, entry, "a:race-voter-token-1234", None, True)
    assert row.helpful is True
    assert db.query(HelpfulVote).filter(HelpfulVote.entry_id == entry).count() == 1
    db.close()


# --- adversarial inputs: none of these may produce a 500 or leak internals ---

@pytest.mark.parametrize("method,path,kwargs", [
    ("post", "/ratings", {"content": b"{not json", "headers": {"Content-Type": "application/json"}}),
    ("post", "/ratings", {"json": [1, 2, 3]}),
    ("post", "/ratings", {"json": {"game_slug": 5, "stars": "five"}}),
    ("post", "/saves", {"json": {"game_id": "g", "save_data": "not a dict"}}),
    ("post", "/auth/login", {"json": {"username": None, "password": 7}}),
    ("post", "/auth/signup", {"json": {"username": "   ", "password": "pw"}}),
    ("post", "/feedback", {"json": {"rating": 99}}),
    ("post", "/answer-reports", {"json": {"item_id": "x", "submitted_answer": "y", "marked_correct_answer": "z"}}),
    ("put", "/saves/NOPE-NOPE", {"json": {"save_data": []}}),
    ("post", "/pools/loop/recovered_units", {"json": {"amount": "NaN"}}),
    ("post", "/scores", {"json": {"game": "x", "board": "y", "score": True}}),
    ("get", "/stats/games/grid/percentile", {"params": {"field": "funds", "value": "inf"}}),
])
def test_malformed_requests_get_a_4xx_never_a_500(method, path, kwargs):
    response = getattr(client, method)(path, **kwargs)
    assert 400 <= response.status_code < 500
    assert "Traceback" not in response.text


@pytest.mark.parametrize("header", ["Bearer ", "bearer abc", "Bearer", "Basic abc", "Bearer " + "x" * 5000])
def test_odd_authorization_headers_are_401_not_admin(header):
    assert client.get("/users/me", headers={"Authorization": header}).status_code == 401
    assert client.get("/admin/users", headers={"Authorization": header}).status_code in (401, 503)


def test_admin_routes_all_refuse_anonymous_callers():
    admin_gets = [r.path for r in app.routes if getattr(r, "methods", None) and "GET" in r.methods and r.path.startswith("/admin")]
    admin_gets += ["/answer-reports", "/owner/notes/ideas-answers"]
    assert len(admin_gets) >= 8
    for path in admin_gets:
        assert client.get(path).status_code in (401, 503), path
    assert client.get("/admin/users", headers={"X-Admin-Token": "wrong"}).status_code == 401
    assert client.get("/admin/users", headers={"X-Admin-Token": ""}).status_code == 401


def test_signup_rejects_usernames_with_markup_but_keeps_ordinary_names():
    from fastapi.testclient import TestClient
    from main import app
    client = TestClient(app)
    for bad in ('x" autofocus onfocus="alert(1)', "<b>hi</b>", "a'b", "a&b", "name;drop"):
        resp = client.post("/auth/signup", json={"username": bad, "password": "hunter22"})
        assert resp.status_code == 422, bad
    ok = client.post("/auth/signup", json={"username": "Ordinary_Name-7 x", "password": "hunter22"})
    assert ok.status_code == 200, ok.text
