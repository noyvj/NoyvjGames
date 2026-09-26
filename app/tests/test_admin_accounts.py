"""U7 (test-data flag, admin account list, stats exclusion) and U9 (optional email)."""

from fastapi.testclient import TestClient

import stats
from main import app

client = TestClient(app)
ADMIN = {"X-Admin-Token": "test-admin-token"}


def _signup(username, password="hunter22"):
    resp = client.post("/auth/signup", json={"username": username, "password": password})
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['bearer_token']}"}


def _user_row(username):
    rows = client.get("/admin/users", headers=ADMIN).json()
    return next(r for r in rows if r["username"] == username)


# --- U9: email ---

def test_email_starts_empty_and_requires_sign_in():
    headers = _signup("mail_a")
    assert client.get("/users/me/email", headers=headers).json() == {"email": None}
    assert client.get("/users/me/email").status_code == 401
    assert client.put("/users/me/email", json={"email": "a@b.co"}).status_code == 401


def test_set_change_and_remove_email():
    headers = _signup("mail_b")
    assert client.put("/users/me/email", json={"email": "  Person@Example.COM "}, headers=headers).json() == {"email": "person@example.com"}
    assert client.get("/users/me/email", headers=headers).json() == {"email": "person@example.com"}
    assert client.put("/users/me/email", json={"email": "new@example.org"}, headers=headers).json() == {"email": "new@example.org"}
    assert client.put("/users/me/email", json={"email": None}, headers=headers).json() == {"email": None}
    client.put("/users/me/email", json={"email": "again@example.org"}, headers=headers)
    assert client.put("/users/me/email", json={"email": ""}, headers=headers).json() == {"email": None}


def test_bad_emails_rejected():
    headers = _signup("mail_c")
    for bad in ("nope", "a@b", "@b.co", "a b@c.co", "a@b.c o", "x" * 250 + "@b.co"):
        assert client.put("/users/me/email", json={"email": bad}, headers=headers).status_code == 422, bad


def test_email_is_visible_only_to_admin_and_owner():
    headers = _signup("mail_d")
    client.put("/users/me/email", json={"email": "secret@example.com"}, headers=headers)
    assert client.get("/admin/users").status_code == 401
    assert _user_row("mail_d")["email"] == "secret@example.com"
    other = _signup("mail_e")
    assert client.get("/users/me/email", headers=other).json() == {"email": None}


def test_email_never_appears_in_public_endpoints():
    headers = _signup("mail_f")
    client.put("/users/me/email", json={"email": "leak@example.com"}, headers=headers)
    for path in ("/feedback", "/ratings/sol", "/stats/games/sol"):
        resp = client.get(path)
        assert "leak@example.com" not in resp.text, path


# --- U7: admin account list and test flag ---

def test_admin_users_needs_the_token():
    assert client.get("/admin/users").status_code == 401
    assert client.patch("/admin/users/x", json={"is_test": True}).status_code == 401


def test_new_accounts_default_to_real():
    _signup("real_one")
    row = _user_row("real_one")
    assert row["is_test"] is False and row["save_count"] == 0


def test_aitest_accounts_are_flagged_automatically():
    _signup("aitest-session-1")
    assert _user_row("aitest-session-1")["is_test"] is True


def test_flag_and_unflag_an_account():
    _signup("flip_me")
    uid = _user_row("flip_me")["id"]
    assert client.patch(f"/admin/users/{uid}", json={"is_test": True}, headers=ADMIN).json()["is_test"] is True
    assert _user_row("flip_me")["is_test"] is True
    assert client.patch(f"/admin/users/{uid}", json={"is_test": False}, headers=ADMIN).json()["is_test"] is False


def test_flag_errors():
    assert client.patch("/admin/users/no-such", json={"is_test": True}, headers=ADMIN).status_code == 404
    uid = _user_row("flip_me" if False else "real_one")["id"]
    for bad in ({}, {"is_test": "yes"}, {"is_test": None}):
        assert client.patch(f"/admin/users/{uid}", json=bad, headers=ADMIN).status_code == 422, bad


def test_include_test_filter_hides_test_accounts():
    _signup("filter_real")
    _signup("aitest-filter")
    hidden = [r["username"] for r in client.get("/admin/users", params={"include_test": "false"}, headers=ADMIN).json()]
    shown = [r["username"] for r in client.get("/admin/users", headers=ADMIN).json()]
    assert "filter_real" in hidden and "aitest-filter" not in hidden
    assert "aitest-filter" in shown


def test_admin_stats_hides_test_accounts_and_saves_by_default():
    headers = _signup("stats_real")
    test_headers = _signup("aitest-stats")
    for h, n in ((headers, 1), (test_headers, 2)):
        save = client.post("/saves", json={"game_id": "statsgame", "save_data": {"n": n}}).json()
        client.post(f"/saves/{save['save_code']}/claim", headers=h)
    hidden = client.get("/admin/stats", headers=ADMIN).json()
    everything = client.get("/admin/stats", params={"hide_test": "false"}, headers=ADMIN).json()
    assert everything["saves_by_game"]["statsgame"] == 2
    assert hidden["saves_by_game"]["statsgame"] == 1
    assert everything["total_users"] > hidden["total_users"]


def test_public_stats_exclude_test_accounts_saves():
    stats.cache_clear()
    headers = _signup("pub_real")
    test_headers = _signup("aitest-pub")
    for h in (headers, test_headers):
        save = client.post("/saves", json={"game_id": "pubstatsgame", "save_data": {"x": 1}}).json()
        client.post(f"/saves/{save['save_code']}/claim", headers=h)
    saves = stats.cache_get("pubstatsgame")
    assert saves is None  # not cached yet
    from database import SessionLocal
    from main import _game_saves
    with SessionLocal() as db:
        assert len(_game_saves(db, "pubstatsgame")) == 1


def test_flagging_clears_the_public_stats_cache():
    from database import SessionLocal
    from main import _game_saves
    stats.cache_clear()
    headers = _signup("cache_real")
    save = client.post("/saves", json={"game_id": "cachegame", "save_data": {"x": 1}}).json()
    client.post(f"/saves/{save['save_code']}/claim", headers=headers)
    with SessionLocal() as db:
        assert len(_game_saves(db, "cachegame")) == 1
    uid = _user_row("cache_real")["id"]
    client.patch(f"/admin/users/{uid}", json={"is_test": True}, headers=ADMIN)
    with SessionLocal() as db:
        assert len(_game_saves(db, "cachegame")) == 0
    client.patch(f"/admin/users/{uid}", json={"is_test": False}, headers=ADMIN)


def test_unclaimed_saves_still_count():
    from database import SessionLocal
    from main import _game_saves
    stats.cache_clear()
    client.post("/saves", json={"game_id": "anongame", "save_data": {"x": 1}})
    with SessionLocal() as db:
        assert len(_game_saves(db, "anongame")) == 1
