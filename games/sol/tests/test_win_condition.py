"""Tests for the Milestone 11 win state: a persistent, non-blocking banner
shown once every real planet in PLANETS has reached full terraform_progress
(100.0). Recomputed fresh on every call rather than tracked with a separate
"achieved" flag, since terraform_progress never regresses. The banner is a
sibling of every per-planet view, not nested inside any of them, so it stays
visible regardless of current_planet and never locks up the rest of the UI."""

from pathlib import Path

INDEX_HTML = Path(__file__).resolve().parent.parent / "index.html"


# --- default state -----------------------------------------------------

def test_win_banner_hidden_by_default(game_env):
    assert game_env.elements["win-banner"].hidden is True


# --- partial completion --------------------------------------------------

def test_banner_stays_hidden_with_seven_of_eight_planets_complete(game_env):
    planets = list(game_env.module.PLANETS)
    for planet in planets[:-1]:
        game_env.state(planet)["terraform_progress"] = 100.0
    game_env.module.update_win_display()
    assert game_env.elements["win-banner"].hidden is True


# --- full completion -------------------------------------------------------

def test_banner_becomes_visible_once_all_real_planets_complete(game_env):
    for planet in game_env.module.PLANETS:
        game_env.state(planet)["terraform_progress"] = 100.0
    game_env.module.update_win_display()
    assert game_env.elements["win-banner"].hidden is False


def test_banner_copy_matches_exact_text_in_html():
    # The banner's copy is static markup (never touched by game.py — only
    # its container's `hidden` attribute is toggled by update_win_display()),
    # so it can only be checked against the real file, matching the pattern
    # used for other static labels (e.g. test_mars_economy.py).
    html = INDEX_HTML.read_text()
    assert 'id="win-banner-heading"' in html
    assert "100% COMPLETE" in html
    assert 'id="win-banner-subtext"' in html
    assert (
        "Every world in the solar system has been fully terraformed. "
        "The simulation continues in sandbox mode."
    ) in html


# --- independent of current_planet -----------------------------------------

def test_banner_visibility_independent_of_current_planet(game_env):
    for planet in game_env.module.PLANETS:
        game_env.state(planet)["terraform_progress"] = 100.0
    game_env.module.update_win_display()
    assert game_env.elements["win-banner"].hidden is False

    game_env.travel_to("Mars")
    game_env.module.update_win_display()
    assert game_env.elements["win-banner"].hidden is False

    game_env.return_to_earth()
    game_env.module.update_win_display()
    assert game_env.elements["win-banner"].hidden is False


# --- driven through tick() --------------------------------------------------

def test_tick_updates_win_banner(game_env):
    for planet in game_env.module.PLANETS:
        game_env.state(planet)["terraform_progress"] = 100.0
    assert game_env.elements["win-banner"].hidden is True

    game_env.module.tick()
    assert game_env.elements["win-banner"].hidden is False


# --- non-blocking: sandbox mode continues -----------------------------------

def test_winning_does_not_disable_or_hide_the_rest_of_the_game(game_env):
    for planet in game_env.module.PLANETS:
        game_env.state(planet)["terraform_progress"] = 100.0
    game_env.module.update_win_display()
    assert game_env.elements["win-banner"].hidden is False

    # Still on Earth (default view) and fully interactive.
    assert game_env.elements["earth-view"].hidden is False
    assert game_env.elements["click-button"].disabled is False

    resource_before = game_env.earth["resource_count"]
    game_env.click()
    assert game_env.earth["resource_count"] == resource_before + 1
