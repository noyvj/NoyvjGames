"""U8: admin endpoints require an X-Admin-Token (ADMIN_TOKEN or AI_ADMIN_TOKEN)."""

import os

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)
PROTECTED = ["/admin/stats", "/answer-reports"]


def test_no_token_is_rejected():
    for path in PROTECTED:
        assert client.get(path).status_code == 401, path


def test_wrong_token_is_rejected():
    for path in PROTECTED:
        assert client.get(path, headers={"X-Admin-Token": "nope"}).status_code == 401, path


def test_empty_token_is_rejected():
    for path in PROTECTED:
        assert client.get(path, headers={"X-Admin-Token": ""}).status_code == 401, path


def test_owner_token_works():
    for path in PROTECTED:
        assert client.get(path, headers={"X-Admin-Token": "test-admin-token"}).status_code == 200, path


def test_ai_token_works_independently():
    for path in PROTECTED:
        assert client.get(path, headers={"X-Admin-Token": "test-ai-token"}).status_code == 200, path


def test_revoking_the_ai_token_leaves_the_owner_token_working(monkeypatch):
    monkeypatch.delenv("AI_ADMIN_TOKEN")
    assert client.get("/admin/stats", headers={"X-Admin-Token": "test-ai-token"}).status_code == 401
    assert client.get("/admin/stats", headers={"X-Admin-Token": "test-admin-token"}).status_code == 200


def test_fails_closed_when_no_token_is_configured(monkeypatch):
    monkeypatch.delenv("ADMIN_TOKEN")
    monkeypatch.delenv("AI_ADMIN_TOKEN")
    for path in PROTECTED:
        assert client.get(path).status_code == 503, path
        assert client.get(path, headers={"X-Admin-Token": ""}).status_code == 503, path
        assert client.get(path, headers={"X-Admin-Token": "anything"}).status_code == 503, path


def test_token_is_case_and_whitespace_sensitive():
    assert client.get("/admin/stats", headers={"X-Admin-Token": "TEST-ADMIN-TOKEN"}).status_code == 401
    assert client.get("/admin/stats", headers={"X-Admin-Token": "test-admin-token "}).status_code == 401


def test_public_endpoints_stay_public():
    assert client.get("/feedback").status_code == 200
    assert client.get("/ratings/sol").status_code == 200


def test_posting_a_report_stays_public():
    resp = client.post(
        "/answer-reports",
        json={"game_id": "champ-de-mots", "topic_type": "vocab", "item_id": "auth-check",
              "submitted_answer": "x", "marked_correct_answer": ["y"]},
    )
    assert resp.status_code == 200


def test_cors_allows_the_admin_header():
    resp = client.options(
        "/admin/stats",
        headers={"Origin": "http://localhost:8073", "Access-Control-Request-Method": "GET",
                 "Access-Control-Request-Headers": "x-admin-token"},
    )
    assert resp.status_code == 200
    assert "x-admin-token" in resp.headers.get("access-control-allow-headers", "").lower() or \
        resp.headers.get("access-control-allow-headers") == "x-admin-token"


def test_env_fixture_is_set_for_this_suite():
    assert os.environ["ADMIN_TOKEN"] == "test-admin-token"
