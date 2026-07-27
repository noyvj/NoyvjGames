"""Tests for the Milestone 5 planet transition + governor system: travel
between Earth and unlocked Near Bodies, and the priority/budget governor
that keeps managing whichever real economy the player is currently not on.

Mars (Milestone 6), Moon (Milestone 9b), Venus (Milestone 9c), the
Asteroid Belt (Milestone 9d), Pluto (Milestone 9e), Jupiter's Moons
(Milestone 9f), and Saturn's Moons (Milestone 9g) each have their own real
economy and dedicated view (#mars-view, #moon-view, #venus-view,
#asteroidbelt-view, #pluto-view, #jupitermoons-view, #saturnmoons-view),
each with cross-summary widgets for every OTHER real economy — their own
click/building/ecology loops are covered in test_mars_economy.py /
test_moon_economy.py / test_venus_economy.py /
test_asteroid_belt_economy.py / test_pluto_economy.py /
test_jupiter_moons_economy.py / test_saturn_moons_economy.py. Every Far
Body now has its own economy, so the generic #away-view placeholder (see
test_research_tier2_framework.py) is no longer reachable through travel.
This file covers travel/view-switching and the governor's cross-planet
behavior."""


def _unlock_near_bodies(game_env):
    game_env.module.unlocked_bodies.update(["Moon", "Mars"])
    game_env.module.update_travel_display()
    # Cross-summary widgets' hidden state is toggled by update_cross_summary()
    # itself (not update_travel_display()), matching the real on_fund_research()
    # code path which calls both when a tier completes.
    game_env.module.update_all_cross_summaries()


# --- initial state -----------------------------------------------------

def test_starts_on_earth(game_env):
    assert game_env.module.current_planet == "Earth"


def test_earth_view_visible_by_default(game_env):
    assert game_env.elements["earth-view"].hidden is False
    assert game_env.elements["mars-view"].hidden is True
    assert game_env.elements["away-view"].hidden is True


def test_travel_buttons_hidden_before_unlock(game_env):
    moon = game_env.elements["travel-moon-button"]
    mars = game_env.elements["travel-mars-button"]
    assert moon.hidden is True
    assert mars.hidden is True
    assert moon.disabled is True
    assert mars.disabled is True


def test_travel_status_explains_lock_before_unlock(game_env):
    assert "Near Bodies" in game_env.elements["travel-status"].innerText


def test_mars_summary_widget_hidden_before_unlock(game_env):
    assert game_env.elements["mars-summary"].hidden is True


def test_default_governor_priority_is_balance(game_env):
    assert game_env.module.governor_priority == "balance"
    assert game_env.elements["priority-balance-button"].classList.contains("selected")


def test_default_governor_budget_is_50_percent(game_env):
    assert game_env.module.governor_budget_pct == 50.0
    assert game_env.elements["governor-budget-value"].innerText == "50"


# --- travel gating -----------------------------------------------------

def test_traveling_before_unlock_does_nothing(game_env):
    game_env.travel_to_moon()
    assert game_env.module.current_planet == "Earth"
    assert game_env.elements["earth-view"].hidden is False


def test_travel_buttons_appear_once_unlocked(game_env):
    _unlock_near_bodies(game_env)
    moon = game_env.elements["travel-moon-button"]
    mars = game_env.elements["travel-mars-button"]
    assert moon.hidden is False
    assert mars.hidden is False
    assert moon.disabled is False
    assert mars.disabled is False


def test_travel_status_updates_once_unlocked(game_env):
    _unlock_near_bodies(game_env)
    assert game_env.elements["travel-status"].innerText == "Choose a destination:"


def test_mars_summary_widget_appears_once_unlocked(game_env):
    _unlock_near_bodies(game_env)
    assert game_env.elements["mars-summary"].hidden is False


# --- cross-summary gating applies on every view, not just Earth's --------
# Regression coverage for a real bug: only Earth's own view ever gated its
# cross-summary widgets by unlock status; every other view showed every
# other real economy's "(governed)" widget unconditionally, leaking the
# name/existence of not-yet-researched Far Bodies the moment you traveled
# to any Near Body. update_cross_summary() now owns this gating generically
# for every viewer, not just update_travel_display()'s Earth-specific logic.

def test_non_earth_views_hide_not_yet_unlocked_targets(game_env):
    _unlock_near_bodies(game_env)  # Mars/Moon unlocked, Far Bodies still locked
    game_env.travel_to_mars()
    assert game_env.elements["mars-venus-summary"].hidden is True
    assert game_env.elements["mars-asteroidbelt-summary"].hidden is True
    assert game_env.elements["mars-pluto-summary"].hidden is True
    assert game_env.elements["mars-jupitermoons-summary"].hidden is True
    assert game_env.elements["mars-saturnmoons-summary"].hidden is True
    # Earth and Moon are both real and unlocked at this point, so Mars's
    # view of each of them should NOT be hidden.
    assert game_env.elements["mars-earth-summary"].hidden is False
    assert game_env.elements["mars-moon-summary"].hidden is False


def test_non_earth_views_reveal_targets_once_unlocked(game_env):
    _unlock_near_bodies(game_env)
    game_env.travel_to_mars()
    assert game_env.elements["mars-venus-summary"].hidden is True

    game_env.module.unlocked_bodies.update(game_env.module.RESEARCH_TIERS[1]["unlocks"])
    game_env.module.update_all_cross_summaries()
    assert game_env.elements["mars-venus-summary"].hidden is False
    assert game_env.elements["mars-asteroidbelt-summary"].hidden is False
    assert game_env.elements["mars-pluto-summary"].hidden is False
    assert game_env.elements["mars-jupitermoons-summary"].hidden is False
    assert game_env.elements["mars-saturnmoons-summary"].hidden is False


def test_funding_research_refreshes_cross_summaries_on_every_view_immediately(game_env):
    # Regression test for the fix accompanying this one: on_fund_research()
    # must call update_all_cross_summaries() itself (not just rely on the
    # next 100ms tick) so every view's gating is correct the instant a tier
    # completes, mirroring test_funding_research_to_completion_unlocks_travel_for_real
    # below but for cross-summary widgets specifically.
    game_env.earth["resource_count"] = 1000
    clicks = 1000 // game_env.module.RESEARCH_FUND_COST
    for _ in range(clicks):
        game_env.fund_research()
    game_env.travel_to_mars()
    assert game_env.elements["mars-venus-summary"].hidden is True  # Far Bodies still locked

    game_env.earth["resource_count"] = 5000
    clicks = 5000 // game_env.module.RESEARCH_FUND_COST
    for _ in range(clicks):
        game_env.fund_research()
    assert game_env.elements["mars-venus-summary"].hidden is False  # no tick() call in between


def test_funding_research_to_completion_unlocks_travel_for_real(game_env):
    # Regression test: exercises the actual on_fund_research code path
    # (rather than the _unlock_near_bodies test shortcut, which sets
    # near_bodies_unlocked directly) to make sure funding research all the
    # way to the target actually refreshes the travel section. This caught
    # a real bug where on_fund_research flipped near_bodies_unlocked but
    # never called update_travel_display(), leaving Travel stuck showing
    # "locked" even after the tier was unlocked.
    game_env.earth["resource_count"] = 1000
    for _ in range(20):
        game_env.fund_research()
    assert "Moon" in game_env.module.unlocked_bodies
    assert "Mars" in game_env.module.unlocked_bodies
    assert game_env.elements["travel-moon-button"].hidden is False
    assert game_env.elements["travel-status"].innerText == "Choose a destination:"


# --- traveling to Moon (still a placeholder) ----------------------------

def test_travel_to_moon_switches_planet(game_env):
    _unlock_near_bodies(game_env)
    game_env.travel_to_moon()
    assert game_env.module.current_planet == "Moon"


# Since Milestone 9b, Moon has its own real economy (like Mars since
# Milestone 6) and no longer uses the shared away-view placeholder — see
# test_moon_economy.py for its own click/building/ecology loop, and
# test_research_tier2_framework.py for the away-view placeholder as used by
# the five bodies that still don't have an economy.

def test_travel_to_moon_swaps_visible_view(game_env):
    _unlock_near_bodies(game_env)
    game_env.travel_to_moon()
    assert game_env.elements["earth-view"].hidden is True
    assert game_env.elements["moon-view"].hidden is False
    assert game_env.elements["away-view"].hidden is True
    assert game_env.elements["mars-view"].hidden is True


def test_travel_to_moon_populates_earth_and_mars_summary_widgets_immediately(game_env):
    _unlock_near_bodies(game_env)
    game_env.earth["resource_count"] = 42
    game_env.earth["generator_count"] = 3
    game_env.earth["recycler_count"] = 1
    game_env.earth["ecology_health"] = 77.0
    game_env.travel_to_moon()
    assert game_env.elements["moon-earth-summary-resource"].innerText == "42"
    assert game_env.elements["moon-earth-summary-generators"].innerText == "3"
    assert game_env.elements["moon-earth-summary-recyclers"].innerText == "1"
    assert game_env.elements["moon-earth-summary-ecology"].innerText == "77"


def test_travel_button_gives_press_feedback(game_env):
    _unlock_near_bodies(game_env)
    button = game_env.elements["travel-moon-button"]
    game_env.travel_to_moon()
    assert button.classList.contains("pressed")
    game_env.timers.flush()
    assert not button.classList.contains("pressed")


def test_travel_button_gives_feedback_even_when_locked(game_env):
    button = game_env.elements["travel-moon-button"]
    game_env.travel_to_moon()
    assert button.classList.contains("pressed")


# --- traveling to Mars (its own real view now) --------------------------

def test_travel_to_mars_switches_planet(game_env):
    _unlock_near_bodies(game_env)
    game_env.travel_to_mars()
    assert game_env.module.current_planet == "Mars"


def test_travel_to_mars_swaps_visible_view(game_env):
    _unlock_near_bodies(game_env)
    game_env.travel_to_mars()
    assert game_env.elements["earth-view"].hidden is True
    assert game_env.elements["mars-view"].hidden is False
    assert game_env.elements["away-view"].hidden is True


def test_travel_to_mars_populates_earth_summary_widget_immediately(game_env):
    _unlock_near_bodies(game_env)
    game_env.earth["resource_count"] = 42
    game_env.earth["generator_count"] = 3
    game_env.earth["recycler_count"] = 1
    game_env.earth["ecology_health"] = 77.0
    game_env.travel_to_mars()
    assert game_env.elements["mars-earth-summary-resource"].innerText == "42"
    assert game_env.elements["mars-earth-summary-generators"].innerText == "3"
    assert game_env.elements["mars-earth-summary-recyclers"].innerText == "1"
    assert game_env.elements["mars-earth-summary-ecology"].innerText == "77"


def test_travel_to_mars_does_not_touch_moon_placeholder(game_env):
    _unlock_near_bodies(game_env)
    game_env.travel_to_mars()
    assert game_env.elements["away-view"].hidden is True


# --- returning to Earth -------------------------------------------------

def test_return_to_earth_switches_planet_back(game_env):
    _unlock_near_bodies(game_env)
    game_env.travel_to_mars()
    game_env.return_to_earth()
    assert game_env.module.current_planet == "Earth"


def test_return_to_earth_swaps_view_back_from_moon(game_env):
    _unlock_near_bodies(game_env)
    game_env.travel_to_moon()
    game_env.return_to_earth()
    assert game_env.elements["earth-view"].hidden is False
    assert game_env.elements["away-view"].hidden is True


def test_return_to_earth_swaps_view_back_from_mars(game_env):
    _unlock_near_bodies(game_env)
    game_env.travel_to_mars()
    game_env.return_to_earth()
    assert game_env.elements["earth-view"].hidden is False
    assert game_env.elements["mars-view"].hidden is True


def test_return_to_earth_refreshes_mars_summary_widget(game_env):
    _unlock_near_bodies(game_env)
    game_env.travel_to_mars()
    game_env.mars["resource_count"] = 5
    game_env.mars["generator_count"] = 2
    game_env.return_to_earth()
    assert game_env.elements["mars-summary-resource"].innerText == "5"
    assert game_env.elements["mars-summary-generators"].innerText == "2"


def test_can_travel_again_after_returning(game_env):
    _unlock_near_bodies(game_env)
    game_env.travel_to_moon()
    game_env.return_to_earth()
    game_env.travel_to_mars()
    assert game_env.module.current_planet == "Mars"


# --- Earth's economy keeps running while away (not idle-silent) -----------

def test_generator_production_continues_while_away(game_env):
    _unlock_near_bodies(game_env)
    game_env.earth["resource_count"] = 10
    game_env.earth["generator_count"] = 1
    game_env.travel_to_moon()
    game_env.timers.tick_intervals(10)  # 1 second
    assert game_env.earth["resource_count"] > 10


def test_ecology_decay_continues_while_away(game_env):
    _unlock_near_bodies(game_env)
    game_env.earth["generator_count"] = 1
    game_env.travel_to_moon()
    game_env.timers.tick_intervals(10)
    assert game_env.earth["ecology_health"] < 100.0


def test_away_summary_refreshes_live_on_tick(game_env):
    _unlock_near_bodies(game_env)
    game_env.earth["resource_count"] = 10
    game_env.earth["generator_count"] = 1
    game_env.travel_to_moon()
    game_env.timers.tick_intervals(10)  # +1 Iron from the generator
    assert game_env.elements["away-earth-resource"].innerText == "11"


def test_earth_summary_on_mars_refreshes_live_on_tick(game_env):
    _unlock_near_bodies(game_env)
    game_env.earth["resource_count"] = 10
    game_env.earth["generator_count"] = 1
    game_env.travel_to_mars()
    game_env.timers.tick_intervals(10)  # +1 Iron from the generator
    assert game_env.elements["mars-earth-summary-resource"].innerText == "11"


def test_mars_summary_on_earth_refreshes_live_on_tick(game_env):
    _unlock_near_bodies(game_env)
    game_env.mars["resource_count"] = 10
    game_env.mars["generator_count"] = 1
    game_env.timers.tick_intervals(10)  # +1 Water Ice from Mars's generator
    assert game_env.elements["mars-summary-resource"].innerText == "11"


# --- governor: priority selection ---------------------------------------

def test_setting_priority_updates_state(game_env):
    game_env.set_priority("growth")
    assert game_env.module.governor_priority == "growth"


def test_setting_priority_updates_selected_highlight(game_env):
    game_env.set_priority("ecology")
    assert game_env.elements["priority-ecology-button"].classList.contains("selected")
    assert not game_env.elements["priority-growth-button"].classList.contains("selected")
    assert not game_env.elements["priority-balance-button"].classList.contains("selected")


def test_priority_buttons_give_press_feedback(game_env):
    button = game_env.elements["priority-growth-button"]
    game_env.set_priority("growth")
    assert button.classList.contains("pressed")


# --- governor: budget adjustment -----------------------------------------

def test_increasing_budget_steps_by_ten(game_env):
    game_env.increase_budget()
    assert game_env.module.governor_budget_pct == 60.0
    assert game_env.elements["governor-budget-value"].innerText == "60"


def test_decreasing_budget_steps_by_ten(game_env):
    game_env.decrease_budget()
    assert game_env.module.governor_budget_pct == 40.0


def test_budget_clamps_at_100(game_env):
    for _ in range(10):
        game_env.increase_budget()
    assert game_env.module.governor_budget_pct == 100.0


def test_budget_clamps_at_0(game_env):
    for _ in range(10):
        game_env.decrease_budget()
    assert game_env.module.governor_budget_pct == 0.0


def test_budget_buttons_give_press_feedback(game_env):
    button = game_env.elements["budget-increase-button"]
    game_env.increase_budget()
    assert button.classList.contains("pressed")


# --- governor: never touches whichever planet is current ------------------

def test_governor_makes_no_purchases_on_earth_while_on_earth(game_env):
    game_env.earth["resource_count"] = 10000
    game_env.set_priority("growth")
    game_env.timers.tick_intervals(50)
    assert game_env.earth["generator_count"] == 0
    assert game_env.earth["recycler_count"] == 0


def test_governor_makes_no_purchases_on_mars_while_on_mars(game_env):
    _unlock_near_bodies(game_env)
    game_env.travel_to_mars()
    game_env.mars["resource_count"] = 10000
    game_env.set_priority("growth")
    game_env.timers.tick_intervals(50)
    assert game_env.mars["generator_count"] == 0
    assert game_env.mars["recycler_count"] == 0


# --- governor: growth priority --------------------------------------------

def test_growth_priority_only_buys_generators(game_env):
    _unlock_near_bodies(game_env)
    game_env.set_priority("growth")
    game_env.earth["resource_count"] = 10000
    game_env.travel_to_mars()
    game_env.timers.tick_intervals(50)  # plenty of ticks to spend down
    assert game_env.earth["generator_count"] > 0
    assert game_env.earth["recycler_count"] == 0


# --- governor: ecology priority -------------------------------------------

def test_ecology_priority_only_buys_recyclers(game_env):
    _unlock_near_bodies(game_env)
    game_env.set_priority("ecology")
    game_env.earth["resource_count"] = 10000
    game_env.travel_to_mars()
    game_env.timers.tick_intervals(50)
    assert game_env.earth["recycler_count"] > 0
    assert game_env.earth["generator_count"] == 0


# --- governor: balance priority --------------------------------------------

def test_balance_priority_buys_both_building_types(game_env):
    _unlock_near_bodies(game_env)
    game_env.set_priority("balance")
    game_env.earth["resource_count"] = 10000
    game_env.travel_to_mars()
    game_env.timers.tick_intervals(50)
    assert game_env.earth["generator_count"] > 0
    assert game_env.earth["recycler_count"] > 0


def test_balance_priority_alternates_purchase_targets(game_env):
    _unlock_near_bodies(game_env)
    game_env.set_priority("balance")
    game_env.earth["resource_count"] = 10000
    game_env.travel_to_mars()

    game_env.timers.tick_intervals(1)  # governor_tick_count -> 1 (odd -> recycler)
    assert game_env.earth["recycler_count"] == 1
    assert game_env.earth["generator_count"] == 0

    game_env.timers.tick_intervals(1)  # governor_tick_count -> 2 (even -> generator)
    assert game_env.earth["generator_count"] == 1
    assert game_env.earth["recycler_count"] == 1


# --- governor: budget respected -------------------------------------------

def test_governor_does_not_spend_beyond_budget(game_env):
    _unlock_near_bodies(game_env)
    game_env.module.governor_budget_pct = 0.0
    game_env.set_priority("growth")
    game_env.earth["resource_count"] = 10000
    game_env.travel_to_mars()
    game_env.timers.tick_intervals(50)
    assert game_env.earth["generator_count"] == 0
    assert game_env.earth["resource_count"] == 10000


def test_governor_spends_up_to_the_configured_budget_fraction(game_env):
    _unlock_near_bodies(game_env)
    game_env.module.governor_budget_pct = 100.0
    game_env.set_priority("growth")
    game_env.earth["resource_count"] = 10  # exactly the first generator's cost
    game_env.travel_to_mars()
    game_env.timers.tick_intervals(1)
    assert game_env.earth["generator_count"] == 1
    assert game_env.earth["resource_count"] == 0


def test_low_budget_still_eventually_affordable_as_iron_grows(game_env):
    # With a 50% budget and generator_cost() == 10, the governor needs at
    # least 20 banked Iron before it can afford the first purchase.
    _unlock_near_bodies(game_env)
    game_env.set_priority("growth")
    game_env.earth["resource_count"] = 19
    game_env.travel_to_mars()
    game_env.timers.tick_intervals(1)
    assert game_env.earth["generator_count"] == 0

    game_env.earth["resource_count"] = 20
    game_env.timers.tick_intervals(1)
    assert game_env.earth["generator_count"] == 1


# --- governor: stops when player returns to Earth -------------------------

def test_governor_stops_purchasing_after_returning_to_earth(game_env):
    _unlock_near_bodies(game_env)
    game_env.set_priority("growth")
    game_env.earth["resource_count"] = 10000
    game_env.travel_to_mars()
    game_env.timers.tick_intervals(10)
    generators_while_away = game_env.earth["generator_count"]
    assert generators_while_away > 0

    game_env.return_to_earth()
    game_env.timers.tick_intervals(50)
    assert game_env.earth["generator_count"] == generators_while_away


# --- governor priority changes take effect immediately on next tick -------

def test_changing_priority_while_away_takes_effect_next_tick(game_env):
    _unlock_near_bodies(game_env)
    game_env.set_priority("growth")
    game_env.earth["resource_count"] = 10000
    game_env.travel_to_mars()
    game_env.timers.tick_intervals(5)
    assert game_env.earth["generator_count"] > 0
    assert game_env.earth["recycler_count"] == 0

    game_env.set_priority("ecology")
    game_env.timers.tick_intervals(5)
    assert game_env.earth["recycler_count"] > 0


# --- governor: reciprocal (Mars governed while on Earth) -------------------

def test_mars_is_governed_while_on_earth(game_env):
    # Symmetric to Earth being governed while the player is on Mars: with
    # the player on Earth (the default), Mars should be autonomously grown.
    _unlock_near_bodies(game_env)
    game_env.set_priority("growth")
    game_env.mars["resource_count"] = 10000
    game_env.timers.tick_intervals(50)
    assert game_env.mars["generator_count"] > 0


def test_both_earth_and_mars_governed_while_on_moon(game_env):
    # On the still-undeveloped Moon, neither Earth nor Mars is "current",
    # so both real economies should be governed simultaneously.
    _unlock_near_bodies(game_env)
    game_env.set_priority("growth")
    game_env.earth["resource_count"] = 10000
    game_env.mars["resource_count"] = 10000
    game_env.travel_to_moon()
    game_env.timers.tick_intervals(50)
    assert game_env.earth["generator_count"] > 0
    assert game_env.mars["generator_count"] > 0
