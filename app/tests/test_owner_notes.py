"""Owner notes: the ideas page's answers, saved to the account so they need no exporting."""

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)
KEY = "/owner/notes/ideas-answers"


def _bearer(username, password="hunter22"):
    resp = client.post("/auth/signup", json={"username": username, "password": password})
    if resp.status_code == 409:
        resp = client.post("/auth/login", json={"username": username, "password": password})
    return {"Authorization": f"Bearer {resp.json()['bearer_token']}"}


def test_nobody_without_credentials_can_read_or_write():
    assert client.get(KEY).status_code == 401
    assert client.put(KEY, json={"value": {}}).status_code == 401


def test_other_accounts_cannot_read_or_write():
    headers = _bearer("notowner2")
    assert client.get(KEY, headers=headers).status_code == 401
    assert client.put(KEY, headers=headers, json={"value": {"x": 1}}).status_code == 403


def test_owner_can_write_then_read_back():
    headers = _bearer("noyvj")
    value = {"round-3": {"GC": {"1": {"c": "yes", "m": "like it"}}}}
    put = client.put(KEY, headers=headers, json={"value": value})
    assert put.status_code == 200 and put.json()["key"] == "ideas-answers"
    got = client.get(KEY, headers=headers)
    assert got.status_code == 200
    assert got.json()["value"] == value
    assert got.headers["cache-control"] == "no-store"


def test_the_ai_admin_token_can_read_but_not_write():
    _bearer("noyvj")
    owner = _bearer("noyvj")
    client.put(KEY, headers=owner, json={"value": {"a": 1}})
    read = client.get(KEY, headers={"X-Admin-Token": "test-ai-token"})
    assert read.status_code == 200 and read.json()["value"] == {"a": 1}
    write = client.put(KEY, headers={"X-Admin-Token": "test-ai-token"}, json={"value": {"a": 2}})
    assert write.status_code == 401   # no bearer at all: the AI cannot answer for the owner


def test_a_second_write_replaces_the_first():
    headers = _bearer("noyvj")
    client.put(KEY, headers=headers, json={"value": {"n": 1}})
    client.put(KEY, headers=headers, json={"value": {"n": 2}})
    assert client.get(KEY, headers=headers).json()["value"] == {"n": 2}


def test_unknown_note_reads_as_empty():
    headers = _bearer("noyvj")
    got = client.get("/owner/notes/never-written", headers=headers)
    assert got.status_code == 200 and got.json()["value"] is None


def test_bad_keys_and_bad_bodies_are_rejected():
    headers = _bearer("noyvj")
    assert client.put("/owner/notes/Bad_Key", headers=headers, json={"value": 1}).status_code == 422
    assert client.put(KEY, headers=headers, json={"nope": 1}).status_code == 422
    assert client.get("/owner/notes/BAD", headers=headers).status_code == 422


def test_an_oversized_note_is_refused():
    headers = _bearer("noyvj")
    big = {"blob": "x" * 1_100_000}
    assert client.put(KEY, headers=headers, json={"value": big}).status_code == 413
