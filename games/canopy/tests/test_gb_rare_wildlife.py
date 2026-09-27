"""GB-20: rare wildlife that only appears under conditions, listed in the wildlife log."""

from .gb_helpers import decline_requests, log_kinds, toast_text

LATE_AUTUMN = 110  # forest_tick before the tick that lands in the last 10 ticks of autumn (80..119)


def _at(env, tick):
    env.module.forest_tick = tick


def _rich_plot(m, index=0, biodiversity=1.9):
    m.plots[index].biodiversity = biodiversity
    m.plots[index].ticks_intact = 5


def test_ghost_stag_at_dusk_in_late_autumn_on_a_90_percent_plot(game_env):
    m = game_env.module
    _rich_plot(m)
    _at(game_env, LATE_AUTUMN)
    game_env.tick()
    assert m.is_dusk_window() and m.current_season() == "autumn"
    assert "ghost_stag" in m.rare_wildlife_found
    assert "rare" in log_kinds(m)
    assert "ghost stag" in toast_text(game_env)


def test_not_before_the_dusk_ticks_of_autumn(game_env):
    m = game_env.module
    _rich_plot(m)
    _at(game_env, 100)
    game_env.tick()
    assert not m.is_dusk_window()
    assert m.rare_wildlife_found == []


def test_not_in_other_seasons_at_the_same_offset(game_env):
    m = game_env.module
    _rich_plot(m)
    for start in (30, 70, 150):  # spring/summer/winter, offset 30+ within the season
        _at(game_env, start)
        game_env.tick()
        assert m.rare_wildlife_found == []


def test_needs_a_ninety_percent_plot(game_env):
    m = game_env.module
    for plot in m.plots:
        plot.biodiversity = 1.7
    _at(game_env, LATE_AUTUMN)
    game_env.tick()
    assert m.rare_wildlife_found == []
    assert abs(m.biodiversity_fraction(m.plots[0]) - 0.9) < 0.1


def test_the_dusk_window_tints_the_grid(game_env):
    m = game_env.module
    _at(game_env, LATE_AUTUMN)
    game_env.tick()
    assert game_env.elements["plot-grid"].classList.contains("plot-grid--dusk")
    _at(game_env, 5)
    m.render()
    assert not game_env.elements["plot-grid"].classList.contains("plot-grid--dusk")


def test_the_stag_is_drawn_on_its_plot_only_during_dusk(game_env):
    m = game_env.module
    _rich_plot(m, 3)
    _at(game_env, LATE_AUTUMN)
    game_env.tick()
    assert "plot-ghost-stag" in game_env.elements["plot-3"].className
    assert "plot-ghost-stag" not in game_env.elements["plot-4"].className
    _at(game_env, 90)
    m.render()
    assert "plot-ghost-stag" not in game_env.elements["plot-3"].className


def test_fox_after_three_declined_clear_requests(game_env):
    m = game_env.module
    game_env.tick(3)
    decline_requests(game_env, 5, 2)
    assert "wary_fox" not in m.rare_wildlife_found
    decline_requests(game_env, 6, 1)
    assert m.declined_clear_requests_total() == 3
    assert "wary_fox" in m.rare_wildlife_found
    assert "wary fox" in toast_text(game_env)


def test_incentive_declines_do_not_count_for_the_fox(game_env):
    m = game_env.module
    game_env.tick(3)
    for _ in range(4):
        m.pending_stakeholder_request = {"plot_index": 5, "reason": "ecotourism", "kind": "incentive"}
        game_env.decline_stakeholder()
    assert m.rare_wildlife_found == []


def test_each_rare_animal_is_logged_once(game_env):
    m = game_env.module
    game_env.tick(3)
    decline_requests(game_env, 5, 5)
    game_env.tick(3)
    assert log_kinds(m).count("rare") == 1
    assert m.rare_wildlife_found == ["wary_fox"]


def test_the_wildlife_log_lists_rare_sightings(game_env):
    m = game_env.module
    game_env.toggle_session_summary()
    assert "Rare sightings (0/2): none yet" in game_env.elements["wildlife-log-list"].innerText
    game_env.tick(3)
    decline_requests(game_env, 5, 3)
    text = game_env.elements["wildlife-log-list"].innerText
    assert "Rare sightings (1/2)" in text and "wary fox" in text
    assert any("wary fox" in line for line in text.splitlines()[2:])
    assert m.forest_log_lines(kinds={"rare"})


def test_rare_finds_save_load_and_reject_junk(game_env):
    m = game_env.module
    assert "rare_wildlife_found" not in m.get_state()
    game_env.tick(3)
    decline_requests(game_env, 5, 3)
    state = m.get_state()
    assert state["rare_wildlife_found"] == ["wary_fox"]
    game_env.reset_session()
    m.load_state(state)
    assert m.rare_wildlife_found == ["wary_fox"]
    for bad in ("ghost_stag", 5, None, [[1], {"a": 1}, "nope", 3, True], ["ghost_stag", "ghost_stag"], {"x": 1}):
        m.load_state(dict(state, rare_wildlife_found=bad))
        assert all(isinstance(x, str) for x in m.rare_wildlife_found)
        assert len(set(m.rare_wildlife_found)) == len(m.rare_wildlife_found)
        assert set(m.rare_wildlife_found) <= {"ghost_stag", "wary_fox"}


def test_reset_forgets_rare_finds(game_env):
    m = game_env.module
    game_env.tick(3)
    decline_requests(game_env, 5, 3)
    game_env.reset_session()
    assert m.rare_wildlife_found == []
