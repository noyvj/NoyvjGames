"""The engine through its one entry point: handle(json) -> json."""

import json

import game
import nonogram as n
import pictures


def call(**req):
    return json.loads(game.handle(json.dumps(req)))


def fresh():
    game.game.__init__()


def cells_of(pid, ch="#"):
    p = pictures.BY_ID[pid]
    return [[r, c] for r in range(p.height) for c in range(p.width) if p.rows[r][c] == ch]


def solve(pid):
    call(action="pick", picture=pid)
    return call(action="paint", cells=cells_of(pid), value=1)


def hang_gallery(g, count=10):
    for p in pictures.GALLERIES[g]["pictures"][:count]:
        solve(p.id)


def test_open_returns_the_whole_view():
    fresh()
    v = call(action="open")
    first = pictures.BY_ID[pictures.ORDER[0]]
    assert v["ok"] and v["picture"]["id"] == first.id and v["picture"]["status"] == "open" and v["editable"]
    assert v["picture"]["row_clues"] == first.row_clues and v["picture"]["col_clues"] == first.col_clues
    assert v["grid"] == ["....."] * 5 and v["wrong"] == [] and v["just"] is None
    assert v["totals"] == {"pictures": 60, "hung": 0, "cells": 0, "hints": 0, "galleries": 6, "galleries_done": 0}
    assert v["tally"] == {"fills": 0, "dots": 0, "clears": 0, "hints": 0} and v["assist"] == {"check": False, "autodot": False, "focus": False}
    assert [g["open"] for g in v["galleries"]] == [True, False, False, False, False, False]


def test_the_view_never_leaks_an_unhung_picture():
    fresh()
    v = call(action="open")
    text = json.dumps(v)
    for p in pictures.ALL:
        assert p.title not in text and p.caption not in text
    assert all("rows" not in f and "title" not in f for g in v["galleries"] for f in g["frames"])
    assert "title" not in v["picture"] and "rows" not in v["picture"]


def test_a_stroke_marks_cells_counts_them_and_is_one_move():
    fresh()
    v = call(action="paint", cells=[[0, 1], [0, 2], [0, 3]], value=1)
    assert v["grid"][0] == ".###." and v["tally"]["fills"] == 3 and v["picture"]["moves"] == 1 and v["totals"]["cells"] == 3
    assert v["satisfied"]["rows"][0] is True and v["satisfied"]["cols"][0] is True      # column 0 wants nothing
    v = call(action="paint", cells=[[4, 0]], value=2)
    assert v["grid"][4] == "x...." and v["tally"]["dots"] == 1 and v["picture"]["moves"] == 2
    v = call(action="paint", cells=[[0, 1], [4, 0]], value=0)
    assert v["grid"][0] == "..##." and v["grid"][4] == "....." and v["tally"]["clears"] == 2


def test_painting_the_same_value_again_changes_and_counts_nothing():
    fresh()
    call(action="paint", cells=[[0, 1]], value=1)
    v = call(action="paint", cells=[[0, 1]], value=1)
    assert v["tally"]["fills"] == 1 and v["picture"]["moves"] == 1 and not call(action="undo")["can_undo"]


def test_bad_paint_requests_change_nothing():
    fresh()
    for bad in ({"cells": "all", "value": 1}, {"cells": [[0, 0]], "value": 3}, {"cells": [[0, 0]], "value": True}, {"cells": [[0, 0]], "value": "1"}):
        assert call(action="paint", **bad)["ok"] is False
    v = call(action="paint", cells=[[9, 9], [-1, 0], ["a", 0], [0], None, [True, 0], [0, 0, 0], [1.5, 1]], value=1)
    assert v["grid"] == ["....."] * 5 and v["tally"]["fills"] == 0 and v["picture"]["moves"] == 0
    assert "error" in call(action="no-such-thing") and "error" in json.loads(game.handle("not json"))


def test_a_repeated_cell_in_one_stroke_counts_once():
    fresh()
    v = call(action="paint", cells=[[0, 1], [0, 1], [0, 1]], value=1)
    assert v["tally"]["fills"] == 1


def test_undo_and_redo_step_through_strokes():
    fresh()
    call(action="paint", cells=[[0, 1], [0, 2]], value=1)
    call(action="paint", cells=[[1, 1]], value=2)
    v = call(action="undo")
    assert v["grid"][1] == "....." and v["can_redo"] and v["can_undo"]
    v = call(action="undo")
    assert v["grid"][0] == "....." and not v["can_undo"]
    assert call(action="undo")["ok"] is False
    v = call(action="redo")
    assert v["grid"][0] == ".##.."
    v = call(action="redo")
    assert v["grid"][1] == ".x..." and not v["can_redo"]
    call(action="undo")
    call(action="paint", cells=[[2, 2]], value=1)           # a new stroke ends the redo line
    assert not call(action="open")["can_redo"]


def test_undo_does_not_give_back_the_tally_or_the_strokes():
    fresh()
    call(action="paint", cells=[[0, 1]], value=1)
    v = call(action="undo")
    assert v["tally"]["fills"] == 1 and v["picture"]["moves"] == 1


def test_a_line_is_satisfied_by_filled_cells_alone_and_dots_do_not_matter():
    fresh()
    v = call(action="paint", cells=[[2, 2]], value=1)
    assert v["satisfied"]["rows"][2] is True and v["satisfied"]["rows"][0] is False
    v = call(action="paint", cells=[[2, 0], [2, 1], [2, 3], [2, 4]], value=2)
    assert v["satisfied"]["rows"][2] is True
    v = call(action="paint", cells=[[2, 3]], value=1)
    assert v["satisfied"]["rows"][2] is False


def test_solving_hangs_the_picture_and_reveals_it():
    fresh()
    v = solve("hammer")
    assert v["picture"]["status"] == "solved" and v["just"] == {"id": "hammer", "first": True, "moves": 1} and not v["editable"]
    assert v["picture"]["title"] == "Hammer" and v["picture"]["rows"] == list(pictures.BY_ID["hammer"].rows)
    assert v["grid"] == list(pictures.BY_ID["hammer"].rows)           # a hung frame shows its filled cells and nothing else
    assert "hung on the wall" in v["message"]
    frame = [f for f in v["galleries"][0]["frames"] if f["id"] == "hammer"][0]
    assert frame["hung"] and frame["title"] == "Hammer" and frame["moves"] == 1 and frame["rows"] == list(pictures.BY_ID["hammer"].rows)
    assert v["totals"]["hung"] == 1 and v["totals"]["cells"] == 9


def test_any_complete_grid_counts_not_only_the_stored_bitmap_and_dots_are_free():
    fresh()
    call(action="paint", cells=cells_of("hammer", "."), value=2)             # dot every empty cell first
    v = call(action="paint", cells=cells_of("hammer"), value=1)
    assert v["picture"]["status"] == "solved"


def test_a_hung_picture_is_locked_until_solve_it_again():
    fresh()
    solve("hammer")
    v = call(action="paint", cells=[[0, 0]], value=1)
    assert v["ok"] is False and v["grid"][0] == ".###." and call(action="undo")["ok"] is False
    v = call(action="retry")
    assert v["picture"]["status"] == "redo" and v["grid"] == ["....."] * 5 and v["editable"] and v["picture"]["best"] == 1
    assert [f["hung"] for f in v["galleries"][0]["frames"]][0] is True          # still hung while it is solved again
    v = call(action="paint", cells=cells_of("hammer")[:5], value=1)
    v = call(action="paint", cells=cells_of("hammer")[5:], value=1)
    assert v["picture"]["status"] == "solved" and v["just"]["first"] is False
    assert v["totals"]["hung"] == 1 and v["picture"]["best"] == 1                  # the best (fewest strokes) is kept
    assert call(action="retry")["ok"] and not call(action="open")["picture"]["status"] == "solved"
    assert call(action="pick", picture="key")["ok"] and call(action="retry")["ok"] is False


def test_a_retry_that_takes_fewer_strokes_improves_the_best():
    fresh()
    call(action="paint", cells=cells_of("hammer")[:4], value=1)
    v = call(action="paint", cells=cells_of("hammer")[4:], value=1)
    assert v["picture"]["best"] == 2
    call(action="retry")
    v = call(action="paint", cells=cells_of("hammer"), value=1)
    assert v["picture"]["best"] == 1 and v["just"]["moves"] == 1


def test_gating_keeps_a_later_gallery_shut_until_six_are_hung():
    fresh()
    second = pictures.GALLERIES[1]["pictures"][0].id
    v = call(action="pick", picture=second)
    assert v["ok"] is False and v["picture"]["id"] == pictures.ORDER[0] and "6" in v["message"]
    hang_gallery(0, 5)
    assert call(action="pick", picture=second)["ok"] is False
    wall = call(action="open")["galleries"]
    assert wall[1]["need"] == 1 and not wall[1]["open"]
    solve(pictures.GALLERIES[0]["pictures"][5].id)
    v = call(action="pick", picture=second)
    assert v["ok"] and v["picture"]["id"] == second and v["picture"]["gallery"] == "Small Machines"
    assert call(action="open")["galleries"][1]["need"] == 0
    assert call(action="pick", picture=pictures.GALLERIES[2]["pictures"][0].id)["ok"] is False
    assert call(action="pick", picture="nonsense")["ok"] is False and call(action="pick", picture=7)["ok"] is False


def test_painting_never_reaches_a_closed_gallery():
    fresh()
    game.game.current = pictures.GALLERIES[1]["pictures"][0].id      # a hand-edited state cannot be used to play ahead
    game.game.load(game.game.to_dict())
    assert call(action="open")["picture"]["id"] == pictures.ORDER[0]


def test_next_goes_to_the_next_open_frame_not_yet_hung():
    fresh()
    solve("hammer")
    v = call(action="next")
    assert v["picture"]["id"] == "key"
    hang_gallery(0)
    v = call(action="next")
    assert v["picture"]["gallery_index"] == 1 and v["picture"]["status"] == "open"
    fresh()
    hang_gallery(0, 6)
    hang_gallery(1, 6)
    call(action="pick", picture=pictures.GALLERIES[0]["pictures"][0].id)
    ids = []
    for _ in range(40):
        v = call(action="next")
        if not v["ok"]:
            break
        ids.append(v["picture"]["id"])
    assert ids[:4] == [p.id for p in pictures.GALLERIES[0]["pictures"][6:10]] and "scrap" in ids


def test_every_gallery_can_be_finished_and_a_full_wall_says_so():
    fresh()
    for g in range(len(pictures.GALLERIES)):
        hang_gallery(g)
    v = call(action="open")
    assert v["totals"]["hung"] == 60 and v["totals"]["galleries_done"] == 6
    assert call(action="next")["message"] == "Every frame is hung."
    assert all(f["hung"] for g in v["galleries"] for f in g["frames"])


def test_check_mistakes_marks_wrong_cells_only_when_asked_and_never_blocks():
    fresh()
    v = call(action="paint", cells=[[0, 0], [0, 1]], value=1)           # (0,0) is wrong, (0,1) is right
    assert v["wrong"] == []
    v = call(action="assist", name="check", on=True)
    assert v["wrong"] == [[0, 0]] and v["assist"]["check"] is True
    v = call(action="paint", cells=[[1, 2]], value=2)                    # a dot where the picture is filled is wrong too
    assert sorted(v["wrong"]) == [[0, 0], [1, 2]]
    v = call(action="paint", cells=[[3, 3]], value=2)                    # a dot on an empty cell is fine
    assert [3, 3] not in v["wrong"]
    v = call(action="assist", name="check", on=False)
    assert v["wrong"] == []
    assert call(action="assist", name="bogus", on=True)["ok"] is False


def test_auto_dot_dots_the_rest_of_a_finished_line_and_undo_takes_it_back():
    fresh()
    call(action="assist", name="autodot", on=True)
    v = call(action="paint", cells=[[0, 1], [0, 2], [0, 3]], value=1)
    assert v["grid"][0] == "x###x"
    assert v["tally"]["dots"] == 0 and v["tally"]["fills"] == 3                # auto dots are not the player's marks
    v = call(action="undo")
    assert v["grid"][0] == "....."
    v = call(action="redo")
    assert v["grid"][0] == "x###x"


def test_auto_dot_is_off_by_default():
    fresh()
    v = call(action="paint", cells=[[0, 1], [0, 2], [0, 3]], value=1)
    assert v["grid"][0] == ".###."


def test_moving_between_frames_keeps_each_frames_work():
    fresh()
    call(action="paint", cells=[[0, 1]], value=1)
    call(action="pick", picture="key")
    v = call(action="open")
    assert v["grid"] == ["....."] * 5 and not v["can_undo"]                    # undo history is per visit
    v = call(action="pick", picture="hammer")
    assert v["grid"][0] == ".#..." and v["picture"]["moves"] == 1


def test_reset_starts_over_completely():
    fresh()
    solve("hammer")
    call(action="assist", name="check", on=True)
    v = call(action="reset")
    assert v["totals"]["hung"] == 0 and v["tally"]["fills"] == 0 and v["assist"]["check"] is False and game.get_state() == {"schema": 1}


def test_the_engine_modules_use_no_clock_and_no_randomness():
    from pathlib import Path
    for path in Path(game.__file__).resolve().parent.glob("*.py"):
        text = path.read_text(encoding="utf-8")
        for banned in ("import time", "import random", "import datetime", "from time", "from random", "from datetime", "Date.now", "Math.random"):
            assert banned not in text, "%s uses %s" % (path.name, banned)
