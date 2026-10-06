"""GET /users/me: the token-to-username lookup behind shared/owner-gate.js."""

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def _auth(username, password="hunter22"):
    resp = client.post("/auth/signup", json={"username": username, "password": password})
    if resp.status_code == 409:
        resp = client.post("/auth/login", json={"username": username, "password": password})
    return {"Authorization": f"Bearer {resp.json()['bearer_token']}"}


def test_requires_sign_in():
    assert client.get("/users/me").status_code == 401
    assert client.get("/users/me", headers={"Authorization": "Bearer nonsense"}).status_code == 401


def test_returns_only_the_username():
    resp = client.get("/users/me", headers=_auth("whoami1"))
    assert resp.status_code == 200
    assert resp.json() == {"username": "whoami1"}
    assert resp.headers["cache-control"] == "no-store"
