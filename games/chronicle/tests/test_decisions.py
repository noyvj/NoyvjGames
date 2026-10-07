"""Milestone 7 (part one), decision points: a choice someone really faced, then what they chose and what followed."""

import copy
import json
import re
from pathlib import Path

import pytest

import decision as dc
from setdata import load_set_dict, validate

from .conftest import strip_extras

FIXTURES = Path(__file__).resolve().parent / "fixtures"
SAMPLE = "presidents-sample"
LOADED = {"great", "worst", "best", "terrible", "heroic", "villain", "tyrant", "failed", "disgrace", "brilliant", "evil", "corrupt",
          "mistake", "blunder", "should", "ought", "wrong", "right", "better", "wise", "unwise", "foolish"}


def codes(files):
    return {p.split(":", 1)[0] for p in validate(files)}


def learn_all(p, sample):
    p.m.load_state({"sets": {SAMPLE: {"learned": list(sample.events)}}})


def pick(p, did, option):
    p.call("decision_start", decision=did)
    return p.call("decision_pick", option=option)


# ---- the sample's decisions: each part is a sourced claim --------------------------------------------------------------

def test_the_sample_has_three_decisions_each_with_three_sourced_parts(sample):
    assert [d["id"] for d in sample.decisions] == ["d-sumter", "d-louisiana", "d-term"]
    for d in sample.decisions:
        assert d["event"] in sample.events and 2 <= len(d["options"]) <= 4
        assert d["chosen"] in {o["id"] for o in d["options"]}
        assert set(d["claims"]) == {"options", "choice", "after"}
        for part, cid in d["claims"].items():
            c = sample.claims[cid]
            assert c["field"] == "decision" and c["value"] == "%s:%s" % (d["id"], part) and c["subject"] == d["event"]
            assert c["confidence"] == "documented" and len(c["sources"]) >= 3
            refs = sample.resolved_sources(c)
            assert len({r["url"] for r in refs}) == len(refs) and len({r["institution"] for r in refs}) >= 2
            assert all(r["url"].startswith("https://") and r["read"] in ("2026-10-07", "2026-10-08") and r["note"] for r in refs)


def test_what_they_chose_is_always_one_of_the_documented_options(sample):
    texts = {"d-sumter": "supply", "d-louisiana": "proceed", "d-term": "serve"}
    for d in sample.decisions:
        assert d["chosen"] == texts[d["id"]]


def test_decision_wording_is_neutral_and_never_alternate_history(sample):
    for d in sample.decisions:
        pieces = [d["title"], d["question"]] + [o["text"] for o in d["options"]]
        pieces += [sample.claims[c]["text"] for c in d["claims"].values()]
        for c in d["claims"].values():
            pieces += [ref["note"] for ref in sample.claims[c]["sources"]]
        for t in pieces:
            assert "—" not in t and "–" not in t and "!" not in t, t
            assert not (set(re.findall(r"[a-z]+", t.lower())) & LOADED), (d["id"], t, set(re.findall(r"[a-z]+", t.lower())) & LOADED)
            assert not re.search(r"\b(would have|could have been|might have|had he|what if)\b", t.lower()), t


def test_the_options_claim_does_not_give_away_the_choice(sample):
    for d in sample.decisions:
        text = sample.claims[d["claims"]["options"]]["text"].lower()
        assert not re.search(r"\b(chose|decided|dropped|submitted|ordered)\b", text), d["id"]


def test_only_the_three_decision_events_are_the_ones_the_sources_document(sample):
    assert {d["event"] for d in sample.decisions} == {"e-fort-sumter", "e-louisiana", "e-farewell"}


# ---- validation ----------------------------------------------------------------------------------------------------

def test_the_sample_with_decisions_is_valid(raw):
    assert validate(raw) == []


def decision(raw, did="d-sumter"):
    return next(d for d in raw["decisions"]["decisions"] if d["id"] == did)


@pytest.mark.parametrize("mutate,code", [
    (lambda d: d.update(chosen="nope"), "E_DECISION_OPTIONS"),
    (lambda d: d.update(options=d["options"][:1]), "E_DECISION_OPTIONS"),
    (lambda d: d.update(options=d["options"] + d["options"]), "E_DECISION_OPTIONS"),
    (lambda d: d.update(event="e-nope"), "E_DECISION"),
    (lambda d: d.update(who=""), "E_DECISION"),
    (lambda d: d.update(title=""), "E_DECISION"),
    (lambda d: d.update(claims={"options": "c-d-sumter-options"}), "E_DECISION_CLAIM"),
    (lambda d: d["claims"].update(after="no-such-claim"), "E_DECISION_CLAIM"),
    (lambda d: d["claims"].update(after="c-e-fort-sumter-date"), "E_DECISION_CLAIM"),       # not a decision claim
    (lambda d: d["claims"].update(choice="c-d-louisiana-choice"), "E_DECISION_CLAIM"),      # another decision's claim
])
def test_bad_decisions_fail(raw, mutate, code):
    mutate(decision(raw))
    assert code in codes(raw)


def test_a_decision_part_must_have_three_sources(raw):
    next(c for c in raw["claims"] if c["id"] == "c-d-sumter-choice")["sources"].pop()
    assert "E_CLAIM_SOURCES" in codes(raw)


def test_a_decision_part_must_be_documented_and_about_the_event(raw):
    claim = next(c for c in raw["claims"] if c["id"] == "c-d-term-after")
    claim["confidence"] = "disputed"
    claim["alternatives"] = ["Another reading."]
    assert "E_DECISION_CLAIM" in codes(raw)
    raw2 = copy.deepcopy(raw)
    next(c for c in raw2["claims"] if c["id"] == "c-d-term-after")["subject"] = "e-gettysburg"
    assert "E_DECISION_CLAIM" in codes(raw2)


def test_a_stray_decision_claim_or_a_missing_file_fails(raw):
    raw["decisions"]["decisions"] = raw["decisions"]["decisions"][:2]
    assert "E_DECISION_CLAIM" in codes(raw)
    raw2 = copy.deepcopy(raw)
    raw2.pop("decisions")
    assert "E_DECISION_CLAIM" in codes(raw2)


def test_malformed_decisions_file_is_reported_not_raised(raw):
    for junk in ([], {"decisions": "x"}, {"decisions": [5]}, {"decisions": [{"id": "x"}]}, {"other": 1}):
        raw["decisions"] = junk
        assert codes(raw)


def test_a_set_without_decisions_is_valid_and_has_no_decision_mode(raw):
    strip_extras(raw)
    assert validate(raw) == []
    assert load_set_dict(raw).decisions == []


# ---- deterministic option order --------------------------------------------------------------------------------------

def test_option_orders_are_pinned_and_hold_every_option_once(sample):
    fixture = json.loads((FIXTURES / "decision_orders_v1.json").read_text(encoding="utf-8"))
    assert fixture["seed_version"] == dc.SEED_VERSION
    for d in sample.decisions:
        order = dc.option_order(sample, d["id"])
        assert order == fixture["puzzles"][d["id"]] and sorted(order) == sorted(o["id"] for o in d["options"])
        assert order == dc.option_order(sample, d["id"])
    with pytest.raises(ValueError):
        dc.option_order(sample, "zz")


# ---- the engine ------------------------------------------------------------------------------------------------------

def test_a_decision_is_locked_until_its_moment_is_learned(p, sample):
    v = p.call("mode", mode="decision")["view"]
    assert v["decision"]["locked"] is True and [d["unlocked"] for d in v["decisions"]] == [False, False, False]
    assert p.call("decision_start", decision="d-sumter")["ok"] is False
    assert p.call("decision_start", decision="zz")["ok"] is False
    p.m.load_state({"sets": {SAMPLE: {"learned": ["e-louisiana"]}}})
    v = p.call("boot")["view"]
    assert [d["unlocked"] for d in v["decisions"]] == [False, True, False] and v["decision"]["id"] == "d-louisiana"


def test_before_the_pick_the_view_shows_the_situation_and_options_but_not_the_choice(p, sample):
    learn_all(p, sample)
    v = p.call("mode", mode="decision")["view"]["decision"]
    text = json.dumps(v)
    assert v["decided"] is False and v["picked"] is None and v["result"] is None
    assert v["situation"]["id"] == "c-d-sumter-options" and len(v["situation"]["sources"]) >= 3
    assert sorted(o["id"] for o in v["options"]) == ["reinforce", "supply", "withdraw"] and not any(o["picked"] for o in v["options"])
    for secret in ("c-d-sumter-choice", "c-d-sumter-after", '"chosen"', "4:30 a.m.", "provisions only"):
        assert secret not in text, secret


def test_picking_shows_what_they_chose_and_what_followed_and_labels_it_honestly(p, sample):
    learn_all(p, sample)
    r = pick(p, "d-sumter", "withdraw")
    v = r["view"]["decision"]
    res = v["result"]
    assert r["ok"] and v["decided"] and v["picked"] == "withdraw" and res["same"] is False and res["chosen"] == "supply"
    assert res["chose_label"] == "What Abraham Lincoln chose" and res["after_label"] == "What followed"
    assert res["choice_claim"]["id"] == "c-d-sumter-choice" and res["after_claim"]["id"] == "c-d-sumter-after"
    for c in (res["choice_claim"], res["after_claim"], v["situation"]):
        assert len(c["sources"]) >= 3 and c["confidence_label"] == "Documented"
    assert "There is no right answer" in res["note"] and "would have happened otherwise" in res["note"]
    assert "You chose differently from Abraham Lincoln" in res["note"]
    assert p.m.S["sets"][SAMPLE]["decided"]["d-sumter"] == {"picked": "withdraw"}


def test_choosing_what_they_chose_says_so(p, sample):
    learn_all(p, sample)
    res = pick(p, "d-louisiana", "proceed")["view"]["decision"]["result"]
    assert res["same"] is True and "matches what Thomas Jefferson chose" in res["note"]


def test_a_choice_is_made_once_and_nothing_is_graded(p, sample):
    learn_all(p, sample)
    pick(p, "d-term", "retire")
    again = p.call("decision_pick", option="serve")
    assert again["ok"] is False and "already made your choice" in again["error"]
    assert p.m.S["sets"][SAMPLE]["decided"]["d-term"] == {"picked": "retire"}
    assert p.call("decision_pick", option="nope")["ok"] is False
    wrong_view = json.dumps(p.call("boot")["view"]["decision"])
    assert "correct" not in wrong_view and '"right"' not in wrong_view and "score" not in wrong_view


def test_picking_before_any_decision_is_open_is_an_error(p):
    assert p.call("mode", mode="decision")["ok"] is True
    assert p.call("decision_pick", option="supply")["ok"] is False


def test_decision_claims_open_in_stages(p, sample):
    learn_all(p, sample)
    assert p.call("view_claim", claim="c-d-sumter-options")["ok"] is True
    assert p.call("view_claim", claim="c-d-sumter-choice")["ok"] is False
    assert p.call("view_claim", claim="c-d-sumter-after")["ok"] is False
    pick(p, "d-sumter", "supply")
    assert p.call("view_claim", claim="c-d-sumter-choice")["ok"] is True
    assert p.call("view_claim", claim="c-d-louisiana-choice")["ok"] is False
    p.m.S["sets"][SAMPLE]["learned"].clear()
    assert p.call("view_claim", claim="c-d-sumter-options")["ok"] is False


def test_the_archive_meter_counts_the_choices_and_lists_them(p, sample):
    learn_all(p, sample)
    before = p.call("boot")["view"]["set"]["found"]
    pick(p, "d-sumter", "supply")
    assert p.call("boot")["view"]["set"]["found"] == before + 1
    group = next(g for g in p.call("archive")["archive"]["groups"] if g["id"] == "choices")
    assert [e["found"] for e in group["entries"]] == [True, False, False] and group["entries"][0]["title"] == "Fort Sumter, spring 1861"
    assert all(e["title"] is None and e["hint"] == "Decision points" for e in group["entries"][1:])
    entry = p.call("entry", id="d-sumter")["entry"]
    assert entry["kind"] == "decision" and entry["decision"]["result"]["chosen"] == "supply"
    assert p.call("entry", id="d-louisiana")["ok"] is False


def test_decision_claims_never_appear_in_the_plain_event_reveal(p, sample):
    learn_all(p, sample)
    pick(p, "d-sumter", "supply")
    entry = p.call("entry", id="e-fort-sumter")["entry"]
    assert [c["id"] for c in [entry["claim"]] + entry["other_claims"]] == ["c-e-fort-sumter-date"]


def test_the_info_page_lists_the_choices_made(p, sample):
    learn_all(p, sample)
    assert p.call("info")["info"]["found_decisions"] == []
    pick(p, "d-sumter", "supply")
    pick(p, "d-term", "serve")
    found = p.call("info")["info"]["found_decisions"]
    assert [d["id"] for d in found] == ["d-sumter", "d-term"] and all(d["result"]["same"] for d in found)


def test_decision_achievements(p, sample):
    learn_all(p, sample)
    pick(p, "d-sumter", "withdraw")
    earned = set(p.m.get_state()["achievements_earned"])
    assert "first_decision" in earned and "every_crossroads" not in earned
    pick(p, "d-louisiana", "amend")
    r = pick(p, "d-term", "retire")
    assert "every_crossroads" in r["new"]


# ---- save and load -----------------------------------------------------------------------------------------------------

def test_choices_round_trip_and_never_replace_a_first_choice(p, sample):
    learn_all(p, sample)
    pick(p, "d-sumter", "withdraw")
    state = copy.deepcopy(p.m.get_state())
    assert state["sets"][SAMPLE]["decided"] == {"d-sumter": {"picked": "withdraw"}} and state["decision_session"] == {"set": SAMPLE, "decision": "d-sumter"}
    p.m.reset_engine()
    p.m.load_state(state)
    assert p.m.get_state()["sets"] == state["sets"]
    p.m.load_state({"sets": {SAMPLE: {"decided": {"d-sumter": {"picked": "supply"}}}}})
    assert p.m.S["sets"][SAMPLE]["decided"]["d-sumter"] == {"picked": "withdraw"}


def test_bad_choices_and_sessions_are_dropped(p, sample):
    learn_all(p, sample)
    p.m.load_state({"sets": {SAMPLE: {"decided": {"d-sumter": {"picked": "nope"}, "zz": {"picked": "x"}, "d-term": "serve", "d-louisiana": {"picked": 5}}}}})
    assert p.m.S["sets"][SAMPLE]["decided"] == {}
    for bad in (None, 5, [], {"set": "zz", "decision": "d-sumter"}, {"set": SAMPLE, "decision": "zz"}, {"set": SAMPLE}):
        assert p.m._clean_dsession(bad) is None
    assert p.m._clean_dsession({"set": SAMPLE, "decision": "d-sumter"}) == {"set": SAMPLE, "decision": "d-sumter"}
    p.m.S["sets"][SAMPLE]["learned"].clear()
    assert p.m._clean_dsession({"set": SAMPLE, "decision": "d-sumter"}) is None        # locked again


def test_choosing_a_set_resets_the_open_decision_to_the_first_unmade_one(p, sample):
    learn_all(p, sample)
    p.call("decision_start", decision="d-term")
    assert p.m.S["dsession"]["decision"] == "d-term"
    p.call("choose_set", set=SAMPLE)
    assert p.call("boot")["view"]["decision"]["id"] == "d-sumter"
