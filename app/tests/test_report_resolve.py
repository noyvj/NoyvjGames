"""U6: an admin can mark an answer report done; done reports drop out of the open queue."""

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


def test_new_reports_start_open():
    row = _make_report("resolve-new")
    assert row["is_resolved"] is False and row["resolved_at"] is None


def test_patch_requires_admin_token():
    row = _make_report("resolve-auth")
    assert client.patch(f"/answer-reports/{row['id']}", json={"resolved": True}).status_code == 401
    assert client.patch(f"/answer-reports/{row['id']}", json={"resolved": True},
                        headers={"X-Admin-Token": "wrong"}).status_code == 401


def test_mark_done_sets_flag_and_timestamp():
    row = _make_report("resolve-done")
    resp = client.patch(f"/answer-reports/{row['id']}", json={"resolved": True}, headers=ADMIN)
    assert resp.status_code == 200
    body = resp.json()
    assert body["is_resolved"] is True and body["resolved_at"] is not None


def test_reopen_clears_the_timestamp():
    row = _make_report("resolve-reopen")
    client.patch(f"/answer-reports/{row['id']}", json={"resolved": True}, headers=ADMIN)
    body = client.patch(f"/answer-reports/{row['id']}", json={"resolved": False}, headers=ADMIN).json()
    assert body["is_resolved"] is False and body["resolved_at"] is None


def test_unknown_report_is_404():
    assert client.patch("/answer-reports/no-such-id", json={"resolved": True}, headers=ADMIN).status_code == 404


def test_bad_body_is_422():
    row = _make_report("resolve-bad")
    for bad in ({}, {"resolved": "maybe"}, {"resolved": None}, [1]):
        assert client.patch(f"/answer-reports/{row['id']}", json=bad, headers=ADMIN).status_code == 422, bad


def test_done_reports_drop_out_of_the_open_filter():
    open_row = _make_report("resolve-filter-open")
    done_row = _make_report("resolve-filter-done")
    client.patch(f"/answer-reports/{done_row['id']}", json={"resolved": True}, headers=ADMIN)
    open_ids = [r["item_id"] for r in client.get("/answer-reports", params={"resolved": "false"}, headers=ADMIN).json()]
    done_ids = [r["item_id"] for r in client.get("/answer-reports", params={"resolved": "true"}, headers=ADMIN).json()]
    all_ids = [r["item_id"] for r in client.get("/answer-reports", headers=ADMIN).json()]
    assert "resolve-filter-open" in open_ids and "resolve-filter-done" not in open_ids
    assert "resolve-filter-done" in done_ids and "resolve-filter-open" not in done_ids
    assert "resolve-filter-open" in all_ids and "resolve-filter-done" in all_ids
    assert open_row["id"] != done_row["id"]


def test_patch_does_not_touch_the_report_content():
    row = _make_report("resolve-content")
    body = client.patch(f"/answer-reports/{row['id']}", json={"resolved": True}, headers=ADMIN).json()
    for key in ("game_id", "item_id", "submitted_answer", "marked_correct_answer", "topic_type"):
        assert body[key] == row[key]
