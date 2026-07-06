"""Tests for the Milestone 3 ecology system on Earth: sustainability meter,
the penalty/halt curve, and Recycler buildings that recover ecological health."""

import math


# --- setup / initial state ---------------------------------------------

def test_ecology_starts_at_full_health(game_env):
    assert game_env.earth["ecology_health"] == 100.0
    assert game_env.elements["ecology-percent"].innerText == "100%"


def test_ecology_bar_starts_full_width(game_env):
    assert game_env.elements["ecology-bar"].style.width == "100.0%"


def test_ecology_status_empty_at_full_health(game_env):
    assert game_env.elements["ecology-status"].innerText == ""


def test_setup_configures_recycler_button(game_env):
    button = game_env.elements["buy-recycler-button"]
    assert button.disabled is False
    assert "15 Iron" in button.innerText


def test_setup_registers_recycler_listener(game_env):
    button = game_env.elements["buy-recycler-button"]
    assert "click" in button._listeners
    assert len(button._listeners["click"]) == 1


def test_initial_recycler_state(game_env):
    assert game_env.earth["recycler_count"] == 0
    assert game_env.elements["recycler-count"].innerText == "0"
    assert game_env.elements["recycler-rate"].innerText == "0.0"


# --- production_multiplier() threshold behaviour -------------------------

def test_multiplier_is_full_above_threshold(game_env):
    game_env.earth["ecology_health"] = 50.0
    assert game_env.module.production_multiplier("Earth") == 1.0


def test_multiplier_is_full_exactly_at_threshold(game_env):
    # Spec: "Below 10% health" triggers the penalty — exactly 10% should not.
    game_env.earth["ecology_health"] = 10.0
    assert game_env.module.production_multiplier("Earth") == 1.0


def test_multiplier_is_penalized_just_below_threshold(game_env):
    game_env.earth["ecology_health"] = 9.999
    assert game_env.module.production_multiplier("Earth") == 0.75


def test_multiplier_is_penalized_throughout_low_band(game_env):
    game_env.earth["ecology_health"] = 1.0
    assert game_env.module.production_multiplier("Earth") == 0.75


def test_multiplier_is_zero_at_exactly_zero(game_env):
    game_env.earth["ecology_health"] = 0.0
    assert game_env.module.production_multiplier("Earth") == 0.0


def test_multiplier_is_zero_below_zero(game_env):
    # Defensive: clamp() should prevent this state, but the multiplier
    # itself should not assume health can never go negative.
    game_env.earth["ecology_health"] = -5.0
    assert game_env.module.production_multiplier("Earth") == 0.0


# --- clamp() ---------------------------------------------------------------

def test_clamp_keeps_value_in_range(game_env):
    clamp = game_env.module.clamp
    assert clamp(50, 0, 100) == 50


def test_clamp_floors_at_low(game_env):
    clamp = game_env.module.clamp
    assert clamp(-10, 0, 100) == 0


def test_clamp_ceils_at_high(game_env):
    clamp = game_env.module.clamp
    assert clamp(150, 0, 100) == 100


# --- ecology decay from generators -----------------------------------------

def test_generator_decays_ecology_over_ticks(game_env):
    game_env.earth["resource_count"] = 10
    game_env.buy_generator()  # 1 generator, decay 1.0%/s
    game_env.timers.tick_intervals(10)  # 1 second
    assert math.isclose(game_env.earth["ecology_health"], 99.0, abs_tol=1e-6)


def test_no_generators_means_no_ecology_decay(game_env):
    game_env.timers.tick_intervals(20)
    assert game_env.earth["ecology_health"] == 100.0


def test_multiple_generators_decay_ecology_faster(game_env):
    game_env.earth["resource_count"] = 1000
    game_env.buy_generator()
    game_env.buy_generator()
    game_env.buy_generator()
    game_env.earth["resource_count"] = 0
    game_env.timers.tick_intervals(10)  # 1 second, 3 generators * 1%/s
    assert math.isclose(game_env.earth["ecology_health"], 97.0, abs_tol=1e-6)


def test_ecology_health_clamps_at_zero_and_does_not_go_negative(game_env):
    game_env.earth["resource_count"] = 10
    game_env.buy_generator()
    game_env.timers.tick_intervals(2000)  # far more than enough to bottom out
    assert game_env.earth["ecology_health"] == 0.0


# --- production penalty / halt applied to passive output -------------------

def test_generator_output_penalized_in_low_ecology_band(game_env):
    game_env.earth["generator_count"] = 1
    game_env.earth["ecology_health"] = 5.0  # in the 0.75x penalty band
    game_env.earth["resource_count"] = 0
    game_env.module.tick()
    # 1 generator * 1 iron/s * 0.1s * 0.75 penalty
    assert math.isclose(game_env.earth["resource_count"], 0.075, abs_tol=1e-9)


def test_generator_output_halted_at_zero_ecology(game_env):
    game_env.earth["generator_count"] = 1
    game_env.earth["ecology_health"] = 0.0
    game_env.earth["resource_count"] = 0
    game_env.module.tick()
    assert game_env.earth["resource_count"] == 0


def test_generator_output_full_rate_above_threshold(game_env):
    game_env.earth["generator_count"] = 1
    game_env.earth["ecology_health"] = 100.0
    game_env.earth["resource_count"] = 0
    game_env.module.tick()
    assert math.isclose(game_env.earth["resource_count"], 0.1, abs_tol=1e-9)


def test_manual_click_is_never_penalized_by_low_ecology(game_env):
    # Deliberate design choice: automated production is gated by ecology
    # health, but manual clicking always works so the player is never
    # permanently stuck (see comment above _mine in game.py).
    game_env.earth["ecology_health"] = 5.0
    game_env.click()
    assert game_env.earth["resource_count"] == 1


def test_manual_click_is_never_halted_at_zero_ecology(game_env):
    game_env.earth["ecology_health"] = 0.0
    game_env.click()
    assert game_env.earth["resource_count"] == 1


# --- ecology-status text -----------------------------------------------

def test_status_message_at_critical_band(game_env):
    game_env.earth["ecology_health"] = 5.0
    game_env.module.update_ecology_display("Earth")
    assert "reduced 25%" in game_env.elements["ecology-status"].innerText


def test_status_message_at_collapse(game_env):
    game_env.earth["ecology_health"] = 0.0
    game_env.module.update_ecology_display("Earth")
    assert "halted" in game_env.elements["ecology-status"].innerText


def test_status_message_clears_once_recovered(game_env):
    game_env.earth["ecology_health"] = 0.0
    game_env.module.update_ecology_display("Earth")
    assert game_env.elements["ecology-status"].innerText != ""

    game_env.earth["ecology_health"] = 50.0
    game_env.module.update_ecology_display("Earth")
    assert game_env.elements["ecology-status"].innerText == ""


# --- ecology-percent / bar display formatting -------------------------

def test_ecology_percent_rounds_to_nearest_integer(game_env):
    game_env.earth["ecology_health"] = 62.6
    game_env.module.update_ecology_display("Earth")
    assert game_env.elements["ecology-percent"].innerText == "63%"


def test_ecology_bar_width_tracks_raw_health(game_env):
    game_env.earth["ecology_health"] = 42.5
    game_env.module.update_ecology_display("Earth")
    assert game_env.elements["ecology-bar"].style.width == "42.5%"


# --- Recycler purchases -----------------------------------------------

def test_cannot_afford_recycler_does_nothing(game_env):
    game_env.buy_recycler()
    assert game_env.earth["recycler_count"] == 0
    assert game_env.earth["resource_count"] == 0


def test_buying_recycler_deducts_cost_and_increments_count(game_env):
    game_env.earth["resource_count"] = 15
    game_env.buy_recycler()
    assert game_env.earth["recycler_count"] == 1
    assert game_env.earth["resource_count"] == 0


def test_buying_recycler_updates_rate_display(game_env):
    game_env.earth["resource_count"] = 15
    game_env.buy_recycler()
    assert game_env.elements["recycler-count"].innerText == "1"
    assert game_env.elements["recycler-rate"].innerText == "2.0"


def test_recycler_cost_increases_after_purchase(game_env):
    first_cost = game_env.module.recycler_cost("Earth")
    game_env.earth["resource_count"] = first_cost
    game_env.buy_recycler()
    second_cost = game_env.module.recycler_cost("Earth")
    assert second_cost > first_cost


def test_recycler_button_label_reflects_next_cost(game_env):
    game_env.earth["resource_count"] = 15
    game_env.buy_recycler()
    button = game_env.elements["buy-recycler-button"]
    expected_cost = game_env.module.recycler_cost("Earth")
    assert str(expected_cost) in button.innerText


def test_recycler_button_gives_press_feedback_even_when_unaffordable(game_env):
    button = game_env.elements["buy-recycler-button"]
    game_env.buy_recycler()
    assert button.classList.contains("pressed")
    game_env.timers.flush()
    assert not button.classList.contains("pressed")


# --- ecology restoration from Recyclers ---------------------------------

def test_recycler_restores_ecology_over_ticks(game_env):
    game_env.earth["ecology_health"] = 50.0
    game_env.earth["resource_count"] = 15
    game_env.buy_recycler()  # 1 recycler, restore 2%/s
    game_env.timers.tick_intervals(10)  # 1 second
    assert math.isclose(game_env.earth["ecology_health"], 52.0, abs_tol=1e-6)


def test_recycler_restore_clamps_at_full_health(game_env):
    game_env.earth["resource_count"] = 15
    game_env.buy_recycler()
    game_env.timers.tick_intervals(1000)  # far more than needed to hit 100%
    assert game_env.earth["ecology_health"] == 100.0


def test_recyclers_and_generators_net_out_correctly(game_env):
    # 2 generators decay at 2%/s, 1 recycler restores at 2%/s -> net -0%/s...
    # net decay of 0, health should hold steady.
    game_env.earth["resource_count"] = 1000
    game_env.buy_generator()
    game_env.buy_generator()
    game_env.buy_recycler()
    game_env.earth["ecology_health"] = 80.0
    game_env.timers.tick_intervals(50)  # 5 seconds
    assert math.isclose(game_env.earth["ecology_health"], 80.0, abs_tol=1e-6)


def test_recycler_alone_can_recover_from_total_collapse(game_env):
    game_env.earth["ecology_health"] = 0.0
    game_env.earth["resource_count"] = 15
    game_env.buy_recycler()
    game_env.timers.tick_intervals(10)  # 1 second at 2%/s restore
    assert math.isclose(game_env.earth["ecology_health"], 2.0, abs_tol=1e-6)


# --- end-to-end recoverability (no dead-end states) -----------------------

def test_full_collapse_and_recovery_is_never_a_dead_end(game_env):
    """Simulates a player who over-built generators, crashed ecology to 0%,
    and had no Iron banked — verifies they can still claw back via manual
    clicking, per the project's "no dead-end/unwinnable states" rule."""
    game_env.earth["ecology_health"] = 0.0
    game_env.earth["resource_count"] = 0
    game_env.earth["generator_count"] = 1  # would otherwise produce 0 (halted)

    # Passive production is halted...
    game_env.timers.tick_intervals(5)
    assert game_env.earth["resource_count"] == 0

    # ...but manual clicking still earns Iron toward a recovery Recycler.
    for _ in range(15):
        game_env.click()
    assert game_env.earth["resource_count"] == 15

    game_env.buy_recycler()
    assert game_env.earth["recycler_count"] == 1
    assert game_env.earth["resource_count"] == 0

    # 1 recycler (2%/s restore) outpaces 1 generator (1%/s decay), so
    # ecology now climbs back out of collapse.
    game_env.timers.tick_intervals(10)  # 1 second
    assert game_env.earth["ecology_health"] > 0.0


def test_being_outpaced_by_generators_is_still_not_a_dead_end(game_env):
    """A single Recycler can't out-restore 5 generators (2%/s vs 5%/s), so
    health stays pinned at 0% — but that's escalating tension, not a
    dead end: the player can always click for Iron to buy more Recyclers."""
    game_env.earth["ecology_health"] = 0.0
    game_env.earth["resource_count"] = 15
    game_env.earth["generator_count"] = 5
    game_env.buy_recycler()  # 1 recycler: restore 2%/s vs decay 5%/s

    game_env.timers.tick_intervals(10)  # 1 second
    assert game_env.earth["ecology_health"] == 0.0  # net negative, still stuck

    # Manual clicking remains available regardless, funding more Recyclers...
    for _ in range(200):
        game_env.click()
    while game_env.earth["resource_count"] >= game_env.module.recycler_cost("Earth"):
        game_env.buy_recycler()
    assert game_env.earth["recycler_count"] >= 3  # enough to outpace 5%/s decay

    game_env.timers.tick_intervals(10)  # 1 second
    assert game_env.earth["ecology_health"] > 0.0
