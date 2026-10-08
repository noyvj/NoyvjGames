"""Z-28: Continuum keeps its own season clock and speed buttons (U1); shared/pause-hidden.js only
adds the 'pause while the tab is hidden' hold on top of them, through two hooks written in index.html
(pause = remember the speed and set it to 0, resume = restore it). The JS is tested in
shared/tests/test_pause_hidden_browser.py; these pin the Continuum side."""

import json
import re
from pathlib import Path

GAME_DIR = Path(__file__).resolve().parent.parent


def _hold(m):
    """What the index.html hook does, step for step."""
    running = m.sim_speed
    if not running:
        return None
    m.set_speed(0)
    return running


def _release(m, saved):
    if saved and not m.sim_speed:
        m.set_speed(saved)


def test_holding_stops_the_clock_and_releasing_restores_the_players_speed(game_env):
    m = game_env.module
    m.set_speed(4)
    saved = _hold(m)
    assert saved == 4 and m.sim_speed == 0
    season = game_env.state.season
    for _ in range(100):
        assert m.tick_clock(1.0) == 0           # a hidden tab that still fires its timer moves nothing
    assert game_env.state.season == season and m.season_progress == 0.0
    _release(m, saved)
    assert m.sim_speed == 4
    assert "Running at 4x" in game_env.elements["season-clock-display"].innerText


def test_a_player_who_had_paused_gets_nothing_held_and_stays_paused(game_env):
    m = game_env.module
    assert m.sim_speed == 0                      # Continuum starts paused
    saved = _hold(m)
    assert saved is None
    _release(m, saved)
    assert m.sim_speed == 0


def test_the_clock_step_is_still_clamped_so_a_woken_tab_never_bursts(game_env):
    m = game_env.module
    m.set_speed(1)
    m.tick_clock(3600.0)                          # an hour in one step counts as at most one second
    assert m.season_progress <= 1.0 + 1e-9


def test_both_pages_have_the_setting_the_script_and_the_hooks():
    for name in ("index.html", "pc.html"):
        html = (GAME_DIR / name).read_text(encoding="utf-8")
        assert 'id="pause-hidden-checkbox"' in html
        assert 'shared/pause-hidden.js" data-game-id="continuum" data-manual' in html
        assert 'NoyvjPauseHidden.init({' in html and 'gameId: "continuum"' in html
        assert 'document.visibilityState === "visible" || (hold && !hold.enabled())' in html
        assert "shared/time-controls" not in html, "Continuum keeps its own speed buttons"


def test_the_existing_speed_buttons_are_the_only_speed_controls():
    html = (GAME_DIR / "index.html").read_text(encoding="utf-8")
    assert len(re.findall(r'id="speed-(?:pause|1x|2x|4x)-button"', html)) == 4
    cfg = json.loads((GAME_DIR / "pc-config.json").read_text(encoding="utf-8"))
    assert "#time-controls" not in json.dumps(cfg)
