"""Tests for the Milestone 9c resource loop: Venus gets its own Sulfur
click loop, Auto-Scrubber automation, and ecology/Recycler system — the
fourth full reuse of the standard building system after Earth, Mars, and
Moon. These tests focus on Venus-specific wiring and naming rather than
re-proving the shared math (already covered generically via game_env.earth
in other files)."""

import math
from pathlib import Path

INDEX_HTML = Path(__file__).resolve().parent.parent / "index.html"


# --- setup / initial state ----------------------------------------------

def test_venus_resource_label_names_sulfur_in_html():
    # The label text is static markup (never touched by game.py, matching
    # Earth's original design), so it can only be checked against the real
    # file rather than through the fake-DOM harness used elsewhere.
    html = INDEX_HTML.read_text()
    assert 'id="venus-resource-label"' in html
    assert "Sulfur — Venus" in html


def test_venus_click_button_configured(game_env):
    button = game_env.elements["venus-click-button"]
    assert button.innerText == "Collect Sulfur"
    assert button.disabled is False


def test_venus_starts_at_zero_resource(game_env):
    assert game_env.venus["resource_count"] == 0
    assert game_env.elements["venus-resource-count"].innerText == "0"


def test_venus_generator_button_configured(game_env):
    button = game_env.elements["venus-buy-generator-button"]
    assert button.disabled is False
    assert "10 Sulfur" in button.innerText


def test_venus_recycler_button_configured(game_env):
    button = game_env.elements["venus-buy-recycler-button"]
    assert button.disabled is False
    assert "15 Sulfur" in button.innerText


def test_venus_ecology_starts_at_full_health(game_env):
    assert game_env.venus["ecology_health"] == 100.0
    assert game_env.elements["venus-ecology-percent"].innerText == "100%"


# --- clicking (manual collection) ----------------------------------------

def test_venus_click_increments_resource(game_env):
    game_env.click("Venus")
    assert game_env.venus["resource_count"] == 1


def test_venus_click_does_not_affect_other_planets(game_env):
    game_env.click("Venus")
    assert game_env.earth["resource_count"] == 0
    assert game_env.mars["resource_count"] == 0
    assert game_env.moon["resource_count"] == 0


def test_venus_click_gives_press_feedback(game_env):
    button = game_env.elements["venus-click-button"]
    game_env.click("Venus")
    assert button.classList.contains("pressed")
    game_env.timers.flush()
    assert not button.classList.contains("pressed")


def test_venus_manual_click_never_halted_by_ecology(game_env):
    game_env.venus["ecology_health"] = 0.0
    game_env.click("Venus")
    assert game_env.venus["resource_count"] == 1


# --- Auto-Scrubber (Venus's generator) -------------------------------------

def test_buying_venus_generator_deducts_cost_and_increments(game_env):
    game_env.venus["resource_count"] = 10
    game_env.buy_generator("Venus")
    assert game_env.venus["generator_count"] == 1
    assert game_env.venus["resource_count"] == 0


def test_buying_venus_generator_does_not_touch_other_planets(game_env):
    game_env.venus["resource_count"] = 10
    game_env.buy_generator("Venus")
    assert game_env.earth["generator_count"] == 0
    assert game_env.mars["generator_count"] == 0
    assert game_env.moon["generator_count"] == 0


def test_venus_generator_cost_scales_independently(game_env):
    game_env.venus["resource_count"] = 1000
    game_env.buy_generator("Venus")
    venus_cost = game_env.module.generator_cost("Venus")
    earth_cost = game_env.module.generator_cost("Earth")
    assert venus_cost > earth_cost  # Venus bought one already, Earth hasn't


def test_venus_generator_produces_sulfur_over_ticks(game_env):
    game_env.venus["resource_count"] = 10
    game_env.buy_generator("Venus")  # 1 scrubber, rate 1/s
    game_env.timers.tick_intervals(10)  # 1 second
    assert math.isclose(game_env.venus["resource_count"], 1.0, abs_tol=1e-9)


def test_venus_generator_display_updates(game_env):
    game_env.venus["resource_count"] = 10
    game_env.buy_generator("Venus")
    assert game_env.elements["venus-generator-count"].innerText == "1"
    assert game_env.elements["venus-generator-rate"].innerText == "1"


# --- Recycler (Venus's ecology-restoring building) -------------------------

def test_buying_venus_recycler_deducts_cost_and_increments(game_env):
    game_env.venus["resource_count"] = 15
    game_env.buy_recycler("Venus")
    assert game_env.venus["recycler_count"] == 1
    assert game_env.venus["resource_count"] == 0


def test_venus_recycler_restores_ecology_over_ticks(game_env):
    game_env.venus["ecology_health"] = 50.0
    game_env.venus["resource_count"] = 15
    game_env.buy_recycler("Venus")  # 1 recycler, restore 2%/s
    game_env.timers.tick_intervals(10)  # 1 second
    assert math.isclose(game_env.venus["ecology_health"], 52.0, abs_tol=1e-6)


def test_venus_ecology_decays_from_its_own_generators(game_env):
    game_env.venus["resource_count"] = 10
    game_env.buy_generator("Venus")
    game_env.timers.tick_intervals(10)  # 1 second
    assert math.isclose(game_env.venus["ecology_health"], 99.0, abs_tol=1e-6)


def test_venus_ecology_decay_does_not_affect_other_planets(game_env):
    game_env.venus["resource_count"] = 10
    game_env.buy_generator("Venus")
    game_env.timers.tick_intervals(10)
    assert game_env.earth["ecology_health"] == 100.0
    assert game_env.mars["ecology_health"] == 100.0
    assert game_env.moon["ecology_health"] == 100.0


# --- production penalty / halt, independent of other planets ---------------

def test_venus_production_halted_at_zero_ecology(game_env):
    game_env.venus["generator_count"] = 1
    game_env.venus["ecology_health"] = 0.0
    game_env.venus["resource_count"] = 0
    game_env.module.tick()
    assert game_env.venus["resource_count"] == 0


def test_venus_production_unaffected_by_earths_ecology(game_env):
    game_env.earth["ecology_health"] = 0.0
    game_env.venus["generator_count"] = 1
    game_env.venus["resource_count"] = 0
    game_env.module.tick()
    assert game_env.venus["resource_count"] > 0


def test_venus_status_message_at_collapse(game_env):
    game_env.venus["ecology_health"] = 0.0
    game_env.module.update_ecology_display("Venus")
    assert "halted" in game_env.elements["venus-ecology-status"].innerText


# --- travel wiring: Venus's own dedicated view -----------------------------

def test_venus_view_hidden_by_default(game_env):
    assert game_env.elements["venus-view"].hidden is True


def test_venus_return_to_earth_button_wired(game_env):
    button = game_env.elements["venus-return-to-earth-button"]
    assert "click" in button._listeners
    assert len(button._listeners["click"]) == 1


def test_traveling_to_venus_requires_tier_2_unlock(game_env):
    game_env.travel_to("Venus")
    assert game_env.module.current_planet == "Earth"

    game_env.module.unlocked_bodies.add("Venus")
    game_env.travel_to("Venus")
    assert game_env.module.current_planet == "Venus"
    assert game_env.elements["venus-view"].hidden is False


# --- Venus and the other three economies are fully independent ------------

def test_all_four_resource_counts_are_independent(game_env):
    game_env.click("Venus")
    game_env.click("Venus")
    game_env.click("Moon")
    game_env.click("Mars")
    game_env.click()  # Earth
    assert game_env.venus["resource_count"] == 2
    assert game_env.moon["resource_count"] == 1
    assert game_env.mars["resource_count"] == 1
    assert game_env.earth["resource_count"] == 1


def test_all_four_generator_counts_are_independent(game_env):
    game_env.earth["resource_count"] = 100
    game_env.mars["resource_count"] = 100
    game_env.moon["resource_count"] = 100
    game_env.venus["resource_count"] = 100
    game_env.buy_generator()  # Earth
    assert game_env.earth["generator_count"] == 1
    assert game_env.mars["generator_count"] == 0
    assert game_env.moon["generator_count"] == 0
    assert game_env.venus["generator_count"] == 0
