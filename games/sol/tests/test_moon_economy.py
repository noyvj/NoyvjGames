"""Tests for the Milestone 9b resource loop: Moon gets its own Regolith
click loop, Auto-Harvester automation, and ecology/Recycler system — a
direct reuse of the Milestone 2/3 mechanics already proven for Earth and
Mars, just reskinned again. These tests focus on Moon-specific wiring and
naming rather than re-proving the shared math (already covered generically
via game_env.earth in other files)."""

import math
from pathlib import Path

INDEX_HTML = Path(__file__).resolve().parent.parent / "index.html"


# --- setup / initial state ----------------------------------------------

def test_moon_resource_label_names_regolith_in_html():
    # The label text is static markup (never touched by game.py, matching
    # Earth's original design), so it can only be checked against the real
    # file rather than through the fake-DOM harness used elsewhere.
    html = INDEX_HTML.read_text()
    assert 'id="moon-resource-label"' in html
    assert "Regolith — Moon" in html


def test_moon_click_button_configured(game_env):
    button = game_env.elements["moon-click-button"]
    assert button.innerText == "Mine Regolith"
    assert button.disabled is False


def test_moon_starts_at_zero_resource(game_env):
    assert game_env.moon["resource_count"] == 0
    assert game_env.elements["moon-resource-count"].innerText == "0"


def test_moon_generator_button_configured(game_env):
    button = game_env.elements["moon-buy-generator-button"]
    assert button.disabled is False
    assert "10 Regolith" in button.innerText


def test_moon_recycler_button_configured(game_env):
    button = game_env.elements["moon-buy-recycler-button"]
    assert button.disabled is False
    assert "15 Regolith" in button.innerText


def test_moon_ecology_starts_at_full_health(game_env):
    assert game_env.moon["ecology_health"] == 100.0
    assert game_env.elements["moon-ecology-percent"].innerText == "100%"


# --- clicking (manual harvesting) ----------------------------------------

def test_moon_click_increments_resource(game_env):
    game_env.click("Moon")
    assert game_env.moon["resource_count"] == 1


def test_moon_click_does_not_affect_earth_or_mars(game_env):
    game_env.click("Moon")
    assert game_env.earth["resource_count"] == 0
    assert game_env.mars["resource_count"] == 0


def test_moon_click_gives_press_feedback(game_env):
    button = game_env.elements["moon-click-button"]
    game_env.click("Moon")
    assert button.classList.contains("pressed")
    game_env.timers.flush()
    assert not button.classList.contains("pressed")


def test_moon_manual_click_never_halted_by_ecology(game_env):
    game_env.moon["ecology_health"] = 0.0
    game_env.click("Moon")
    assert game_env.moon["resource_count"] == 1


# --- Auto-Harvester (Moon's generator) -----------------------------------

def test_buying_moon_generator_deducts_cost_and_increments(game_env):
    game_env.moon["resource_count"] = 10
    game_env.buy_generator("Moon")
    assert game_env.moon["generator_count"] == 1
    assert game_env.moon["resource_count"] == 0


def test_buying_moon_generator_does_not_touch_earth_or_mars(game_env):
    game_env.moon["resource_count"] = 10
    game_env.buy_generator("Moon")
    assert game_env.earth["generator_count"] == 0
    assert game_env.mars["generator_count"] == 0


def test_moon_generator_cost_scales_independently(game_env):
    game_env.moon["resource_count"] = 1000
    game_env.buy_generator("Moon")
    moon_cost = game_env.module.generator_cost("Moon")
    earth_cost = game_env.module.generator_cost("Earth")
    assert moon_cost > earth_cost  # Moon bought one already, Earth hasn't


def test_moon_generator_produces_regolith_over_ticks(game_env):
    game_env.moon["resource_count"] = 10
    game_env.buy_generator("Moon")  # 1 harvester, rate 1/s
    game_env.timers.tick_intervals(10)  # 1 second
    assert math.isclose(game_env.moon["resource_count"], 1.0, abs_tol=1e-9)


def test_moon_generator_display_updates(game_env):
    game_env.moon["resource_count"] = 10
    game_env.buy_generator("Moon")
    assert game_env.elements["moon-generator-count"].innerText == "1"
    assert game_env.elements["moon-generator-rate"].innerText == "1"


# --- Recycler (Moon's ecology-restoring building) -------------------------

def test_buying_moon_recycler_deducts_cost_and_increments(game_env):
    game_env.moon["resource_count"] = 15
    game_env.buy_recycler("Moon")
    assert game_env.moon["recycler_count"] == 1
    assert game_env.moon["resource_count"] == 0


def test_moon_recycler_restores_ecology_over_ticks(game_env):
    game_env.moon["ecology_health"] = 50.0
    game_env.moon["resource_count"] = 15
    game_env.buy_recycler("Moon")  # 1 recycler, restore 2%/s
    game_env.timers.tick_intervals(10)  # 1 second
    assert math.isclose(game_env.moon["ecology_health"], 52.0, abs_tol=1e-6)


def test_moon_ecology_decays_from_its_own_generators(game_env):
    game_env.moon["resource_count"] = 10
    game_env.buy_generator("Moon")
    game_env.timers.tick_intervals(10)  # 1 second
    assert math.isclose(game_env.moon["ecology_health"], 99.0, abs_tol=1e-6)


def test_moon_ecology_decay_does_not_affect_earth_or_mars(game_env):
    game_env.moon["resource_count"] = 10
    game_env.buy_generator("Moon")
    game_env.timers.tick_intervals(10)
    assert game_env.earth["ecology_health"] == 100.0
    assert game_env.mars["ecology_health"] == 100.0


# --- production penalty / halt, independent of Earth/Mars -----------------

def test_moon_production_halted_at_zero_ecology(game_env):
    game_env.moon["generator_count"] = 1
    game_env.moon["ecology_health"] = 0.0
    game_env.moon["resource_count"] = 0
    game_env.module.tick()
    assert game_env.moon["resource_count"] == 0


def test_moon_production_unaffected_by_earths_ecology(game_env):
    game_env.earth["ecology_health"] = 0.0
    game_env.moon["generator_count"] = 1
    game_env.moon["resource_count"] = 0
    game_env.module.tick()
    assert game_env.moon["resource_count"] > 0


def test_moon_status_message_at_collapse(game_env):
    game_env.moon["ecology_health"] = 0.0
    game_env.module.update_ecology_display("Moon")
    assert "halted" in game_env.elements["moon-ecology-status"].innerText


# --- travel wiring: Moon's own dedicated view ------------------------------

def test_moon_view_hidden_by_default(game_env):
    assert game_env.elements["moon-view"].hidden is True


def test_moon_return_to_earth_button_wired(game_env):
    button = game_env.elements["moon-return-to-earth-button"]
    assert "click" in button._listeners
    assert len(button._listeners["click"]) == 1


# --- Moon, Earth, and Mars economies are fully independent ----------------

def test_all_three_resource_counts_are_independent(game_env):
    game_env.click("Moon")
    game_env.click("Moon")
    game_env.click("Mars")
    game_env.click()  # Earth
    assert game_env.moon["resource_count"] == 2
    assert game_env.mars["resource_count"] == 1
    assert game_env.earth["resource_count"] == 1


def test_all_three_generator_counts_are_independent(game_env):
    game_env.earth["resource_count"] = 100
    game_env.mars["resource_count"] = 100
    game_env.moon["resource_count"] = 100
    game_env.buy_generator()  # Earth
    assert game_env.earth["generator_count"] == 1
    assert game_env.mars["generator_count"] == 0
    assert game_env.moon["generator_count"] == 0
