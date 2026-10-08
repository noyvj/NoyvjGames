"""An admin (the owner or the AI token) can tick "fixed" on an answer report with a note; it is separate from done."""

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)
ADMIN = {"X-Admin-Token": "test-admin-token"}


def _make_report(item_id):
    resp = client.post("/answer-reports", json={
        "game_id": "champ-de-mots", "item_id": item_id, "submitted_answer": "x",
        "marked_correct_answer": ["y"], "topic_type": "vocab",
    })
    assert resp.status_code == 200
    return resp.json()


def test_new_reports_are_not_fixed():
    row = _make_report("fixed-new")
    assert row["is_fixed"] is False and row["fixed_note"] is None and row["fixed_at"] is None


def test_fixed_requires_admin_token():
    row = _make_report("fixed-auth")
    assert client.patch(f"/answer-reports/{row['id']}/fixed", json={"fixed": True}).status_code == 401
    assert client.patch(f"/answer-reports/{row['id']}/fixed", json={"fixed": True},
                        headers={"X-Admin-Token": "wrong"}).status_code == 401


def test_mark_fixed_stores_note_and_time_and_leaves_done_alone():
    row = _make_report("fixed-set")
    body = client.patch(f"/answer-reports/{row['id']}/fixed",
                        json={"fixed": True, "note": "  Added 'nice' as an accepted answer.  "}, headers=ADMIN).json()
    assert body["is_fixed"] is True and body["fixed_note"] == "Added 'nice' as an accepted answer."
    assert body["fixed_at"] is not None
    assert body["is_resolved"] is False


def test_unfix_clears_note_and_time():
    row = _make_report("fixed-clear")
    client.patch(f"/answer-reports/{row['id']}/fixed", json={"fixed": True, "note": "n"}, headers=ADMIN)
    body = client.patch(f"/answer-reports/{row['id']}/fixed", json={"fixed": False, "note": "ignored"}, headers=ADMIN).json()
    assert body["is_fixed"] is False and body["fixed_note"] is None and body["fixed_at"] is None


def test_long_note_is_trimmed_and_unknown_report_is_404():
    row = _make_report("fixed-long")
    body = client.patch(f"/answer-reports/{row['id']}/fixed", json={"fixed": True, "note": "a" * 900}, headers=ADMIN).json()
    assert len(body["fixed_note"]) == 300
    assert client.patch("/answer-reports/no-such-id/fixed", json={"fixed": True}, headers=ADMIN).status_code == 404


def test_bad_body_is_422_and_list_shows_the_flag():
    row = _make_report("fixed-list")
    for bad in ({}, {"fixed": "maybe"}, [1]):
        assert client.patch(f"/answer-reports/{row['id']}/fixed", json=bad, headers=ADMIN).status_code == 422, bad
    client.patch(f"/answer-reports/{row['id']}/fixed", json={"fixed": True, "note": "ok"}, headers=ADMIN)
    rows = client.get("/answer-reports?item_id=fixed-list", headers=ADMIN).json()
    assert rows and rows[0]["is_fixed"] is True
