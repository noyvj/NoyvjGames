import json

import cases
import game
import lang


def call(**req):
    return json.loads(game.handle(json.dumps(req)))


def fresh():
    game.game.__init__()


def rule(*lits, ops=()):
    return {"lits": [list(x) for x in lits], "ops": list(ops)}


def name_it(case_id, text=None):
    c = cases.BY_ID[case_id]
    r = lang.parse_rule(c.kind, text or c.rule_text)
    return call(action="name", rule=lang.rule_json(r))


def test_open_returns_the_whole_view_with_the_menu_once():
    fresh()
    v = call(action="open")
    assert v["case"]["id"] == cases.ORDER[0] and v["case"]["status"] == "open" and v["menu"]
    assert v["totals"] == {"cases": len(cases.ORDER), "named": 0, "clean": 0, "drawers": len(cases.DRAWER_LIST), "drawers_closed": 0}
    assert v["tally"] == {"tests": 0, "near": 0, "hints": 0} and v["last"] is None and v["verdict"] is None
    assert "menu" not in call(action="preview", rule=rule(("even", 0)))
    assert "menu" in call(action="open")
    first = cases.BY_ID[cases.ORDER[0]]
    assert [e["item"] for e in v["case"]["log"]] == list(first.yes + first.no)
    assert [e["src"] for e in v["case"]["log"]] == ["given"] * len(first.examples)


def test_every_case_in_every_drawer_is_open_from_the_start():
    fresh()
    for cid in cases.ORDER:
        v = call(action="pick", case=cid)
        assert v["ok"] and v["case"]["id"] == cid and "menu" in v
    assert all("open" not in x and "need" not in x for d in call(action="open")["cases"] for x in d["cases"])


def test_a_new_test_counts_once_and_the_answer_is_the_hidden_rules():
    fresh()
    c = cases.BY_ID["latch"]
    v = call(action="test", item="12")
    assert v["ok"] and v["last"] == {"item": "12", "yes": True, "repeat": False, "label": "12"}
    assert v["tally"]["tests"] == 1 and v["case"]["tests"] == 1
    v = call(action="test", item=7)
    assert v["last"]["yes"] is False and v["tally"]["tests"] == 2
    assert [e["item"] for e in v["case"]["log"]][-2:] == ["12", "7"]
    for n in range(0, 100):
        assert call(action="test", item=str(n))["last"]["yes"] == c.accepts(str(n))


def test_sending_an_item_you_have_already_seen_is_free():
    fresh()
    c = cases.BY_ID["latch"]
    given = c.yes[0]
    v = call(action="test", item=given)
    assert v["last"]["repeat"] is True and v["last"]["yes"] is True and v["tally"]["tests"] == 0 and v["case"]["tests"] == 0
    call(action="test", item="30")
    v = call(action="test", item="030")
    assert v["last"]["repeat"] is True and v["tally"]["tests"] == 1


def test_bad_items_and_bad_requests_are_refused_without_breaking_the_game():
    fresh()
    for bad in ("", "abc", -1, 100, 3.5, None, True, [1], "1e2", "٣", "   "):
        v = call(action="test", item=bad)
        assert v["ok"] is False and v["message"], bad
    assert call(action="test")["ok"] is False
    assert call(action="pick", case="nope")["ok"] is False and call(action="pick", case=5)["ok"] is False
    assert call(action="name", rule="nope")["ok"] is False and call(action="name")["ok"] is False
    assert call(action="name", rule=rule(("nope", 0)))["ok"] is False
    assert call(action="name", rule=rule(("even", 0), ("ge:50", 0), ops=("and",)))["ok"] is False      # more clauses than this drawer uses
    assert "error" in call(action="dance")
    assert json.loads(game.handle("not json")) == {"error": "bad request"}
    assert json.loads(game.handle("[1]")) == {"error": "bad request"}
    assert call(action="open")["tally"]["tests"] == 0


def test_preview_changes_nothing_and_reports_words_and_conflicts():
    fresh()
    before = json.dumps(game.get_state(), sort_keys=True)
    v = call(action="preview", rule=rule(("even", 0)))
    assert v["draft"]["valid"] and v["draft"]["words"] == "A number goes Through if it is even." and v["draft"]["conflict"] is None
    v = call(action="preview", rule=rule(("mult:5", 0)))
    assert v["draft"]["conflict"]["sorter"] in ("Through", "Stopped") and v["draft"]["conflict"]["rule"] != v["draft"]["conflict"]["sorter"]
    assert call(action="preview", rule=rule(("nope", 0)))["draft"] == {"valid": False, "words": "", "conflict": None}
    assert json.dumps(game.get_state(), sort_keys=True) == before


def test_a_rule_that_contradicts_what_you_have_seen_is_not_a_near_miss():
    fresh()
    v = name_it("latch", "mult:5")
    assert v["ok"] is False and v["verdict"]["kind"] == "conflict" and v["tally"]["near"] == 0
    assert v["case"]["free"] == 0 and v["totals"]["named"] == 0


def test_a_wrong_rule_that_fits_everything_shows_one_free_counter_example():
    fresh()
    c = cases.BY_ID["latch"]
    wrong = lang.parse_rule("num", "ge:30")                # agrees with every starting example of Latch
    assert all(lang.rule_accepts("num", wrong, k) == c.accepts(k) for k in c.examples) and not lang.agree("num", wrong, c.rule)
    v = call(action="name", rule=lang.rule_json(wrong))
    assert v["ok"] and v["verdict"]["kind"] == "near" and v["tally"]["near"] == 1 and v["tally"]["tests"] == 0
    cf = v["verdict"]["conflict"]
    assert c.accepts(cf["item"]) != lang.rule_accepts("num", wrong, cf["item"])
    assert cf["sorter"] == ("Through" if c.accepts(cf["item"]) else "Stopped")
    assert v["case"]["free"] == 1 and v["case"]["tests"] == 0
    assert v["case"]["log"][-1] == {"item": cf["item"], "yes": c.accepts(cf["item"]), "src": "free", "label": cf["label"]}
    assert v["totals"]["named"] == 0 and "latch" not in game.game.named
    again = call(action="name", rule=lang.rule_json(wrong))
    assert again["verdict"]["kind"] == "conflict"            # the counter-example is now in the log
    assert again["tally"]["near"] == 1


def test_the_right_rule_names_the_case():
    fresh()
    call(action="test", item="12")
    v = name_it("latch")
    assert v["verdict"]["kind"] == "named" and v["verdict"]["first"] and v["verdict"]["tests"] == 1
    assert v["case"]["status"] == "named" and v["case"]["best"] == 1 and v["case"]["medal"] == "gold"
    assert v["totals"]["named"] == 1 and v["totals"]["clean"] == 1 and v["verdict"]["next"] == "hinge"
    assert v["case"]["words"] == "A number goes Through if it is even." and v["case"]["line"]
    call(action="pick", case="hinge")
    assert name_it("hinge")["verdict"]["kind"] == "named"


def test_a_rule_that_is_equal_on_every_item_is_accepted_even_if_the_words_differ():
    fresh()
    game.game._enter("spring")
    v = call(action="name", rule=rule(("mult:3", 0)))
    assert v["verdict"]["kind"] == "named"
    fresh()
    game.game._enter("spring")
    assert call(action="name", rule=rule(("mult:9", 0)))["verdict"]["kind"] in ("near", "conflict")


def test_naming_again_only_improves_the_best_and_keeps_the_rule_of_the_best():
    fresh()
    for n in ("12", "14", "16"):
        call(action="test", item=n)
    v = name_it("latch")
    assert v["case"]["best"] == 3 and v["verdict"]["improved"] is False and v["verdict"]["first"] is True
    v = call(action="restart")
    assert v["ok"] and v["case"]["tests"] == 0 and v["case"]["best"] == 3 and v["case"]["status"] == "named"
    call(action="test", item="12")
    v = name_it("latch")
    assert v["case"]["best"] == 1 and v["verdict"]["improved"] is True and v["totals"]["named"] == 1
    for n in ("20", "22", "24", "26"):
        call(action="test", item=n)
    v = name_it("latch")
    assert v["case"]["best"] == 1 and v["verdict"]["improved"] is False       # a worse count never lowers the best


def test_restart_needs_a_named_case_and_keeps_the_tally():
    fresh()
    v = call(action="restart")
    assert v["ok"] is False
    call(action="test", item="12")
    name_it("latch")
    v = call(action="restart")
    assert v["tally"]["tests"] == 1 and v["case"]["log"][-1]["src"] == "given"


def test_a_near_miss_before_naming_is_remembered_for_the_case():
    fresh()
    wrong = lang.parse_rule("num", "ge:30")
    call(action="name", rule=lang.rule_json(wrong))
    name_it("latch")
    assert game.game.named["latch"]["m"] == 1
    fresh()
    name_it("latch")
    assert game.game.named["latch"]["m"] == 0


def test_next_goes_to_the_next_case_not_yet_named_and_says_when_none_is_left():
    fresh()
    assert call(action="next")["case"]["id"] == cases.ORDER[1]
    call(action="pick", case=cases.ORDER[0])
    name_it(cases.ORDER[0])
    assert call(action="next")["case"]["id"] == cases.ORDER[1]
    for cid in cases.ORDER:
        game.game.named[cid] = {"t": 1, "r": cases.BY_ID[cid].rule_text, "m": 0}
    v = call(action="next")
    assert v["ok"] is False


def test_the_picker_view_lists_every_case_with_its_state():
    fresh()
    name_it("latch")
    v = call(action="open")
    drawer = v["cases"][0]
    assert drawer["name"] == "Number Gates" and drawer["named"] == 1 and drawer["total"] == 8 and drawer["max_clauses"] == 1
    assert [x["id"] for x in drawer["cases"]] == [c.id for c in cases.DRAWER_LIST[0]["cases"]]
    assert drawer["cases"][0]["named"] and drawer["cases"][0]["medal"] == "gold" and drawer["cases"][0]["current"]
    assert not drawer["cases"][1]["named"] and drawer["cases"][1]["best"] is None


def test_reset_starts_over():
    fresh()
    call(action="test", item="12")
    name_it("latch")
    v = call(action="reset")
    assert v["totals"]["named"] == 0 and v["tally"]["tests"] == 0 and game.get_state() == {}
