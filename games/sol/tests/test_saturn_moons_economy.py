"""Tests for the Milestone 9g resource loop: Saturn's Moons get their own
Methane click loop, Auto-Condenser automation, and ecology/Recycler system
— the eighth and final full reuse of the standard building system after
Earth, Mars, Moon, Venus, the Asteroid Belt, Pluto, and Jupiter's Moons.
Per the "parallel-unlock" framing, this is ONE combined economy for the
whole Saturn's Moons body, not one per moon (Titan, Enceladus, etc.). With
this milestone, every Far Body now has a real economy — see
test_research_tier2_framework.py for how that retires the #away-view
placeholder. These tests focus on Saturn's-Moons-specific wiring and
naming rather than re-proving the shared math (already covered generically
via game_env.earth in other files)."""

import math
from pathlib import Path

INDEX_HTML = Path(__file__).resolve().parent.parent / "index.html"


# --- setup / initial state ----------------------------------------------

def test_saturn_moons_resource_label_names_methane_in_html():
    # The label text is static markup (never touched by game.py, matching
    # Earth's original design), so it can only be checked against the real
    # file rather than through the fake-DOM harness used elsewhere.
    html = INDEX_HTML.read_text()
    assert 'id="saturnmoons-resource-label"' in html
    assert "Methane — Saturn's Moons" in html


def test_saturn_moons_click_button_configured(game_env):
    button = game_env.elements["saturnmoons-click-button"]
    assert button.innerText == "Condense Methane"
    assert button.disabled is False


def test_saturn_moons_starts_at_zero_resource(game_env):
    assert game_env.saturn_moons["resource_count"] == 0
    assert game_env.elements["saturnmoons-resource-count"].innerText == "0"


def test_saturn_moons_generator_button_configured(game_env):
    button = game_env.elements["saturnmoons-buy-generator-button"]
    assert button.disabled is False
    assert "10 Methane" in button.innerText


def test_saturn_moons_recycler_button_configured(game_env):
    button = game_env.elements["saturnmoons-buy-recycler-button"]
    assert button.disabled is False
    assert "15 Methane" in button.innerText


def test_saturn_moons_ecology_starts_at_full_health(game_env):
    assert game_env.saturn_moons["ecology_health"] == 100.0
    assert game_env.elements["saturnmoons-ecology-percent"].innerText == "100%"


# --- clicking (manual collection) ----------------------------------------

def test_saturn_moons_click_increments_resource(game_env):
    game_env.click("SaturnMoons")
    assert game_env.saturn_moons["resource_count"] == 1


def test_saturn_moons_click_does_not_affect_other_planets(game_env):
    game_env.click("SaturnMoons")
    assert game_env.earth["resource_count"] == 0
    assert game_env.mars["resource_count"] == 0
    assert game_env.moon["resource_count"] == 0
    assert game_env.venus["resource_count"] == 0
    assert game_env.asteroid_belt["resource_count"] == 0
    assert game_env.pluto["resource_count"] == 0
    assert game_env.jupiter_moons["resource_count"] == 0


def test_saturn_moons_click_gives_press_feedback(game_env):
    button = game_env.elements["saturnmoons-click-button"]
    game_env.click("SaturnMoons")
    assert button.classList.contains("pressed")
    game_env.timers.flush()
    assert not button.classList.contains("pressed")


def test_saturn_moons_manual_click_never_halted_by_ecology(game_env):
    game_env.saturn_moons["ecology_health"] = 0.0
    game_env.click("SaturnMoons")
    assert game_env.saturn_moons["resource_count"] == 1


# --- Auto-Condenser (Saturn's Moons's generator) ----------------------------

def test_buying_saturn_moons_generator_deducts_cost_and_increments(game_env):
    game_env.saturn_moons["resource_count"] = 10
    game_env.buy_generator("SaturnMoons")
    assert game_env.saturn_moons["generator_count"] == 1
    assert game_env.saturn_moons["resource_count"] == 0


def test_buying_saturn_moons_generator_does_not_touch_other_planets(game_env):
    game_env.saturn_moons["resource_count"] = 10
    game_env.buy_generator("SaturnMoons")
    assert game_env.earth["generator_count"] == 0
    assert game_env.mars["generator_count"] == 0
    assert game_env.moon["generator_count"] == 0
    assert game_env.venus["generator_count"] == 0
    assert game_env.asteroid_belt["generator_count"] == 0
    assert game_env.pluto["generator_count"] == 0
    assert game_env.jupiter_moons["generator_count"] == 0


def test_saturn_moons_generator_cost_scales_independently(game_env):
    game_env.saturn_moons["resource_count"] = 1000
    game_env.buy_generator("SaturnMoons")
    saturn_moons_cost = game_env.module.generator_cost("SaturnMoons")
    earth_cost = game_env.module.generator_cost("Earth")
    assert saturn_moons_cost > earth_cost  # Saturn's Moons bought one already, Earth hasn't


def test_saturn_moons_generator_produces_methane_over_ticks(game_env):
    game_env.saturn_moons["resource_count"] = 10
    game_env.buy_generator("SaturnMoons")  # 1 condenser, rate 1/s
    game_env.timers.tick_intervals(10)  # 1 second
    assert math.isclose(game_env.saturn_moons["resource_count"], 1.0, abs_tol=1e-9)


def test_saturn_moons_generator_display_updates(game_env):
    game_env.saturn_moons["resource_count"] = 10
    game_env.buy_generator("SaturnMoons")
    assert game_env.elements["saturnmoons-generator-count"].innerText == "1"
    assert game_env.elements["saturnmoons-generator-rate"].innerText == "1"


# --- Recycler (Saturn's Moons's ecology-restoring building) ----------------

def test_buying_saturn_moons_recycler_deducts_cost_and_increments(game_env):
    game_env.saturn_moons["resource_count"] = 15
    game_env.buy_recycler("SaturnMoons")
    assert game_env.saturn_moons["recycler_count"] == 1
    assert game_env.saturn_moons["resource_count"] == 0


def test_saturn_moons_recycler_restores_ecology_over_ticks(game_env):
    game_env.saturn_moons["ecology_health"] = 50.0
    game_env.saturn_moons["resource_count"] = 15
    game_env.buy_recycler("SaturnMoons")  # 1 recycler, restore 2%/s
    game_env.timers.tick_intervals(10)  # 1 second
    assert math.isclose(game_env.saturn_moons["ecology_health"], 52.0, abs_tol=1e-6)


def test_saturn_moons_ecology_decays_from_its_own_generators(game_env):
    game_env.saturn_moons["resource_count"] = 10
    game_env.buy_generator("SaturnMoons")
    game_env.timers.tick_intervals(10)  # 1 second
    assert math.isclose(game_env.saturn_moons["ecology_health"], 99.0, abs_tol=1e-6)


def test_saturn_moons_ecology_decay_does_not_affect_other_planets(game_env):
    game_env.saturn_moons["resource_count"] = 10
    game_env.buy_generator("SaturnMoons")
    game_env.timers.tick_intervals(10)
    assert game_env.earth["ecology_health"] == 100.0
    assert game_env.mars["ecology_health"] == 100.0
    assert game_env.moon["ecology_health"] == 100.0
    assert game_env.venus["ecology_health"] == 100.0
    assert game_env.asteroid_belt["ecology_health"] == 100.0
    assert game_env.pluto["ecology_health"] == 100.0
    assert game_env.jupiter_moons["ecology_health"] == 100.0


# --- production penalty / halt, independent of other planets ---------------

def test_saturn_moons_production_halted_at_zero_ecology(game_env):
    game_env.saturn_moons["generator_count"] = 1
    game_env.saturn_moons["ecology_health"] = 0.0
    game_env.saturn_moons["resource_count"] = 0
    game_env.module.tick()
    assert game_env.saturn_moons["resource_count"] == 0


def test_saturn_moons_production_unaffected_by_earths_ecology(game_env):
    game_env.earth["ecology_health"] = 0.0
    game_env.saturn_moons["generator_count"] = 1
    game_env.saturn_moons["resource_count"] = 0
    game_env.module.tick()
    assert game_env.saturn_moons["resource_count"] > 0


def test_saturn_moons_status_message_at_collapse(game_env):
    game_env.saturn_moons["ecology_health"] = 0.0
    game_env.module.update_ecology_display("SaturnMoons")
    assert "halted" in game_env.elements["saturnmoons-ecology-status"].innerText


# --- travel wiring: Saturn's Moons's own dedicated view --------------------

def test_saturn_moons_view_hidden_by_default(game_env):
    assert game_env.elements["saturnmoons-view"].hidden is True


def test_saturn_moons_return_to_earth_button_wired(game_env):
    button = game_env.elements["saturnmoons-return-to-earth-button"]
    assert "click" in button._listeners
    assert len(button._listeners["click"]) == 1


def test_traveling_to_saturn_moons_requires_tier_2_unlock(game_env):
    game_env.travel_to("SaturnMoons")
    assert game_env.module.current_planet == "Earth"

    game_env.module.unlocked_bodies.add("SaturnMoons")
    game_env.travel_to("SaturnMoons")
    assert game_env.module.current_planet == "SaturnMoons"
    assert game_env.elements["saturnmoons-view"].hidden is False


# --- Saturn's Moons and the other seven economies are fully independent ---

def test_all_eight_resource_counts_are_independent(game_env):
    game_env.click("SaturnMoons")
    game_env.click("SaturnMoons")
    game_env.click("JupiterMoons")
    game_env.click("Pluto")
    game_env.click("AsteroidBelt")
    game_env.click("Venus")
    game_env.click("Moon")
    game_env.click("Mars")
    game_env.click()  # Earth
    assert game_env.saturn_moons["resource_count"] == 2
    assert game_env.jupiter_moons["resource_count"] == 1
    assert game_env.pluto["resource_count"] == 1
    assert game_env.asteroid_belt["resource_count"] == 1
    assert game_env.venus["resource_count"] == 1
    assert game_env.moon["resource_count"] == 1
    assert game_env.mars["resource_count"] == 1
    assert game_env.earth["resource_count"] == 1


def test_all_eight_generator_counts_are_independent(game_env):
    game_env.earth["resource_count"] = 100
    game_env.mars["resource_count"] = 100
    game_env.moon["resource_count"] = 100
    game_env.venus["resource_count"] = 100
    game_env.asteroid_belt["resource_count"] = 100
    game_env.pluto["resource_count"] = 100
    game_env.jupiter_moons["resource_count"] = 100
    game_env.saturn_moons["resource_count"] = 100
    game_env.buy_generator()  # Earth
    assert game_env.earth["generator_count"] == 1
    assert game_env.mars["generator_count"] == 0
    assert game_env.moon["generator_count"] == 0
    assert game_env.venus["generator_count"] == 0
    assert game_env.asteroid_belt["generator_count"] == 0
    assert game_env.pluto["generator_count"] == 0
    assert game_env.jupiter_moons["generator_count"] == 0
    assert game_env.saturn_moons["generator_count"] == 0
