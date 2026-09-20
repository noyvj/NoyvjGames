"""Admin aggregate stats (TODO.md L8) — backs the unlisted admin.html
Overview panel. Runs against the in-memory sqlite DB substituted in
conftest.py, never the real Neon database.

The in-memory DB is shared across every test module in this pytest
session (one process-wide engine, see conftest.py), so these tests
compare before/after deltas rather than asserting exact totals — other
test modules' signups/saves land in the same tables.
"""

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def _stats():
    resp = client.get("/admin/stats")
    assert resp.status_code == 200
    return resp.json()


def test_admin_stats_has_the_expected_shape():
    body = _stats()
    assert "total_users" in body
    assert "total_saves" in body
    assert "saves_by_game" in body
    assert isinstance(body["saves_by_game"], dict)


def test_admin_stats_total_users_increases_after_signup():
    before = _stats()["total_users"]
    client.post("/auth/signup", json={"username": "admin-stats-user", "password": "pw"})
    after = _stats()["total_users"]
    assert after == before + 1


def test_admin_stats_total_saves_and_per_game_breakdown_increase_after_save():
    before = _stats()
    client.post("/saves", json={"game_id": "admin-stats-game", "save_data": {"x": 1}})
    after = _stats()
    assert after["total_saves"] == before["total_saves"] + 1
    assert after["saves_by_game"].get("admin-stats-game", 0) == before["saves_by_game"].get(
        "admin-stats-game", 0
    ) + 1


def test_admin_stats_does_not_leak_save_contents_or_usernames():
    client.post("/auth/signup", json={"username": "should-not-appear", "password": "pw"})
    client.post("/saves", json={"game_id": "sol", "save_data": {"secret": "should-not-appear"}})
    body = _stats()
    assert "should-not-appear" not in str(body)
