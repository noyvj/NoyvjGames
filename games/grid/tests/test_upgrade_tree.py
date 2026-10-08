"""GC-2b / GC-1: the career is an upgrade tree (shared/skill_tree.py): the four original perks are the
first nodes, Projects are deterministic named modifiers (the replacement for the declined card draw),
and the Starting loadout branch lets a run begin with one chosen option."""
import json

import skill_tree

from .test_career import _install_storage, _play


def _buy(g, *nodes, points=60):
    g.career["points"] = points
    for node in nodes:
        assert g.unlock_career_perk(node), node
    g._sync_perks()


# --- the tree itself -----------------------------------------------------------------------------

def test_the_tree_is_valid_and_keeps_the_four_original_perks_as_first_nodes(game_env):
    g = game_env.module
    assert skill_tree.validate(g.CAREER_TREE) == []
    for old in ("seed_capital", "crew_training", "storage_partners", "demand_analytics"):
        node = g.CAREER_UNLOCKS[old]
        assert node["branch"] == "operations" and node["requires"] == []
    assert {n["branch"] for n in g.CAREER_TREE["nodes"]} == {"operations", "projects", "loadout", "meteorology"}
    assert g.CAREER_UNLOCK_ORDER[:4] == ["seed_capital", "crew_training", "storage_partners", "demand_analytics"]
    assert set(g.LOADOUT_NODES) == {"old_coal_contract", "storage_startup", "diplomatic_immunity"}


def test_there_are_no_random_draws_in_the_tree(game_env):
    """Deterministic by construction: every node has a fixed cost and effect text, and buying twice is refused."""
    g = game_env.module
    _install_storage()
    g.career["points"] = 40
    assert g.unlock_career_perk("wind_sites") is True
    assert g.unlock_career_perk("wind_sites") is False
    assert g.unlock_career_perk("no_such_node") is False


def test_prerequisites_gate_purchases(game_env):
    g = game_env.module
    _install_storage()
    g.career["points"] = 40
    assert g.unlock_career_perk("rd_grant") is False       # needs both site leases
    assert g.unlock_career_perk("wind_sites") is True
    assert g.unlock_career_perk("rd_grant") is False
    assert g.unlock_career_perk("solar_sites") is True
    assert g.unlock_career_perk("rd_grant") is True
    assert g.unlock_career_perk("long_range_outlook") is False
    assert "needs Wind site leases" not in g.career_perk_progress_text("long_range_outlook")
    assert "needs Weather station first" in g.career_perk_progress_text("long_range_outlook")


def test_old_careers_still_load_and_overspent_ones_are_trimmed(game_env):
    g = game_env.module
    old = {"runs": 2, "points": 8, "unlocked": ["seed_capital", "crew_training"]}
    career = g.validate_career(old)
    assert career["unlocked"] == ["seed_capital", "crew_training"] and career["loadout"] is None
    overspent = g.validate_career({"runs": 1, "points": 3, "unlocked": ["seed_capital", "crew_training", "rd_grant"]})
    assert overspent["unlocked"] == ["seed_capital"]
    junk = g.validate_career({"points": 50, "unlocked": ["rd_grant", "nope", 5, "seed_capital", "seed_capital"]})
    assert junk["unlocked"] == ["seed_capital"]  # rd_grant lacks its prerequisites, repeats and junk dropped
    assert g.validate_career({"points": 9, "unlocked": ["storage_startup"], "loadout": "old_coal_contract"})["loadout"] is None
    assert g.validate_career({"points": 9, "unlocked": ["storage_startup"], "loadout": "storage_startup"})["loadout"] == "storage_startup"


def test_career_panel_text_summarises_the_tree(game_env):
    g = game_env.module
    _install_storage()
    g.career["points"] = 5
    g.unlock_career_perk("wind_sites")
    game_env.toggle_career()
    text = game_env.elements["career-tree-summary"].innerText
    assert "2 career points to spend (5 earned in all)" in text and "1 of 14 upgrades owned" in text


# --- GC-1 projects -------------------------------------------------------------------------------

def test_site_leases_and_storage_subsidy_cut_build_costs(game_env):
    g = game_env.module
    s = game_env.state
    base = {t: s.plant_cost(t) for t in g.PLANT_TYPES}
    _buy(g, "wind_sites", "solar_sites", "storage_subsidy")
    assert abs(s.plant_cost("wind") - base["wind"] * 0.85) < 1e-9
    assert abs(s.plant_cost("solar") - base["solar"] * 0.85) < 1e-9
    assert abs(s.plant_cost("battery") - base["battery"] * 0.8) < 1e-9
    assert s.plant_cost("hydro") == base["hydro"] and s.plant_cost("coal") == base["coal"]


def test_projects_never_open_a_build_and_retire_exploit(game_env):
    g = game_env.module
    s = game_env.state
    _buy(g, "wind_sites", "solar_sites", "storage_subsidy", "rd_grant", "policy_liaison")
    s.funds = 100000
    s.policy_lever_available = True
    s.enact_policy("renewable_subsidy")
    for plant in ("wind", "solar", "battery", "hydro"):
        for _ in range(60):
            before = s.funds
            assert s.build_plant(plant)
            assert s.retire_plant(plant)
            assert s.funds < before, plant  # a build + retire cycle always loses money


def test_rd_grant_speeds_the_cost_curve(game_env):
    g = game_env.module
    s = game_env.state
    s.cumulative_built["wind"] = 5
    plain = s._learning_curve_cost("wind")
    _buy(g, "wind_sites", "solar_sites", "rd_grant")
    assert abs(s._learning_curve_cost("wind") - 70 * 0.94 ** 5) < 1e-9
    assert s._learning_curve_cost("wind") < plain
    s.cumulative_built["wind"] = 500
    assert s._learning_curve_cost("wind") == 70 * g.MIN_COST_MULTIPLIER  # the floor is unchanged


def test_policy_liaison_deepens_and_extends_the_renewable_subsidy(game_env):
    g = game_env.module
    s = game_env.state
    _buy(g, "wind_sites", "policy_liaison")
    s.policy_lever_available = True
    assert s.enact_policy("renewable_subsidy")
    assert s.active_policy["rounds_remaining"] == g.POLICY_LEVER_DURATION + 2
    assert abs(s.plant_cost("hydro") - 150 * 0.70) < 1e-9
    s.active_policy = None
    s.policy_lever_available = True
    s.enact_policy("carbon_pricing")
    assert s.active_policy["rounds_remaining"] == g.POLICY_LEVER_DURATION  # carbon pricing is not stretched


def test_a_run_in_progress_keeps_its_rules_until_the_next_run(game_env):
    g = game_env.module
    _install_storage()
    s = game_env.state
    s.build_plant("coal")
    g.career["points"] = 5
    g.unlock_career_perk("wind_sites")
    assert "wind_sites" not in s.perks
    g.career["points"] = 20
    _play(game_env, 5)
    g.finish_run()
    assert "wind_sites" in game_env.state.perks


def test_an_unstarted_run_picks_up_a_new_node_at_once(game_env):
    g = game_env.module
    _install_storage()
    g.career["points"] = 3
    g.unlock_career_perk("seed_capital")
    assert game_env.state.funds == g.STARTING_FUNDS + g.SEED_CAPITAL_BONUS


# --- GC-2b loadouts ------------------------------------------------------------------------------

def test_loadout_needs_its_node_and_an_unstarted_run(game_env):
    g = game_env.module
    s = game_env.state
    assert g.set_loadout("old_coal_contract") is False
    _buy(g, "old_coal_contract", "storage_startup")
    assert g.set_loadout("old_coal_contract") is True
    assert s.plant_counts["coal"] == 2 and s.plant_age["coal"] == 4.0
    assert g.set_loadout("diplomatic_immunity") is False   # not owned
    assert g.set_loadout("seed_capital") is False          # not a loadout
    s.build_plant("gas")
    assert s.set_start_option(None) is False                # the run has started


def test_switching_loadouts_resets_to_the_scenario_baseline(game_env):
    g = game_env.module
    s = game_env.state
    _buy(g, "old_coal_contract", "storage_startup")
    g.set_loadout("old_coal_contract")
    g.set_loadout("storage_startup")
    assert s.plant_counts["coal"] == 0 and s.plant_counts["battery"] == 1 and s.plant_age["coal"] == 0
    g.set_loadout(None)
    assert sum(s.plant_counts.values()) == 0 and s.funds == g.STARTING_FUNDS


def test_loadout_stacks_on_a_scenario_start(game_env):
    g = game_env.module
    s = game_env.state
    _buy(g, "old_coal_contract")
    assert s.apply_scenario("coal_legacy")
    g.set_loadout("old_coal_contract")
    assert s.plant_counts["coal"] == 4 + 2 and s.plant_counts["gas"] == 1
    assert abs(s.plant_age["coal"] - 4.0 * 2 / 6) < 1e-9


def test_diplomatic_immunity_waives_only_the_first_disruption(game_env):
    g = game_env.module
    s = game_env.state
    _buy(g, "diplomatic_immunity")
    g.set_loadout("diplomatic_immunity")
    assert s.immunity_available is True
    s.plant_counts["coal"] = 3
    s.emissions = 1500.0
    s.advance_round(rng=lambda: 0.0, age_rng=lambda: 1.0)
    assert s.last_event is None and s.immunity_available is False and s.immunity_used is True
    assert s.last_round_recap["immunity"] is True
    assert s.current_clean_streak == 1
    s.advance_round(rng=lambda: 0.0, age_rng=lambda: 1.0)
    assert s.last_event is not None  # the second one hits


def test_loadout_is_remembered_for_the_next_run(game_env):
    g = game_env.module
    _install_storage()
    _buy(g, "storage_startup")
    g.set_loadout("storage_startup")
    _play(game_env, 5)
    g.finish_run()
    s = game_env.state
    assert s.start_option == "storage_startup" and s.plant_counts["battery"] == 1
    assert g.career["loadout"] == "storage_startup"


def test_loadout_select_in_the_ui(game_env):
    g = game_env.module
    el = game_env.elements
    g.render()
    assert el["start-option-select"].disabled is True
    assert "No loadout bought yet" in el["start-option-note"].innerText
    _buy(g, "storage_startup")
    g.render()
    assert el["start-option-select"].disabled is False
    el["start-option-select"].value = "storage_startup"
    el["start-option-select"].dispatch("change", None)
    assert game_env.state.plant_counts["battery"] == 1
    assert "Storage Startup" in el["start-option-note"].innerText
    game_env.build("coal")
    assert el["start-option-select"].disabled is True
    el["start-option-select"].value = "none"
    el["start-option-select"].dispatch("change", None)
    assert el["start-option-select"].value == "storage_startup"  # locked once play began


def test_loadout_state_round_trips_through_a_save(game_env):
    g = game_env.module
    _buy(g, "diplomatic_immunity")
    g.set_loadout("diplomatic_immunity")
    data = json.loads(json.dumps(g.get_state()))
    assert data["start_option"] == "diplomatic_immunity" and data["immunity_available"] is True
    g.load_state(dict(data, start_option="not-a-loadout", immunity_available=True))
    assert game_env.state.start_option is None and game_env.state.immunity_available is False
