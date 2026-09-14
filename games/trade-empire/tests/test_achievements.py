"""Tests for the ACHIEVEMENTS-SYSTEM-DESIGN.md rollout to Trade Empire: the
achievements.json catalog, the checkers/progress readouts in game.py, the
in-game toggle/panel, and the unlock toast + hub-dashboard link. SOL is the
reference integration; this adopts the same contract but is grounded in
Trade Empire's own mechanics (sales, automation, fleet priority, research,
colony development, market crashes, the multi-system endgame) -- these
tests drive the real game systems rather than poking a hand-maintained
"earned" flag that doesn't exist.
"""


def _sell_all_home_system_goods(game_env):
    """Sells all 5 home-system goods (ore, grain, machinery, water,
    energy) in a single session, using all 4 ships -- there's no ship
    starting at Helion, so ship 4 does a second leg (Cryo -> Helion)
    after its first delivery to pick up energy."""
    module = game_env.module
    game_env.load(ship_id="1")
    game_env.depart("verdant", ship_id="1")  # sells ore
    game_env.load(ship_id="2")
    game_env.depart("ferrum", ship_id="2")  # sells grain
    game_env.load(ship_id="3")
    game_env.depart("aurum", ship_id="3")  # sells machinery
    game_env.load(ship_id="4")
    game_env.depart("helion", ship_id="4")  # sells water
    game_env.tick(module.TRAVEL_TICKS)

    game_env.load(ship_id="4")  # now docked at Helion, produces energy
    game_env.depart("cryo", ship_id="4")  # sells energy
    game_env.tick(module.TRAVEL_TICKS)


def _meet_endgame_criteria(game_env):
    module = game_env.module
    module.total_profit = 10_000
    for ship_id in module.ships:
        module.automate_ship(ship_id)
    game_env.toggle_fleet_priority()
    module.research_points = 1000
    game_env.unlock_research("galaxy_expansion")


# --- the catalog itself -----------------------------------------------

def test_achievements_catalog_loads_from_json_with_a_reasonable_count(game_env):
    module = game_env.module
    assert 15 <= len(module.ACHIEVEMENTS) <= 25
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


# --- nothing earned on a fresh game -------------------------------------

def test_nothing_is_earned_on_a_fresh_game(game_env):
    assert game_env.module.achievement_ids_earned() == []


def test_summary_shows_every_entry_as_not_earned_initially(game_env):
    summary = game_env.module.achievements_summary()
    assert len(summary) == len(game_env.module.ACHIEVEMENTS)
    assert all(entry["earned"] is False for entry in summary)


# --- individual achievements, driven through real game systems ---------

def test_first_sale_earned_after_first_delivery(game_env):
    module = game_env.module
    assert "first_sale" not in module.achievement_ids_earned()
    game_env.load(ship_id="1")
    game_env.depart("verdant", ship_id="1")
    game_env.tick(module.TRAVEL_TICKS)
    assert "first_sale" in module.achievement_ids_earned()


def test_first_automation_earned_on_automating_any_ship(game_env):
    module = game_env.module
    module.total_profit = 1000
    assert "first_automation" not in module.achievement_ids_earned()
    module.automate_ship("1")
    assert "first_automation" in module.achievement_ids_earned()


def test_automation_slots_maxed_requires_every_unlocked_slot_filled(game_env):
    module = game_env.module
    module.total_profit = 1000
    module.automate_ship("1")
    assert "automation_slots_maxed" not in module.achievement_ids_earned()
    module.automate_ship("2")  # MAX_AUTOMATED_SHIPS == 2 by default
    assert "automation_slots_maxed" in module.achievement_ids_earned()


def test_fleet_priority_enabled_achievement(game_env):
    module = game_env.module
    assert "fleet_priority_enabled" not in module.achievement_ids_earned()
    game_env.toggle_fleet_priority()
    assert "fleet_priority_enabled" in module.achievement_ids_earned()


def test_fleet_priority_reposition_earned_when_an_idle_ship_repositions(game_env):
    module = game_env.module
    module.total_profit = 1000
    module.automate_ship("1")  # docked at Aurum, empty
    game_env.toggle_fleet_priority()
    # Make Helion (needs Water) the most urgent colony -- its producer is
    # Cryo, which differs from ship 1's current location (Aurum), so the
    # fleet-priority branch should reposition it there instead of loading
    # its local Ore.
    module.colony_states["helion"].need_satisfaction = 0.0
    assert "fleet_priority_reposition" not in module.achievement_ids_earned()
    module.run_automation()
    assert module.ever_repositioned is True
    assert "fleet_priority_reposition" in module.achievement_ids_earned()


def test_research_achievements_earned_on_unlocking_their_node(game_env):
    module = game_env.module
    module.research_points = 1000
    for node_id, achievement_id in (
        ("fast_ships", "fast_ships_researched"),
        ("hauler", "hauler_researched"),
        ("automation_slot", "automation_slot_researched"),
    ):
        assert achievement_id not in module.achievement_ids_earned()
        module.unlock_research(node_id)
        assert achievement_id in module.achievement_ids_earned()


def test_all_research_unlocked_requires_every_home_system_node(game_env):
    module = game_env.module
    module.research_points = 1000
    module.unlock_research("fast_ships")
    module.unlock_research("hauler")
    module.unlock_research("automation_slot")
    assert "all_research_unlocked" not in module.achievement_ids_earned()
    module.unlock_research("galaxy_expansion")
    assert "all_research_unlocked" in module.achievement_ids_earned()


def test_galaxy_expansion_unlocked_achievement(game_env):
    module = game_env.module
    module.research_points = 1000
    assert "galaxy_expansion_unlocked" not in module.achievement_ids_earned()
    module.unlock_research("galaxy_expansion")
    assert "galaxy_expansion_unlocked" in module.achievement_ids_earned()


def test_colony_developed_earned_by_any_single_colony(game_env):
    module = game_env.module
    assert "colony_developed" not in module.achievement_ids_earned()
    module.colony_states["aurum"].deliver(module.DEVELOPMENT_THRESHOLD)
    assert "colony_developed" in module.achievement_ids_earned()


def test_home_system_fully_developed_requires_all_five(game_env):
    module = game_env.module
    for colony_id in list(module.COLONIES)[:-1]:
        module.colony_states[colony_id].deliver(module.DEVELOPMENT_THRESHOLD)
    assert "home_system_fully_developed" not in module.achievement_ids_earned()
    last_colony = list(module.COLONIES)[-1]
    module.colony_states[last_colony].deliver(module.DEVELOPMENT_THRESHOLD)
    assert "home_system_fully_developed" in module.achievement_ids_earned()


def test_kepler_colony_developed_requires_expansion_unlocked_first(game_env):
    module = game_env.module
    module.research_points = 1000
    module.unlock_research("galaxy_expansion")
    assert "kepler_colony_developed" not in module.achievement_ids_earned()
    module.colony_states["kepler_a"].deliver(module.DEVELOPMENT_THRESHOLD)
    assert "kepler_colony_developed" in module.achievement_ids_earned()


def test_profit_thresholds_use_the_highest_profit_ever_reached(game_env):
    module = game_env.module
    module.total_profit = 10_000
    game_env.tick(1)  # tick() is what updates max_profit_ever
    assert "profit_10k" in module.achievement_ids_earned()
    assert "profit_100k" not in module.achievement_ids_earned()
    module.total_profit = 100_000
    game_env.tick(1)
    assert "profit_100k" in module.achievement_ids_earned()
    # Spending back down (e.g. buying automation) shouldn't lose either.
    module.total_profit = 0
    assert "profit_10k" in module.achievement_ids_earned()
    assert "profit_100k" in module.achievement_ids_earned()


def test_diversified_trader_requires_every_home_system_good_sold_once(game_env):
    module = game_env.module
    game_env.load(ship_id="1")
    game_env.depart("verdant", ship_id="1")
    game_env.tick(module.TRAVEL_TICKS)
    assert "diversified_trader" not in module.achievement_ids_earned()
    _sell_all_home_system_goods(game_env)
    assert "diversified_trader" in module.achievement_ids_earned()


def test_market_recovery_requires_a_crash_and_then_recovery_of_the_same_good(game_env):
    module = game_env.module
    for _ in range(50):
        module.apply_market_sale("ore", 10)
    assert module.market_multiplier["ore"] < module.MARKET_CRASH_THRESHOLD
    assert module.market_crash_ever["ore"] is True
    assert "market_recovery" not in module.achievement_ids_earned()
    module.market_multiplier["ore"] = 0.95  # simulate recovery
    assert "market_recovery" in module.achievement_ids_earned()


def test_endgame_reached_achievement(game_env):
    module = game_env.module
    assert "endgame_reached" not in module.achievement_ids_earned()
    _meet_endgame_criteria(game_env)
    game_env.tick(1)
    assert "endgame_reached" in module.achievement_ids_earned()


def test_background_galaxy_maxed_achievement(game_env):
    module = game_env.module
    _meet_endgame_criteria(game_env)
    game_env.tick(1)
    assert "background_galaxy_maxed" not in module.achievement_ids_earned()
    module.ticks_since_endgame = 10_000  # far past the cap
    assert "background_galaxy_maxed" in module.achievement_ids_earned()


# --- checking achievements never mutates other game state --------------

def test_checking_achievements_does_not_mutate_state(game_env):
    module = game_env.module
    game_env.load(ship_id="1")
    game_env.depart("verdant", ship_id="1")
    game_env.tick(module.TRAVEL_TICKS)
    before = module.get_state()
    module.achievement_ids_earned()
    module.achievements_summary()
    after = module.get_state()
    before.pop("achievements_earned", None)
    after.pop("achievements_earned", None)
    assert before == after


# --- progress readouts ---------------------------------------------------

def test_progress_readout_for_profit_10k(game_env):
    module = game_env.module
    module.total_profit = 2500
    game_env.tick(1)
    summary = {entry["id"]: entry for entry in module.achievements_summary()}
    assert summary["profit_10k"]["progress"] == (2500, module.PROFIT_10K_THRESHOLD)


def test_progress_readout_for_diversified_trader(game_env):
    module = game_env.module
    game_env.load(ship_id="1")
    game_env.depart("verdant", ship_id="1")
    game_env.tick(module.TRAVEL_TICKS)
    summary = {entry["id"]: entry for entry in module.achievements_summary()}
    assert summary["diversified_trader"]["progress"] == (1, len(module.HOME_SYSTEM_GOODS))


# --- toggle/panel ----------------------------------------------------------

def test_achievements_panel_hidden_by_default(game_env):
    assert game_env.elements["achievements-panel"].hidden is True


def test_toggle_opens_and_closes_panel(game_env):
    game_env.toggle_achievements()
    assert game_env.elements["achievements-panel"].hidden is False
    game_env.toggle_achievements()
    assert game_env.elements["achievements-panel"].hidden is True


def test_panel_renders_every_catalog_entry_plus_hub_link(game_env):
    module = game_env.module
    game_env.toggle_achievements()
    panel = game_env.elements["achievements-panel"]
    assert len(panel.children) == len(module.ACHIEVEMENTS) + 1


def test_panel_marks_earned_card_distinctly(game_env):
    module = game_env.module
    game_env.load(ship_id="1")
    game_env.depart("verdant", ship_id="1")
    game_env.tick(module.TRAVEL_TICKS)
    game_env.toggle_achievements()
    panel = game_env.elements["achievements-panel"]
    earned_cards = [c for c in panel.children if "achievement-card--earned" in c.className]
    assert len(earned_cards) == 1


def test_toggle_button_shows_earned_count(game_env):
    module = game_env.module
    game_env.load(ship_id="1")
    game_env.depart("verdant", ship_id="1")
    game_env.tick(module.TRAVEL_TICKS)
    game_env.toggle_achievements()
    text = game_env.elements["achievements-toggle-button"].innerText
    assert "1/" in text


def test_panel_stays_live_across_render(game_env):
    module = game_env.module
    game_env.toggle_achievements()
    game_env.load(ship_id="1")
    game_env.depart("verdant", ship_id="1")
    game_env.tick(module.TRAVEL_TICKS)  # render() runs inside tick()
    text = game_env.elements["achievements-toggle-button"].innerText
    assert "1/" in text


# --- unlock toast ----------------------------------------------------------

def test_toast_hidden_before_any_unlock(game_env):
    assert game_env.elements["achievement-toast"].hidden is True


def test_toast_shows_on_first_unlock(game_env):
    module = game_env.module
    game_env.load(ship_id="1")
    game_env.depart("verdant", ship_id="1")
    game_env.tick(module.TRAVEL_TICKS)
    toast = game_env.elements["achievement-toast"]
    assert toast.hidden is False
    assert "First Contract" in toast.innerText


def test_toast_auto_hides_after_timeout(game_env):
    module = game_env.module
    game_env.load(ship_id="1")
    game_env.depart("verdant", ship_id="1")
    game_env.tick(module.TRAVEL_TICKS)
    assert game_env.elements["achievement-toast"].hidden is False
    game_env.timers.flush()
    assert game_env.elements["achievement-toast"].hidden is True


def test_loading_a_save_with_earned_achievements_does_not_flood_toasts(game_env):
    module = game_env.module
    game_env.load(ship_id="1")
    game_env.depart("verdant", ship_id="1")
    game_env.tick(module.TRAVEL_TICKS)
    game_env.timers.flush()  # dismiss the first-sale toast
    saved = module.get_state()
    assert "first_sale" in saved["achievements_earned"]

    module.load_state(saved)
    assert game_env.elements["achievement-toast"].hidden is True
