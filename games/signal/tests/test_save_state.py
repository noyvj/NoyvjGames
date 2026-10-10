"""get_state/load_state: the save-widget contract, validation and merge."""

import copy
import json

import pytest


def played(g, offsets=(0, 1), mode="easy"):
    for offset in offsets:
        day = g.set_day(offset)
        g.call("boot")
        g.call("open", date=day, mode=mode)
        g.win_current(pings=2)


def fresh(g):
    g.m.reset_engine()
    g.set_day(30)


def test_state_is_json_safe_and_has_the_documented_keys(g):
    played(g)
    g.call("practice", mode="easy")
    g.call("ping", r=4, c=4)
    state = g.m.get_state()
    assert json.loads(json.dumps(state)) == state
    assert set(state) == {
        "schema", "stats", "days", "practice", "practice_stats", "settings", "earned",
        "flags", "onboarding_seen", "session", "achievements_earned",
    }
    assert state["schema"] == 1 and set(state["days"]) == {"2026-09-27:easy", "2026-09-28:easy"}
    assert state["practice"]["code"].startswith("P-E") and len(state["practice"]["pings"]) == 1


def test_get_state_returns_copies(g):
    played(g, offsets=(0,))
    state = g.m.get_state()
    state["days"]["2026-09-27:easy"]["pings"].append([8, 8, 0])
    state["earned"]["hacked"] = "x"
    assert len(g.m.S["days"]["2026-09-27:easy"]["pings"]) == 2 and "hacked" not in g.m.S["earned"]


def test_round_trip_restores_everything(g):
    played(g)
    g.call("share")
    g.call("settings", assist_shading=False, ascii_share=True)
    g.call("practice", mode="hard")
    g.call("ping", r=3, c=3)
    saved = json.loads(json.dumps(g.m.get_state()))
    fresh(g)
    assert g.m.load_state(saved) is True
    again = g.m.get_state()
    for key in ("days", "practice", "practice_stats", "settings", "earned", "flags", "onboarding_seen", "achievements_earned"):
        assert again[key] == saved[key], key
    assert again["stats"]["easy"]["best_streak"] == 2


def test_load_state_accepts_a_json_string(g):
    played(g, offsets=(0,))
    text = json.dumps(g.m.get_state())
    fresh(g)
    assert g.m.load_state(text) is True and "2026-09-27:easy" in g.m.S["days"]
    assert g.m.load_state("{not json") is False


@pytest.mark.parametrize("junk", [None, 5, "x", [], [1, 2], True, 3.5])
def test_non_dict_saves_are_rejected_without_touching_state(g, junk):
    played(g, offsets=(0,))
    before = json.dumps(g.m.get_state(), sort_keys=True)
    assert g.m.load_state(junk) is False
    assert json.dumps(g.m.get_state(), sort_keys=True) == before


@pytest.mark.parametrize("schema", [0, -1, 2, 99, "1", 1.0, True, None, [1], {"a": 1}])
def test_bad_schema_versions_are_rejected(g, schema):
    played(g, offsets=(0,))
    saved = g.m.get_state()
    saved["schema"] = schema
    fresh(g)
    assert g.m.load_state(saved) is False
    assert g.m.S["days"] == {}


def test_missing_schema_is_treated_as_v1(g):
    played(g, offsets=(0,))
    saved = g.m.get_state()
    del saved["schema"]
    fresh(g)
    assert g.m.load_state(saved) is True and g.m.S["days"]


def base_day():
    return {
        "mode": "easy", "kind": "daily", "pings": [[4, 4, 2], [2, 2, 0]], "marks": [], "guess": [],
        "result": "inprogress", "pings_used": 2, "par": None,
    }


def load_days(g, days):
    fresh(g)
    g.m.load_state({"schema": 1, "days": days})
    return g.m.S["days"]


def test_valid_day_records_load(g):
    days = load_days(g, {"2026-09-27:easy": base_day()})
    assert days["2026-09-27:easy"]["pings"] == [[4, 4, 2], [2, 2, 0]]


BAD_MUTATIONS = {
    "bool as int (ping row)": lambda d: d["pings"].__setitem__(0, [True, 4, 2]),
    "bool as int (reading)": lambda d: d["pings"].__setitem__(0, [4, 4, True]),
    "float coord": lambda d: d["pings"].__setitem__(0, [4.0, 4, 2]),
    "string coord": lambda d: d["pings"].__setitem__(0, ["4", 4, 2]),
    "off board": lambda d: d["pings"].__setitem__(0, [9, 4, 2]),
    "negative coord": lambda d: d["pings"].__setitem__(0, [-1, 4, 2]),
    "negative reading": lambda d: d["pings"].__setitem__(0, [4, 4, -1]),
    "absurd reading": lambda d: d["pings"].__setitem__(0, [4, 4, 999]),
    "duplicate ping": lambda d: d["pings"].append([4, 4, 2]),
    "too many pings": lambda d: d.__setitem__("pings", [[r, c, 0] for r in range(3) for c in range(4)]),
    "ping wrong length": lambda d: d["pings"].__setitem__(0, [4, 4]),
    "pings not a list": lambda d: d.__setitem__("pings", {"a": 1}),
    "unhashable mode": lambda d: d.__setitem__("mode", ["easy"]),
    "unknown mode": lambda d: d.__setitem__("mode", "nightmare"),
    "mode mismatch with key": lambda d: d.__setitem__("mode", "hard"),
    "unhashable kind": lambda d: d.__setitem__("kind", ["daily"]),
    "practice kind in days": lambda d: d.__setitem__("kind", "practice"),
    "unhashable result": lambda d: d.__setitem__("result", [1]),
    "bad result": lambda d: d.__setitem__("result", "draw"),
    "marks ring tile": lambda d: d.__setitem__("marks", [[0, 3]]),
    "marks too many": lambda d: d.__setitem__("marks", [[3, 3], [5, 5], [6, 6]]),
    "marks duplicate": lambda d: d.__setitem__("marks", [[3, 3], [3, 3]]),
    "marks bool": lambda d: d.__setitem__("marks", [[True, 3]]),
    "marks not list": lambda d: d.__setitem__("marks", "x"),
    "won without a full guess": lambda d: d.update(result="won", guess=[[3, 3]]),
    "par out of range": lambda d: d.__setitem__("par", 99),
    "par bool": lambda d: d.__setitem__("par", True),
    "par string": lambda d: d.__setitem__("par", "4"),
}


@pytest.mark.parametrize("name", sorted(BAD_MUTATIONS))
def test_invalid_day_records_are_dropped_not_loaded(g, name):
    rec = base_day()
    BAD_MUTATIONS[name](rec)
    days = load_days(g, {"2026-09-27:easy": rec, "2026-09-28:easy": base_day()})
    assert "2026-09-27:easy" not in days
    assert "2026-09-28:easy" in days  # one bad record never poisons the rest


@pytest.mark.parametrize("key", ["2026-09-27", "2026-09-27:wide", "2026-13-01:easy", "junk", "2026-09-27:easy:x", "", 5, None, ("a",)])
def test_bad_day_keys_are_dropped(g, key):
    days = load_days(g, {key: base_day()})
    assert days == {}


def test_non_dict_days_and_unhashable_junk_are_harmless(g):
    for junk in ([], "x", 5, None, [[1, 2]]):
        fresh(g)
        assert g.m.load_state({"schema": 1, "days": junk}) is True
        assert g.m.S["days"] == {}
    fresh(g)
    assert g.m.load_state({"schema": 1, "days": {"2026-09-27:easy": [1, 2], "2026-09-28:easy": None}}) is True


def test_settings_are_validated_field_by_field(g):
    fresh(g)
    g.m.load_state({"schema": 1, "settings": {
        "mode": ["hard"], "assist_shading": 1, "ascii_share": "yes", "last_preset": {"a": 1}}})
    assert g.m.S["settings"] == g.m._DEFAULT_SETTINGS
    g.m.load_state({"schema": 1, "settings": {"mode": "hard", "assist_shading": False, "ascii_share": True, "last_preset": "bigsky"}})
    assert g.m.S["settings"] == {"mode": "hard", "assist_shading": False, "ascii_share": True, "show_streaks": False, "last_preset": "bigsky"}
    g.m.load_state({"schema": 1, "settings": {"show_streaks": True}})
    assert g.m.S["settings"]["show_streaks"] is True
    g.m.load_state({"schema": 1, "settings": {"show_streaks": "yes"}})
    assert g.m.S["settings"]["show_streaks"] is False
    g.m.load_state({"schema": 1, "settings": {"mode": "wide"}})  # wide is not a daily mode
    assert g.m.S["settings"]["mode"] == "easy"


def test_earned_achievements_are_validated(g):
    fresh(g)
    g.m.load_state({"schema": 1, "earned": {
        "first_contact": "2026-09-30", "bogus": "2026-09-30", "static": "not a date", "show_off": 5, ("x",): "2026-09-30"}})
    assert g.m.S["earned"]["first_contact"] == "2026-09-30"
    assert set(g.m.S["earned"]) == {"first_contact"}


def test_practice_stats_and_flags_are_validated(g):
    fresh(g)
    g.m.load_state({"schema": 1, "practice_stats": {
        "easy": {"played": True, "won": 5, "pings_hist": [1] * 8},
        "hard": {"played": 4, "won": 9, "pings_hist": [0] * 9},
        "wide": {"played": 3, "won": 2, "pings_hist": [0, 1]},
        "bigsky": "junk"}, "flags": {"shared": 1}, "onboarding_seen": "yes"})
    ps = g.m.S["practice_stats"]
    assert ps["easy"]["played"] == 0 and ps["easy"]["won"] == 0
    assert ps["hard"]["played"] == 4 and ps["hard"]["won"] == 0  # won > played rejected
    assert ps["wide"]["played"] == 3 and ps["wide"]["pings_hist"] == [0] * 12
    assert ps["bigsky"] == {"played": 0, "won": 0, "pings_hist": [0] * 14}
    assert g.m.S["flags"]["shared"] is False and g.m.S["onboarding_seen"] is False


def test_practice_record_is_validated(g):
    good = {"code": "P-E12345", "mode": "easy", "kind": "practice", "pings": [], "marks": [], "guess": [],
            "result": "inprogress", "pings_used": 0, "par": None}
    fresh(g)
    g.m.load_state({"schema": 1, "practice": good})
    assert g.m.S["practice"]["code"] == "P-E12345"
    for mutate in (lambda d: d.update(code="P-H12345"), lambda d: d.update(code=None), lambda d: d.update(kind="daily"), lambda d: d.update(code=["x"])):
        fresh(g)
        bad = copy.deepcopy(good)
        mutate(bad)
        g.m.load_state({"schema": 1, "practice": bad})
        assert g.m.S["practice"] is None


def test_stored_readings_are_repaired_and_forged_wins_are_downgraded_on_open(g):
    day = g.set_day(0)
    g.call("boot")
    truth = g.truth_rc()
    forged = {
        "mode": "easy", "kind": "daily", "pings": [[4, 4, 5]], "marks": [], "guess": [[1, 1], [7, 7]],
        "result": "won", "pings_used": 1, "par": 1,
    }
    fresh(g)
    g.set_day(0)
    g.m.load_state({"schema": 1, "days": {"%s:easy" % day: forged}})
    view = g.call("boot")["view"]
    rec = g.m.S["days"]["%s:easy" % day]
    assert rec["pings"][0][2] == g.m.reading_at(g.m.board_for("easy"), g.truth(), 40)
    assert rec["result"] == "lost" and view["status"] == "lost" and truth


def test_days_are_capped_and_oldest_pruned(g):
    fresh(g)
    days = {}
    import datetime
    start = datetime.date(2024, 1, 1)
    for i in range(500):
        d = (start + datetime.timedelta(days=i)).isoformat()
        for mode in ("easy", "hard"):
            rec = base_day()
            rec["mode"] = mode
            days["%s:%s" % (d, mode)] = rec
    g.m.load_state({"schema": 1, "days": days})
    assert len(g.m.S["days"]) == g.m.MAX_DAYS == 800
    assert "2024-01-01:easy" not in g.m.S["days"] and "2025-05-14:hard" in g.m.S["days"]


# ---- merge --------------------------------------------------------------


def finished(result="won", kind="daily", pings=3, mode="easy"):
    rec = base_day()
    rec.update(result=result, kind=kind, mode=mode, pings=[[i, i, 0] for i in range(pings)], pings_used=pings,
               guess=[[3, 3], [5, 5]], par=4)
    return rec


def merged(g, a, b):
    fresh(g)
    g.m.load_state({"schema": 1, "days": {"2026-09-27:easy": a}})
    g.m.load_state({"schema": 1, "days": {"2026-09-27:easy": b}})
    return g.m.S["days"]["2026-09-27:easy"]


def test_merge_prefers_a_result_over_in_progress(g):
    assert merged(g, base_day(), finished("lost"))["result"] == "lost"
    assert merged(g, finished("lost"), base_day())["result"] == "lost"


def test_merge_keeps_the_daily_over_an_archive_replay(g):
    assert merged(g, finished("lost", "daily"), finished("won", "archive"))["kind"] == "daily"
    assert merged(g, finished("won", "archive"), finished("lost", "daily"))["result"] == "lost"


def test_merge_prefers_wins_then_fewer_pings_and_is_commutative(g):
    a, b = finished("won", pings=5), finished("won", pings=3)
    assert merged(g, a, b) == merged(g, b, a)
    assert merged(g, a, b)["pings_used"] == 3
    assert merged(g, finished("lost"), finished("won"))["result"] == "won"
    p, q = base_day(), base_day()
    q["pings"].append([6, 6, 1])
    q["pings_used"] = 3
    assert merged(g, p, q) == merged(g, q, p) and merged(g, p, q)["pings_used"] == 3


def test_merge_unions_days_earned_and_flags_and_keeps_larger_practice_counters(g):
    fresh(g)
    g.m.load_state({"schema": 1, "days": {"2026-09-27:easy": finished()}, "earned": {"first_contact": "2026-09-27"},
                    "practice_stats": {"easy": {"played": 3, "won": 2, "pings_hist": [0, 1, 1, 0, 0, 0, 0, 0]}}})
    g.m.load_state({"schema": 1, "days": {"2026-09-28:easy": finished()}, "earned": {"static": "2026-09-28", "first_contact": "2026-09-20"},
                    "flags": {"shared": True}, "onboarding_seen": True,
                    "practice_stats": {"easy": {"played": 2, "won": 2, "pings_hist": [1, 0, 0, 0, 0, 0, 0, 0]}}})
    assert set(g.m.S["days"]) == {"2026-09-27:easy", "2026-09-28:easy"}
    assert g.m.S["earned"]["first_contact"] == "2026-09-20" and "static" in g.m.S["earned"]
    assert g.m.S["flags"]["shared"] and g.m.S["onboarding_seen"]
    assert g.m.S["practice_stats"]["easy"] == {"played": 3, "won": 2, "pings_hist": [1, 1, 1, 0, 0, 0, 0, 0]}


def test_loading_never_loses_local_progress(g):
    played(g, offsets=(0, 1, 2))
    local = set(g.m.S["days"])
    g.m.load_state({"schema": 1, "days": {}})
    assert set(g.m.S["days"]) == local


def test_loading_recomputes_achievements_from_merged_days(g):
    played(g, offsets=(0,))
    state = g.m.get_state()
    state["earned"] = {}
    state["achievements_earned"] = []
    fresh(g)
    g.m.load_state(state)
    assert "first_contact" in g.m.S["earned"]


def test_load_state_notifies_the_ui_when_available(g, monkeypatch):
    import sys
    import types
    calls = []
    fake = types.ModuleType("js")
    fake.window = types.SimpleNamespace(signalOnStateLoaded=lambda: calls.append(1))
    monkeypatch.setitem(sys.modules, "js", fake)
    fresh(g)
    assert g.m.load_state({"schema": 1}) is True
    assert calls == [1]


def test_a_broken_ui_hook_cannot_break_loading(g, monkeypatch):
    import sys
    import types

    def boom():
        raise RuntimeError("ui exploded")

    fake = types.ModuleType("js")
    fake.window = types.SimpleNamespace(signalOnStateLoaded=boom)
    monkeypatch.setitem(sys.modules, "js", fake)
    fresh(g)
    assert g.m.load_state({"schema": 1}) is True
