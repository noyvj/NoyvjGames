"""J21 -- "trade empire legacy": found a new corporation after the endgame."""

import json


def _endgame(module):
    module.endgame_reached = True


def _expand(module):
    module.unlocked_research.add("galaxy_expansion")
    for colony_id in module.EXPANSION_COLONIES:
        module.colony_states[colony_id] = module.ColonyState(colony_id)


def test_not_available_before_the_endgame(game_env):
    module = game_env.module
    assert module.can_found_new_corporation() is False
    assert module.found_new_corporation() is False
    assert module.legacy_level == 0


def test_button_appears_only_once_the_endgame_is_reached(game_env):
    module = game_env.module
    module.render()
    assert game_env.elements["found-new-corporation-button"].hidden is True
    _endgame(module)
    module.render()
    assert game_env.elements["found-new-corporation-button"].hidden is False
    assert "Legacy" in game_env.elements["legacy-display"].innerText


def test_founding_resets_the_world_but_keeps_and_raises_the_legacy(game_env):
    module = game_env.module
    _expand(module)
    _endgame(module)
    module.total_profit = 123456
    module.research_points = 999
    module.ships["1"].automated = True
    assert module.found_new_corporation() is True
    assert module.legacy_level == 1
    assert module.endgame_reached is False
    assert module.total_profit == module.legacy_starting_credits() == module.LEGACY_STARTING_CREDITS
    assert module.research_points != 999
    assert "galaxy_expansion" not in module.unlocked_research
    assert not any(cid in module.colony_states for cid in module.EXPANSION_COLONIES)
    assert module.ships["1"].automated is False


def test_legacy_stacks_to_the_cap_then_stops(game_env):
    module = game_env.module
    for expected in range(1, module.LEGACY_MAX_LEVEL + 1):
        _endgame(module)
        assert module.found_new_corporation() is True
        assert module.legacy_level == expected
    _endgame(module)
    assert module.can_found_new_corporation() is False
    assert module.found_new_corporation() is False
    assert module.legacy_level == module.LEGACY_MAX_LEVEL


def test_the_sale_bonus_scales_with_the_level(game_env):
    module = game_env.module
    assert module.legacy_sale_multiplier() == 1.0
    module.legacy_level = 3
    assert abs(module.legacy_sale_multiplier() - (1.0 + 3 * module.LEGACY_SALE_BONUS)) < 1e-9


def test_a_sale_pays_more_at_a_higher_legacy_level(game_env):
    module = game_env.module

    def one_trip_profit():
        before = module.total_profit
        game_env.load(ship_id="1")
        game_env.depart("verdant", ship_id="1")
        game_env.tick(module.TRAVEL_TICKS)
        profit = module.total_profit - before
        # Return the ship to its start so the second trip is identical.
        game_env.load(ship_id="1")
        game_env.depart("ferrum", ship_id="1")
        game_env.tick(module.TRAVEL_TICKS)
        return profit

    module.legacy_level = 0
    base = one_trip_profit()
    module.legacy_level = 5
    boosted = one_trip_profit()
    assert base > 0 and boosted > base


def test_earned_achievements_carry_over_and_the_new_one_is_earned(game_env):
    module = game_env.module
    module.total_profit = 1000
    module.automate_ship("1")
    assert "first_automation" in module.achievement_ids_earned()
    _endgame(module)
    module.found_new_corporation()
    earned = module.achievement_ids_earned()
    assert "first_automation" in earned  # carried by the legacy, though the ship is gone
    assert module.ships["1"].automated is False
    assert "new_corporation" in earned


def test_carried_achievements_do_not_all_toast_again(game_env):
    module = game_env.module
    module.total_profit = 1000
    module.automate_ship("1")
    _endgame(module)
    module.found_new_corporation()
    toast_text = game_env.elements["achievement-toast"].innerText
    assert "A New Beginning" in toast_text
    assert "First" not in toast_text.replace("Beginning", "")


def test_legacy_round_trips_through_a_save(game_env):
    module = game_env.module
    _endgame(module)
    module.found_new_corporation()
    saved = json.loads(json.dumps(module.get_state()))
    assert saved["legacy"]["level"] == 1
    module.legacy_level, module.legacy_achievements = 0, []
    assert module.load_state(saved) is True
    assert module.legacy_level == 1


def test_a_first_run_save_has_no_legacy_key(game_env):
    assert "legacy" not in game_env.module.get_state()


def test_loading_a_save_without_legacy_resets_it(game_env):
    module = game_env.module
    module.legacy_level, module.legacy_achievements = 3, ["first_sale"]
    saved = module.get_state()
    saved.pop("legacy", None)
    module.load_state(saved)
    assert module.legacy_level == 0 and module.legacy_achievements == []


def test_a_tampered_legacy_field_is_clamped_and_filtered(game_env):
    module = game_env.module
    saved = module.get_state()
    saved["legacy"] = {"level": 99, "achievements": ["first_sale", "not_real", 7, "first_sale"]}
    module.load_state(saved)
    assert module.legacy_level == module.LEGACY_MAX_LEVEL
    assert module.legacy_achievements == ["first_sale"]
    saved["legacy"] = {"level": True, "achievements": "junk"}
    module.load_state(saved)
    assert module.legacy_level == 0 and module.legacy_achievements == []
    saved["legacy"] = "nope"
    module.load_state(saved)
    assert module.legacy_level == 0


def test_loading_an_unexpanded_save_drops_expansion_colonies_left_from_before(game_env):
    module = game_env.module
    fresh = module.get_state()
    _expand(module)
    assert all(cid in module.colony_states for cid in module.EXPANSION_COLONIES)
    module.load_state(fresh)
    assert not any(cid in module.colony_states for cid in module.EXPANSION_COLONIES)


def test_summary_shows_the_legacy_line(game_env):
    module = game_env.module
    module.legacy_level = 2
    game_env.elements["summary-toggle-button"].dispatch("click", None)
    text = " ".join(c.innerText for c in game_env.elements["summary-panel"].children)
    assert "Legacy level 2/" in text
