"""Y29 (planning/TODO.md): the opt-in, self-hosted pageview counter."""

import pytest
from fastapi.testclient import TestClient

from database import SessionLocal
from main import app
from models import PageView

client = TestClient(app)


@pytest.fixture(autouse=True)
def _clean():
    def wipe():
        db = SessionLocal()
        db.query(PageView).delete()
        db.commit()
        db.close()

    wipe()
    yield
    wipe()


def test_pageview_starts_at_zero():
    db = SessionLocal()
    try:
        assert db.query(PageView).count() == 0
    finally:
        db.close()


def test_pageview_post_increments_and_returns_running_total():
    assert client.post("/stats/pageview").json() == {"total": 1}
    assert client.post("/stats/pageview").json() == {"total": 2}
    assert client.post("/stats/pageview").json() == {"total": 3}


def test_pageview_row_carries_no_identifying_data():
    client.post("/stats/pageview")
    db = SessionLocal()
    try:
        db.query(PageView).one()
        columns = {c.name for c in PageView.__table__.columns}
        assert columns == {"id", "created_at"}
    finally:
        db.close()
