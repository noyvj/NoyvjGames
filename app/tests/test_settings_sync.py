"""Y31: account-synced site-wide settings (GET/PUT /users/me/settings)."""

from fastapi.testclient import TestClient

from database import SessionLocal
from main import app
from models import User

client = TestClient(app)


def _auth(username="settler", password="hunter22"):
    resp = client.post("/auth/signup", json={"username": username, "password": password})
    if resp.status_code == 409:
        resp = client.post("/auth/login", json={"username": username, "password": password})
    return {"Authorization": f"Bearer {resp.json()['bearer_token']}"}


def test_requires_sign_in():
    assert client.get("/users/me/settings").status_code == 401
    assert client.put("/users/me/settings", json={"theme": "dark"}).status_code == 401


def test_new_account_has_no_settings():
    headers = _auth("fresh1")
    resp = client.get("/users/me/settings", headers=headers)
    assert resp.status_code == 200
    assert resp.json() == {"settings": {}}
    assert resp.headers["cache-control"] == "no-store"


def test_put_then_get_round_trip():
    headers = _auth("roundtrip")
    body = {"theme": "light", "text_scale": 1.2, "reduced_motion": True}
    assert client.put("/users/me/settings", json=body, headers=headers).json() == {"settings": body}
    assert client.get("/users/me/settings", headers=headers).json() == {"settings": body}


def test_put_merges_instead_of_replacing():
    headers = _auth("merger")
    client.put("/users/me/settings", json={"theme": "light", "text_scale": 1.1}, headers=headers)
    resp = client.put("/users/me/settings", json={"reduced_motion": True}, headers=headers)
    assert resp.json()["settings"] == {"theme": "light", "text_scale": 1.1, "reduced_motion": True}


def test_settings_are_per_account():
    a, b = _auth("acct_a"), _auth("acct_b")
    client.put("/users/me/settings", json={"theme": "light"}, headers=a)
    assert client.get("/users/me/settings", headers=b).json() == {"settings": {}}


def test_unknown_keys_are_ignored_not_stored():
    headers = _auth("extras")
    resp = client.put("/users/me/settings", json={"theme": "dark", "evil": "<script>", "nested": {"a": 1}}, headers=headers)
    assert resp.status_code == 200
    assert resp.json() == {"settings": {"theme": "dark"}}


def test_invalid_values_are_rejected():
    headers = _auth("badvals")
    for bad in (
        {"theme": "purple"}, {"theme": 3}, {"text_scale": 0.5}, {"text_scale": 9},
        {"text_scale": "1.2"}, {"text_scale": True}, {"reduced_motion": "yes"}, {"reduced_motion": 1},
    ):
        assert client.put("/users/me/settings", json=bad, headers=headers).status_code == 422, bad
    assert client.get("/users/me/settings", headers=headers).json() == {"settings": {}}


def test_a_rejected_request_changes_nothing():
    headers = _auth("atomic")
    client.put("/users/me/settings", json={"theme": "light"}, headers=headers)
    assert client.put("/users/me/settings", json={"theme": "dark", "text_scale": 99}, headers=headers).status_code == 422
    assert client.get("/users/me/settings", headers=headers).json() == {"settings": {"theme": "light"}}


def test_non_object_body_rejected():
    headers = _auth("nonobj")
    assert client.put("/users/me/settings", json=[1, 2], headers=headers).status_code == 422


def test_hand_edited_row_is_re_validated_on_read():
    headers = _auth("tampered")
    with SessionLocal() as db:
        user = db.query(User).filter(User.username == "tampered").one()
        user.settings_json = '{"theme": "purple", "text_scale": 1.3, "junk": 1}'
        db.commit()
    assert client.get("/users/me/settings", headers=headers).json() == {"settings": {}}
    with SessionLocal() as db:
        user = db.query(User).filter(User.username == "tampered").one()
        user.settings_json = "not json"
        db.commit()
    assert client.get("/users/me/settings", headers=headers).json() == {"settings": {}}


def test_integer_text_scale_is_stored_as_float():
    headers = _auth("intscale")
    resp = client.put("/users/me/settings", json={"text_scale": 1}, headers=headers)
    assert resp.json()["settings"]["text_scale"] == 1.0
