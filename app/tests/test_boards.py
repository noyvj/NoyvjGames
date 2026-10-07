"""W-5 / Z-4: the general opt-in board system (boards.py, POST /scores,
GET /leaderboard/{game}/{board}). Users and sessions are inserted directly so the
suite does not pay for password hashing; the clock is injected."""

import re
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

import boards
from database import SessionLocal
from main import app
from models import AuthSession, ScoreEntry, ScoreProfile, User

client = TestClient(app)
ADMIN = {"X-Admin-Token": "test-admin-token"}
GAME = "testgame"
HIGH = "score_desc"   # desc, 0 to 1000, daily + weekly + alltime
LOW = "time_asc"      # asc, 1 to 500, whole numbers, weekly + alltime only
ANON = re.compile(r"^Player [2-9A-HJ-NP-Z]{4}$")


def ts(year, month, day, hour=12, minute=0):
    return datetime(year, month, day, hour, minute, tzinfo=timezone.utc).timestamp()


T0 = ts(2026, 10, 8)  # a Thursday, ISO week 2026-W41


@pytest.fixture(autouse=True)
def fresh():
    boards.register_board(GAME, HIGH, label="Test high", order="desc", low=0, high=1000, unit="pts")
    boards.register_board(GAME, LOW, label="Test low", order="asc", low=1, high=500, integer=True,
                          windows=("weekly", "alltime"), unit="s")
    clock = {"now": T0}
    boards.set_clock(lambda: clock["now"])
    boards.reset_throttles()
    db = SessionLocal()
    db.query(ScoreEntry).delete()
    db.query(ScoreProfile).delete()
    db.commit()
    db.close()
    yield clock
    boards.set_clock(None)
    boards.reset_throttles()
    boards.unregister_board(GAME, HIGH)
    boards.unregister_board(GAME, LOW)


def make_user(name, *, test=False):
    """(auth headers, user id). Idempotent per username."""
    db = SessionLocal()
    user = db.query(User).filter(User.username == name).first()
    if user is None:
        user = User(username=name, password_hash="not-a-real-hash", is_test=test)
        db.add(user)
        db.commit()
    elif user.is_test != test:
        user.is_test = test
        db.commit()
    token = f"tok-{name}"
    if db.query(AuthSession).filter(AuthSession.token == token).first() is None:
        db.add(AuthSession(user_id=user.id, token=token))
        db.commit()
    user_id = user.id
    db.close()
    return {"Authorization": f"Bearer {token}"}, user_id


def post(headers, score, board=HIGH, **extra):
    body = {"game": GAME, "board": board, "score": score, "opt_in": True, **extra}
    return client.post("/scores", json=body, headers=headers)


def get(board=HIGH, headers=None, **params):
    return client.get(f"/leaderboard/{GAME}/{board}", params=params, headers=headers or {})


def fill(n, board=HIGH, start=100, prefix="p"):
    """n distinct accounts with distinct scores; returns their (headers, id) pairs."""
    users = []
    for i in range(n):
        headers, uid = make_user(f"{prefix}{i}")
        assert post(headers, start + i * 10, board=board).status_code == 200
        users.append((headers, uid))
    return users


# ---------------------------------------------------------------- registry

def test_register_board_validates_its_definition():
    ok = dict(label="x", order="desc", low=0, high=10)
    for bad in (
        {"game_id": "Bad Game", "board": "b"},
        {"game_id": "g", "board": "B!"},
        {"game_id": "g", "board": "b", "order": "sideways"},
        {"game_id": "g", "board": "b", "low": 5, "high": 5},
        {"game_id": "g", "board": "b", "low": float("nan")},
        {"game_id": "g", "board": "b", "high": float("inf")},
        {"game_id": "g", "board": "b", "windows": ()},
        {"game_id": "g", "board": "b", "windows": ("yearly",)},
        {"game_id": "g", "board": "b", "windows": ("daily", "daily")},
        {"game_id": "g", "board": "b", "label": ""},
    ):
        args = {"game_id": "g", "board": "b", **ok, **bad}
        with pytest.raises(ValueError):
            boards.register_board(**args)
    assert boards.board_config("g", "b") is None


def test_windows_are_kept_in_canonical_order_and_the_registry_lists_them():
    config = boards.register_board("regtest", "b", label="L", order="asc", low=0, high=1, windows=("alltime", "daily"))
    assert config["windows"] == ("daily", "alltime")
    try:
        data = client.get("/leaderboard").json()
        row = next(b for b in data["boards"] if b["game_id"] == "regtest")
        assert row["windows"] == ["daily", "alltime"] and row["default_window"] == "alltime"
        assert row["order"] == "asc" and row["label"] == "L"
        assert data["min_visible"] == boards.MIN_VISIBLE
        low = next(b for b in data["boards"] if b["board"] == LOW)
        assert low["default_window"] == "alltime" and low["integer"] is True
    finally:
        boards.unregister_board("regtest", "b")


def test_reserved_boards_for_planned_games_exist():
    for key in (("canopy", "community_investment"), ("last-line", "endless_best_wave"), ("thaw", "hold_the_line")):
        assert boards.board_config(*key) is not None


def test_unknown_board_is_404_everywhere():
    headers, _ = make_user("b_unknown")
    assert client.get("/leaderboard/nope/x").status_code == 404
    assert client.post("/scores", json={"game": "nope", "board": "x", "score": 1, "opt_in": True}, headers=headers).status_code == 404
    assert client.delete("/scores/nope/x", headers=headers).status_code == 404


# ------------------------------------------------------- validation bounds

def test_scores_outside_the_bounds_are_rejected_and_the_edges_accepted():
    headers, _ = make_user("b_bounds")
    for bad in (-0.01, 1000.01, 10**9, -5):
        assert post(headers, bad).status_code == 422, bad
    boards.reset_throttles()
    assert post(headers, 0).status_code == 200
    assert post(headers, 1000).status_code == 200
    assert get(headers=headers, window="alltime").json()["mine"]["score"] == 1000.0


def test_non_numbers_and_non_finite_values_are_rejected():
    headers, _ = make_user("b_junk")
    for bad in ("12", None, True, [1], {"a": 1}):
        assert post(headers, bad).status_code == 422, repr(bad)
    for raw in ("NaN", "Infinity", "-Infinity"):
        resp = client.post(
            "/scores", headers={**headers, "Content-Type": "application/json"},
            content=f'{{"game":"{GAME}","board":"{HIGH}","score":{raw},"opt_in":true}}',
        )
        assert resp.status_code == 422, raw
    assert client.post("/scores", json={"game": GAME, "board": HIGH, "opt_in": True}, headers=headers).status_code == 422


def test_an_integer_board_rejects_fractions_but_not_whole_floats():
    headers, _ = make_user("b_int")
    assert post(headers, 12.5, board=LOW).status_code == 422
    assert post(headers, 12.0, board=LOW).status_code == 200
    assert post(headers, 12, board=LOW).status_code == 200
    assert post(headers, 0, board=LOW).status_code == 422   # below the low bound of 1
    assert post(headers, 501, board=LOW).status_code == 422


def test_windows_option_must_be_a_subset_of_the_boards_windows():
    headers, _ = make_user("b_win_opt")
    assert post(headers, 5, windows=[]).status_code == 422
    assert post(headers, 5, windows=["yearly"]).status_code == 422
    assert post(headers, 5, board=LOW, windows=["daily"]).status_code == 422   # LOW has no daily window
    assert post(headers, 5, board=LOW, windows=["weekly"]).status_code == 200


def test_detail_is_cleaned_and_capped():
    headers, _ = make_user("b_detail")
    post(headers, 5, detail="line\nbreak\x00 " + "x" * 200)
    mine = get(headers=headers, window="alltime").json()["mine"]
    assert "\n" not in mine["detail"] and "\x00" not in mine["detail"] and len(mine["detail"]) <= 60


# ---------------------------------------------------------------- opt-in

def test_submitting_needs_an_account_and_an_explicit_opt_in():
    body = {"game": GAME, "board": HIGH, "score": 10, "opt_in": True}
    assert client.post("/scores", json=body).status_code == 401
    assert client.post("/scores", json=body, headers={"Authorization": "Bearer nonsense"}).status_code == 401
    headers, _ = make_user("b_optin")
    assert client.post("/scores", json={**body, "opt_in": False}, headers=headers).status_code == 400
    without = {k: v for k, v in body.items() if k != "opt_in"}
    assert client.post("/scores", json=without, headers=headers).status_code == 400
    assert client.post("/scores", json={**body, "opt_in": "yes"}, headers=headers).status_code == 422
    db = SessionLocal()
    assert db.query(ScoreEntry).count() == 0   # nothing was stored by any refused request
    db.close()


def test_reading_needs_no_account_and_is_never_cached():
    resp = get()
    assert resp.status_code == 200 and resp.headers["cache-control"] == "no-store"
    assert resp.json()["entries"] == [] and resp.json()["mine"] is None and resp.json()["shows_username"] is None


def test_test_accounts_never_post_and_do_not_count():
    headers, _ = make_user("b_testacct", test=True)
    data = post(headers, 50).json()
    assert data == {"accepted": False, "reason": "test account"}
    db = SessionLocal()
    assert db.query(ScoreEntry).count() == 0
    db.close()


def test_an_account_flagged_as_test_later_disappears_from_the_board():
    fill(3)
    assert len(get().json()["entries"]) == 3
    _, uid = make_user("p0")
    db = SessionLocal()
    db.query(User).filter(User.id == uid).update({"is_test": True})
    db.commit()
    db.close()
    data = get().json()
    assert data["suppressed"] is True and data["entries"] == []   # only two visible players left
    make_user("p0")  # restore the flag for other tests


# ----------------------------------------------------------- privacy tier

def test_entries_are_anonymous_by_default_and_never_carry_the_username():
    users = fill(4, prefix="privacy_secretname_")
    resp = get(headers=users[0][0])
    text = resp.text
    assert "privacy_secretname_" not in text and "user_id" not in text
    data = resp.json()
    assert [e["rank"] for e in data["entries"]] == [1, 2, 3, 4]
    assert all(ANON.match(e["name"]) for e in data["entries"])
    assert len({e["name"] for e in data["entries"]}) == 4
    assert [e["you"] for e in data["entries"]].count(True) == 1 and data["entries"][3]["you"] is True
    assert data["mine"]["name"] == data["entries"][3]["name"] and data["shows_username"] is False
    # Stable from one request to the next.
    assert [e["name"] for e in get().json()["entries"]] == [e["name"] for e in data["entries"]]


def test_the_same_account_has_a_different_handle_on_each_game():
    _, uid = make_user("b_perGame")
    assert boards.anon_name(uid, "game-a") != boards.anon_name(uid, "game-b")
    assert boards.anon_name(uid, "game-a") == boards.anon_name(uid, "game-a")
    assert ANON.match(boards.anon_name(uid, "game-a"))


def test_the_salt_changes_the_handles(monkeypatch):
    before = boards.anon_name("some-user-id", "g")
    monkeypatch.setenv("LEADERBOARD_SALT", "another-salt")
    assert boards.anon_name("some-user-id", "g") != before


def test_the_account_setting_shows_the_username_and_can_be_turned_back_off():
    users = fill(3, prefix="privshow_")
    headers = users[2][0]   # the top scorer, privshow_2
    assert client.get("/users/me/leaderboard-privacy", headers=headers).json() == {"show_username": False}
    assert client.put("/users/me/leaderboard-privacy", json={"show_username": True}, headers=headers).json() == {"show_username": True}
    data = get(headers=headers).json()
    assert data["entries"][0]["name"] == "privshow_2" and data["shows_username"] is True
    assert data["mine"]["name"] == "privshow_2"
    assert [e["name"] for e in data["entries"][1:]] != ["privshow_1", "privshow_0"]   # others stay anonymous
    assert all(ANON.match(e["name"]) for e in data["entries"][1:])
    # The setting is account-wide: it applies to every board, including past rows.
    post(headers, 77, board=LOW)
    assert client.put("/users/me/leaderboard-privacy", json={"show_username": False}, headers=headers).json() == {"show_username": False}
    assert ANON.match(get(headers=headers).json()["entries"][0]["name"])


def test_privacy_setting_needs_an_account_and_a_real_boolean():
    assert client.get("/users/me/leaderboard-privacy").status_code == 401
    assert client.put("/users/me/leaderboard-privacy", json={"show_username": True}).status_code == 401
    headers, _ = make_user("b_privbool")
    assert client.put("/users/me/leaderboard-privacy", json={"show_username": "yes"}, headers=headers).status_code == 422
    assert client.put("/users/me/leaderboard-privacy", json={}, headers=headers).status_code == 422


def test_clashing_anonymous_handles_get_longer_ones(monkeypatch):
    monkeypatch.setattr(boards, "anon_name", lambda uid, game, length=4: "Player AAAA" if length == 4 else f"Player {uid}-{length}")
    names = boards.public_names([("u1", "alice", False), ("u2", "bob", False), ("u3", "carol", True)], "g")
    assert names == ["Player u1-8", "Player u2-8", "carol"]
    assert boards.public_names([("u1", "alice", False)], "g") == ["Player AAAA"]


def test_the_players_handle_is_not_derived_from_the_username():
    a, uid_a = make_user("b_samename")
    assert "samename" not in boards.anon_name(uid_a, GAME).lower()


# ------------------------------------------------- small-group suppression

def test_a_board_is_hidden_until_enough_players_have_joined():
    users = fill(2)
    data = get(headers=users[0][0]).json()
    assert data["suppressed"] is True and data["entries"] == [] and data["total"] is None
    assert data["min_visible"] == boards.MIN_VISIBLE
    assert data["mine"] is not None and data["mine"]["rank"] == 2   # you always see your own entry
    assert get().json()["mine"] is None
    third, _ = make_user("p2")
    post(third, 500)
    shown = get().json()
    assert shown["suppressed"] is False and shown["total"] == 3 and len(shown["entries"]) == 3


def test_suppression_counts_only_visible_players():
    users = fill(3)
    assert get().json()["suppressed"] is False
    db = SessionLocal()
    db.query(ScoreEntry).filter(ScoreEntry.user_id == users[0][1]).update({"is_hidden": True})
    db.commit()
    db.close()
    assert get().json()["suppressed"] is True


def test_each_window_is_suppressed_on_its_own(fresh):
    fill(3)
    fresh["now"] = ts(2026, 10, 9)   # next day: the daily board is empty again, the week and all-time are not
    assert get(window="daily").json()["suppressed"] is True
    assert get(window="weekly").json()["suppressed"] is False
    assert get(window="alltime").json()["suppressed"] is False


def test_the_board_shows_only_the_top_ten_but_counts_everyone():
    fill(13)
    data = get().json()
    assert len(data["entries"]) == boards.TOP_N and data["total"] == 13
    assert data["entries"][0]["score"] == 220.0


# ---------------------------------------------------------- throttling

def test_the_default_limits_are_wired_to_the_limiters():
    assert boards.SUBMIT_LIMITER.max_failures == boards.SUBMIT_LIMIT_PER_HOUR == 60
    assert boards.SUBMIT_LIMITER.window_seconds == 3600
    assert boards.SUBMIT_IP_LIMITER.max_failures == boards.SUBMIT_IP_LIMIT_PER_HOUR
    assert boards.REJECT_LIMITER.max_failures == boards.REJECT_LIMIT_PER_15_MIN
    assert boards.REJECT_LIMITER.window_seconds == 15 * 60


@pytest.fixture
def small_limits(monkeypatch):
    """Tiny limits so the throttle tests make a handful of requests, not hundreds."""
    monkeypatch.setattr(boards.SUBMIT_LIMITER, "max_failures", 6)
    monkeypatch.setattr(boards.SUBMIT_IP_LIMITER, "max_failures", 10)


def test_one_account_is_limited_per_hour_and_the_clock_releases_it(fresh, small_limits):
    headers, _ = make_user("b_thr")
    for _ in range(6):
        assert post(headers, 5).status_code == 200
    assert post(headers, 6).status_code == 429
    fresh["now"] = T0 + 3601
    assert post(headers, 7).status_code == 200


def test_repeatedly_probing_the_bounds_gets_the_account_cut_off(fresh):
    headers, _ = make_user("b_probe")
    for _ in range(boards.REJECT_LIMIT_PER_15_MIN):
        assert post(headers, 10**6).status_code == 422
    assert post(headers, 10**6).status_code == 429
    assert post(headers, 5).status_code == 429   # even a good score waits
    fresh["now"] = T0 + 15 * 60 + 1
    assert post(headers, 5).status_code == 200


def test_throttle_is_per_account_not_global(small_limits):
    a, _ = make_user("b_thr_a")
    b, _ = make_user("b_thr_b")
    for _ in range(6):
        post(a, 5)
    assert post(a, 5).status_code == 429
    assert post(b, 5).status_code == 200


def test_many_accounts_behind_one_address_hit_the_address_limit(small_limits):
    per_user = 4
    ip = {"X-Forwarded-For": "203.0.113.50"}
    sent = 0
    i = 0
    while sent < 10:
        headers, _ = make_user(f"b_ip_{i}")
        i += 1
        for _ in range(min(per_user, 10 - sent)):
            assert post({**headers, **ip}, 5).status_code == 200
            sent += 1
    fresh_user, _ = make_user("b_ip_fresh")
    assert post({**fresh_user, **ip}, 5).status_code == 429
    assert post({**fresh_user, "X-Forwarded-For": "203.0.113.51"}, 5).status_code == 200


def test_refused_requests_do_not_use_up_the_submit_allowance():
    headers, _ = make_user("b_refused")
    for _ in range(boards.REJECT_LIMIT_PER_15_MIN - 1):
        client.post("/scores", json={"game": GAME, "board": HIGH, "score": 5, "opt_in": False}, headers=headers)   # 400s
    assert post(headers, 5).status_code == 200


# ------------------------------------------------------------- hidden rows

def test_admin_routes_need_the_admin_token():
    assert client.get("/admin/scores").status_code == 401
    assert client.get("/admin/scores", headers={"X-Admin-Token": "wrong"}).status_code == 401
    assert client.patch("/admin/scores/abc", json={"is_hidden": True}).status_code == 401


def test_admin_can_hide_a_test_row_and_restore_it():
    users = fill(4, prefix="hid")   # scores 100, 110, 120, 130
    top_headers, top_uid = users[3]
    rows = client.get("/admin/scores", params={"game_id": GAME, "board": HIGH, "window": "alltime"}, headers=ADMIN).json()
    assert len(rows) == 4 and {r["username"] for r in rows} == {"hid0", "hid1", "hid2", "hid3"}
    target = next(r for r in rows if r["username"] == "hid3")
    assert target["is_hidden"] is False and target["is_test_account"] is False

    hidden = client.patch(f"/admin/scores/{target['id']}", json={"is_hidden": True}, headers=ADMIN)
    assert hidden.status_code == 200 and hidden.json()["is_hidden"] is True
    data = get(headers=top_headers).json()
    assert data["total"] == 3 and [e["score"] for e in data["entries"]] == [120.0, 110.0, 100.0]
    assert data["mine"] is None   # a hidden row is not shown to its owner either
    # Everyone's rank moved up and the row still exists for admin.
    again = client.get("/admin/scores", params={"game_id": GAME, "board": HIGH}, headers=ADMIN).json()
    assert next(r for r in again if r["id"] == target["id"])["is_hidden"] is True
    assert all(r["id"] != target["id"] for r in client.get("/admin/scores", params={"include_hidden": "false", "game_id": GAME}, headers=ADMIN).json())

    client.patch(f"/admin/scores/{target['id']}", json={"is_hidden": False}, headers=ADMIN)
    assert get().json()["total"] == 4


def test_a_hidden_row_stays_hidden_when_the_player_improves_it():
    users = fill(3, prefix="hs")
    rows = client.get("/admin/scores", params={"game_id": GAME, "board": HIGH, "window": "alltime"}, headers=ADMIN).json()
    row = next(r for r in rows if r["username"] == "hs2")
    client.patch(f"/admin/scores/{row['id']}", json={"is_hidden": True}, headers=ADMIN)
    resp = post(users[2][0], 900).json()
    assert resp["accepted"] is True and resp["results"]["alltime"]["improved"] is True
    assert resp["results"]["alltime"]["rank"] is None   # no rank is revealed for a hidden row
    assert get().json()["suppressed"] is True


def test_admin_hide_of_an_unknown_row_is_404_and_flag_must_be_boolean():
    assert client.patch("/admin/scores/does-not-exist", json={"is_hidden": True}, headers=ADMIN).status_code == 404
    users = fill(1, prefix="hb")
    row = client.get("/admin/scores", params={"game_id": GAME}, headers=ADMIN).json()[0]
    assert client.patch(f"/admin/scores/{row['id']}", json={"is_hidden": "yes"}, headers=ADMIN).status_code == 422


def test_public_reads_never_show_hidden_rows_in_ranks():
    users = fill(4, prefix="rk")   # 100..130
    rows = client.get("/admin/scores", params={"game_id": GAME, "board": HIGH, "window": "alltime"}, headers=ADMIN).json()
    top = next(r for r in rows if r["score"] == 130.0)
    client.patch(f"/admin/scores/{top['id']}", json={"is_hidden": True}, headers=ADMIN)
    assert get(headers=users[2][0]).json()["mine"]["rank"] == 1   # 120 is now first


# ------------------------------------------------------------ windows (clock)

def test_a_submit_updates_the_day_the_week_and_all_time(fresh):
    headers, _ = make_user("b_win")
    data = post(headers, 40).json()
    assert data["accepted"] is True and data["improved"] is True
    assert {w: r["period"] for w, r in data["results"].items()} == {"daily": "2026-10-08", "weekly": "2026-W41", "alltime": "all"}
    db = SessionLocal()
    assert db.query(ScoreEntry).count() == 3
    db.close()


def test_the_daily_board_rolls_over_at_utc_midnight(fresh):
    users = fill(3, prefix="dr")
    assert get(window="daily").json()["total"] == 3
    fresh["now"] = ts(2026, 10, 8, 23, 59)
    assert get(window="daily").json()["total"] == 3
    fresh["now"] = ts(2026, 10, 9, 0, 0)
    assert get(window="daily").json()["total"] is None and get(window="daily").json()["period"] == "2026-10-09"
    # Yesterday is still readable by asking for its period.
    past = get(window="daily", period="2026-10-08").json()
    assert past["total"] == 3 and past["suppressed"] is False
    # Same ISO week, so the weekly board carried over.
    assert get(window="weekly").json()["total"] == 3


def test_the_weekly_board_starts_on_monday(fresh):
    headers, _ = make_user("b_week")
    fresh["now"] = ts(2026, 10, 11, 23, 0)   # Sunday
    assert post(headers, 10).json()["results"]["weekly"]["period"] == "2026-W41"
    fresh["now"] = ts(2026, 10, 12, 0, 1)    # Monday
    assert post(headers, 20).json()["results"]["weekly"]["period"] == "2026-W42"
    db = SessionLocal()
    weekly = sorted((r.period, r.score) for r in db.query(ScoreEntry).filter(ScoreEntry.window == "weekly"))
    db.close()
    assert weekly == [("2026-W41", 10.0), ("2026-W42", 20.0)]


def test_weeks_follow_the_iso_year(fresh):
    assert boards.window_period("weekly", ts(2026, 12, 31)) == "2026-W53"
    assert boards.window_period("weekly", ts(2027, 1, 3)) == "2026-W53"
    assert boards.window_period("weekly", ts(2027, 1, 4)) == "2027-W01"
    assert boards.window_period("daily", ts(2027, 1, 1)) == "2027-01-01"
    assert boards.window_period("alltime", T0) == "all"
    with pytest.raises(ValueError):
        boards.window_period("hourly", T0)


def test_only_the_best_score_is_kept_per_window(fresh):
    headers, _ = make_user("b_best")
    assert post(headers, 500).json()["improved"] is True
    worse = post(headers, 300).json()
    assert worse["improved"] is False and worse["results"]["alltime"]["score"] == 500.0
    assert post(headers, 700, detail="new best").json()["improved"] is True
    # A worse score on a later day still beats nothing on that day's board, and does not touch all-time.
    fresh["now"] = ts(2026, 10, 9)
    later = post(headers, 100).json()["results"]
    assert later["daily"]["improved"] is True and later["alltime"]["improved"] is False
    assert later["alltime"]["score"] == 700.0 and later["daily"]["score"] == 100.0
    db = SessionLocal()
    assert db.query(ScoreEntry).filter(ScoreEntry.window == "alltime").count() == 1
    db.close()
    assert get(headers=headers, window="alltime").json()["mine"]["detail"] == "new best"


def test_an_ascending_board_keeps_the_lowest_score(fresh):
    headers, _ = make_user("b_asc")
    post(headers, 300, board=LOW)
    assert post(headers, 400, board=LOW).json()["improved"] is False
    assert post(headers, 250, board=LOW).json()["improved"] is True
    assert get(board=LOW, headers=headers, window="alltime").json()["mine"]["score"] == 250.0


def test_ascending_boards_rank_the_lowest_first():
    for i, secs in enumerate((90, 30, 60)):
        headers, _ = make_user(f"asc{i}")
        post(headers, secs, board=LOW)
    assert [e["score"] for e in get(board=LOW).json()["entries"]] == [30.0, 60.0, 90.0]


def test_the_windows_option_limits_which_boards_are_touched(fresh):
    headers, _ = make_user("b_only_all")
    data = post(headers, 40, windows=["alltime"]).json()
    assert list(data["results"]) == ["alltime"]
    db = SessionLocal()
    assert [r.window for r in db.query(ScoreEntry)] == ["alltime"]
    db.close()


def test_a_board_only_has_its_declared_windows():
    headers, _ = make_user("b_declared")
    data = post(headers, 40, board=LOW).json()
    assert sorted(data["results"]) == ["alltime", "weekly"]
    assert get(board=LOW, window="daily").status_code == 422
    assert get(board=LOW).json()["window"] == "alltime"          # the default view
    assert get(board=HIGH).json()["window"] == "alltime"
    assert get(window="yearly").status_code == 422


def test_period_parameter_is_validated(fresh):
    for window, bad in (("daily", "2026-10-09"), ("daily", "2026-13-01"), ("daily", "yesterday"), ("daily", "2026-W41"),
                        ("weekly", "2026-W42"), ("weekly", "2026-W60"), ("weekly", "2026-10-08"), ("alltime", "2026-10-08")):
        assert get(window=window, period=bad).status_code == 422, (window, bad)
    for window, good in (("daily", "2026-10-08"), ("daily", "2020-01-01"), ("weekly", "2026-W41"), ("alltime", "all")):
        assert get(window=window, period=good).status_code == 200, (window, good)
    assert boards.valid_period("weekly", "2026-W53", ts(2027, 1, 1)) is True
    assert boards.valid_period("weekly", "2025-W53", ts(2027, 1, 1)) is False   # 2025 has 52 ISO weeks


def test_old_daily_and_weekly_rows_are_pruned_but_all_time_is_kept(fresh):
    headers, uid = make_user("b_prune")
    db = SessionLocal()
    db.add_all([
        ScoreEntry(game_id=GAME, board=HIGH, user_id=uid, window="daily", period="2026-06-01", score=1),
        ScoreEntry(game_id=GAME, board=HIGH, user_id=uid, window="daily", period="2026-09-20", score=1),
        ScoreEntry(game_id=GAME, board=HIGH, user_id=uid, window="weekly", period="2025-W01", score=1),
        ScoreEntry(game_id=GAME, board=HIGH, user_id=uid, window="weekly", period="2026-W30", score=1),
    ])
    db.commit()
    db.close()
    post(headers, 50)
    db = SessionLocal()
    kept = sorted((r.window, r.period) for r in db.query(ScoreEntry))
    db.close()
    assert ("daily", "2026-06-01") not in kept and ("weekly", "2025-W01") not in kept
    assert ("daily", "2026-09-20") in kept and ("weekly", "2026-W30") in kept
    assert ("alltime", "all") in kept


def test_prune_cutoffs_are_ninety_days_and_about_a_year():
    cutoffs = boards.prune_cutoffs(T0)
    assert cutoffs["daily"] == "2026-07-10"
    assert cutoffs["weekly"] == "2025-W40"   # 370 days back is Friday 2025-10-03


# ------------------------------------------------- the player's own view

def test_my_scores_lists_current_rows_with_ranks_and_the_setting(fresh):
    users = fill(3, prefix="my")
    headers = users[0][0]
    fresh["now"] = ts(2026, 10, 9)
    post(headers, 1)   # a new day: a new daily row
    mine = client.get("/users/me/scores", headers=headers).json()
    assert mine["show_username"] is False
    by_window = {r["window"]: r for r in mine["scores"] if r["board"] == HIGH}
    assert by_window["daily"]["period"] == "2026-10-09" and by_window["daily"]["score"] == 1.0 and by_window["daily"]["rank"] == 1
    assert by_window["alltime"]["score"] == 100.0 and by_window["alltime"]["rank"] == 3
    assert by_window["weekly"]["rank"] == 3
    assert all(r["label"] and r["game_id"] == GAME for r in mine["scores"])
    assert client.get("/users/me/scores").status_code == 401


def test_my_scores_skips_past_days():
    headers, uid = make_user("b_mypast")
    db = SessionLocal()
    db.add(ScoreEntry(game_id=GAME, board=HIGH, user_id=uid, window="daily", period="2026-09-30", score=9))
    db.commit()
    db.close()
    assert client.get("/users/me/scores", headers=headers).json()["scores"] == []


def test_opting_out_of_one_board_removes_only_that_boards_rows():
    headers, uid = make_user("b_out")
    post(headers, 20)
    post(headers, 30, board=LOW)
    assert client.delete(f"/scores/{GAME}/{HIGH}").status_code == 401
    assert client.delete(f"/scores/{GAME}/{HIGH}", headers=headers).json() == {"removed": 3}
    db = SessionLocal()
    assert sorted(r.board for r in db.query(ScoreEntry).filter(ScoreEntry.user_id == uid)) == [LOW, LOW]
    db.close()
    assert client.delete(f"/scores/{GAME}/{HIGH}", headers=headers).json() == {"removed": 0}


def test_opting_out_of_everything_removes_every_row_but_only_this_accounts():
    headers, uid = make_user("b_outall")
    other, other_uid = make_user("b_outall_other")
    post(headers, 20)
    post(headers, 30, board=LOW)
    post(other, 20)
    assert client.delete("/users/me/scores", headers=headers).json() == {"removed": 5}
    db = SessionLocal()
    assert db.query(ScoreEntry).filter(ScoreEntry.user_id == uid).count() == 0
    assert db.query(ScoreEntry).filter(ScoreEntry.user_id == other_uid).count() == 3
    db.close()
    assert client.delete("/users/me/scores").status_code == 401


def test_the_registry_route_is_cacheable_and_lists_every_board():
    resp = client.get("/leaderboard")
    assert resp.status_code == 200 and "max-age" in resp.headers["cache-control"]
    ids = {(b["game_id"], b["board"]) for b in resp.json()["boards"]}
    assert (GAME, HIGH) in ids and ("canopy", "community_investment") in ids
