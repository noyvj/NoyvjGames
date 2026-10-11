"""The save contract: get_state() writes only what differs from a fresh game; load_state() validates every field on its own."""

import json
import re

import benches
import game
import optics


def call(**req):
    return json.loads(game.handle(json.dumps(req)))


def fresh():
    game.game.__init__()


def play_a_little():
    fresh()
    call(action="place", r=3, c=4, piece="mirror")                  # clears c1-1
    call(action="pick", bench="c1-2")
    call(action="place", r=0, c=3, piece="mirror")
    call(action="flip", r=0, c=3)
    call(action="pick", bench="c1-3")
    call(action="place", r=0, c=1, piece="mirror")


def test_a_fresh_game_saves_as_nothing():
    fresh()
    assert game.get_state() == {}


def test_only_changed_keys_are_written_and_the_state_is_json_safe():
    play_a_little()
    state = game.get_state()
    assert set(state) == {"schema", "cur", "cleared", "layouts", "tally", "used"} and state["schema"] == 1
    assert state["cur"] == "c1-3" and state["cleared"] == {"c1-1": [[3, 4, "m", 0]]}
    assert state["layouts"]["c1-2"] == [[0, 3, "m", 1]] and state["layouts"]["c1-3"] == [[0, 1, "m", 0]]
    assert state["tally"] == {"placed": 3, "flips": 1} and state["used"] == ["mirror"]
    assert json.loads(json.dumps(state)) == state
    fresh()
    call(action="place", r=3, c=4, piece="mirror")
    call(action="pickup", r=3, c=4)
    assert "cur" not in game.get_state() and "layouts" not in game.get_state()                 # an emptied bench is not stored


def test_the_save_round_trips_exactly():
    play_a_little()
    state = json.loads(json.dumps(game.get_state()))
    before = call(action="open")
    fresh()
    game.load_state(json.loads(json.dumps(state)))
    after = call(action="open")
    assert after == before and game.get_state() == state


def test_the_save_holds_nothing_about_time():
    play_a_little()
    assert not re.search(r"time|date|stamp|day|clock", json.dumps(game.get_state()), flags=re.I)


def test_garbage_loads_as_a_fresh_game_and_never_raises():
    for bad in (None, 5, "x", [], {"cleared": 5, "layouts": "x", "tally": [], "cur": {}, "used": 3}, {"cleared": {"c1-1": 5}}, {"layouts": {"c1-1": {"a": 1}}}):
        fresh()
        game.load_state(bad)
        assert game.get_state() == {} and call(action="open")["bench"]["id"] == "c1-1"


def test_every_field_is_checked_on_its_own():
    fresh()
    game.load_state({
        "cur": "c3-1",                                                       # chapter 3 is locked: falls back
        "cleared": {"c1-1": [[3, 4, "m", 0]], "c1-2": [[0, 3, "m", 1]],     # c1-2 is not a solution: dropped
                    "c1-3": [[9, 9, "m", 0]], "nope": [[0, 0, "m", 0]], "c1-4": [[0, 2, "m", True]],
                    "c1-5": [[4, 3, "m", 1], [4, 6, "m", 0]]},
        "layouts": {"c1-2": [[0, 3, "m", 1], [0, 3, "m", 0], [9, 9, "m", 0], [4, 3, "x", 0], "junk", [0, 2, "m", 5], [4, 3, "m", 1], [1, 2, "m", 0]],
                    "ghost": [[0, 0, "m", 0]]},
        "tally": {"placed": 7, "picked": -1, "flips": "x"},
        "used": ["mirror", "splitter", "lens", 5],
    })
    state = game.get_state()
    assert game.game.current == "c1-1"
    assert set(state["cleared"]) == {"c1-1", "c1-5"}                       # only layouts that really light the bench count
    assert state["layouts"]["c1-2"] == [[0, 3, "m", 1], [4, 3, "m", 1]]    # the tray holds 2 mirrors: the rest is dropped
    assert state["tally"] == {"placed": 7}
    assert state["used"] == ["mirror", "splitter"]


def test_a_cleared_bench_is_re_judged_by_the_rules_not_trusted():
    fresh()
    game.load_state({"cleared": {"c1-1": [[3, 3, "m", 0]]}})
    assert game.game.cleared == {}
    game.load_state({"cleared": {"c1-1": [[3, 4, "m", 0], [3, 4, "m", 1]]}})            # two pieces on one slot: invalid as a whole
    assert game.game.cleared == {}
    game.load_state({"cleared": {"c1-1": [[3, 4, "m", 0]]}})
    assert set(game.game.cleared) == {"c1-1"}


def test_a_saved_current_bench_is_only_kept_when_its_chapter_is_open():
    fresh()
    cleared = {b.id: [[r, c, optics.PIECE_CODE[p], s] for r, c, p, s in b.solution] for b in benches.CHAPTERS[0]["benches"][:5]}
    game.load_state({"cur": "c2-3", "cleared": cleared})
    assert game.game.current == "c2-3"
    game.load_state({"cur": "c2-3"})
    assert game.game.current == "c1-1"


def test_a_page_filled_by_a_layout_in_the_save_stays_filled():
    fresh()
    game.load_state({"layouts": {"c2-1": [[3, 3, "s", 0]]}})
    assert "splitter" in game.get_state()["used"]
