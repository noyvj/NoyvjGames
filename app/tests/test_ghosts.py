"""R-33: anonymous ghost settlements (ghosts.py: POST/DELETE /ghosts, GET /ghosts/{game}/peer,
POST /ghosts/report, admin routes). Users and sessions are inserted directly so the suite does not pay
for password hashing; the clock and the RNG are injected."""

import random

import pytest
from fastapi.testclient import TestClient

import ghosts
from database import SessionLocal
from main import app
from models import AuthSession, GhostReport, GhostSeries, User

client = TestClient(app)
ADMIN = {"X-Admin-Token": "test-admin-token"}
GAME = "continuum"


@pytest.fixture(autouse=True)
def fresh():
    clock = {"now": 1_800_000_000.0}
    ghosts.set_clock(lambda: clock["now"])
    ghosts.set_rng(random.Random(7))
    ghosts.reset_throttles()
    db = SessionLocal()
    db.query(GhostReport).delete()
    db.query(GhostSeries).delete()
    db.commit()
    db.close()
    yield clock
    ghosts.set_clock(None)
    ghosts.set_rng(None)
    ghosts.reset_throttles()


def make_user(name, *, test=False):
    name = f"gh-{name}"   # a prefix of its own, so these direct-insert accounts never collide with other test files' sign-ups
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
    uid = user.id
    db.close()
    return {"Authorization": f"Bearer {token}"}, uid


def series(n=8, era=2, people=10, score=40.0):
    return [[i + 1, era, people + i, score + i] for i in range(n)]


def publish(headers, *, rows=None, scenario="standard", hard=False, opt_in=True, game=GAME, **extra):
    body = {"game": game, "scenario": scenario, "hard": hard, "series": rows if rows is not None else series(),
            "opt_in": opt_in, **extra}
    return client.post("/ghosts", json=body, headers=headers)


def peer(headers=None, *, scenario="standard", era=2, hard=False, **params):
    query = {"scenario": scenario, "era": era, "hard": str(hard).lower(), **params}
    return client.get(f"/ghosts/{GAME}/peer", params=query, headers=headers or {})


def fill(n, *, prefix="p", era=2, scenario="standard", hard=False):
    users = []
    for i in range(n):
        headers, uid = make_user(f"{prefix}{i}")
        assert publish(headers, rows=series(era=era, people=10 + i), scenario=scenario, hard=hard).status_code == 200
        users.append((headers, uid))
    return users


def rows_in_db():
    db = SessionLocal()
    try:
        return db.query(GhostSeries).count()
    finally:
        db.close()


# ---------------------------------------------------------------- opt-in and auth

def test_publish_needs_an_account():
    assert client.post("/ghosts", json={"game": GAME, "scenario": "standard", "series": series(), "opt_in": True}).status_code == 401


def test_publish_without_opt_in_is_refused_and_stores_nothing():
    headers, _ = make_user("optless")
    assert publish(headers, opt_in=False).status_code == 400
    assert client.post("/ghosts", json={"game": GAME, "scenario": "standard", "series": series()}, headers=headers).status_code == 400
    assert rows_in_db() == 0


def test_opt_in_must_be_a_real_boolean():
    headers, _ = make_user("strict")
    body = {"game": GAME, "scenario": "standard", "series": series(), "opt_in": "true"}
    assert client.post("/ghosts", json=body, headers=headers).status_code == 422
    assert rows_in_db() == 0


def test_unknown_game_is_404():
    headers, _ = make_user("nogame")
    assert publish(headers, game="not-a-game").status_code == 404
    assert client.get("/ghosts/not-a-game/peer").status_code == 404


def test_a_test_account_is_accepted_but_nothing_is_stored():
    headers, _ = make_user("tester", test=True)
    body = publish(headers).json()
    assert body == {"accepted": False, "reason": "test account"}
    assert rows_in_db() == 0


# ---------------------------------------------------------------- validation

@pytest.mark.parametrize("rows", [
    "not a list",
    series(4),                                        # fewer than the minimum
    series(151),                                      # more than the maximum
    [[1, 2, 10]] * 5,                                 # wrong row length
    [[1, 2, 10, 40, 9]] * 5,
    [["1", 2, 10, 40]] * 5,                           # strings are not numbers
    [[True, 2, 10, 40]] * 5,                          # neither are booleans
    [[1.5, 2, 10, 40]] + series(6)[1:],               # fractional season
    [[1, 2.5, 10, 40]] + series(6)[1:],               # fractional era
    [[0, 2, 10, 40]] + series(6)[1:],                 # season below 1
    [[1, 2, 10, 40]] * 6,                             # seasons not increasing
    [[1, 8, 10, 40]] + series(6)[1:],                 # era above the top era
    [[1, -1, 10, 40]] + series(6)[1:],
    [[1, 2, -5, 40]] + series(6)[1:],                 # negative people
    [[1, 2, 10_000_001, 40]] + series(6)[1:],         # absurd people
    [[1, 2, 10, 100.5]] + series(6)[1:],              # score above 100
    [[1, 2, 10, -1]] + series(6)[1:],
])
def test_bad_series_are_rejected(rows):
    headers, _ = make_user("validator")
    response = client.post("/ghosts", json={"game": GAME, "scenario": "standard", "series": rows, "opt_in": True}, headers=headers)
    assert response.status_code == 422
    assert rows_in_db() == 0


def test_nan_and_infinity_are_rejected():
    headers, _ = make_user("nanny")
    for bad in ("NaN", "Infinity", "-Infinity"):
        body = '{"game": "continuum", "scenario": "standard", "opt_in": true, "series": [[1,2,10,%s],[2,2,10,40],[3,2,10,40],[4,2,10,40],[5,2,10,40]]}' % bad
        response = client.post("/ghosts", content=body, headers={**headers, "Content-Type": "application/json"})
        assert response.status_code == 422
    assert rows_in_db() == 0


def test_free_text_cannot_ride_along_in_a_row():
    headers, _ = make_user("texty")
    rows = series(6)
    rows[2] = [3, 2, 12, "my name is Sam"]
    assert publish(headers, rows=rows).status_code == 422
    assert rows_in_db() == 0


@pytest.mark.parametrize("scenario", ["", "Bad Scenario", "has/slash", "x" * 33, "<script>"])
def test_bad_scenario_is_rejected(scenario):
    headers, _ = make_user("scen")
    assert publish(headers, scenario=scenario).status_code == 422


def test_extra_fields_in_the_body_are_ignored_not_stored():
    headers, uid = make_user("extras")
    assert publish(headers, username="Sam", note="hello", save={"x": 1}).status_code == 200
    db = SessionLocal()
    row = db.query(GhostSeries).filter(GhostSeries.user_id == uid).one()
    stored = (row.id, row.game_id, row.scenario, row.hard, row.era, row.seasons, row.series_json)
    db.close()
    assert "Sam" not in repr(stored) and "hello" not in repr(stored)


def test_values_are_rounded_and_the_clean_rows_are_what_is_stored():
    headers, uid = make_user("rounder")
    rows = [[i + 1, 1, 10.4 + i, 33.333] for i in range(6)]
    body = publish(headers, rows=rows).json()
    assert body == {"accepted": True, "seasons": 6, "era": 1}
    db = SessionLocal()
    stored = db.query(GhostSeries).filter(GhostSeries.user_id == uid).one().series_json
    db.close()
    assert stored[0] == [1, 1, 10, 33.3]


# ---------------------------------------------------------------- one row per account, replace, delete

def test_republishing_replaces_the_row_instead_of_adding_one():
    headers, uid = make_user("replacer")
    assert publish(headers, rows=series(6, era=1)).status_code == 200
    assert publish(headers, rows=series(9, era=3), scenario="frontier", hard=True).json()["seasons"] == 9
    assert rows_in_db() == 1
    mine = client.get(f"/ghosts/{GAME}/mine", headers=headers).json()
    assert mine == {"published": True, "seasons": 9, "era": 3, "hidden": False}


def test_mine_before_publishing_and_after_deleting():
    headers, _ = make_user("minegone")
    assert client.get(f"/ghosts/{GAME}/mine", headers=headers).json() == {"published": False}
    assert client.get(f"/ghosts/{GAME}/mine").status_code == 401
    publish(headers)
    assert client.get(f"/ghosts/{GAME}/mine", headers=headers).json()["published"] is True
    assert client.delete(f"/ghosts/{GAME}", headers=headers).json() == {"removed": 1}
    assert client.get(f"/ghosts/{GAME}/mine", headers=headers).json() == {"published": False}
    assert client.delete(f"/ghosts/{GAME}", headers=headers).json() == {"removed": 0}
    assert rows_in_db() == 0


def test_delete_needs_an_account_and_only_touches_your_own_row():
    a, _ = make_user("dela")
    b, _ = make_user("delb")
    publish(a)
    publish(b)
    assert client.delete(f"/ghosts/{GAME}").status_code == 401
    assert client.delete(f"/ghosts/{GAME}", headers=a).json() == {"removed": 1}
    assert rows_in_db() == 1


def test_a_deleted_accounts_row_is_never_served_and_is_swept_on_the_next_publish():
    users = fill(4, prefix="orph")
    db = SessionLocal()
    victim_id = users[0][1]
    db.query(AuthSession).filter(AuthSession.user_id == victim_id).delete()
    db.query(User).filter(User.id == victim_id).delete()  # as account deletion does (no cascade on sqlite)
    db.commit()
    db.close()
    seen = set()
    for _ in range(12):
        ghosts.set_rng(random.Random(_))
        got = peer().json()["ghost"]
        if got:
            seen.add(got["id"])
    db = SessionLocal()
    assert db.query(GhostSeries).filter(GhostSeries.user_id == victim_id).count() == 1
    db.close()
    headers, _ = make_user("sweeper")
    publish(headers)
    db = SessionLocal()
    try:
        assert db.query(GhostSeries).filter(GhostSeries.user_id == victim_id).count() == 0
    finally:
        db.close()


# ---------------------------------------------------------------- reading: suppression, band, anonymity

def test_no_ghost_below_the_minimum_number_of_other_publishers():
    fill(ghosts.MIN_VISIBLE - 1)
    body = peer().json()
    assert body["ghost"] is None and body["reason"] == "too_few"


def test_a_ghost_appears_once_enough_others_have_published():
    fill(ghosts.MIN_VISIBLE)
    body = peer().json()
    assert body["reason"] is None and body["ghost"]["seasons"] == 8
    assert body["ghost"]["scenario"] == "standard"


def test_your_own_series_does_not_count_towards_the_minimum_and_is_never_returned():
    others = fill(ghosts.MIN_VISIBLE - 1)
    mine, my_id = make_user("self")
    publish(mine)
    assert peer(mine).json()["reason"] == "too_few"   # only MIN_VISIBLE - 1 *other* rows
    extra, _ = make_user("one-more")
    publish(extra)
    for i in range(30):
        ghosts.set_rng(random.Random(i))
        got = peer(mine).json()["ghost"]
        assert got is not None
        db = SessionLocal()
        row = db.query(GhostSeries).filter(GhostSeries.id == got["id"]).one()
        db.close()
        assert row.user_id != my_id


def test_a_signed_out_reader_gets_ghosts_too():
    fill(ghosts.MIN_VISIBLE)
    assert peer().json()["ghost"] is not None


def test_nothing_that_identifies_anyone_is_in_the_response():
    users = fill(ghosts.MIN_VISIBLE, prefix="whoami")
    body = peer().json()
    text = repr(body)
    for name in ("whoami0", "whoami1", "whoami2"):
        assert name not in text
    for _, uid in users:
        assert uid not in text
    assert set(body["ghost"]) == {"id", "scenario", "hard", "era", "seasons", "series"}
    assert "user" not in text and "created" not in text and "updated" not in text


def test_the_band_is_scenario_hard_flag_and_era_within_one():
    fill(2, prefix="a", era=2, scenario="standard")
    fill(1, prefix="b", era=6, scenario="standard")      # far era
    fill(1, prefix="c", era=2, scenario="frontier")      # other scenario
    fill(1, prefix="d", era=2, scenario="standard", hard=True)
    # 5 others in total, but only a0 and a1 are in the (standard, easy, era 2) band
    seen = set()
    for i in range(40):
        ghosts.set_rng(random.Random(i))
        got = peer(era=2).json()["ghost"]
        assert got is not None
        assert got["scenario"] == "standard" and got["hard"] is False and 1 <= got["era"] <= 3
        seen.add(got["id"])
    assert len(seen) == 2
    # era 3 still reaches era-2 ghosts; era 5 reaches only the era-6 one
    assert peer(era=3).json()["ghost"]["era"] == 2
    assert peer(era=5).json()["ghost"]["era"] == 6
    # hard band and other scenario each have exactly one
    assert peer(hard=True).json()["ghost"]["hard"] is True
    assert peer(scenario="frontier").json()["ghost"]["scenario"] == "frontier"


def test_an_empty_band_says_so_without_an_error():
    fill(ghosts.MIN_VISIBLE, era=2)
    body = peer(era=7).json()
    assert body["ghost"] is None and body["reason"] == "no_match"
    assert peer(scenario="river").json()["reason"] == "no_match"


def test_the_pick_is_random_but_deterministic_with_a_seeded_rng():
    fill(5)
    ghosts.set_rng(random.Random(123))
    first = [peer().json()["ghost"]["id"] for _ in range(6)]
    ghosts.set_rng(random.Random(123))
    again = [peer().json()["ghost"]["id"] for _ in range(6)]
    assert first == again
    assert len(set(first)) > 1


def test_exclude_avoids_repeating_the_same_ghost_when_there_is_another():
    fill(4)
    ghosts.set_rng(random.Random(1))
    for _ in range(25):
        first = peer().json()["ghost"]["id"]
        second = peer(exclude=first).json()["ghost"]["id"]
        assert second != first


def test_exclude_still_returns_the_only_match_rather_than_nothing():
    fill(ghosts.MIN_VISIBLE - 1)
    others = fill(1, prefix="solo", era=6)
    only = peer(era=6).json()["ghost"]
    again = peer(era=6, exclude=only["id"]).json()["ghost"]
    assert again["id"] == only["id"]


def test_hidden_and_test_account_rows_are_not_served_or_counted():
    users = fill(ghosts.MIN_VISIBLE)
    db = SessionLocal()
    db.query(GhostSeries).filter(GhostSeries.user_id == users[0][1]).update({"is_hidden": True})
    db.commit()
    db.close()
    assert peer().json()["reason"] == "too_few"
    db = SessionLocal()
    db.query(GhostSeries).filter(GhostSeries.user_id == users[0][1]).update({"is_hidden": False})
    db.query(User).filter(User.id == users[1][1]).update({"is_test": True})
    db.commit()
    db.close()
    assert peer().json()["reason"] == "too_few"


def test_peer_query_parameters_are_validated():
    fill(ghosts.MIN_VISIBLE)
    assert client.get(f"/ghosts/{GAME}/peer", params={"era": 99}).status_code == 422
    assert client.get(f"/ghosts/{GAME}/peer", params={"era": -1}).status_code == 422
    assert client.get(f"/ghosts/{GAME}/peer", params={"scenario": "Bad Scenario!"}).status_code == 422
    assert client.get(f"/ghosts/{GAME}/peer", params={"era": "x"}).status_code == 422
    # a junk exclude is simply ignored
    assert client.get(f"/ghosts/{GAME}/peer", params={"exclude": "';--"}).status_code == 200


def test_reads_are_not_cached():
    fill(ghosts.MIN_VISIBLE)
    assert peer().headers["cache-control"] == "no-store"


# ---------------------------------------------------------------- rate limits

def test_publish_is_rate_limited_per_account(fresh):
    headers, _ = make_user("flood")
    for _ in range(ghosts.PUBLISH_LIMIT_PER_HOUR):
        assert publish(headers).status_code == 200
    assert publish(headers).status_code == 429
    fresh["now"] += 3601
    assert publish(headers).status_code == 200


def test_probing_the_bounds_is_cut_off_sooner(fresh):
    headers, _ = make_user("prober")
    bad = [[1, 99, 10, 40]] + series(6)[1:]
    for _ in range(ghosts.REJECT_LIMIT_PER_15_MIN):
        assert publish(headers, rows=bad).status_code == 422
    assert publish(headers, rows=bad).status_code == 429
    assert publish(headers).status_code == 429          # even a good one waits out the 15 minutes
    fresh["now"] += 15 * 60 + 1
    assert publish(headers).status_code == 200


def test_reads_are_rate_limited_per_address(fresh):
    fill(ghosts.MIN_VISIBLE)
    for _ in range(ghosts.PEER_IP_LIMIT_PER_HOUR):
        assert peer().status_code == 200
    assert peer().status_code == 429
    fresh["now"] += 3601
    assert peer().status_code == 200


def test_reports_are_rate_limited_per_address(fresh):
    users = fill(1)
    ghost_id = peer_ids()[0]
    for i in range(ghosts.REPORT_IP_LIMIT_PER_HOUR):
        assert client.post("/ghosts/report", json={"game": GAME, "ghost_id": ghost_id}).status_code == 200
    assert client.post("/ghosts/report", json={"game": GAME, "ghost_id": ghost_id}).status_code == 429


# ---------------------------------------------------------------- reports and moderation

def peer_ids():
    db = SessionLocal()
    try:
        return [r.id for r in db.query(GhostSeries).order_by(GhostSeries.id).all()]
    finally:
        db.close()


def test_a_report_stores_a_row_with_no_reporter_details():
    fill(ghosts.MIN_VISIBLE)
    ghost = peer().json()["ghost"]
    response = client.post("/ghosts/report", json={"game": GAME, "ghost_id": ghost["id"], "reason": "implausible"})
    assert response.json() == {"reported": True, "counted": True}
    db = SessionLocal()
    try:
        report = db.query(GhostReport).one()
        assert (report.game_id, report.ghost_id, report.reason, report.is_resolved) == (GAME, ghost["id"], "implausible", False)
        assert {c.name for c in GhostReport.__table__.columns} == {"id", "game_id", "ghost_id", "reason", "is_resolved", "created_at"}
    finally:
        db.close()


def test_report_validates_reason_and_ghost():
    fill(ghosts.MIN_VISIBLE)
    ghost_id = peer_ids()[0]
    assert client.post("/ghosts/report", json={"game": GAME, "ghost_id": ghost_id, "reason": "free text here"}).status_code == 422
    assert client.post("/ghosts/report", json={"game": GAME, "ghost_id": "00000000-0000-0000-0000-000000000000"}).status_code == 404
    assert client.post("/ghosts/report", json={"game": GAME, "ghost_id": "bad id!"}).status_code == 404
    assert client.post("/ghosts/report", json={"game": "nope", "ghost_id": ghost_id}).status_code == 404
    db = SessionLocal()
    assert db.query(GhostReport).count() == 0
    db.close()


def test_the_same_address_reporting_twice_counts_once():
    fill(ghosts.MIN_VISIBLE)
    ghost_id = peer_ids()[0]
    first = client.post("/ghosts/report", json={"game": GAME, "ghost_id": ghost_id}).json()
    second = client.post("/ghosts/report", json={"game": GAME, "ghost_id": ghost_id}).json()
    assert first["counted"] is True and second == {"reported": True, "counted": False}
    db = SessionLocal()
    try:
        assert db.query(GhostReport).count() == 1
        assert db.query(GhostSeries).filter(GhostSeries.id == ghost_id).one().report_count == 1
    finally:
        db.close()


def test_enough_reports_from_different_addresses_hide_a_ghost_pending_review():
    fill(ghosts.MIN_VISIBLE + 1)
    ghost_id = peer_ids()[0]
    for i in range(ghosts.REPORT_HIDE_AT):
        r = client.post("/ghosts/report", json={"game": GAME, "ghost_id": ghost_id}, headers={"X-Forwarded-For": f"10.0.0.{i}"})
        assert r.json()["counted"] is True
    db = SessionLocal()
    row = db.query(GhostSeries).filter(GhostSeries.id == ghost_id).one()
    assert row.is_hidden is True
    db.close()
    for i in range(20):
        ghosts.set_rng(random.Random(i))
        assert peer().json()["ghost"]["id"] != ghost_id


def test_admin_lists_reports_and_can_hide_and_restore_a_ghost():
    fill(ghosts.MIN_VISIBLE + 1)
    ghost_id = peer_ids()[0]
    client.post("/ghosts/report", json={"game": GAME, "ghost_id": ghost_id, "reason": "offensive"})
    assert client.get("/admin/ghost-reports").status_code in (401, 403)
    listed = client.get("/admin/ghost-reports", headers=ADMIN).json()["reports"]
    assert len(listed) == 1 and listed[0]["reason"] == "offensive" and listed[0]["ghost"]["report_count"] == 1
    assert "user" not in repr(listed)
    assert client.put(f"/admin/ghosts/{ghost_id}/hidden", json={"hidden": True}).status_code in (401, 403)
    assert client.put(f"/admin/ghosts/{ghost_id}/hidden", json={"hidden": True}, headers=ADMIN).json()["is_hidden"] is True
    assert client.get(f"/ghosts/{GAME}/mine").status_code == 401
    assert client.put(f"/admin/ghosts/{ghost_id}/hidden", json={"hidden": False}, headers=ADMIN).json()["is_hidden"] is False
    assert client.post(f"/admin/ghost-reports/{listed[0]['id']}/resolve", headers=ADMIN).json()["is_resolved"] is True
    assert client.get("/admin/ghost-reports?resolved=false", headers=ADMIN).json()["reports"] == []
    assert client.put("/admin/ghosts/missing/hidden", json={"hidden": True}, headers=ADMIN).status_code == 404


def test_a_hidden_ghost_shows_as_hidden_to_its_owner_only():
    headers, uid = make_user("hiddenowner")
    publish(headers)
    db = SessionLocal()
    db.query(GhostSeries).filter(GhostSeries.user_id == uid).update({"is_hidden": True})
    db.commit()
    db.close()
    assert client.get(f"/ghosts/{GAME}/mine", headers=headers).json()["hidden"] is True


# ---------------------------------------------------------------- the registry

def test_register_ghost_game_validates_its_definition():
    for bad in (
        dict(game_id="Bad Game", min_seasons=1, max_seasons=2, max_era=1),
        dict(game_id="g", min_seasons=0, max_seasons=2, max_era=1),
        dict(game_id="g", min_seasons=5, max_seasons=2, max_era=1),
        dict(game_id="g", min_seasons=1, max_seasons=2000, max_era=1),
        dict(game_id="g", min_seasons=1, max_seasons=2, max_era=-1),
    ):
        with pytest.raises(ValueError):
            ghosts.register_ghost_game(**bad)


def test_the_table_is_new_and_has_one_row_per_account_and_game():
    columns = {c.name for c in GhostSeries.__table__.columns}
    assert columns == {"id", "game_id", "user_id", "scenario", "hard", "era", "seasons", "series_json",
                       "is_hidden", "report_count", "created_at", "updated_at"}
    names = {c.name for c in GhostSeries.__table__.constraints} | {i.name for i in GhostSeries.__table__.indexes}
    assert "uq_ghost_series_game_user" in names


# ---- the account export and deletion know about published ghosts ----

def test_the_account_export_lists_a_published_series_and_deletion_removes_it():
    import account_data
    headers, uid = make_user("export-me")
    assert publish(headers).status_code == 200
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == uid).first()
        export = account_data.build_export(db, user)
        assert [g["game_id"] for g in export["published_ghosts"]] == [GAME]
        assert export["published_ghosts"][0]["series"] == series()
        account_data.delete_account(db, user)
        assert db.query(GhostSeries).filter(GhostSeries.user_id == uid).count() == 0
    finally:
        db.close()
