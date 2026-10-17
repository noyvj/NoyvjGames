"""Round-8 pass: the round-advance animation (C-23)."""
from pathlib import Path

from .test_round7_trend import _tick
from .pagefiles import game_css

STYLE = game_css()


def test_nothing_is_drawn_until_a_round_is_advanced(game_env):
    game_env.module.render()
    assert game_env.elements["round-animation"].innerHTML == ""
    game_env.build("coal")
    game_env.advance_round()  # coal only and one round: just the empty-scene case, nothing to show yet
    assert game_env.elements["round-animation"].innerHTML == ""


def test_scenes_follow_what_the_grid_has(game_env):
    g = game_env.module
    game_env.state.plant_counts["coal"] = 3
    game_env.advance_round()
    game_env.advance_round()
    parts = g.round_animation_parts()
    assert parts == {"sun": False, "wind": False, "streaks": 0, "curve": True}
    svg = g.round_animation_svg()
    assert "ra-demand" in svg and "ra-sun" not in svg and "ra-streak" not in svg
    game_env.state.plant_counts["solar"] = 2
    game_env.state.plant_counts["wind"] = 7
    parts = g.round_animation_parts()
    assert parts["sun"] and parts["wind"] and parts["streaks"] == 3
    svg = g.round_animation_svg()
    assert "ra-sun" in svg and svg.count("ra-streak") == 3 and "ra-demand" in svg
    game_env.state.plant_counts["wind"] = 40
    assert g.round_animation_parts()["streaks"] == g.ROUND_ANIMATION_MAX_STREAKS


def test_advance_plays_and_the_timer_hides_it(game_env):
    game_env.state.plant_counts["solar"] = 1
    game_env.build("coal")
    game_env.advance_round()
    box = game_env.elements["round-animation"]
    assert box.hidden is False and "ra-sun" in box.innerHTML
    assert 'aria-hidden="true"' in box.innerHTML
    delays = [d for _cb, d in game_env.timers.pending]
    assert game_env.module.ROUND_ANIMATION_MS in delays and game_env.module.ROUND_ANIMATION_MS < 1000
    game_env.timers.flush()
    assert box.hidden is True and box.innerHTML == ""


def test_a_quick_second_advance_is_not_cut_short_by_the_first_timer(game_env):
    game_env.state.plant_counts["solar"] = 1
    game_env.build("coal")
    game_env.advance_round()
    first_pending = list(game_env.timers.pending)
    game_env.advance_round()
    box = game_env.elements["round-animation"]
    # run only the first round's hide timer: the newer animation must stay
    first_pending[-1][0]()
    assert box.hidden is False and box.innerHTML != ""


def test_checkbox_switches_it_off(game_env):
    _tick(game_env, "pref-round-animation", False)
    assert game_env.module.prefs["round_animation"] is False
    game_env.state.plant_counts["solar"] = 1
    game_env.build("coal")
    game_env.advance_round()
    assert game_env.elements["round-animation"].hidden is True
    assert game_env.elements["round-animation"].innerHTML == ""
    _tick(game_env, "pref-round-animation", True)
    assert game_env.module.prefs["round_animation"] is True


def test_auto_advance_plays_it_once_at_the_end(game_env):
    game_env.state.plant_counts["solar"] = 1
    game_env.build("coal")
    game_env.auto_advance()
    assert game_env.elements["round-animation"].hidden is False
    assert sum(1 for _cb, d in game_env.timers.pending if d == game_env.module.ROUND_ANIMATION_MS) == 1


def test_it_changes_no_numbers_and_is_not_saved(game_env):
    g = game_env.module
    assert "round_animation" not in g.get_state()
    game_env.build("coal")
    game_env.advance_round()
    assert g.state.round_number == 2


def test_it_is_off_under_reduced_motion_and_decorative():
    assert "@media (prefers-reduced-motion: reduce) { .round-animation { display: none !important; } }" in STYLE
    assert 'html[data-reduced-motion="true"] .round-animation { display: none !important; }' in STYLE
