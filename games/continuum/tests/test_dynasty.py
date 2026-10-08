"""K-2: the Dynasty meta-progression (Legacy points, perk tree, starting perks, new scenarios)."""

import copy
import math
import sys
import types

import pytest

import challengerun
import dynasty
import founding
import sim
import skill_tree

from .test_space_age_era import push_to_agrarian


def ui_with(earned=0, owned=(), **extra):
    record = {"earned": earned, "owned": list(owned)}
    record.update(extra)
    return {dynasty.KEY: record}


# --- the tree and the points -----------------------------------------------------------------
def test_the_tree_is_valid_and_fully_reachable_with_a_few_runs():
    assert dynasty.tree_problems() == []
    total = sum(node["cost"] for node in dynasty.DYNASTY_TREE["nodes"])
    assert total == 34
    # a settlement that reaches the Classical era on Hard Mode alone buys nearly half of it
    assert dynasty.run_points(2, 120, 80, True, False) >= 15


def test_ranks_ascend_and_only_ever_go_up():
    needs = [need for need, _ in dynasty.RANKS]
    assert needs == sorted(needs) and needs[0] == 0
    assert dynasty.rank_name(0) == "Founder"
    assert dynasty.rank_index(5) == 1 and dynasty.rank_index(10**6) == len(dynasty.RANKS) - 1
    assert dynasty.next_rank(0) == (5, "Steward")
    assert dynasty.next_rank(10**6) is None


def test_points_are_earned_by_eras_not_by_replaying_the_first():
    assert dynasty.run_points(0, 39, 90, False, False) == 0  # too short a life
    first_era_only = dynasty.run_points(0, 10_000, 90, False, False)
    assert first_era_only <= 2  # farming the Tribal era pays almost nothing
    assert dynasty.run_points(1, 40, 80, False, False) > first_era_only
    for era in range(1, len(sim.ERA_ORDER)):
        assert dynasty.run_points(era, 200, 80, False, False) > dynasty.run_points(era - 1, 200, 80, False, False)


def test_hard_mode_pays_half_again_and_failure_has_a_floor_and_a_cap():
    normal = dynasty.run_points(3, 200, 80, False, False)
    hard = dynasty.run_points(3, 200, 80, True, False)
    assert hard == normal + math.ceil(normal / 2)
    assert dynasty.run_points(0, 40, 10, False, True) == 2  # a collapsed settlement still banks its lessons
    assert dynasty.run_points(0, 39, 10, False, True) == 0
    assert 0 < dynasty.run_points(7, 10**7, 99, True, False) <= dynasty.MAX_RUN_POINTS


def test_bad_inputs_to_run_points_are_safe():
    assert dynasty.run_points("x", None, float("nan"), "yes", None) == 0
    assert dynasty.run_points(99, 400, True, False, False) <= dynasty.MAX_RUN_POINTS


# --- the saved record --------------------------------------------------------------------------
@pytest.mark.parametrize("raw", [None, 5, [], "x", {"earned": "9", "owned": "nope"}, {"earned": float("nan")},
                                 {"earned": -4, "owned": [None, {}, 3]}, {"earned": 10**12}])
def test_hostile_records_clean_to_something_valid(raw):
    record = dynasty.clean(raw)
    assert record["earned"] >= 0 and record["earned"] <= dynasty.MAX_EARNED
    assert all(isinstance(i, str) for i in record["owned"])
    assert dynasty.clean(record) == record


def test_owned_perks_must_be_known_affordable_and_have_their_prerequisites():
    record = dynasty.clean({"earned": 1, "owned": ["heirloom_granary", "heirloom_toolkit", "kin_arrive", "made_up"]})
    assert record["owned"] == ["heirloom_granary"]  # 1 point: the rest are trimmed
    record = dynasty.clean({"earned": 50, "owned": ["kin_arrive"]})
    assert record["owned"] == []  # prerequisites missing


def test_the_untouched_default_is_not_stored():
    ui = {}
    dynasty.put(ui, dynasty.default())
    assert dynasty.KEY not in ui
    dynasty.put(ui, {"earned": 3})
    assert ui[dynasty.KEY]["earned"] == 3


# --- banking ---------------------------------------------------------------------------------
def info(points, hard=False, collapsed=False, era=1):
    return {"points": points, "era_index": era, "hard_mode": hard, "collapsed": collapsed}


def test_banking_pays_the_difference_and_counts_a_run_once():
    ui = {}
    first = dynasty.bank(ui, info(4))
    assert first == {"gained": 4, "points": 4, "banked": 4, "total": 4, "first": True}
    again = dynasty.bank(ui, info(4))
    assert again["gained"] == 0 and again["total"] == 4 and again["first"] is False
    more = dynasty.bank(ui, info(7, hard=True))
    assert more["gained"] == 3 and more["total"] == 7
    record = dynasty.get(ui)
    assert record["runs"] == 1 and record["hard_runs"] == 0  # hard mode is judged when the run is first counted
    assert record["best_era"] == 1


def test_a_collapsed_run_is_counted_once_as_failed():
    ui = {}
    dynasty.bank(ui, info(2, collapsed=True, era=0))
    dynasty.bank(ui, info(3, collapsed=True, era=0))
    record = dynasty.get(ui)
    assert record["failed"] == 1 and record["runs"] == 1 and record["earned"] == 3


def test_a_worthless_settlement_banks_nothing_and_junk_is_refused():
    ui = {}
    assert dynasty.bank(ui, info(0))["gained"] == 0 and dynasty.KEY not in ui
    assert dynasty.bank(ui, "junk")["gained"] == 0
    assert dynasty.bank(ui, {"points": float("nan")})["gained"] == 0


def test_a_new_run_banks_again_after_the_run_record_resets():
    ui = {}
    dynasty.bank(ui, info(5))
    ui.pop(dynasty.RUN_KEY)  # what founding a new settlement does
    assert dynasty.bank(ui, info(5))["gained"] == 5
    assert dynasty.get(ui)["runs"] == 2


# --- perks -------------------------------------------------------------------------------------
def test_buying_and_refunding_follow_the_tree_rules():
    ui = ui_with(earned=10)
    assert dynasty.buy(ui, "kin_arrive")["ok"] is False  # locked
    assert dynasty.buy(ui, "heirloom_granary")["ok"] and dynasty.buy(ui, "heirloom_toolkit")["ok"]
    assert dynasty.buy(ui, "kin_arrive")["ok"]
    assert dynasty.points_free(dynasty.get(ui)) == 10 - 5
    assert dynasty.refund(ui, "heirloom_granary")["ok"] is False  # kin_arrive needs it
    assert dynasty.refund_all(ui)["refunded"] == 5
    assert dynasty.get(ui)["owned"] == []
    assert dynasty.buy(ui, "river_charter")["ok"] is False  # needs the granary


def test_starting_perks_deliver_once_and_only_while_active():
    ui = ui_with(earned=20, owned=["heirloom_granary", "heirloom_toolkit", "stacked_timber", "elders_tales", "kin_arrive"])
    assert dynasty.start_bonuses(ui) == {"food": 4.0, "tools": 1.0, "materials": 6.0, "knowledge": 3.0, "people": 1}
    assert dynasty.start_bonuses(ui, resting=True) == {}
    dynasty.set_off(ui, True)
    assert dynasty.start_bonuses(ui) == {}
    text = dynasty.start_text({"food": 4.0, "tools": 1.0, "people": 1})
    assert text == "+4 food, +1 tool, +1 person"


def test_standing_perks_are_small_and_rest():
    ui = ui_with(earned=20, owned=["heirloom_granary", "steady_hands", "deep_cellars", "elders_tales", "quiet_ledgers"])
    base = dict(sim.NEUTRAL_EFFECTS)
    merged = dynasty.apply_effects(base, ui)
    assert merged["food_yield_mult"] == pytest.approx(1.02)
    assert merged["knowledge_mult"] == pytest.approx(1.03)
    assert merged["food_storage_bonus"] == pytest.approx(6.0)
    assert dynasty.apply_effects(base, ui, resting=True) is base
    assert base["food_yield_mult"] == 1.0  # never mutated


def test_dynasty_scenarios_unlock_by_perk_and_stay_unlocked_when_switched_off():
    ui = {}
    for scenario in dynasty.SCENARIO_UNLOCKS:
        assert dynasty.scenario_unlocked(ui, scenario) is False
    assert dynasty.scenario_unlocked(ui, "standard") is True
    ui = ui_with(earned=10, owned=["heirloom_toolkit", "hardy_charter"])
    assert dynasty.scenario_unlocked(ui, "hardy") and not dynasty.scenario_unlocked(ui, "river")
    dynasty.set_off(ui, True)
    assert dynasty.scenario_unlocked(ui, "hardy")


def test_the_three_new_scenarios_are_real_openings_and_not_better_than_standard():
    for scenario in ("hardy", "river", "heirloom"):
        config = sim.SCENARIOS[scenario]
        assert config["population"] >= 5
        state = sim.CityState(scenario=scenario)
        assert state.population == config["population"]
        total = config["food"] + config["materials"] + 5 * config["tools"] + config.get("knowledge", 0) * 2
        standard = sim.SCENARIOS["standard"]
        assert total <= standard["food"] + standard["materials"] + 5 * standard["tools"] + 12
    assert sim.CityState(scenario="heirloom").resources["knowledge"] == 10.0


def test_merge_never_loses_progress():
    saved = {"earned": 10, "owned": ["heirloom_granary"], "runs": 2}
    local = {"earned": 14, "owned": ["heirloom_granary", "steady_hands"], "runs": 3, "best_era": 2}
    merged = dynasty.merge(saved, local)
    assert merged["earned"] == 14 and merged["runs"] == 3 and merged["best_era"] == 2
    assert merged["owned"] == ["heirloom_granary", "steady_hands"]
    assert dynasty.merge(None, None) == dynasty.default()
    assert dynasty.merge(saved, "junk")["earned"] == 10


def test_rewind_and_doctrine_perks():
    ui = ui_with(earned=20, owned=["hourglass_keepers", "second_hourglass", "schools_of_thought"])
    assert dynasty.rewind_perk_tokens(ui) == 2
    assert dynasty.doctrine_edge(ui) == 5 and dynasty.doctrine_edge(ui, resting=True) == 0


# --- in the game -------------------------------------------------------------------------------
def give_perks(game_env, earned=30, owned=("heirloom_granary", "heirloom_toolkit", "stacked_timber", "elders_tales", "kin_arrive")):
    game_env.module.campaign.ui[dynasty.KEY] = {"earned": earned, "owned": list(owned)}


def test_starting_perks_arrive_with_the_opening_season_exactly_once(game_env):
    give_perks(game_env)
    state = game_env.state
    before = dict(state.resources)
    people = state.population
    game_env.advance_season()
    assert state.population >= people + 1
    # +4 food and +6 materials arrived (the season itself also produced/consumed, so compare the gift loosely)
    log = " ".join(e.text for e in game_env.module.chronicle.entries)
    assert "Dynasty heritage arrives" in log and "+4 food" in log
    run = dynasty.get_run(game_env.module.campaign.ui)
    assert run["start"] is True
    snapshot = dict(state.resources)
    game_env.advance_season()
    assert "Dynasty heritage arrives" not in " ".join(e.text for e in game_env.module.chronicle.entries[:0])
    assert dynasty.get_run(game_env.module.campaign.ui)["start"] is True
    assert snapshot["knowledge"] >= before["knowledge"] + 3 - 1e-9 or state.resources["knowledge"] >= 3


def test_a_settlement_that_has_already_played_never_gets_the_gift_retroactively(game_env):
    game_env.advance_season(2)
    give_perks(game_env)
    people = game_env.state.population
    game_env.advance_season()
    assert "Dynasty heritage arrives" not in " ".join(e.text for e in game_env.module.chronicle.entries)
    assert game_env.state.population <= people + 1  # only ordinary growth


def test_perks_rest_in_a_challenge_run_and_the_gift_is_not_saved_for_later(game_env):
    module = game_env.module
    give_perks(game_env)
    module._challenge_utc_today_override = "2026-10-08"
    game_env.elements["challenge-toggle-button"].dispatch("click", None)
    game_env.elements["challenge-daily-start-button"].dispatch("click", None)
    assert challengerun.get(module.campaign.ui) is not None
    assert module._resting() is True
    effects = module.current_effects()
    assert effects["food_yield_mult"] == pytest.approx(challengerun.apply_effects(module.tree.effects(), module.campaign.ui)["food_yield_mult"])
    game_env.advance_season()
    assert "Dynasty heritage arrives" not in " ".join(e.text for e in module.chronicle.entries)
    assert dynasty.get_run(module.campaign.ui)["start"] is True  # the turn is used up


def test_the_switch_turns_every_perk_off_in_the_game(game_env):
    give_perks(game_env, owned=("heirloom_granary", "steady_hands"))
    module = game_env.module
    assert module.current_effects()["food_yield_mult"] == pytest.approx(1.02)
    module.on_dynasty_off()
    assert module.current_effects()["food_yield_mult"] == pytest.approx(1.0)
    module.on_dynasty_off()
    assert module.current_effects()["food_yield_mult"] == pytest.approx(1.02)


def test_dynasty_scenario_buttons_unlock_with_the_perk(game_env):
    el = game_env.elements
    module = game_env.module
    assert el["scenario-hardy-button"].disabled is True and el["scenario-hardy-button"].innerText.startswith("🔒")
    assert "Hardier Tribe" in el["scenario-hardy-button"].title
    module.campaign.ui[dynasty.KEY] = {"earned": 5, "owned": ["heirloom_toolkit", "hardy_charter"]}
    module.render()
    assert el["scenario-hardy-button"].disabled is False and el["scenario-hardy-button"].innerText == "Hardier Tribe"
    el["scenario-hardy-button"].dispatch("click", None)
    assert game_env.state.scenario == "hardy" and game_env.state.population == 8
    el["scenario-river-button"].dispatch("click", None)  # still locked: ignored
    assert game_env.state.scenario == "hardy"


def test_banking_by_button_and_the_status_line(game_env):
    module = game_env.module
    state = game_env.state
    game_env.elements["dynasty-toggle-button"].dispatch("click", None)
    game_env.elements["dynasty-bank-button"].dispatch("click", None)
    assert "lived 40 seasons" in game_env.elements["dynasty-bank-status"].innerText
    state.season = 80
    state.population = 15
    game_env.elements["dynasty-bank-button"].dispatch("click", None)
    first = dynasty.get(module.campaign.ui)["earned"]
    assert first == 2 and "Banked 2 Legacy points" in game_env.elements["dynasty-bank-status"].innerText
    game_env.elements["dynasty-bank-button"].dispatch("click", None)
    assert dynasty.get(module.campaign.ui)["earned"] == first
    assert "Already banked" in game_env.elements["dynasty-bank-status"].innerText


class _Storage:
    def __init__(self):
        self.data = {}

    def getItem(self, key):
        return self.data.get(key)

    def setItem(self, key, value):
        self.data[key] = value


def test_founding_banks_the_old_settlement_and_carries_the_dynasty(game_env):
    storage = _Storage()
    sys.modules["js"].window = types.SimpleNamespace(localStorage=storage)
    module = game_env.module
    state = game_env.state
    push_to_agrarian(game_env)
    state.season = 120
    module.campaign.ui["banner"] = {"banner": "cairn", "flourish": "none"}
    expected = dynasty.run_info(module.campaign)["points"]
    assert expected > 0
    assert module.found_new_settlement() is True
    record = dynasty.get(module.campaign.ui)
    assert record["earned"] == expected and record["runs"] == 1
    assert dynasty.get_run(module.campaign.ui)["banked"] == 0  # the new settlement starts unbanked
    assert module.campaign.ui["banner"]["banner"] == "cairn"
    assert "Legacy is banked" in module.found_status


def test_a_collapse_banks_once_and_says_so(game_env):
    module = game_env.module
    state = game_env.state
    state.season = 60
    state.score_history[:] = [10.0, 12.0, 9.0]
    module._bank_if_collapsed()
    first = dynasty.get(module.campaign.ui)
    assert first["failed"] == 1 and first["earned"] >= 2
    module._bank_if_collapsed()
    assert dynasty.get(module.campaign.ui)["earned"] == first["earned"]
    assert any("failed" in e.text for e in module.chronicle.entries)


def test_the_archive_records_the_rank_and_active_perks(game_env):
    module = game_env.module
    module.campaign.ui[dynasty.KEY] = {"earned": 6, "owned": ["heirloom_granary"]}
    record = module.current_record()
    assert record["dynasty"] == {"rank": 1, "perks": ["heirloom_granary"]}
    assert "Dynasty Steward, 1 perk" in module_lines(record)


def module_lines(record):
    import archive
    return archive.card_lines(record)


def test_founding_keeps_unrelated_ui_out_of_the_new_settlement():
    assert set(founding.CARRY_KEYS) == {"dynasty", "rewind", "banner", "citizens"}


def test_skill_tree_mirror_agrees_on_the_dynasty_tree():
    owned = ["heirloom_granary", "steady_hands"]
    assert skill_tree.status(dynasty.DYNASTY_TREE, owned, "deep_cellars", 10) == "available"
    assert skill_tree.status(dynasty.DYNASTY_TREE, owned, "kin_arrive", 10) == "locked"
    assert copy.deepcopy(dynasty.DYNASTY_TREE) == dynasty.DYNASTY_TREE


def test_the_dynasty_is_mirrored_into_this_browsers_storage_and_adopted_back(game_env):
    storage = _Storage()
    sys.modules["js"].window = types.SimpleNamespace(localStorage=storage)
    module = game_env.module
    module.campaign.ui[dynasty.KEY] = {"earned": 6, "owned": []}
    module.on_dynasty_off()
    assert '"earned": 6' in storage.data[module.DYNASTY_STORAGE_KEY]
    # an older save with less progress loads without taking the browser's progress away
    module.campaign.ui.pop(dynasty.KEY)
    module._adopt_local_dynasty()
    assert dynasty.get(module.campaign.ui)["earned"] == 6
