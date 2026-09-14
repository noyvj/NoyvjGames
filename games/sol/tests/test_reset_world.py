"""Tests for A18: "reset this world only" -- distinct from a full save
wipe, this clears exactly one planet's own economy (resources, buildings,
ecology, trade routes, terraforming) back to its fresh-game defaults,
gated behind a real confirm() dialog, and leaves everything else (research,
unlocked_bodies, visited_bodies, achievements, current_planet) untouched."""


def test_reset_clears_earths_economy(game_env):
    game_env.earth["resource_count"] = 500
    game_env.earth["generator_count"] = 3
    game_env.earth["recycler_count"] = 2
    game_env.earth["ecology_health"] = 40.0
    game_env.earth["terraform_progress"] = 60.0

    game_env.reset_world("Earth")

    assert game_env.earth["resource_count"] == 0.0
    assert game_env.earth["generator_count"] == 0
    assert game_env.earth["recycler_count"] == 0
    assert game_env.earth["ecology_health"] == 100.0
    assert game_env.earth["terraform_progress"] == 0.0
    assert game_env.earth["trade_routes"] == {}


def test_reset_updates_the_displayed_numbers(game_env):
    game_env.earth["resource_count"] = 500
    game_env.earth["generator_count"] = 3
    game_env.reset_world("Earth")
    assert game_env.elements["resource-count"].innerText == "0"
    assert game_env.elements["generator-count"].innerText == "0"
    assert game_env.elements["ecology-percent"].innerText == "100%"
    assert game_env.elements["terraform-percent"].innerText == "0%"


def test_reset_does_nothing_without_confirmation(game_env):
    game_env.earth["resource_count"] = 500
    game_env.earth["generator_count"] = 3
    game_env.set_confirm_response(False)

    game_env.reset_world("Earth")

    assert game_env.earth["resource_count"] == 500
    assert game_env.earth["generator_count"] == 3


def test_reset_does_not_touch_research_or_unlocked_bodies(game_env):
    module = game_env.module
    module.unlocked_bodies.add("Mars")
    module.unlocked_bodies.add("Moon")
    module.completed_tiers = 1
    module.research_progress = 250.0

    game_env.reset_world("Earth")

    assert module.unlocked_bodies == {"Mars", "Moon"}
    assert module.completed_tiers == 1
    assert module.research_progress == 250.0


def test_reset_does_not_unvisit_the_world(game_env):
    module = game_env.module
    module.unlocked_bodies.add("Mars")
    game_env.travel_to("Mars")
    assert "Mars" in module.visited_bodies

    game_env.reset_world("Mars")

    assert "Mars" in module.visited_bodies


def test_reset_does_not_affect_other_planets(game_env):
    game_env.earth["resource_count"] = 500
    game_env.mars["resource_count"] = 300
    game_env.reset_world("Earth")
    assert game_env.mars["resource_count"] == 300


def test_reset_sky_city_count_on_a_gas_giant_moon(game_env):
    module = game_env.module
    module.unlocked_bodies.update(["JupiterMoons"])
    game_env.jupiter_moons["sky_city_count"] = 2
    game_env.jupiter_moons["resource_count"] = 999

    game_env.reset_world("JupiterMoons")

    assert game_env.jupiter_moons["sky_city_count"] == 0
    assert game_env.jupiter_moons["resource_count"] == 0.0


def test_reset_button_gives_press_feedback(game_env):
    game_env.reset_world("Earth")
    button = game_env.elements["reset-world-button"]
    assert "pressed" in button.classList
    game_env.timers.flush()
    assert "pressed" not in button.classList


def test_reset_recomputes_the_win_banner(game_env):
    """A world reset can drop terraform_progress back below 100%, which
    must un-hide-toggle the win banner correctly if it had been showing."""
    module = game_env.module
    for planet in module.PLANETS:
        module.planet_state[planet]["terraform_progress"] = module.TERRAFORM_MAX
    module.update_win_display()
    assert game_env.elements["win-banner"].hidden is False

    game_env.reset_world("Earth")
    assert game_env.elements["win-banner"].hidden is True


def test_reset_world_button_wired_up_for_every_planet(game_env):
    ids = [
        "reset-world-button",
        "mars-reset-world-button",
        "moon-reset-world-button",
        "venus-reset-world-button",
        "asteroidbelt-reset-world-button",
        "pluto-reset-world-button",
        "jupitermoons-reset-world-button",
        "saturnmoons-reset-world-button",
    ]
    for id_ in ids:
        assert "click" in game_env.elements[id_]._listeners
