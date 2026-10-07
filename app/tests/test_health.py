"""GET /health (Y-27): the read-only check behind the hub footer's status dot."""

from fastapi.testclient import TestClient

import main
from main import app

client = TestClient(app)


def test_health_is_ok_when_the_database_answers():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok", "db": True}
    assert resp.headers["cache-control"] == "no-store"


def test_health_needs_no_sign_in_and_exposes_nothing_else():
    resp = client.get("/health")
    assert set(resp.json()) == {"status", "db"}


def test_health_reports_degraded_instead_of_failing_when_the_database_is_down(monkeypatch):
    class DeadEngine:
        def connect(self):
            raise RuntimeError("database unreachable")

    monkeypatch.setattr(main, "engine", DeadEngine())
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "degraded", "db": False}
