"""Opt-in community leaderboards (A29 / E23 / F21)."""

from fastapi.testclient import TestClient

from database import SessionLocal
from main import app
from models import LeaderboardEntry, User

client = TestClient(app)
SOL = "/leaderboards/sol/fastest_completion"
HERD = "/leaderboards/herd/decoupling_gap"


def _auth(username, password="hunter22"):
    resp = client.post("/auth/signup", json={"username": username, "password": password})
    if resp.status_code == 409:
        resp = client.post("/auth/login", json={"username": username, "password": password})
    return {"Authorization": f"Bearer {resp.json()['bearer_token']}"}


def _clear():
    db = SessionLocal()
    db.query(LeaderboardEntry).delete()
    db.commit()
    db.close()


def test_unknown_board_is_404_everywhere():
    headers = _auth("lb_unknown")
    assert client.get("/leaderboards/sol/nope").status_code == 404
    assert client.put("/leaderboards/nope/x", json={"score": 1}, headers=headers).status_code == 404
    assert client.delete("/leaderboards/nope/x", headers=headers).status_code == 404


def test_submitting_needs_a_signed_in_account_but_reading_does_not():
    _clear()
    assert client.put(SOL, json={"score": 100}).status_code == 401
    assert client.delete(SOL).status_code == 401
    resp = client.get(SOL)
    assert resp.status_code == 200
    assert resp.json()["entries"] == [] and resp.json()["mine"] is None
    assert resp.headers["cache-control"] == "no-store"


def test_fastest_board_sorts_ascending_and_ranks():
    _clear()
    a, b, c = _auth("lb_a"), _auth("lb_b"), _auth("lb_c")
    client.put(SOL, json={"score": 500, "detail": "run 1"}, headers=a)
    client.put(SOL, json={"score": 300}, headers=b)
    client.put(SOL, json={"score": 900}, headers=c)
    entries = client.get(SOL).json()["entries"]
    assert [e["username"] for e in entries] == ["lb_b", "lb_a", "lb_c"]
    assert [e["rank"] for e in entries] == [1, 2, 3]
    mine = client.get(SOL, headers=a).json()["mine"]
    assert mine == {"score": 500.0, "detail": "run 1", "rank": 2}


def test_highest_board_sorts_descending():
    _clear()
    a, b = _auth("lb_h1"), _auth("lb_h2")
    client.put(HERD, json={"score": 10}, headers=a)
    client.put(HERD, json={"score": 99}, headers=b)
    assert [e["username"] for e in client.get(HERD).json()["entries"]] == ["lb_h2", "lb_h1"]


def test_only_the_personal_best_is_kept():
    _clear()
    h = _auth("lb_best")
    assert client.put(SOL, json={"score": 400}, headers=h).json()["improved"] is True
    worse = client.put(SOL, json={"score": 800}, headers=h).json()
    assert worse["improved"] is False and worse["score"] == 400.0
    better = client.put(SOL, json={"score": 250, "detail": "faster"}, headers=h).json()
    assert better["improved"] is True and better["score"] == 250.0
    assert client.get(SOL, headers=h).json()["mine"]["detail"] == "faster"
    db = SessionLocal()
    assert db.query(LeaderboardEntry).count() == 1
    db.close()


def test_out_of_range_and_non_finite_scores_are_rejected():
    _clear()
    h = _auth("lb_range")
    for bad in (-5, 0, 10 ** 12):
        assert client.put(SOL, json={"score": bad}, headers=h).status_code == 422
    assert client.put(SOL, json={"score": "fast"}, headers=h).status_code == 422
    assert client.get(SOL).json()["entries"] == []


def test_detail_is_trimmed_and_cleaned():
    _clear()
    h = _auth("lb_detail")
    client.put(SOL, json={"score": 5, "detail": "  hello\nworld " + "x" * 200}, headers=h)
    detail = client.get(SOL).json()["entries"][0]["detail"]
    assert "\n" not in detail and len(detail) <= 60 and detail.startswith("helloworld")


def test_opting_out_removes_the_entry():
    _clear()
    h = _auth("lb_out")
    client.put(SOL, json={"score": 7}, headers=h)
    assert client.delete(SOL, headers=h).json() == {"removed": True}
    assert client.get(SOL, headers=h).json()["mine"] is None
    assert client.delete(SOL, headers=h).json() == {"removed": False}


def test_test_accounts_are_never_listed_or_stored():
    _clear()
    h = _auth("ai_test_lb")
    db = SessionLocal()
    user = db.query(User).filter(User.username == "ai_test_lb").first()
    user.is_test = True
    db.commit()
    user_id = user.id
    db.close()
    assert client.put(SOL, json={"score": 3}, headers=h).json()["accepted"] is False
    db = SessionLocal()
    db.add(LeaderboardEntry(game_id="sol", board="fastest_completion", user_id=user_id, score=1.0))
    db.commit()
    db.close()
    assert client.get(SOL).json()["entries"] == []


def test_only_ten_entries_are_shown():
    _clear()
    for i in range(12):
        client.put(SOL, json={"score": 100 + i}, headers=_auth(f"lb_many{i}"))
    entries = client.get(SOL).json()["entries"]
    assert len(entries) == 10 and entries[0]["score"] == 100.0
    assert "user_id" not in entries[0]
