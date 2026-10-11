"""The save contract: get_state() writes only what differs from a fresh game; load_state() validates every field on its own."""

import copy
import json
import re

import game
import pictures


def call(**req):
    return json.loads(game.handle(json.dumps(req)))


def fresh():
    game.game.__init__()


def cells_of(pid):
    p = pictures.BY_ID[pid]
    return [[r, c] for r in range(p.height) for c in range(p.width) if p.rows[r][c] == "#"]


def play_a_little():
    fresh()
    call(action="pick", picture="hammer")
    call(action="paint", cells=cells_of("hammer"), value=1)
    call(action="pick", picture="key")
    call(action="paint", cells=[[0, 1], [0, 2]], value=1)
    call(action="paint", cells=[[4, 0]], value=2)
    call(action="assist", name="focus", on=True)


def test_a_fresh_game_saves_as_just_its_layout_version():
    fresh()
    assert game.get_state() == {"schema": 1} and game.SCHEMA == 1


def test_only_changed_keys_are_written_and_the_state_is_json_safe():
    play_a_little()
    state = game.get_state()
    assert set(state) == {"schema", "cur", "solved", "work", "moves", "tally", "assist", "achievements_earned"} and state["schema"] == 1
    assert state["achievements_earned"] == ["first_frame"]
    assert state["cur"] == "key" and state["solved"] == {"hammer": 1} and state["moves"] == {"key": 2}
    assert state["work"] == {"key": [".##..", ".....", ".....", ".....", "x...."]}
    assert state["tally"] == {"fills": 11, "dots": 1} and state["assist"] == {"focus": 1}
    assert json.loads(json.dumps(state)) == state
    fresh()
    call(action="paint", cells=[[0, 1]], value=1)
    assert set(game.get_state()) == {"schema", "work", "moves", "tally"} and "cur" not in game.get_state()


def test_an_untouched_blank_frame_is_not_saved_and_a_redo_frame_is():
    fresh()
    call(action="paint", cells=[[0, 1]], value=1)
    call(action="undo")
    assert "work" not in game.get_state()
    call(action="paint", cells=cells_of("hammer"), value=1)
    call(action="retry")
    assert game.get_state()["work"] == {"hammer": ["....."] * 5}


def test_the_save_round_trips_exactly():
    play_a_little()
    state = json.loads(json.dumps(game.get_state()))
    before = call(action="open")
    fresh()
    game.load_state(json.loads(json.dumps(state)))
    after = call(action="open")
    before["just"] = None
    after["can_undo"] = before["can_undo"]                   # undo history is not saved
    assert after == before and game.get_state() == state


def test_a_hung_picture_in_redo_survives_a_round_trip():
    fresh()
    call(action="paint", cells=cells_of("hammer"), value=1)
    call(action="retry")
    call(action="paint", cells=[[0, 1]], value=1)
    state = json.loads(json.dumps(game.get_state()))
    fresh()
    game.load_state(state)
    v = call(action="open")
    assert v["picture"]["status"] == "redo" and v["grid"][0] == ".#..." and v["picture"]["best"] == 1 and v["picture"]["moves"] == 1


def test_the_save_holds_nothing_about_time():
    play_a_little()
    assert not re.search(r"time|date|stamp|day|clock", json.dumps(game.get_state()), flags=re.I)


def test_load_state_of_junk_is_a_fresh_game():
    for junk in (None, 5, "x", [], [1], {"solved": 3}, {"work": []}, {"cur": 9}, {"tally": "no"}):
        fresh()
        game.load_state(junk)
        assert game.get_state() == {"schema": 1}, junk


def test_every_field_is_checked_on_its_own():
    fresh()
    good = {"hammer": 4}
    game.load_state({"solved": {"hammer": 4, "nothing": 2, "key": -1, "lantern": "x", "flask": True, "bell": 1.5}, "tally": {"fills": "many", "dots": 7, "clears": -2},
                     "assist": {"check": 1, "autodot": "yes", "bogus": 1}, "cur": "hammer"})
    s = game.get_state()
    assert s["solved"]["hammer"] == 4 and s["solved"]["key"] == 0 and s["solved"]["lantern"] == 0
    assert "nothing" not in s["solved"] and "flask" in s["solved"] and s["solved"]["flask"] == 0 and s["solved"]["bell"] == 0
    assert s["tally"] == {"dots": 7} and s["assist"] == {"check": 1} and "cur" not in s


def test_a_hung_picture_in_a_closed_gallery_is_dropped():
    fresh()
    game.load_state({"solved": {"gear": 3, "scrap": 2, "hammer": 1}, "cur": "gear"})
    s = game.get_state()
    assert s["solved"] == {"hammer": 1} and "cur" not in s


def test_gating_is_judged_in_gallery_order_so_a_save_cannot_skip_ahead():
    first = [p.id for p in pictures.GALLERIES[0]["pictures"]]
    second = [p.id for p in pictures.GALLERIES[1]["pictures"]]
    third = [p.id for p in pictures.GALLERIES[2]["pictures"]]
    fresh()
    game.load_state({"solved": {**{i: 1 for i in first[:6]}, **{i: 1 for i in second[:5]}, third[0]: 1}})
    s = game.get_state()["solved"]
    assert set(s) == set(first[:6]) | set(second[:5])
    fresh()
    game.load_state({"solved": {**{i: 1 for i in first[:6]}, **{i: 1 for i in second[:6]}, third[0]: 1}, "cur": third[0]})
    s = game.get_state()
    assert third[0] in s["solved"] and s["cur"] == third[0]


def test_a_saved_frame_must_be_exactly_the_pictures_shape_and_alphabet():
    for bad in (["....."] * 4, ["......"] * 5, ["....."] * 5 + ["....."], ["..?.."] * 5, [".....", 5, ".....", ".....", "....."], "....." * 5, {"a": 1}, [None] * 5):
        fresh()
        game.load_state({"work": {"hammer": bad}})
        assert "work" not in game.get_state(), bad
    fresh()
    game.load_state({"work": {"hammer": [".#x..", ".....", ".....", ".....", "....."]}, "moves": {"hammer": 12}})
    assert game.get_state()["work"]["hammer"][0] == ".#x.." and game.get_state()["moves"] == {"hammer": 12}


def test_a_saved_frame_for_a_closed_gallery_or_an_unknown_picture_is_dropped():
    fresh()
    game.load_state({"work": {"gear": ["........"] * 7 + ["#......."], "ghost": ["....."] * 5}})
    assert game.get_state() == {"schema": 1}


def test_a_saved_frame_that_is_already_complete_is_hung_on_load():
    fresh()
    p = pictures.BY_ID["hammer"]
    game.load_state({"work": {"hammer": list(p.rows)}, "moves": {"hammer": 5}})
    s = game.get_state()
    assert s["solved"] == {"hammer": 5} and "work" not in s and "moves" not in s
    # and a finished redo frame keeps the better stroke count
    fresh()
    game.load_state({"solved": {"hammer": 3}, "work": {"hammer": list(p.rows)}, "moves": {"hammer": 9}})
    assert game.get_state()["solved"] == {"hammer": 3} and "work" not in game.get_state()


def test_a_bad_save_never_crashes_the_view():
    for state in ({"solved": {"hammer": 10 ** 20}}, {"work": {"hammer": [".....", ".....", ".....", ".....", "....."]}, "moves": {"hammer": "7"}}, {"cur": ["hammer"]}):
        fresh()
        game.load_state(copy.deepcopy(state))
        assert call(action="open")["ok"]


def test_moves_are_only_kept_for_frames_that_are_saved():
    fresh()
    game.load_state({"moves": {"hammer": 4, "key": 2}, "work": {"hammer": [".#...", ".....", ".....", ".....", "....."]}})
    assert game.get_state()["moves"] == {"hammer": 4}


def test_a_save_from_a_newer_layout_or_with_a_bad_version_is_not_half_read():
    good = {"schema": 1, "solved": {"hammer": 3}, "tally": {"fills": 9}}
    fresh()
    game.load_state(good)
    assert game.get_state()["solved"] == {"hammer": 3}
    for bad in (2, 0, -1, "1", 1.0, True, None, [1]):
        fresh()
        game.load_state(dict(good, schema=bad))
        assert game.get_state() == {"schema": 1}, bad
    fresh()
    game.load_state({"solved": {"hammer": 3}})                      # no version at all: an older save, read as layout 1
    assert game.get_state()["solved"] == {"hammer": 3}
