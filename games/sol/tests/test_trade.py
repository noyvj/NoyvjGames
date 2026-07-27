"""Tests for the Milestone 7 trade system v1: a passive Trade Route
building (reusing the Milestone 2 continuous-rate building pattern) that
ships ecology restoration to the *other* planet — directly implementing the
ecology system's own spec line, "recoverable by shipping in materials from
an already-stabilized planet." Deliberately weaker than a local Recycler
(0.5%/s vs 2.0%/s): a supplementary lever, not a replacement.

Milestone 9f made the destination itself player-selectable (previously it
always resolved to the first other real planet, e.g. always Earth for
every non-Earth planet once the roster grew past two) via a "Change
Destination" button that cycles through every other real economy. See the
"player-selectable trade destination" section below."""

import math


def _unlock_near_bodies(game_env):
    game_env.module.unlocked_bodies.update(["Moon", "Mars"])
    game_env.module.update_travel_display()


# --- setup / initial state ----------------------------------------------

def test_earth_trade_section_hidden_before_unlock(game_env):
    assert game_env.elements["earth-trade"].hidden is True


def test_earth_trade_section_visible_once_unlocked(game_env):
    _unlock_near_bodies(game_env)
    assert game_env.elements["earth-trade"].hidden is False


def test_mars_trade_section_always_visible(game_env):
    # Reaching #mars-view at all already implies near_bodies_unlocked, so
    # unlike Earth's trade widget, Mars's own doesn't need extra gating.
    assert game_env.elements["mars-trade-route-count"] is not None


def test_initial_trade_route_state(game_env):
    assert game_env.earth["trade_routes"].get("Mars", 0) == 0
    assert game_env.mars["trade_routes"].get("Earth", 0) == 0
    assert game_env.elements["trade-route-count"].innerText == "0"
    assert game_env.elements["trade-route-rate"].innerText == "0.0"


def test_trade_route_button_configured(game_env):
    button = game_env.elements["buy-trade-route-button"]
    assert button.disabled is False
    assert "30 Iron" in button.innerText


def test_mars_trade_route_button_configured(game_env):
    button = game_env.elements["mars-buy-trade-route-button"]
    assert button.disabled is False
    assert "30 Water Ice" in button.innerText


def test_trade_route_destination_labels(game_env):
    assert game_env.elements["trade-route-destination"].innerText == "Mars"
    assert game_env.elements["mars-trade-route-destination"].innerText == "Earth"


# --- buying Trade Routes -------------------------------------------------

def test_cannot_afford_trade_route_does_nothing(game_env):
    game_env.buy_trade_route()
    assert game_env.earth["trade_routes"].get("Mars", 0) == 0
    assert game_env.earth["resource_count"] == 0


def test_buying_trade_route_deducts_cost_and_increments(game_env):
    game_env.earth["resource_count"] = 30
    game_env.buy_trade_route()
    assert game_env.earth["trade_routes"].get("Mars", 0) == 1
    assert game_env.earth["resource_count"] == 0


def test_trade_route_cost_increases_after_purchase(game_env):
    first_cost = game_env.module.trade_route_cost("Earth", "Mars")
    game_env.earth["resource_count"] = first_cost
    game_env.buy_trade_route()
    second_cost = game_env.module.trade_route_cost("Earth", "Mars")
    assert second_cost > first_cost


def test_trade_route_display_updates_after_purchase(game_env):
    game_env.earth["resource_count"] = 30
    game_env.buy_trade_route()
    assert game_env.elements["trade-route-count"].innerText == "1"
    assert game_env.elements["trade-route-rate"].innerText == "0.5"


def test_trade_route_button_gives_press_feedback_even_when_unaffordable(game_env):
    button = game_env.elements["buy-trade-route-button"]
    game_env.buy_trade_route()
    assert button.classList.contains("pressed")
    game_env.timers.flush()
    assert not button.classList.contains("pressed")


def test_mars_trade_route_purchase_independent_of_earth(game_env):
    game_env.mars["resource_count"] = 30
    game_env.buy_trade_route("Mars")
    assert game_env.mars["trade_routes"].get("Earth", 0) == 1
    assert game_env.earth["trade_routes"].get("Mars", 0) == 0


# --- cross-planet ecology restoration -------------------------------------

def test_earth_trade_route_restores_mars_ecology(game_env):
    game_env.earth["resource_count"] = 30
    game_env.buy_trade_route()  # ships to Mars
    game_env.mars["ecology_health"] = 50.0
    game_env.timers.tick_intervals(10)  # 1 second at 0.5%/s
    assert math.isclose(game_env.mars["ecology_health"], 50.5, abs_tol=1e-6)


def test_mars_trade_route_restores_earth_ecology(game_env):
    game_env.mars["resource_count"] = 30
    game_env.buy_trade_route("Mars")  # ships to Earth
    game_env.earth["ecology_health"] = 50.0
    game_env.timers.tick_intervals(10)  # 1 second at 0.5%/s
    assert math.isclose(game_env.earth["ecology_health"], 50.5, abs_tol=1e-6)


def test_trade_route_does_not_restore_the_sending_planets_own_ecology(game_env):
    game_env.earth["resource_count"] = 30
    game_env.buy_trade_route()  # Earth ships to Mars
    game_env.earth["ecology_health"] = 50.0
    game_env.timers.tick_intervals(10)
    # Earth's own ecology only changes from its own decay/restore, never
    # from a Trade Route it built (the restoration lands on Mars instead).
    assert game_env.earth["ecology_health"] == 50.0


def test_multiple_trade_routes_scale_restoration_linearly(game_env):
    game_env.earth["resource_count"] = 1000
    game_env.buy_trade_route()
    game_env.buy_trade_route()
    game_env.buy_trade_route()
    assert game_env.earth["trade_routes"].get("Mars", 0) == 3

    game_env.mars["ecology_health"] = 50.0
    game_env.timers.tick_intervals(10)  # 1 second, 3 routes * 0.5%/s
    assert math.isclose(game_env.mars["ecology_health"], 51.5, abs_tol=1e-6)


def test_trade_route_restoration_clamps_at_full_health(game_env):
    game_env.earth["resource_count"] = 30
    game_env.buy_trade_route()
    game_env.mars["ecology_health"] = 100.0
    game_env.timers.tick_intervals(100)
    assert game_env.mars["ecology_health"] == 100.0


def test_both_planets_can_ship_to_each_other_simultaneously(game_env):
    game_env.earth["resource_count"] = 30
    game_env.mars["resource_count"] = 30
    game_env.buy_trade_route("Earth")
    game_env.buy_trade_route("Mars")

    game_env.earth["ecology_health"] = 50.0
    game_env.mars["ecology_health"] = 50.0
    game_env.timers.tick_intervals(10)  # 1 second each direction
    assert math.isclose(game_env.earth["ecology_health"], 50.5, abs_tol=1e-6)
    assert math.isclose(game_env.mars["ecology_health"], 50.5, abs_tol=1e-6)


def test_trade_route_weaker_than_local_recycler(game_env):
    # Per design: cross-planet aid is a supplementary lever, not a
    # replacement for local investment.
    assert game_env.module.TRADE_ROUTE_RESTORE_PER_SEC < 2.0  # Recycler's rate


# --- interplay with existing decay/production -----------------------------

def test_trade_route_restoration_combines_with_local_decay(game_env):
    # Mars has 1 generator decaying at 1%/s, and receives 0.5%/s from
    # Earth's Trade Route — net should be -0.5%/s.
    game_env.mars["generator_count"] = 1
    game_env.mars["ecology_health"] = 80.0
    game_env.earth["resource_count"] = 30
    game_env.buy_trade_route()  # ships to Mars
    game_env.timers.tick_intervals(20)  # 2 seconds: -2% decay, +1% trade
    assert math.isclose(game_env.mars["ecology_health"], 79.0, abs_tol=1e-6)


def test_trade_route_can_fully_offset_a_single_generators_decay(game_env):
    # 2 Trade Routes (1.0%/s) exactly offset 1 generator's decay (1.0%/s).
    game_env.mars["generator_count"] = 1
    game_env.mars["ecology_health"] = 50.0
    game_env.earth["resource_count"] = 1000
    game_env.buy_trade_route()
    game_env.buy_trade_route()
    game_env.timers.tick_intervals(50)  # 5 seconds
    assert math.isclose(game_env.mars["ecology_health"], 50.0, abs_tol=1e-6)


# --- no dead-end: trade as an additional recovery lever -------------------

def test_trade_route_alone_can_recover_a_planet_with_no_local_recyclers(game_env):
    """A planet in full ecological collapse, with no local Recyclers built
    and no Iron of its own, can still be nursed back by the other planet's
    Trade Route — reinforcing the "always recoverable" balance rule via a
    second independent lever, not just local Recyclers."""
    game_env.mars["ecology_health"] = 0.0
    game_env.mars["resource_count"] = 0
    game_env.mars["generator_count"] = 0  # nothing decaying it further

    game_env.earth["resource_count"] = 30
    game_env.buy_trade_route()  # Earth ships aid to Mars

    game_env.timers.tick_intervals(10)  # 1 second at 0.5%/s
    assert game_env.mars["ecology_health"] > 0.0


# --- Milestone 9f: player-selectable trade destination ---------------------

def test_cycle_destination_button_configured(game_env):
    button = game_env.elements["cycle-trade-destination-button"]
    assert button.disabled is False
    assert button.innerText == "Change Destination"


def test_cycling_destination_changes_the_displayed_destination(game_env):
    assert game_env.elements["trade-route-destination"].innerText == "Mars"
    game_env.cycle_trade_destination()  # Earth
    assert game_env.elements["trade-route-destination"].innerText != "Mars"


def test_cycling_destination_shows_a_clean_display_name_for_asteroid_belt(game_env):
    # "AsteroidBelt" is the internal PLANETS key (no space, for DOM-id
    # safety) — the destination display must show the human-readable
    # "Asteroid Belt" instead, not the raw internal key.
    for _ in range(len(game_env.module.other_real_planets("Earth"))):
        game_env.cycle_trade_destination()
        if game_env.module.current_trade_destination("Earth") == "AsteroidBelt":
            break
    assert game_env.module.current_trade_destination("Earth") == "AsteroidBelt"
    assert game_env.elements["trade-route-destination"].innerText == "Asteroid Belt"


def test_cycling_destination_visits_every_other_real_planet_exactly_once(game_env):
    # 6 real economies now means Earth has 5 "others" — cycling 5 times
    # should visit each exactly once and the 6th cycle should wrap back to
    # the start.
    others = game_env.module.other_real_planets("Earth")
    seen = [game_env.module.current_trade_destination("Earth")]
    for _ in range(len(others)):
        game_env.cycle_trade_destination()
        seen.append(game_env.module.current_trade_destination("Earth"))
    assert seen == [others[0]] + others[1:] + [others[0]]
    assert set(seen[:-1]) == set(others)


def test_cycling_destination_is_independent_per_planet(game_env):
    game_env.cycle_trade_destination("Earth")
    earth_destination = game_env.module.current_trade_destination("Earth")
    mars_destination = game_env.module.current_trade_destination("Mars")
    assert mars_destination == "Earth"  # Mars untouched by Earth's cycle
    assert earth_destination != "Mars"  # Earth's cycle actually moved off the default


def test_buying_trade_route_targets_the_currently_selected_destination(game_env):
    game_env.cycle_trade_destination()  # Earth: Mars -> next real planet
    destination = game_env.module.current_trade_destination("Earth")
    game_env.earth["resource_count"] = 30
    game_env.buy_trade_route()
    assert game_env.earth["trade_routes"].get(destination, 0) == 1
    assert game_env.earth["trade_routes"].get("Mars", 0) == 0


def test_route_counts_are_kept_separately_per_destination(game_env):
    # Building toward one destination, cycling away, and building toward a
    # second destination must not merge or clobber the first destination's
    # count — each is its own bucket in trade_routes.
    game_env.earth["resource_count"] = 1000
    game_env.buy_trade_route()  # 1 route to Mars (the default)
    game_env.cycle_trade_destination()
    second_destination = game_env.module.current_trade_destination("Earth")
    game_env.buy_trade_route()  # 1 route to the new destination
    assert game_env.earth["trade_routes"].get("Mars", 0) == 1
    assert game_env.earth["trade_routes"].get(second_destination, 0) == 1


def test_switching_back_to_a_destination_keeps_its_earlier_route_count(game_env):
    game_env.earth["resource_count"] = 1000
    game_env.buy_trade_route()  # 1 route to Mars
    game_env.cycle_trade_destination()  # move off Mars
    others = game_env.module.other_real_planets("Earth")
    # Cycle all the way back around to Mars.
    for _ in range(len(others) - 1):
        game_env.cycle_trade_destination()
    assert game_env.module.current_trade_destination("Earth") == "Mars"
    assert game_env.elements["trade-route-count"].innerText == "1"


def test_cycle_destination_button_gives_press_feedback(game_env):
    button = game_env.elements["cycle-trade-destination-button"]
    game_env.cycle_trade_destination()
    assert button.classList.contains("pressed")
    game_env.timers.flush()
    assert not button.classList.contains("pressed")


def test_mars_cycle_destination_button_wired(game_env):
    button = game_env.elements["mars-cycle-trade-destination-button"]
    assert "click" in button._listeners
    assert len(button._listeners["click"]) == 1
