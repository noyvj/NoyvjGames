"""Z-17: POST /bug-reports (public, rate limited, size limited), the admin list and triage routes,
the opt-in rules (a null field means "not attached") and the secret scrubbing of console lines."""

import pytest
from fastapi.testclient import TestClient

from database import SessionLocal
from main import app
from models import BugReport

client = TestClient(app)
ADMIN = {"X-Admin-Token": "test-admin-token"}
GOOD = {"game_id": "br-game", "page": "/games/br-game/index.html", "note": "The button did nothing."}


def _signed_in(name):
    resp = client.post("/auth/signup", json={"username": name, "password": "hunter22"})
    if resp.status_code == 409:
        resp = client.post("/auth/login", json={"username": name, "password": "hunter22"})
    return {"Authorization": f"Bearer {resp.json()['bearer_token']}"}


def _rows(game):
    db = SessionLocal()
    try:
        return db.query(BugReport).filter(BugReport.game_id == game).order_by(BugReport.created_at).all()
    finally:
        db.close()


def test_a_minimal_report_is_stored_with_nothing_optional():
    resp = client.post("/bug-reports", json={**GOOD, "game_id": "br-min"})
    assert resp.status_code == 200 and resp.json()["received"] is True
    (row,) = _rows("br-min")
    assert row.note == GOOD["note"] and row.page == GOOD["page"]
    assert row.browser is None and row.viewport is None and row.console_log is None
    assert row.attachment is None and row.user_id is None and row.schema_version is None
    assert row.is_resolved is False and row.is_fixed is False


def test_a_full_opt_in_report_round_trips_through_the_admin_list():
    body = {
        **GOOD, "game_id": "br-full", "schema_version": "7", "browser": "Chrome 130 on Mac", "viewport": "360x740",
        "console_log": [f"line {i}" for i in range(20)], "attachment": {"save_code": "abcd-2345"},
    }
    assert client.post("/bug-reports", json=body).status_code == 200
    rows = client.get("/admin/bug-reports", params={"game_id": "br-full"}, headers=ADMIN).json()
    assert len(rows) == 1
    row = rows[0]
    assert row["schema_version"] == "7" and row["browser"] == "Chrome 130 on Mac" and row["viewport"] == "360x740"
    assert len(row["console_log"]) == 20
    assert row["attachment"] == {"save_code": "ABCD-2345"}      # normalised to upper case
    assert row["username"] is None


@pytest.mark.parametrize("bad", [
    {"note": ""},
    {"note": "   "},
    {"note": "x" * 2001},
    {"game_id": ""},
    {"game_id": "has space"},
    {"game_id": "x" * 65},
    {"page": "p" * 301},
    {"viewport": "1" * 41},
    {"browser": "b" * 301},
    {"console_log": ["x"] * 21},
    {"console_log": "not a list"},
    {"attachment": {"save_code": "not-a-code"}},
    {"attachment": {"save_code": "ABCD-1111"}},          # 1 is not in the save-code alphabet
    {"attachment": {"save_code": 12345}},
    {"attachment": {"save_code": "ABCD-2345", "password": "hunter2"}},
    {"attachment": {"anything": "else"}},
])
def test_invalid_reports_are_refused(bad):
    resp = client.post("/bug-reports", json={**GOOD, "game_id": "br-bad", **bad})
    assert resp.status_code == 422, bad
    assert _rows("br-bad") == []


def test_the_page_is_stored_as_a_path_only():
    client.post("/bug-reports", json={**GOOD, "game_id": "br-page", "page": "/games/x/index.html?code=ABCD-2345#top"})
    assert _rows("br-page")[0].page == "/games/x/index.html"


def test_console_lines_are_scrubbed_and_capped():
    lines = [
        "fetch failed Authorization: Bearer abc.DEF-123_xyz",
        "GET /thing?token=sekrit123&x=1",
        "loaded save ABCD-2345 ok",
        "contact me at someone@example.com please",
        "y" * 900,
    ]
    client.post("/bug-reports", json={**GOOD, "game_id": "br-scrub", "console_log": lines})
    stored = _rows("br-scrub")[0].console_log
    text = "\n".join(stored)
    for secret in ("abc.DEF-123_xyz", "sekrit123", "ABCD-2345", "someone@example.com"):
        assert secret not in text
    assert "[removed]" in text
    assert all(len(line) <= 300 for line in stored)


def test_anonymous_unless_the_player_is_signed_in_and_asks_to_be_linked():
    headers = _signed_in("br-linker")
    client.post("/bug-reports", json={**GOOD, "game_id": "br-link", "link_account": False}, headers=headers)
    client.post("/bug-reports", json={**GOOD, "game_id": "br-link", "link_account": True})           # no token
    client.post("/bug-reports", json={**GOOD, "game_id": "br-link", "link_account": True}, headers={"Authorization": "Bearer junk"})
    client.post("/bug-reports", json={**GOOD, "game_id": "br-link", "link_account": True}, headers=headers)
    linked = [r.user_id is not None for r in _rows("br-link")]
    assert linked == [False, False, False, True]
    named = [r["username"] for r in client.get("/admin/bug-reports", params={"game_id": "br-link"}, headers=ADMIN).json()]
    assert sorted(n for n in named if n) == ["br-linker"]


def test_rate_limit_per_address(monkeypatch):
    import main
    monkeypatch.setattr(main, "BUG_REPORT_LIMITER", main.FailureLimiter(max_failures=3, window_seconds=3600))
    codes = [client.post("/bug-reports", json={**GOOD, "game_id": "br-rate"}).status_code for _ in range(5)]
    assert codes == [200, 200, 200, 429, 429]


def test_an_oversized_body_is_refused_before_it_is_read():
    resp = client.post("/bug-reports", content=b"{" + b" " * 6_000_000 + b"}", headers={"content-type": "application/json"})
    assert resp.status_code == 413


def test_admin_routes_need_admin():
    assert client.get("/admin/bug-reports").status_code == 401
    assert client.get("/admin/bug-reports", headers={"X-Admin-Token": "wrong"}).status_code == 401
    assert client.patch("/admin/bug-reports/x", json={"resolved": True}).status_code == 401
    headers = _signed_in("br-not-owner")
    assert client.get("/admin/bug-reports", headers=headers).status_code == 401
    assert client.get("/admin/bug-reports", headers={"X-Admin-Token": "test-ai-token"}).status_code == 200


def test_triage_resolved_and_fixed_work_like_answer_reports():
    client.post("/bug-reports", json={**GOOD, "game_id": "br-triage"})
    rid = client.get("/admin/bug-reports", params={"game_id": "br-triage"}, headers=ADMIN).json()[0]["id"]
    done = client.patch(f"/admin/bug-reports/{rid}", json={"resolved": True}, headers=ADMIN).json()
    assert done["is_resolved"] is True and done["resolved_at"] and done["is_fixed"] is False
    fixed = client.patch(f"/admin/bug-reports/{rid}", json={"fixed": True, "note": "  Fixed the button  "}, headers=ADMIN).json()
    assert fixed["is_fixed"] is True and fixed["fixed_note"] == "Fixed the button" and fixed["is_resolved"] is True
    reopened = client.patch(f"/admin/bug-reports/{rid}", json={"resolved": False, "fixed": False}, headers=ADMIN).json()
    assert reopened["is_resolved"] is False and reopened["is_fixed"] is False and reopened["fixed_note"] is None
    assert client.patch("/admin/bug-reports/nope", json={"resolved": True}, headers=ADMIN).status_code == 404


def test_admin_list_filters():
    for i in range(3):
        client.post("/bug-reports", json={**GOOD, "game_id": "br-filter", "note": f"n{i}"})
    ids = [r["id"] for r in client.get("/admin/bug-reports", params={"game_id": "br-filter"}, headers=ADMIN).json()]
    assert len(ids) == 3
    client.patch(f"/admin/bug-reports/{ids[0]}", json={"resolved": True}, headers=ADMIN)
    open_ = client.get("/admin/bug-reports", params={"game_id": "br-filter", "resolved": "false"}, headers=ADMIN).json()
    assert len(open_) == 2 and ids[0] not in [r["id"] for r in open_]
    assert len(client.get("/admin/bug-reports", params={"game_id": "br-filter", "limit": 1}, headers=ADMIN).json()) == 1
    assert client.get("/admin/bug-reports", params={"game_id": "br-nothing"}, headers=ADMIN).json() == []


def test_the_public_cannot_read_reports_back():
    client.post("/bug-reports", json={**GOOD, "game_id": "br-private", "attachment": {"save_code": "ABCD-2345"}})
    for path in ("/bug-reports", "/bug-reports/anything", "/answer-reports"):
        resp = client.get(path)
        assert resp.status_code in (401, 404, 405), path
        assert "ABCD-2345" not in resp.text
