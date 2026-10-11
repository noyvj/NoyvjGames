"""The hint ladder (each rung opens only on a press, free, never touching a medal), the three goals, and the last two drawers."""

import json

import achievements
import cases
import game
import hints
import lang


def call(**req):
    return json.loads(game.handle(json.dumps(req)))


def fresh():
    game.game.__init__()


def test_the_ladder_starts_closed_and_each_press_opens_exactly_one_rung():
    fresh()
    v = call(action="open")
    assert v["hint"] == {"rung": 0, "nudge": "", "hint": None, "answer": None}
    v = call(action="hint")
    assert v["hint"]["rung"] == 1 and v["hint"]["nudge"] and v["hint"]["hint"] is None and v["tally"]["hints"] == 1
    assert "is even" not in v["hint"]["nudge"] and "Latch" not in v["hint"]["nudge"]
    v = call(action="hint")
    assert v["hint"]["rung"] == 2 and v["hint"]["hint"]["item"] == cases.BY_ID["latch"].shortest[0] and v["hint"]["answer"] is None
    v = call(action="hint")
    assert v["hint"]["rung"] == 3 and v["hint"]["answer"]["words"] == cases.BY_ID["latch"].words
    assert lang.agree("num", lang.parse_rule("num", v["hint"]["answer"]["rule"]), cases.BY_ID["latch"].rule)
    v = call(action="hint")
    assert v["ok"] is False and v["tally"]["hints"] == 3


def test_hints_never_touch_a_medal_a_name_or_a_test_and_do_not_name_the_case():
    fresh()
    for _ in range(3):
        call(action="hint")
    v = call(action="open")
    assert v["tally"]["tests"] == 0 and v["totals"]["named"] == 0 and v["case"]["tests"] == 0 and v["case"]["status"] == "open"
    named = call(action="name", rule=v["hint"]["answer"]["rule"])
    assert named["verdict"]["kind"] == "named" and named["verdict"]["medal"] == "gold"      # the player still presses Name it


def test_the_hint_item_moves_on_when_it_has_been_sent_and_says_when_nothing_is_left():
    fresh()
    c = cases.BY_ID["latch"]
    call(action="hint")
    call(action="hint")
    for k in c.shortest:
        v = call(action="open")
        assert v["hint"]["hint"]["item"] == k
        call(action="test", item=k)
    v = call(action="open")
    assert v["hint"]["hint"]["item"] == "" and "seen enough" in v["hint"]["hint"]["text"]


def test_rungs_are_per_case_and_saved_and_loaded_checked():
    fresh()
    call(action="hint")
    call(action="pick", case="hinge")
    assert call(action="open")["hint"]["rung"] == 0
    call(action="hint")
    call(action="hint")
    state = json.loads(json.dumps(game.get_state()))
    assert state["rungs"] == {"latch": 1, "hinge": 2}
    fresh()
    game.load_state(state)
    assert game.game.rungs == {"latch": 1, "hinge": 2}
    game.load_state({"rungs": {"latch": 9, "hinge": 0, "pane": "x", "ghost": 1, "lever": True, "spring": 3}})
    assert game.game.rungs == {"spring": 3}


def test_every_nudge_names_a_kind_of_property_but_never_the_clause():
    for c in cases.ALL_CASES:
        text = hints.nudge_text(c)
        assert text.endswith(".") and len(text) < 160
        for cid in c.rule.lits:
            assert lang.domain(c.kind).clause_by_id[cid[0]].yes not in text


def test_there_are_always_three_goals_and_each_is_a_real_achievement_with_a_count():
    fresh()
    v = call(action="open")
    assert len(v["goals"]) == 3 and [g["id"] for g in v["goals"]] == ["first_gate", "eight_named", "twenty_four"]
    assert all(g["need"] >= 1 and g["have"] == 0 for g in v["goals"])
    assert len(v["achievements"]) == len(achievements.ACHIEVEMENTS) == 14
    game.game._enter("latch")
    call(action="name", rule=lang.rule_json(cases.BY_ID["latch"].rule))
    v = call(action="open")
    assert v["goals"][0]["id"] == "eight_named" and v["goals"][0]["have"] == 1 and len(v["goals"]) == 3


def test_the_odd_gate_is_one_surprising_exception_that_the_shortest_path_must_test():
    drawer = [d for d in cases.DRAWER_LIST if d["id"] == "odd"][0]
    assert len(drawer["cases"]) == 8
    for c in drawer["cases"]:
        dom = c.domain
        base = dom.table(c.rule.lits[0][0])
        if c.rule.lits[0][1]:
            base = dom.full ^ base
        diff = c.table ^ base
        assert bin(diff).count("1") == 1, c.id
        exception = dom.items[diff.bit_length() - 1]
        assert exception in c.shortest, "%s: the exception %s is not on the shortest path" % (c.id, exception)
        assert exception not in c.examples


def test_the_patterns_drawer_uses_the_grid_domain_throughout():
    drawer = [d for d in cases.DRAWER_LIST if d["id"] == "patterns"][0]
    assert len(drawer["cases"]) == 8 and all(c.kind == "grid" for c in drawer["cases"])
    assert [d["id"] for d in cases.DRAWER_LIST] == ["numbers", "shapes", "two", "not", "patterns", "odd"]
    assert len(cases.ORDER) == 48
