"""K11 civic challenges, K19/K13/K25/K8 trajectory + reference line,
K2/K10/K21a small readouts, K21b research-tree expansion (Milestone 25)."""

import copy
import json
import math

import challenges
import research
import save
import sim
import sustainability
import trajectory


def fresh():
    return sim.CityState()


def report(**over):
    base = {
        "extraction": 10.0, "sustainable_yield": 26.0, "fed_fraction": 1.0, "deaths": 0,
        "pollution": 0.0, "sprawl": 0.0, "food_gathered": 8.0, "materials_gathered": 4.0,
        "tools_made": 1.0, "knowledge_made": 1.0,
    }
    base.update(over)
    return base


# --- K11 -------------------------------------------------------------------
def test_fresh_city_offers_only_meaningful_early_challenges():
    state = fresh()
    ids = challenges.offered(state, sim.NEUTRAL_EFFECTS)
    assert "everyone_fed" in ids and "score_climb" in ids
    assert "land_recovery" not in ids  # land is healthy
    assert "lean_harvest" not in ids   # no last season to measure against
    assert "quiet_industry" not in ids and "tight_growth" not in ids  # later eras


def test_start_and_abandon_and_only_one_at_a_time():
    state = fresh()
    assert challenges.start(state, sim.NEUTRAL_EFFECTS, "everyone_fed")
    assert not challenges.start(state, sim.NEUTRAL_EFFECTS, "score_climb")
    assert challenges.offered(state, sim.NEUTRAL_EFFECTS) == []
    assert challenges.status_text(state).startswith("Nobody Goes Hungry")
    assert challenges.abandon(state)
    assert not challenges.abandon(state)
    assert not challenges.start(state, sim.NEUTRAL_EFFECTS, "not_a_challenge")


def test_challenge_pass_awards_knowledge_and_counts():
    state = fresh()
    challenges.start(state, sim.NEUTRAL_EFFECTS, "everyone_fed")
    before = state.resources["knowledge"]
    event = None
    for i in range(challenges.CHALLENGES["everyone_fed"]["seasons"]):
        state.population += 1 if i == 0 else 0
        event = challenges.after_season(state, report(), sim.NEUTRAL_EFFECTS)
    assert event["kind"] == "passed"
    assert state.resources["knowledge"] == before + challenges.reward_for(state.era)
    assert state.challenge["completed"]["everyone_fed"] == 1
    assert state.challenge["active"] is None


def test_challenge_fails_without_penalty_when_constraint_breaks():
    state = fresh()
    state.last_report = report()
    state.last_extraction = 20.0
    assert challenges.start(state, sim.NEUTRAL_EFFECTS, "lean_harvest")
    before = dict(state.resources)
    event = challenges.after_season(state, report(extraction=19.0), sim.NEUTRAL_EFFECTS)
    assert event["kind"] == "failed"
    assert state.resources == before
    assert state.challenge["failed"] == 1 and state.challenge["active"] is None


def test_lean_harvest_passes_at_twenty_percent_less():
    state = fresh()
    state.last_report = report()
    state.last_extraction = 20.0
    challenges.start(state, sim.NEUTRAL_EFFECTS, "lean_harvest")
    event = None
    for _ in range(4):
        event = challenges.after_season(state, report(extraction=16.0), sim.NEUTRAL_EFFECTS)
    assert event["kind"] == "passed"


def test_final_goal_can_fail_after_the_window():
    state = fresh()
    challenges.start(state, sim.NEUTRAL_EFFECTS, "everyone_fed")
    event = None
    for _ in range(5):  # never grows past the baseline population
        event = challenges.after_season(state, report(), sim.NEUTRAL_EFFECTS)
    assert event["kind"] == "failed"


def test_era_gated_challenges_appear_in_their_era():
    state = fresh()
    state.era = "industrial"
    assert "quiet_industry" in challenges.offered(state, sim.NEUTRAL_EFFECTS)
    state.era = "digital"
    assert "tight_growth" in challenges.offered(state, sim.NEUTRAL_EFFECTS)


def test_clean_rejects_adversarial_challenge_saves():
    for bad in (None, 5, [], "x", {"active": 3}, {"active": {"id": "nope", "seasons_done": 0, "baseline": 1}}):
        assert challenges.clean(bad) == challenges.empty_state()
    got = challenges.clean({
        "active": {"id": "everyone_fed", "seasons_done": 99, "baseline": 3},  # out of window
        "completed": {"everyone_fed": -5, "bogus": 3, "score_climb": True},
        "failed": float("nan"),
    })
    assert got["active"] is None
    assert got["completed"] == {"everyone_fed": 0}
    assert got["failed"] == 0
    nan_baseline = challenges.clean({"active": {"id": "everyone_fed", "seasons_done": 1, "baseline": float("nan")}})
    assert nan_baseline["active"] is None
    good = challenges.clean({"active": {"id": "everyone_fed", "seasons_done": 2, "baseline": 7}})
    assert good["active"] == {"id": "everyone_fed", "seasons_done": 2, "baseline": 7.0}


def test_active_challenge_round_trips_through_a_save():
    campaign = save.Campaign()
    challenges.start(campaign.state, sim.NEUTRAL_EFFECTS, "score_climb")
    data = json.loads(json.dumps(campaign.to_dict()))
    other = save.Campaign()
    assert other.load_dict(data)
    assert other.state.challenge == campaign.state.challenge


def test_tampered_save_fields_load_safely():
    campaign = save.Campaign()
    data = campaign.to_dict()
    data["current_state"]["city"]["challenge"] = {"active": {"id": "everyone_fed", "seasons_done": "x", "baseline": None}}
    data["current_state"]["city"]["trajectory"] = [[1, 2], "x", [float("inf"), 0, 1, 1], [1.0, 99, 5.0, 500.0]]
    data["current_state"]["city"]["calm_streak"] = float("nan")
    other = save.Campaign()
    assert other.load_dict(data)
    assert other.state.challenge["active"] is None
    assert other.state.trajectory == [[1.0, 6.0, 5.0, 100.0]]
    assert other.state.calm_streak == 0


def test_game_ui_start_advance_and_log(game_env):
    game_env.elements["challenge-list"]  # panel exists
    game_env.module.challenges.start(game_env.state, sim.NEUTRAL_EFFECTS, "everyone_fed")
    game_env.module.render()
    assert "Nobody Goes Hungry" in game_env.elements["challenge-status-display"].innerText
    assert "1 active" in game_env.elements["challenges-summary"].innerText
    game_env.advance_season()
    assert game_env.state.challenge["active"]["seasons_done"] in (0, 1) or game_env.state.challenge["active"] is None


def test_game_accept_button_starts_a_challenge(game_env):
    game_env.elements["challenge-start-score_climb-button"].dispatch("click", None)
    assert game_env.state.challenge["active"]["id"] == "score_climb"
    game_env.elements["challenge-abandon-button"].dispatch("click", None)
    assert game_env.state.challenge["active"] is None


# --- K19 / K13 / K25 / K8 -----------------------------------------------------
def test_output_index_is_finite_and_guarded():
    assert trajectory.output_index(report(), 6) == (14.0 / 6) / sim.FOOD_PER_PERSON
    assert trajectory.output_index({"food_gathered": float("nan")}, 6) == 0.0
    assert trajectory.output_index(None, 6) == 0.0
    assert trajectory.output_index(report(), 0) > 0  # population floor of 1


def test_reference_curve_is_monotone_and_honest_about_gaps():
    values = [trajectory.reference_index(e) for e in sim.ERA_ORDER]
    assert values == sorted(values)
    assert trajectory.REFERENCE["tribal"][2] is False  # assumption, not data
    assert trajectory.REFERENCE["space"][2] is False   # no data at all
    assert "Maddison" in trajectory.SOURCE_NOTE and "no data" in trajectory.SOURCE_NOTE.lower()


def test_record_caps_history_and_svg_renders():
    state = fresh()
    for _ in range(trajectory.MAX_POINTS + 25):
        trajectory.record(state, report(), 60.0)
    assert len(state.trajectory) == trajectory.MAX_POINTS
    svg = trajectory.trajectory_svg(state.trajectory)
    assert svg.count("<polyline") == 2 and "nan" not in svg.lower()
    assert "<circle" in trajectory.scatter_svg(state.trajectory)
    assert trajectory.trajectory_svg([]) == "" and trajectory.scatter_svg([]) == ""


def test_svg_handles_a_single_point_and_extreme_values():
    pts = [[1e9, 0.0, 5.0, 50.0]]
    assert "polyline" in trajectory.trajectory_svg(pts)
    assert "nan" not in trajectory.trajectory_svg([[0.0, 6.0, 0.0, 0.0]]).lower()


def test_advancing_seasons_fills_the_charts_in_game(game_env):
    game_env.advance_season(3)
    assert len(game_env.state.trajectory) == 3
    assert "<polyline" in game_env.elements["trajectory-graph"].innerHTML
    assert "Real-world reference" in game_env.elements["trajectory-summary"].innerText
    assert "x subsistence" in game_env.elements["efficiency-display"].innerText


# --- small readouts --------------------------------------------------------------
def test_year_and_season_and_founded_plaque(game_env):
    assert game_env.module.year_and_season(1) == (1, "Spring")
    assert game_env.module.year_and_season(6) == (2, "Summer")
    assert "Founded Year 1" in game_env.elements["founded-display"].innerText


def test_tree_completion_readout(game_env):
    done, total, pct = game_env.module.tree_completion()
    assert (done, pct) == (0, 0) and total == len(research.NODES)
    assert "0%" in game_env.elements["research-completion-display"].innerText


def test_calm_streak_grows_then_resets_on_hunger():
    state = fresh()
    state.resources["food"] = 500.0
    state.advance_season()
    state.advance_season()
    assert state.calm_streak == 2
    state.resources["food"] = 0.0
    state.allocation = {k: 0 for k in state.allocation}
    state.advance_season()
    assert state.calm_streak == 0


# --- K21b -------------------------------------------------------------------------
def test_expanded_tree_is_valid_and_bigger():
    tree = research.build_tree(current_era="space")
    assert tree.validate() == []
    assert len(tree.nodes) >= 54


def test_new_nodes_sit_in_late_tiers_and_are_all_reachable():
    new_ids = {
        "storehouse_rotation", "civic_records", "almshouses", "tenement_reform",
        "materials_recovery", "open_data_portals", "urban_farms_and_green_roofs",
        "orbital_agronomy", "habitat_commons",
    }
    for node_id in new_ids:
        node = research.NODES[node_id]
        assert node.tier == research.era_tiers(node.era)[1]
    tree = research.build_tree(current_era="space")
    resources = {"knowledge": 100_000.0}
    for _ in range(len(tree.nodes)):
        for n in tree.available_nodes():
            tree.research(n.node_id, resources)
    assert new_ids <= set(tree.researched)


def test_new_nodes_do_not_break_the_score_bound():
    tree = research.build_tree(current_era="space", researched=list(research.NODES))
    effects = tree.effects()
    state = fresh()
    state.era = "space"
    value = sustainability.score(state, effects)
    assert 0.0 <= value <= 100.0 and math.isfinite(value)


# --- K12 / K23 / K6 / K17 / K7 -----------------------------------------------
import summary


def test_every_effect_key_has_a_label_and_describe_effects_reads_numbers():
    for key in sim.NEUTRAL_EFFECTS:
        assert key in research.EFFECT_LABELS, key
    assert research.describe_effects(research.NODES["foraging_lore"]) == "food yield +20%"
    text = research.describe_effects(research.NODES["seasonal_rounds"])
    assert "land recovery +25%" in text and "land pressure per harvest -10%" in text
    assert "people housed +4" in research.describe_effects(research.NODES["banked_shelters"])


def test_research_rows_show_effects_and_locked_rows_show_an_estimate(game_env):
    locked = game_env.elements["research-locked-list"].children
    assert locked
    texts = []
    def walk(el):
        texts.append(el.innerText)
        for c in el.children:
            walk(c)
    for row in locked:
        walk(row)
    assert any(t.startswith("Effect: ") for t in texts)
    assert any("Roughly" in t for t in texts)


def test_unlock_estimate_only_for_tier_gated_nodes():
    tree = research.build_tree(current_era="agrarian")
    # plow_and_furrow is tier 3, gated by the tier-2 nodes.
    estimate = research.unlock_estimate(tree, "plow_and_furrow")
    assert estimate is None or estimate > research.NODES["plow_and_furrow"].cost
    assert research.unlock_estimate(tree, "fire_keeping") is None      # tier 1: not gated
    assert research.unlock_estimate(tree, "canal_engineering") is None  # era not reached
    assert research.unlock_estimate(tree, "no_such_node") is None


def test_branch_chips_filter_the_research_list(game_env):
    def names():
        out = []
        for c in game_env.elements["research-list"].children:
            out.append(c)
        return out
    all_rows = len(names())
    game_env.elements["research-branch-craft-button"].dispatch("click", None)
    assert game_env.module.research_branch_filter == {"craft"}
    craft_rows = len(names())
    assert 0 < craft_rows < all_rows
    game_env.elements["research-branch-craft-button"].dispatch("click", None)
    assert game_env.module.research_branch_filter == set()
    assert len(names()) == all_rows


def test_efficiency_rank_follows_the_score_bands():
    assert summary.efficiency_rank(90) == "Gold"
    assert summary.efficiency_rank(75) == "Silver"
    assert summary.efficiency_rank(40) == "Bronze"
    assert summary.efficiency_rank(90, hard_mode=True) == "Silver"  # harder bands
    assert summary.efficiency_rank(None) is None
    assert summary.efficiency_rank(float("nan")) is None


def test_stakeholder_statement_and_rank_in_summary_panel(game_env):
    game_env.advance_season(2)
    game_env.elements["summary-toggle-button"].dispatch("click", None)
    panel = game_env.elements["summary-panel"]
    text = " ".join(c.innerText for c in panel.children)
    assert "stakeholders" in text and "Efficiency rank" in text
