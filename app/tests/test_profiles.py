"""Z-7 / Y-1: the profile data model, GET/PUT /users/me/profile and the public GET /profiles/{name}."""

import pytest
from fastapi.testclient import TestClient

from database import SessionLocal
from main import app
from models import User, UserProfile

client = TestClient(app)

SECRET_WORDS = ("password", "hash", "token", "email", "save_code", "bearer", "settings")


def _account(name):
    resp = client.post("/auth/signup", json={"username": name, "password": "hunter22"})
    if resp.status_code == 409:
        resp = client.post("/auth/login", json={"username": name, "password": "hunter22"})
    return {"Authorization": f"Bearer {resp.json()['bearer_token']}"}


def _progress(headers, game, seconds=0, achievements=None, streaks=None, **extra):
    body = {"progress": {"game": game, "add_seconds": seconds}, **extra}
    if achievements is not None:
        body["progress"]["achievements"] = achievements
    if streaks is not None:
        body["progress"]["streaks"] = streaks
    resp = client.put("/users/me/profile", json=body, headers=headers)
    assert resp.status_code == 200, resp.text
    return resp.json()


def test_profile_is_off_by_default_and_empty():
    headers = _account("pf-new")
    mine = client.get("/users/me/profile", headers=headers).json()
    assert mine["is_public"] is False
    assert mine["games"] == [] and mine["badges"] == [] and mine["total_seconds"] == 0
    assert mine["favourite_game"] is None and mine["member_since"]
    assert client.get("/profiles/pf-new").status_code == 404


def test_requires_sign_in():
    assert client.get("/users/me/profile").status_code == 401
    assert client.put("/users/me/profile", json={"is_public": True}).status_code == 401
    assert client.put("/users/me/profile", json={"is_public": True}, headers={"Authorization": "Bearer junk"}).status_code == 401


def test_the_switch_controls_the_public_page_and_it_answers_404_the_same_way():
    headers = _account("pf-switch")
    unknown = client.get("/profiles/pf-nobody-here")
    hidden = client.get("/profiles/pf-switch")
    assert unknown.status_code == hidden.status_code == 404
    assert unknown.json() == hidden.json()          # never says whether the account exists

    assert client.put("/users/me/profile", json={"is_public": True}, headers=headers).json()["is_public"] is True
    shown = client.get("/profiles/pf-switch")
    assert shown.status_code == 200 and shown.json()["username"] == "pf-switch"
    assert client.get("/profiles/PF-SWITCH ").status_code == 200        # same normalising as login
    assert shown.headers["cache-control"] == "no-store"

    client.put("/users/me/profile", json={"is_public": False}, headers=headers)
    assert client.get("/profiles/pf-switch").status_code == 404


def test_is_public_must_be_a_real_boolean():
    headers = _account("pf-strict")
    for bad in ("yes", 1, "true", []):
        assert client.put("/users/me/profile", json={"is_public": bad}, headers=headers).status_code == 422
    assert client.get("/users/me/profile", headers=headers).json()["is_public"] is False


def test_public_view_never_contains_secrets_or_other_accounts_data():
    headers = _account("pf-secret")
    db = SessionLocal()
    user = db.query(User).filter(User.username == "pf-secret").first()
    user.email = "private@example.test"
    db.commit()
    db.close()
    client.put("/users/me/saves/pfgame/slots/1", json={"save_data": {"achievements_earned": ["a"], "secretvalue": "zzz"}}, headers=headers)
    client.put("/users/me/settings", json={"theme": "light"}, headers=headers)
    _progress(headers, "pfgame", 600, 3, is_public=True)
    text = client.get("/profiles/pf-secret").text.lower()
    for word in SECRET_WORDS + ("private@example.test", "secretvalue", "zzz"):
        assert word not in text, word
    assert set(client.get("/profiles/pf-secret").json()) == {
        "username", "member_since", "favourite_game", "favourite_is_most_played", "games", "total_seconds",
        "total_achievements", "games_played", "streaks", "badges",
    }
    assert "id" not in client.get("/profiles/pf-secret").json()


def test_seconds_add_up_and_achievements_keep_the_higher_count():
    headers = _account("pf-sum")
    _progress(headers, "canopy", 120, 2)
    _progress(headers, "canopy", 300, 5)
    after = _progress(headers, "canopy", 60, 1)           # a lower count (a new game) never lowers it
    _progress(headers, "grid", 3600, 4)
    mine = client.get("/users/me/profile", headers=headers).json()
    by_game = {g["game"]: g for g in mine["games"]}
    assert by_game["canopy"] == {"game": "canopy", "seconds": 480, "achievements": 5}
    assert by_game["grid"] == {"game": "grid", "seconds": 3600, "achievements": 4}
    assert mine["total_seconds"] == 4080 and mine["total_achievements"] == 9 and mine["games_played"] == 2
    assert after["total_achievements"] == 5
    assert [g["game"] for g in mine["games"]] == ["canopy", "grid"]          # most achievements first


def test_update_without_seconds_or_count_leaves_them_alone():
    headers = _account("pf-partial")
    _progress(headers, "sol", 100, 7)
    client.put("/users/me/profile", json={"progress": {"game": "sol"}}, headers=headers)
    game = client.get("/users/me/profile", headers=headers).json()["games"][0]
    assert game["seconds"] == 100 and game["achievements"] == 7


@pytest.mark.parametrize("progress", [
    {"game": "Bad Slug"}, {"game": ""}, {"game": "../x"}, {"game": "g" * 65},
    {"game": "ok", "add_seconds": -1}, {"game": "ok", "add_seconds": 4 * 3600 + 1}, {"game": "ok", "add_seconds": "9"},
    {"game": "ok", "achievements": -1}, {"game": "ok", "achievements": 1001},
    {"game": "ok", "streaks": {"Bad Label": 3}}, {"game": "ok", "streaks": {"a": -1}}, {"game": "ok", "streaks": {"a": True}},
    {"game": "ok", "streaks": {"a": 1.5}}, {"game": "ok", "streaks": {f"s{i}": 1 for i in range(11)}},
    {},
])
def test_invalid_progress_is_refused(progress, request):
    headers = _account("pf-invalid-" + request.node.name.split("[")[-1].rstrip("]"))
    assert client.put("/users/me/profile", json={"progress": progress}, headers=headers).status_code == 422
    assert client.get("/users/me/profile", headers=headers).json()["games"] == []


def test_streaks_keep_the_longest_and_are_listed_by_game():
    headers = _account("pf-streak")
    _progress(headers, "signal", 10, streaks={"daily": 9})
    _progress(headers, "signal", 10, streaks={"daily": 4, "perfect": 2})
    _progress(headers, "canopy", 10, streaks={"daily": 12})
    streaks = client.get("/users/me/profile", headers=headers).json()["streaks"]
    assert streaks == [
        {"game": "canopy", "label": "daily", "value": 12},
        {"game": "signal", "label": "daily", "value": 9},
        {"game": "signal", "label": "perfect", "value": 2},
    ]


def test_favourite_game_set_cleared_and_defaulting_to_the_most_played():
    headers = _account("pf-fav")
    assert client.get("/users/me/profile", headers=headers).json()["favourite_game"] is None
    _progress(headers, "tide", 100)
    _progress(headers, "herd", 900)
    mine = client.get("/users/me/profile", headers=headers).json()
    assert mine["favourite_game"] == "herd" and mine["favourite_is_most_played"] is True and mine["favourite_game_choice"] is None
    chosen = client.put("/users/me/profile", json={"favourite_game": "tide"}, headers=headers).json()
    assert chosen["favourite_game"] == "tide" and chosen["favourite_is_most_played"] is False
    assert client.put("/users/me/profile", json={"favourite_game": "Not A Slug"}, headers=headers).status_code == 422
    cleared = client.put("/users/me/profile", json={"favourite_game": None}, headers=headers).json()
    assert cleared["favourite_game"] == "herd"
    # a PUT that does not mention it leaves a choice alone
    client.put("/users/me/profile", json={"favourite_game": "tide"}, headers=headers)
    client.put("/users/me/profile", json={"is_public": True}, headers=headers)
    assert client.get("/users/me/profile", headers=headers).json()["favourite_game"] == "tide"


def test_badges_are_computed_from_the_numbers_and_events_use_ids_only():
    headers = _account("pf-badges")
    out = _progress(headers, "a1", 3600, 1)
    ids = {b["id"] for b in out["badges"]}
    assert ids == {"first-steps", "time-1h"}
    for slug in ("a2", "a3"):
        out = _progress(headers, slug, 10, 10)
    ids = {b["id"] for b in out["badges"]}
    assert {"achiever-10", "explorer-3"} <= ids and "achiever-50" not in ids
    out = client.put("/users/me/profile", json={"event_badges": ["halloween-2026", "Bad Id!", "x" * 80, "new-year-2027"]}, headers=headers).json()
    events = {b["id"]: b["label"] for b in out["badges"] if b["kind"] == "event"}
    assert events == {"halloween-2026": "Halloween 2026", "new-year-2027": "New Year 2027"}
    # labels come from the id, so a client cannot put wording of its own on a public page
    again = client.put("/users/me/profile", json={"event_badges": ["halloween-2026"], "progress": {"game": "a1"}}, headers=headers).json()
    assert sum(1 for b in again["badges"] if b["kind"] == "event") == 2


def test_streak_badges():
    headers = _account("pf-streakbadge")
    out = _progress(headers, "signal", 5, streaks={"daily": 7})
    assert "streak-7" in {b["id"] for b in out["badges"]} and "streak-30" not in {b["id"] for b in out["badges"]}
    out = _progress(headers, "signal", 5, streaks={"daily": 31})
    assert {"streak-7", "streak-30"} <= {b["id"] for b in out["badges"]}


def test_a_profile_cannot_grow_without_bound():
    headers = _account("pf-bounds")
    for i in range(70):
        client.put("/users/me/profile", json={"progress": {"game": f"g{i}", "add_seconds": 1}}, headers=headers)
    assert len(client.get("/users/me/profile", headers=headers).json()["games"]) == 60
    for i in range(50):
        client.put("/users/me/profile", json={"progress": {"game": "g1", "streaks": {f"s{i}": 1}}}, headers=headers)
    db = SessionLocal()
    row = db.query(UserProfile).join(User, User.id == UserProfile.user_id).filter(User.username == "pf-bounds").first()
    assert len(row.streaks_json) <= 40
    db.close()


def test_progress_posts_are_rate_limited_per_account(monkeypatch):
    import main
    monkeypatch.setattr(main, "PROFILE_UPDATE_LIMITER", main.FailureLimiter(max_failures=3, window_seconds=3600))
    headers = _account("pf-limited")
    codes = [client.put("/users/me/profile", json={"progress": {"game": "sol", "add_seconds": 1}}, headers=headers).status_code for _ in range(5)]
    assert codes == [200, 200, 200, 429, 429]
    # the switch is not a progress post, so it still works
    assert client.put("/users/me/profile", json={"is_public": True}, headers=headers).status_code == 200


def test_public_lookups_are_rate_limited_per_address(monkeypatch):
    import main
    monkeypatch.setattr(main, "PROFILE_LOOKUP_LIMITER", main.FailureLimiter(max_failures=2, window_seconds=3600))
    assert [client.get("/profiles/pf-whoever").status_code for _ in range(4)] == [404, 404, 429, 429]


def test_accounts_do_not_see_or_change_each_other():
    a, b = _account("pf-a"), _account("pf-b")
    _progress(a, "sol", 500, 3, is_public=True)
    assert client.get("/users/me/profile", headers=b).json()["games"] == []
    assert client.get("/profiles/pf-b").status_code == 404
    assert client.get("/profiles/pf-a").json()["total_achievements"] == 3


def test_a_corrupt_stored_row_is_cleaned_on_the_way_out():
    headers = _account("pf-corrupt")
    db = SessionLocal()
    user = db.query(User).filter(User.username == "pf-corrupt").first()
    db.add(UserProfile(user_id=user.id, is_public=True, games_json={"ok": {"seconds": 5, "achievements": 1}, "Bad Slug": {"seconds": 99}, "x": "junk"},
                       streaks_json={"ok:daily": 3, "nocolon": 5, "ok:bool": True}, event_badges_json=["fine-2026", "Bad Id", 5]))
    db.commit()
    db.close()
    body = client.get("/profiles/pf-corrupt").json()
    assert [g["game"] for g in body["games"]] == ["ok"]
    assert body["streaks"] == [{"game": "ok", "label": "daily", "value": 3}]
    assert [b["id"] for b in body["badges"] if b["kind"] == "event"] == ["fine-2026"]


# ---- GN-7: backfill from existing saves ----

def _save_for(headers, game, data):
    resp = client.post("/saves", json={"game_id": game, "save_data": data})
    assert resp.status_code in (200, 201), resp.text
    code = resp.json()["save_code"]
    claim = client.post(f"/saves/{code}/claim", headers=headers)
    assert claim.status_code == 200, claim.text
    return code


def test_backfill_raises_counts_from_the_best_save_per_game_and_never_lowers():
    headers = _account("pf-backfill")
    _save_for(headers, "canopy", {"achievements_earned": ["a", "b", "c", "a"]})      # 3 distinct
    _save_for(headers, "canopy", {"achievements_earned": ["a"]})
    _save_for(headers, "sol", {"achievements_earned": ["x", "y"]})
    _save_for(headers, "tide", {"achievements_earned": []})                         # nothing to add
    _progress(headers, "sol", seconds=120, achievements=5)                           # already higher: stays 5
    resp = client.post("/users/me/profile/backfill", headers=headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["updated"] == [{"game": "canopy", "achievements": 3}]
    games = {g["game"]: g for g in body["profile"]["games"]}
    assert games["canopy"]["achievements"] == 3 and games["sol"]["achievements"] == 5
    assert games["sol"]["seconds"] == 120 and "tide" not in games
    again = client.post("/users/me/profile/backfill", headers=headers).json()
    assert again["updated"] == []


def test_backfill_merges_seasonal_badges_by_id_only_and_ignores_junk():
    headers = _account("pf-backfill-badges")
    _save_for(headers, "aftermath", {"achievements_earned": ["q"], "event_badges": [
        {"id": "halloween-2026", "label": "Anything the client says"}, {"id": "BAD ID"}, "new-year-2027", 7, None]})
    body = client.post("/users/me/profile/backfill", headers=headers).json()
    ids = {b["id"] for b in body["profile"]["badges"] if b["kind"] == "event"}
    assert ids == {"halloween-2026", "new-year-2027"}
    labels = {b["label"] for b in body["profile"]["badges"] if b["kind"] == "event"}
    assert "Anything the client says" not in labels


def test_backfill_needs_sign_in_and_only_reads_the_callers_saves():
    assert client.post("/users/me/profile/backfill").status_code == 401
    other = _account("pf-backfill-other")
    _save_for(other, "canopy", {"achievements_earned": ["a", "b"]})
    mine = _account("pf-backfill-mine")
    assert client.post("/users/me/profile/backfill", headers=mine).json()["updated"] == []


def test_backfill_is_rate_limited_like_other_profile_writes(monkeypatch):
    import main
    headers = _account("pf-backfill-limit")
    monkeypatch.setattr(main, "PROFILE_UPDATE_LIMITER", main.FailureLimiter(max_failures=1, window_seconds=3600))
    assert client.post("/users/me/profile/backfill", headers=headers).status_code == 200
    assert client.post("/users/me/profile/backfill", headers=headers).status_code == 429
