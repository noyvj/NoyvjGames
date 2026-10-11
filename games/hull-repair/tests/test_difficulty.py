"""AN-17: Easy / Normal / Hard. Hull Repair has no par or medals (a board is open, patched or restored), so difficulty is only the
hint ladder: Easy opens the nudge and the hint together and shows more of the starting line, Hard has no answer step. Normal is the
game exactly as it always was (pinned below); the rules, the boards and what counts as restored never change."""

import json

import pytest

import achievements
import boards
import game
import hints
import progress
import rules
from tests.test_game_handle import lay


def call(**req):
    return json.loads(game.handle(json.dumps(req)))


@pytest.fixture(autouse=True)
def clean():
    game.game.__init__()
    call(action="difficulty", level="normal")
    yield
    call(action="difficulty", level="normal")
    game.game.__init__()


def long_board():
    """A board whose starting line is longer than the Normal opening, so Easy's longer hint shows."""
    for b in boards.ALL_BOARDS:
        c = hints.starter(b)
        if len(b.solution[c]) > hints.OPENING + 2:
            return b
    raise AssertionError("no board with a long starting line")


# ---- Normal is today's game --------------------------------------------------------------------
def script():
    out = []
    first, second = boards.ORDER[0], boards.ORDER[1]
    out.append(call(action="open"))
    for _ in range(3):
        out.append(call(action="hint"))
    out.append(call(action="load_answer"))
    out.append(call(action="undo"))
    out.append(call(action="pick", board=second))
    for _ in range(2):
        out.append(call(action="hint"))
    out.append(call(action="clear"))
    out.append(call(action="pick", board=first))
    out.append(call(action="open"))
    return json.dumps(out, sort_keys=True), json.dumps(game.get_state(), sort_keys=True)


def test_normal_is_byte_for_byte_the_same_with_or_without_being_told():
    plain = script()
    game.game.__init__()
    call(action="difficulty", level="normal")
    assert script() == plain


def test_a_detour_through_hard_and_easy_leaves_no_trace():
    plain = script()
    game.game.__init__()
    for level in ("hard", "easy", "normal"):
        call(action="difficulty", level=level)
    assert script() == plain


def test_the_helper_defaults_are_the_normal_ladder_for_every_board():
    for b in boards.ALL_BOARDS:
        for rung in range(4):
            assert hints.view(b, rung) == dict(hints.view(b, rung, 3, False))
            assert hints.view(b, rung)["max"] == 3
            assert hints.ghosts(b, rung) == hints.ghosts(b, rung, 3, False)
        assert hints.hint_text(b) == hints.hint_text(b, False)
        assert hints.opening(b) == hints.opening(b, False)
        assert len(hints.opening(b)[1]) == min(len(b.solution[hints.starter(b)]), hints.OPENING + 1)


def test_normal_hint_ladder_is_unchanged():
    v = [call(action="hint") for _ in range(3)]
    assert [x["hint"]["rung"] for x in v] == [1, 2, 3] and v[2]["hint"]["answer"] is True and v[2]["hint"]["max"] == 3
    assert v[1]["layer"].count("hr-ghost") == 1 and v[2]["layer"].count("hr-ghost") == len(game.game.board.lines)
    assert call(action="hint")["message"] == "That is every rung: the answer is showing."
    before = call(action="open")["board"]["empty"]
    assert call(action="load_answer")["board"]["empty"] == 0 and before > 0


def test_a_bad_difficulty_is_refused_and_changes_nothing():
    call(action="difficulty", level="hard")
    for bad in ("extreme", "", None, 3, ["easy"], "HARD"):
        v = call(action="difficulty", level=bad)
        assert v["ok"] is False and v["message"] == "That is not a difficulty." and v["difficulty"] == "hard"


def test_the_difficulty_is_never_saved():
    call(action="difficulty", level="hard")
    lay(boards.ORDER[0])
    assert "difficulty" not in json.dumps(game.get_state()) and "hard" not in json.dumps(game.get_state())


def test_changing_the_difficulty_does_not_touch_the_board_or_the_progress():
    lay(boards.ORDER[0])
    before = json.dumps(game.get_state(), sort_keys=True)
    paths = call(action="open")["board"]["paths"]
    for level in ("hard", "easy", "normal"):
        v = call(action="difficulty", level=level)
        assert v["board"]["paths"] == paths
    assert json.dumps(game.get_state(), sort_keys=True) == before


# ---- Easy --------------------------------------------------------------------------------------
def test_easy_first_press_opens_the_nudge_and_the_hint_together():
    call(action="difficulty", level="easy")
    v = call(action="hint")
    assert v["hint"]["rung"] == 2 and v["hint"]["nudge"] and v["hint"]["hint"] and v["hint"]["answer"] is False
    assert v["layer"].count("hr-ghost") == 1
    v = call(action="hint")
    assert v["hint"]["rung"] == 3 and v["hint"]["answer"] is True
    assert game.game.tally["hints"] == 2


def test_easy_hint_shows_a_longer_start_of_the_same_line():
    b = long_board()
    call(action="pick", board=b.id)
    normal = hints.ghosts(b, 2)
    easy = hints.ghosts(b, 2, 3, True)
    c = hints.starter(b)
    assert list(normal) == list(easy) == [c]
    assert len(easy[c]) == min(len(b.solution[c]), hints.EASY_OPENING + 1) > len(normal[c])
    assert easy[c][:len(normal[c])] == normal[c]
    call(action="difficulty", level="easy")
    v = call(action="hint")
    assert v["layer"].count("hr-ghost") == 1
    assert hints.hint_text(b, True) != hints.hint_text(b) and v["hint"]["hint"] == hints.hint_text(b, True)


def test_easy_never_changes_what_counts_as_patched_or_restored():
    call(action="difficulty", level="easy")
    v = lay(boards.ORDER[0])
    assert v["board"]["status_name"] == "restored" and v["totals"]["restored"] == 1


# ---- Hard --------------------------------------------------------------------------------------
def test_hard_has_no_answer_step_at_all():
    call(action="difficulty", level="hard")
    v = call(action="hint")
    assert v["hint"]["rung"] == 1 and v["hint"]["max"] == 2
    v = call(action="hint")
    assert v["hint"]["rung"] == 2 and v["hint"]["hint"] and v["hint"]["answer"] is False and v["layer"].count("hr-ghost") == 1
    v = call(action="hint")
    assert v["ok"] is False and "no answer step" in v["message"] and game.game.rungs[game.game.current] == 2
    before = json.dumps(call(action="open")["board"]["paths"], sort_keys=True)
    v = call(action="load_answer")
    assert v["ok"] is False and "no answer step" in v["message"] and json.dumps(v["board"]["paths"], sort_keys=True) == before


def test_hard_hides_the_answer_even_when_normal_already_opened_it():
    for _ in range(3):
        call(action="hint")
    v = call(action="difficulty", level="hard")
    assert v["hint"]["rung"] == 2 and v["hint"]["answer"] is False and v["layer"].count("hr-ghost") == 1
    assert game.game.rungs[game.game.current] == 3
    assert call(action="difficulty", level="normal")["hint"]["answer"] is True


def test_every_board_can_be_restored_on_hard_by_drawing_alone():
    call(action="difficulty", level="hard")
    for bid in boards.ORDER:
        v = lay(bid)
        assert v["board"]["status_name"] == "restored", bid
    assert call(action="open")["totals"]["restored"] == len(boards.ORDER)


def test_achievements_are_the_same_on_every_difficulty_except_the_one_that_needs_the_answer_rung():
    def play():
        for bid in boards.ORDER:
            lay(bid)
        call(action="pick", board=boards.ORDER[0])
        for _ in range(3):
            call(action="hint")
        return achievements.earned(game.game.facts())
    normal = play()
    game.game.__init__()
    call(action="difficulty", level="hard")
    hard = play()
    assert "second_opinion" in normal and "second_opinion" not in hard        # Hard has no answer rung: reachable on Normal (and Easy)
    assert [a for a in normal if a != "second_opinion"] == hard
    game.game.__init__()
    call(action="difficulty", level="easy")
    assert play() == normal


def test_the_rung_three_achievement_is_reachable_on_normal():
    for _ in range(3):
        call(action="hint")
    assert game.game.facts()["rung3"] == 1


def test_hard_stops_at_two_rungs_so_the_rung_three_fact_is_a_normal_or_easy_thing():
    call(action="difficulty", level="hard")
    for _ in range(5):
        call(action="hint")
    assert game.game.facts()["rung3"] == 0 and progress.totals(game.game.st)["rooms"] == len(boards.ORDER)


def test_a_save_made_on_any_difficulty_loads_the_same():
    lay(boards.ORDER[0])
    normal = json.dumps(game.get_state(), sort_keys=True)
    game.game.__init__()
    call(action="difficulty", level="hard")
    lay(boards.ORDER[0])
    assert json.dumps(game.get_state(), sort_keys=True) == normal
    assert rules.STATUS_NAMES[2] == "restored"
