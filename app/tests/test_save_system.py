"""Save system (SAVE-SYSTEM-DESIGN.md Phase 1): save codes, no accounts.
Runs against the in-memory sqlite DB substituted in conftest.py, never
the real Neon database.
"""

import re

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)

SAVE_CODE_PATTERN = re.compile(r"^[23456789ABCDEFGHJKMNPQRSTUVWXYZ]{4}-[23456789ABCDEFGHJKMNPQRSTUVWXYZ]{4}$")


def test_create_save_returns_a_well_formed_code():
    resp = client.post("/saves", json={"game_id": "sol", "save_data": {"iron": 100}})
    assert resp.status_code == 200
    body = resp.json()
    assert SAVE_CODE_PATTERN.match(body["save_code"])
    assert body["game_id"] == "sol"
    assert body["save_data"] == {"iron": 100}


def test_create_save_rejects_unambiguous_characters():
    """The alphabet excludes 0/O/1/I/L entirely — a generated code should
    never contain them."""
    resp = client.post("/saves", json={"game_id": "sol", "save_data": {}})
    code = resp.json()["save_code"]
    assert not any(c in code for c in "01OIL")


def test_two_saves_get_different_codes():
    a = client.post("/saves", json={"game_id": "sol", "save_data": {"n": 1}}).json()
    b = client.post("/saves", json={"game_id": "sol", "save_data": {"n": 2}}).json()
    assert a["save_code"] != b["save_code"]


def test_get_save_returns_created_data():
    created = client.post(
        "/saves", json={"game_id": "sol", "save_data": {"planet": "Earth", "iron": 42}}
    ).json()
    resp = client.get(f"/saves/{created['save_code']}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["save_data"] == {"planet": "Earth", "iron": 42}
    assert body["game_id"] == "sol"


def test_get_unknown_save_code_returns_404():
    resp = client.get("/saves/ZZZZ-ZZZZ")
    assert resp.status_code == 404


def test_put_overwrites_save_data():
    created = client.post("/saves", json={"game_id": "sol", "save_data": {"iron": 1}}).json()
    code = created["save_code"]

    resp = client.put(f"/saves/{code}", json={"save_data": {"iron": 999, "mars_unlocked": True}})
    assert resp.status_code == 200
    assert resp.json()["save_data"] == {"iron": 999, "mars_unlocked": True}

    refetched = client.get(f"/saves/{code}").json()
    assert refetched["save_data"] == {"iron": 999, "mars_unlocked": True}


def test_put_unknown_save_code_returns_404():
    resp = client.put("/saves/ZZZZ-ZZZZ", json={"save_data": {"iron": 1}})
    assert resp.status_code == 404


def test_save_data_round_trips_nested_structures():
    """Mirrors the shape a real game (SOL) would actually send: nested
    per-planet dicts, lists, booleans, floats."""
    nested = {
        "planet_state": {
            "Earth": {"resource_count": 12.5, "generator_count": 3, "trade_routes": {"Mars": 2}},
            "Mars": {"resource_count": 0.0, "generator_count": 0, "trade_routes": {}},
        },
        "unlocked_bodies": ["Moon", "Mars"],
        "current_planet": "Earth",
        "governor_priority": "balance",
    }
    created = client.post("/saves", json={"game_id": "sol", "save_data": nested}).json()
    fetched = client.get(f"/saves/{created['save_code']}").json()
    assert fetched["save_data"] == nested


def test_save_response_includes_timestamps():
    created = client.post("/saves", json={"game_id": "sol", "save_data": {}}).json()
    assert created["created_at"] is not None
