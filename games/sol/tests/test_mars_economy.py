"""Tests for the Milestone 6 second-planet resource loop: Mars gets its own
Water Ice click loop, Auto-Extractor automation, and ecology/Recycler
system — a direct reuse of the Milestone 2/3 mechanics already proven for
Earth in test_automation.py / test_ecology.py, just reskinned. These tests
focus on Mars-specific wiring and naming rather than re-proving the shared
math (already covered generically via game_env.earth in other files)."""

import math
from pathlib import Path

INDEX_HTML = Path(__file__).resolve().parent.parent / "index.html"


# --- setup / initial state ----------------------------------------------

def test_mars_resource_label_names_water_ice_in_html():
    # The label text is static markup (never touched by game.py, matching
    # Earth's original design), so it can only be checked against the real
    # file rather than through the fake-DOM harness used elsewhere.
    html = INDEX_HTML.read_text()
    assert 'id="mars-resource-label"' in html
    assert "Water Ice — Mars" in html


def test_mars_click_button_configured(game_env):
    button = game_env.elements["mars-click-button"]
    assert button.innerText == "Extract Ice"
    assert button.disabled is False


def test_mars_starts_at_zero_resource(game_env):
    assert game_env.mars["resource_count"] == 0
    assert game_env.elements["mars-resource-count"].innerText == "0"


def test_mars_generator_button_configured(game_env):
    button = game_env.elements["mars-buy-generator-button"]
    assert button.disabled is False
    assert "10 Water Ice" in button.innerText


def test_mars_recycler_button_configured(game_env):
    button = game_env.elements["mars-buy-recycler-button"]
    assert button.disabled is False
    assert "15 Water Ice" in button.innerText


def test_mars_ecology_starts_at_full_health(game_env):
    assert game_env.mars["ecology_health"] == 100.0
    assert game_env.elements["mars-ecology-percent"].innerText == "100%"


# --- clicking (manual extraction) ----------------------------------------

def test_mars_click_increments_resource(game_env):
    game_env.click("Mars")
    assert game_env.mars["resource_count"] == 1


def test_mars_click_does_not_affect_earth(game_env):
    game_env.click("Mars")
    assert game_env.earth["resource_count"] == 0


def test_mars_click_gives_press_feedback(game_env):
    button = game_env.elements["mars-click-button"]
    game_env.click("Mars")
    assert button.classList.contains("pressed")
    game_env.timers.flush()
    assert not button.classList.contains("pressed")


def test_mars_manual_click_never_halted_by_ecology(game_env):
    game_env.mars["ecology_health"] = 0.0
    game_env.click("Mars")
    assert game_env.mars["resource_count"] == 1


# --- Auto-Extractor (Mars's generator) -----------------------------------

def test_buying_mars_generator_deducts_cost_and_increments(game_env):
    game_env.mars["resource_count"] = 10
    game_env.buy_generator("Mars")
    assert game_env.mars["generator_count"] == 1
    assert game_env.mars["resource_count"] == 0


def test_buying_mars_generator_does_not_touch_earth(game_env):
    game_env.mars["resource_count"] = 10
    game_env.buy_generator("Mars")
    assert game_env.earth["generator_count"] == 0


def test_mars_generator_cost_scales_independently_of_earth(game_env):
    game_env.mars["resource_count"] = 1000
    game_env.buy_generator("Mars")
    mars_cost = game_env.module.generator_cost("Mars")
    earth_cost = game_env.module.generator_cost("Earth")
    assert mars_cost > earth_cost  # Mars bought one already, Earth hasn't


def test_mars_generator_produces_water_ice_over_ticks(game_env):
    game_env.mars["resource_count"] = 10
    game_env.buy_generator("Mars")  # 1 extractor, rate 1/s
    game_env.timers.tick_intervals(10)  # 1 second
    assert math.isclose(game_env.mars["resource_count"], 1.0, abs_tol=1e-9)


def test_mars_generator_display_updates(game_env):
    game_env.mars["resource_count"] = 10
    game_env.buy_generator("Mars")
    assert game_env.elements["mars-generator-count"].innerText == "1"
    assert game_env.elements["mars-generator-rate"].innerText == "1"


# --- Recycler (Mars's ecology-restoring building) -------------------------

def test_buying_mars_recycler_deducts_cost_and_increments(game_env):
    game_env.mars["resource_count"] = 15
    game_env.buy_recycler("Mars")
    assert game_env.mars["recycler_count"] == 1
    assert game_env.mars["resource_count"] == 0


def test_mars_recycler_restores_ecology_over_ticks(game_env):
    game_env.mars["ecology_health"] = 50.0
    game_env.mars["resource_count"] = 15
    game_env.buy_recycler("Mars")  # 1 recycler, restore 2%/s
    game_env.timers.tick_intervals(10)  # 1 second
    assert math.isclose(game_env.mars["ecology_health"], 52.0, abs_tol=1e-6)


def test_mars_ecology_decays_from_its_own_generators(game_env):
    game_env.mars["resource_count"] = 10
    game_env.buy_generator("Mars")
    game_env.timers.tick_intervals(10)  # 1 second
    assert math.isclose(game_env.mars["ecology_health"], 99.0, abs_tol=1e-6)


def test_mars_ecology_decay_does_not_affect_earth(game_env):
    game_env.mars["resource_count"] = 10
    game_env.buy_generator("Mars")
    game_env.timers.tick_intervals(10)
    assert game_env.earth["ecology_health"] == 100.0


# --- production penalty / halt, independent of Earth ----------------------

def test_mars_production_halted_at_zero_ecology(game_env):
    game_env.mars["generator_count"] = 1
    game_env.mars["ecology_health"] = 0.0
    game_env.mars["resource_count"] = 0
    game_env.module.tick()
    assert game_env.mars["resource_count"] == 0


def test_mars_production_unaffected_by_earths_ecology(game_env):
    # Earth in collapse shouldn't halt Mars's independent economy.
    game_env.earth["ecology_health"] = 0.0
    game_env.mars["generator_count"] = 1
    game_env.mars["resource_count"] = 0
    game_env.module.tick()
    assert game_env.mars["resource_count"] > 0


def test_mars_status_message_at_collapse(game_env):
    game_env.mars["ecology_health"] = 0.0
    game_env.module.update_ecology_display("Mars")
    assert "halted" in game_env.elements["mars-ecology-status"].innerText


# --- Mars and Earth economies are fully independent -----------------------

def test_earth_and_mars_resource_counts_are_independent(game_env):
    game_env.click("Mars")
    game_env.click("Mars")
    game_env.click()  # Earth
    assert game_env.mars["resource_count"] == 2
    assert game_env.earth["resource_count"] == 1


def test_earth_and_mars_generator_counts_are_independent(game_env):
    game_env.earth["resource_count"] = 100
    game_env.mars["resource_count"] = 100
    game_env.buy_generator()  # Earth
    assert game_env.earth["generator_count"] == 1
    assert game_env.mars["generator_count"] == 0
