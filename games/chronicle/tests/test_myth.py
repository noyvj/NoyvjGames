"""Milestone 5, myth or record: sorting claims by their own confidence field, with a reason from the source notes."""

import copy
import json
from pathlib import Path

import pytest

import achievements
import myth as mq
from setdata import load_set_dict

FIXTURES = Path(__file__).resolve().parent / "fixtures"
SAMPLE = "presidents-sample"
DOC, DIS, DOUBT = "documented", "disputed", "traditional-but-doubtful"


def learn_all(p, sample):
    p.m.load_state({"sets": {SAMPLE: {"learned": list(sample.events)}}})


def sort_correctly(p, sample, chapter="m1", rnd=0):
    p.call("myth_start", chapter=chapter, round=rnd)
    puz = mq.make_myth_puzzle(sample, chapter, rnd)
    for cid in puz.tray:
        p.call("myth_sort", claim=cid, bin=puz.answer[cid])
    return puz, p.call("myth_check")


# ---- the sample's claims -----------------------------------------------------------------------------------------

def test_the_sample_has_documented_disputed_and_doubtful_claims_each_with_three_sources(sample):
    levels = {}
    for c in sample.claims.values():
        levels.setdefault(c["confidence"], []).append(c["id"])
        assert len(c["sources"]) >= 3
    assert len(levels[DIS]) >= 2 and len(levels[DOUBT]) >= 3 and len(levels[DOC]) >= 20
    for cid in ("c-e-emancipation-scope", "c-e-washington-oath-words"):
        assert sample.claims[cid]["confidence"] == DOUBT and sample.claims[cid]["alternatives"]


def test_the_myth_chapter_holds_every_non_documented_event_claim(sample):
    chapter = sample.myth_chapter("m1")
    for c in sample.claims.values():
        if c["confidence"] != DOC and c["field"] != "relation":
            assert c["id"] in chapter["claims"], c["id"]
    assert {sample.claims[c]["confidence"] for c in chapter["claims"]} == {DOC, DIS, DOUBT}
    assert sample.myth_claim_ids() == chapter["claims"] and len(chapter["claims"]) == 7


def test_new_claim_wording_is_plain_and_unloaded(sample):
    import re
    for cid in ("c-e-emancipation-scope", "c-e-washington-oath-words", "c-r-sumter-emancipation", "c-r-farewell-22nd", "c-r-sputnik-apollo"):
        c = sample.claims[cid]
        for t in [c["text"]] + c.get("alternatives", []) + [r["note"] for r in c["sources"]]:
            assert "—" not in t and "–" not in t and "!" not in t
        assert not re.search(r"\b(great|worst|best|terrible|heroic|villain|tyrant|failed|disgrace|brilliant|evil|corrupt)\b", c["text"].lower())


# ---- deterministic puzzles ---------------------------------------------------------------------------------------

def test_myth_puzzles_are_pinned_by_a_fixture(sample):
    fixture = json.loads((FIXTURES / "myth_puzzles_v1.json").read_text(encoding="utf-8"))
    assert fixture["seed_version"] == mq.SEED_VERSION and len(fixture["puzzles"]) >= 7
    for code, want in fixture["puzzles"].items():
        _s, chapter, rnd = code.split("/")
        got = mq.make_myth_puzzle(sample, chapter, int(rnd))
        assert got.tray == want["tray"] and got.answer == want["answer"], code


def test_every_puzzle_is_mixed_the_right_size_and_answers_from_the_confidence_field(sample):
    for r in range(40):
        puz = mq.make_myth_puzzle(sample, "m1", r)
        assert puz.size == len(puz.tray) == 4 and len(set(puz.tray)) == 4
        kinds = {puz.answer[c] == DOC for c in puz.tray}
        assert kinds == {True, False}, (r, puz.answer)
        assert all(puz.answer[c] == sample.claims[c]["confidence"] for c in puz.tray)


def test_the_first_rounds_visit_every_claim_so_sorting_everything_is_reachable(sample):
    seen = set()
    chapter = sample.myth_chapter("m1")
    for r in range(mq.main_rounds(sample, "m1")):
        puz = mq.make_myth_puzzle(sample, "m1", r)
        assert chapter["claims"][r % len(chapter["claims"])] in puz.tray
        seen |= set(puz.tray)
    assert seen == set(chapter["claims"])


def test_the_same_inputs_give_the_same_puzzle(sample):
    assert mq.make_myth_puzzle(sample, "m1", 5).to_dict() == mq.make_myth_puzzle(sample, "m1", 5).to_dict()
    assert len({tuple(mq.make_myth_puzzle(sample, "m1", r).tray) for r in range(20)}) > 5


def test_bad_inputs_raise_value_error(sample):
    for chapter, rnd in (("zz", 0), ("m1", -1), ("m1", False), ("m1", None)):
        with pytest.raises(ValueError):
            mq.make_myth_puzzle(sample, chapter, rnd)


def test_grading(sample):
    puz = mq.make_myth_puzzle(sample, "m1", 0)
    bins = {c: puz.answer[c] for c in puz.tray}
    assert mq.grade(puz, bins)["all_right"] is True
    wrong = dict(bins)
    first = puz.tray[0]
    wrong[first] = DIS if bins[first] != DIS else DOC
    g = mq.grade(puz, wrong)
    assert g["right"] == 3 and [c["status"] for c in g["claims"]].count("wrong") == 1
    assert mq.grade(puz, {})["placed"] == 0 and {c["status"] for c in mq.grade(puz, {})["claims"]} == {"empty"}


# ---- the engine ----------------------------------------------------------------------------------------------------

def test_the_chapter_unlocks_when_the_events_behind_its_claims_are_learned(p, sample):
    v = p.call("mode", mode="myth")["view"]
    assert v["myths"][0]["unlocked"] is False and v["myth"]["locked"] is True and v["myths"][0]["missing"] == 3
    assert p.call("myth_start", chapter="m1")["ok"] is False
    p.m.load_state({"sets": {SAMPLE: {"learned": ["e-gettysburg", "e-emancipation"]}}})
    assert p.call("boot")["view"]["myths"][0]["unlocked"] is False
    p.m.load_state({"sets": {SAMPLE: {"learned": ["e-washington-oath"]}}})
    v = p.call("boot")["view"]
    assert v["myths"][0]["unlocked"] is True and v["myth"]["status"] == "playing"


def test_the_view_never_contains_the_answer_before_the_puzzle_is_done(p, sample):
    learn_all(p, sample)
    v = p.call("myth_start", chapter="m1", round=2)["view"]
    m = v["myth"]
    text = json.dumps(m)
    assert m["result"] is None and all(c["bin"] is None for c in m["claims"])
    for key in ("confidence", "alternatives", "sources", "explanation"):
        assert '"%s"' % key not in text, key
    assert [b["id"] for b in m["bins"]] == [DOC, DIS, DOUBT] and all(b["symbol"] and b["label"] for b in m["bins"])


def test_sorting_and_unsorting_and_refusals(p, sample):
    learn_all(p, sample)
    p.call("myth_start", chapter="m1", round=0)
    puz = mq.make_myth_puzzle(sample, "m1", 0)
    first = puz.tray[0]
    assert p.call("myth_sort", claim=first, bin=DIS)["view"]["myth"]["claims"][0]["bin"] == DIS
    assert p.call("myth_sort", claim=first, bin=None)["view"]["myth"]["claims"][0]["bin"] is None
    assert p.call("myth_sort", claim=first, bin="mythical")["ok"] is False
    assert p.call("myth_sort", claim="c-e-removal-act-date", bin=DOC)["ok"] is False
    assert p.call("myth_sort", claim=first)["ok"] is True                    # a missing bin clears it
    assert p.call("myth_check")["ok"] is False                              # not every claim is sorted
    assert p.call("myth_check")["error"].startswith("Sort all 4")


def test_a_wrong_check_locks_only_the_right_claims_and_never_says_the_answer(p, sample):
    learn_all(p, sample)
    p.call("myth_start", chapter="m1", round=0)
    puz = mq.make_myth_puzzle(sample, "m1", 0)
    for cid in puz.tray:
        p.call("myth_sort", claim=cid, bin=puz.answer[cid])
    victim = puz.tray[0]
    p.call("myth_sort", claim=victim, bin=DIS if puz.answer[victim] != DIS else DOC)
    r = p.call("myth_check")
    m = r["view"]["myth"]
    assert r["ok"] and m["status"] == "playing" and "3 of 4" in m["message"] and m["checks"] == 1
    assert [c["status"] for c in m["claims"]].count("right") == 3 and m["claims"][0]["status"] == "wrong" and m["result"] is None
    assert p.call("myth_sort", claim=puz.tray[1], bin=DOC)["ok"] is False          # a locked claim cannot move
    assert p.m.S["sets"][SAMPLE]["sorted"] == {c for c in puz.tray if c != victim}
    p.call("myth_sort", claim=victim, bin=puz.answer[victim])
    r = p.call("myth_check")
    assert r["view"]["myth"]["status"] == "solved" and "2 checks" in r["view"]["myth"]["message"]
    assert p.m.S["sets"][SAMPLE]["msolved"]["m1:0"] == {"checks": 2}


def test_a_solved_puzzle_explains_each_claim_from_its_own_source_notes(p, sample):
    learn_all(p, sample)
    puz, r = sort_correctly(p, sample)
    m = r["view"]["myth"]
    assert m["status"] == "solved" and m["result"]["solved"] and "one check" in m["message"]
    rows = {c["id"]: c for c in m["result"]["claims"]}
    assert set(rows) == set(puz.tray) and all(len(c["sources"]) >= 3 for c in rows.values())
    for cid, row in rows.items():
        claim = sample.claims[cid]
        notes = [ref["note"] for ref in claim["sources"]]
        assert row["confidence"] == claim["confidence"] and row["explanation"].endswith(" ".join(notes[:2]))
        assert row["explanation"].startswith({DOC: "Record", DIS: "Disputed", DOUBT: "Traditional but doubtful"}[claim["confidence"]])
    assert m["result"]["new_count"] == 4


def test_showing_the_answer_reveals_but_learns_nothing(p, sample):
    learn_all(p, sample)
    p.call("myth_start", chapter="m1", round=0)
    r = p.call("myth_show")
    m = r["view"]["myth"]
    assert m["status"] == "revealed" and m["result"]["solved"] is False and m["result"]["new_count"] == 0
    assert p.m.S["sets"][SAMPLE]["sorted"] == set() and p.m.S["sets"][SAMPLE]["msolved"] == {}
    assert p.call("myth_sort", claim=m["claims"][0]["id"], bin=DOC)["ok"] is False


def test_next_skips_solved_rounds(p, sample):
    learn_all(p, sample)
    sort_correctly(p, sample, rnd=0)
    assert p.call("myth_next")["view"]["myth"]["round"] == 1
    assert p.call("myth_start", chapter="m1")["view"]["myth"]["round"] == 1


def test_the_meter_archive_and_entries_count_sorted_claims(p, sample):
    learn_all(p, sample)
    before = p.call("boot")["view"]["set"]["found"]
    puz, _ = sort_correctly(p, sample)
    assert p.call("boot")["view"]["set"]["found"] == before + 4
    a = p.call("archive")["archive"]
    group = next(g for g in a["groups"] if g["id"] == "records")
    assert len(group["entries"]) == 7 and sum(1 for e in group["entries"] if e["found"]) == 4
    found = next(e for e in group["entries"] if e["id"] == "c-e-washington-oath-words" and e["found"]) if "c-e-washington-oath-words" in puz.tray else next(e for e in group["entries"] if e["found"])
    assert found["title"] and found["date_label"]
    hidden = next(e for e in group["entries"] if not e["found"])
    assert hidden["title"] is None and hidden["hint"] == "Myth or record"
    assert p.call("entry", id=hidden["id"])["ok"] is False
    e = p.call("entry", id=found["id"])["entry"]
    assert e["kind"] == "record" and e["claim"]["explanation"] and len(e["claim"]["sources"]) >= 3


def test_sorting_everything_is_reachable_and_earns_the_achievements(p, sample):
    learn_all(p, sample)
    for r in range(mq.main_rounds(sample, "m1")):
        sort_correctly(p, sample, rnd=r)
    assert p.m.S["sets"][SAMPLE]["sorted"] == set(sample.myth_claim_ids())
    earned = set(p.m.get_state()["achievements_earned"])
    assert {"first_sort", "myth_spotter", "straight_sort", "fair_judge"} <= earned
    assert all(c["cleared"] for c in p.call("boot")["view"]["myths"])


def test_myth_spotter_needs_a_doubtful_claim_and_straight_sort_a_single_check(p, sample):
    learn_all(p, sample)
    p.m.load_state({"sets": {SAMPLE: {"sorted": ["c-e-gettysburg-date"], "myth_solved": {"m1:0": {"checks": 3}}}}})
    earned = set(p.m.get_state()["achievements_earned"])
    assert "first_sort" in earned and not ({"myth_spotter", "straight_sort", "fair_judge"} & earned)
    p.m.load_state({"sets": {SAMPLE: {"sorted": ["c-e-gettysburg-tradition"], "myth_solved": {"m1:1": {"checks": 1}}}}})
    assert {"myth_spotter", "straight_sort"} <= set(p.m.get_state()["achievements_earned"])


# ---- save and load -------------------------------------------------------------------------------------------------

def test_sorted_claims_and_the_session_round_trip(p, sample):
    learn_all(p, sample)
    puz = mq.make_myth_puzzle(sample, "m1", 0)
    p.call("myth_start", chapter="m1", round=0)
    for cid in puz.tray[:3]:
        p.call("myth_sort", claim=cid, bin=puz.answer[cid])
    p.call("myth_sort", claim=puz.tray[3], bin=DOC if puz.answer[puz.tray[3]] != DOC else DIS)
    p.call("myth_check")
    state = copy.deepcopy(p.m.get_state())
    assert json.loads(json.dumps(state)) == state and state["settings"]["mode"] == "myth"
    assert len(state["sets"][SAMPLE]["sorted"]) == 3 and state["myth_session"]["checks"] == 1
    p.m.reset_engine()
    p.m.load_state(state)
    assert p.m.get_state() == state
    m = p.call("boot")["view"]["myth"]
    assert m["checks"] == 1 and [c["status"] for c in m["claims"]].count("right") == 3


def test_load_state_filters_sorted_and_records(p, sample):
    p.m.load_state({"sets": {SAMPLE: {"sorted": ["c-e-gettysburg-date", "c-r-sputnik-apollo", "nope", 4], "myth_solved": {"m1:0": {"checks": 2}, "m1:1": {"checks": 0}, "m9:0": {"checks": 1}, "m1:2": {"checks": "1"}}}}})
    prog = p.m.S["sets"][SAMPLE]
    assert prog["sorted"] == {"c-e-gettysburg-date"} and prog["msolved"] == {"m1:0": {"checks": 2}}
    p.m.load_state({"sets": {SAMPLE: {"myth_solved": {"m1:0": {"checks": 1}}}}})
    p.m.load_state({"sets": {SAMPLE: {"myth_solved": {"m1:0": {"checks": 9}}}}})
    assert prog["msolved"]["m1:0"] == {"checks": 1}


def test_a_hostile_myth_session_is_dropped(p, sample):
    learn_all(p, sample)
    puz = mq.make_myth_puzzle(sample, "m1", 0)
    p.call("myth_start", chapter="m1", round=0)
    good = copy.deepcopy(p.m.get_state()["myth_session"])
    assert p.m._clean_msession(good) is not None
    bad = []
    for key, value in (("bins", ["zz", None, None, None]), ("bins", [None, None]), ("locked", [True, False, False, False]), ("locked", ["x", False, False, False]),
                       ("marks", ["boom", None, None, None]), ("round", -1), ("round", 10 ** 9), ("chapter", "zz"), ("set", "zz"), ("status", "won"),
                       ("checks", -1), ("checks", True)):
        x = copy.deepcopy(good); x[key] = value; bad.append(x)
    x = copy.deepcopy(good); x["status"] = "solved"; bad.append(x)                              # solved but nothing locked
    x = copy.deepcopy(good)
    wrong = DIS if puz.answer[puz.tray[0]] != DIS else DOC
    x["bins"][0] = wrong; x["locked"][0] = True; bad.append(x)                                  # locked in the WRONG bin
    x = copy.deepcopy(good)
    x["bins"][0] = puz.answer[puz.tray[0]]; x["locked"][0] = True; bad.append(x)                # locked but never earned (sorted is empty)
    for s in bad:
        assert p.m._clean_msession(s) is None, s


def test_a_locked_chapter_session_is_dropped(p):
    p.m.load_state({"myth_session": {"set": SAMPLE, "chapter": "m1", "round": 0, "bins": [None] * 4, "locked": [False] * 4, "marks": [None] * 4,
                                     "checks": 0, "status": "playing", "new": [], "message": ""}})
    assert p.m.S["msession"] is None


def test_the_achievement_manifest_has_nineteen_all_computed_and_described(sample):
    assert len(achievements.IDS) == 19
    data = json.loads((Path(__file__).resolve().parent.parent / "achievements.json").read_text(encoding="utf-8"))["achievements"]
    assert [a["id"] for a in data] == achievements.IDS
    for aid in ("first_thread", "clean_web", "whole_web", "first_sort", "myth_spotter", "straight_sort", "fair_judge"):
        assert aid in achievements.IDS


def test_a_set_with_no_chapters_can_still_reach_100_percent(g, raw):
    raw.pop("chapters")
    raw["meta"]["id"] = "plain"
    raw["relations"] = []
    raw["claims"] = [c for c in raw["claims"] if c["field"] != "relation"]
    cset = load_set_dict(raw)
    g.register_set(cset)
    g._prog("plain")["learned"] |= set(cset.events)
    assert g.HELP.percent("plain") == 100 and g._counts("plain")[1] == len(cset.events) + len(cset.people) + len(cset.places)
