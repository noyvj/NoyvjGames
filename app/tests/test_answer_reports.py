"""Champ de Mots Milestone 9 (§14.2.4): the "I think this should count"
report queue. `answer_reports` is a plain flag-and-triage table -- no
auto-accept, no in-game admin UI (§14.4's decision): a human lists/filters
the queue via these endpoints and, if a report is genuine, hand-adds the
phrasing to the catalog item's `accepted_fr`/`accepted_en` array themselves.
Runs against the in-memory sqlite DB substituted in conftest.py, never the
real Neon database.
"""

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def _report(**overrides):
    payload = {
        "game_id": "champ-de-mots",
        "item_id": "fren151-w7-grammar001",
        "submitted_answer": "il y a un theatre",
        "marked_correct_answer": ["Il y a un théâtre.", "Il y a un théâtre"],
        "topic_type": "grammar",
    }
    payload.update(overrides)
    return payload


def test_create_answer_report_returns_the_stored_row():
    resp = client.post("/answer-reports", json=_report())
    assert resp.status_code == 200
    body = resp.json()
    assert body["item_id"] == "fren151-w7-grammar001"
    assert body["submitted_answer"] == "il y a un theatre"
    assert body["marked_correct_answer"] == ["Il y a un théâtre.", "Il y a un théâtre"]
    assert body["topic_type"] == "grammar"
    assert body["game_id"] == "champ-de-mots"
    assert body["id"]
    assert body["created_at"]


def test_create_answer_report_requires_item_id():
    resp = client.post(
        "/answer-reports",
        json={
            "submitted_answer": "il y a un theatre",
            "marked_correct_answer": ["Il y a un théâtre."],
        },
    )
    assert resp.status_code == 422


def test_create_answer_report_requires_submitted_answer():
    resp = client.post(
        "/answer-reports",
        json={"item_id": "x", "marked_correct_answer": ["y"]},
    )
    assert resp.status_code == 422


def test_create_answer_report_requires_at_least_one_marked_correct_answer():
    resp = client.post(
        "/answer-reports",
        json={"item_id": "x", "submitted_answer": "y", "marked_correct_answer": []},
    )
    assert resp.status_code == 422


def test_game_id_defaults_to_champ_de_mots_when_omitted():
    resp = client.post(
        "/answer-reports",
        json={
            "item_id": "fren151-w1-vocab002-i00",
            "submitted_answer": "zero",
            "marked_correct_answer": ["zéro"],
        },
    )
    assert resp.status_code == 200
    assert resp.json()["game_id"] == "champ-de-mots"


def test_topic_type_is_optional():
    resp = client.post(
        "/answer-reports",
        json={
            "item_id": "fren151-w1-vocab002-i00",
            "submitted_answer": "zero",
            "marked_correct_answer": ["zéro"],
        },
    )
    assert resp.status_code == 200
    assert resp.json()["topic_type"] is None


def test_list_answer_reports_returns_newest_first():
    """Sqlite's CURRENT_TIMESTAMP is only second-resolution, so two posts
    issued back-to-back in a test can land on an identical `created_at` --
    this checks the listing is actually sorted descending by that column
    (ties included) rather than assuming which of two rapid inserts is
    "newer"."""
    client.post("/answer-reports", json=_report(item_id="report-order-a"))
    client.post("/answer-reports", json=_report(item_id="report-order-b"))

    resp = client.get("/answer-reports")
    assert resp.status_code == 200
    created_ats = [row["created_at"] for row in resp.json()]
    assert created_ats == sorted(created_ats, reverse=True)


def test_list_answer_reports_filters_by_game_id():
    client.post("/answer-reports", json=_report(item_id="filter-game-a", game_id="champ-de-mots"))
    client.post("/answer-reports", json=_report(item_id="filter-game-b", game_id="some-other-game"))

    resp = client.get("/answer-reports", params={"game_id": "some-other-game"})
    assert resp.status_code == 200
    assert all(row["game_id"] == "some-other-game" for row in resp.json())
    assert any(row["item_id"] == "filter-game-b" for row in resp.json())
    assert not any(row["item_id"] == "filter-game-a" for row in resp.json())


def test_list_answer_reports_filters_by_topic_type():
    client.post("/answer-reports", json=_report(item_id="filter-topic-a", topic_type="grammar"))
    client.post("/answer-reports", json=_report(item_id="filter-topic-b", topic_type="vocab"))

    resp = client.get("/answer-reports", params={"topic_type": "vocab"})
    assert resp.status_code == 200
    assert all(row["topic_type"] == "vocab" for row in resp.json())
    assert any(row["item_id"] == "filter-topic-b" for row in resp.json())
    assert not any(row["item_id"] == "filter-topic-a" for row in resp.json())


def test_list_answer_reports_filters_by_item_id():
    client.post("/answer-reports", json=_report(item_id="filter-item-unique-1"))
    client.post("/answer-reports", json=_report(item_id="filter-item-unique-2"))

    resp = client.get("/answer-reports", params={"item_id": "filter-item-unique-1"})
    assert resp.status_code == 200
    rows = resp.json()
    assert rows
    assert all(row["item_id"] == "filter-item-unique-1" for row in rows)


def test_list_answer_reports_combines_filters():
    client.post(
        "/answer-reports",
        json=_report(item_id="combo-a", game_id="champ-de-mots", topic_type="grammar"),
    )
    client.post(
        "/answer-reports",
        json=_report(item_id="combo-b", game_id="champ-de-mots", topic_type="vocab"),
    )

    resp = client.get(
        "/answer-reports", params={"game_id": "champ-de-mots", "topic_type": "grammar"}
    )
    ids = [row["item_id"] for row in resp.json()]
    assert "combo-a" in ids
    assert "combo-b" not in ids
