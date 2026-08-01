"""Verifies the Milestone 6 schema extension (nullable stars + new
response field) without touching the real Neon database — see conftest.py
for the in-memory sqlite substitution. Each test uses its own game_slug so
tests don't see each other's rows (the sqlite DB persists for the whole
session, not per-test).
"""

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_existing_star_rating_flow_still_works():
    """The hub's pre-existing review widget: stars + optional comment, no response."""
    resp = client.post(
        "/ratings",
        json={"game_slug": "test-sol-stars", "stars": 4, "comment": "Fun!"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["stars"] == 4
    assert body["comment"] == "Fun!"
    assert body["response"] is None


def test_feedback_prompt_response_without_stars():
    """Canopy's end-of-session feedback prompt: response, no star rating."""
    resp = client.post(
        "/ratings",
        json={"game_slug": "test-canopy-feedback", "response": "yes — made me think about it"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["stars"] is None
    assert body["response"] == "yes — made me think about it"


def test_submission_with_neither_stars_nor_response_is_rejected():
    resp = client.post("/ratings", json={"game_slug": "test-empty-submission"})
    assert resp.status_code == 422


def test_submission_can_include_both_stars_and_response():
    resp = client.post(
        "/ratings",
        json={"game_slug": "test-both", "stars": 5, "response": "no — already knew this"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["stars"] == 5
    assert body["response"] == "no — already knew this"


def test_list_ratings_returns_feedback_rows_for_the_right_slug():
    client.post("/ratings", json={"game_slug": "test-list-canopy", "response": "yes"})
    client.post("/ratings", json={"game_slug": "test-list-other", "response": "no"})

    resp = client.get("/ratings/test-list-canopy")
    assert resp.status_code == 200
    rows = resp.json()
    assert len(rows) == 1
    assert rows[0]["response"] == "yes"


def test_out_of_range_stars_still_rejected():
    resp = client.post("/ratings", json={"game_slug": "test-bad-stars", "stars": 9})
    assert resp.status_code == 422
