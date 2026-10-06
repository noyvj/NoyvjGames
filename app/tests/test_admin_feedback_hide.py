"""UX-9: admin can flag feedback rows (both tables) as test/hidden; the public
reads then skip them while admin still lists them with the flag."""

import pytest
from fastapi.testclient import TestClient

import main
from main import app

client = TestClient(app)
ADMIN = {"X-Admin-Token": "test-admin-token"}


@pytest.fixture(autouse=True)
def reset_rate_limit():
    main._feedback_submission_log.clear()
    yield
    main._feedback_submission_log.clear()


def _feedback(game_id, comment):
    resp = client.post("/feedback", json={"game_id": game_id, "comment": comment})
    assert resp.status_code == 200, resp.text
    return resp.json()["id"]


def _rating(slug, **kw):
    resp = client.post("/ratings", json={"game_slug": slug, **kw})
    assert resp.status_code == 200, resp.text
    return resp.json()["id"]


def test_admin_routes_require_admin():
    fid = _feedback("hide_auth", "x")
    rid = _rating("hide_auth", stars=3)
    for method, path in (
        ("get", "/admin/feedback"),
        ("get", "/admin/ratings"),
        ("patch", f"/admin/feedback/{fid}"),
        ("patch", f"/admin/ratings/{rid}"),
    ):
        kwargs = {"json": {"is_hidden": True}} if method == "patch" else {}
        assert getattr(client, method)(path, **kwargs).status_code == 401, path
        assert getattr(client, method)(path, headers={"X-Admin-Token": "wrong"}, **kwargs).status_code == 401, path


def test_hide_feedback_removes_it_from_public_list_but_not_admin():
    keep = _feedback("hide_fb", "real one")
    test = _feedback("hide_fb", "just testing")
    resp = client.patch(f"/admin/feedback/{test}", json={"is_hidden": True}, headers=ADMIN)
    assert resp.status_code == 200
    assert resp.json()["is_hidden"] is True

    public = client.get("/feedback", params={"game_id": "hide_fb"}).json()
    assert [r["id"] for r in public] == [keep]
    assert "is_hidden" not in public[0]

    admin_rows = [r for r in client.get("/admin/feedback", headers=ADMIN).json() if r["game_id"] == "hide_fb"]
    assert {r["id"]: r["is_hidden"] for r in admin_rows} == {keep: False, test: True}

    only_visible = client.get("/admin/feedback", params={"include_hidden": "false"}, headers=ADMIN).json()
    assert test not in [r["id"] for r in only_visible]
    assert keep in [r["id"] for r in only_visible]


def test_unhide_feedback_restores_it():
    fid = _feedback("hide_fb2", "toggle me")
    client.patch(f"/admin/feedback/{fid}", json={"is_hidden": True}, headers=ADMIN)
    assert client.get("/feedback", params={"game_id": "hide_fb2"}).json() == []
    resp = client.patch(f"/admin/feedback/{fid}", json={"is_hidden": False}, headers=ADMIN)
    assert resp.json()["is_hidden"] is False
    assert [r["id"] for r in client.get("/feedback", params={"game_id": "hide_fb2"}).json()] == [fid]


def test_hide_general_feedback():
    resp = client.post("/feedback", json={"comment": "general hide test"})
    fid = resp.json()["id"]
    client.patch(f"/admin/feedback/{fid}", json={"is_hidden": True}, headers=ADMIN)
    assert fid not in [r["id"] for r in client.get("/feedback").json()]


def test_hide_rating_row_removes_it_from_public_list():
    star = _rating("hide_rt", stars=1, comment="test review")
    prompt = _rating("hide_rt", response="yes")
    keep = _rating("hide_rt", stars=5, comment="real review")
    resp = client.patch(f"/admin/ratings/{star}", json={"is_hidden": True}, headers=ADMIN)
    assert resp.status_code == 200 and resp.json()["is_hidden"] is True
    client.patch(f"/admin/ratings/{prompt}", json={"is_hidden": True}, headers=ADMIN)

    public = client.get("/ratings/hide_rt").json()
    assert [r["id"] for r in public] == [keep]

    admin_rows = client.get("/admin/ratings", params={"game_slug": "hide_rt"}, headers=ADMIN).json()
    assert {r["id"]: r["is_hidden"] for r in admin_rows} == {star: True, prompt: True, keep: False}
    visible = client.get("/admin/ratings", params={"game_slug": "hide_rt", "include_hidden": "false"}, headers=ADMIN).json()
    assert [r["id"] for r in visible] == [keep]

    client.patch(f"/admin/ratings/{star}", json={"is_hidden": False}, headers=ADMIN)
    assert {r["id"] for r in client.get("/ratings/hide_rt").json()} == {star, keep}


def test_new_rows_default_to_visible():
    rid = _rating("hide_default", stars=4)
    fid = _feedback("hide_default", "hello")
    assert [r["id"] for r in client.get("/ratings/hide_default").json()] == [rid]
    assert [r["id"] for r in client.get("/feedback", params={"game_id": "hide_default"}).json()] == [fid]


def test_patch_unknown_id_is_404_and_bad_body_is_422():
    assert client.patch("/admin/feedback/does-not-exist", json={"is_hidden": True}, headers=ADMIN).status_code == 404
    assert client.patch("/admin/ratings/999999", json={"is_hidden": True}, headers=ADMIN).status_code == 404
    fid = _feedback("hide_bad", "x")
    assert client.patch(f"/admin/feedback/{fid}", json={"is_hidden": "yes"}, headers=ADMIN).status_code == 422
    assert client.patch(f"/admin/feedback/{fid}", json={}, headers=ADMIN).status_code == 422
    assert client.patch("/admin/ratings/not-a-number", json={"is_hidden": True}, headers=ADMIN).status_code == 422


def test_owner_bearer_token_accepted():
    resp = client.post("/auth/signup", json={"username": "noyvj", "password": "hunter22"})
    if resp.status_code == 200:
        headers = {"Authorization": f"Bearer {resp.json()['bearer_token']}"}
        assert client.get("/admin/feedback", headers=headers).status_code == 200
        assert client.get("/admin/ratings", headers=headers).status_code == 200


def test_patch_schema_statements_cover_new_columns(monkeypatch):
    """patch_schema is Postgres-only; check the statements it would run."""
    import database

    executed = []

    class FakeConn:
        def execute(self, stmt):
            executed.append(str(stmt))

    class FakeBegin:
        def __enter__(self):
            return FakeConn()

        def __exit__(self, *a):
            return False

    class FakeEngine:
        class dialect:
            name = "postgresql"

        def begin(self):
            return FakeBegin()

    monkeypatch.setattr(database, "engine", FakeEngine())
    database.patch_schema()
    assert any("ratings ADD COLUMN IF NOT EXISTS is_hidden" in s for s in executed)
    assert any("feedback ADD COLUMN IF NOT EXISTS is_hidden" in s for s in executed)
