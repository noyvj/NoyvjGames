"""AN-17: Easy / Normal / Hard. Stranded has no par, medals or seals (you cannot do badly at a story), so difficulty is only the help:
Easy opens the nudge and the hint together and lets the What if? peek open after one reply tried; Hard has no answer step and no
loose-end jump. Nothing about the story, the replies, the stats or the endings changes on any difficulty."""

import json

import pytest

import achievements
import explore
import game


def call(**req):
    return json.loads(game.handle(json.dumps(req)))


@pytest.fixture(autouse=True)
def clean():
    game.game.__init__()
    call(action="difficulty", level="normal")
    yield
    call(action="difficulty", level="normal")
    game.game.__init__()


def play(path):
    v = None
    for ch in path:
        v = call(action="choose", i=int(ch))
        assert v["ok"], (path, ch, v["message"])
    return v


# ---- Normal is today's game --------------------------------------------------------------------
def script():
    out = [call(action="open"), play("0"), call(action="hint")]
    out += [call(action="hint"), call(action="hint"), call(action="hint_do"), call(action="peek")]
    out += [play("1"), call(action="restart"), call(action="peek"), call(action="loose"), call(action="open")]
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


def test_each_hint_rung_is_in_the_view_only_once_it_has_been_asked_for():
    """Bug found while building AN-17: the view used to carry the hint and the answer (and its jump button) from the first press."""
    play("0")
    assert call(action="open")["hint"] == {"rung": 0, "max": 3}
    v = call(action="hint")
    assert v["hint"]["rung"] == 1 and v["hint"]["nudge"] and "hint" not in v["hint"] and "answer" not in v["hint"] and "do" not in v["hint"]
    v = call(action="hint")
    assert v["hint"]["rung"] == 2 and v["hint"]["hint"] and "answer" not in v["hint"] and "do" not in v["hint"]
    v = call(action="hint")
    assert v["hint"]["rung"] == 3 and v["hint"]["answer"] and v["hint"]["do"] and v["hint"]["max"] == 3
    assert call(action="hint")["message"] == "That is every rung: the answer is showing."


def test_normal_peek_needs_two_different_replies():
    assert call(action="open")["peek"]["need"] == 2
    play("0")
    call(action="restart")
    assert call(action="open")["peek"] == {"open": False, "need": 1, "showing": False, "rows": []}
    assert call(action="peek")["message"] == "Try 1 more different reply here first."


def test_a_bad_difficulty_is_refused_and_changes_nothing():
    call(action="difficulty", level="hard")
    for bad in ("extreme", "", None, 3, ["easy"], "HARD"):
        v = call(action="difficulty", level=bad)
        assert v["ok"] is False and v["message"] == "That is not a difficulty." and v["difficulty"] == "hard"


def test_the_difficulty_is_never_saved_and_never_touches_the_story():
    play("0000")
    saved = json.dumps(game.get_state(), sort_keys=True)
    before = call(action="open")
    for level in ("hard", "easy", "normal"):
        v = call(action="difficulty", level=level)
        assert v["run"] == before["run"] and v["stats"] == before["stats"] and v["transcript"] == before["transcript"]
        assert v["choices"] == before["choices"] and v["progress"] == before["progress"]
    assert json.dumps(game.get_state(), sort_keys=True) == saved and "difficulty" not in saved and "hard" not in saved


# ---- Easy --------------------------------------------------------------------------------------
def test_easy_first_press_opens_the_nudge_and_the_hint_together():
    play("0")
    call(action="difficulty", level="easy")
    v = call(action="hint")
    assert v["hint"]["rung"] == 2 and v["hint"]["nudge"] and v["hint"]["hint"] and "answer" not in v["hint"]
    v = call(action="hint")
    assert v["hint"]["rung"] == 3 and v["hint"]["answer"] and v["tally"]["hints"] == 2
    assert call(action="hint_do")["ok"]


def test_easy_peek_opens_after_one_reply_is_tried_in_a_scene():
    call(action="difficulty", level="easy")
    v = call(action="open")
    assert not v["peek"]["open"] and v["peek"]["need"] == 1
    assert not call(action="peek")["ok"]
    play("0")
    call(action="restart")
    v = call(action="peek")
    assert v["ok"] and v["peek"]["showing"] and len(v["peek"]["rows"]) == 3 and v["tally"]["peeks"] == 1
    assert [r["tried"] for r in v["peek"]["rows"]] == [True, False, False]
    assert call(action="difficulty", level="normal")["peek"]["need"] == 1       # two are needed on Normal, one is tried


def test_explore_peek_default_is_two():
    call(action="open")
    state = game.game.state
    assert explore.peek(state, set())["need"] == 2 == explore.peek(state, set(), 2)["need"]
    assert explore.peek(state, set(), 1)["need"] == 1


# ---- Hard --------------------------------------------------------------------------------------
def test_hard_has_no_answer_step():
    play("0")
    call(action="difficulty", level="hard")
    v = call(action="hint")
    assert v["hint"]["rung"] == 1 and v["hint"]["max"] == 2
    v = call(action="hint")
    assert v["hint"]["rung"] == 2 and v["hint"]["hint"] and "answer" not in v["hint"] and "do" not in v["hint"]
    v = call(action="hint")
    assert v["ok"] is False and "no answer step" in v["message"] and game.game.rung == 2
    path, hints = game.game.path, game.game.tally["jumps"] + game.game.tally["rewinds"]
    v = call(action="hint_do")
    assert v["ok"] is False and "no answer step" in v["message"] and game.game.path == path
    v = call(action="loose")
    assert v["ok"] is False and "no answer step" in v["message"] and game.game.path == path
    assert game.game.tally["jumps"] + game.game.tally["rewinds"] == hints


def test_hard_hides_the_answer_even_when_normal_already_opened_it():
    play("0")
    for _ in range(3):
        call(action="hint")
    v = call(action="difficulty", level="hard")
    assert v["hint"]["rung"] == 2 and "answer" not in v["hint"] and game.game.rung == 3
    assert call(action="difficulty", level="normal")["hint"]["answer"]


def test_hard_keeps_the_what_if_peek_as_it_is_on_normal():
    call(action="difficulty", level="hard")
    assert call(action="open")["peek"]["need"] == 2


def test_the_story_is_completable_on_hard_without_the_answer_step():
    """Walk loose ends with the engine's own search (the same one the answer step uses) as a player who found them unaided."""
    call(action="difficulty", level="hard")
    for _round in range(60):
        le = explore.loose_end(game.game.taken, game.game.path)
        if le is None:
            break
        game.game.path = game.game.path[:le["step"]] if le["kind"] == "rewind" else le["path"]
        game.game._sync()
        assert game.game.choose(le["choice"])[0], le
    assert len(game.game.taken) > 30
    assert call(action="hint_do")["ok"] is False


def test_achievements_and_goals_are_the_same_whatever_the_difficulty():
    def walk():
        for _round in range(25):
            le = explore.loose_end(game.game.taken, game.game.path)
            if le is None:
                break
            game.game.path = game.game.path[:le["step"]] if le["kind"] == "rewind" else le["path"]
            game.game._sync()
            game.game.choose(le["choice"])
        return achievements.earned(game.game.facts()), achievements.goals(game.game.facts())
    normal = walk()
    game.game.__init__()
    call(action="difficulty", level="hard")
    assert walk() == normal
    assert normal[0]


def test_the_hint_view_only_changes_with_the_difficulty_not_the_story_graph():
    play("0")
    views = {}
    for level in ("easy", "normal", "hard"):
        call(action="difficulty", level=level)
        game.game.rung = 0
        views[level] = call(action="hint")["hint"]["nudge"]
    assert len(set(views.values())) == 1
