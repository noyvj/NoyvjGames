"""Milestone 4, the cause web: sourced relations, chapters, deterministic puzzles, judging threads, honest strength."""

import copy
import json
from pathlib import Path

import pytest

import web as wb
from setdata import load_set_dict, validate

FIXTURES = Path(__file__).resolve().parent / "fixtures"
SAMPLE = "presidents-sample"


def codes(files):
    return {p.split(":", 1)[0] for p in validate(files)}


def claim(raw, cid):
    return next(c for c in raw["claims"] if c["id"] == cid)


def learn_all(p, sample):
    p.m.load_state({"sets": {SAMPLE: {"learned": list(sample.events)}}})


# ---- the sample set's relations ----------------------------------------------------------------------------------

def test_the_sample_has_sourced_relations_with_the_cause_effect_convention(sample):
    assert len(sample.relations) == 3
    for r in sample.relations:
        c = sample.claims[r["claim"]]
        assert c["field"] == "relation" and c["subject"] == r["to"] and c["value"] == "%s>%s" % (r["from"], r["to"])
        assert r["strength"] in ("direct", "contributing") and r["type"] == "led_to"
        refs = sample.resolved_sources(c)
        assert len(refs) >= 3 and len({x["institution"] for x in refs}) >= 2
        assert len({x["url"] for x in refs}) == len(refs)
        assert all(x["read"] in ("2026-10-07", "2026-10-08") and x["note"] for x in refs)


def test_a_disputed_relation_shows_its_alternatives(sample):
    c = sample.claims["c-r-farewell-22nd"]
    assert c["confidence"] == "disputed" and len(c["alternatives"]) == 2


def test_relation_claims_do_not_leak_into_an_events_other_claims(p, sample):
    learn_all(p, sample)
    full = p.call("entry", id="e-22nd-amendment")["entry"]
    assert all(c["field"] != "relation" for c in full["other_claims"])
    info = p.call("info")["info"]
    assert all(c["field"] != "relation" for f in info["found_claims"] for c in f["claims"])


# ---- validation rules ----------------------------------------------------------------------------------------------

def test_a_relation_claim_must_name_its_pair_and_its_effect(raw):
    claim(raw, "c-r-sputnik-apollo")["value"] = "c-apollo>c-sputnik"
    assert "E_RELATION_CLAIM" in codes(raw)
    raw2 = copy.deepcopy(raw)
    claim(raw2, "c-r-sputnik-apollo")["value"] = "c-sputnik>c-apollo"
    claim(raw2, "c-r-sputnik-apollo")["subject"] = "c-sputnik"
    assert "E_RELATION_CLAIM" in codes(raw2)


def test_two_relations_cannot_share_one_claim_and_an_orphan_relation_claim_fails(raw):
    raw["relations"][1]["claim"] = raw["relations"][0]["claim"]
    found = validate(raw)
    assert any(x.startswith("E_RELATION_CLAIM") and "each relation needs its own claim" in x for x in found)
    assert any("no relation uses it" in x for x in found)


def test_several_causes_of_one_effect_are_allowed(raw):
    extra = copy.deepcopy(claim(raw, "c-r-sumter-emancipation"))
    extra.update({"id": "c-r-removal-emancipation", "value": "e-removal-act>e-emancipation"})
    raw["claims"].append(extra)
    raw["relations"].append({"id": "r-removal-emancipation", "from": "e-removal-act", "to": "e-emancipation", "type": "led_to",
                             "strength": "direct", "claim": "c-r-removal-emancipation"})
    assert validate(raw) == []                 # same subject and field, different cause: not a contradiction
    cset = load_set_dict(raw)
    assert cset.causes_of("e-emancipation") == ["r-sumter-emancipation", "r-removal-emancipation"]


def test_repeating_the_same_relation_is_a_contradiction(raw):
    extra = copy.deepcopy(claim(raw, "c-r-sumter-emancipation"))
    extra["id"] = "c-r-again"
    raw["claims"].append(extra)
    raw["relations"].append({"id": "r-again", "from": "e-fort-sumter", "to": "e-emancipation", "type": "led_to", "strength": "direct", "claim": "c-r-again"})
    assert "E_CONTRADICTION" in codes(raw)


def test_a_relation_claim_needs_three_sources_like_any_claim(raw):
    claim(raw, "c-r-sumter-emancipation")["sources"] = claim(raw, "c-r-sumter-emancipation")["sources"][:2]
    assert "E_CLAIM_SOURCES" in codes(raw)


def test_a_relation_cycle_is_rejected(raw):
    raw["claims"].append(dict(copy.deepcopy(claim(raw, "c-r-sumter-emancipation")), id="c-r-back", subject="e-fort-sumter", value="e-emancipation>e-fort-sumter"))
    raw["relations"].append({"id": "r-back", "from": "e-emancipation", "to": "e-fort-sumter", "type": "led_to", "strength": "direct", "claim": "c-r-back"})
    assert {"E_RELATION_CONTRADICTION", "E_RELATION_ORDER"} <= codes(raw)


def test_a_relation_in_no_web_chapter_is_unreachable(raw):
    raw["chapters"]["web"] = [raw["chapters"]["web"][1]]
    assert "E_CHAPTER_UNREACHABLE" in codes(raw)


def test_chapter_rules_each_fail_a_bad_set(raw):
    def mutated(fn):
        files = copy.deepcopy(raw)
        fn(files["chapters"])
        return codes(files)

    assert "E_CHAPTER" in mutated(lambda c: c["web"][0].update(size=2))
    assert "E_CHAPTER" in mutated(lambda c: c["web"][0].update(size=7))
    assert "E_CHAPTER" in mutated(lambda c: c["web"][0].update(events=["e-nope"] + c["web"][0]["events"]))
    assert "E_CHAPTER" in mutated(lambda c: c["web"][0].update(id="W bad"))
    assert "E_CHAPTER" in mutated(lambda c: c["web"].append(dict(c["web"][0])))              # duplicate id
    assert "E_CHAPTER" in mutated(lambda c: c.update(extra=[]))
    assert "E_CHAPTER_EMPTY" in mutated(lambda c: c["web"][1].update(events=["c-bastille", "c-waterloo", "c-berlin-wall"]))
    assert "E_CHAPTER" in mutated(lambda c: c["myth"][0].update(claims=c["myth"][0]["claims"] + ["c-r-sputnik-apollo"]))   # relation claim
    assert "E_CHAPTER" in mutated(lambda c: c["myth"][0].update(claims=[x for x in c["myth"][0]["claims"] if x != "c-e-gettysburg-date"] + ["nope"]))
    assert "E_CHAPTER_MIX" in mutated(lambda c: c["myth"][0].update(claims=["c-e-gettysburg-tradition", "c-e-emancipation-scope", "c-e-washington-oath-words", "c-e-gettysburg-final-revision"]))
    assert "E_CHAPTER_UNREACHABLE" in mutated(lambda c: c["myth"][0].update(claims=[x for x in c["myth"][0]["claims"] if x != "c-e-emancipation-scope"]))


def test_a_set_without_chapters_is_still_valid_and_has_neither_mechanic(raw):
    raw.pop("chapters")
    cset = load_set_dict(raw)
    assert cset.web_chapters == [] and cset.myth_chapters == [] and cset.web_relation_ids() == []


def test_a_chapter_claim_without_a_short_name_fails(raw):
    del claim(raw, "c-e-gettysburg-date")["short"]
    assert "E_CHAPTER" in codes(raw)


# ---- deterministic puzzles ---------------------------------------------------------------------------------------

def test_web_puzzles_are_pinned_by_a_fixture(sample):
    fixture = json.loads((FIXTURES / "web_puzzles_v1.json").read_text(encoding="utf-8"))
    assert fixture["seed_version"] == wb.SEED_VERSION
    assert len(fixture["puzzles"]) >= 8
    for code, want in fixture["puzzles"].items():
        _s, chapter, rnd = code.split("/")
        got = wb.make_web_puzzle(sample, chapter, int(rnd))
        assert got.cards == want["cards"] and got.relations == want["relations"], code


def test_the_same_inputs_give_the_same_puzzle_and_other_inputs_can_differ(sample):
    a = wb.make_web_puzzle(sample, "w1", 3).to_dict()
    assert a == wb.make_web_puzzle(sample, "w1", 3).to_dict()
    assert len({tuple(wb.make_web_puzzle(sample, "w1", r).cards) for r in range(12)}) > 2


def test_the_first_rounds_visit_every_relation_and_cards_are_in_date_order(sample):
    for chapter in sample.web_chapters:
        rels = sample.chapter_relations(chapter)
        seen = set()
        for r in range(wb.main_rounds(sample, chapter["id"])):
            puz = wb.make_web_puzzle(sample, chapter["id"], r)
            anchor = sample.relation_by_id[rels[r % len(rels)]]
            assert anchor["id"] in puz.relations and anchor["from"] in puz.cards and anchor["to"] in puz.cards
            years = [sample.events[c]["date"] for c in puz.cards]
            assert years == sorted(years)
            assert puz.size == len(puz.cards) == chapter["size"] and set(puz.cards) <= set(chapter["events"])
            seen |= set(puz.relations)
        assert seen == set(rels)


def test_every_relation_between_the_cards_is_part_of_the_puzzle(sample):
    for r in range(30):
        puz = wb.make_web_puzzle(sample, "w1", r)
        want = [x["id"] for x in sample.relations if x["from"] in puz.cards and x["to"] in puz.cards]
        assert puz.relations == want


def test_bad_inputs_raise_value_error(sample):
    for chapter, rnd in (("zz", 0), ("w1", -1), ("w1", True), ("w1", "1")):
        with pytest.raises(ValueError):
            wb.make_web_puzzle(sample, chapter, rnd)


def test_judging_a_thread(sample):
    puz = wb.make_web_puzzle(sample, "w1", 0)
    assert puz.relations == ["r-sumter-emancipation"]
    assert wb.judge(sample, puz, "e-fort-sumter", "e-emancipation") == {"verdict": "confirmed", "relation": "r-sumter-emancipation"}
    assert wb.judge(sample, puz, "e-emancipation", "e-fort-sumter")["verdict"] == "reversed"
    other = next(c for c in puz.cards if c not in ("e-fort-sumter", "e-emancipation"))
    assert wb.judge(sample, puz, "e-fort-sumter", other)["verdict"] == "unconfirmed"
    assert wb.judge(sample, puz, "e-fort-sumter", "e-fort-sumter")["verdict"] == "invalid"
    assert wb.judge(sample, puz, "e-fort-sumter", "c-bastille")["verdict"] == "invalid"


# ---- the engine ----------------------------------------------------------------------------------------------------

def test_chapters_unlock_when_every_moment_they_use_is_learned(p, sample):
    v = p.call("mode", mode="web")["view"]
    assert [w["unlocked"] for w in v["webs"]] == [False, False]
    assert v["web"]["locked"] is True and "Find" in v["web"]["message"]
    assert v["webs"][0]["missing"] == 7 and "7 more moments" in v["webs"][0]["requires_text"]
    assert p.call("web_start", chapter="w1")["ok"] is False
    p.m.load_state({"sets": {SAMPLE: {"learned": [e for e in sample.events if e != "c-berlin-wall"]}}})
    v = p.call("boot")["view"]
    assert [w["unlocked"] for w in v["webs"]] == [True, False] and v["webs"][1]["missing"] == 1
    p.m.load_state({"sets": {SAMPLE: {"learned": ["c-berlin-wall"]}}})
    assert [w["unlocked"] for w in p.call("boot")["view"]["webs"]] == [True, True]


def test_the_view_does_not_reveal_a_link_before_it_is_found(p, sample):
    learn_all(p, sample)
    v = p.call("web_start", chapter="w1", round=0)["view"]
    text = json.dumps(v["web"])
    assert v["web"]["found"] == [] and v["web"]["result"] is None and v["web"]["links_total"] == 1
    for cid in ("c-r-sumter-emancipation", "r-sumter-emancipation", "Antietam"):
        assert cid not in text
    assert all("claim" not in c for c in v["web"]["cards"])


def test_a_confirmed_thread_names_its_strength_and_is_learned(p, sample):
    learn_all(p, sample)
    p.call("web_start", chapter="w1", round=0)
    r = p.call("web_link", **{"from": "e-fort-sumter", "to": "e-emancipation"})
    assert r["ok"] and r["dirty"] and "Confirmed" in r["view"]["web"]["message"] and "contributing cause" in r["view"]["web"]["message"]
    t = r["view"]["web"]["found"][0]
    assert t["strength"] == "contributing" and t["strength_label"] == "Contributing cause" and t["strength_symbol"] == "⇢"
    assert len(t["claim"]["sources"]) >= 3 and t["claim"]["confidence"] == "documented"
    assert "only cause" in t["plural_note"] and t["n_causes"] == 1
    assert p.m.S["sets"][SAMPLE]["threads"] == {"r-sumter-emancipation"}
    assert r["view"]["web"]["status"] == "solved" and "first_thread" in r["new"]


def test_a_disputed_link_is_confirmed_with_its_disputed_label(p, sample):
    learn_all(p, sample)
    p.call("web_start", chapter="w1", round=1)
    r = p.call("web_link", **{"from": "e-farewell", "to": "e-22nd-amendment"})
    t = r["view"]["web"]["found"][0]
    assert t["claim"]["confidence"] == "disputed" and t["claim"]["alternatives"] and t["claim"]["symbol"] == "≈"


def test_wrong_and_reversed_threads_are_not_confirmed_and_count_as_misses(p, sample):
    learn_all(p, sample)
    p.call("web_start", chapter="w1", round=0)
    r = p.call("web_link", **{"from": "e-emancipation", "to": "e-fort-sumter"})
    assert r["ok"] and "other way" in r["view"]["web"]["message"] and r["view"]["web"]["misses"] == 1
    other = next(c["id"] for c in r["view"]["web"]["cards"] if c["id"] not in ("e-fort-sumter", "e-emancipation"))
    r = p.call("web_link", **{"from": "e-fort-sumter", "to": other})
    assert "Not confirmed" in r["view"]["web"]["message"] and "does not mean they are unrelated" in r["view"]["web"]["message"]
    assert [t["verdict"] for t in r["view"]["web"]["tries"]] == ["reversed", "unconfirmed"]
    assert p.m.S["sets"][SAMPLE]["threads"] == set()
    r = p.call("web_link", **{"from": "e-fort-sumter", "to": "e-emancipation"})
    assert r["view"]["web"]["status"] == "solved"
    assert p.m.S["sets"][SAMPLE]["wsolved"]["w1:0"] == {"misses": 2}
    assert "clean_web" not in r["new"]


def test_a_clean_puzzle_earns_clean_web_and_fewer_misses_are_kept(p, sample):
    learn_all(p, sample)
    p.call("web_start", chapter="w1", round=0)
    r = p.call("web_link", **{"from": "e-fort-sumter", "to": "e-emancipation"})
    assert "clean_web" in r["new"] and p.m.S["sets"][SAMPLE]["wsolved"]["w1:0"] == {"misses": 0}
    p.m.load_state({"sets": {SAMPLE: {"web_solved": {"w1:0": {"misses": 5}}}}})
    assert p.m.S["sets"][SAMPLE]["wsolved"]["w1:0"] == {"misses": 0}


def test_bad_links_are_refused_and_a_finished_puzzle_is_closed(p, sample):
    learn_all(p, sample)
    p.call("web_start", chapter="w1", round=0)
    assert p.call("web_link", **{"from": "e-fort-sumter", "to": "e-fort-sumter"})["ok"] is False
    assert p.call("web_link", **{"from": "e-fort-sumter", "to": "c-bastille"})["ok"] is False
    assert p.call("web_link", **{"from": "e-fort-sumter"})["ok"] is False
    p.call("web_link", **{"from": "e-fort-sumter", "to": "e-emancipation"})
    assert p.call("web_link", **{"from": "e-fort-sumter", "to": "e-emancipation"})["ok"] is False
    assert p.call("web_show")["ok"] is False


def test_showing_the_links_reveals_but_learns_nothing(p, sample):
    learn_all(p, sample)
    p.call("web_start", chapter="w1", round=0)
    r = p.call("web_show")
    assert r["view"]["web"]["status"] == "revealed" and r["view"]["web"]["result"]["solved"] is False
    assert [t["relation"] for t in r["view"]["web"]["result"]["threads"]] == ["r-sumter-emancipation"]
    assert p.m.S["sets"][SAMPLE]["threads"] == set() and p.m.S["sets"][SAMPLE]["wsolved"] == {}
    assert p.call("view_claim", claim="c-r-sumter-emancipation")["ok"]      # a revealed puzzle's claims can be opened for their sources
    assert p.call("view_claim", claim="c-r-farewell-22nd")["ok"] is False


def test_next_moves_to_a_round_with_a_link_still_to_find(p, sample):
    learn_all(p, sample)
    p.call("web_start", chapter="w1", round=0)
    p.call("web_link", **{"from": "e-fort-sumter", "to": "e-emancipation"})
    v = p.call("web_next")["view"]
    assert v["web"]["round"] == 1 and v["web"]["status"] == "playing"
    assert p.call("web_start", chapter="w1")["view"]["web"]["round"] == 1       # the default round skips solved ones


def test_one_of_several_causes_is_shown_honestly(g, raw):
    extra = copy.deepcopy(next(c for c in raw["claims"] if c["id"] == "c-r-sumter-emancipation"))
    extra.update({"id": "c-r-removal-emancipation", "value": "e-removal-act>e-emancipation"})
    raw["claims"].append(extra)
    raw["relations"].append({"id": "r-removal-emancipation", "from": "e-removal-act", "to": "e-emancipation", "type": "led_to",
                             "strength": "direct", "claim": "c-r-removal-emancipation"})
    cset = load_set_dict(raw)
    g.register_set(cset)
    g.SETS[cset.id] = cset
    view = g._thread_view(cset, "r-sumter-emancipation")
    assert view["n_causes"] == 2 and view["plural_note"] == "One of 2 causes of this moment that the set records."
    direct = g._thread_view(cset, "r-removal-emancipation")
    assert direct["strength_label"] == "Direct cause" and direct["strength_symbol"] == "⇒" and "immediate trigger" in direct["strength_note"]


def test_the_meter_archive_and_entries_count_the_links(p, sample):
    a = p.call("archive")["archive"]
    group = next(g for g in a["groups"] if g["id"] == "connections")
    assert len(group["entries"]) == 3 and all(not e["found"] and e["title"] is None and e["hint"] == "Cause web" for e in group["entries"])
    assert p.call("entry", id="r-sumter-emancipation")["ok"] is False
    learn_all(p, sample)
    before = p.call("boot")["view"]["set"]["found"]
    p.call("web_start", chapter="w1", round=0)
    p.call("web_link", **{"from": "e-fort-sumter", "to": "e-emancipation"})
    v = p.call("boot")["view"]
    assert v["set"]["found"] == before + 1
    a = p.call("archive")["archive"]
    entry = next(e for g in a["groups"] if g["id"] == "connections" for e in g["entries"] if e["found"])
    assert entry["title"] == "Confederate guns open fire on Fort Sumter led to Lincoln signs the Emancipation Proclamation" and entry["date_label"] == "Contributing cause"
    e = p.call("entry", id="r-sumter-emancipation")["entry"]
    assert e["kind"] == "relation" and len(e["thread"]["claim"]["sources"]) >= 3


def test_the_info_page_lists_found_links_with_strength_legend_and_coverage(p, sample):
    info = p.call("info")["info"]
    assert [s["id"] for s in info["strengths"]] == ["direct", "contributing"] and info["found_relations"] == []
    assert info["counts"]["relations"] == 3 and info["coverage"]["total"] == 28
    learn_all(p, sample)
    p.call("web_start", chapter="w1", round=0)
    p.call("web_link", **{"from": "e-fort-sumter", "to": "e-emancipation"})
    info = p.call("info")["info"]
    assert [t["relation"] for t in info["found_relations"]] == ["r-sumter-emancipation"]
    assert all(len(t["claim"]["sources"]) >= 3 for t in info["found_relations"])
    assert info["coverage"]["shown"] > 20 and "of 28 claims" in info["coverage"]["note"]


def test_claim_views_name_their_institutions(p, sample):
    learn_all(p, sample)
    v = p.call("info")["info"]["found_claims"][0]["claims"][0]
    assert v["institutions"] and v["institutions"] == sorted(set(v["institutions"]))


def test_the_whole_web_is_reachable_and_earns_its_achievements(p, sample):
    learn_all(p, sample)
    for chapter in sample.web_chapters:
        for r in range(wb.main_rounds(sample, chapter["id"])):
            p.call("web_start", chapter=chapter["id"], round=r)
            for rid in wb.make_web_puzzle(sample, chapter["id"], r).relations:
                rel = sample.relation_by_id[rid]
                p.call("web_link", **{"from": rel["from"], "to": rel["to"]})
    assert p.m.S["sets"][SAMPLE]["threads"] == set(sample.web_relation_ids())
    earned = p.m.get_state()["achievements_earned"]
    assert {"first_thread", "clean_web", "whole_web"} <= set(earned)
    assert all(w["cleared"] for w in p.call("boot")["view"]["webs"])


# ---- save and load -------------------------------------------------------------------------------------------------

def test_threads_and_the_session_round_trip_through_the_save(p, sample):
    learn_all(p, sample)
    p.call("web_start", chapter="w1", round=1)
    p.call("web_link", **{"from": "e-farewell", "to": "e-22nd-amendment"})
    p.call("web_start", chapter="w1", round=0)
    p.call("web_link", **{"from": "e-fort-sumter", "to": "e-farewell"})
    state = copy.deepcopy(p.m.get_state())
    assert json.loads(json.dumps(state)) == state and state["settings"]["mode"] == "web"
    assert state["sets"][SAMPLE]["threads"] == ["r-farewell-22nd"] and state["web_session"]["misses"] == 1
    p.m.reset_engine()
    p.m.load_state(state)
    assert p.m.get_state() == state
    v = p.call("boot")["view"]
    assert v["mode"] == "web" and v["web"]["round"] == 0 and v["web"]["misses"] == 1


def test_load_state_filters_threads_and_records(p, sample):
    p.m.load_state({"sets": {SAMPLE: {"learned": list(sample.events), "threads": ["r-sumter-emancipation", "nope", 5, None, "e-fort-sumter"],
                                       "web_solved": {"w1:0": {"misses": 1}, "zz:0": {"misses": 1}, "w1:x": {"misses": 1}, "w1:1": {"misses": -4}, "w1:2": {"misses": True}}}}})
    prog = p.m.S["sets"][SAMPLE]
    assert prog["threads"] == {"r-sumter-emancipation"} and prog["wsolved"] == {"w1:0": {"misses": 1}}


def test_a_hostile_web_session_is_dropped(p, sample):
    learn_all(p, sample)
    p.call("web_start", chapter="w1", round=0)
    good = copy.deepcopy(p.m.get_state()["web_session"])
    p.call("web_link", **{"from": "e-fort-sumter", "to": "e-emancipation"})
    solved = copy.deepcopy(p.m.get_state()["web_session"])
    assert p.m._clean_wsession(solved) is not None
    bad = []
    for key, value in (("found", ["r-farewell-22nd"]), ("found", ["nope"]), ("found", ["r-sumter-emancipation", "r-sumter-emancipation"]),
                       ("round", -1), ("round", 10 ** 9), ("round", True), ("chapter", "zz"), ("set", "zz"), ("status", "won"),
                       ("misses", -1), ("misses", "3"), ("tries", "x"), ("tries", [{"from": "e-nope", "to": "e-farewell", "verdict": "unconfirmed"}]),
                       ("tries", [{"from": "e-farewell", "to": "e-fort-sumter", "verdict": "confirmed"}])):
        x = copy.deepcopy(good)
        x[key] = value
        bad.append(x)
    x = copy.deepcopy(good); x["status"] = "solved"; bad.append(x)                    # solved without every link
    x = copy.deepcopy(solved); p.m.S["sets"][SAMPLE]["threads"].clear(); bad.append(x)  # a found link the player never earned
    for s in bad:
        assert p.m._clean_wsession(s) is None, s


def test_a_locked_chapter_session_is_dropped_and_progress_for_unknown_sets_is_kept(p, sample):
    p.m.load_state({"web_session": {"set": SAMPLE, "chapter": "w1", "round": 0, "found": [], "tries": [], "misses": 0, "status": "playing", "message": ""}})
    assert p.m.S["wsession"] is None                    # nothing is learned yet, so w1 is locked
    p.m.load_state({"sets": {"future-set": {"learned": ["a"], "threads": ["r1", 4], "sorted": ["c1"]}}})
    out = p.m.get_state()["sets"]["future-set"]
    assert out["threads"] == ["r1"] and out["sorted"] == ["c1"]


def test_garbage_in_the_new_fields_never_raises(p, sample):
    for junk in ({"web_session": 5}, {"myth_session": []}, {"settings": {"mode": "zz"}}, {"sets": {SAMPLE: {"threads": "x", "sorted": 3, "web_solved": [], "myth_solved": 7}}}):
        p.m.load_state(junk)
    assert p.m.get_state()["settings"]["mode"] == "timeline"


def test_the_mode_setting_is_validated_and_a_set_without_the_mechanic_falls_back(p, g, raw):
    assert p.call("mode", mode="zz")["ok"] is False
    assert p.call("mode", mode="web")["view"]["mode"] == "web"
    raw.pop("chapters")
    raw["meta"]["id"] = "plain"
    g.register_set(load_set_dict(raw))
    g.S["settings"]["set"] = "plain"
    g.S["session"] = None
    v = p.call("boot")["view"]
    assert v["mode"] == "timeline" and [m["available"] for m in v["modes"]] == [True, False, False]
    assert p.call("mode", mode="web")["ok"] is False
