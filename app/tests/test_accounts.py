"""Accounts (ACCOUNTS-AND-FEEDBACK-DESIGN.md Phase 2, revised): username +
password sign-up/sign-in, save-claiming, and listing a user's saves. Runs
against the in-memory sqlite DB substituted in conftest.py, never the
real Neon database.
"""

from fastapi.testclient import TestClient

from main import app

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
