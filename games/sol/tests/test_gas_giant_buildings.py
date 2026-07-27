"""Tests for the Milestone 10 "Gas giant buildings" feature: Sky City, a
fourth building type available ONLY on Jupiter's Moons and Saturn's Moons.
A Sky City costs BOTH the local resource (Helium-3 / Methane) AND Mars's
Water Ice, and boosts that planet's generator output by +10% per city — the
payoff for the trade system existing at all, per the game's design doc
("gas giant buildings need Mars materials"). Earth/Mars/Moon/Venus/Asteroid
Belt/Pluto have no Sky City concept at all — not just hidden in the UI, the
state key itself doesn't exist on those planets. These tests focus on the
Sky City wiring rather than re-proving the shared generator/ecology math
(already covered generically via game_env.earth in other files)."""

import math

import pytest


GAS_GIANTS = ["JupiterMoons", "SaturnMoons"]
OTHER_PLANETS = ["Earth", "Mars", "Moon", "Venus", "AsteroidBelt", "Pluto"]


# --- initial state --------------------------------------------------------

@pytest.mark.parametrize("planet", GAS_GIANTS)
def test_sky_city_starts_at_zero(game_env, planet):
    assert game_env.state(planet)["sky_city_count"] == 0


@pytest.mark.parametrize(
    "planet,prefix,resource_name",
    [
        ("JupiterMoons", "jupitermoons", "Helium-3"),
        ("SaturnMoons", "saturnmoons", "Methane"),
    ],
)
def test_sky_city_button_shows_dual_cost(game_env, planet, prefix, resource_name):
    button = game_env.elements[f"{prefix}-buy-sky-city-button"]
    assert button.disabled is False
    assert f"50 {resource_name}" in button.innerText
    assert "20 Water Ice" in button.innerText


@pytest.mark.parametrize("prefix", ["jupitermoons", "saturnmoons"])
def test_sky_city_count_and_bonus_displays_start_at_zero(game_env, prefix):
    assert game_env.elements[f"{prefix}-sky-city-count"].innerText == "0"
    assert game_env.elements[f"{prefix}-sky-city-bonus"].innerText == "0"


# --- buying a Sky City -----------------------------------------------------

@pytest.mark.parametrize("planet", GAS_GIANTS)
def test_buying_sky_city_deducts_both_costs_and_increments(game_env, planet):
    game_env.state(planet)["resource_count"] = 50
    game_env.mars["resource_count"] = 20
    game_env.buy_sky_city(planet)
    assert game_env.state(planet)["sky_city_count"] == 1
    assert game_env.state(planet)["resource_count"] == 0
    assert game_env.mars["resource_count"] == 0


@pytest.mark.parametrize("planet", GAS_GIANTS)
def test_buying_sky_city_fails_when_local_resource_insufficient(game_env, planet):
    game_env.state(planet)["resource_count"] = 49  # one short
    game_env.mars["resource_count"] = 20
    game_env.buy_sky_city(planet)
    assert game_env.state(planet)["sky_city_count"] == 0
    assert game_env.state(planet)["resource_count"] == 49
    assert game_env.mars["resource_count"] == 20


@pytest.mark.parametrize("planet", GAS_GIANTS)
def test_buying_sky_city_fails_when_mars_water_ice_insufficient(game_env, planet):
    game_env.state(planet)["resource_count"] = 50
    game_env.mars["resource_count"] = 19  # one short
    game_env.buy_sky_city(planet)
    assert game_env.state(planet)["sky_city_count"] == 0
    assert game_env.state(planet)["resource_count"] == 50
    assert game_env.mars["resource_count"] == 19


@pytest.mark.parametrize("planet,prefix", [("JupiterMoons", "jupitermoons"), ("SaturnMoons", "saturnmoons")])
def test_sky_city_button_gives_press_feedback_even_when_unaffordable(game_env, planet, prefix):
    button = game_env.elements[f"{prefix}-buy-sky-city-button"]
    game_env.buy_sky_city(planet)
    assert button.classList.contains("pressed")
    game_env.timers.flush()
    assert not button.classList.contains("pressed")


@pytest.mark.parametrize("planet", GAS_GIANTS)
def test_sky_city_cost_scales_after_purchase(game_env, planet):
    first_local_cost = game_env.module.sky_city_local_cost(planet)
    first_mars_cost = game_env.module.sky_city_mars_cost(planet)
    game_env.state(planet)["resource_count"] = first_local_cost
    game_env.mars["resource_count"] = first_mars_cost
    game_env.buy_sky_city(planet)
    second_local_cost = game_env.module.sky_city_local_cost(planet)
    second_mars_cost = game_env.module.sky_city_mars_cost(planet)
    assert second_local_cost > first_local_cost
    assert second_mars_cost > first_mars_cost


@pytest.mark.parametrize("planet,prefix", [("JupiterMoons", "jupitermoons"), ("SaturnMoons", "saturnmoons")])
def test_sky_city_display_updates_after_purchase(game_env, planet, prefix):
    game_env.state(planet)["resource_count"] = 50
    game_env.mars["resource_count"] = 20
    game_env.buy_sky_city(planet)
    assert game_env.elements[f"{prefix}-sky-city-count"].innerText == "1"
    assert game_env.elements[f"{prefix}-sky-city-bonus"].innerText == "10"


def test_buying_sky_city_deducts_mars_water_ice_even_when_not_on_mars(game_env):
    # Proves the cross-planet deduction is real state, not just a display
    # that happens to be visible from Mars's own view.
    assert game_env.module.current_planet == "Earth"
    game_env.jupiter_moons["resource_count"] = 50
    game_env.mars["resource_count"] = 20
    game_env.buy_sky_city("JupiterMoons")
    assert game_env.module.current_planet == "Earth"
    assert game_env.mars["resource_count"] == 0


# --- production bonus ------------------------------------------------------

@pytest.mark.parametrize("planet", GAS_GIANTS)
def test_sky_city_boosts_production_over_ticks(game_env, planet):
    # Same generator_count in both scenarios; only the Sky City count
    # differs, isolating the +10%/city bonus.
    state = game_env.state(planet)
    state["generator_count"] = 1
    state["resource_count"] = 0
    game_env.timers.tick_intervals(10)  # 1 second, no Sky City
    baseline = state["resource_count"]

    state["resource_count"] = 0
    state["sky_city_count"] = 1
    game_env.timers.tick_intervals(10)  # 1 second, with 1 Sky City
    boosted = state["resource_count"]

    assert boosted > baseline
    assert math.isclose(boosted, baseline * 1.1, rel_tol=1e-6)


@pytest.mark.parametrize("planet", GAS_GIANTS)
def test_sky_city_does_not_affect_ecology_decay(game_env, planet):
    state = game_env.state(planet)
    state["generator_count"] = 1
    state["sky_city_count"] = 0
    game_env.timers.tick_intervals(10)
    baseline_ecology = state["ecology_health"]

    state["ecology_health"] = 100.0
    state["sky_city_count"] = 5
    game_env.timers.tick_intervals(10)
    boosted_ecology = state["ecology_health"]

    assert math.isclose(boosted_ecology, baseline_ecology, abs_tol=1e-9)


# --- exclusivity to the gas giant moons ------------------------------------

@pytest.mark.parametrize("planet", OTHER_PLANETS)
def test_other_planets_have_no_sky_city_state(game_env, planet):
    assert "sky_city_count" not in game_env.state(planet)


def test_other_planets_have_no_sky_city_button_element():
    # None of the six non-gas-giant planets have a buy-sky-city-button id
    # wired up anywhere in game.py's DOM lookups; the only ones that exist
    # in the fake DOM are the two gas giants'.
    from .conftest import ELEMENT_IDS

    assert "buy-sky-city-button" not in ELEMENT_IDS
    for prefix in ["mars", "moon", "venus", "asteroidbelt", "pluto"]:
        assert f"{prefix}-buy-sky-city-button" not in ELEMENT_IDS


def test_jupiter_moons_and_saturn_moons_sky_cities_are_independent(game_env):
    game_env.jupiter_moons["resource_count"] = 50
    game_env.saturn_moons["resource_count"] = 50
    game_env.mars["resource_count"] = 40
    game_env.buy_sky_city("JupiterMoons")
    assert game_env.jupiter_moons["sky_city_count"] == 1
    assert game_env.saturn_moons["sky_city_count"] == 0

    game_env.buy_sky_city("SaturnMoons")
    assert game_env.jupiter_moons["sky_city_count"] == 1
    assert game_env.saturn_moons["sky_city_count"] == 1
