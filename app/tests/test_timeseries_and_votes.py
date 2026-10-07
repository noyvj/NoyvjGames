"""Y-13 (GET /admin/timeseries) and Y-24 (What's New "was this helpful?" votes)."""

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

import account_data
import main
from database import SessionLocal
from main import app
from models import AnswerReport, AuthSession, Feedback, HelpfulVote, PageView, Rating, Save, User

client = TestClient(app)
ADMIN = {"X-Admin-Token": "test-admin-token"}
NOW = datetime.now(timezone.utc)


def at(days_ago, hour=12):
    d = (NOW - timedelta(days=days_ago)).date()
    return datetime(d.year, d.month, d.day, hour, tzinfo=timezone.utc)


def label(days_ago):
    return at(days_ago).date().isoformat()


def user_with_token(name, test=False):
    db = SessionLocal()
    user = db.query(User).filter(User.username == name).first()
    if user is None:
        user = User(username=name, password_hash="x", is_test=test, created_at=at(0))
        db.add(user)
        db.commit()
    token = f"tok-{name}"
    if db.query(AuthSession).filter(AuthSession.token == token).first() is None:
        db.add(AuthSession(user_id=user.id, token=token))
        db.commit()
    uid = user.id
    db.close()
    return {"Authorization": f"Bearer {token}"}, uid


# ------------------------------------------------------------ time series

def test_timeseries_needs_admin():
    assert client.get("/admin/timeseries").status_code == 401
    assert client.get("/admin/timeseries", headers={"X-Admin-Token": "wrong"}).status_code == 401


def test_timeseries_shape_is_zero_filled_and_clamped():
    body = client.get("/admin/timeseries?days=10", headers=ADMIN).json()
    assert len(body["days"]) == 10 and body["days"][-1] == label(0)
    for name in ("plays", "saves", "signups", "feedback", "ratings", "reports", "visits"):
        s = body["series"][name]
        assert len(s["counts"]) == 10 and s["total"] == sum(s["counts"])
    assert len(client.get("/admin/timeseries?days=1", headers=ADMIN).json()["days"]) == account_data.MIN_DAYS
    assert len(client.get("/admin/timeseries?days=9999", headers=ADMIN).json()["days"]) == account_data.MAX_DAYS
    assert len(client.get("/admin/timeseries", headers=ADMIN).json()["days"]) == account_data.DEFAULT_DAYS
    assert "errors" in body["notes"]


def test_timeseries_counts_by_day_and_excludes_test_and_hidden_rows():
    base = client.get("/admin/timeseries?days=14", headers=ADMIN).json()
    base_hidden_off = client.get("/admin/timeseries?days=14&hide_test=false", headers=ADMIN).json()
    _h, real_id = user_with_token("ts-real")
    _h, test_id = user_with_token("ts-test", test=True)
    db = SessionLocal()
    db.add_all([
        Save(save_code="TS-REAL-1", game_id="tsgame", save_data={}, user_id=real_id, created_at=at(2), updated_at=at(1)),
        Save(save_code="TS-TEST-1", game_id="tsgame", save_data={}, user_id=test_id, created_at=at(2), updated_at=at(2)),
        Save(save_code="TS-ANON-1", game_id="tsgame", save_data={}, created_at=at(3), updated_at=at(3)),
        Feedback(game_id=None, user_id=None, comment="ts-shown", created_at=at(2)),
        Feedback(game_id=None, user_id=None, comment="ts-hidden", is_hidden=True, created_at=at(2)),
        Feedback(game_id=None, user_id=test_id, comment="ts-test-author", created_at=at(2)),
        Rating(game_slug="tsgame", stars=5, created_at=at(1)),
        Rating(game_slug="tsgame", stars=1, is_hidden=True, created_at=at(1)),
        AnswerReport(game_id="tsgame", item_id="ts1", submitted_answer="a", marked_correct_answer=["b"], created_at=at(4)),
        PageView(created_at=at(0)),
        PageView(created_at=at(0)),
    ])
    db.commit()
    db.close()

    def delta(after, before, name, days_ago):
        i = after["days"].index(label(days_ago))
        return after["series"][name]["counts"][i] - before["series"][name]["counts"][i]

    now = client.get("/admin/timeseries?days=14", headers=ADMIN).json()
    assert delta(now, base, "saves", 2) == 1          # the test account's save is left out
    assert delta(now, base, "saves", 3) == 1          # anonymous saves count
    assert delta(now, base, "plays", 1) == 1          # updated yesterday
    assert delta(now, base, "plays", 2) == 0
    assert delta(now, base, "signups", 0) == 1        # ts-real only, ts-test is a test account
    assert delta(now, base, "feedback", 2) == 1       # hidden and test-authored rows are left out
    assert delta(now, base, "ratings", 1) == 1
    assert delta(now, base, "reports", 4) == 1
    assert delta(now, base, "visits", 0) == 2

    everything = client.get("/admin/timeseries?days=14&hide_test=false", headers=ADMIN).json()
    assert delta(everything, base_hidden_off, "saves", 2) == 2
    assert delta(everything, base_hidden_off, "feedback", 2) == 3
    assert delta(everything, base_hidden_off, "ratings", 1) == 2
    assert delta(everything, base_hidden_off, "signups", 0) == 2


def test_timeseries_leaves_out_days_older_than_the_window():
    before = client.get("/admin/timeseries?days=7", headers=ADMIN).json()["series"]["reports"]["total"]
    db = SessionLocal()
    db.add(AnswerReport(game_id="tsgame", item_id="old", submitted_answer="a", marked_correct_answer=["b"], created_at=at(40)))
    db.commit()
    db.close()
    assert client.get("/admin/timeseries?days=7", headers=ADMIN).json()["series"]["reports"]["total"] == before


# ------------------------------------------------------------ votes

ENTRY = "game-2026-10-08-deadbeef"
OTHER = "site-2026-10-07-00112233"
TOKEN = "anon-token-0123456789abcdef"


@pytest.fixture(autouse=True)
def fresh_votes():
    main.VOTE_LIMITER.reset()
    db = SessionLocal()
    db.query(HelpfulVote).delete()
    db.commit()
    db.close()
    yield
    main.VOTE_LIMITER.reset()


def tally(hide_test=True):
    body = client.get(f"/admin/whats-new-votes?hide_test={str(hide_test).lower()}", headers=ADMIN).json()
    return {e["entry_id"]: (e["up"], e["down"]) for e in body["entries"]}


def vote(entry, helpful, token=TOKEN, headers=None):
    h = dict(headers or {})
    if token:
        h["X-Vote-Token"] = token
    return client.put(f"/whats-new/votes/{entry}", json={"helpful": helpful}, headers=h)


def test_vote_validation():
    assert vote("not-an-entry", True).status_code == 422
    assert vote("../../etc", True).status_code in (404, 422)
    assert vote(ENTRY, True, token=None).status_code == 422          # nobody identifiable
    assert vote(ENTRY, True, token="short").status_code == 422
    assert client.put(f"/whats-new/votes/{ENTRY}", json={"helpful": "yes"}, headers={"X-Vote-Token": TOKEN}).status_code == 422
    assert tally() == {}


def test_one_vote_per_browser_and_voting_again_changes_it():
    assert vote(ENTRY, True).json() == {"entry_id": ENTRY, "helpful": True}
    assert vote(ENTRY, True).status_code == 200
    assert tally() == {ENTRY: (1, 0)}
    vote(ENTRY, False)
    assert tally() == {ENTRY: (0, 1)}
    vote(ENTRY, True, token="another-browser-token-9999")
    vote(OTHER, False)
    assert tally() == {ENTRY: (1, 1), OTHER: (0, 1)}


def test_one_vote_per_account_even_with_different_tokens():
    headers, uid = user_with_token("voter-one")
    vote(ENTRY, True, token=None, headers=headers)
    vote(ENTRY, True, token="whatever-token-0123456789", headers=headers)
    assert tally() == {ENTRY: (1, 0)}
    db = SessionLocal()
    assert db.query(HelpfulVote).filter(HelpfulVote.user_id == uid).count() == 1
    db.close()


def test_retracting_a_vote():
    vote(ENTRY, True)
    resp = client.delete(f"/whats-new/votes/{ENTRY}", headers={"X-Vote-Token": TOKEN})
    assert resp.status_code == 200 and resp.json()["removed"] == 1
    assert tally() == {}
    assert client.delete(f"/whats-new/votes/{ENTRY}", headers={"X-Vote-Token": TOKEN}).json()["removed"] == 0


def test_votes_are_rate_limited_per_address():
    for i in range(60):
        assert vote(ENTRY, True, token=f"flood-token-{i:016d}").status_code == 200
    assert vote(ENTRY, True, token="flood-token-after-the-limit").status_code == 429
    main.VOTE_LIMITER.reset()
    assert vote(ENTRY, True, token="flood-token-after-reset-ok").status_code == 200


def test_tallies_are_admin_only_and_leave_out_test_accounts():
    assert client.get("/admin/whats-new-votes").status_code == 401
    real, _ = user_with_token("vote-real")
    fake, _ = user_with_token("vote-test", test=True)
    vote(ENTRY, True, token=None, headers=real)
    vote(ENTRY, False, token=None, headers=fake)
    assert tally() == {ENTRY: (1, 0)}
    assert tally(hide_test=False) == {ENTRY: (1, 1)}
