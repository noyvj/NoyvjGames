import json
from pathlib import Path

import achievements
import game
import rooms

GAME_DIR = Path(__file__).resolve().parent.parent
HTML = (GAME_DIR / "index.html").read_text(encoding="utf-8")
APP = (GAME_DIR / "app.js").read_text(encoding="utf-8")


def call(**req):
    return json.loads(game.handle(json.dumps(req)))


def test_manifest_matches_the_engine_table_and_has_fourteen():
    manifest = json.loads((GAME_DIR / "achievements.json").read_text(encoding="utf-8"))["achievements"]
    assert [m["id"] for m in manifest] == list(achievements.IDS) and len(manifest) == 14
    for entry, row in zip(manifest, achievements.ACHIEVEMENTS):
        assert entry == {"id": row[0], "label": row[1], "description": row[2]}


def test_every_achievement_has_a_visible_number_and_none_is_hidden():
    for a in achievements.view({}):
        assert a["need"] >= 1 and a["have"] == 0 and not a["earned"]
    assert "hidden" not in (GAME_DIR / "achievements.json").read_text(encoding="utf-8")


def test_totals_follow_the_game_size():
    by_id = {a[0]: a for a in achievements.ACHIEVEMENTS}
    assert by_id["perfect_script"][4] == len(rooms.ORDER) == 42
    assert by_id["shift_done"][4] == len(rooms.CHAPTER_LIST) == 6


def test_nothing_is_time_luck_or_streak_based():
    for _i, label, description, fact, _n, _c in achievements.ACHIEVEMENTS:
        for word in ("day", "week", "streak", "daily", "minute", "second", "random", "luck"):
            assert word not in description.lower().split(), (label, word)
        assert fact in {"rooms", "gold", "chapters_done", "flag_rep", "flag_call", "flag_branch", "flag_comeback", "rung3", "sbx"}


def test_the_panel_and_toast_are_wired_with_the_hub_hooks():
    for needle in ('id="achievements-panel"', 'id="achievements-list"', 'id="achievements-toggle-button"', 'data-game-name="Robot Script"'):
        assert needle in HTML
    assert "data-achievement-id" in APP and "data-achievement-label" in APP and "Achievement unlocked: " in APP


def test_earned_ids_are_written_to_the_save_and_never_read_back():
    game.game.__init__()
    game.game._enter("wake-up")
    game.game.ed.load(rooms.BY_ID["wake-up"].ref)
    call(action="run")
    state = game.get_state()
    assert "first_light" in state["achievements_earned"]
    game.game.__init__()
    game.load_state({"achievements_earned": list(achievements.IDS)})
    assert call(action="open")["totals"]["cleared"] == 0 and not any(a["earned"] for a in call(action="open")["achievements"])
