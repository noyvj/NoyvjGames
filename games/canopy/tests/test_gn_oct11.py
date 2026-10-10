"""GN-3 (Next level button) and GN-4 (the badge frame no longer sits above the map)."""
import json
import re
from pathlib import Path

GAME_DIR = Path(__file__).resolve().parent.parent
INDEX = (GAME_DIR / "index.html").read_text(encoding="utf-8")
PC = (GAME_DIR / "pc.html").read_text(encoding="utf-8")
CONFIG = json.loads((GAME_DIR / "pc-config.json").read_text(encoding="utf-8"))


def _finish(env, limit=400):
    for _ in range(limit):
        if env.module.level_done_tick is not None:
            return True
        env.tick()
    return False


def test_next_level_is_hidden_until_the_level_is_finished(game_env):
    m = game_env.module
    m.start_level("wren_hollow", force=True)
    assert game_env.elements["level-next-button"].hidden is True
    assert m.on_next_level() is False


def test_next_level_appears_beside_leave_level_and_starts_the_next_one(game_env):
    m = game_env.module
    m.start_level("wren_hollow", force=True)
    assert _finish(game_env)
    m.render_level_status()
    button = game_env.elements["level-next-button"]
    assert button.hidden is False and button.disabled is False
    assert "Next level" in button.innerText
    assert game_env.elements["level-leave-button"].disabled is False
    button.dispatch("click", None)
    assert m.current_level == m.LEVEL_ORDER[1]
    assert m.level_ticks == 0 and m.level_done_tick is None
    assert game_env.elements["level-next-button"].hidden is True


def test_next_level_is_disabled_with_the_reason_when_the_next_level_is_locked(game_env):
    m = game_env.module
    m.start_level("wren_hollow", force=True)
    _finish(game_env)
    m.levels_state["done"] = []  # the next level wants wren_hollow done
    m.render_level_status()
    button = game_env.elements["level-next-button"]
    assert button.disabled is True and button.title
    assert m.on_next_level() is False


def test_the_last_level_has_no_next_level(game_env):
    m = game_env.module
    m.start_level(m.LEVEL_ORDER[-1], force=True)
    m.level_done_tick = 5
    m.render_level_status()
    assert m.next_level_id() is None
    assert game_env.elements["level-next-button"].hidden is True


def test_next_level_button_exists_on_both_pages_next_to_leave_level():
    for html in (INDEX, PC):
        assert re.search(r'<button id="level-next-button"[^>]*hidden>[^<]*</button>\s*<button id="level-leave-button"', html)


def test_forest_rank_panel_is_not_in_the_flow_above_the_map():
    assert INDEX.index('id="forest-rank-panel"') > INDEX.index('id="plot-grid"')


def test_forest_rank_panel_is_its_own_window_in_the_desktop_layout():
    composites = [c for c in CONFIG["composites"] if "#forest-rank-panel" in c["members"]]
    assert len(composites) == 1
    for ids in CONFIG["zones"].values():
        assert "#forest-rank-panel" not in ids
    assert 'id="forest-frame-select"' in PC and 'id="forest-palette-select"' in PC
