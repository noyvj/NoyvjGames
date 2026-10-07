"""get_state / load_state (the shared save widget's contract) and the achievements computed from state."""

import copy
import json
import re
from pathlib import Path

import achievements

GAME_DIR = Path(__file__).resolve().parent.parent


def test_get_state_is_plain_json_and_round_trips(p):
    p.solve()
    state = p.m.get_state()
    assert json.loads(json.dumps(state)) == state
    snapshot = copy.deepcopy(state)
    p.m.reset_engine()
    assert p.m.load_state(snapshot) is True
    assert p.m.get_state() == state


def test_load_state_merges_never_replaces(p):
    p.solve()
    mine = p.m.get_state()
    other = {"schema": 1, "sets": {"presidents-sample": {"learned": ["e-removal-act"], "solved": {"s2:0": {"checks": 4}}, "revealed": []}},
             "viewed": ["presidents-sample/c-e-removal-act-date"]}
    p.m.load_state(other)
    prog = p.m.S["sets"]["presidents-sample"]
    assert set(mine["sets"]["presidents-sample"]["learned"]) <= prog["learned"] and "e-removal-act" in prog["learned"]
    assert prog["solved"]["s2:0"] == {"checks": 4} and "s1:0" in prog["solved"]


def test_solved_puzzles_keep_the_fewer_checks(p):
    p.m.load_state({"sets": {"presidents-sample": {"solved": {"s1:0": {"checks": 5}}}}})
    p.m.load_state({"sets": {"presidents-sample": {"solved": {"s1:0": {"checks": 2}}}}})
    p.m.load_state({"sets": {"presidents-sample": {"solved": {"s1:0": {"checks": 9}}}}})
    assert p.m.S["sets"]["presidents-sample"]["solved"]["s1:0"] == {"checks": 2}


def test_garbage_never_raises_and_good_fields_survive(p):
    p.solve()
    before = p.m.get_state()
    for junk in (None, 5, "x", [], {"sets": 3}, {"sets": {"presidents-sample": 7}}, {"sets": {"presidents-sample": {"learned": "no"}}},
                 {"viewed": [1, None, {}]}, {"session": {"set": "nope"}}, {"settings": {"hints": "x", "set": 9}}, {"flags": []}):
        p.m.load_state(junk)
    assert p.m.get_state()["sets"] == before["sets"]
    mixed = {"sets": {"presidents-sample": {"learned": ["e-removal-act", 5, None, "not-an-event"], "solved": {"zz": 1, "s9:0": {"checks": 1}, "s2:x": {"checks": 1}, "s2:1": {"checks": True}}}}}
    p.m.load_state(mixed)
    prog = p.m.S["sets"]["presidents-sample"]
    assert "e-removal-act" in prog["learned"] and "not-an-event" not in prog["learned"]
    assert set(prog["solved"]) == {"s1:0"}


def test_a_hostile_session_is_dropped(p):
    good = copy.deepcopy(p.m.get_state()["session"])
    puz = p.puzzle()
    bad = []
    x = copy.deepcopy(good); x["placement"] = ["e-nope", None, None]; bad.append(x)
    x = copy.deepcopy(good); x["locked"] = [True, False, False]; bad.append(x)                     # locked but empty
    x = copy.deepcopy(good); x["placement"] = [puz.tray[0], puz.tray[0], None]; bad.append(x)         # duplicate card
    x = copy.deepcopy(good); x["status"] = "solved"; bad.append(x)                                  # solved but not in order
    x = copy.deepcopy(good); x["round"] = -4; bad.append(x)
    x = copy.deepcopy(good); x["round"] = 10 ** 9; bad.append(x)
    x = copy.deepcopy(good); x["section"] = "zz"; bad.append(x)
    x = copy.deepcopy(good); x["marks"] = ["boom", None, None]; bad.append(x)
    x = copy.deepcopy(good); x["checks"] = -1; bad.append(x)
    x = copy.deepcopy(good); x["placement"] = [puz.answer[1], None, None]; x["locked"] = [True, False, False]; bad.append(x)   # locked in the WRONG slot
    for s in bad:
        assert p.m._clean_session(s) is None, s


def test_a_valid_session_resumes_mid_puzzle(p):
    puz = p.puzzle()
    p.call("place", event=puz.answer[0], slot=0)
    p.call("place", event=puz.answer[2], slot=1)
    state = copy.deepcopy(p.m.get_state())
    p.m.reset_engine()
    p.m.load_state(state)
    v = p.call("boot")["view"]["puzzle"]
    assert [s["card"] for s in v["slots"]] == [puz.answer[0], puz.answer[2], None]


def test_progress_for_a_set_this_build_lacks_is_kept_and_written_back(p):
    p.m.load_state({"sets": {"future-set": {"learned": ["a", "b"], "solved": {"s1:0": {"checks": 3}}}}})
    out = p.m.get_state()["sets"]["future-set"]
    assert out["learned"] == ["a", "b"] and out["solved"] == {"s1:0": {"checks": 3}}


def test_reset_erases_everything(p):
    p.solve()
    assert p.call("reset")["view"]["set"]["found"] == 0
    st = p.m.get_state()
    assert st["sets"]["presidents-sample"]["learned"] == [] and st["viewed"] == [] and st["achievements_earned"] == []


# ---- achievements --------------------------------------------------------------------------------------------

def test_manifest_matches_the_engine_and_is_well_formed():
    data = json.loads((GAME_DIR / "achievements.json").read_text(encoding="utf-8"))["achievements"]
    assert 8 <= len(data) <= 12
    assert [a["id"] for a in data] == achievements.IDS
    assert [(a["id"], a["label"], a["description"]) for a in data] == [tuple(x) for x in achievements.ACHIEVEMENTS]
    for a in data:
        assert re.fullmatch(r"[a-z0-9_]{1,64}", a["id"]) and a["label"].strip() and a["description"].strip()


def test_every_achievement_id_is_computed_by_the_module():
    src = (GAME_DIR / "achievements.py").read_text(encoding="utf-8")
    for aid in achievements.IDS:
        assert 'got.add("%s")' % aid in src, aid


def test_achievements_are_computed_from_state_not_stored(p):
    assert p.m.get_state()["achievements_earned"] == []
    r = p.solve()
    assert {"first_card", "first_timeline", "straight_line"} <= set(p.m.get_state()["achievements_earned"])
    assert set(r["new"]) >= {"first_card", "first_timeline", "straight_line"}
    snapshot = copy.deepcopy(p.m.get_state())
    p.m.reset_engine()
    p.m.load_state(snapshot)                          # a loaded save earns exactly what a played one did
    assert p.m.get_state()["achievements_earned"] == snapshot["achievements_earned"]


def test_straight_line_needs_a_single_check(p):
    puz = p.puzzle()
    for i, e in enumerate(puz.answer[1:] + puz.answer[:1]):
        p.call("place", event=e, slot=i)
    p.call("check")                                   # wrong first
    p.solve()
    assert "straight_line" not in p.m.get_state()["achievements_earned"]
    assert "first_timeline" in p.m.get_state()["achievements_earned"]


def test_viewing_a_doubtful_claim_earns_doubting_reader_and_five_claims_fine_print(p):
    p.m.load_state({"sets": {"presidents-sample": {"learned": ["e-gettysburg"]}}})
    r = p.call("view_claim", claim="c-e-gettysburg-tradition")
    assert "doubting_reader" in r["new"] and "fine_print" not in r["new"]
    for cid in ("c-e-gettysburg-date", "c-e-gettysburg-final-revision"):
        p.call("view_claim", claim=cid)
    p.m.load_state({"sets": {"presidents-sample": {"learned": ["e-removal-act", "e-fort-sumter"]}}})
    p.call("view_claim", claim="c-e-removal-act-date")
    r = p.call("view_claim", claim="c-e-fort-sumter-date")
    assert "fine_print" in r["new"]


def test_every_achievement_can_be_earned_in_the_sample_set(p, sample):
    """Easy to 100%: learn everything and view claims, and every achievement is earned (none is luck-gated)."""
    p.m.load_state({"sets": {"presidents-sample": {"learned": list(sample.events),
                                                    "solved": {"s1:0": {"checks": 1}, "s4:0": {"checks": 1}, "s4:1": {"checks": 1}, "s4:2": {"checks": 2}, "s2:0": {"checks": 1}}}}})
    for cid in list(sample.claims)[:6] + ["c-e-gettysburg-tradition"]:
        p.call("view_claim", claim=cid)
    earned = p.m.get_state()["achievements_earned"]
    assert earned == achievements.IDS
    v = p.call("boot")["view"]
    assert v["set"]["percent"] == 100 and v["set"]["found"] == v["set"]["total"] == 45


def test_percent_only_reaches_100_when_everything_is_found(p, sample):
    p.m.load_state({"sets": {"presidents-sample": {"learned": [e for e in sample.events if e != "c-berlin-wall"]}}})
    assert p.m.HELP.percent("presidents-sample") < 100
    p.m.load_state({"sets": {"presidents-sample": {"learned": ["c-berlin-wall"]}}})
    assert p.m.HELP.percent("presidents-sample") == 100


def test_the_save_widget_hook_is_called_after_a_load(p, monkeypatch):
    import sys
    import types
    calls = []
    fake = types.SimpleNamespace(window=types.SimpleNamespace(chronicleOnStateLoaded=lambda: calls.append(1)))
    monkeypatch.setitem(sys.modules, "js", fake)
    p.m.load_state({"schema": 1})
    assert calls == [1]
