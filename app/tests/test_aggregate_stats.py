"""Cross-game aggregate stats (TODO.md Z1). In-memory sqlite, shared across
the pytest session — so tests use a whitelisted game id but wipe that game's
saves first (and clear the in-process cache) for exact assertions."""

import pytest
from fastapi.testclient import TestClient

import stats
from database import SessionLocal
from main import app
from models import Save

client = TestClient(app)


@pytest.fixture(autouse=True)
def _clean():
    def wipe():
        db = SessionLocal()
        db.query(Save).filter(Save.game_id.in_(["grid", "herd", "thaw", "tide"])).delete(synchronize_session=False)
        db.commit()
        db.close()
        stats.cache_clear()

    wipe()
    yield
    wipe()


def _seed(game, blobs):
    db = SessionLocal()
    for i, b in enumerate(blobs):
        db.add(Save(save_code=f"T{game}{i}{id(b)}", game_id=game, save_data=b))
    db.commit()
    db.close()
    stats.cache_clear()


# --- pure helpers ---

def test_percentile_of_edges():
    v = [1.0, 2.0, 3.0, 4.0]
    assert stats.percentile_of(v, -100) == 0.0
    assert stats.percentile_of(v, 100) == 100.0
    assert stats.percentile_of([5.0, 5.0, 5.0], 5) == 50.0
    assert stats.percentile_of(v, 2.5) == 50.0
    with pytest.raises(ValueError):
        stats.percentile_of([], 1)


def test_extract_number_rejects_non_numbers():
    d = {"a": 1, "b": True, "c": "3", "d": None, "e": float("nan"), "f": {"g": 2.5}, "h": [1]}
    assert stats.extract_number(d, "a") == 1.0
    for bad in ("b", "c", "d", "e", "h", "missing", "a.b", "f.x"):
        assert stats.extract_number(d, bad) is None
    assert stats.extract_number(d, "f.g") == 2.5
    assert stats.extract_number("not a dict", "a") is None


def test_extract_achievements_tolerates_junk():
    assert stats.extract_achievements({"achievements_earned": ["ok_1", 5, None, "Bad Id", "x" * 100, ["n"]]}) == {"ok_1"}
    assert stats.extract_achievements({"achievements_earned": "nope"}) == set()
    assert stats.extract_achievements([1, 2]) == set()


# --- endpoints ---

def test_unknown_game_404():
    assert client.get("/stats/games/nope").status_code == 404
    assert client.get("/stats/games/nope/percentile?field=x&value=1").status_code == 404


def test_game_below_min_bucket_is_fully_suppressed():
    _seed("grid", [{"round_number": 5, "achievements_earned": ["a"]}, {"round_number": 9}])
    body = client.get("/stats/games/grid").json()
    assert body["suppressed"] is True
    assert body["save_count"] is None
    assert body["fields"] == {} and body["achievements"] == {}


def test_empty_game_is_suppressed_not_an_error():
    assert client.get("/stats/games/tide").json()["suppressed"] is True


def test_aggregates_and_small_achievement_bucket_suppression():
    blobs = [
        {"round_number": r, "achievements_earned": ["common"] + (["rare"] if r == 1 else [])}
        for r in (1, 2, 3, 4)
    ]
    _seed("grid", blobs)
    resp = client.get("/stats/games/grid")
    assert "public" in resp.headers["cache-control"]
    body = resp.json()
    assert body["save_count"] == 4
    assert body["achievements"]["common"]["earned_pct"] == 100.0
    assert "rare" not in body["achievements"]  # earned by 1 save < 3
    assert body["achievements_suppressed_count"] == 1
    f = body["fields"]["round_number"]
    assert f["count"] == 4 and f["mean"] == 2.5
    assert f["percentiles"]["p50"] == 2.5
    assert "min" not in f and "max" not in f
    # only whitelisted fields appear
    assert set(body["fields"]) <= set(stats.STATS_FIELDS["grid"])


def test_malformed_saves_are_tolerated():
    _seed("grid", [
        {"round_number": "x", "achievements_earned": "no"},
        {"round_number": 1e308, "achievements_earned": [1, {}]},
        {"round_number": None},
        {"round_number": True},
        {},
        {"round_number": 4}, {"round_number": 6}, {"round_number": 8},
    ])
    body = client.get("/stats/games/grid").json()
    assert body["save_count"] == 8
    assert body["fields"]["round_number"]["count"] == 4  # 1e308, 4, 6, 8
    assert body["achievements"] == {}


def test_nested_path_field():
    _seed("thaw", [{"region": {"temperature": t}} for t in (1, 2, 3)] + [{"region": "bad"}])
    body = client.get("/stats/games/thaw").json()
    assert body["fields"]["region.temperature"]["count"] == 3


def test_no_identifying_data_leaks():
    _seed("herd", [{"funds": 1, "player_name": "SECRET-NAME", "achievements_earned": ["ok"]}] * 3)
    for url in ("/stats/games/herd", "/stats/achievements", "/stats/games"):
        text = client.get(url).text
        assert "SECRET-NAME" not in text


def test_percentile_endpoint():
    _seed("grid", [{"round_number": r} for r in (10, 20, 30, 40)])
    ok = client.get("/stats/games/grid/percentile?field=round_number&value=25").json()
    assert ok["percentile"] == 50.0 and ok["count"] == 4 and ok["suppressed"] is False
    assert client.get("/stats/games/grid/percentile?field=round_number&value=-5").json()["percentile"] == 0.0
    assert client.get("/stats/games/grid/percentile?field=round_number&value=999").json()["percentile"] == 100.0


def test_percentile_validation_and_suppression():
    _seed("grid", [{"round_number": 1}, {"round_number": 2}])
    body = client.get("/stats/games/grid/percentile?field=round_number&value=1").json()
    assert body["suppressed"] is True and body["percentile"] is None
    assert client.get("/stats/games/grid/percentile?field=not_whitelisted&value=1").status_code == 404
    assert client.get("/stats/games/grid/percentile?field=round_number&value=abc").status_code == 422
    assert client.get("/stats/games/grid/percentile?field=round_number&value=nan").status_code == 422
    assert client.get("/stats/games/grid/percentile?field=round_number&value=inf").status_code == 422
    assert client.get("/stats/games/grid/percentile?field=round_number").status_code == 422


def test_achievements_rollup_and_games_listing_and_cors():
    _seed("herd", [{"achievements_earned": ["a"]}] * 3 + [{}])
    body = client.get("/stats/achievements").json()
    assert body["games"]["herd"]["achievements"]["a"]["earned_pct"] == 75.0
    assert body["games"]["grid"]["suppressed"] is True
    assert set(body["games"]) == set(stats.STATS_FIELDS)
    listing = client.get("/stats/games").json()
    assert "round_number" in listing["games"]["grid"]
    r = client.get("/stats/games/herd", headers={"Origin": "https://noyvj.github.io"})
    assert r.headers["access-control-allow-origin"] == "https://noyvj.github.io"


def test_cache_serves_repeat_reads_until_cleared():
    _seed("grid", [{"round_number": 1}] * 3)
    assert client.get("/stats/games/grid").json()["save_count"] == 3
    db = SessionLocal()
    db.add(Save(save_code="CACHEX", game_id="grid", save_data={}))
    db.commit(); db.close()
    assert client.get("/stats/games/grid").json()["save_count"] == 3  # cached
    stats.cache_clear()
    assert client.get("/stats/games/grid").json()["save_count"] == 4
