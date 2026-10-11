"""Round-7 pass: a printable Run Summary (C-24)."""
from pathlib import Path

from .test_career import _play

GAME_DIR = Path(__file__).resolve().parent.parent


def test_summary_panel_is_the_print_target_on_both_pages():
    for page in ("index.html", "pc.html"):
        html = (GAME_DIR / page).read_text(encoding="utf-8")
        assert '<link rel="stylesheet" href="../../shared/print-summary.css" media="print">' in html, page
        line = next(ln for ln in html.splitlines() if 'id="summary-panel"' in ln)
        assert "print-summary" in line, page
        assert "summary-print-button" in html, page
        assert html.count("print-summary") == 3  # the stylesheet link, the class, and the comment


def test_the_print_button_is_only_added_to_the_panel_and_calls_print():
    html = (GAME_DIR / "index.html").read_text(encoding="utf-8")
    assert "window.print()" in html and 'panel.querySelector(":scope > .summary-print-button")' in html


def test_summary_lists_scenario_grade_resilience_and_career_points(game_env):
    g = game_env.module
    game_env.state.plant_counts["solar"] = 6
    _play(game_env, 6)
    html = g.summary_panel_html()
    assert "Scenario: Standard" in html and "Difficulty: Standard" in html and "Run seed: " in html
    assert "Operator grade" in html and "Grid resilience" in html
    assert "Career: 0 point(s) earned over 0 finished run(s); finishing this run would bank" in html


def test_short_runs_do_not_promise_career_points(game_env):
    g = game_env.module
    _play(game_env, 2)
    html = g.summary_panel_html()
    assert "finishing this run would bank" not in html and "Career: 0 point(s) earned over 0 finished run(s)." in html


def test_summary_reads_the_preset_and_scenario_in_force(game_env):
    g = game_env.module
    game_env.choose_difficulty_preset("operator")
    assert "Difficulty: Operator" in g.summary_panel_html()
    game_env.toggle_steeper_demand()
    game_env.toggle_weather_variability()
    assert "Difficulty: Custom" in g.summary_panel_html() or "Difficulty: Standard" in g.summary_panel_html()


def test_opening_the_panel_fills_it(game_env):
    game_env.toggle_summary_panel()
    assert "Career:" in game_env.elements["summary-panel"].innerHTML
