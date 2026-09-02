"""Accounts (ACCOUNTS-AND-FEEDBACK-DESIGN.md Phase 2, revised): username +
password sign-up/sign-in, save-claiming, and listing a user's saves. Runs
against the in-memory sqlite DB substituted in conftest.py, never the
real Neon database.
"""

from fastapi.testclient import TestClient

import main
from database import SessionLocal
from main import app
from models import User

client = TestClient(app)


def _signup(username="player", password="hunter22"):
    resp = client.post("/auth/signup", json={"username": username, "password": password})
    assert resp.status_code == 200
    return resp.json()


def test_signup_returns_bearer_token_and_username():
    body = _signup("newplayer", "correcthorse")
    assert body["bearer_token"]
    assert body["username"] == "newplayer"


def test_signup_normalizes_username_to_lowercase():
    body = _signup("MixedCase", "pw")
    assert body["username"] == "mixedcase"


def test_signup_rejects_duplicate_username_case_insensitively():
    _signup("dupe", "pw1")
    resp = client.post("/auth/signup", json={"username": "DUPE", "password": "pw2"})
    assert resp.status_code == 409


def test_signup_rejects_empty_username():
    resp = client.post("/auth/signup", json={"username": "   ", "password": "pw"})
    assert resp.status_code == 422


def test_signup_rejects_empty_password():
    resp = client.post("/auth/signup", json={"username": "someone", "password": ""})
    assert resp.status_code == 422


def test_signup_has_no_strength_requirement():
    # Explicitly no caps/digits/special-char policy — a single character
    # password must be accepted.
    body = _signup("laxpw", "a")
    assert body["bearer_token"]


def test_login_succeeds_with_correct_credentials():
    _signup("logintest", "correctpw")
    resp = client.post("/auth/login", json={"username": "logintest", "password": "correctpw"})
    assert resp.status_code == 200
    assert resp.json()["username"] == "logintest"


def test_login_is_case_insensitive_on_username():
    _signup("CaseLogin", "pw123")
    resp = client.post("/auth/login", json={"username": "caselogin", "password": "pw123"})
    assert resp.status_code == 200


def test_login_rejects_wrong_password():
    _signup("wrongpw", "rightpassword")
    resp = client.post("/auth/login", json={"username": "wrongpw", "password": "nope"})
    assert resp.status_code == 401


def test_login_rejects_unknown_username():
    resp = client.post("/auth/login", json={"username": "doesnotexist", "password": "whatever"})
    assert resp.status_code == 401


def test_claim_save_without_auth_is_rejected():
    save = client.post("/saves", json={"game_id": "sol", "save_data": {"iron": 1}}).json()
    resp = client.post(f"/saves/{save['save_code']}/claim")
    assert resp.status_code == 401


def test_claim_save_attaches_current_user():
    bearer = _signup("claimer", "pw")["bearer_token"]
    save = client.post("/saves", json={"game_id": "sol", "save_data": {"iron": 5}}).json()

    resp = client.post(
        f"/saves/{save['save_code']}/claim", headers={"Authorization": f"Bearer {bearer}"}
    )
    assert resp.status_code == 200

    my_saves = client.get("/users/me/saves", headers={"Authorization": f"Bearer {bearer}"})
    assert my_saves.status_code == 200
    codes = [s["save_code"] for s in my_saves.json()]
    assert save["save_code"] in codes


def test_claim_unknown_save_code_returns_404():
    bearer = _signup("claimer2", "pw")["bearer_token"]
    resp = client.post("/saves/ZZZZ-ZZZZ/claim", headers={"Authorization": f"Bearer {bearer}"})
    assert resp.status_code == 404


def test_list_my_saves_excludes_other_users_saves():
    bearer_a = _signup("user-a", "pw")["bearer_token"]
    bearer_b = _signup("user-b", "pw")["bearer_token"]

    save = client.post("/saves", json={"game_id": "sol", "save_data": {}}).json()
    client.post(f"/saves/{save['save_code']}/claim", headers={"Authorization": f"Bearer {bearer_a}"})

    resp_b = client.get("/users/me/saves", headers={"Authorization": f"Bearer {bearer_b}"})
    assert save["save_code"] not in [s["save_code"] for s in resp_b.json()]


def test_endpoints_reject_bad_bearer_token():
    resp = client.get("/users/me/saves", headers={"Authorization": "Bearer not-a-real-session"})
    assert resp.status_code == 401


def test_claiming_a_save_already_claimed_by_another_user_is_rejected():
    # PR #1 (sean-hart) review finding: claim_save had no ownership check,
    # so a second user posting the same code could silently steal a save
    # already claimed by the first — contradicts SAVE-SYSTEM-DESIGN.md's
    # "nobody loses a save by signing up" invariant.
    bearer_a = _signup("owner-a", "pw")["bearer_token"]
    bearer_b = _signup("thief-b", "pw")["bearer_token"]
    save = client.post("/saves", json={"game_id": "sol", "save_data": {"iron": 1}}).json()

    first_claim = client.post(
        f"/saves/{save['save_code']}/claim", headers={"Authorization": f"Bearer {bearer_a}"}
    )
    assert first_claim.status_code == 200

    second_claim = client.post(
        f"/saves/{save['save_code']}/claim", headers={"Authorization": f"Bearer {bearer_b}"}
    )
    assert second_claim.status_code == 409

    # Still owned by A, not reassigned to B.
    my_saves_a = client.get("/users/me/saves", headers={"Authorization": f"Bearer {bearer_a}"})
    assert save["save_code"] in [s["save_code"] for s in my_saves_a.json()]
    my_saves_b = client.get("/users/me/saves", headers={"Authorization": f"Bearer {bearer_b}"})
    assert save["save_code"] not in [s["save_code"] for s in my_saves_b.json()]


def test_reclaiming_own_already_claimed_save_is_a_harmless_noop():
    # The ownership guard must only reject a *different* account — the same
    # account re-posting /claim (e.g. a retried request) should still succeed.
    bearer = _signup("reclaimer", "pw")["bearer_token"]
    save = client.post("/saves", json={"game_id": "sol", "save_data": {}}).json()

    first = client.post(f"/saves/{save['save_code']}/claim", headers={"Authorization": f"Bearer {bearer}"})
    assert first.status_code == 200
    second = client.post(f"/saves/{save['save_code']}/claim", headers={"Authorization": f"Bearer {bearer}"})
    assert second.status_code == 200


def test_signup_commit_time_username_collision_returns_409_not_500(monkeypatch):
    # PR #1 review finding: the existence check and the commit aren't
    # atomic, so a genuine concurrent signup can pass the check before
    # either commits, then hit an unhandled IntegrityError (bare 500) on
    # the second commit instead of the intended 409. Forcing the "no
    # existing user" branch via monkeypatch while a real competing row is
    # already in the database reproduces the commit-time collision without
    # needing actual concurrent requests.
    monkeypatch.setattr(main, "_username_exists", lambda db, username: False)

    db = SessionLocal()
    try:
        db.add(User(username="raceduser", password_hash=main._hash_password("whatever")))
        db.commit()
    finally:
        db.close()

    resp = client.post("/auth/signup", json={"username": "raceduser", "password": "pw2"})
    assert resp.status_code == 409
    assert resp.json()["detail"] == "Username already taken"
