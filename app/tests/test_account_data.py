"""Y-14: GET /users/me/export and DELETE /users/me. The delete test fills EVERY table
that can hold a row linked to an account, deletes it, then checks directly in the
database that nothing of theirs (and nothing of anyone else's removed) remains."""

import boards
import pytest
from fastapi.testclient import TestClient

from database import SessionLocal
from main import app
from models import (
    AnswerReport, AuthSession, Feedback, HelpfulVote, LeaderboardEntry, Rating, Save, SaveSnapshot, ScoreEntry,
    ScoreProfile, User, BugReport, UserProfile,
)

client = TestClient(app)
GAME = "acctgame"
BOARD = "score_desc"
ENTRY = "site-2026-10-08-0a1b2c3d"


@pytest.fixture(autouse=True)
def board():
    boards.register_board(GAME, BOARD, label="Acct test", order="desc", low=0, high=1000, unit="pts")
    boards.reset_throttles()
    yield
    boards.unregister_board(GAME, BOARD)
    boards.reset_throttles()


def make_user(name):
    db = SessionLocal()
    user = db.query(User).filter(User.username == name).first()
    if user is None:
        user = User(username=name, password_hash="not-a-real-hash", email=f"{name}@example.test")
        db.add(user)
        db.commit()
    token = f"tok-{name}"
    if db.query(AuthSession).filter(AuthSession.token == token).first() is None:
        db.add(AuthSession(user_id=user.id, token=token))
        db.commit()
    uid = user.id
    db.close()
    return {"Authorization": f"Bearer {token}"}, uid


def fill_account(headers, uid):
    """One of everything that can be linked to an account."""
    assert client.put(f"/users/me/saves/{GAME}/slots/1", json={"save_data": {"achievements_earned": ["first_step", "second"], "n": 1}}, headers=headers).status_code == 200
    assert client.put(f"/users/me/saves/{GAME}/slots/2", json={"save_data": {"achievements_earned": ["third"]}, "name": "Second"}, headers=headers).status_code == 200
    assert client.post("/feedback", json={"game_id": GAME, "rating": 4, "comment": f"fb-{uid}"}, headers=headers).status_code == 200
    assert client.put("/leaderboards/sol/fastest_completion", json={"score": 100}, headers=headers).status_code == 200
    assert client.post("/scores", json={"game": GAME, "board": BOARD, "score": 50, "opt_in": True}, headers=headers).json()["accepted"]
    assert client.put("/users/me/leaderboard-privacy", json={"show_username": True}, headers=headers).status_code == 200
    assert client.put(f"/whats-new/votes/{ENTRY}", json={"helpful": True}, headers=headers).status_code == 200
    assert client.put("/users/me/settings", json={"theme": "light"}, headers=headers).status_code == 200
    assert client.post("/users/me/snapshots", json={"game_id": GAME, "slot": 1, "summary": f"snap-{uid}", "save_data": {"n": 0}}, headers=headers).status_code == 200
    # Z-7/Y-1 profile and Z-17 linked bug report
    assert client.put("/users/me/profile", json={"is_public": True, "progress": {"game": GAME, "add_seconds": 60, "achievements": 2}}, headers=headers).status_code == 200
    assert client.post("/bug-reports", json={"game_id": GAME, "note": f"bug-{uid}", "link_account": True}, headers=headers).status_code == 200


def rows_for(uid):
    db = SessionLocal()
    try:
        return {
            "users": db.query(User).filter(User.id == uid).count(),
            "sessions": db.query(AuthSession).filter(AuthSession.user_id == uid).count(),
            "saves": db.query(Save).filter(Save.user_id == uid).count(),
            "snapshots": db.query(SaveSnapshot).filter(SaveSnapshot.user_id == uid).count(),
            "legacy_boards": db.query(LeaderboardEntry).filter(LeaderboardEntry.user_id == uid).count(),
            "scores": db.query(ScoreEntry).filter(ScoreEntry.user_id == uid).count(),
            "profiles": db.query(ScoreProfile).filter(ScoreProfile.user_id == uid).count(),
            "feedback": db.query(Feedback).filter(Feedback.user_id == uid).count(),
            "votes": db.query(HelpfulVote).filter(HelpfulVote.user_id == uid).count(),
            "user_profiles": db.query(UserProfile).filter(UserProfile.user_id == uid).count(),
            "bug_reports": db.query(BugReport).filter(BugReport.user_id == uid).count(),
        }
    finally:
        db.close()


def test_export_requires_sign_in():
    assert client.get("/users/me/export").status_code == 401
    assert client.request("DELETE", "/users/me", json={"confirm_username": "x"}).status_code == 401


def test_export_holds_everything_and_no_secrets():
    headers, uid = make_user("exportee")
    fill_account(headers, uid)
    body = client.get("/users/me/export", headers=headers).json()
    assert body["account"]["username"] == "exportee"
    assert body["account"]["email"] == "exportee@example.test"
    assert body["account"]["settings"] == {"theme": "light"}
    assert len(body["saves"]) == 2
    assert {s["slot"] for s in body["saves"]} == {1, 2}
    assert body["saves"][0]["save_data"]["n"] == 1
    assert [(r["game_id"], r["slot"], r["save_data"]) for r in body["save_snapshots"]] == [(GAME, 1, {"n": 0})]
    assert body["achievements"][GAME] == ["first_step", "second", "third"]
    assert [f["comment"] for f in body["feedback"]] == [f"fb-{uid}"]
    assert body["leaderboards"]["show_username"] is True
    assert len(body["leaderboards"]["legacy_entries"]) == 1
    assert body["leaderboards"]["score_entries"][0]["score"] == 50
    assert body["profile"]["is_public"] is True and body["profile"]["total_achievements"] == 2
    assert [r["note"] for r in body["bug_reports"]] == [f"bug-{uid}"]
    assert body["whats_new_votes"] == [{"entry_id": ENTRY, "helpful": True, "updated_at": body["whats_new_votes"][0]["updated_at"]}]
    text = str(body)
    assert "not-a-real-hash" not in text and "tok-exportee" not in text and "password" not in text.lower().replace("passwords", "")


def test_export_only_contains_the_callers_rows():
    mine, _ = make_user("exp-mine")
    theirs, their_id = make_user("exp-theirs")
    client.put(f"/users/me/saves/{GAME}/slots/1", json={"save_data": {"secret": "theirs-only"}}, headers=theirs)
    client.post("/feedback", json={"comment": "theirs-comment"}, headers=theirs)
    body = client.get("/users/me/export", headers=mine).json()
    assert "theirs-only" not in str(body) and "theirs-comment" not in str(body)
    assert body["saves"] == [] and body["save_snapshots"] == []


def test_delete_needs_the_typed_username():
    headers, uid = make_user("typo-user")
    assert client.request("DELETE", "/users/me", json={"confirm_username": "nope"}, headers=headers).status_code == 422
    assert client.request("DELETE", "/users/me", json={}, headers=headers).status_code == 422
    assert rows_for(uid)["users"] == 1


def test_delete_removes_every_row_of_the_account_and_leaves_others_alone():
    headers, uid = make_user("goner")
    other, other_id = make_user("bystander")
    fill_account(headers, uid)
    fill_account(other, other_id)
    before = rows_for(uid)
    assert all(count >= 1 for count in before.values()), before

    resp = client.request("DELETE", "/users/me", json={"confirm_username": "  Goner "}, headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["deleted"] is True and body["removed"]["saves"] == 2 and body["removed"]["feedback"] == 1
    assert rows_for(uid) == {key: 0 for key in before}

    # the old token no longer works, and the name can be taken again
    assert client.get("/users/me", headers=headers).status_code == 401
    assert client.get("/users/me/export", headers=headers).status_code == 401
    # the bystander is untouched
    assert rows_for(other_id) == before
    # their feedback is gone, the bystander's stays
    db = SessionLocal()
    assert db.query(Feedback).filter(Feedback.comment == f"fb-{uid}").count() == 0
    assert db.query(Feedback).filter(Feedback.comment == f"fb-{other_id}").count() == 1
    db.close()


def test_delete_does_not_touch_unlinked_anonymous_rows():
    headers, uid = make_user("anon-keeper")
    db = SessionLocal()
    db.add(Rating(game_slug=GAME, stars=5, comment="anon star"))
    db.add(AnswerReport(game_id=GAME, item_id="i1", submitted_answer="a", marked_correct_answer=["b"]))
    db.add(Save(save_code="ANON-0001", game_id=GAME, save_data={"x": 1}))
    db.commit()
    db.close()
    assert client.request("DELETE", "/users/me", json={"confirm_username": "anon-keeper"}, headers=headers).status_code == 200
    db = SessionLocal()
    assert db.query(Rating).filter(Rating.comment == "anon star").count() == 1
    assert db.query(AnswerReport).filter(AnswerReport.item_id == "i1").count() == 1
    assert db.query(Save).filter(Save.save_code == "ANON-0001").count() == 1
    db.close()


def test_the_owner_account_cannot_be_deleted():
    # Other test modules sign this exact name up with a real password, so leave no trace behind.
    db = SessionLocal()
    existing = db.query(User).filter(User.username == "noyvj").first()
    db.close()
    assert existing is None, "the owner account already exists in this test database"
    headers, uid = make_user("noyvj")
    try:
        resp = client.request("DELETE", "/users/me", json={"confirm_username": "noyvj"}, headers=headers)
        assert resp.status_code == 403
        assert rows_for(uid)["users"] == 1
    finally:
        db = SessionLocal()
        db.query(AuthSession).filter(AuthSession.user_id == uid).delete()
        db.query(User).filter(User.id == uid).delete()
        db.commit()
        db.close()
