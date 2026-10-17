"""Round-8 pass: chart colour themes (C-28)."""
from pathlib import Path

from .test_round7_trend import _tick
from .pagefiles import game_css

STYLE = game_css()


def _choose(env, value):
    select = env.elements["pref-chart-theme"]
    select.value = value

    class _Event:
        pass

    event = _Event()
    event.target = select
    select.dispatch("change", event)


def test_default_theme_is_set_on_the_charts(game_env):
    game_env.module.render()
    for element_id in ("trend-graph", "trend-controls", "plant-mix"):
        assert game_env.elements[element_id].dataset.chartTheme == "default"
    assert game_env.elements["pref-chart-theme"].value == "default"


def test_choosing_a_theme_updates_the_charts_and_the_pref(game_env):
    _choose(game_env, "pattern")
    assert game_env.module.prefs["chart_theme"] == "pattern"
    for element_id in ("trend-graph", "trend-controls", "plant-mix"):
        assert game_env.elements[element_id].dataset.chartTheme == "pattern"
    _choose(game_env, "contrast")
    assert game_env.elements["plant-mix"].dataset.chartTheme == "contrast"


def test_an_unknown_theme_is_refused_and_prefs_validate(game_env):
    g = game_env.module
    assert g.set_pref("chart_theme", "neon") is False
    assert g.prefs["chart_theme"] == "default"
    assert g.validate_prefs({"chart_theme": "neon"})["chart_theme"] == "default"
    assert g.validate_prefs({"chart_theme": "pattern"})["chart_theme"] == "pattern"
    assert g.validate_prefs({"chart_theme": 3})["chart_theme"] == "default"


def test_theme_is_a_preference_not_part_of_a_save(game_env):
    g = game_env.module
    _choose(game_env, "pattern")
    assert "chart_theme" not in g.get_state()
    g.load_state(g.get_state())
    assert g.prefs["chart_theme"] == "pattern"


def test_reset_to_default_puts_the_theme_back(game_env):
    _choose(game_env, "contrast")
    game_env.elements["settings-reset-button"].dispatch("click", None)
    assert game_env.module.prefs["chart_theme"] == "default"
    assert game_env.elements["trend-graph"].dataset.chartTheme == "default"


def test_the_theme_does_not_change_the_numbers(game_env):
    g = game_env.module
    for _ in range(3):
        game_env.build("coal")
        game_env.advance_round()
    before = g.trend_graph_svg(g.state.emissions_history, g.state.avg_renewable_cost_history,
                               g.state.global_reference_emissions_history, g.state.clean_fraction_log)
    _choose(game_env, "pattern")
    after = g.trend_graph_svg(g.state.emissions_history, g.state.avg_renewable_cost_history,
                              g.state.global_reference_emissions_history, g.state.clean_fraction_log)
    assert before == after and before


def test_every_plant_bar_and_line_has_a_pattern_rule_in_the_grayscale_theme():
    for plant in ("coal", "gas", "nuclear", "solar", "wind", "hydro"):
        assert f'[data-chart-theme="pattern"] .mix-bar--{plant} ' in STYLE
    patterns = {line.split("{")[1] for line in STYLE.splitlines() if line.startswith('[data-chart-theme="pattern"] .mix-bar--')}
    assert len(patterns) == 6  # no two bars share a fill
    # The grayscale theme keeps the dash patterns (they are set on the base rules and not overridden).
    pattern_lines = [ln for ln in STYLE.splitlines() if ln.startswith('[data-chart-theme="pattern"] .trend-line--')]
    assert not any("stroke-dasharray" in ln for ln in pattern_lines)
    for key in ("cost", "global", "funds", "demand", "clean"):
        assert f".trend-line--{key}" in STYLE


def test_a_tick_helper_still_works(game_env):
    _tick(game_env, "trend-show-funds", True)
    assert game_env.module.prefs["trend_funds"] is True
