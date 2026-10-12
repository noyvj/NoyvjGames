"""The engine's actions and what the view may and may not show."""

import json

import pytest

import game as game_module
import lessons
import why


@pytest.fixture(autouse=True)
def fresh():
    game_module.handle(json.dumps({"action": "reset"}))
    yield
    game_module.handle(json.dumps({"action": "reset"}))


def do(**request):
    return json.loads(game_module.handle(json.dumps(request)))


def set_switches(lid, wanted):
    """Toggle until exactly `wanted` features are on (current lesson must be `lid`)."""
    view = do(action="open")
    for f in view["lesson"]["features"]:
        if f["on"] != (f["id"] in wanted):
            view = do(action="toggle", feature=f["id"])
    return view


def clear(lid, with_set=None):
    do(action="pick", lesson=lid)
    set_switches(lid, set(with_set or lessons.BY_ID[lid]["best"]))
    do(action="train")
    return do(action="test")


def clear_shelf(s, count=8):
    for l in lessons.SHELVES[s]["lessons"][:count]:
        view = clear(l["id"])
        assert view["lesson"]["cleared"], l["id"]


def test_a_fresh_view_opens_on_lesson_one_with_the_starting_switches():
    v = do(action="open")
    l = v["lesson"]
    assert l["id"] == lessons.ORDER[0] and l["number"] == 1 and l["of"] == 8 and l["shelf"] == "Sorting Basics"
    assert [f["id"] for f in l["features"] if f["on"]] == lessons.BY_ID[l["id"]]["start"]
    assert not l["trained"] and l["tree"] is None and l["result"] is None and l["why"] is None
    assert v["totals"]["cleared"] == 0 and v["totals"]["lessons"] == 24 and v["totals"]["shelves_open"] == 1


def test_the_view_is_plain_json_and_hides_the_unseen_cases_and_the_answers():
    v = do(action="open")
    text = json.dumps(v)
    for l in lessons.ALL:
        assert l["learned"] not in text
    for c in lessons.BY_ID[lessons.ORDER[0]]["test_cases"]:
        assert '"%s"' % c["name"] not in text and '"%s"' % c["id"] not in text, c["name"]     # the unseen table stays out until a test is taken
    assert not any('"%s":' % k in text for k in ("needs", "golden", "mislabelled", "shortcuts", "best_score", "seed"))
    assert v["lesson"]["unseen"] == 20 and len(v["lesson"]["train"]) == 16


def test_training_cases_show_every_feature_and_say_which_ones_pip_can_see():
    v = set_switches(lessons.ORDER[0], {"glow"})
    row = v["lesson"]["train"][0]
    assert [c["feature"] for c in row["chips"]] == ["glow", "stripes", "weight"]
    assert [c["on"] for c in row["chips"]] == [True, False, False]
    assert all(": " in c["text"] for c in row["chips"]) and row["answer"] in ("Ripe", "Not yet")


def test_train_and_test_need_each_other_and_a_feature():
    assert not do(action="test")["ok"]
    set_switches(lessons.ORDER[0], set())
    v = do(action="train")
    assert not v["ok"] and "at least one" in v["message"]
    set_switches(lessons.ORDER[0], {"glow"})
    v = do(action="train")
    assert v["ok"] and v["lesson"]["trained"] and v["lesson"]["tree"] and v["lesson"]["train_score"]["total"] == 16
    assert "Press Test" in v["message"] and v["lesson"]["lamp"]["state"] == "trained"


def test_changing_a_switch_throws_the_tree_and_the_test_away():
    do(action="train")
    do(action="test")
    v = do(action="toggle", feature="stripes")
    assert not v["lesson"]["trained"] and v["lesson"]["tree"] is None and v["lesson"]["result"] is None and v["lesson"]["lamp"]["state"] == "idle"
    assert "Press Train" in v["say"]
    assert not do(action="toggle", feature="nope")["ok"] and not do(action="toggle", feature=3)["ok"]


def test_reset_switches_goes_back_to_the_start():
    lid = "friendly-signals"
    do(action="pick", lesson=lid)
    assert [f["id"] for f in do(action="open")["lesson"]["features"] if f["on"]] == ["gap"]
    set_switches(lid, {"pulses", "tone", "gap"})
    v = do(action="reset_switches")
    assert [f["id"] for f in v["lesson"]["features"] if f["on"]] == ["gap"] and v["lesson"]["at_start"]


def test_a_test_shows_every_unseen_case_marked_right_or_wrong_in_words():
    do(action="pick", lesson="friendly-signals")
    do(action="train")
    v = do(action="test")
    r = v["lesson"]["result"]
    assert r["total"] == 20 and len(r["cases"]) == 20 and r["need"] == 18
    assert r["right"] == sum(1 for c in r["cases"] if c["right"]) and not r["passed"]
    for c in r["cases"]:
        assert c["pip"] in v["lesson"]["bins"] and c["truth"] in v["lesson"]["bins"] and c["right"] == (c["pip"] == c["truth"])
        assert not c["explained"] and len(c["chips"]) == 3
    assert v["lesson"]["lamp"]["state"] == "puzzled" and "Why" in v["message"]
    assert not v["lesson"]["cleared"] and v["just"] is None


def test_clearing_a_lesson_with_the_best_features_earns_the_best_mark():
    v = clear("safe-doors")
    assert v["lesson"]["cleared"] and v["just"]["first"] and v["just"]["best"] and v["lesson"]["best_mark"]
    assert v["lesson"]["learned"] == lessons.BY_ID["safe-doors"]["learned"] and v["lesson"]["cleared_with"] == ["Door heat"]
    assert v["totals"]["cleared"] == 1 and v["totals"]["best_marks"] == 1 and v["lesson"]["lamp"]["state"] == "pleased"
    shelf = v["shelves"][0]["lessons"][1]
    assert shelf["cleared"] and shelf["best"]


def test_a_clear_with_more_features_has_no_best_mark_until_it_is_cleared_again_with_the_best_set():
    v = clear("ripe-crates", with_set=["glow", "stripes", "weight"])
    assert v["lesson"]["cleared"] and not v["lesson"]["best_mark"] and v["totals"]["best_marks"] == 0
    v = clear("ripe-crates", with_set=["glow"])
    assert v["lesson"]["best_mark"] and v["totals"]["cleared"] == 1 and v["totals"]["best_marks"] == 1 and not v["just"]["first"]
    v = clear("ripe-crates", with_set=["glow", "stripes"])            # clearing again with something else never takes the mark away
    assert v["lesson"]["best_mark"] and v["totals"]["best_marks"] == 1


def test_a_failed_test_never_takes_anything_away():
    clear("ripe-crates")
    do(action="pick", lesson="ripe-crates")
    set_switches("ripe-crates", {"weight"})
    do(action="train")
    v = do(action="test")
    assert not v["lesson"]["result"]["passed"] and v["lesson"]["cleared"] and v["totals"]["cleared"] == 1 and v["lesson"]["best_mark"]


def test_the_why_panel_opens_on_a_wrong_answer_only_and_counts_once():
    do(action="pick", lesson="friendly-signals")
    do(action="train")
    v = do(action="test")
    wrong = [c for c in v["lesson"]["result"]["cases"] if not c["right"]]
    right = [c for c in v["lesson"]["result"]["cases"] if c["right"]]
    assert not do(action="why", case=right[0]["id"])["ok"] and not do(action="why", case="nope")["ok"]
    v = do(action="why", case=wrong[0]["id"])
    assert v["ok"] and v["lesson"]["why"]["case"] == wrong[0]["id"] and v["totals"]["whys"] == 1
    assert v["lesson"]["why"]["category"] in why.CATEGORY_IDS and v["lesson"]["why"]["steps"] is not None
    assert "Failure Notebook" in v["message"] and v["totals"]["notebook"] == 1
    again = do(action="why", case=wrong[0]["id"])
    assert again["totals"]["whys"] == 1 and again["lesson"]["why"] is not None
    assert any(c["explained"] for c in again["lesson"]["result"]["cases"] if c["id"] == wrong[0]["id"])
    do(action="why", case=wrong[1]["id"])
    assert do(action="open")["totals"]["whys"] == 2
    assert do(action="close_why")["lesson"]["why"] is None


def test_why_before_a_test_is_refused():
    assert not do(action="why", case="U1")["ok"]


def test_a_new_train_closes_the_why_and_forgets_the_test_but_keeps_the_notebook():
    do(action="pick", lesson="friendly-signals")
    do(action="train")
    v = do(action="test")
    wrong = [c for c in v["lesson"]["result"]["cases"] if not c["right"]][0]
    do(action="why", case=wrong["id"])
    v = do(action="train")
    assert v["lesson"]["why"] is None and v["lesson"]["result"] is None and v["totals"]["notebook"] == 1 and v["totals"]["whys"] == 1


def test_the_notebook_shows_names_always_and_the_rest_only_when_found():
    v = do(action="open")
    assert [e["id"] for e in v["notebook"]] == ["missing", "too_few", "distracting", "shortcut", "mislabelled"]
    assert all(not e["found"] and "about" not in e and "example" not in e for e in v["notebook"])
    do(action="pick", lesson="friendly-signals")
    do(action="train")
    wrong = [c for c in do(action="test")["lesson"]["result"]["cases"] if not c["right"]][0]
    v = do(action="why", case=wrong["id"])
    found = [e for e in v["notebook"] if e["found"]]
    assert len(found) == 1 and found[0]["lessons"] == ["Friendly Signals"] and found[0]["about"] and found[0]["example"]


def test_the_gallery_has_a_card_per_cleared_lesson_with_the_tree_in_words():
    assert do(action="open")["gallery"] == []
    clear("pipe-taps")
    g = do(action="open")["gallery"]
    assert len(g) == 1 and g[0]["id"] == "pipe-taps" and g[0]["best"] and g[0]["looked_at"] == ["Pitch"] and g[0]["tree"] and g[0]["learned"]


def test_shelves_open_at_five_cleared_lessons_in_any_order():
    first = lessons.SHELVES[0]["lessons"]
    assert not do(action="pick", lesson=lessons.SHELVES[1]["lessons"][0]["id"])["ok"]
    for l in reversed(first[3:]):                                       # any order
        clear(l["id"])
    v = do(action="open")
    assert v["totals"]["cleared"] == 5 and v["shelves"][1]["open"] and not v["shelves"][2]["open"]
    assert do(action="pick", lesson=lessons.SHELVES[1]["lessons"][0]["id"])["ok"]
    assert not do(action="pick", lesson=lessons.SHELVES[2]["lessons"][0]["id"])["ok"]


def test_the_message_names_the_shelf_that_just_opened():
    first = lessons.SHELVES[0]["lessons"]
    for l in first[:4]:
        clear(l["id"])
    v = clear(first[4]["id"])
    assert v["just"]["opened"] == ["Two Features"] and "A new shelf opens: Two Features." in v["message"]


def test_next_goes_to_the_next_open_lesson_that_is_not_cleared():
    clear(lessons.ORDER[1])
    do(action="pick", lesson=lessons.ORDER[0])
    assert do(action="next")["lesson"]["id"] == lessons.ORDER[2]


def test_pick_refuses_a_missing_lesson():
    assert not do(action="pick", lesson="nope")["ok"] and not do(action="pick", lesson=4)["ok"]


def test_every_lesson_can_be_cleared_in_order_with_its_proved_best_set():
    for s in range(3):
        clear_shelf(s)
    v = do(action="open")
    assert v["totals"]["cleared"] == 24 and v["totals"]["best_marks"] == 24 and v["totals"]["shelves_done"] == 3
    assert not do(action="next")["ok"] and "Every lesson is cleared" in do(action="next")["message"]
    assert len(v["gallery"]) == 24


def test_the_tally_counts_trains_tests_and_whys():
    do(action="train")
    do(action="train")
    do(action="test")
    t = do(action="open")["tally"]
    assert t["trains"] == 2 and t["tests"] == 1


def test_reset_starts_over():
    clear("ripe-crates")
    v = do(action="reset")
    assert v["totals"]["cleared"] == 0 and v["tally"] == {"trains": 0, "tests": 0, "whys": 0} and game_module.get_state() == {"schema": 1}


def test_unknown_and_malformed_requests_are_answered_not_raised():
    assert "error" in do(action="launch_missiles")
    assert "error" in json.loads(game_module.handle("not json"))


def test_the_about_page_is_in_the_view():
    info = do(action="open")["info"]
    assert info["pledge"] and info["how"] and len(info["facts"]) >= 3 and info["live"]["api"].startswith("https://en.wikipedia.org/api/rest_v1/")
