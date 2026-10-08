"""FY-16: the username "noyvj" (the owner account, which carries admin access) cannot be signed up
unless the server environment variable OWNER_SIGNUP_ALLOWED is "1". Protects a rebuilt or empty
database only; the production owner account already exists. conftest.py turns the variable on for the
rest of the suite, so each test here sets or clears it explicitly."""

import pytest
from fastapi.testclient import TestClient

from database import SessionLocal
from main import app
from models import AuthSession, User

client = TestClient(app)


def _remove_owner():
    db = SessionLocal()
    for user in db.query(User).filter(User.username == "noyvj").all():
        db.query(AuthSession).filter(AuthSession.user_id == user.id).delete()
        db.delete(user)
    db.commit()
    db.close()


@pytest.fixture(autouse=True, scope="module")
def _leave_no_owner_account_behind():
    """Other modules assume a clean database for this one name (test_account_data checks it)."""
    _remove_owner()
    yield
    _remove_owner()


@pytest.fixture(autouse=True)
def _no_leftover_owner_variable(monkeypatch):
    monkeypatch.delenv("OWNER_SIGNUP_ALLOWED", raising=False)


@pytest.mark.parametrize("name", ["noyvj", "Noyvj", "  NOYVJ  "])
def test_owner_name_is_refused_by_default(name):
    resp = client.post("/auth/signup", json={"username": name, "password": "hunter22"})
    assert resp.status_code == 403
    assert "reserved" in resp.json()["detail"]
    assert "bearer_token" not in resp.json()


@pytest.mark.parametrize("value", ["", "0", "no", "false", "2"])
def test_other_values_of_the_variable_do_not_open_it(monkeypatch, value):
    monkeypatch.setenv("OWNER_SIGNUP_ALLOWED", value)
    assert client.post("/auth/signup", json={"username": "noyvj", "password": "hunter22"}).status_code == 403


def test_owner_name_works_when_the_variable_is_set(monkeypatch):
    monkeypatch.setenv("OWNER_SIGNUP_ALLOWED", "1")
    resp = client.post("/auth/signup", json={"username": "noyvj", "password": "hunter22"})
    if resp.status_code == 409:   # another test module already created it in this database
        return
    assert resp.status_code == 200 and resp.json()["username"] == "noyvj"


def test_lookalike_names_are_not_reserved():
    for name in ("noyvj2", "noyvjj", "xnoyvj", "noyvj-fan"):
        resp = client.post("/auth/signup", json={"username": name, "password": "hunter22"})
        assert resp.status_code in (200, 409), (name, resp.status_code)


def test_refusal_does_not_depend_on_whether_the_owner_exists(monkeypatch):
    first = client.post("/auth/signup", json={"username": "noyvj", "password": "x"}).status_code
    monkeypatch.setenv("OWNER_SIGNUP_ALLOWED", "1")
    client.post("/auth/signup", json={"username": "noyvj", "password": "hunter22"})   # exists now (or created)
    monkeypatch.delenv("OWNER_SIGNUP_ALLOWED")
    second = client.post("/auth/signup", json={"username": "noyvj", "password": "x"}).status_code
    assert first == second == 403


def test_login_for_an_existing_owner_is_unaffected(monkeypatch):
    monkeypatch.setenv("OWNER_SIGNUP_ALLOWED", "1")
    client.post("/auth/signup", json={"username": "noyvj", "password": "hunter22"})
    monkeypatch.delenv("OWNER_SIGNUP_ALLOWED")
    assert client.post("/auth/login", json={"username": "noyvj", "password": "hunter22"}).status_code == 200
