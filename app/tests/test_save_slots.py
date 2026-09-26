"""U3: three save slots per game for signed-in accounts."""

from datetime import datetime, timezone

from fastapi.testclient import TestClient

from database import SessionLocal
from main import app
from models import Save, User

client = TestClient(app)


def _auth(username):
    resp = client.post("/auth/signup", json={"username": username, "password": "hunter22"})
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['bearer_token']}"}


def _put(headers, game, slot, data, name=None):
    body = {"save_data": data}
    if name is not None:
        body["name"] = name
    return client.put(f"/users/me/saves/{game}/slots/{slot}", json=body, headers=headers)


def test_requires_sign_in():
    assert client.put("/users/me/saves/sol/slots/1", json={"save_data": {}}).status_code == 401


def test_first_write_creates_the_slot_with_a_default_name():
    h = _auth("slot_a")
    resp = _put(h, "sol", 1, {"iron": 5})
    assert resp.status_code == 200
    body = resp.json()
    assert body["slot"] == 1 and body["slot_name"] == "Save 1" and body["save_data"] == {"iron": 5}
    assert body["save_code"]


def test_second_write_overwrites_the_same_row():
    h = _auth("slot_b")
    first = _put(h, "sol", 2, {"n": 1}).json()
    second = _put(h, "sol", 2, {"n": 2}).json()
    assert first["save_code"] == second["save_code"]
    assert second["save_data"] == {"n": 2}
    saves = [s for s in client.get("/users/me/saves", headers=h).json() if s["game_id"] == "sol"]
    assert len(saves) == 1


def test_slots_are_independent_and_per_game():
    h = _auth("slot_c")
    _put(h, "sol", 1, {"a": 1})
    _put(h, "sol", 2, {"a": 2})
    _put(h, "canopy", 1, {"a": 3})
    saves = client.get("/users/me/saves", headers=h).json()
    got = {(s["game_id"], s["slot"]): s["save_data"]["a"] for s in saves}
    assert got == {("sol", 1): 1, ("sol", 2): 2, ("canopy", 1): 3}


def test_slots_are_per_account():
    a, b = _auth("slot_d1"), _auth("slot_d2")
    _put(a, "sol", 1, {"who": "a"})
    assert client.get("/users/me/saves", headers=b).json() == []


def test_slot_out_of_range_rejected():
    h = _auth("slot_e")
    for bad in (0, 4, -1, 99):
        assert _put(h, "sol", bad, {}).status_code == 422, bad


def test_rename_and_keep_name_on_later_writes():
    h = _auth("slot_f")
    _put(h, "sol", 1, {"n": 1}, name="  My run  ")
    body = _put(h, "sol", 1, {"n": 2}).json()
    assert body["slot_name"] == "My run"
    body = _put(h, "sol", 1, {"n": 3}, name="Renamed").json()
    assert body["slot_name"] == "Renamed"


def test_name_is_trimmed_and_capped():
    h = _auth("slot_g")
    body = _put(h, "sol", 3, {}, name="x" * 200).json()
    assert len(body["slot_name"]) == 40
    assert _put(h, "sol", 3, {}, name="   ").json()["slot_name"] == "x" * 40


def test_slot_save_code_still_loads_anonymously_like_any_save():
    h = _auth("slot_h")
    code = _put(h, "sol", 1, {"n": 9}).json()["save_code"]
    assert client.get(f"/saves/{code}").json()["save_data"] == {"n": 9}


def test_existing_claimed_save_becomes_slot_one():
    h = _auth("slot_i")
    code = client.post("/saves", json={"game_id": "sol", "save_data": {"old": 1}}).json()["save_code"]
    with SessionLocal() as db:
        user = db.query(User).filter(User.username == "slot_i").one()
        row = db.query(Save).filter(Save.save_code == code).one()
        row.user_id = user.id  # a claimed save from before slots existed: no slot
        db.commit()
    saves = client.get("/users/me/saves", headers=h).json()
    assert [(s["slot"], s["save_data"]) for s in saves] == [(1, {"old": 1})]
    assert saves[0]["slot_name"] == "Save 1"


def test_several_legacy_saves_fill_slots_newest_first():
    h = _auth("slot_j")
    codes = [client.post("/saves", json={"game_id": "sol", "save_data": {"n": n}}).json()["save_code"] for n in range(4)]
    with SessionLocal() as db:
        user = db.query(User).filter(User.username == "slot_j").one()
        for i, code in enumerate(codes):
            row = db.query(Save).filter(Save.save_code == code).one()
            row.user_id = user.id
            row.updated_at = datetime(2026, 1, i + 1, tzinfo=timezone.utc)
        db.commit()
    saves = client.get("/users/me/saves", headers=h).json()
    by_slot = {s["slot"]: s["save_data"]["n"] for s in saves if s["slot"]}
    assert by_slot == {1: 3, 2: 2, 3: 1}
    assert len(saves) == 4  # the fourth stays listed, slot-less


def test_claiming_takes_the_first_free_slot():
    h = _auth("slot_k")
    _put(h, "sol", 1, {"taken": 1})
    code = client.post("/saves", json={"game_id": "sol", "save_data": {"claimed": 1}}).json()["save_code"]
    resp = client.post(f"/saves/{code}/claim", headers=h)
    assert resp.status_code == 200 and resp.json()["slot"] == 2


def test_claiming_with_all_slots_full_is_refused():
    h = _auth("slot_l")
    for n in (1, 2, 3):
        _put(h, "sol", n, {"n": n})
    code = client.post("/saves", json={"game_id": "sol", "save_data": {}}).json()["save_code"]
    assert client.post(f"/saves/{code}/claim", headers=h).status_code == 409
    # and the save stays unclaimed, so someone can still claim it once a slot is free
    with SessionLocal() as db:
        assert db.query(Save).filter(Save.save_code == code).one().user_id is None


def test_reclaiming_your_own_save_is_a_harmless_no_op():
    h = _auth("slot_m")
    code = client.post("/saves", json={"game_id": "sol", "save_data": {}}).json()["save_code"]
    first = client.post(f"/saves/{code}/claim", headers=h).json()
    again = client.post(f"/saves/{code}/claim", headers=h)
    assert again.status_code == 200 and again.json()["slot"] == first["slot"]


def test_anonymous_saves_have_no_slot():
    body = client.post("/saves", json={"game_id": "sol", "save_data": {}}).json()
    assert body["slot"] is None and body["slot_name"] is None
