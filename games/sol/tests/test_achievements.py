"""Tests for the ACHIEVEMENTS-SYSTEM-DESIGN.md reference integration: SOL's
own achievements.json catalog, the checkers/progress readouts in game.py,
and the in-game toggle/panel. Every achievement's earned status is meant to
be a pure function of state that already exists elsewhere in this module —
these tests exercise that by driving the real game systems (clicking,
buying, traveling, funding research) rather than poking `_earned` flags
that don't exist."""


def _tier(game_env, index):
    return game_env.module.RESEARCH_TIERS[index]


def _complete_tier(game_env, index):
    """Same helper as test_research.py: funds and completes tiers 0..index
    in sequence (tiers must be researched in order)."""
    for i in range(index + 1):
        target = _tier(game_env, i)["target"]
        game_env.earth["resource_count"] = target
        clicks = target // game_env.module.RESEARCH_FUND_COST
        for _ in range(clicks):
            game_env.fund_research()


def _all_texts(element):
    texts = [element.innerText]
    for child in element.children:
        texts.extend(_all_texts(child))
    return texts


# --- the catalog itself -----------------------------------------------

def test_achievements_catalog_loads_from_json_with_a_reasonable_count(game_env):
    module = game_env.module
    assert 5 <= len(module.ACHIEVEMENTS) <= 30
    ids = [entry["id"] for entry in module.ACHIEVEMENTS]
    assert len(ids) == len(set(ids))  # no duplicate ids


def test_every_catalog_entry_has_a_matching_checker(game_env):
    module = game_env.module
    for entry in module.ACHIEVEMENTS:
        assert entry["id"] in module.ACHIEVEMENT_CHECKS
        assert callable(module.ACHIEVEMENT_CHECKS[entry["id"]])


def test_every_progress_entry_refers_to_a_real_achievement(game_env):
    module = game_env.module
    catalog_ids = {entry["id"] for entry in module.ACHIEVEMENTS}
    assert set(module.ACHIEVEMENT_PROGRESS).issubset(catalog_ids)


# --- nothing earned on a fresh game ------------------------------------

def test_nothing_is_earned_on_a_fresh_game(game_env):
    assert game_env.module.achievement_ids_earned() == []


def test_summary_shows_every_entry_as_not_earned_initially(game_env):
    summary = game_env.module.achievements_summary()
    assert len(summary) == len(game_env.module.ACHIEVEMENTS)
    assert all(entry["earned"] is False for entry in summary)


# --- individual achievements, driven through real game systems --------

def test_first_ore_earned_after_the_first_earth_click(game_env):
    assert "first_ore" not in game_env.module.achievement_ids_earned()
    game_env.click("Earth")
    assert "first_ore" in game_env.module.achievement_ids_earned()


def test_automated_earned_after_earths_first_generator(game_env):
    game_env.earth["resource_count"] = 10
    game_env.buy_generator("Earth")
    assert "automated" in game_env.module.achievement_ids_earned()


def test_recycler_online_earned_after_any_planets_first_recycler(game_env):
    game_env.mars["resource_count"] = 15
    game_env.buy_recycler("Mars")
    assert "recycler_online" in game_env.module.achievement_ids_earned()


def test_off_world_earned_after_the_first_trip_away_from_earth(game_env):
    assert "off_world" not in game_env.module.achievement_ids_earned()
    game_env.module.unlocked_bodies.add("Mars")
    game_env.travel_to_mars()
    assert "off_world" in game_env.module.achievement_ids_earned()


def test_grand_tour_requires_visiting_every_world_not_just_unlocking_them(game_env):
    module = game_env.module
    module.unlocked_bodies.update(p for p in module.PLANETS if p != "Earth")
    module.update_travel_display()
    # Unlocked everywhere, but never actually traveled anywhere yet.
    assert "grand_tour" not in module.achievement_ids_earned()

    for body in module.TRAVEL_BUTTON_ID:
        game_env.travel_to(body)
        game_env.return_to_earth()

    assert "grand_tour" in module.achievement_ids_earned()
    assert module.visited_bodies == set(module.PLANETS)


def test_trade_route_established_after_the_first_route(game_env):
    game_env.earth["resource_count"] = 30
    game_env.buy_trade_route("Earth")
    assert "trade_route_established" in game_env.module.achievement_ids_earned()


def test_trade_network_needs_five_routes_across_the_system(game_env):
    module = game_env.module
    game_env.earth["trade_routes"]["Mars"] = 4
    assert "trade_network" not in module.achievement_ids_earned()
    game_env.mars["trade_routes"]["Earth"] = 1
    assert "trade_network" in module.achievement_ids_earned()


def test_tier_one_cleared_after_the_near_bodies_tier(game_env):
    _complete_tier(game_env, 0)
    assert "tier_one_cleared" in game_env.module.achievement_ids_earned()
    assert "tier_two_cleared" not in game_env.module.achievement_ids_earned()


def test_tier_two_cleared_after_every_research_tier(game_env):
    module = game_env.module
    _complete_tier(game_env, len(module.RESEARCH_TIERS) - 1)
    assert "tier_two_cleared" in module.achievement_ids_earned()


def test_solar_system_unlocked_needs_every_non_earth_body(game_env):
    module = game_env.module
    non_earth = [p for p in module.PLANETS if p != "Earth"]
    for body in non_earth[:-1]:
        module.unlocked_bodies.add(body)
    assert "solar_system_unlocked" not in module.achievement_ids_earned()
    module.unlocked_bodies.add(non_earth[-1])
    assert "solar_system_unlocked" in module.achievement_ids_earned()


def test_a_governed_tick_alone_does_not_earn_governor_appointed(game_env):
    """governor_tick_count increments the instant any other planet exists
    to govern -- true from the very first tick of a brand-new game, before
    the governor has ever actually bought anything. This is exactly the
    bug this test guards against: it was caught live, in the browser, when
    a completely fresh, untouched game showed this achievement already
    earned within the first second."""
    game_env.timers.tick_intervals(3)
    assert game_env.module.governor_tick_count >= 1
    assert game_env.module.governor_purchase_count == 0
    assert "governor_appointed" not in game_env.module.achievement_ids_earned()


def test_governor_appointed_after_the_governor_actually_buys_something(game_env):
    module = game_env.module
    assert "governor_appointed" not in module.achievement_ids_earned()
    # Give Mars (governed while the player sits on Earth) enough Water Ice
    # and budget for the governor to actually afford a purchase.
    game_env.mars["resource_count"] = 1000.0
    module.governor_budget_pct = 100.0
    game_env.timers.tick_intervals(2)  # one growth-turn, one ecology-turn
    assert module.governor_purchase_count >= 1
    assert "governor_appointed" in module.achievement_ids_earned()


def test_sky_city_founder_after_the_first_sky_city(game_env):
    game_env.state("JupiterMoons")["resource_count"] = 50
    game_env.mars["resource_count"] = 20
    game_env.buy_sky_city("JupiterMoons")
    assert "sky_city_founder" in game_env.module.achievement_ids_earned()


def test_ecological_balance_needs_a_running_economy_and_high_health(game_env):
    module = game_env.module
    game_env.earth["generator_count"] = 1
    game_env.earth["ecology_health"] = 90.0
    assert "ecological_balance" not in module.achievement_ids_earned()
    game_env.earth["ecology_health"] = 95.0
    assert "ecological_balance" in module.achievement_ids_earned()


def test_resource_baron_needs_a_million_of_one_resource(game_env):
    module = game_env.module
    game_env.earth["resource_count"] = module.RESOURCE_BARON_THRESHOLD - 1
    assert "resource_baron" not in module.achievement_ids_earned()
    game_env.earth["resource_count"] = module.RESOURCE_BARON_THRESHOLD
    assert "resource_baron" in module.achievement_ids_earned()


def test_terraformer_after_the_first_fully_terraformed_world(game_env):
    game_env.mars["terraform_progress"] = 100.0
    assert "terraformer" in game_env.module.achievement_ids_earned()


def test_planetary_renaissance_needs_four_terraformed_worlds(game_env):
    module = game_env.module
    for planet in list(module.PLANETS)[:3]:
        module.planet_state[planet]["terraform_progress"] = 100.0
    assert "planetary_renaissance" not in module.achievement_ids_earned()
    module.planet_state[list(module.PLANETS)[3]]["terraform_progress"] = 100.0
    assert "planetary_renaissance" in module.achievement_ids_earned()


def test_eight_economies_needs_every_world_generating(game_env):
    module = game_env.module
    for planet in list(module.PLANETS)[:-1]:
        module.planet_state[planet]["generator_count"] = 1
    assert "eight_economies" not in module.achievement_ids_earned()
    module.planet_state[list(module.PLANETS)[-1]]["generator_count"] = 1
    assert "eight_economies" in module.achievement_ids_earned()


def test_full_system_terraformed_matches_the_win_condition(game_env):
    """This is deliberately the same predicate update_win_display() already
    uses for the win banner -- full completion is one milestone with two
    presentations (a persistent banner + a catalog entry), not two separate
    definitions of "done" that could drift apart."""
    module = game_env.module
    for planet in module.PLANETS:
        module.planet_state[planet]["terraform_progress"] = 100.0
    module.update_win_display()
    assert game_env.elements["win-banner"].hidden is False
    assert "full_system_terraformed" in module.achievement_ids_earned()


# --- progress readouts --------------------------------------------------

def test_progress_readout_tracks_partial_progress_toward_a_numeric_target(game_env):
    module = game_env.module
    module.unlocked_bodies.update(["Mars", "Moon"])
    summary = {entry["id"]: entry for entry in module.achievements_summary()}
    current, target = summary["solar_system_unlocked"]["progress"]
    assert current == 2
    assert target == len(module.PLANETS) - 1


def test_earned_entries_carry_no_progress_readout(game_env):
    game_env.click("Earth")
    summary = {entry["id"]: entry for entry in game_env.module.achievements_summary()}
    assert summary["first_ore"]["earned"] is True
    # first_ore has no numeric target at all -- it's a one-shot milestone.
    assert summary["first_ore"]["progress"] is None


# --- achievements never mutate other state -----------------------------

def test_checking_achievements_never_mutates_game_state(game_env):
    module = game_env.module
    game_env.click("Earth")
    game_env.earth["resource_count"] = 500
    before = module.serialize_state()

    module.achievement_ids_earned()
    module.achievements_summary()
    module.on_toggle_achievements()
    module.on_toggle_achievements()

    after = module.serialize_state()
    # Ignore the derived, always-fresh "achievements_earned" projection —
    # everything else must be byte-identical.
    before.pop("achievements_earned")
    after.pop("achievements_earned")
    assert before == after


# --- the toggle + panel --------------------------------------------------

def test_panel_is_hidden_until_toggled(game_env):
    assert game_env.module.achievements_open is False
    assert game_env.elements["achievements-panel"].hidden is True


def test_toggle_button_shows_earned_count(game_env):
    module = game_env.module
    button = game_env.elements["achievements-toggle-button"]
    module.update_achievements_display()
    assert f"0/{len(module.ACHIEVEMENTS)}" in button.innerText

    game_env.click("Earth")
    module.update_achievements_display()
    assert f"1/{len(module.ACHIEVEMENTS)}" in button.innerText


def test_toggling_opens_and_closes_the_panel(game_env):
    module = game_env.module
    module.on_toggle_achievements()
    assert module.achievements_open is True
    assert game_env.elements["achievements-panel"].hidden is False
    assert "Hide" in game_env.elements["achievements-toggle-button"].innerText

    module.on_toggle_achievements()
    assert module.achievements_open is False
    assert game_env.elements["achievements-panel"].hidden is True


def test_toggle_button_is_wired_up_by_setup(game_env):
    button = game_env.elements["achievements-toggle-button"]
    assert "click" in button._listeners
    assert len(button._listeners["click"]) == 1


def test_panel_lists_every_achievement_with_label_and_description(game_env):
    module = game_env.module
    module.on_toggle_achievements()
    texts = _all_texts(game_env.elements["achievements-panel"])
    for entry in module.ACHIEVEMENTS:
        assert any(entry["label"] in text for text in texts)
        assert any(entry["description"] in text for text in texts)


def test_panel_shows_an_earned_badge_distinctly(game_env):
    module = game_env.module
    game_env.click("Earth")
    module.on_toggle_achievements()
    cards = game_env.elements["achievements-panel"].children
    earned_card = next(c for c in cards if "🏆 First Ore" in _all_texts(c))
    assert "achievement-card--earned" in earned_card.className


def test_panel_shows_a_progress_readout_for_an_unearned_numeric_achievement(game_env):
    module = game_env.module
    module.unlocked_bodies.add("Mars")
    module.on_toggle_achievements()
    texts = _all_texts(game_env.elements["achievements-panel"])
    target = len(module.PLANETS) - 1
    assert any(f"1 of {target}" in text for text in texts)


def test_tick_keeps_the_open_panel_and_toggle_label_live(game_env):
    """A tick can itself change what's earned (e.g. governor_appointed
    fires the moment governor_step() runs at all) -- the count checked
    here is whatever's actually true after the tick, not a number picked
    in advance, so this only pins that update_achievements_display() is
    actually wired into tick() rather than only into _full_render()."""
    module = game_env.module
    module.on_toggle_achievements()
    game_env.click("Earth")
    game_env.timers.tick_intervals(1)
    earned_count = len(module.achievement_ids_earned())
    assert earned_count >= 1
    button = game_env.elements["achievements-toggle-button"]
    assert f"{earned_count}/{len(module.ACHIEVEMENTS)}" in button.innerText


# --- retrofit: unlock toast + hub dashboard link ------------------------
# TODO.md "roll achievements out everywhere" — SOL already shipped the base
# 18-achievement catalog + panel; this retrofit adds an unlock-moment toast
# (not just visible inside the panel) and a link from the panel out to the
# hub-wide dashboard (ACHIEVEMENTS-SYSTEM-DESIGN.md §5).


def test_toast_is_hidden_on_a_fresh_game(game_env):
    assert game_env.elements["achievement-toast"].hidden is True


def test_toast_appears_the_tick_an_achievement_is_newly_earned(game_env):
    game_env.click("Earth")
    game_env.timers.tick_intervals(1)
    toast = game_env.elements["achievement-toast"]
    assert toast.hidden is False
    assert "First Ore" in game_env.elements["achievement-toast-text"].innerText


def test_toast_is_not_shown_before_the_earning_tick_runs(game_env):
    # Earning the achievement doesn't retroactively show the toast until
    # tick() actually runs the check -- clicking alone calls
    # update_resource_display(), not the achievement-toast check.
    game_env.click("Earth")
    assert game_env.elements["achievement-toast"].hidden is True


def test_toast_auto_hides_after_its_timeout(game_env):
    game_env.click("Earth")
    game_env.timers.tick_intervals(1)
    game_env.timers.flush()
    assert game_env.elements["achievement-toast"].hidden is True


def test_toast_does_not_repeat_for_an_already_earned_achievement(game_env):
    game_env.click("Earth")
    game_env.timers.tick_intervals(1)
    game_env.timers.flush()
    game_env.timers.tick_intervals(1)  # nothing new earned this tick
    assert game_env.elements["achievement-toast"].hidden is True


def test_toast_reports_multiple_simultaneous_unlocks_together(game_env):
    module = game_env.module
    # Completing tier 2 in one research_node() purchase earns both
    # "tier_two_cleared" and "solar_system_unlocked" (every Far Body
    # unlocks at once) in the same tick -- both should be named in one
    # toast rather than only the last one winning.
    game_env.unlock_tier(1)
    for node in module.RESEARCH_NODES:
        if node["tier"] == 1 and node["id"] != "far_bodies":
            module.researched_nodes.add(node["id"])
    module._recompute_research()
    game_env.earth["resource_count"] = 10_000
    game_env.research_node("far_bodies")
    game_env.timers.tick_intervals(1)
    text = game_env.elements["achievement-toast-text"].innerText
    assert "achievements unlocked" in text


def test_loading_a_save_with_already_earned_achievements_does_not_replay_them_as_toasts(game_env):
    """A save made after playing for a while already has several
    achievements earned -- load_state() must seed the toast baseline to
    that save's own earned set, not diff against an empty one, or every
    reload/autoload would replay every past unlock as a fresh toast. A3's
    own welcome-back toast DOES fire on load (that's its whole point), so
    this checks the toast text is the welcome-back message, not an
    achievement-unlock one, and that a subsequent tick doesn't add a
    second, achievement-flavored toast on top of it."""
    module = game_env.module
    game_env.click("Earth")
    saved = module.get_state()
    assert saved["achievements_earned"]  # sanity: this save really has one

    module.load_state(saved)
    toast_text = game_env.elements["achievement-toast-text"].innerText
    assert "Welcome back" in toast_text
    assert "Achievement unlocked" not in toast_text

    game_env.timers.tick_intervals(1)
    assert "Achievement unlocked" not in game_env.elements["achievement-toast-text"].innerText


def test_hub_dashboard_link_is_present_when_the_panel_is_open(game_env):
    module = game_env.module
    module.on_toggle_achievements()
    panel = game_env.elements["achievements-panel"]
    link = next(c for c in panel.children if getattr(c, "tagName", None) == "A")
    assert link.href == "../../index.html#account-achievements-dashboard"
    assert "hub" in link.innerText.lower()


# --- A2/A13: second achievement wave (speedrun + pure-clicker) ---------
# Both categories are one-shot historical flags (game.py's own module
# comment above ACHIEVEMENT_CHECKS explains why a live-derived check can't
# express "before a generator ever existed" or "within N minutes of play"),
# each checked at the exact moment its condition can first become true.


def test_quick_start_earned_by_completing_tier_one_within_the_time_window(game_env):
    module = game_env.module
    tier = _tier(game_env, 0)
    game_env.earth["resource_count"] = tier["target"]
    for _ in range(tier["target"] // module.RESEARCH_FUND_COST):
        game_env.fund_research()
    assert module.quick_start_hit is True
    assert "quick_start" in module.achievement_ids_earned()


def test_quick_start_not_earned_outside_the_time_window(game_env):
    module = game_env.module
    game_env.timers.tick_intervals(module.QUICK_START_TICKS + 1)
    tier = _tier(game_env, 0)
    game_env.earth["resource_count"] = tier["target"]
    for _ in range(tier["target"] // module.RESEARCH_FUND_COST):
        game_env.fund_research()
    assert module.quick_start_hit is False


def test_swift_expansion_earned_by_completing_both_tiers_in_time(game_env):
    module = game_env.module
    _complete_tier(game_env, 1)
    assert module.swift_expansion_hit is True
    assert "swift_expansion" in module.achievement_ids_earned()


def test_swift_expansion_not_earned_outside_the_time_window(game_env):
    module = game_env.module
    game_env.timers.tick_intervals(module.SWIFT_EXPANSION_TICKS + 1)
    _complete_tier(game_env, 1)
    assert module.swift_expansion_hit is False
    # quick_start also fails here since both tiers were funded well past
    # its own (shorter) window.
    assert module.quick_start_hit is False


def test_manual_labor_earned_by_reaching_the_threshold_by_hand(game_env):
    module = game_env.module
    for _ in range(module.MANUAL_LABOR_THRESHOLD):
        game_env.click("Earth")
    assert module.manual_labor_hit is True
    assert "manual_labor" in module.achievement_ids_earned()


def test_manual_labor_not_earned_if_a_generator_exists_first(game_env):
    module = game_env.module
    game_env.earth["resource_count"] = 10
    game_env.buy_generator("Earth")
    for _ in range(module.MANUAL_LABOR_THRESHOLD):
        game_env.click("Earth")
    assert module.manual_labor_hit is False


def test_manual_labor_not_earned_below_the_threshold(game_env):
    module = game_env.module
    for _ in range(module.MANUAL_LABOR_THRESHOLD - 1):
        game_env.click("Earth")
    assert module.manual_labor_hit is False


def test_off_the_grid_earned_by_clearing_tier_one_with_no_generator(game_env):
    module = game_env.module
    tier = _tier(game_env, 0)
    game_env.earth["resource_count"] = tier["target"]
    for _ in range(tier["target"] // module.RESEARCH_FUND_COST):
        game_env.fund_research()
    assert module.off_the_grid_hit is True
    assert "off_the_grid" in module.achievement_ids_earned()


def test_off_the_grid_not_earned_if_a_generator_was_ever_built(game_env):
    module = game_env.module
    game_env.earth["resource_count"] = 10
    game_env.buy_generator("Earth")
    tier = _tier(game_env, 0)
    game_env.earth["resource_count"] = tier["target"]
    for _ in range(tier["target"] // module.RESEARCH_FUND_COST):
        game_env.fund_research()
    assert module.off_the_grid_hit is False


def test_off_the_grid_not_earned_if_the_governor_ever_built_one(game_env):
    """any_generator_ever_built is also set from governor_step()'s own buy
    branch -- "never automated" means nowhere, not just not-by-hand."""
    module = game_env.module
    module.governor_purchase_count = 0
    module.any_generator_ever_built = True  # simulate a prior governor buy
    tier = _tier(game_env, 0)
    game_env.earth["resource_count"] = tier["target"]
    for _ in range(tier["target"] // module.RESEARCH_FUND_COST):
        game_env.fund_research()
    assert module.off_the_grid_hit is False


def test_new_wave_achievements_are_in_the_catalog(game_env):
    ids = {entry["id"] for entry in game_env.module.ACHIEVEMENTS}
    assert {"quick_start", "swift_expansion", "manual_labor", "off_the_grid"}.issubset(ids)


# --- A3: "welcome back" return-visit summary toast ----------------------
# Fires only when a save is actually loaded (load_state()/
# load_save_state_json(), the shared/save-widget.js contract entry
# points) -- a brand-new game (setup() alone, no save) is never "a
# returning player" and must not show it.


def test_fresh_game_never_shows_a_welcome_back_toast(game_env):
    assert game_env.elements["achievement-toast"].hidden is True
    game_env.timers.tick_intervals(5)
    assert "Welcome back" not in game_env.elements["achievement-toast-text"].innerText


def test_load_state_shows_a_welcome_back_toast(game_env):
    module = game_env.module
    module.unlocked_bodies.add("Mars")
    game_env.travel_to("Mars")
    saved = module.get_state()

    module.load_state(saved)

    toast = game_env.elements["achievement-toast"]
    assert toast.hidden is False
    text = game_env.elements["achievement-toast-text"].innerText
    assert "Welcome back" in text
    assert "2/" in text  # worlds visited: Earth + Mars


def test_load_save_state_json_also_shows_the_welcome_back_toast(game_env):
    module = game_env.module
    saved_json = module.get_save_state_json()
    module.load_save_state_json(saved_json)
    assert "Welcome back" in game_env.elements["achievement-toast-text"].innerText


def test_welcome_back_toast_auto_hides_after_its_timeout(game_env):
    module = game_env.module
    module.load_state(module.get_state())
    game_env.timers.flush()
    assert game_env.elements["achievement-toast"].hidden is True
