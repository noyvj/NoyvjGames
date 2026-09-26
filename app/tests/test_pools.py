"""Shared community pools (H11 and the daily community plot)."""

import pools
from database import SessionLocal
from fastapi.testclient import TestClient
from main import app
from models import PoolDay

client = TestClient(app)
LOOP = "/pools/loop/recovered_units"


def setup_function():
    db = SessionLocal()
    db.query(PoolDay).delete()
    db.commit()
    db.close()
    pools.reset_rate_limits()


def test_unknown_pool_is_404():
    assert client.get("/pools/loop/nope").status_code == 404
    assert client.post("/pools/nope/x", json={"amount": 1}).status_code == 404


def test_empty_pool_reads_as_zero():
    data = client.get(LOOP).json()
    assert data["total"] == 0 and data["today"]["total"] == 0 and data["best_day"] is None
    assert data["label"] and data["recent_days"] == []


def test_contributions_add_up_without_an_account():
    client.post(LOOP, json={"amount": 12.5})
    data = client.post(LOOP, json={"amount": 7.5}).json()
    assert data["today"]["total"] == 20.0 and data["today"]["contributions"] == 2
    assert data["total"] == 20.0 and data["best_day"]["total"] == 20.0
    assert client.get(LOOP).json()["total"] == 20.0


def test_bad_amounts_are_rejected():
    limit = pools.POOLS[("loop", "recovered_units")]["max_per_request"]
    for bad in (0, -3, limit + 1, "lots", None):
        assert client.post(LOOP, json={"amount": bad}).status_code == 422
    assert client.get(LOOP).json()["total"] == 0


def test_best_day_and_recent_days_use_stored_days():
    db = SessionLocal()
    for day, total in (("2026-09-20", 50.0), ("2026-09-21", 90.0), ("2026-09-22", 10.0)):
        db.add(PoolDay(game_id="loop", pool="recovered_units", day=day, total=total, contributions=1))
    db.commit()
    db.close()
    data = client.get(LOOP).json()
    assert data["best_day"] == {"day": "2026-09-21", "total": 90.0}
    assert data["total"] == 150.0
    assert [d["day"] for d in data["recent_days"]] == ["2026-09-22", "2026-09-21", "2026-09-20"]


def test_rate_limit_stops_a_flood():
    for _ in range(pools.RATE_LIMIT_PER_HOUR):
        assert client.post(LOOP, json={"amount": 1}).status_code == 200
    assert client.post(LOOP, json={"amount": 1}).status_code == 429


def test_only_aggregates_are_exposed():
    client.post(LOOP, json={"amount": 5})
    data = client.get(LOOP).json()
    assert set(data) == {"game_id", "pool", "label", "today", "total", "best_day", "recent_days"}


def test_helpers():
    config = pools.pool_config("canopy", "community_plot")
    assert pools.valid_amount(config, 10) == 10.0
    assert pools.valid_amount(config, True) is None
    assert pools.valid_amount(config, float("nan")) is None
    assert pools.today_utc(0) == "1970-01-01"
