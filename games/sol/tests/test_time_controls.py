"""W-2 / Z-28: SOL hands its tick to shared/time-controls.js (pause and 1x/2x/4x) and
shared/pause-hidden.js holds it while the tab is hidden. The JS behaviour itself is tested in
shared/tests/test_time_controls_browser.py and test_pause_hidden_browser.py; these tests pin the
SOL side: the wiring, the fallback, that the tick never knows about speed, and that a paused
game does not move."""

import re
import sys
import types
from pathlib import Path

GAME_DIR = Path(__file__).resolve().parent.parent
SLUG = "sol"


class FakeController:
    """Stands in for window.NoyvjTime: records start(), and models the two gates (the player's pause and a
    hold) so a test can 'run real time' through it. Speed only changes how many times tick() is called."""

    def __init__(self):
        self.started = []
        self.paused = False
        self.holds = set()
        self.speed = 1
        self._tick = None

    def start(self, game_id, tick, base_ms):
        self.started.append((game_id, tick, base_ms))
        self._tick = tick
        return True

    def run(self, seconds, base_ms):
        """Calls the tick as often as the real controller would in `seconds` of wall time."""
        if self.paused or self.holds:
            return 0
        calls = int(seconds * 1000 / (base_ms / self.speed))
        for _ in range(calls):
            self._tick()
        return calls


def install_controller():
    controller = FakeController()
    window = types.SimpleNamespace(NoyvjTime=controller)
    sys.modules["js"].window = window
    return controller


def uninstall():
    if hasattr(sys.modules["js"], "window"):
        del sys.modules["js"].window


def test_without_the_shared_script_the_game_keeps_its_own_interval(game_env):
    intervals = game_env.timers.intervals
    assert len(intervals) == 1
    assert intervals[0][1] == game_env.module.TICK_INTERVAL_MS


def test_with_the_shared_script_the_tick_is_handed_over_and_no_second_timer_is_made(game_env):
    controller = install_controller()
    try:
        before = len(game_env.timers.intervals)
        assert game_env.module._start_tick_loop() == "shared"
        assert len(game_env.timers.intervals) == before
        assert [(g, b) for g, _t, b in controller.started] == [(SLUG, game_env.module.TICK_INTERVAL_MS)]
    finally:
        uninstall()


def test_the_handed_over_tick_is_the_games_own_tick(game_env):
    controller = install_controller()
    try:
        game_env.module._start_tick_loop()
        before = game_env.module.total_ticks
        controller.started[0][1]()
        assert game_env.module.total_ticks == before + 1
    finally:
        uninstall()


def test_a_missing_start_method_falls_back_to_the_interval(game_env):
    sys.modules["js"].window = types.SimpleNamespace(NoyvjTime=object())
    try:
        before = len(game_env.timers.intervals)
        assert game_env.module._start_tick_loop() == "interval"
        assert len(game_env.timers.intervals) == before + 1
    finally:
        uninstall()


def test_paused_or_held_means_no_tick_and_no_change_to_the_game(game_env):
    controller = install_controller()
    try:
        m = game_env.module
        m._start_tick_loop()
        controller.run(5, m.TICK_INTERVAL_MS)
        frozen = repr(m.get_state())
        counter = m.total_ticks
        controller.paused = True
        assert controller.run(600, m.TICK_INTERVAL_MS) == 0
        controller.paused = False
        controller.holds.add("hidden")
        assert controller.run(600, m.TICK_INTERVAL_MS) == 0
        assert m.total_ticks == counter and repr(m.get_state()) == frozen
        controller.holds.clear()
        controller.run(1, m.TICK_INTERVAL_MS)
        assert m.total_ticks > counter      # resumes with ordinary ticks, no burst to catch up
    finally:
        uninstall()


def test_fast_forward_is_more_ticks_never_a_different_tick(game_env):
    controller = install_controller()
    try:
        m = game_env.module
        m._start_tick_loop()
        base = m.total_ticks
        controller.speed = 4
        calls = controller.run(10, m.TICK_INTERVAL_MS)
        assert calls == 4 * 10 * 1000 // m.TICK_INTERVAL_MS
        assert m.total_ticks == base + calls        # each call advanced the counter by exactly one tick
    finally:
        uninstall()


def test_the_tick_and_the_rules_never_read_the_speed():
    source = (GAME_DIR / "game.py").read_text(encoding="utf-8")
    code = re.sub(r"def _start_tick_loop\(\):.*?return \"interval\"\n", "", source, flags=re.S)
    assert "NoyvjTime" not in code, "only _start_tick_loop may talk to the time controller"


def test_both_pages_carry_the_controls_the_setting_and_the_scripts():
    for name in ("index.html", "pc.html"):
        html = (GAME_DIR / name).read_text(encoding="utf-8")
        assert 'id="time-controls"' in html and 'id="pause-hidden-checkbox"' in html
        assert 'shared/time-controls.js" data-game-id="%s"' % SLUG in html
        assert 'shared/pause-hidden.js" data-game-id="%s"' % SLUG in html
        assert "shared/time-controls.css" in html
        assert html.index("shared/time-controls.js") < html.index("shared/pause-hidden.js")


def test_the_desktop_boot_has_the_controls_in_the_stage_bar_and_the_keys_in_the_hints():
    import json
    cfg = json.loads((GAME_DIR / "pc-config.json").read_text(encoding="utf-8"))
    assert "#time-controls" in cfg["zones"]["stagebar"]
    keys = [k for k, _label in cfg["hints"]]
    assert "Space" in keys and "[ ]" in keys


def test_the_away_report_counts_game_ticks_so_hidden_time_adds_nothing(game_env):
    """A5's 'while you were away' report is measured in simulated ticks (TICK_INTERVAL_MS each), not in
    wall-clock time. A hidden tab runs no ticks, so ten minutes hidden leaves the report exactly where it
    was: nothing to report yet; only real ticks make it grow."""
    controller = install_controller()
    try:
        m = game_env.module
        m._start_tick_loop()
        m._snapshot_departure("Earth")
        controller.holds.add("hidden")
        assert controller.run(600, m.TICK_INTERVAL_MS) == 0
        m._report_arrival("Earth")
        assert game_env.elements["away-report"].hidden is not False      # still nothing to report
        m._snapshot_departure("Earth")
        controller.holds.clear()
        controller.run(m.AWAY_REPORT_MIN_TICKS * m.TICK_INTERVAL_MS / 1000, m.TICK_INTERVAL_MS)
        m._report_arrival("Earth")
        text = game_env.elements["away-report-text"].innerText
        assert text.startswith("While you were away from") and "(10s)" in text
        assert game_env.elements["away-report"].hidden is False
    finally:
        uninstall()


def test_the_report_is_in_game_time_so_fast_forward_reports_more_game_time_per_second(game_env):
    controller = install_controller()
    try:
        m = game_env.module
        m._start_tick_loop()
        m._snapshot_departure("Earth")
        controller.speed = 4
        controller.run(10, m.TICK_INTERVAL_MS)          # ten real seconds at 4x = forty game seconds
        m._report_arrival("Earth")
        assert "(40s)" in game_env.elements["away-report-text"].innerText
    finally:
        uninstall()
