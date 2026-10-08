"""Z-10: the save "time machine" routes (POST/GET /users/me/snapshots, GET/DELETE by id). Covers the
per-slot cap (oldest deleted), isolation between slots, games and accounts, the size limit, the empty
state refusal, the per-account rate limit, and that deleting or exporting the account includes them."""

import time

import pytest
from fastapi.testclient import TestClient

import main
import snapshots
from database import SessionLocal
from main import app
from models import AuthSession, SaveSnapshot, User

client = TestClient(app)


def make_user(name):
    db = SessionLocal()
    user = db.query(User).filter(User.username == name).first()
    if user is None:
        user = User(username=name, password_hash="not-a-real-hash")
        db.add(user)
        db.commit()
    token = f"snaptok-{name}"
    if db.query(AuthSession).filter(AuthSession.token == token).first() is None:
        db.add(AuthSession(user_id=user.id, token=token))
        db.commit()
    uid = user.id
    db.close()
    return {"Authorization": f"Bearer {token}"}, uid


def snap(headers, game="snapgame", slot=1, n=1, summary=None, data=None):
    body = {"game_id": game, "slot": slot, "summary": summary or f"turn {n}", "save_data": {"turn": n} if data is None else data}
    return client.post("/users/me/snapshots", json=body, headers=headers)


def count(uid, game=None, slot=None):
    db = SessionLocal()
    try:
        q = db.query(SaveSnapshot).filter(SaveSnapshot.user_id == uid)
        if game:
            q = q.filter(SaveSnapshot.game_id == game)
        if slot is not None:
            q = q.filter(SaveSnapshot.slot == slot)
        return q.count()
    finally:
        db.close()


def test_every_route_needs_sign_in():
    assert client.post("/users/me/snapshots", json={"game_id": "g", "save_data": {"a": 1}}).status_code == 401
    assert client.get("/users/me/snapshots").status_code == 401
    assert client.get("/users/me/snapshots/abc").status_code == 401
    assert client.delete("/users/me/snapshots/abc").status_code == 401


def test_create_list_and_fetch_one():
    headers, uid = make_user("snap-a")
    created = snap(headers, summary="  Day 4,\n  3 plots   ", data={"day": 4, "plots": [1, 2, 3]})
    assert created.status_code == 200, created.text
    body = created.json()
    assert body["game_id"] == "snapgame" and body["slot"] == 1
    assert body["summary"] == "Day 4, 3 plots", "the summary is one trimmed line"
    assert body["size"] == len('{"day":4,"plots":[1,2,3]}')
    assert "save_data" not in body
    listed = client.get("/users/me/snapshots?game_id=snapgame", headers=headers).json()
    assert [r["id"] for r in listed] == [body["id"]] and "save_data" not in listed[0]
    one = client.get(f"/users/me/snapshots/{body['id']}", headers=headers).json()
    assert one["save_data"] == {"day": 4, "plots": [1, 2, 3]}
    assert one["created_at"]


def test_only_the_newest_five_per_game_and_slot_are_kept_oldest_deleted():
    headers, uid = make_user("snap-cap")
    ids = []
    for n in range(1, 9):
        r = snap(headers, n=n)
        assert r.status_code == 200
        ids.append(r.json()["id"])
    assert count(uid, "snapgame", 1) == snapshots.SNAPSHOTS_PER_SLOT == 5
    listed = client.get("/users/me/snapshots?game_id=snapgame", headers=headers).json()
    assert [r["id"] for r in listed] == list(reversed(ids[3:])), "newest first, the three oldest are gone"
    assert client.get(f"/users/me/snapshots/{ids[0]}", headers=headers).status_code == 404
    assert client.get(f"/users/me/snapshots/{ids[7]}", headers=headers).json()["save_data"] == {"turn": 8}


def test_slots_games_and_accounts_have_separate_caps_and_are_private():
    a, a_id = make_user("snap-iso-a")
    b, b_id = make_user("snap-iso-b")
    for n in range(1, 7):
        snap(a, slot=1, n=n)
        snap(a, slot=2, n=n + 100)
        snap(a, game="othergame", slot=1, n=n + 200)
        snap(a, slot=0, n=n + 300)
    assert count(a_id, "snapgame", 1) == 5 and count(a_id, "snapgame", 2) == 5
    assert count(a_id, "othergame", 1) == 5 and count(a_id, "snapgame", 0) == 5
    mine = client.get("/users/me/snapshots", headers=a).json()
    assert len(mine) == 20
    assert len(client.get("/users/me/snapshots?game_id=othergame", headers=a).json()) == 5
    # the other account sees none of it and cannot read or delete it by id
    assert client.get("/users/me/snapshots", headers=b).json() == []
    victim = mine[0]["id"]
    assert client.get(f"/users/me/snapshots/{victim}", headers=b).status_code == 404
    assert client.delete(f"/users/me/snapshots/{victim}", headers=b).status_code == 404
    assert client.get(f"/users/me/snapshots/{victim}", headers=a).status_code == 200


def test_the_same_state_twice_in_a_row_does_not_add_a_second_row():
    headers, uid = make_user("snap-dupe")
    first = snap(headers, data={"x": 1}).json()
    again = snap(headers, data={"x": 1}).json()
    assert again["id"] == first["id"] and count(uid) == 1
    snap(headers, data={"x": 2})
    third = snap(headers, data={"x": 1}).json()   # not the newest any more, so it is a new row
    assert third["id"] != first["id"] and count(uid) == 3


def test_validation_empty_state_slot_range_and_size_limit():
    headers, uid = make_user("snap-valid")
    assert snap(headers, data={}).status_code in (422,), "an empty state is never snapshotted"
    client_empty = client.post("/users/me/snapshots", json={"game_id": "g", "slot": 1, "save_data": {}}, headers=headers)
    assert client_empty.status_code == 422
    assert snap(headers, slot=4).status_code == 422 and snap(headers, slot=-1).status_code == 422
    assert client.post("/users/me/snapshots", json={"game_id": "", "save_data": {"a": 1}}, headers=headers).status_code == 422
    assert client.post("/users/me/snapshots", json={"game_id": "g" * 65, "save_data": {"a": 1}}, headers=headers).status_code == 422
    assert client.post("/users/me/snapshots", json={"game_id": "g", "save_data": [1]}, headers=headers).status_code == 422
    big = {"blob": "x" * (snapshots.SNAPSHOT_MAX_BYTES + 10)}
    too_big = snap(headers, data=big)
    assert too_big.status_code == 413 and "too large" in too_big.json()["detail"]
    ok = snap(headers, data={"blob": "x" * 200_000})
    assert ok.status_code == 200 and ok.json()["size"] > 200_000
    assert count(uid) == 1, "refused snapshots store nothing"


def test_summary_is_capped_in_length():
    headers, _ = make_user("snap-sum")
    r = snap(headers, summary="word " * 150)
    assert r.status_code == 200 and len(r.json()["summary"]) <= snapshots.SUMMARY_MAX_LENGTH
    too_long = client.post("/users/me/snapshots", json={"game_id": "g", "summary": "y" * 1001, "save_data": {"a": 1}}, headers=headers)
    assert too_long.status_code == 422


def test_snapshots_are_rate_limited_per_account():
    a, _ = make_user("snap-rate-a")
    b, _ = make_user("snap-rate-b")
    codes = [snap(a, n=n).status_code for n in range(main.SNAPSHOT_LIMITER.max_failures + 3)]
    assert codes[:main.SNAPSHOT_LIMITER.max_failures] == [200] * main.SNAPSHOT_LIMITER.max_failures
    assert set(codes[main.SNAPSHOT_LIMITER.max_failures:]) == {429}
    assert snap(b, n=1).status_code == 200, "another account is not affected"
    main.reset_write_limiters()
    assert snap(a, n=99).status_code == 200


def test_delete_one_snapshot():
    headers, uid = make_user("snap-del")
    sid = snap(headers).json()["id"]
    assert client.delete(f"/users/me/snapshots/{sid}", headers=headers).json() == {"deleted": True}
    assert count(uid) == 0
    assert client.delete(f"/users/me/snapshots/{sid}", headers=headers).status_code == 404


def test_account_wide_cap_deletes_the_oldest_snapshots(monkeypatch):
    monkeypatch.setattr(snapshots, "MAX_SNAPSHOTS_PER_ACCOUNT", 7)
    headers, uid = make_user("snap-wide")
    ids = []
    for n in range(10):
        ids.append(snap(headers, game=f"g{n}", n=n).json()["id"])
        time.sleep(0.002)
    assert count(uid) == 7
    left = {r["id"] for r in client.get("/users/me/snapshots", headers=headers).json()}
    assert left == set(ids[3:])


def test_account_export_includes_snapshots_with_their_state():
    headers, uid = make_user("snap-export")
    other, _ = make_user("snap-export-other")
    snap(headers, game="exp", slot=2, summary="exported", data={"keep": "me"})
    snap(other, game="exp", slot=2, summary="theirs", data={"secret": "theirs-only"})
    body = client.get("/users/me/export", headers=headers).json()
    assert [(r["game_id"], r["slot"], r["summary"], r["save_data"]) for r in body["save_snapshots"]] == [
        ("exp", 2, "exported", {"keep": "me"})]
    assert body["save_snapshots"][0]["size"] > 0 and body["save_snapshots"][0]["created_at"]
    assert "theirs-only" not in str(body)


def test_deleting_the_account_deletes_its_snapshots_and_only_those():
    gone, gone_id = make_user("snap-goner")
    stay, stay_id = make_user("snap-stayer")
    for n in range(3):
        snap(gone, n=n)
        snap(stay, n=n)
    removed = client.request("DELETE", "/users/me", json={"confirm_username": "snap-goner"}, headers=gone)
    assert removed.status_code == 200 and removed.json()["removed"]["save_snapshots"] == 3
    assert count(gone_id) == 0 and count(stay_id) == 3
