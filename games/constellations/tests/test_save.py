"""The save contract: get_state / load_state, every field checked on its own, nothing skippable by editing a save."""

import json

import pytest

import charts
import game as game_module
import sky


@pytest.fixture(autouse=True)
def fresh():
    game_module.handle(json.dumps({"action": "reset"}))
    yield
    game_module.handle(json.dumps({"action": "reset"}))


def do(**request):
    return json.loads(game_module.handle(json.dumps(request)))


def solve(cid):
    do(action="pick", chart=cid)
    for a, b in charts.BY_ID[cid]["figure"]:
        do(action="toggle", a=a, b=b)
    return do(action="finish")


def season_one():
    return [c["id"] for c in charts.SEASONS[0]["charts"]]


def test_a_fresh_game_saves_only_the_layout_version():
    assert game_module.get_state() == {"schema": 1}


def test_the_save_is_plain_json_data():
    solve(season_one()[0])
    do(action="pick", chart=season_one()[1])
    do(action="toggle", a=charts.BY_ID[season_one()[1]]["edges"][0][0], b=charts.BY_ID[season_one()[1]]["edges"][0][1])
    state = game_module.get_state()
    assert json.loads(json.dumps(state)) == state
    assert set(state) <= {"schema", "cur", "solved", "work", "moves", "tally", "hints", "achievements_earned"}


def test_round_trip_keeps_progress_work_and_tally():
    ids = season_one()
    solve(ids[0])
    solve(ids[1])
    do(action="pick", chart=ids[2])
    rules = charts.rules(ids[2])
    free = [e for e in rules.edges if rules.index[e] not in rules.must and rules.index[e] not in rules.never][:2]
    for a, b in free:
        do(action="toggle", a=a, b=b)
    state = json.loads(json.dumps(game_module.get_state()))
    before = do(action="open")
    game_module.handle(json.dumps({"action": "reset"}))
    game_module.load_state(state)
    after = do(action="open")
    assert after["chart"]["id"] == ids[2]
    assert after["chart"]["lines"] == before["chart"]["lines"]
    assert after["totals"] == before["totals"] and after["tally"] == before["tally"]
    assert after["chart"]["moves"] == before["chart"]["moves"] == 2
    assert [c["id"] for c in after["cards"]] == ids[:2]
    assert game_module.get_state() == state


def test_given_lines_are_never_written_to_the_save_and_never_lost():
    do(action="pick", chart="columba")
    state = game_module.get_state()
    assert "work" not in state
    game_module.load_state(state)
    v = do(action="open")
    assert any(l["given"] for l in v["chart"]["lines"])


def test_bad_fields_fall_back_alone():
    ids = season_one()
    state = {"schema": 1, "solved": {ids[0]: 7, ids[1]: "many", "nonsense": 3, ids[2]: -4}, "tally": {"draws": "x", "erases": 5},
             "work": {ids[3]: ["0-1", "bad", "9-9", 7, None, "1-0-2"], ids[4]: "oops", "nonsense": ["0-1"]}, "moves": {ids[3]: "two"}, "cur": 42}
    game_module.load_state(state)
    v = do(action="open")
    assert v["totals"]["done"] == 3                                              # the string and negative counts reset to 0 but the charts count
    assert v["tally"] == {"draws": 0, "erases": 5, "hints": 0}
    assert v["chart"]["id"] == charts.ORDER[0]
    st = game_module.get_state()
    assert st["solved"][ids[0]] == 7 and st["solved"][ids[1]] == 0
    assert all(isinstance(t, str) for t in st.get("work", {}).get(ids[3], []))


@pytest.mark.parametrize("bad", [None, [], "x", 5, {"schema": 2}, {"schema": 0}, {"schema": True}, {"schema": "1"}, {"schema": 1.0}])
def test_unreadable_saves_give_a_fresh_game(bad):
    solve(season_one()[0])
    game_module.load_state(bad)
    assert do(action="open")["totals"]["done"] == 0


def test_a_hand_edited_save_cannot_skip_a_season():
    spring = [c["id"] for c in charts.SEASONS[1]["charts"]]
    game_module.load_state({"schema": 1, "solved": {spring[0]: 3, spring[1]: 3}, "cur": spring[0]})
    v = do(action="open")
    assert v["totals"]["done"] == 0 and v["chart"]["id"] == charts.ORDER[0]
    # with four winter charts done, spring is still shut
    winter = season_one()
    game_module.load_state({"schema": 1, "solved": {w: 1 for w in winter[:4]} | {spring[0]: 1}})
    assert do(action="open")["totals"]["done"] == 4
    # with five it opens, and the spring chart then counts, whatever order the keys are in
    game_module.load_state({"schema": 1, "solved": {spring[0]: 1, **{w: 1 for w in winter[:5]}}, "cur": spring[0]})
    v = do(action="open")
    assert v["totals"]["done"] == 6 and v["chart"]["id"] == spring[0]


def test_saved_lines_must_be_real_allowed_lines_that_are_not_given_or_crossed_out():
    cid = "columba"
    c = charts.BY_ID[cid]
    rules = charts.rules(cid)
    must = "%d-%d" % tuple(c["clues"]["must"][0])
    never = "%d-%d" % tuple(c["clues"]["never"][0])
    ok = "%d-%d" % tuple(next(e for e in c["edges"] if rules.index[tuple(e)] not in rules.must and rules.index[tuple(e)] not in rules.never))
    game_module.load_state({"schema": 1, "work": {cid: [must, never, ok, "0-0", "20-30"]}, "cur": cid})
    assert game_module.get_state()["work"][cid] == [ok]


def test_a_saved_figure_that_is_already_complete_is_finished_on_load():
    cid = season_one()[0]
    c = charts.BY_ID[cid]
    game_module.load_state({"schema": 1, "work": {cid: ["%d-%d" % tuple(e) for e in c["figure"]]}, "moves": {cid: 6}})
    st = game_module.get_state()
    assert cid in st["solved"] and "work" not in st
    assert st["solved"][cid] == 6


def test_work_on_a_closed_season_is_dropped():
    spring0 = charts.SEASONS[1]["charts"][0]
    edge = spring0["edges"][0]
    game_module.load_state({"schema": 1, "work": {spring0["id"]: ["%d-%d" % tuple(edge)]}})
    assert "work" not in game_module.get_state()


def test_load_never_keeps_old_progress_that_the_save_lacks():
    solve(season_one()[0])
    game_module.load_state({"schema": 1})
    v = do(action="open")
    assert v["totals"]["done"] == 0 and v["tally"] == {"draws": 0, "erases": 0, "hints": 0}


def test_finished_charts_are_listed_in_chart_order_whatever_order_they_were_done_in():
    ids = season_one()
    for cid in reversed(ids[:5]):
        solve(cid)
    assert list(game_module.get_state()["solved"]) == ids[:5]
