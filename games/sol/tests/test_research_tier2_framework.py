"""Tests for Milestone 9a: the research tier 2 framework. Covers the five
Far Bodies travel destinations unlocked by tier 2 (Venus, Asteroid Belt,
Pluto, Jupiter's Moons, Saturn's Moons), and the generalization of
governor/trade beyond the former hardcoded 2-planet assumption.

Venus (9c), the Asteroid Belt (9d), Pluto (9e), and Jupiter's Moons (9f)
got their own real economies (see test_venus_economy.py /
test_asteroid_belt_economy.py / test_pluto_economy.py /
test_jupiter_moons_economy.py) and no longer use the shared #away-view
placeholder — only Saturn's Moons still does, until its own milestone
(9g) lands.

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


# All five bodies tier 2 unlocks for travel (used for gating tests, which
# apply uniformly regardless of whether a body has its own economy yet).
FAR_BODIES = ["Venus", "AsteroidBelt", "Pluto", "JupiterMoons", "SaturnMoons"]

# Of those, the ones still using the shared away-view placeholder.
STILL_UNDEVELOPED_FAR_BODIES = ["SaturnMoons"]


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


def test_traveling_to_each_still_undeveloped_body_shows_away_view(game_env):
    _complete_tier(game_env, 1)
    for body in STILL_UNDEVELOPED_FAR_BODIES:
        game_env.travel_to(body)
        assert game_env.module.current_planet == body
        assert game_env.elements["away-view"].hidden is False
        assert game_env.elements["earth-view"].hidden is True
        assert game_env.elements["mars-view"].hidden is True
        game_env.return_to_earth()


def test_away_view_heading_shows_correct_display_name_per_body(game_env):
    _complete_tier(game_env, 1)
    expected = {
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

def test_away_view_shows_all_seven_real_economy_summaries(game_env):
    # Moon (9b), Venus (9c), the Asteroid Belt (9d), Pluto (9e), and
    # Jupiter's Moons (9f) are now real economies too, so the shared
    # placeholder used by the remaining undeveloped body shows all seven,
    # not just the original Earth+Mars pair from Milestone 9a.
    _complete_tier(game_env, 1)
    game_env.earth["resource_count"] = 12
    game_env.mars["resource_count"] = 34
    game_env.moon["resource_count"] = 56
    game_env.venus["resource_count"] = 78
    game_env.asteroid_belt["resource_count"] = 90
    game_env.pluto["resource_count"] = 11
    game_env.jupiter_moons["resource_count"] = 22
    game_env.travel_to("SaturnMoons")
    assert game_env.elements["away-earth-resource"].innerText == "12"
    assert game_env.elements["away-mars-resource"].innerText == "34"
    assert game_env.elements["away-moon-resource"].innerText == "56"
    assert game_env.elements["away-venus-resource"].innerText == "78"
    assert game_env.elements["away-asteroidbelt-resource"].innerText == "90"
    assert game_env.elements["away-pluto-resource"].innerText == "11"
    assert game_env.elements["away-jupitermoons-resource"].innerText == "22"


def test_away_view_all_seven_summaries_refresh_live_on_tick(game_env):
    _complete_tier(game_env, 1)
    game_env.earth["generator_count"] = 1
    game_env.mars["generator_count"] = 1
    game_env.moon["generator_count"] = 1
    game_env.venus["generator_count"] = 1
    game_env.asteroid_belt["generator_count"] = 1
    game_env.pluto["generator_count"] = 1
    game_env.jupiter_moons["generator_count"] = 1
    game_env.earth["resource_count"] = 0
    game_env.mars["resource_count"] = 0
    game_env.moon["resource_count"] = 0
    game_env.venus["resource_count"] = 0
    game_env.asteroid_belt["resource_count"] = 0
    game_env.pluto["resource_count"] = 0
    game_env.jupiter_moons["resource_count"] = 0
    game_env.travel_to("SaturnMoons")  # the only remaining undeveloped body
    game_env.timers.tick_intervals(10)  # 1 second each
    assert game_env.elements["away-earth-resource"].innerText == "1"
    assert game_env.elements["away-mars-resource"].innerText == "1"
    assert game_env.elements["away-moon-resource"].innerText == "1"
    assert game_env.elements["away-venus-resource"].innerText == "1"
    assert game_env.elements["away-asteroidbelt-resource"].innerText == "1"
    assert game_env.elements["away-pluto-resource"].innerText == "1"
    assert game_env.elements["away-jupitermoons-resource"].innerText == "1"


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


def test_governor_governs_all_seven_real_economies_from_any_far_body(game_env):
    # Now that Moon, Venus, the Asteroid Belt, Pluto, and Jupiter's Moons
    # are real economies too, the governor's genericity actually gets
    # exercised with N=7, not just N=2.
    _complete_tier(game_env, 1)
    game_env.set_priority("growth")
    game_env.earth["resource_count"] = 10000
    game_env.mars["resource_count"] = 10000
    game_env.moon["resource_count"] = 10000
    game_env.venus["resource_count"] = 10000
    game_env.asteroid_belt["resource_count"] = 10000
    game_env.pluto["resource_count"] = 10000
    game_env.jupiter_moons["resource_count"] = 10000
    game_env.travel_to("SaturnMoons")
    game_env.timers.tick_intervals(50)
    assert game_env.earth["generator_count"] > 0
    assert game_env.mars["generator_count"] > 0
    assert game_env.moon["generator_count"] > 0
    assert game_env.venus["generator_count"] > 0
    assert game_env.asteroid_belt["generator_count"] > 0
    assert game_env.pluto["generator_count"] > 0
    assert game_env.jupiter_moons["generator_count"] > 0


# --- trade generalization: destination computed, not hardcoded ------------

def test_other_real_planets_is_computed_not_hardcoded(game_env):
    # Moon (9b), Venus (9c), the Asteroid Belt (9d), Pluto (9e), and
    # Jupiter's Moons (9f) each added another real economy, so every planet
    # now has six "others" rather than exactly one — proving this was
    # never a hardcoded pair.
    assert set(game_env.module.other_real_planets("Earth")) == {
        "Mars", "Moon", "Venus", "AsteroidBelt", "Pluto", "JupiterMoons"
    }
    assert set(game_env.module.other_real_planets("Mars")) == {
        "Earth", "Moon", "Venus", "AsteroidBelt", "Pluto", "JupiterMoons"
    }
    assert set(game_env.module.other_real_planets("Moon")) == {
        "Earth", "Mars", "Venus", "AsteroidBelt", "Pluto", "JupiterMoons"
    }
    assert set(game_env.module.other_real_planets("Venus")) == {
        "Earth", "Mars", "Moon", "AsteroidBelt", "Pluto", "JupiterMoons"
    }
    assert set(game_env.module.other_real_planets("AsteroidBelt")) == {
        "Earth", "Mars", "Moon", "Venus", "Pluto", "JupiterMoons"
    }
    assert set(game_env.module.other_real_planets("Pluto")) == {
        "Earth", "Mars", "Moon", "Venus", "AsteroidBelt", "JupiterMoons"
    }
    assert set(game_env.module.other_real_planets("JupiterMoons")) == {
        "Earth", "Mars", "Moon", "Venus", "AsteroidBelt", "Pluto"
    }


def test_current_trade_destination_defaults_to_first_other_real_planet(game_env):
    # Milestone 9f made the destination player-selectable (see
    # test_trade.py for the cycling behavior itself), but the default for
    # anyone who hasn't cycled yet is still the first other real planet in
    # PLANETS insertion order, matching pre-9f behavior exactly.
    assert game_env.module.current_trade_destination("Earth") == "Mars"
    assert game_env.module.current_trade_destination("Mars") == "Earth"
    assert game_env.module.current_trade_destination("Moon") == "Earth"
    assert game_env.module.current_trade_destination("Venus") == "Earth"
    assert game_env.module.current_trade_destination("AsteroidBelt") == "Earth"
    assert game_env.module.current_trade_destination("Pluto") == "Earth"
    assert game_env.module.current_trade_destination("JupiterMoons") == "Earth"


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
    # N=7 real economies now (Earth, Mars, Moon, Venus, Asteroid Belt,
    # Pluto, Jupiter's Moons) means 42 ordered pairs total — checked
    # explicitly rather than trusting the loop.
    game_env.earth["resource_count"] = 1
    game_env.mars["resource_count"] = 2
    game_env.moon["resource_count"] = 3
    game_env.venus["resource_count"] = 4
    game_env.asteroid_belt["resource_count"] = 5
    game_env.pluto["resource_count"] = 6
    game_env.jupiter_moons["resource_count"] = 7
    game_env.module.update_all_cross_summaries()

    assert game_env.elements["mars-summary-resource"].innerText == "2"  # Earth's view of Mars
    assert game_env.elements["moon-summary-resource"].innerText == "3"  # Earth's view of Moon
    assert game_env.elements["venus-summary-resource"].innerText == "4"  # Earth's view of Venus
    assert game_env.elements["asteroidbelt-summary-resource"].innerText == "5"  # Earth's view of Asteroid Belt
    assert game_env.elements["pluto-summary-resource"].innerText == "6"  # Earth's view of Pluto
    assert game_env.elements["jupitermoons-summary-resource"].innerText == "7"  # Earth's view of Jupiter's Moons
    assert game_env.elements["mars-earth-summary-resource"].innerText == "1"  # Mars's view of Earth
    assert game_env.elements["mars-moon-summary-resource"].innerText == "3"  # Mars's view of Moon
    assert game_env.elements["mars-venus-summary-resource"].innerText == "4"  # Mars's view of Venus
    assert game_env.elements["mars-asteroidbelt-summary-resource"].innerText == "5"  # Mars's view of Asteroid Belt
    assert game_env.elements["mars-pluto-summary-resource"].innerText == "6"  # Mars's view of Pluto
    assert game_env.elements["mars-jupitermoons-summary-resource"].innerText == "7"  # Mars's view of Jupiter's Moons
    assert game_env.elements["moon-earth-summary-resource"].innerText == "1"  # Moon's view of Earth
    assert game_env.elements["moon-mars-summary-resource"].innerText == "2"  # Moon's view of Mars
    assert game_env.elements["moon-venus-summary-resource"].innerText == "4"  # Moon's view of Venus
    assert game_env.elements["moon-asteroidbelt-summary-resource"].innerText == "5"  # Moon's view of Asteroid Belt
    assert game_env.elements["moon-pluto-summary-resource"].innerText == "6"  # Moon's view of Pluto
    assert game_env.elements["moon-jupitermoons-summary-resource"].innerText == "7"  # Moon's view of Jupiter's Moons
    assert game_env.elements["venus-earth-summary-resource"].innerText == "1"  # Venus's view of Earth
    assert game_env.elements["venus-mars-summary-resource"].innerText == "2"  # Venus's view of Mars
    assert game_env.elements["venus-moon-summary-resource"].innerText == "3"  # Venus's view of Moon
    assert game_env.elements["venus-asteroidbelt-summary-resource"].innerText == "5"  # Venus's view of Asteroid Belt
    assert game_env.elements["venus-pluto-summary-resource"].innerText == "6"  # Venus's view of Pluto
    assert game_env.elements["venus-jupitermoons-summary-resource"].innerText == "7"  # Venus's view of Jupiter's Moons
    assert game_env.elements["asteroidbelt-earth-summary-resource"].innerText == "1"  # Asteroid Belt's view of Earth
    assert game_env.elements["asteroidbelt-mars-summary-resource"].innerText == "2"  # Asteroid Belt's view of Mars
    assert game_env.elements["asteroidbelt-moon-summary-resource"].innerText == "3"  # Asteroid Belt's view of Moon
    assert game_env.elements["asteroidbelt-venus-summary-resource"].innerText == "4"  # Asteroid Belt's view of Venus
    assert game_env.elements["asteroidbelt-pluto-summary-resource"].innerText == "6"  # Asteroid Belt's view of Pluto
    assert (
        game_env.elements["asteroidbelt-jupitermoons-summary-resource"].innerText == "7"
    )  # Asteroid Belt's view of Jupiter's Moons
    assert game_env.elements["pluto-earth-summary-resource"].innerText == "1"  # Pluto's view of Earth
    assert game_env.elements["pluto-mars-summary-resource"].innerText == "2"  # Pluto's view of Mars
    assert game_env.elements["pluto-moon-summary-resource"].innerText == "3"  # Pluto's view of Moon
    assert game_env.elements["pluto-venus-summary-resource"].innerText == "4"  # Pluto's view of Venus
    assert game_env.elements["pluto-asteroidbelt-summary-resource"].innerText == "5"  # Pluto's view of Asteroid Belt
    assert game_env.elements["pluto-jupitermoons-summary-resource"].innerText == "7"  # Pluto's view of Jupiter's Moons
    assert game_env.elements["jupitermoons-earth-summary-resource"].innerText == "1"  # Jupiter's Moons's view of Earth
    assert game_env.elements["jupitermoons-mars-summary-resource"].innerText == "2"  # Jupiter's Moons's view of Mars
    assert game_env.elements["jupitermoons-moon-summary-resource"].innerText == "3"  # Jupiter's Moons's view of Moon
    assert game_env.elements["jupitermoons-venus-summary-resource"].innerText == "4"  # Jupiter's Moons's view of Venus
    assert (
        game_env.elements["jupitermoons-asteroidbelt-summary-resource"].innerText == "5"
    )  # Jupiter's Moons's view of Asteroid Belt
    assert game_env.elements["jupitermoons-pluto-summary-resource"].innerText == "6"  # Jupiter's Moons's view of Pluto
