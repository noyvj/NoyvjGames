"""Tests for Milestone 9a: the research tier 2 framework. Covers the five
new Far Bodies travel destinations (Venus, Asteroid Belt, Pluto, Jupiter's
Moons, Saturn's Moons — all still undeveloped placeholders, reusing the
shared #away-view), and the generalization of governor/trade beyond the
former hardcoded 2-planet assumption.

Moon and Mars's own tier-1 behavior is covered in test_research.py and
test_travel_governor.py; this file is specifically about what's new here."""

import math


def _complete_tier(game_env, index):
    for i in range(index + 1):
        target = game_env.module.RESEARCH_TIERS[i]["target"]
        game_env.earth["resource_count"] = target
        clicks = target // game_env.module.RESEARCH_FUND_COST
        for _ in range(clicks):
            game_env.fund_research()


FAR_BODIES = ["Venus", "AsteroidBelt", "Pluto", "JupiterMoons", "SaturnMoons"]


# --- Far Bodies travel gating ---------------------------------------------

def test_far_body_buttons_hidden_before_tier_2(game_env):
    for body in FAR_BODIES:
        button_id = game_env.module.TRAVEL_BUTTON_ID[body]
        button = game_env.elements[button_id]
        assert button.hidden is True
        assert button.disabled is True


def test_far_bodies_still_locked_after_only_tier_1(game_env):
    _complete_tier(game_env, 0)
    for body in FAR_BODIES:
        assert body not in game_env.module.unlocked_bodies
        button = game_env.elements[game_env.module.TRAVEL_BUTTON_ID[body]]
        assert button.hidden is True


def test_far_body_buttons_appear_after_tier_2(game_env):
    _complete_tier(game_env, 1)
    for body in FAR_BODIES:
        button = game_env.elements[game_env.module.TRAVEL_BUTTON_ID[body]]
        assert button.hidden is False
        assert button.disabled is False


def test_near_bodies_stay_unlocked_after_tier_2_completes_too(game_env):
    _complete_tier(game_env, 1)
    assert "Moon" in game_env.module.unlocked_bodies
    assert "Mars" in game_env.module.unlocked_bodies


# --- traveling to each Far Body (shared away-view placeholder) ------------

def test_traveling_to_venus_before_unlock_does_nothing(game_env):
    game_env.travel_to("Venus")
    assert game_env.module.current_planet == "Earth"


def test_traveling_to_each_far_body_shows_away_view(game_env):
    _complete_tier(game_env, 1)
    for body in FAR_BODIES:
        game_env.travel_to(body)
        assert game_env.module.current_planet == body
        assert game_env.elements["away-view"].hidden is False
        assert game_env.elements["earth-view"].hidden is True
        assert game_env.elements["mars-view"].hidden is True
        game_env.return_to_earth()


def test_away_view_heading_shows_correct_display_name_per_body(game_env):
    _complete_tier(game_env, 1)
    expected = {
        "Venus": "VENUS",
        "AsteroidBelt": "ASTEROID BELT",
        "Pluto": "PLUTO",
        "JupiterMoons": "JUPITER'S MOONS",
        "SaturnMoons": "SATURN'S MOONS",
    }
    for body, heading in expected.items():
        game_env.travel_to(body)
        assert game_env.elements["away-planet-name"].innerText == heading
        game_env.return_to_earth()


def test_far_body_travel_buttons_give_press_feedback(game_env):
    _complete_tier(game_env, 1)
    button = game_env.elements["travel-venus-button"]
    game_env.travel_to("Venus")
    assert button.classList.contains("pressed")


# --- away-view now shows BOTH real economies (fixes the Milestone 6 gap) --

def test_away_view_shows_all_three_real_economy_summaries(game_env):
    # Since Moon (Milestone 9b) is now a real economy too, the shared
    # placeholder used by the remaining undeveloped bodies shows all three,
    # not just the original Earth+Mars pair from Milestone 9a.
    _complete_tier(game_env, 1)
    game_env.earth["resource_count"] = 12
    game_env.mars["resource_count"] = 34
    game_env.moon["resource_count"] = 56
    game_env.travel_to("Pluto")
    assert game_env.elements["away-earth-resource"].innerText == "12"
    assert game_env.elements["away-mars-resource"].innerText == "34"
    assert game_env.elements["away-moon-resource"].innerText == "56"


def test_away_view_all_three_summaries_refresh_live_on_tick(game_env):
    _complete_tier(game_env, 1)
    game_env.earth["generator_count"] = 1
    game_env.mars["generator_count"] = 1
    game_env.moon["generator_count"] = 1
    game_env.earth["resource_count"] = 0
    game_env.mars["resource_count"] = 0
    game_env.moon["resource_count"] = 0
    game_env.travel_to("Venus")
    game_env.timers.tick_intervals(10)  # 1 second each
    assert game_env.elements["away-earth-resource"].innerText == "1"
    assert game_env.elements["away-mars-resource"].innerText == "1"
    assert game_env.elements["away-moon-resource"].innerText == "1"


# --- governor generalization (already-generic loop, proven explicitly) ---

def test_governor_governs_both_earth_and_mars_from_any_far_body(game_env):
    _complete_tier(game_env, 1)
    game_env.set_priority("growth")
    game_env.earth["resource_count"] = 10000
    game_env.mars["resource_count"] = 10000
    game_env.travel_to("SaturnMoons")
    game_env.timers.tick_intervals(50)
    assert game_env.earth["generator_count"] > 0
    assert game_env.mars["generator_count"] > 0


def test_governor_governs_all_three_real_economies_from_any_far_body(game_env):
    # Now that Moon is a third real economy, the governor's genericity
    # actually gets exercised with N=3, not just N=2.
    _complete_tier(game_env, 1)
    game_env.set_priority("growth")
    game_env.earth["resource_count"] = 10000
    game_env.mars["resource_count"] = 10000
    game_env.moon["resource_count"] = 10000
    game_env.travel_to("JupiterMoons")
    game_env.timers.tick_intervals(50)
    assert game_env.earth["generator_count"] > 0
    assert game_env.mars["generator_count"] > 0
    assert game_env.moon["generator_count"] > 0


# --- trade generalization: destination computed, not hardcoded ------------

def test_other_real_planets_is_computed_not_hardcoded(game_env):
    # Moon became a third real economy in Milestone 9b, so Earth and Mars
    # now each have two "other" real planets rather than exactly one —
    # proving this was never a hardcoded pair.
    assert set(game_env.module.other_real_planets("Earth")) == {"Mars", "Moon"}
    assert set(game_env.module.other_real_planets("Mars")) == {"Earth", "Moon"}
    assert set(game_env.module.other_real_planets("Moon")) == {"Earth", "Mars"}


def test_primary_trade_destination_matches_other_real_planets(game_env):
    # Simplest deterministic choice for now (first in PLANETS insertion
    # order) — a real multi-destination selector is deferred until a
    # milestone actually needs to make that UX decision.
    assert game_env.module.primary_trade_destination("Earth") == "Mars"
    assert game_env.module.primary_trade_destination("Mars") == "Earth"
    assert game_env.module.primary_trade_destination("Moon") == "Earth"


def test_trade_routes_are_stored_per_destination(game_env):
    game_env.earth["resource_count"] = 30
    game_env.buy_trade_route()
    assert game_env.earth["trade_routes"] == {"Mars": 1}


def test_incoming_trade_restore_sums_all_senders_targeting_a_planet(game_env):
    # Even though only one sender exists today, the helper itself sums
    # over every planet whose trade_routes target the given planet —
    # verified directly rather than only through the 2-planet happy path.
    game_env.mars["trade_routes"]["Earth"] = 2
    restore = game_env.module._incoming_trade_restore("Earth")
    expected = 2 * game_env.module.TRADE_ROUTE_RESTORE_PER_SEC * (game_env.module.TICK_INTERVAL_MS / 1000)
    assert math.isclose(restore, expected, abs_tol=1e-9)


def test_incoming_trade_restore_ignores_self(game_env):
    game_env.earth["trade_routes"]["Mars"] = 5  # Earth's own outgoing routes
    assert game_env.module._incoming_trade_restore("Earth") == 0.0


# --- generic cross-summary widget system (replaces the old hardcoded pair) -

def test_update_cross_summary_writes_viewer_prefixed_ids(game_env):
    game_env.mars["resource_count"] = 7
    game_env.mars["generator_count"] = 2
    game_env.module.update_cross_summary("Earth", "Mars")
    assert game_env.elements["mars-summary-resource"].innerText == "7"
    assert game_env.elements["mars-summary-generators"].innerText == "2"


def test_update_cross_summary_does_not_collide_between_viewers(game_env):
    # Mars's view and Moon's view both need an "Earth (governed)" widget —
    # this only works if their ids don't collide.
    game_env.earth["resource_count"] = 9
    game_env.module.update_cross_summary("Mars", "Earth")
    game_env.module.update_cross_summary("Moon", "Earth")
    assert game_env.elements["mars-earth-summary-resource"].innerText == "9"
    assert game_env.elements["moon-earth-summary-resource"].innerText == "9"


def test_update_all_cross_summaries_covers_every_ordered_pair(game_env):
    game_env.earth["resource_count"] = 1
    game_env.mars["resource_count"] = 2
    game_env.moon["resource_count"] = 3
    game_env.module.update_all_cross_summaries()

    assert game_env.elements["mars-summary-resource"].innerText == "2"  # Earth's view of Mars
    assert game_env.elements["moon-summary-resource"].innerText == "3"  # Earth's view of Moon
    assert game_env.elements["mars-earth-summary-resource"].innerText == "1"  # Mars's view of Earth
    assert game_env.elements["mars-moon-summary-resource"].innerText == "3"  # Mars's view of Moon
    assert game_env.elements["moon-earth-summary-resource"].innerText == "1"  # Moon's view of Earth
    assert game_env.elements["moon-mars-summary-resource"].innerText == "2"  # Moon's view of Mars
