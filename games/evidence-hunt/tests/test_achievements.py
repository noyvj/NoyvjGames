"""The 14 achievements: the manifest matches the code, every one can be earned from a clean save without luck, none is hidden or timed,
and `achievements_earned` is written to the save and never read back."""

import json
from pathlib import Path

import achievements
import game
import progress
from tests.helpers import call, solve_thoroughly, solve_with_hints

GAME_DIR = Path(__file__).resolve().parent.parent


def test_the_manifest_is_exactly_what_the_code_defines():
    manifest = json.loads((GAME_DIR / "achievements.json").read_text(encoding="utf-8"))["achievements"]
    assert [m["id"] for m in manifest] == list(achievements.IDS) and len(manifest) == 14
    for m, a in zip(manifest, achievements.ACHIEVEMENTS):
        assert m == {"id": a[0], "label": a[1], "description": a[2]}


def test_every_achievement_has_a_number_and_none_is_hidden_timed_or_luck_based():
    for _i, label, description, _fact, need, _chapter in achievements.ACHIEVEMENTS:
        assert need > 0 and label and description
    text = json.dumps([a[:3] for a in achievements.ACHIEVEMENTS]).lower()
    for word in ("secret", "hidden", "daily", "streak", "within", "minutes", "seconds", "luck", "random"):
        assert word not in text, word


def test_progress_is_reported_from_facts_so_a_loaded_save_agrees_with_a_played_one():
    game.game.__init__()
    call(action="open")
    solve_with_hints()
    played = game.game.view()["achievements"]
    state = json.loads(json.dumps(game.get_state()))
    game.game.__init__()
    game.load_state(state)
    assert game.game.view()["achievements"] == played


def test_earned_is_written_to_the_save_and_never_read_back():
    game.game.__init__()
    call(action="open")
    solve_with_hints()
    state = game.get_state()
    assert state["achievements_earned"] == ["first_case"]
    game.game.__init__()
    game.load_state({"achievements_earned": list(achievements.IDS)})
    assert game.get_state() == {} and game.game.view()["achievements"][0]["earned"] is False


def test_all_fourteen_can_be_earned_from_a_clean_save():
    game.game.__init__()
    call(action="open")
    for i, cid in enumerate(progress.ORDER):
        call(action="pick", case=cid)
        if i < 5:
            call(action="cover")                                  # five different cases solved with the sheet covered
        v = solve_with_hints()
        assert v["result"]["grade_name"] == "Clean"
    for d in (1, 2, 3):
        call(action="practice", difficulty=d)
        solve_with_hints()
    for cid in progress.ORDER:
        solve_thoroughly(cid)
        if game.compiled(cid).keep_room >= 0:
            call(action="return")
    v = call(action="open")
    assert [a["id"] for a in v["achievements"] if not a["earned"]] == [], [a for a in v["achievements"] if not a["earned"]]
    assert game.get_state()["achievements_earned"] == list(achievements.IDS)
    assert v["goals"] == [] and v["guide"]["found"] == 37 and v["tally"]["sandbox"] == 3 and len(game.game.mem) == 5
