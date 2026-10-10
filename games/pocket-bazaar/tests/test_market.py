"""The Daily Market (M-4b-9): one deterministic, fairness-proven market day per UTC date, from the date text alone, that
pays nothing extra and keeps no streak. The pledge checks for it live in test_market_pledge.py."""

import datetime
import json
import re
from pathlib import Path

import pytest

import game
import market
import marketbot
from .bot import call, step

GAME_DIR = Path(__file__).resolve().parent.parent
TODAY = "2026-10-11"


@pytest.fixture(autouse=True)
def fresh():
    game.stall.__init__()
    game._today = None
    market._cache.clear()
    yield
    game.stall.__init__()
    game._today = None


def dates(n, start=market.EPOCH):
    out = []
    for i in range(n):
        out.append(market.add_days(start, i))
    return out


# --- the calendar is plain arithmetic, and agrees with the real one -----------------------------------------------
def test_the_arithmetic_calendar_agrees_with_datetime_over_ten_years():
    d0 = datetime.date(2026, 10, 1)
    for i in range(0, 3700, 3):
        text = (d0 + datetime.timedelta(days=i)).isoformat()
        assert market.add_days(market.EPOCH, i) == text and market.day_number(text) == i + 1
    assert market.add_days("2028-02-28", 1) == "2028-02-29" and market.add_days("2100-02-28", 1) == "2100-03-01"


def test_dates_are_strict_and_the_playable_range_is_epoch_to_today():
    for bad in ("2026-02-30", "2026-13-01", "2026-1-01", "20261001", "2026-10-01x", "", None, 5, "２０２６-10-01", "2026/10/01"):
        assert not market.valid_date(bad), bad
    assert market.valid_date("2028-02-29") and not market.valid_date("2027-02-29")
    assert market.playable(market.EPOCH, TODAY) and market.playable(TODAY, TODAY)
    assert not market.playable("2026-09-30", TODAY) and not market.playable("2026-10-12", TODAY) and not market.playable("x", TODAY)


def test_the_market_modules_never_touch_a_clock_or_a_date_library():
    for name in ("market.py", "marketbot.py"):
        text = (GAME_DIR / name).read_text(encoding="utf-8")
        assert not re.search(r"\b(import|from)\s+(time|datetime|calendar|random)\b", text), name
        assert not re.search(r"\b(time|datetime)\.(time|now|today|sleep)\b", text), name
    with pytest.raises(ValueError):
        market.spec("not a date")


# --- determinism ---------------------------------------------------------------------------------------------------
def test_a_date_gives_the_same_market_every_time_and_in_any_order():
    first = {d: json.dumps(market.spec(d), sort_keys=True) for d in dates(30)}
    market._cache.clear()
    for d in reversed(dates(30)):
        assert json.dumps(market.spec(d), sort_keys=True) == first[d]
    market._cache.clear()
    a, b = market.new_day("2026-10-09"), market.new_day("2026-10-09")
    assert a.to_dict() == b.to_dict()


def test_different_dates_are_different_markets_and_every_festival_comes_up():
    specs = [market.spec(d) for d in dates(300)]
    assert {s["festival"] for s in specs} == set(__import__("festival").ORDER)
    queues = {json.dumps(market.new_day(d).to_dict()["queue"]) for d in dates(60)}
    assert len(queues) == 60
    assert {len(s["families"]) for s in specs} == {3, 4}


# --- the fairness bar --------------------------------------------------------------------------------------------------
def test_every_market_for_300_days_has_reachable_orders_and_a_greedy_player_serves_enough():
    for d in dates(300):
        s = market.spec(d)
        day = market.new_day(d)
        assert day.total == s["customers"] and day.number == market.day_number(d)
        assert all(__import__("orders").order_is_reachable(c, day.board) for c in day.queue), d
        marketbot.play(day, s["families"])
        assert day.served * 100 // day.total >= market.MIN_SERVED_PCT and day.served * 100 // day.total == s["bot_pct"], d
        assert day.summary()["stars"] >= 2, d


def test_every_family_a_market_uses_is_open_to_it_and_nothing_else():
    for d in dates(120):
        s = market.spec(d)
        day = market.new_day(d)
        allowed = set(s["families"])
        assert all(f in allowed for c in day.queue for f, _t, _x in c.items), d
        assert not any(c.reg for c in day.queue)                      # no named regulars in a market
        assert not day.board.has_shelf and day.board.width == 5


def test_a_candidate_that_fails_the_bar_is_replaced_not_served(monkeypatch):
    real = market._fair
    calls = []

    def stingy(spec, day):
        calls.append(spec["attempt"])
        return None if len(calls) < 3 else real(spec, day)

    monkeypatch.setattr(market, "_fair", stingy)
    s = market.spec("2027-01-02")
    assert s["attempt"] == 2 and calls == [0, 1, 2]


def test_the_engine_bot_and_the_view_bot_play_a_market_the_same_way():
    """marketbot.py (used for the bar) mirrors tests/bot.py (which reads the view); both must reach the same end."""
    for d in ("2026-10-02", "2026-10-09", "2026-10-17", "2026-11-03"):
        view = call(action="start_market", date=d, today="2027-01-01")
        assert view["phase"] == "open"
        steps = 0
        while view["phase"] == "open":
            view = step(view)
            steps += 1
            assert steps < 3000
        result = view["market"]["result"]
        s = market.spec(d)
        assert result["served"] * 100 // result["total"] == s["bot_pct"], d
        assert result["date"] == d


# --- the game flow ---------------------------------------------------------------------------------------------------------
def test_the_closed_stall_offers_the_market_only_when_the_view_passes_the_date():
    assert call(action="open")["market"] is None
    m = call(action="open", today=TODAY)["market"]
    assert m["open"] and m["number"] == 11 and m["tally"] == {"open": 11, "played": 0, "perfect": 0}
    assert m["record"] is None and m["days"] == {} and m["result"] is None and m["active"] is None
    early = call(action="open", today="2026-09-01")["market"]
    assert early["open"] is False and early["festival"] is None


def test_start_market_checks_the_date_and_the_state_of_the_stall():
    for date, word in (("2026-10-12", "not open"), ("2026-09-30", "no market"), ("garbage", "no market"), (None, "no market")):
        v = call(action="start_market", date=date, today=TODAY)
        assert v["ok"] is False and word in v["message"] and v["phase"] == "closed"
    game._today = None
    assert "not known" in call(action="start_market", date="2026-10-05")["message"]
    call(action="start_day", today=TODAY)
    v = call(action="start_market", date="2026-10-05", today=TODAY)
    assert v["ok"] is False and "Finish the open day" in v["message"] and game.stall.market is None


def test_a_market_changes_nothing_but_the_dates_own_record():
    call(action="open", today=TODAY)
    before = json.dumps({k: v for k, v in game.get_state().items() if k != "market_days"}, sort_keys=True)
    view = call(action="start_market", date="2026-10-05", today=TODAY)
    assert view["phase"] == "open" and view["market"]["active"] == "2026-10-05"
    assert len(view["crates"]) in (3, 4) and view["upcoming"] is None
    steps = 0
    while view["phase"] == "open":
        view = step(view)
        steps += 1
        assert steps < 3000
    assert view["coins"] == 0 and view["tally"] == {k: 0 for k in game.TALLY_KEYS} and view["renown"] == 0
    assert view["days_played"] == 0 and view["next_day"] == 1 and view["summary"] is None
    after = game.get_state()
    assert json.dumps({k: v for k, v in after.items() if k != "market_days"}, sort_keys=True) == before
    assert set(after["market_days"]) == {"2026-10-05"}
    result = view["market"]["result"]
    assert result["improved"] is True and 1 <= result["stars"] <= 3 and view["market"]["tally"]["played"] == 1


def test_selling_in_a_market_pays_nothing_and_says_so():
    call(action="start_market", date="2026-10-05", today=TODAY)
    call(action="crate", family="produce")
    v = call(action="sell", at=0)
    assert v["ok"] and "coin" not in v["message"] and v["coins"] == 0


def test_a_replay_keeps_the_best_result_and_the_archive_stays_open():
    call(action="open", today=TODAY)
    play_market("2026-10-05")
    best = dict(game.stall.market_days["2026-10-05"])
    # a worse replay (do nothing but sell until nobody is left) never lowers the record
    call(action="start_market", date="2026-10-05", today=TODAY)
    day = game.stall.day
    day.queue, day.total, day.left, day.served = [], 3, 3, 0
    game.stall.close_market()
    assert game.stall.market_days["2026-10-05"] == best
    assert game.stall.market_result["improved"] is False
    play_market("2026-10-01")
    assert set(game.stall.market_days) == {"2026-10-05", "2026-10-01"}


def play_market(date):
    view = call(action="start_market", date=date, today=TODAY)
    while view["phase"] == "open":
        view = step(view)
    return view


def test_a_market_cannot_be_started_over_the_open_one_and_resuming_is_a_no_op():
    call(action="start_market", date="2026-10-05", today=TODAY)
    call(action="crate", family="produce")
    snapshot = json.dumps(game.get_state(), sort_keys=True)
    again = call(action="start_market", date="2026-10-05", today=TODAY)
    assert again["phase"] == "open" and json.dumps(game.get_state(), sort_keys=True) == snapshot
    other = call(action="start_market", date="2026-10-06", today=TODAY)
    assert other["ok"] is False and game.stall.market == "2026-10-05"
    assert call(action="start_day", today=TODAY)["ok"] is False


def test_start_over_keeps_the_market_results_because_they_belong_to_dates():
    call(action="open", today=TODAY)
    play_market("2026-10-04")
    v = call(action="reset", today=TODAY)
    assert v["market"]["tally"]["played"] == 1 and v["coins"] == 0


# --- saves ---------------------------------------------------------------------------------------------------------------------
def test_old_saves_load_unchanged_and_a_fresh_save_has_no_market_keys():
    assert not any(k.startswith("market") for k in game.get_state())
    game.load_state({"coins": 40, "next_day": 3, "days_played": 2, "renown": 6})
    assert game.stall.coins == 40 and game.stall.market_days == {} and game.stall.market is None
    assert not any(k.startswith("market") for k in game.get_state())


def test_a_market_in_progress_survives_a_save_and_load_exactly():
    call(action="start_market", date="2026-10-08", today=TODAY)
    for _ in range(6):
        call(action="crate", family="produce")
    state = json.loads(json.dumps(game.get_state()))
    assert "market_day" in state and "day" not in state and state["market_day"]["date"] == "2026-10-08"
    game.stall.__init__()
    game.load_state(state)
    assert game.stall.market == "2026-10-08" and game.stall.day is not None
    assert json.dumps(game.get_state(), sort_keys=True) == json.dumps(state, sort_keys=True)
    assert call(action="open", today=TODAY)["market"]["active"] == "2026-10-08"


def test_a_tampered_market_save_is_dropped_field_by_field():
    good = {"market_days": {"2026-10-05": {"stars": 2, "served": 5, "total": 8, "coins": 60},
                            "2026-10-06": {"stars": 9, "served": 5, "total": 8, "coins": 60},
                            "2026-10-07": {"stars": 2, "served": 9, "total": 8, "coins": 60},
                            "2026-09-01": {"stars": 2, "served": 5, "total": 8, "coins": 60},
                            "nope": {"stars": 1, "served": 1, "total": 1, "coins": 1},
                            "2026-10-08": {"stars": True, "served": 5, "total": 8, "coins": 60},
                            "2026-10-09": [1], 5: {}}}
    game.load_state(good)
    assert game.stall.market_days == {"2026-10-05": {"stars": 2, "served": 5, "total": 8, "coins": 60}}
    for junk in (None, [], "x", {"date": "2026-10-05"}, {"date": "2020-01-01", "day": {}}, {"date": 5, "day": {}},
                 {"date": "2026-10-05", "day": {"number": 99, "board": {}, "queue": [], "total": 1}}):
        game.load_state({"market_day": junk})
        assert game.stall.market is None and game.stall.day is None
    game.load_state({"market_days": "junk", "coins": 5})
    assert game.stall.market_days == {} and game.stall.coins == 5


def test_a_campaign_day_wins_over_a_market_day_if_a_save_holds_both():
    call(action="start_day", today=TODAY)
    state = json.loads(json.dumps(game.get_state()))
    game.stall.__init__()
    market_state = json.loads(json.dumps(_market_state()))
    state["market_day"] = market_state["market_day"]
    game.load_state(state)
    assert game.stall.market is None and game.stall.day is not None and game.stall.day.number == 1


def _market_state():
    game.stall.__init__()
    call(action="start_market", date="2026-10-08", today=TODAY)
    out = game.get_state()
    game.stall.__init__()
    return out


def test_the_market_leaderboard_hook_only_shapes_an_entry():
    entry = market.leaderboard_entry("2026-10-05", {"stars": 3, "served": 8, "total": 8, "coins": 120})
    assert entry == {"board": "pocket-bazaar-market", "date": "2026-10-05", "score": 120, "stars": 3, "served": 8}
    call(action="open", today=TODAY)
    view = play_market("2026-10-05")
    assert view["market"]["entry"]["board"] == "pocket-bazaar-market"


def test_merge_record_prefers_stars_then_served_then_coins():
    a = {"stars": 2, "served": 6, "total": 8, "coins": 90}
    assert market.merge_record(a, {"stars": 3, "served": 8, "total": 8, "coins": 50})["stars"] == 3
    assert market.merge_record(a, {"stars": 2, "served": 7, "total": 8, "coins": 10})["served"] == 7
    assert market.merge_record(a, {"stars": 2, "served": 6, "total": 8, "coins": 99})["coins"] == 99
    assert market.merge_record(a, {"stars": 1, "served": 8, "total": 8, "coins": 999}) == a
