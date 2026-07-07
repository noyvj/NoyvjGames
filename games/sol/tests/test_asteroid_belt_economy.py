"""Tests for the Milestone 9d resource loop: the Asteroid Belt gets its own
Platinum click loop, Auto-Prospector automation, and ecology/Recycler
system — the fifth full reuse of the standard building system after Earth,
Mars, Moon, and Venus. These tests focus on Asteroid-Belt-specific wiring
and naming rather than re-proving the shared math (already covered
generically via game_env.earth in other files)."""

import math
from pathlib import Path

INDEX_HTML = Path(__file__).resolve().parent.parent / "index.html"


# --- setup / initial state ----------------------------------------------

def test_asteroid_belt_resource_label_names_platinum_in_html():
    # The label text is static markup (never touched by game.py, matching
    # Earth's original design), so it can only be checked against the real
    # file rather than through the fake-DOM harness used elsewhere.
    html = INDEX_HTML.read_text()
    assert 'id="asteroidbelt-resource-label"' in html
    assert "Platinum — Asteroid Belt" in html


def test_asteroid_belt_click_button_configured(game_env):
    button = game_env.elements["asteroidbelt-click-button"]
    assert button.innerText == "Prospect Platinum"
    assert button.disabled is False


def test_asteroid_belt_starts_at_zero_resource(game_env):
    assert game_env.asteroid_belt["resource_count"] == 0
    assert game_env.elements["asteroidbelt-resource-count"].innerText == "0"


def test_asteroid_belt_generator_button_configured(game_env):
    button = game_env.elements["asteroidbelt-buy-generator-button"]
    assert button.disabled is False
    assert "10 Platinum" in button.innerText


def test_asteroid_belt_recycler_button_configured(game_env):
    button = game_env.elements["asteroidbelt-buy-recycler-button"]
    assert button.disabled is False
    assert "15 Platinum" in button.innerText


def test_asteroid_belt_ecology_starts_at_full_health(game_env):
    assert game_env.asteroid_belt["ecology_health"] == 100.0
    assert game_env.elements["asteroidbelt-ecology-percent"].innerText == "100%"


# --- clicking (manual collection) ----------------------------------------

def test_asteroid_belt_click_increments_resource(game_env):
    game_env.click("AsteroidBelt")
    assert game_env.asteroid_belt["resource_count"] == 1


def test_asteroid_belt_click_does_not_affect_other_planets(game_env):
    game_env.click("AsteroidBelt")
    assert game_env.earth["resource_count"] == 0
    assert game_env.mars["resource_count"] == 0
    assert game_env.moon["resource_count"] == 0
    assert game_env.venus["resource_count"] == 0


def test_asteroid_belt_click_gives_press_feedback(game_env):
    button = game_env.elements["asteroidbelt-click-button"]
    game_env.click("AsteroidBelt")
    assert button.classList.contains("pressed")
    game_env.timers.flush()
    assert not button.classList.contains("pressed")


def test_asteroid_belt_manual_click_never_halted_by_ecology(game_env):
    game_env.asteroid_belt["ecology_health"] = 0.0
    game_env.click("AsteroidBelt")
    assert game_env.asteroid_belt["resource_count"] == 1


# --- Auto-Prospector (Asteroid Belt's generator) ---------------------------

def test_buying_asteroid_belt_generator_deducts_cost_and_increments(game_env):
    game_env.asteroid_belt["resource_count"] = 10
    game_env.buy_generator("AsteroidBelt")
    assert game_env.asteroid_belt["generator_count"] == 1
    assert game_env.asteroid_belt["resource_count"] == 0


def test_buying_asteroid_belt_generator_does_not_touch_other_planets(game_env):
    game_env.asteroid_belt["resource_count"] = 10
    game_env.buy_generator("AsteroidBelt")
    assert game_env.earth["generator_count"] == 0
    assert game_env.mars["generator_count"] == 0
    assert game_env.moon["generator_count"] == 0
    assert game_env.venus["generator_count"] == 0


def test_asteroid_belt_generator_cost_scales_independently(game_env):
    game_env.asteroid_belt["resource_count"] = 1000
    game_env.buy_generator("AsteroidBelt")
    asteroid_belt_cost = game_env.module.generator_cost("AsteroidBelt")
    earth_cost = game_env.module.generator_cost("Earth")
    assert asteroid_belt_cost > earth_cost  # Asteroid Belt bought one already, Earth hasn't


def test_asteroid_belt_generator_produces_platinum_over_ticks(game_env):
    game_env.asteroid_belt["resource_count"] = 10
    game_env.buy_generator("AsteroidBelt")  # 1 prospector, rate 1/s
    game_env.timers.tick_intervals(10)  # 1 second
    assert math.isclose(game_env.asteroid_belt["resource_count"], 1.0, abs_tol=1e-9)


def test_asteroid_belt_generator_display_updates(game_env):
    game_env.asteroid_belt["resource_count"] = 10
    game_env.buy_generator("AsteroidBelt")
    assert game_env.elements["asteroidbelt-generator-count"].innerText == "1"
    assert game_env.elements["asteroidbelt-generator-rate"].innerText == "1"


# --- Recycler (Asteroid Belt's ecology-restoring building) -----------------

def test_buying_asteroid_belt_recycler_deducts_cost_and_increments(game_env):
    game_env.asteroid_belt["resource_count"] = 15
    game_env.buy_recycler("AsteroidBelt")
    assert game_env.asteroid_belt["recycler_count"] == 1
    assert game_env.asteroid_belt["resource_count"] == 0


def test_asteroid_belt_recycler_restores_ecology_over_ticks(game_env):
    game_env.asteroid_belt["ecology_health"] = 50.0
    game_env.asteroid_belt["resource_count"] = 15
    game_env.buy_recycler("AsteroidBelt")  # 1 recycler, restore 2%/s
    game_env.timers.tick_intervals(10)  # 1 second
    assert math.isclose(game_env.asteroid_belt["ecology_health"], 52.0, abs_tol=1e-6)


def test_asteroid_belt_ecology_decays_from_its_own_generators(game_env):
    game_env.asteroid_belt["resource_count"] = 10
    game_env.buy_generator("AsteroidBelt")
    game_env.timers.tick_intervals(10)  # 1 second
    assert math.isclose(game_env.asteroid_belt["ecology_health"], 99.0, abs_tol=1e-6)


def test_asteroid_belt_ecology_decay_does_not_affect_other_planets(game_env):
    game_env.asteroid_belt["resource_count"] = 10
    game_env.buy_generator("AsteroidBelt")
    game_env.timers.tick_intervals(10)
    assert game_env.earth["ecology_health"] == 100.0
    assert game_env.mars["ecology_health"] == 100.0
    assert game_env.moon["ecology_health"] == 100.0
    assert game_env.venus["ecology_health"] == 100.0


# --- production penalty / halt, independent of other planets ---------------

def test_asteroid_belt_production_halted_at_zero_ecology(game_env):
    game_env.asteroid_belt["generator_count"] = 1
    game_env.asteroid_belt["ecology_health"] = 0.0
    game_env.asteroid_belt["resource_count"] = 0
    game_env.module.tick()
    assert game_env.asteroid_belt["resource_count"] == 0


def test_asteroid_belt_production_unaffected_by_earths_ecology(game_env):
    game_env.earth["ecology_health"] = 0.0
    game_env.asteroid_belt["generator_count"] = 1
    game_env.asteroid_belt["resource_count"] = 0
    game_env.module.tick()
    assert game_env.asteroid_belt["resource_count"] > 0


def test_asteroid_belt_status_message_at_collapse(game_env):
    game_env.asteroid_belt["ecology_health"] = 0.0
    game_env.module.update_ecology_display("AsteroidBelt")
    assert "halted" in game_env.elements["asteroidbelt-ecology-status"].innerText


# --- travel wiring: Asteroid Belt's own dedicated view ---------------------

def test_asteroid_belt_view_hidden_by_default(game_env):
    assert game_env.elements["asteroidbelt-view"].hidden is True


def test_asteroid_belt_return_to_earth_button_wired(game_env):
    button = game_env.elements["asteroidbelt-return-to-earth-button"]
    assert "click" in button._listeners
    assert len(button._listeners["click"]) == 1


def test_traveling_to_asteroid_belt_requires_tier_2_unlock(game_env):
    game_env.travel_to("AsteroidBelt")
    assert game_env.module.current_planet == "Earth"

    game_env.module.unlocked_bodies.add("AsteroidBelt")
    game_env.travel_to("AsteroidBelt")
    assert game_env.module.current_planet == "AsteroidBelt"
    assert game_env.elements["asteroidbelt-view"].hidden is False


# --- Asteroid Belt and the other four economies are fully independent -----

def test_all_five_resource_counts_are_independent(game_env):
    game_env.click("AsteroidBelt")
    game_env.click("AsteroidBelt")
    game_env.click("Venus")
    game_env.click("Moon")
    game_env.click("Mars")
    game_env.click()  # Earth
    assert game_env.asteroid_belt["resource_count"] == 2
    assert game_env.venus["resource_count"] == 1
    assert game_env.moon["resource_count"] == 1
    assert game_env.mars["resource_count"] == 1
    assert game_env.earth["resource_count"] == 1


def test_all_five_generator_counts_are_independent(game_env):
    game_env.earth["resource_count"] = 100
    game_env.mars["resource_count"] = 100
    game_env.moon["resource_count"] = 100
    game_env.venus["resource_count"] = 100
    game_env.asteroid_belt["resource_count"] = 100
    game_env.buy_generator()  # Earth
    assert game_env.earth["generator_count"] == 1
    assert game_env.mars["generator_count"] == 0
    assert game_env.moon["generator_count"] == 0
    assert game_env.venus["generator_count"] == 0
    assert game_env.asteroid_belt["generator_count"] == 0
