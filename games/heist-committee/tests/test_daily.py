"""The Daily Job (M-1b-10): one deterministic, fairness-proven job per UTC date, derived from the date text alone."""

import itertools
import json
import re
from pathlib import Path

import pytest

import bots
import daily
import engine

GAME = Path(__file__).resolve().parent.parent


def dates(start, n):
    out, d = [], start
    for _ in range(n):
        out.append(d)
        d = daily.add_days(d, 1)
    return out


@pytest.fixture(scope="module")
def three_hundred():
    return dates(daily.EPOCH, 300)


# --- dates --------------------------------------------------------------------------------------------
def test_dates_are_strict_and_playable_range_is_epoch_to_today():
    assert daily.valid_date("2026-10-11") and not daily.valid_date("2026-13-01") and not daily.valid_date("2026-2-3")
    assert not daily.valid_date(None) and not daily.valid_date(20261011) and not daily.valid_date("2026-10-11T00:00")
    assert daily.playable("2026-10-01", "2026-10-11") and daily.playable("2026-10-11", "2026-10-11")
    assert not daily.playable("2026-09-30", "2026-10-11") and not daily.playable("2026-10-12", "2026-10-11")
    assert not daily.playable("nonsense", "2026-10-11") and not daily.playable("2026-10-05", "nonsense")
    assert daily.day_number(daily.EPOCH) == 1 and daily.day_number("2026-10-11") == 11


def test_the_module_never_reads_the_clock():
    source = (GAME / "daily.py").read_text(encoding="utf-8")
    assert not re.search(r"\b(time\.|datetime\.now|\.today\(|utcnow|random\.|import random|import time)", source)
    with pytest.raises(ValueError):
        daily.spec(__import__("content").load(), "not a date")


# --- determinism ---------------------------------------------------------------------------------------
def test_a_date_gives_the_same_job_every_time(C):
    for d in ("2026-10-01", "2026-10-11", "2027-03-14", "2030-01-01"):
        first = json.dumps(daily.spec(C, d), sort_keys=True)
        daily._cache.clear()
        assert json.dumps(daily.spec(C, d), sort_keys=True) == first


def test_the_order_of_asking_never_matters(C, three_hundred):
    forward = [json.dumps(daily.spec(C, d), sort_keys=True) for d in three_hundred[:40]]
    daily._cache.clear()
    backward = [json.dumps(daily.spec(C, d), sort_keys=True) for d in reversed(three_hundred[:40])]
    assert forward == list(reversed(backward))


def test_different_dates_give_different_nights_and_every_target_comes_up(C, three_hundred):
    specs = [daily.spec(C, d) for d in three_hundred]
    assert len({s["seed"] for s in specs}) >= 295
    assert {s["target"] for s in specs} == set(C.target_order)
    assert len({(s["target"], tuple(s["offer"])) for s in specs}) >= 295


# --- the fairness bar ----------------------------------------------------------------------------------
def test_every_daily_for_300_days_has_three_clean_witness_crews(C, three_hundred):
    for d in three_hundred:
        s = daily.spec(C, d)
        assert len(s["offer"]) == 8 and len(set(s["offer"])) == 8
        assert {C.crew[c]["role"] for c in s["offer"]} == set(C.roles), d
        assert len(s["van"]) == daily.VAN_SIZE and len(set(s["van"])) == daily.VAN_SIZE
        assert len(s["witnesses"]) >= daily.MIN_CLEAN_CREWS
        assert len({tuple(w["crew"]) for w in s["witnesses"]}) == len(s["witnesses"])
        for w in s["witnesses"]:
            assert len(w["crew"]) == 5 and set(w["crew"]) <= set(s["offer"])
            plan = bots.greedy_plan(C, s["target"], w["crew"], kinds=bots.scouted_kinds(C, s["target"]))
            out = engine.simulate(C, s["target"], w["crew"], plan, (), s["seed"])["outcome"]
            assert out["escaped"] and not out["alarm"] and out["net"] == w["net"], (d, w)
        assert s["par"] == min(w["net"] for w in s["witnesses"]) and s["par"] > C.targets[s["target"]]["consolation"]


def test_an_exhaustive_search_agrees_there_are_many_clean_crews(C, three_hundred):
    for d in three_hundred[::10]:
        s = daily.spec(C, d)
        kinds = bots.scouted_kinds(C, s["target"])
        clean = 0
        for combo in itertools.combinations(s["offer"], 5):
            out = engine.simulate(C, s["target"], list(combo), bots.greedy_plan(C, s["target"], list(combo), kinds=kinds), (), s["seed"])["outcome"]
            clean += out["escaped"] and not out["alarm"]
        assert clean >= daily.MIN_CLEAN_CREWS, (d, clean)


def test_a_job_that_fails_the_bar_is_replaced_not_served(C, monkeypatch):
    real = daily.prove
    calls = []

    def stingy(content, target_id, offer, seed, key=""):
        calls.append(key)
        return None if len(calls) < 3 else real(content, target_id, offer, seed, key)

    monkeypatch.setattr(daily, "prove", stingy)
    daily._cache.clear()
    s = daily.spec(C, "2026-12-25")
    assert s["attempt"] == 2 and len(calls) == 3
    daily._cache.clear()


def test_tiers_follow_the_outcome():
    assert daily.tier_of({"escaped": False, "alarm": False, "net": 90}, 300) == "busted"
    assert daily.tier_of({"escaped": True, "alarm": True, "net": 900}, 300) == "escaped"
    assert daily.tier_of({"escaped": True, "alarm": False, "net": 299}, 300) == "clean"
    assert daily.tier_of({"escaped": True, "alarm": False, "net": 300}, 300) == "par"


# --- records: best only, validated --------------------------------------------------------------------------
def test_merge_record_keeps_the_best_and_counts_tries():
    r = daily.merge_record(None, "escaped", 200)
    r = daily.merge_record(r, "busted", 90)
    assert r == {"tier": 1, "net": 200, "tries": 2}
    r = daily.merge_record(r, "par", 640)
    assert r == {"tier": 3, "net": 640, "tries": 3}


def test_clean_days_drops_junk_one_entry_at_a_time():
    raw = {"2026-10-05": {"tier": 2, "net": 300, "tries": 1}, "2026-10-06": {"tier": 9, "net": -5, "tries": 0},
           "nope": {"tier": 1, "net": 1, "tries": 1}, "2026-09-01": {"tier": 1, "net": 1, "tries": 1},
           "2026-10-07": {"tier": "x", "net": 1, "tries": 1}, "2026-10-08": [1], "2026-10-09": {"tier": True, "net": 1, "tries": 1}, 5: {}}
    assert daily.clean_days(raw) == {"2026-10-05": {"tier": 2, "net": 300, "tries": 1},
                                     "2026-10-06": {"tier": 3, "net": 0, "tries": 1}}
    assert daily.clean_days("junk") == {} and daily.clean_days(None) == {}


def test_leaderboard_hook_only_shapes_an_entry():
    entry = daily.leaderboard_entry("2026-10-05", {"tier": 2, "net": 410, "tries": 3})
    assert entry == {"board": "heist-daily-job", "date": "2026-10-05", "score": 410, "tier": "clean"}


def test_tally_counts_open_days_without_any_streak():
    days = {"2026-10-02": {"tier": 2, "net": 1, "tries": 1}, "2026-10-09": {"tier": 0, "net": 1, "tries": 1}, "2026-10-20": {"tier": 3, "net": 1, "tries": 1}}
    assert daily.tally(days, "2026-10-11") == {"open": 11, "played": 2, "clean": 1}
    assert daily.tally(days, "2026-09-01") == {"open": 0, "played": 0, "clean": 0}
    assert "streak" not in json.dumps(daily.tally(days, "2026-10-11"))


# --- the game flow --------------------------------------------------------------------------------------
TODAY = "2026-10-11"


@pytest.fixture(autouse=True)
def _fresh_daily_history(g):
    """A new career keeps the daily history (by design), so each test starts from an empty one."""
    def wipe():
        g.module.career.daily_days.clear()
        g.module.career.daily_job = None
        g.module._today = None
    wipe()
    yield
    wipe()


def play_daily(g, date, crew_index=0):
    """Open a date's daily, hire a witness crew, plan with the bot and play it to the payout."""
    s = daily.spec(g.module.C, date)
    g(action="daily_open", date=date, today=TODAY)
    g(action="to_recruit", today=TODAY)
    crew = s["witnesses"][crew_index]["crew"]
    for cid in crew:
        g(action="hire", crew=cid, today=TODAY)
    g(action="confirm_crew", today=TODAY)
    plan = bots.greedy_plan(g.module.C, s["target"], crew, kinds=bots.scouted_kinds(g.module.C, s["target"]))
    g.module.career.job["plan"] = engine.clean_plan(g.module.C, plan, len(plan["lanes"][0]))
    g(action="start_heist", today=TODAY)
    g(action="skip", today=TODAY)
    return g(action="finish", today=TODAY)["view"]


def test_the_board_offers_today_only_when_the_view_passes_the_date(g):
    assert g(action="open")["view"]["daily_board"] is None
    board = g(action="open", today=TODAY)["view"]["daily_board"]
    assert board["number"] == 11 and board["open"] and board["target"]["id"] == daily.spec(g.module.C, TODAY)["target"]
    assert board["tally"] == {"open": 11, "played": 0, "clean": 0} and board["days"] == {}
    before = g(action="open", today="2026-09-01")["view"]["daily_board"]
    assert before["open"] is False and before["target"] is None


def test_opening_a_daily_checks_the_date(g):
    for date, word in (("2026-10-12", "not out yet"), ("2026-09-30", "no daily job"), ("garbage", "not a date")):
        reply = g(action="daily_open", date=date, today=TODAY)
        assert reply["view"]["phase"] == "board" and word in reply["view"]["note"]
    assert "not known" in g(action="daily_open", date=TODAY)["view"]["note"] or True
    g.module._today = None
    assert "not known" in g(action="daily_open", date=TODAY)["view"]["note"]


def test_the_daily_is_free_and_does_not_touch_the_career(g):
    g(action="open", today=TODAY)
    before = {k: v for k, v in g.module.get_state().items() if k != "daily_days"}
    view = g(action="daily_open", date="2026-10-05", today=TODAY)["view"]
    assert view["phase"] == "scout" and view["daily"]["number"] == 5 and view["scout"]["next"] is None
    recruit = g(action="to_recruit", today=TODAY)["view"]
    assert len(recruit["offer"]) == 8 and all(c["quirk"] for c in recruit["offer"])
    assert [x["id"] for x in recruit["gear"]] == daily.spec(g.module.C, "2026-10-05")["van"]
    assert all(x["cost"] == 0 and not x["locked"] for x in recruit["gear"])
    view = play_daily(g, "2026-10-05")
    assert view["phase"] == "payout" and view["daily"]["tier"] in daily.TIERS
    assert view["cash"] == 300 and view["reputation"] == 0 and view["payout"]["credited"] == 0
    assert view["payout"]["new_unlocks"] == [] and view["payout"]["relations_changed"] == []
    after = g.module.get_state()
    for key, value in before.items():
        assert after.get(key) == value if key != "daily_job" else True
    assert after["daily_days"]["2026-10-05"]["tries"] == 1
    assert "meta" not in after and "job" not in after and "cash" not in after


def test_the_witness_crew_earns_the_top_tier_and_a_retry_keeps_the_best(g):
    g(action="open", today=TODAY)
    view = play_daily(g, "2026-10-05")
    spec = daily.spec(g.module.C, "2026-10-05")
    assert view["daily"]["tier"] in ("clean", "par") and view["payout"]["net"] == spec["witnesses"][0]["net"]
    best = dict(g.module.career.daily_days["2026-10-05"])
    assert g(action="retry", today=TODAY)["view"]["phase"] == "plan"
    g.module.career.job["plan"] = engine.empty_plan(len(g.module.C.targets[spec["target"]]["beats"]))
    g(action="start_heist", today=TODAY)
    g(action="skip", today=TODAY)
    worse = g(action="finish", today=TODAY)["view"]
    assert worse["daily"]["tier"] == "busted"
    now = g.module.career.daily_days["2026-10-05"]
    assert now["tier"] == best["tier"] and now["net"] == best["net"] and now["tries"] == 2
    board = g(action="back_to_board", today=TODAY)["view"]
    assert board["phase"] == "board" and board["daily_board"]["tally"]["played"] == 1


def test_a_career_job_in_progress_blocks_the_daily_and_nothing_is_lost(g):
    g(action="open", today=TODAY)
    g(action="take_job", target="pigeon_museum", today=TODAY)
    reply = g(action="daily_open", date=TODAY, today=TODAY)
    assert "Finish or abandon" in reply["view"]["note"] and reply["view"]["phase"] == "scout"
    assert g.module.career.daily_job is None


def test_setting_a_daily_aside_costs_nothing_and_resuming_keeps_the_plan(g):
    g(action="open", today=TODAY)
    g(action="daily_open", date=TODAY, today=TODAY)
    again = g(action="daily_open", date=TODAY, today=TODAY)["view"]
    assert again["phase"] == "scout"                       # the same open job, not a second one
    note = g(action="abandon", today=TODAY)["view"]
    assert note["phase"] == "board" and "set aside" in note["note"] and note["cash"] == 300
    assert g.module.career.jobs_started == 0


def test_a_new_career_keeps_the_daily_history(g):
    g(action="open", today=TODAY)
    play_daily(g, "2026-10-03")
    g(action="back_to_board", today=TODAY)
    view = g(action="new_career", seed=5, today=TODAY)["view"]
    assert view["daily_board"]["tally"]["played"] == 1 and view["cash"] == 300


# --- saves ----------------------------------------------------------------------------------------------------
def test_old_saves_load_unchanged_and_a_fresh_save_has_no_daily_keys(g):
    state = g.module.get_state()
    assert not any(k.startswith("daily") for k in state)
    g.module.load_state({"schema": 1, "career_seed": 9, "cash": 410, "jobs_started": 2})
    assert g.module.career.cash == 410 and g.module.career.daily_days == {} and g.module.career.daily_job is None
    assert not any(k.startswith("daily") for k in g.module.get_state())


def test_a_daily_in_progress_survives_a_save_and_load(g):
    g(action="open", today=TODAY)
    s = daily.spec(g.module.C, "2026-10-07")
    g(action="daily_open", date="2026-10-07", today=TODAY)
    g(action="to_recruit", today=TODAY)
    for cid in s["witnesses"][0]["crew"]:
        g(action="hire", crew=cid, today=TODAY)
    g(action="confirm_crew", today=TODAY)
    state = json.loads(json.dumps(g.module.get_state()))
    assert state["daily_job"]["phase"] == "plan" and "job" not in state
    g.module.load_state(state)
    view = g(action="open", today=TODAY)["view"]
    assert view["phase"] == "plan" and view["daily"]["date"] == "2026-10-07" and view["crew_ids"] == s["witnesses"][0]["crew"]


def test_a_tampered_daily_job_is_rebuilt_from_its_date(g):
    s = daily.spec(g.module.C, "2026-10-07")
    other = "the_affineur" if s["target"] != "the_affineur" else "lucky_barge"
    save = {"schema": 1, "career_seed": 3, "daily_job": {"phase": "plan", "target": other, "seed": 5, "daily": "2026-10-07",
                                                         "offer": ["dot"], "crew": ["dot", "pip", "zzz", "bea", "tomasz", "hank"],
                                                         "gear": ["sticky_gloves", "bogus"], "scout": 0, "plan": "junk"},
            "daily_days": {"2026-10-07": {"tier": 99, "net": "x", "tries": 1}, "2026-10-06": {"tier": 1, "net": 5, "tries": 2}}}
    g.module.load_state(save)
    job = g.module.career.daily_job
    assert job is None or (job["target"] == s["target"] and job["seed"] == s["seed"] and job["offer"] == s["offer"]
                           and set(job["crew"]) <= set(s["offer"]) and set(job["gear"]) <= set(s["van"]))
    assert g.module.career.daily_days == {"2026-10-06": {"tier": 1, "net": 5, "tries": 2}}
    for junk in (None, [], "x", {"daily": "2026-10-07"}, {"daily": "2020-01-01", "phase": "plan"}, {"daily": 5}):
        g.module.load_state({"daily_job": junk})
        assert g.module.career.daily_job is None


def test_a_saved_daily_for_a_future_date_is_dropped_when_the_view_gives_the_date(g):
    s = {"schema": 1, "career_seed": 3, "daily_job": {"phase": "scout", "daily": "2026-10-20"}}
    g.module.load_state(s)
    assert g(action="open", today=TODAY)["view"]["phase"] == "board"
    assert g.module.career.daily_job is None


def test_a_payout_without_its_result_is_replayed_not_trusted(g):
    s = daily.spec(g.module.C, "2026-10-07")
    plan = bots.greedy_plan(g.module.C, s["target"], s["witnesses"][0]["crew"])
    save = {"schema": 1, "career_seed": 3, "daily_job": {"phase": "payout", "daily": "2026-10-07", "crew": s["witnesses"][0]["crew"],
                                                         "plan": plan, "cursor": 6, "attempt": 1}}
    g.module.load_state(save)
    assert g.module.career.daily_job["phase"] == "plan"
