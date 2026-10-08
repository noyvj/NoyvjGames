"""Y-31: GET /ratings-summary, the hub's star averages in one small response."""

from fastapi.testclient import TestClient

from database import SessionLocal
from main import app
from models import Rating

client = TestClient(app)
ADMIN = {"X-Admin-Token": "test-admin-token"}


def _rate(slug, stars=None, **extra):
    resp = client.post("/ratings", json={"game_slug": slug, **({"stars": stars} if stars else {}), **extra})
    assert resp.status_code == 200, resp.text
    return resp.json()["id"]


def _game(slug):
    return client.get("/ratings-summary").json()["games"].get(slug)


def test_average_count_and_distribution_per_game():
    for stars in (5, 4, 4, 1):
        _rate("rs-basic", stars, comment="a comment that must never appear in the summary")
    entry = _game("rs-basic")
    assert entry["count"] == 4
    assert entry["average"] == 3.5
    assert entry["distribution"] == {"1": 1, "2": 0, "3": 0, "4": 2, "5": 1}
    assert "comment" not in str(client.get("/ratings-summary").json())


def test_games_without_star_rows_are_absent_and_prompt_rows_do_not_count():
    _rate("rs-prompt-only", response="yes, it made me think")
    assert _game("rs-prompt-only") is None
    _rate("rs-mixed", 5)
    _rate("rs-mixed", response="no")
    _rate("rs-mixed", 3, response="both")
    entry = _game("rs-mixed")
    assert entry["count"] == 2 and entry["average"] == 4.0


def test_hidden_rows_are_left_out_and_come_back_when_unhidden():
    keep = _rate("rs-hidden", 5)
    test_row = _rate("rs-hidden", 1)
    assert client.patch(f"/admin/ratings/{test_row}", json={"is_hidden": True}, headers=ADMIN).status_code == 200
    entry = _game("rs-hidden")
    assert entry["count"] == 1 and entry["average"] == 5.0
    assert client.patch(f"/admin/ratings/{test_row}", json={"is_hidden": False}, headers=ADMIN).status_code == 200
    assert _game("rs-hidden")["count"] == 2
    # all rows hidden: the game disappears rather than showing an average of nothing
    for rid in (keep, test_row):
        client.patch(f"/admin/ratings/{rid}", json={"is_hidden": True}, headers=ADMIN)
    assert _game("rs-hidden") is None


def test_matches_what_the_per_game_listing_would_have_given():
    for stars in (2, 3, 5, 5, 4):
        _rate("rs-match", stars)
    rows = [r for r in client.get("/ratings/rs-match").json() if r["stars"] is not None]
    entry = _game("rs-match")
    assert entry["count"] == len(rows)
    assert abs(entry["average"] - sum(r["stars"] for r in rows) / len(rows)) < 1e-3


def test_public_with_a_short_cache_and_no_auth_needed():
    resp = client.get("/ratings-summary")
    assert resp.status_code == 200
    cache = resp.headers["cache-control"]
    assert "public" in cache and "max-age=60" in cache


def test_rows_with_out_of_range_stars_in_the_database_are_ignored():
    db = SessionLocal()
    db.add(Rating(game_slug="rs-corrupt", stars=9))
    db.add(Rating(game_slug="rs-corrupt", stars=4))
    db.commit()
    db.close()
    entry = _game("rs-corrupt")
    assert entry["count"] == 1 and entry["average"] == 4.0
