"""The save contract: get_state / load_state, every field checked on its own, nothing skippable by editing a save."""

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


def clear(lid, on=None):
    do(action="pick", lesson=lid)
    for f in do(action="open")["lesson"]["features"]:
        if f["on"] != (f["id"] in (on or lessons.BY_ID[lid]["best"])):
            do(action="toggle", feature=f["id"])
    do(action="train")
    return do(action="test")


def shelf_one():
    return [l["id"] for l in lessons.SHELVES[0]["lessons"]]


def test_a_fresh_game_saves_only_the_layout_version():
    assert game_module.get_state() == {"schema": 1}


def test_the_save_is_plain_json_data_with_known_keys():
    clear(shelf_one()[0])
    clear(shelf_one()[2], ["gap"])
    do(action="train")
    wrong = [c for c in do(action="test")["lesson"]["result"]["cases"] if not c["right"]][0]
    do(action="why", case=wrong["id"])
    state = game_module.get_state()
    assert json.loads(json.dumps(state)) == state
    assert set(state) <= {"schema", "cur", "cleared", "sel", "notebook", "tally", "achievements_earned"}
    assert state["cleared"] == {shelf_one()[0]: ["glow"]} and state["tally"]["whys"] == 1


def test_round_trip_keeps_progress_switches_notebook_and_tally():
    ids = shelf_one()
    clear(ids[0])
    clear(ids[1], ["heat", "number"])
    do(action="pick", lesson=ids[2])
    do(action="toggle", feature="tone")
    do(action="train")
    wrong = [c for c in do(action="test")["lesson"]["result"]["cases"] if not c["right"]][0]
    do(action="why", case=wrong["id"])
    state = json.loads(json.dumps(game_module.get_state()))
    before = do(action="open")
    game_module.handle(json.dumps({"action": "reset"}))
    game_module.load_state(state)
    after = do(action="open")
    for key in ("shelves", "notebook", "gallery", "totals", "tally"):
        assert after[key] == before[key], key
    assert after["lesson"]["id"] == ids[2]
    assert [f["on"] for f in after["lesson"]["features"]] == [f["on"] for f in before["lesson"]["features"]]
    assert not after["lesson"]["trained"]                                  # the tree is not saved: Train again
    assert game_module.get_state() == state


def test_a_default_selection_is_not_written():
    do(action="toggle", feature="glow")
    do(action="toggle", feature="glow")
    assert "sel" not in game_module.get_state()


def test_a_bad_or_newer_layout_gives_a_fresh_game():
    clear(shelf_one()[0])
    state = game_module.get_state()
    for schema in (0, 2, "1", None, True, 1.5):
        game_module.load_state(dict(state, schema=schema))
        assert do(action="open")["totals"]["cleared"] == 0, schema
    for junk in (None, [], "x", 3, {"cleared": 4}):
        game_module.load_state(junk)
        assert do(action="open")["totals"]["cleared"] == 0


def test_a_cleared_lesson_in_a_closed_shelf_is_dropped_and_shelves_are_judged_in_order():
    two = lessons.SHELVES[1]["lessons"][0]["id"]
    three = lessons.SHELVES[2]["lessons"][0]["id"]
    game_module.load_state({"schema": 1, "cleared": {two: lessons.BY_ID[two]["best"], three: lessons.BY_ID[three]["best"]}, "cur": three})
    v = do(action="open")
    assert v["totals"]["cleared"] == 0 and v["lesson"]["id"] == lessons.ORDER[0]
    five = {l: lessons.BY_ID[l]["best"] for l in shelf_one()[:5]}
    game_module.load_state({"schema": 1, "cleared": dict(five, **{two: lessons.BY_ID[two]["best"], three: lessons.BY_ID[three]["best"]})})
    assert do(action="open")["totals"]["cleared"] == 6                     # shelf 2 was open by the five, shelf 3 still needs five of shelf 2


def test_a_saved_set_that_does_not_really_clear_is_replaced_by_the_proved_best_set():
    lid = shelf_one()[0]
    for bad in (["weight"], [], ["nonsense"], "glow", None, [1, 2]):
        game_module.load_state({"schema": 1, "cleared": {lid: bad}})
        v = do(action="open")
        assert v["totals"]["cleared"] == 1 and game_module.get_state()["cleared"][lid] == lessons.BY_ID[lid]["best"], bad
    game_module.load_state({"schema": 1, "cleared": {lid: ["weight", "glow", "glow", "zzz"]}})
    assert game_module.get_state()["cleared"][lid] == ["glow", "weight"]


def test_each_bad_field_falls_back_on_its_own():
    lid = shelf_one()[0]
    game_module.load_state({"schema": 1, "cleared": {lid: ["glow"]}, "tally": {"trains": -5, "tests": "x", "whys": 7}, "sel": 3, "notebook": "no", "cur": 12})
    v = do(action="open")
    assert v["totals"]["cleared"] == 1 and v["tally"] == {"trains": 0, "tests": 0, "whys": 7} and v["lesson"]["id"] == lessons.ORDER[0]
    assert v["totals"]["notebook"] == 0


def test_the_saved_selection_is_checked_and_only_for_open_lessons():
    ids = shelf_one()
    locked = lessons.SHELVES[1]["lessons"][0]["id"]
    game_module.load_state({"schema": 1, "sel": {ids[2]: ["tone", "tone", "bogus", 4], locked: ["glow"], "nope": ["x"], ids[3]: "no"}, "cur": ids[2]})
    v = do(action="open")
    assert [f["id"] for f in v["lesson"]["features"] if f["on"]] == ["tone"]
    assert game_module.get_state()["sel"] == {ids[2]: ["tone"]}
    game_module.load_state({"schema": 1, "sel": {ids[2]: []}, "cur": ids[2]})
    assert do(action="open")["lesson"]["on_count"] == 0                      # all switches off is a real choice


def test_the_notebook_is_checked_category_by_category():
    ids = shelf_one()
    game_module.load_state({"schema": 1, "notebook": {"missing": [ids[0], "nope", ids[0], lessons.SHELVES[2]["lessons"][0]["id"]], "weird": [ids[0]], "too_few": "x",
                                                      "distracting": []}})
    v = do(action="open")
    found = {e["id"]: e["count"] for e in v["notebook"]}
    assert found == {"missing": 1, "too_few": 0, "distracting": 0, "shortcut": 0, "mislabelled": 0}


def test_loading_closes_any_work_in_progress():
    do(action="train")
    do(action="test")
    game_module.load_state(game_module.get_state())
    v = do(action="open")
    assert v["lesson"]["result"] is None and v["lesson"]["tree"] is None


def test_the_notebook_categories_in_a_save_are_real_ones():
    clear(shelf_one()[2], ["gap"])
    assert set(game_module.get_state().get("notebook", {})) <= set(why.CATEGORY_IDS)
