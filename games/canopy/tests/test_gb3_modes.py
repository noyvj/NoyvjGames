"""GB batch 3: Poacher Patrol (GB-13), Storm Front (GB-15) and the Spirit's Walk (GB-16), run as levels."""

import json

from .gb_helpers import tile

# --- GB-13 Poacher Patrol ---------------------------------------------------------------------------------------


def _start(env, level_id):
    env.module.start_level(level_id, force=True)
    return env.module


def _tick_to_poacher(env, limit=80):
    m = env.module
    for _ in range(limit):
        if m.poacher_run["plot"] is not None:
            return m.poacher_run["plot"]
        env.tick()
    raise AssertionError("no poacher appeared")


def test_there_are_no_poachers_outside_their_level(game_env):
    m = game_env.module
    game_env.tick(40)
    assert m.poacher_run == {} and m._active_poacher_plot() is None
    assert not any("plot-poacher" in game_env.elements[f"plot-{p.index}"].className for p in m.plots)
    assert m.drive_off_poacher() is False


def test_the_first_poacher_arrives_on_schedule_and_is_marked(game_env):
    m = _start(game_env, "poacher_patrol")
    game_env.tick(m.POACHER_FIRST_TICKS - 1)
    assert m.poacher_run["plot"] is None
    game_env.tick()
    index = m.poacher_run["plot"]
    assert index is not None and m.plots[index].state in m.ACCRUING_STATES
    assert m.poacher_run["ticks_left"] == m.POACHER_STAY_TICKS
    element = tile(game_env, index)
    assert "plot-poacher" in element.className  # an outline class and a glyph, not motion alone
    assert [c.className for c in element.children if "poacher-mark" in c.className]
    assert "POACHER" in element.getAttribute("aria-label")
    assert "poacher" in game_env.elements["level-status"].innerText.lower()


def test_clicking_the_poachers_plot_drives_it_off(game_env):
    m = _start(game_env, "poacher_patrol")
    index = _tick_to_poacher(game_env)
    before = m.plots[index].value
    game_env.select_tile_click(index)
    assert m.poacher_run["driven"] == 1 and m.poacher_run["plot"] is None
    assert m.plots[index].value >= before  # nothing was taken
    assert "1 of 8" in game_env.elements["level-status"].innerText
    assert any("Drove off" in e["text"] for e in m.forest_log)


def test_clicking_another_plot_does_not_count(game_env):
    m = _start(game_env, "poacher_patrol")
    index = _tick_to_poacher(game_env)
    other = (index + 1) % len(m.plots)
    game_env.select_tile_click(other)
    assert m.poacher_run["driven"] == 0 and m.poacher_run["plot"] == index


def test_the_p_key_drives_it_off_wherever_it_is(game_env):
    m = _start(game_env, "poacher_patrol")
    assert m.hotkey_drive_off_poacher() is False
    _tick_to_poacher(game_env)
    assert m.hotkey_drive_off_poacher() is True
    assert m.poacher_run["driven"] == 1


def test_a_poacher_left_alone_strikes_and_takes_a_quarter(game_env):
    m = _start(game_env, "poacher_patrol")
    index = _tick_to_poacher(game_env)
    for _ in range(m.POACHER_STAY_TICKS - 1):
        game_env.tick()
    assert m.poacher_run["plot"] == index
    before = m.plots[index].value
    game_env.tick()
    assert m.poacher_run["plot"] is None and m.poacher_run["missed"] == 1
    # the strike takes a quarter, then the same tick's growth is not part of it (accrual comes first)
    assert m.plots[index].value < before
    assert abs(m.plots[index].value - before * (1 - m.POACHER_LOSS_FRACTION)) < before * 0.1
    assert any("struck" in e["text"] for e in m.forest_log)


def test_a_poacher_gives_up_on_a_plot_you_cleared(game_env):
    m = _start(game_env, "poacher_patrol")
    index = _tick_to_poacher(game_env)
    game_env.select(index)
    game_env.clear()
    game_env.tick()
    assert m.poacher_run["plot"] is None and m.poacher_run["missed"] == 0


def test_poachers_stay_a_tick_less_every_three_driven_off(game_env):
    m = _start(game_env, "poacher_patrol")
    assert m.poacher_stay_ticks() == m.POACHER_STAY_TICKS
    m.poacher_run["driven"] = 3
    assert m.poacher_stay_ticks() == m.POACHER_STAY_TICKS - 1
    m.poacher_run["driven"] = 99
    assert m.poacher_stay_ticks() == m.POACHER_MIN_STAY_TICKS


def test_eight_driven_off_completes_with_the_missed_count_as_the_result(game_env):
    m = _start(game_env, "poacher_patrol")
    for _ in range(400):
        if m.level_done_tick is not None:
            break
        if m.poacher_run["plot"] is not None:
            m.drive_off_poacher()
        game_env.tick()
    assert m.level_done_tick is not None and m.poacher_run["driven"] == 8
    assert m.levels_state["best"]["poacher_patrol"] == {"value": 0, "text": "0 missed"}
    assert m._active_poacher_plot() is None  # a won level stops sending poachers
    game_env.tick(30)
    assert m.poacher_run["plot"] is None


def test_poacher_picks_repeat_exactly(game_env):
    """No randomness: two identical runs see the same poachers on the same plots."""
    def run():
        m = _start(game_env, "poacher_patrol")
        seen = []
        for _ in range(60):
            if m.poacher_run["plot"] is not None:
                seen.append((m.forest_tick, m.poacher_run["plot"]))
                m.drive_off_poacher()
            game_env.tick()
        return seen
    assert run() == run()


def test_poacher_state_round_trips(game_env):
    m = _start(game_env, "poacher_patrol")
    index = _tick_to_poacher(game_env)
    game_env.tick()
    state = json.loads(json.dumps(m.get_state()))
    saved = dict(m.poacher_run)
    m.start_level("wren_hollow", force=True)
    m.load_state(state)
    assert m.current_level == "poacher_patrol" and m.poacher_run["plot"] == index
    assert m.poacher_run["ticks_left"] == saved["ticks_left"] and m.poacher_run["driven"] == saved["driven"]


def test_a_saved_poacher_on_a_plot_that_is_no_longer_standing_is_dropped(game_env):
    m = _start(game_env, "poacher_patrol")
    state = m.get_state()
    state["level_run"]["poacher"] = {"plot": 3, "ticks_left": 2, "driven": 1, "missed": 0, "next_in": 4}
    state["plots"][3]["state"] = "bare"
    m.load_state(state)
    assert m.poacher_run["plot"] is None and m.poacher_run["ticks_left"] == 0


# --- GB-15 Storm Front ---------------------------------------------------------------------------------------------

def test_storm_level_starts_with_a_ragged_canopy(game_env):
    m = _start(game_env, "storm_front")
    bare = [p for p in m.plots if p.state == m.BARE]
    assert len(bare) == 9  # a quarter of 36
    assert all(p.clear_count == 0 for p in bare)  # nothing counts as a clear


def test_storm_bands_are_two_rows_and_deterministic(game_env):
    m = _start(game_env, "storm_front")
    for front in range(1, 9):
        rows = m._storm_band_rows(front)
        assert len(rows) == 2 and rows[1] == rows[0] + 1 and 0 <= rows[0] and rows[1] < m.GRID_ROWS
        assert rows == m._storm_band_rows(front)
    m.start_level("fern_glade", force=True)  # a 4x4 grid still fits a two-row band
    assert all(max(m._storm_band_rows(n)) < 4 for n in range(1, 20))


def test_the_band_is_shown_only_in_the_warning_window(game_env):
    m = _start(game_env, "storm_front")
    game_env.tick(m.STORM_INTERVAL_TICKS - m.STORM_WARNING_TICKS - 1)
    assert m._storm_warning_rows() == ()
    assert not any("plot-storm-warning" in game_env.elements[f"plot-{p.index}"].className for p in m.plots)
    game_env.tick()
    rows = m._storm_warning_rows()
    assert rows == m._storm_band_rows(1)
    warned = [p.index for p in m.plots if "plot-storm-warning" in game_env.elements[f"plot-{p.index}"].className]
    assert sorted(warned) == sorted(i for i in range(len(m.plots)) if i // m.GRID_COLS in rows)
    first = game_env.elements[f"plot-{warned[0]}"]
    assert [c.className for c in first.children if "storm-mark" in c.className]
    assert "storm front" in first.getAttribute("aria-label")
    assert "front in" in game_env.elements["level-status"].innerText


def test_exposed_plots_lose_more_than_sheltered_ones(game_env):
    m = _start(game_env, "storm_front")
    for plot in m.plots:
        plot.state, plot.value, plot.ticks_intact = m.PRESERVED, 100.0, 5
    rows = m._storm_band_rows(1)
    row = rows[0]
    gap = row * m.GRID_COLS + 1
    m.plots[gap].state = m.BARE
    m.plots[gap].value = 0.0
    exposed, sheltered = row * m.GRID_COLS, row * m.GRID_COLS + 4
    assert m._storm_exposed(exposed) and not m._storm_exposed(sheltered)
    m.storm_run["next_in"] = 1
    m._advance_storm()
    assert abs(m.plots[exposed].value - 100 * (1 - m.STORM_LOSS_EXPOSED)) < 1e-9
    assert abs(m.plots[sheltered].value - 100 * (1 - m.STORM_LOSS_SHELTERED)) < 1e-9
    assert m.storm_run["fronts"] == 1 and m.storm_run["next_in"] == m.STORM_INTERVAL_TICKS
    other_row = next(r for r in range(m.GRID_ROWS) if r not in rows)
    assert m.plots[other_row * m.GRID_COLS].value == 100.0  # outside the band: untouched


def test_replanting_neighbours_also_leave_a_plot_exposed_and_edges_do_not(game_env):
    m = _start(game_env, "storm_front")
    for plot in m.plots:
        plot.state = m.PRESERVED
    m.plots[1].state = m.REPLANTING
    assert m._storm_exposed(0) and m._storm_exposed(2) and not m._storm_exposed(3)
    assert not m._storm_exposed(m.GRID_COLS - 1)  # the end of a row has one neighbour only


def test_mature_plots_shrug_off_storms_better(game_env):
    m = _start(game_env, "storm_front")
    for plot in m.plots:
        plot.state, plot.value, plot.ticks_intact = m.PRESERVED, 100.0, m.MATURITY_TICKS
    rows = m._storm_band_rows(1)
    plot = m.plots[rows[0] * m.GRID_COLS + 2]
    m.storm_run["next_in"] = 1
    m._advance_storm()
    assert plot.value == 100.0  # sheltered and mature: no loss at all
    m2 = m.plots[rows[0] * m.GRID_COLS + 2]
    m2.value = 100.0
    m.plots[rows[0] * m.GRID_COLS + 1].state = m.BARE
    m.storm_run["next_in"] = 1
    m._advance_storm()
    assert abs(m2.value - 100 * (1 - m.STORM_LOSS_EXPOSED_MATURE)) < 1e-9


def test_four_fronts_finish_the_level_with_the_value_lost_as_the_result(game_env):
    m = _start(game_env, "storm_front")
    assert m.level_done_tick is None
    for _ in range(m.STORM_INTERVAL_TICKS * 4 + 2):
        if m.level_done_tick is not None:
            break
        game_env.tick()
    assert m.level_done_tick == m.STORM_INTERVAL_TICKS * 4
    best = m.levels_state["best"]["storm_front"]
    assert best["value"] == int(round(m.storm_run["lost"])) and best["text"].endswith("value lost")
    fronts = m.storm_run["fronts"]
    game_env.tick(30)
    assert m.storm_run["fronts"] == fronts  # a finished level stops sending storms


def test_replanting_the_gaps_first_costs_less(game_env):
    """The mode's point: closing the canopy before the front arrives loses less than leaving it ragged."""
    def lost(replant):
        m = _start(game_env, "storm_front")
        if replant:
            for plot in m.plots:
                if plot.state == m.BARE:
                    plot.replant()
        for _ in range(m.STORM_INTERVAL_TICKS):
            game_env.tick()
        return m.storm_run["lost"]
    assert lost(True) < lost(False)


def test_storm_state_round_trips(game_env):
    m = _start(game_env, "storm_front")
    game_env.tick(25)
    state = json.loads(json.dumps(m.get_state()))
    keep = dict(m.storm_run)
    m.start_level("wren_hollow", force=True)
    m.load_state(state)
    assert m.current_level == "storm_front" and m.storm_run == keep


# --- GB-16 The Spirit's Walk ---------------------------------------------------------------------------------------

def test_the_spirit_speaks_first_and_logs_each_line(game_env):
    m = _start(game_env, "spirits_walk")
    assert m.spirit_line_text() == m.SPIRIT_STEPS[0][1]
    game_env.tick()
    assert game_env.elements["spirit-line"].hidden is False
    assert game_env.elements["spirit-line"].innerText.endswith(m.SPIRIT_STEPS[0][1])
    assert any(e["kind"] == "spirit" and m.SPIRIT_STEPS[0][1] in e["text"] for e in m.forest_log)


def test_no_spirit_outside_her_level(game_env):
    assert game_env.module.spirit_line_text() == ""
    game_env.tick(3)
    assert game_env.elements["spirit-line"].hidden is True


def test_each_step_moves_on_when_its_task_is_done(game_env):
    m = _start(game_env, "spirits_walk")
    assert m._spirit_step_done("tend") is False
    game_env.tick(10)  # one plot passes 10 value
    assert m.spirit_run["step"] == 1
    assert m.spirit_line_text() == m.SPIRIT_STEPS[1][1]
    m.tend_plot(0)
    game_env.tick()
    assert m.spirit_run["step"] == 2  # tend done
    bare = next(p.index for p in m.plots if p.state == m.BARE)
    game_env.select(bare)
    game_env.replant()
    game_env.tick()
    assert m.spirit_run["step"] >= 3
    assert any(m.SPIRIT_STEPS[2][1] in e["text"] for e in m.forest_log)


def test_the_walk_ends_with_a_farewell_and_the_level_is_done(game_env):
    m = _start(game_env, "spirits_walk")
    for _ in range(200):
        if m.level_done_tick is not None:
            break
        game_env.tick()
        if m.forest_tick == 3:
            m.tend_plot(0)
        if m.forest_tick == 4:
            game_env.select(next(p.index for p in m.plots if p.state == m.BARE))
            game_env.replant()
        if m.pending_stakeholder_request is not None:
            game_env.decline_stakeholder()
    assert m.level_done_tick is not None and m.spirit_run["step"] == len(m.SPIRIT_STEPS)
    assert m.spirit_line_text() == m.SPIRIT_FAREWELL
    assert any(m.SPIRIT_FAREWELL in e["text"] for e in m.forest_log)
    assert "spirits_walk" in m.levels_state["done"]


def test_spirit_state_round_trips_and_does_not_repeat_lines(game_env):
    m = _start(game_env, "spirits_walk")
    game_env.tick(11)
    lines = len([e for e in m.forest_log if e["kind"] == "spirit"])
    state = json.loads(json.dumps(m.get_state()))
    m.start_level("wren_hollow", force=True)
    m.load_state(state)
    assert m.current_level == "spirits_walk" and m.spirit_run["step"] == state["level_run"]["spirit"]["step"]
    game_env.tick()
    assert len([e for e in m.forest_log if e["kind"] == "spirit"]) == lines  # the saved log has them; none repeated


def test_the_spirit_text_is_plain_text_never_markup(game_env):
    m = game_env.module
    for _step_id, line, task in m.SPIRIT_STEPS:
        assert "<" not in line and ">" not in line and "<" not in task


# --- the off switch for effects -------------------------------------------------------------------------------------

def test_every_mode_animation_is_behind_the_effects_switch_and_reduced_motion():
    from pathlib import Path
    css = (Path(__file__).resolve().parent.parent / "style.css").read_text(encoding="utf-8")
    start = css.index("GB batch 3 (2026-10-08)")
    block = css[start: css.index("Light theme (Y11b", start)]
    for name in ("gb3-poacher-shake", "gb3-storm-flicker", "gb3-spirit-glow"):
        usages = [line for line in block.splitlines() if f"animation: {name}" in line]
        assert usages, name
        assert all('html:not([data-level-effects="off"])' in line for line in usages), name
    assert "prefers-reduced-motion: reduce" in block


def test_the_switch_is_a_per_browser_setting_that_default_on():
    from pathlib import Path
    root = Path(__file__).resolve().parent.parent
    js = (root / "settings.js").read_text(encoding="utf-8")
    html = (root / "index.html").read_text(encoding="utf-8")
    assert 'canopy-level-effects' in js and '!== "off"' in js  # absent means on
    assert 'id="level-effects-checkbox" checked' in html
    game = (root / "game.py").read_text(encoding="utf-8")
    assert "level-effects" not in game and "level_effects" not in game  # a browser preference, never part of a save
