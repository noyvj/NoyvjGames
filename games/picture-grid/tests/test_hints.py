"""The hint ladder: every rung opens only on a press, every hint is a line-logic deduction that agrees with the picture, a hint
never names a cell before rung 3, and Easy / Normal / Hard change only how the ladder opens."""

import json

import pytest

import game
import hints
import nonogram as n
import pictures

U, F, E = n.UNKNOWN, n.FILLED, n.EMPTY


def call(**req):
    return json.loads(game.handle(json.dumps(req)))


def fresh(pid=None):
    game.game.__init__()
    if pid:
        game.game.current = pid


def cells_of(pid, ch="#"):
    p = pictures.BY_ID[pid]
    return [[r, c] for r in range(p.height) for c in range(p.width) if p.rows[r][c] == ch]


def level(name):
    return call(action="difficulty", level=name)


# ---- the reasoning kinds, line by line ----------------------------------------------------------------------------------
def test_reasoning_names_the_kind_of_deduction():
    assert hints.reasoning([], [U] * 4) == "empty"
    assert hints.reasoning([3, 2], [U] * 6) == "exact"                    # 3 + 1 + 2 = 6: no spare room
    assert hints.reasoning([4], [U] * 6) == "overlap"                     # 2 spare, block of 4: the middle is certain
    assert hints.reasoning([2, 1], [F, F, U, U, U]) == "pinned"
    assert hints.reasoning([2], [F, F, U, U]) == "complete"               # the block is already there: the rest is empty
    assert hints.reasoning([2, 1], [U, E, U, U, U]) == "pinned"
    assert set(hints.KINDS) == {"empty", "complete", "exact", "overlap", "pinned"}


def test_the_reasoning_is_true_to_the_deductions_it_describes():
    """For every picture and every line, a blank-frame deduction is 'empty', 'exact' or 'overlap' and the claim holds."""
    for p in pictures.ALL:
        for kind, count in (("row", p.height), ("col", p.width)):
            for i in range(count):
                clue = hints.clue_of(p, kind, i)
                length = p.width if kind == "row" else p.height
                found = n.line_deductions(clue, [U] * length)
                if not found:
                    continue
                why = hints.reasoning(clue, [U] * length)
                total = sum(clue) + len(clue) - 1
                assert why in ("empty", "exact", "overlap"), (p.id, kind, i)
                if why == "overlap":
                    assert max(clue) > length - total
                if why == "exact":
                    assert total == length and len(found) == length


def test_cells_phrase_reads_in_runs_from_one():
    moves = [(1, F), (2, F), (3, F), (6, E)]
    assert hints.cells_phrase("row", moves) == "filled columns 2 to 4, dotted column 7"
    assert hints.cells_phrase("col", [(0, F), (4, F)]) == "filled row 1, row 5"
    assert hints.fill_text("row", 3, [(0, F)]) == "Row 4: filled column 1."


def test_a_wrong_mark_is_ignored_when_working_out_what_is_certain():
    p = pictures.BY_ID["hammer"]
    grid = n.blank_grid(p.height, p.width)
    solution = p.solution_grid()
    r, c = next((r, c) for r in range(p.height) for c in range(p.width) if solution[r][c] != F)
    grid[r][c] = F                                                        # a wrong fill
    know = hints.knowledge(p, grid)
    assert know[r][c] == U
    r2, c2 = next((r, c) for r in range(p.height) for c in range(p.width) if solution[r][c] == F)
    grid[r2][c2] = F
    assert hints.knowledge(p, grid)[r2][c2] == F


def test_the_line_is_chosen_the_same_way_every_time_and_every_move_is_true():
    for p in pictures.ALL[::7]:
        grid = n.blank_grid(p.height, p.width)
        a, b = hints.pick(p, grid), hints.pick(p, grid)
        assert a == b and a is not None
        solution = p.solution_grid()
        for i, value in a["moves"]:
            r, c = hints.point(a["kind"], a["index"], i)
            assert (solution[r][c] == F) == (value == F), (p.id, a["kind"], a["index"], i)


# ---- the ladder through the engine ----------------------------------------------------------------------------------------
def test_nothing_is_shown_until_the_player_presses():
    fresh()
    v = call(action="open")
    assert v["hint"] is None and v["hint_ui"]["next"] == 1 and v["hint_ui"]["label"] == "Would you like a suggestion?"
    assert v["totals"]["hints"] == 0 and v["tally"]["hints"] == 0
    assert "has a move that is certain" not in json.dumps(v)               # no nudge text anywhere until a press
    assert v["hint_ui"]["available"] is True and v["hint_ui"]["confirm"] is False


def test_rung_one_names_a_line_but_no_cell_and_is_counted():
    fresh()
    v = call(action="hint")
    h = v["hint"]
    assert v["ok"] and h["rung"] == 1 and h["line"].split()[0] in ("Row", "Column")
    assert h["detail"] == "" and h["fill"] == "" and h["cells"] == []
    assert v["tally"]["hints"] == 1 and v["totals"]["hints"] == 1
    assert v["hint_ui"]["next"] == 2 and v["hint_ui"]["label"] == "Another hint"
    assert v["grid"] == ["....."] * 5 and v["picture"]["moves"] == 0          # asking changes nothing on the frame


def test_rung_two_says_what_kind_of_reasoning_and_still_names_no_cell():
    fresh()
    call(action="hint")
    v = call(action="hint")
    h = v["hint"]
    assert h["rung"] == 2 and h["detail"].startswith(h["line"] + ", clue ") and h["fill"] == "" and h["cells"] == []
    assert any(word in h["detail"] for word in ("spare", "exact", "no spare room", "empty", "already", "marked"))
    assert "filled column" not in h["detail"] and "filled row" not in h["detail"]
    assert v["tally"]["hints"] == 2 and v["hint_ui"]["next"] == 3 and v["hint_ui"]["confirm"] is True


def test_rung_three_needs_a_confirm_on_normal_and_does_nothing_without_one():
    fresh()
    call(action="hint")
    call(action="hint")
    v = call(action="hint")
    assert v["ok"] is False and "confirm" in v["message"].lower() and v["grid"] == ["....."] * 5
    assert v["tally"]["hints"] == 2 and v["hint"]["rung"] == 2
    v = call(action="hint", confirm=True)
    assert v["ok"] and v["hint"]["rung"] == 3 and v["hint"]["done"] is True and v["hint"]["fill"] and v["hint"]["cells"]
    assert v["tally"]["hints"] == 3 and v["tally"]["fills"] == 0         # the fill is not the player's own mark
    assert v["picture"]["moves"] == 1 and v["can_undo"] is True
    p = pictures.BY_ID[game.game.current]
    sol = p.solution_grid()
    for r, c, value in v["hint"]["cells"]:
        assert (sol[r][c] == F) == (value == F)
        assert v["grid"][r][c] == ("#" if value == F else "x")
    assert call(action="undo")["grid"] == ["....."] * 5


def test_a_confirm_that_is_not_exactly_true_is_not_a_confirm():
    fresh()
    call(action="hint")
    call(action="hint")
    v = call(action="hint", confirm="yes")
    assert v["ok"] is False and v["grid"] == ["....."] * 5


def test_after_a_fill_the_next_press_starts_a_new_ladder():
    fresh()
    call(action="hint"); call(action="hint"); call(action="hint", confirm=True)
    v = call(action="hint")
    assert v["ok"] and v["hint"]["rung"] == 1 and v["hint"]["cells"] == []


def test_any_change_to_the_frame_clears_the_ladder():
    for change in (lambda: call(action="paint", cells=[[0, 0]], value=2), lambda: call(action="pick", picture="key"),
                   lambda: call(action="next"), lambda: call(action="undo"), lambda: call(action="reset")):
        fresh()
        call(action="paint", cells=[[4, 4]], value=2)
        call(action="hint")
        assert call(action="open")["hint"] is not None
        v = change()
        assert v["hint"] is None, change


def test_asking_on_the_frame_you_are_already_on_keeps_the_ladder():
    fresh()
    call(action="hint")
    assert call(action="pick", picture=game.game.current)["hint"]["rung"] == 1


def test_a_hung_picture_gives_no_suggestions_until_solved_again():
    fresh()
    call(action="paint", cells=cells_of("hammer"), value=1)
    v = call(action="hint")
    assert v["ok"] is False and v["tally"]["hints"] == 0 and v["hint"] is None and v["hint_ui"]["available"] is False
    call(action="retry")
    assert call(action="hint")["ok"] is True


def test_the_highest_rung_asked_is_kept_per_picture_only_while_it_is_first_solved():
    fresh()
    pid = game.game.current
    call(action="hint")
    assert game.get_state()["hints"] == {pid: 1}
    call(action="hint"); call(action="hint", confirm=True)
    assert game.get_state()["hints"] == {pid: 3}
    call(action="paint", cells=cells_of(pid), value=1)                      # hangs it (the fill is part of the solve)
    v = call(action="open")
    assert v["galleries"][0]["frames"][0]["hinted"] is True
    call(action="retry")
    call(action="hint")
    assert game.get_state()["hints"] == {pid: 3} and game.get_state()["tally"]["hints"] == 4     # counted, record untouched


def test_a_picture_solved_without_asking_is_not_marked_hinted():
    fresh()
    pid = game.game.current
    v = call(action="paint", cells=cells_of(pid), value=1)
    assert v["galleries"][0]["frames"][0]["hinted"] is False and "hints" not in game.get_state()


@pytest.mark.parametrize("pid", [p.id for p in pictures.ALL][::6])
def test_pressing_through_the_ladder_alone_always_finishes_the_picture_and_never_places_a_wrong_cell(pid):
    fresh()
    for g in range(pictures.BY_ID[pid].gallery):                              # open the gallery
        for q in pictures.GALLERIES[g]["pictures"][:6]:
            game.game.solved[q.id] = 1
    call(action="pick", picture=pid)
    p = pictures.BY_ID[pid]
    sol = p.solution_grid()
    for _ in range(4 * (p.width + p.height)):
        v = call(action="hint")
        if v["picture"]["status"] == "solved":
            break
        v = call(action="hint")
        v = call(action="hint", confirm=True)
        for r in range(p.height):
            for c in range(p.width):
                mark = v["grid"][r][c] if v["picture"]["status"] != "solved" else None
                if mark == "#":
                    assert sol[r][c] == F
                elif mark == "x":
                    assert sol[r][c] != F
        if v["picture"]["status"] == "solved":
            break
    assert call(action="open")["picture"]["status"] == "solved"
    assert game.game.hinted[pid] == 3 or pid in game.game.solved


def test_a_wrong_mark_does_not_mislead_the_ladder_and_the_fill_replaces_it():
    fresh("hammer")
    p = pictures.BY_ID["hammer"]
    sol = p.solution_grid()
    wr, wc = next((r, c) for r in range(p.height) for c in range(p.width) if sol[r][c] != F)
    call(action="paint", cells=[[wr, wc]], value=1)
    for _ in range(40):
        v = call(action="hint")
        v = call(action="hint")
        v = call(action="hint", confirm=True)
        if v["grid"][wr][wc] != "#" or v["picture"]["status"] == "solved":
            break
    assert call(action="open")["grid"][wr][wc] != "#" or call(action="open")["picture"]["status"] == "solved"


# ---- Easy, Normal, Hard --------------------------------------------------------------------------------------------------------
def test_normal_is_the_default_and_a_bad_level_changes_nothing():
    fresh()
    assert call(action="open")["difficulty"] == "normal"
    v = call(action="difficulty", level="brutal")
    assert v["ok"] is False and v["difficulty"] == "normal"
    assert call(action="difficulty", level=3)["ok"] is False


def test_easy_opens_the_nudge_and_hint_together_and_the_fill_without_a_question():
    fresh()
    level("easy")
    v = call(action="open")
    assert v["hint_ui"]["opens_two"] is True and v["hint_ui"]["confirm"] is False
    v = call(action="hint")
    assert v["hint"]["rung"] == 2 and v["hint"]["nudge"] and v["hint"]["detail"] and v["tally"]["hints"] == 1
    assert v["hint_ui"]["next"] == 3 and v["hint_ui"]["confirm"] is False
    assert game.get_state()["hints"][game.game.current] == 2
    v = call(action="hint")                                                   # no confirm needed on Easy
    assert v["ok"] and v["hint"]["rung"] == 3 and v["hint"]["cells"] and v["tally"]["hints"] == 2


def test_hard_has_no_fill_step_so_the_two_first_rungs_are_all_there_is():
    fresh()
    level("hard")
    call(action="hint")
    v = call(action="hint")
    assert v["hint"]["rung"] == 2 and v["hint_ui"]["next"] == 0 and v["hint_ui"]["limit"] is True
    before = v["grid"]
    for confirm in (False, True):
        v = call(action="hint", confirm=confirm)
        assert v["ok"] is False and "Hard" in v["message"] and v["grid"] == before and v["hint"]["rung"] == 2
    assert v["tally"]["hints"] == 2 and v["tally"]["fills"] == 0


def test_changing_the_level_clears_a_ladder_opened_under_the_old_one():
    fresh()
    call(action="hint")
    assert level("hard")["hint"] is None


def test_the_level_is_never_saved_and_reset_and_load_leave_it_alone():
    fresh()
    level("hard")
    assert "difficulty" not in json.dumps(game.get_state())
    call(action="reset")
    assert call(action="open")["difficulty"] == "hard"
    game.load_state({"schema": 1})
    assert call(action="open")["difficulty"] == "hard"


def _scripted_session():
    """One fixed session: solve three pictures with exactly the same strokes (and one hint press on the first)."""
    fresh()
    out = []
    for pid in ("hammer", "key", "lantern"):
        call(action="pick", picture=pid)
        call(action="hint")
        out.append(call(action="paint", cells=cells_of(pid), value=1))
    return out


def test_the_level_never_lowers_a_record():
    """Hung pictures, best strokes, cells and the hung wall are the same on every level; only the ladder differs."""
    results = {}
    for name in ("normal", "easy", "hard"):
        level(name)
        views = _scripted_session()
        last = views[-1]
        results[name] = (last["totals"]["hung"], last["totals"]["cells"], [f["moves"] for f in last["galleries"][0]["frames"] if f["hung"]],
                         last["picture"]["best"], last["goals"])
    assert results["normal"] == results["easy"] == results["hard"]


def test_the_level_told_as_normal_changes_nothing_from_never_telling():
    fresh()
    never = [call(action="open")] + [call(action="paint", cells=[[0, 1]], value=1), call(action="hint")]
    state_never = game.get_state()
    fresh()
    level("normal")
    told = [call(action="open")] + [call(action="paint", cells=[[0, 1]], value=1), call(action="hint")]
    assert never == told and state_never == game.get_state()


# ---- saving ----------------------------------------------------------------------------------------------------------------------
def test_hints_and_the_hint_tally_round_trip_and_junk_is_dropped():
    fresh()
    call(action="hint"); call(action="hint")
    saved = game.get_state()
    assert saved["tally"]["hints"] == 2 and saved["hints"] == {game.game.current: 2}
    assert json.loads(json.dumps(saved)) == saved
    fresh()
    game.load_state(saved)
    assert game.get_state()["hints"] == saved["hints"] and call(action="open")["tally"]["hints"] == 2
    bad = dict(saved, hints={"hammer": 9, "nonsense": 1, "key": "x", "lantern": True, "flask": 0, "compass": 2})
    game.load_state(bad)
    assert game.get_state().get("hints") == {"compass": 2}
    game.load_state(dict(saved, hints=[1, 2]))
    assert "hints" not in game.get_state()


def test_a_hint_for_a_picture_in_a_closed_gallery_is_dropped_on_load():
    fresh()
    game.load_state({"schema": 1, "hints": {"airlock": 2}})
    assert "hints" not in game.get_state()


def test_an_old_save_without_any_hint_fields_loads_with_zero_hints():
    fresh()
    game.load_state({"schema": 1, "tally": {"fills": 5}})
    v = call(action="open")
    assert v["tally"]["hints"] == 0 and v["hint"] is None
