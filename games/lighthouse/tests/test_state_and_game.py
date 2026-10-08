"""The save contract and the `handle` entry point: a round trip loses nothing, junk never raises, and every
action answers with the whole view."""

import copy
import json
import random

import data
import game
import sim
from state import Keep, clean_order


def req(**kw):
    return json.loads(game.handle(json.dumps(kw)))


def fresh(seed=1):
    return req(action="new_game", seed=seed)


# ---- state -------------------------------------------------------------------------------------------------
def test_a_new_keep_round_trips_and_writes_only_non_defaults():
    k = Keep(7)
    sim.to_evening(k)
    d = k.to_dict()
    for absent in ("override", "incident", "progress", "boat_due", "upgrades", "waiting", "log", "report", "mode", "quiet"):
        assert absent not in d["run"], absent
    assert d["meta"] == {}
    assert Keep.from_dict(json.loads(json.dumps(d))).to_dict() == d


def test_a_mid_night_save_round_trips_exactly():
    k = Keep(3)
    k.night = 11
    sim.to_evening(k)
    sim.begin_night(k)
    sim.step(k, 17)
    d = k.to_dict()
    assert d["run"]["phase"] == "night" and d["run"]["tick"] == 17
    again = Keep.from_dict(json.loads(json.dumps(d)))
    assert again.to_dict() == d
    sim.step(k, 10 ** 6)
    sim.step(again, 10 ** 6)
    assert k.to_dict() == again.to_dict()


def test_from_dict_never_raises_on_garbage():
    rng = random.Random(5)
    junk = [None, 5, "x", [], {}, {"run": 5}, {"run": {"phase": 3, "night": "x", "oil": float("nan")}},
            {"run": {"plan": {"levels": ["nope", 3, None, 4]}}}, {"meta": {"counters": 5, "achievements_earned": "a"}},
            {"run": {"supplies": {"food": -9, "tar": 10 ** 9}, "structure": {"tower": "x", "dock": 500}}},
            {"run": {"ships": 3, "log": [[1], ["a", "b", "c"], 5], "report": {"ships": 4}, "waiting": [1, {"id": 3}]}},
            {"run": {"override": [9, 9], "incident": {"kind": "boo"}, "progress": {"x": 5}}}]
    for item in junk:
        k = Keep.from_dict(item)
        k.to_dict()
        assert 0 <= k.oil <= 280 and all(0 <= v <= 100 for v in k.structure.values())
        assert all(0 <= k.supplies[s] <= data.SUPPLY_CAP for s in data.SUPPLIES)
    base = Keep(2)
    sim.to_evening(base)
    sim.begin_night(base)
    sim.step(base, 20)
    good = base.to_dict()
    for _ in range(300):
        broken = copy.deepcopy(good)
        target = broken["run"]
        key = rng.choice(sorted(target))
        target[key] = rng.choice([None, "zz", -1, 10 ** 12, [], {}, [1, 2], {"a": 1}, True, 1.5, float("inf")])
        k = Keep.from_dict(broken)
        k.to_dict()
        sim.step(k, 5)                         # and the broken-then-cleaned keep still runs


def test_values_are_clamped_not_trusted():
    k = Keep.from_dict({"run": {"night": 0, "oil": 99999, "energy": -5, "reputation": -3, "comfort": 99, "salvage": -1,
                                "tick": 9999, "plan": {"ration": -2, "focus": "roof"}}})
    assert k.night == 1 and k.oil == 280 and k.energy == 0 and k.reputation == 0 and k.comfort == data.COMFORT_MAX
    assert k.salvage == 0 and k.tick <= 42 and k.ration == 0 and k.focus == "worst"


def test_clean_order_demands_exactly_the_boat_load():
    assert clean_order({"oil": 12, "food": 0, "timber": 0, "tar": 0, "glass": 0})["oil"] == 12
    assert clean_order({"oil": 5}) == data.DEFAULT_ORDER
    assert clean_order({"oil": 6, "food": 6, "timber": 6, "tar": 0, "glass": 0}) == data.DEFAULT_ORDER
    assert clean_order("junk") == data.DEFAULT_ORDER


# ---- the game entry point -----------------------------------------------------------------------------------
def test_open_returns_the_whole_view_and_json_is_always_valid():
    v = fresh(3)
    for key in ("phase", "night", "oil", "energy", "structure", "supplies", "plan", "forecast", "notice", "log", "boat",
                "day", "upgrades", "meta", "achievements", "ok", "message", "beam", "ships"):
        assert key in v, key
    assert v["phase"] == "evening" and v["night"] == 1 and v["ok"] is True
    json.dumps(v)


def test_a_whole_night_through_handle():
    fresh(4)
    assert req(action="start_night")["phase"] == "night"
    n = 0
    while True:
        v = req(action="step", n=1)
        n += 1
        assert n < 200
        if v["phase"] != "night":
            break
    assert v["phase"] == "morning" and v["report"]["night"] == 1 and v["tick"] == v["length"]
    v = req(action="end_morning")
    assert v["phase"] == "day" and v["day"]["slots"] == data.DAY_SLOTS
    v = req(action="end_day")
    assert v["phase"] == "evening" and v["night"] == 2


def test_bad_requests_answer_in_words_and_change_nothing():
    fresh(5)
    before = game.get_state()
    for bad in (dict(action="plan", levels=["x", "y", "z"]), dict(action="plan", levels="bright"), dict(action="plan", tasks=5),
                dict(action="plan", ration=-5), dict(action="plan", focus="roof"), dict(action="level", level="storm"),
                dict(action="wind"), dict(action="tend"), dict(action="patch", part="tower"), dict(action="end_morning"),
                dict(action="end_day"), dict(action="day", task="repair", part="tower"), dict(action="day", task="fly"),
                dict(action="upgrade", id="lens"), dict(action="upgrade", id="warp"), dict(action="continue"),
                dict(action="order", order={"oil": 3}), dict(action="order", order=5)):
        v = req(**bad)
        assert v.get("ok") is False and v["message"], bad
    assert game.get_state() == before
    assert "error" in req(action="no_such_thing")
    assert "error" in json.loads(game.handle("not json"))
    assert "error" in json.loads(game.handle("[1]"))


def test_the_plan_can_be_edited_and_is_saved():
    fresh(5)
    v = req(action="plan", levels=["bright", "dim", "storm"], tasks={"watch": True, "repair": True}, ration=40, focus="dock")
    assert v["ok"] and v["plan"]["levels"] == ["bright", "dim", "storm"] and v["plan"]["ration"] == 40 and v["plan"]["focus"] == "dock"
    assert v["plan"]["tasks"] == {"wind": True, "watch": True, "repair": True}
    saved = game.get_state()
    assert saved["run"]["plan"]["levels"] == ["bright", "dim", "storm"] and saved["run"]["plan"]["ration"] == 40


def test_get_state_and_load_state_are_the_save_widget_contract():
    fresh(6)
    req(action="plan", levels=["bright", "bright", "dim"])
    req(action="start_night")
    req(action="step", n=12)
    saved = copy.deepcopy(game.get_state())
    assert saved["schema"] == 1 and isinstance(saved["achievements_earned"], list)
    json.dumps(saved)
    req(action="step", n=5)
    fresh(99)
    assert game.load_state(saved) is True
    v = req(action="open")
    assert v["phase"] == "night" and v["tick"] == 12 and v["plan"]["levels"] == ["bright", "bright", "dim"]
    assert game.load_state("garbage") is True               # never raises; falls back to a fresh keeper
    assert req(action="open")["phase"] in ("evening", "night")
    fields = game.copy_result_fields()
    assert fields["game"] == "Lighthouse" and fields["stats"]


def test_load_state_with_a_morning_and_no_report_recovers():
    fresh(2)
    bad = copy.deepcopy(game.get_state())
    bad["run"]["phase"] = "morning"
    game.load_state(bad)
    assert req(action="open")["phase"] == "evening"


def test_new_game_keeps_the_meta_and_reset_wipes_it():
    fresh(8)
    req(action="start_night")
    req(action="step", n=500)
    assert game.keep.meta["nights_kept"] == 1
    v = req(action="abandon", seed=9)
    assert v["night"] == 1 and game.keep.meta["nights_kept"] == 1
    req(action="reset", seed=10)
    assert game.keep.meta["nights_kept"] == 0


def test_settings_action_only_touches_display_choices_the_engine_must_know():
    fresh(1)
    assert req(action="settings", eerie=False)["eerie"] is False
    assert "eerie" not in json.dumps(game.get_state())
    assert req(action="settings", eerie=True)["eerie"] is True
