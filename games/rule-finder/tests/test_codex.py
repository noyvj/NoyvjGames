"""The Rule Codex and the wall map: pages fill when a case is named and count as read when opened."""

import json
import re

import cases
import codex
import game
import lang
import render


def call(**req):
    return json.loads(game.handle(json.dumps(req)))


def fresh():
    game.game.__init__()


def name_it(cid):
    game.game._enter(cid)
    return call(action="name", rule=lang.rule_json(cases.BY_ID[cid].rule))


def test_a_page_is_empty_until_its_case_is_named_and_then_it_is_filled_not_yet_read():
    fresh()
    v = call(action="open")
    assert v["page"] is None and all(not e["filled"] and not e["read"] for e in v["codex"]) and len(v["codex"]) == len(cases.ORDER)
    assert call(action="page", case="latch")["ok"] is False and call(action="page", case="nope")["ok"] is False and call(action="page", case=4)["ok"] is False
    v = name_it("latch")
    entry = [e for e in v["codex"] if e["id"] == "latch"][0]
    assert entry["filled"] and not entry["read"] and v["totals"]["pages"] == 1 and v["totals"]["read"] == 0


def test_opening_a_page_shows_the_rule_the_family_and_the_shortest_path_and_counts_as_read():
    fresh()
    name_it("latch")
    v = call(action="page", case="latch")
    p = v["page"]
    c = cases.BY_ID["latch"]
    assert p["words"] == c.words and p["families"] == ["Odd and even"] and p["clauses"] == 1
    assert [t["item"] for t in p["shortest"]] == list(c.shortest) and all(t["yes"] == c.accepts(t["item"]) for t in p["shortest"])
    assert p["par"] == c.par and p["best"] == 0 and p["medal"] == "gold" and p["line"] == c.line and p["rule_used"] == c.words
    assert v["totals"]["read"] == 1 and [e for e in v["codex"] if e["id"] == "latch"][0]["read"]
    assert call(action="pick", case="hinge")["page"] is None                  # going to another case closes the page


def test_the_shortest_path_proves_the_rule_with_the_starting_examples():
    for c in cases.ALL_CASES:
        fresh()
        name_it(c.id)
        p = call(action="page", case=c.id)["page"]
        assert len(p["shortest"]) == len(c.shortest) >= 1 and p["kind"] == c.kind


def test_reading_is_saved_only_for_named_cases_and_loads_back_checked():
    fresh()
    name_it("latch")
    call(action="page", case="latch")
    state = game.get_state()
    assert state["read"] == ["latch"]
    fresh()
    game.load_state(json.loads(json.dumps(state)))
    assert game.get_state() == state
    fresh()
    game.load_state({"named": {"latch": {"t": 1, "r": "even"}}, "read": ["latch", "hinge", "ghost", 5, None, "latch"]})
    assert game.get_state()["read"] == ["latch"]
    game.load_state({"read": ["latch"]})
    assert "read" not in game.get_state()
    game.load_state({"read": "latch"})
    assert game.get_state() == {}


def test_every_page_read_is_what_the_full_codex_achievement_will_count():
    fresh()
    for c in cases.ALL_CASES:
        name_it(c.id)
        assert call(action="page", case=c.id)["ok"]
    t = call(action="open")["totals"]
    assert t["pages"] == t["read"] == t["cases"] == len(cases.ORDER)
    assert codex.counts(game.game.named, game.game.read) == {"filled": len(cases.ORDER), "read": len(cases.ORDER), "total": len(cases.ORDER)}


def test_the_wall_map_has_a_cubby_per_case_with_state_in_shape_and_words():
    fresh()
    name_it("latch")
    v = call(action="open")
    svg = v["map"]
    assert svg.startswith("<svg") and svg.count('class="rf-slot') == len(cases.ORDER)
    assert svg.count('role="button" tabindex="0"') == len(cases.ORDER)
    assert 'data-id="latch"' in svg and "cubby-tick" in svg and svg.count("cubby-tick") == 1 and 'class="pip gold"' in svg
    assert "not named yet" in svg and "named, gold medal" in svg
    assert svg.count("rf-slot s1") == 1 and svg.count("current") == 1
    for d in cases.DRAWER_LIST:
        assert d["name"] in svg
    assert not re.search(r"<script|onclick", svg)


def test_the_wall_pads_short_drawers_and_escapes_text():
    drawers = [{"id": "x", "name": 'A <b> "drawer"', "named": 0, "total": 1,
                "cases": [{"id": "a&b", "name": "<i>", "number": 1, "named": False, "medal": "", "current": False}]}]
    svg = render.wall_svg(drawers)
    assert "<b>" not in svg and "&lt;b&gt;" in svg and "&amp;" in svg and svg.count("empty-slot") == render.SLOTS - 1
