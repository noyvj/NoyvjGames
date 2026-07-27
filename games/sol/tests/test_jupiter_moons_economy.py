"""Tests for the Milestone 9f resource loop: Jupiter's Moons get their own
Helium-3 click loop, Auto-Skimmer automation, and ecology/Recycler system —
the seventh full reuse of the standard building system after Earth, Mars,
Moon, Venus, the Asteroid Belt, and Pluto. Per the "parallel-unlock"
framing, this is ONE combined economy for the whole Jupiter's Moons body,
not one per moon (Io, Europa, Ganymede, Callisto). These tests focus on
Jupiter's-Moons-specific wiring and naming rather than re-proving the
shared math (already covered generically via game_env.earth in other
files)."""

import math
from pathlib import Path

INDEX_HTML = Path(__file__).resolve().parent.parent / "index.html"


# --- setup / initial state ----------------------------------------------

def test_jupiter_moons_resource_label_names_helium3_in_html():
    # The label text is static markup (never touched by game.py, matching
    # Earth's original design), so it can only be checked against the real
    # file rather than through the fake-DOM harness used elsewhere.
    html = INDEX_HTML.read_text()
    assert 'id="jupitermoons-resource-label"' in html
    assert "Helium-3 — Jupiter's Moons" in html


def test_jupiter_moons_click_button_configured(game_env):
    button = game_env.elements["jupitermoons-click-button"]
    assert button.innerText == "Skim Helium-3"
    assert button.disabled is False


def test_jupiter_moons_starts_at_zero_resource(game_env):
    assert game_env.jupiter_moons["resource_count"] == 0
    assert game_env.elements["jupitermoons-resource-count"].innerText == "0"


def test_jupiter_moons_generator_button_configured(game_env):
    button = game_env.elements["jupitermoons-buy-generator-button"]
    assert button.disabled is False
    assert "10 Helium-3" in button.innerText


def test_jupiter_moons_recycler_button_configured(game_env):
    button = game_env.elements["jupitermoons-buy-recycler-button"]
    assert button.disabled is False
    assert "15 Helium-3" in button.innerText


def test_jupiter_moons_ecology_starts_at_full_health(game_env):
    assert game_env.jupiter_moons["ecology_health"] == 100.0
    assert game_env.elements["jupitermoons-ecology-percent"].innerText == "100%"


# --- clicking (manual collection) ----------------------------------------

def test_jupiter_moons_click_increments_resource(game_env):
    game_env.click("JupiterMoons")
    assert game_env.jupiter_moons["resource_count"] == 1


def test_jupiter_moons_click_does_not_affect_other_planets(game_env):
    game_env.click("JupiterMoons")
    assert game_env.earth["resource_count"] == 0
    assert game_env.mars["resource_count"] == 0
    assert game_env.moon["resource_count"] == 0
    assert game_env.venus["resource_count"] == 0
    assert game_env.asteroid_belt["resource_count"] == 0
    assert game_env.pluto["resource_count"] == 0


def test_jupiter_moons_click_gives_press_feedback(game_env):
    button = game_env.elements["jupitermoons-click-button"]
    game_env.click("JupiterMoons")
    assert button.classList.contains("pressed")
    game_env.timers.flush()
    assert not button.classList.contains("pressed")


def test_jupiter_moons_manual_click_never_halted_by_ecology(game_env):
    game_env.jupiter_moons["ecology_health"] = 0.0
    game_env.click("JupiterMoons")
    assert game_env.jupiter_moons["resource_count"] == 1


# --- Auto-Skimmer (Jupiter's Moons's generator) -----------------------------

def test_buying_jupiter_moons_generator_deducts_cost_and_increments(game_env):
    game_env.jupiter_moons["resource_count"] = 10
    game_env.buy_generator("JupiterMoons")
    assert game_env.jupiter_moons["generator_count"] == 1
    assert game_env.jupiter_moons["resource_count"] == 0


def test_buying_jupiter_moons_generator_does_not_touch_other_planets(game_env):
    game_env.jupiter_moons["resource_count"] = 10
    game_env.buy_generator("JupiterMoons")
    assert game_env.earth["generator_count"] == 0
    assert game_env.mars["generator_count"] == 0
    assert game_env.moon["generator_count"] == 0
    assert game_env.venus["generator_count"] == 0
    assert game_env.asteroid_belt["generator_count"] == 0
    assert game_env.pluto["generator_count"] == 0


def test_jupiter_moons_generator_cost_scales_independently(game_env):
    game_env.jupiter_moons["resource_count"] = 1000
    game_env.buy_generator("JupiterMoons")
    jupiter_moons_cost = game_env.module.generator_cost("JupiterMoons")
    earth_cost = game_env.module.generator_cost("Earth")
    assert jupiter_moons_cost > earth_cost  # Jupiter's Moons bought one already, Earth hasn't


def test_jupiter_moons_generator_produces_helium3_over_ticks(game_env):
    game_env.jupiter_moons["resource_count"] = 10
    game_env.buy_generator("JupiterMoons")  # 1 skimmer, rate 1/s
    game_env.timers.tick_intervals(10)  # 1 second
    assert math.isclose(game_env.jupiter_moons["resource_count"], 1.0, abs_tol=1e-9)


def test_jupiter_moons_generator_display_updates(game_env):
    game_env.jupiter_moons["resource_count"] = 10
    game_env.buy_generator("JupiterMoons")
    assert game_env.elements["jupitermoons-generator-count"].innerText == "1"
    assert game_env.elements["jupitermoons-generator-rate"].innerText == "1"


# --- Recycler (Jupiter's Moons's ecology-restoring building) ---------------

def test_buying_jupiter_moons_recycler_deducts_cost_and_increments(game_env):
    game_env.jupiter_moons["resource_count"] = 15
    game_env.buy_recycler("JupiterMoons")
    assert game_env.jupiter_moons["recycler_count"] == 1
    assert game_env.jupiter_moons["resource_count"] == 0


def test_jupiter_moons_recycler_restores_ecology_over_ticks(game_env):
    game_env.jupiter_moons["ecology_health"] = 50.0
    game_env.jupiter_moons["resource_count"] = 15
    game_env.buy_recycler("JupiterMoons")  # 1 recycler, restore 2%/s
    game_env.timers.tick_intervals(10)  # 1 second
    assert math.isclose(game_env.jupiter_moons["ecology_health"], 52.0, abs_tol=1e-6)


def test_jupiter_moons_ecology_decays_from_its_own_generators(game_env):
    game_env.jupiter_moons["resource_count"] = 10
    game_env.buy_generator("JupiterMoons")
    game_env.timers.tick_intervals(10)  # 1 second
    assert math.isclose(game_env.jupiter_moons["ecology_health"], 99.0, abs_tol=1e-6)


def test_jupiter_moons_ecology_decay_does_not_affect_other_planets(game_env):
    game_env.jupiter_moons["resource_count"] = 10
    game_env.buy_generator("JupiterMoons")
    game_env.timers.tick_intervals(10)
    assert game_env.earth["ecology_health"] == 100.0
    assert game_env.mars["ecology_health"] == 100.0
    assert game_env.moon["ecology_health"] == 100.0
    assert game_env.venus["ecology_health"] == 100.0
    assert game_env.asteroid_belt["ecology_health"] == 100.0
    assert game_env.pluto["ecology_health"] == 100.0


# --- production penalty / halt, independent of other planets ---------------

def test_jupiter_moons_production_halted_at_zero_ecology(game_env):
    game_env.jupiter_moons["generator_count"] = 1
    game_env.jupiter_moons["ecology_health"] = 0.0
    game_env.jupiter_moons["resource_count"] = 0
    game_env.module.tick()
    assert game_env.jupiter_moons["resource_count"] == 0


def test_jupiter_moons_production_unaffected_by_earths_ecology(game_env):
    game_env.earth["ecology_health"] = 0.0
    game_env.jupiter_moons["generator_count"] = 1
    game_env.jupiter_moons["resource_count"] = 0
    game_env.module.tick()
    assert game_env.jupiter_moons["resource_count"] > 0


def test_jupiter_moons_status_message_at_collapse(game_env):
    game_env.jupiter_moons["ecology_health"] = 0.0
    game_env.module.update_ecology_display("JupiterMoons")
    assert "halted" in game_env.elements["jupitermoons-ecology-status"].innerText


# --- travel wiring: Jupiter's Moons's own dedicated view -------------------

def test_jupiter_moons_view_hidden_by_default(game_env):
    assert game_env.elements["jupitermoons-view"].hidden is True


def test_jupiter_moons_return_to_earth_button_wired(game_env):
    button = game_env.elements["jupitermoons-return-to-earth-button"]
    assert "click" in button._listeners
    assert len(button._listeners["click"]) == 1


def test_traveling_to_jupiter_moons_requires_tier_2_unlock(game_env):
    game_env.travel_to("JupiterMoons")
    assert game_env.module.current_planet == "Earth"

    game_env.module.unlocked_bodies.add("JupiterMoons")
    game_env.travel_to("JupiterMoons")
    assert game_env.module.current_planet == "JupiterMoons"
    assert game_env.elements["jupitermoons-view"].hidden is False


# --- Jupiter's Moons and the other six economies are fully independent ----

def test_all_seven_resource_counts_are_independent(game_env):
    game_env.click("JupiterMoons")
    game_env.click("JupiterMoons")
    game_env.click("Pluto")
    game_env.click("AsteroidBelt")
    game_env.click("Venus")
    game_env.click("Moon")
    game_env.click("Mars")
    game_env.click()  # Earth
    assert game_env.jupiter_moons["resource_count"] == 2
    assert game_env.pluto["resource_count"] == 1
    assert game_env.asteroid_belt["resource_count"] == 1
    assert game_env.venus["resource_count"] == 1
    assert game_env.moon["resource_count"] == 1
    assert game_env.mars["resource_count"] == 1
    assert game_env.earth["resource_count"] == 1


def test_all_seven_generator_counts_are_independent(game_env):
    game_env.earth["resource_count"] = 100
    game_env.mars["resource_count"] = 100
    game_env.moon["resource_count"] = 100
    game_env.venus["resource_count"] = 100
    game_env.asteroid_belt["resource_count"] = 100
    game_env.pluto["resource_count"] = 100
    game_env.jupiter_moons["resource_count"] = 100
    game_env.buy_generator()  # Earth
    assert game_env.earth["generator_count"] == 1
    assert game_env.mars["generator_count"] == 0
    assert game_env.moon["generator_count"] == 0
    assert game_env.venus["generator_count"] == 0
    assert game_env.asteroid_belt["generator_count"] == 0
    assert game_env.pluto["generator_count"] == 0
    assert game_env.jupiter_moons["generator_count"] == 0
