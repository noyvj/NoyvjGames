"""R2-K26 -- the eighth era, Space Age -> Relay Age.

The Relay Age is the first era added after what Phase 3 originally called
the final one (the user asked for more eras instead of an epilogue). Per
CLAUDE.md's "R2-K26" section its mechanic is deliberately a THIRD shape:
not a lagged growth stock (Industrial pollution / Digital sprawl) and not a
fourth basic provision (Space Age habitat usability), but the game's first
REGIONAL mechanic. Relay Stations link the settlement to outlying holdings;
Wayfinders haul banked `surplus` out along the links (throughput is the
smaller of what they can haul and what the stations allow); a holding that
is kept supplied opens up sustainable land yield for the whole settlement,
and one that is not costs equity by the gap between how well the core and
the holdings are served. This file covers the sim, the score term, the six
new research nodes, the info-panel content, the Space -> Relay transition
driven through game.py's real UI, saves, and the surrounding views.
"""

import pytest

import hamlet
import info_content
import log
import research
import sim
import sustainability
import trajectory
import transition
import views
import visual

from .test_space_age_era import (
    push_to_space,
    save_reload,
)


def push_to_relay_ready(game_env):
    """Continues past push_to_space() to satisfy every Space -> Relay
    requirement: tier 14 has to be UNLOCKED (two tier-13 nodes researched),
    which needs tier 13 unlocked (two tier-12 nodes researched). Population
    250 needs housing, gathering space and (Space Age's own provision)
    enough staffed habitat rings to not crater the score."""
    state = game_env.state
    tree = game_env.module.tree
    state.resources["knowledge"] = 1e9
    tree.research("transit_oriented_design", state.resources)  # tier 12, craft
    tree.research("circular_resource_systems", state.resources)  # tier 12, provision
    tree.research("modular_habitat_design", state.resources)  # tier 13, craft
    tree.research("closed_loop_life_support", state.resources)  # tier 13, provision
    state.buildings["shelter"] = 63
    state.buildings["hearth"] = 32
    state.buildings["habitat_rings"] = 9
    state.population = 250
    state.allocation["architects"] = 27
    state.resources["food"] = 1500.0
    state.resources["tools"] = 250.0
    state.fed_fraction = 1.0


def push_to_relay(game_env):
    """All the way to the Relay Age, clicking through every transition."""
    push_to_space(game_env)
    push_to_relay_ready(game_env)
    game_env.module.render()
    game_env.elements["advance-era-button"].dispatch("click", None)


def relay_state(relays=2, wayfinders=0, surplus=0.0, population=60):
    """A bare Relay Age CityState with plenty of housing/culture so the
    core itself is well provided for and only the network is under test."""
    state = sim.CityState(era="relay")
    state.population = population
    state.allocation = dict.fromkeys(sim.ROLES, 0)
    state.allocation["foragers"] = 10
    state.allocation["wayfinders"] = wayfinders
    # Space Age's own provision (habitat usability) stays fully met, so the
    # core is genuinely well provided for and only the network is under test.
    rings = -(-population // int(sim.RING_CAPACITY_PER_BUILDING))
    state.buildings["habitat_rings"] = rings
    state.allocation["architects"] = rings * sim.ARCHITECTS_PER_RING
    state.buildings["shelter"] = 40
    state.buildings["hearth"] = 20
    state.buildings["granary"] = 40
    state.buildings["relay_stations"] = relays
    state.resources["surplus"] = surplus
    state.resources["food"] = 5000.0
    return state


# --- sim.py: Wayfinders / Relay Stations ------------------------------------
def test_wayfinders_and_relay_stations_exist_but_are_not_available_before_relay():
    assert "wayfinders" in sim.ROLES
    assert "relay_stations" in sim.BUILDINGS
    for era in sim.ERA_ORDER[:-1]:
        assert "wayfinders" not in sim.roles_for_era(era)
        assert "relay_stations" not in sim.buildings_for_era(era)
    assert "wayfinders" in sim.roles_for_era("relay")
    assert "relay_stations" in sim.buildings_for_era("relay")
    assert set(sim.roles_for_era("space")).issubset(set(sim.roles_for_era("relay")))
    assert set(sim.buildings_for_era("space")).issubset(set(sim.buildings_for_era("relay")))


def test_a_fresh_settlement_starts_with_no_wayfinders_relays_and_a_clean_supply_record():
    state = sim.CityState()
    assert state.allocation["wayfinders"] == 0
    assert state.buildings["relay_stations"] == 0
    assert state.outlying_served == 1.0


def test_relay_is_the_current_last_era():
    assert sim.ERA_ORDER[-1] == "relay"
    assert sim.ERA_LABEL["relay"] == "Relay Age"
    assert "relay" in sim.IMPLEMENTED_ERAS


def test_every_role_and_building_has_label_blurb_emoji_and_cost():
    assert sim.ROLE_LABEL["wayfinders"] and sim.ROLE_BLURB["wayfinders"] and sim.ROLE_EMOJI["wayfinders"]
    for table in (sim.BUILDING_LABEL, sim.BUILDING_BLURB, sim.BUILDING_EMOJI, sim.BUILDING_COST):
        assert "relay_stations" in table
    assert sim.BUILDING_COST["relay_stations"] > sim.BUILDING_COST["habitat_rings"]


def test_nothing_regional_exists_before_the_relay_age():
    for era in sim.ERA_ORDER[:-1]:
        state = sim.CityState(era=era)
        state.buildings["relay_stations"] = 5
        state.allocation["wayfinders"] = 30
        state.resources["surplus"] = 500.0
        assert state.holdings_residents() == 0
        assert state.relay_throughput() == 0.0
        assert state.relay_land_yield() == 0.0
        assert state.housing_capacity() == state.buildings["shelter"] * sim.SHELTER_CAPACITY


def test_holdings_residents_is_capped_by_population_and_relay_capacity():
    assert relay_state(relays=0).holdings_residents() == 0
    assert relay_state(relays=2, population=60).holdings_residents() == 2 * sim.HOLDING_RESIDENTS_PER_RELAY
    assert relay_state(relays=20, population=30).holdings_residents() == 30


def test_a_relay_houses_its_holdings_residents():
    with_relays = relay_state(relays=3)
    without = relay_state(relays=0)
    assert with_relays.housing_capacity() - without.housing_capacity() == 3 * sim.HOLDING_RESIDENTS_PER_RELAY


def test_throughput_is_the_smaller_of_hauling_and_the_station_ceiling():
    hauling_limited = relay_state(relays=4, wayfinders=2)
    assert hauling_limited.relay_throughput() == pytest.approx(2 * sim.WAYFINDER_CARRY)
    ceiling_limited = relay_state(relays=1, wayfinders=50)
    assert ceiling_limited.relay_throughput() == pytest.approx(sim.RELAY_THROUGHPUT)
    assert relay_state(relays=3, wayfinders=0).relay_throughput() == 0.0


def test_relay_bonus_effect_raises_the_ceiling_only():
    state = relay_state(relays=1, wayfinders=50)
    boosted = dict(sim.NEUTRAL_EFFECTS)
    boosted["relay_bonus"] = 0.5
    assert state.relay_throughput(boosted) == pytest.approx(sim.RELAY_THROUGHPUT * 1.5)
    hauling_limited = relay_state(relays=4, wayfinders=1)
    assert hauling_limited.relay_throughput(boosted) == hauling_limited.relay_throughput()


# --- sim.py: the season loop's relay step ------------------------------------
def test_a_supplied_holding_draws_down_surplus_and_reads_fully_served():
    state = relay_state(relays=2, wayfinders=6, surplus=100.0)
    needed = 2 * sim.HOLDING_RESIDENTS_PER_RELAY * sim.OUTLYING_SUPPLY_PER_RESIDENT
    report = state.advance_season()
    assert report["relay_needed"] == pytest.approx(needed)
    assert report["relay_delivered"] == pytest.approx(needed)
    assert state.outlying_served == pytest.approx(1.0)
    assert state.resources["surplus"] == pytest.approx(100.0 + report["surplus_banked"] - needed)
    assert report["outlying_served"] == pytest.approx(1.0)


def test_no_wayfinders_means_nothing_is_delivered_however_much_surplus_there_is():
    state = relay_state(relays=2, wayfinders=0, surplus=500.0)
    banked_before = state.resources["surplus"]
    report = state.advance_season()
    assert report["relay_delivered"] == 0.0
    assert state.outlying_served == 0.0
    assert state.resources["surplus"] >= banked_before  # nothing left the store


def test_an_empty_surplus_store_leaves_the_holdings_unsupplied():
    state = relay_state(relays=2, wayfinders=20, surplus=0.0)
    state.food_storage_capacity = lambda effects=None: 1e9  # nothing spoils into surplus
    report = state.advance_season()
    assert report["relay_delivered"] == 0.0
    assert state.outlying_served == 0.0


def test_partial_supply_gives_a_fractional_served_ratio():
    state = relay_state(relays=2, wayfinders=3, surplus=500.0)  # hauls 6 of 12
    state.advance_season()
    assert state.outlying_served == pytest.approx(0.5)


def test_with_no_holdings_the_served_ratio_stays_at_one_and_nothing_is_needed():
    state = relay_state(relays=0, wayfinders=5, surplus=50.0)
    state.outlying_served = 0.2
    report = state.advance_season()
    assert state.outlying_served == 1.0
    assert report["relay_needed"] == 0.0 and report["relay_delivered"] == 0.0


def test_supplied_holdings_open_up_land_yield_and_unsupplied_ones_open_nothing():
    supplied = relay_state(relays=2)
    supplied.outlying_served = 1.0
    unsupplied = relay_state(relays=2)
    unsupplied.outlying_served = 0.0
    base = sim.LAND_SUSTAINABLE_YIELD
    assert supplied.sustainable_yield() == pytest.approx(base + 2 * sim.RELAY_LAND_YIELD)
    assert unsupplied.sustainable_yield() == pytest.approx(base)
    half = relay_state(relays=2)
    half.outlying_served = 0.5
    assert half.sustainable_yield() == pytest.approx(base + sim.RELAY_LAND_YIELD)


def test_land_yield_reads_last_seasons_supply_not_this_seasons():
    """The same lagged-stock ordering land_health/pollution/sprawl use: this
    season's land check must see LAST season's `outlying_served`."""
    state = relay_state(relays=2, wayfinders=0, surplus=0.0)
    state.outlying_served = 1.0
    state.advance_season()
    assert state.last_sustainable_yield == pytest.approx(sim.LAND_SUSTAINABLE_YIELD + 2 * sim.RELAY_LAND_YIELD)
    assert state.outlying_served == 0.0


def test_wayfinders_produce_nothing_of_their_own():
    a = relay_state(relays=0, wayfinders=0)
    b = relay_state(relays=0, wayfinders=15)
    ra, rb = a.advance_season(), b.advance_season()
    assert ra["food_gathered"] == pytest.approx(rb["food_gathered"])
    assert ra["materials_gathered"] == pytest.approx(rb["materials_gathered"])
    assert ra["tools_made"] == pytest.approx(rb["tools_made"])


def test_role_diversity_is_unaffected_by_wayfinders_for_earlier_eras():
    state = sim.CityState(era="space")
    state.population = 20
    state.allocation["foragers"] = 5
    state.allocation["gatherers"] = 5
    before = state.role_diversity()
    state.allocation["wayfinders"] = 0
    assert state.role_diversity() == before


# --- sustainability.py: the core-vs-holdings equity gap -----------------------
def test_regional_gap_penalty_is_zero_before_relay_and_with_no_holdings():
    space = sim.CityState(era="space")
    space.buildings["relay_stations"] = 3
    space.outlying_served = 0.0
    assert sustainability._regional_gap_penalty(space, 1.0) == 0.0
    no_holdings = relay_state(relays=0)
    no_holdings.outlying_served = 0.0
    assert sustainability._regional_gap_penalty(no_holdings, 1.0) == 0.0


def test_a_well_supplied_holding_costs_no_equity():
    served = relay_state(relays=2)
    served.outlying_served = 1.0
    none = relay_state(relays=0)
    assert sustainability.equity(served) == pytest.approx(sustainability.equity(none))


def test_an_unsupplied_holding_costs_equity_by_the_gap():
    starved = relay_state(relays=2)
    starved.outlying_served = 0.0
    served = relay_state(relays=2)
    served.outlying_served = 1.0
    assert sustainability.equity(starved) < sustainability.equity(served)
    core = sustainability.equity(served)
    assert sustainability.equity(starved) == pytest.approx(core * (1.0 - sustainability.REGIONAL_GAP_PENALTY_WEIGHT))


def test_a_saturating_research_equity_bonus_does_not_wash_out_the_gap():
    """By the Relay Age the tree's accumulated equity_bonus alone can pin
    equity at 1.0; the regional term is applied after it so an unsupplied
    holding still costs something."""
    effects = dict(sim.NEUTRAL_EFFECTS)
    effects["equity_bonus"] = 1.5
    starved = relay_state(relays=2)
    starved.outlying_served = 0.0
    served = relay_state(relays=2)
    served.outlying_served = 1.0
    assert sustainability.equity(served, effects) == pytest.approx(1.0)
    assert sustainability.equity(starved, effects) == pytest.approx(1.0 - sustainability.REGIONAL_GAP_PENALTY_WEIGHT)


def test_expanding_without_the_means_to_supply_it_is_worse_than_not_expanding():
    """The mechanic's whole point: an over-extended network scores WORSE than
    the same settlement that never built the relays at all."""
    never = relay_state(relays=0)
    over = relay_state(relays=4)
    over.outlying_served = 0.0
    assert sustainability.equity(over) < sustainability.equity(never)
    assert sustainability.score(over) < sustainability.score(never)


def test_the_gap_is_bounded_by_how_far_the_holdings_fall_behind_the_core():
    slightly = relay_state(relays=2)
    slightly.outlying_served = 0.9
    badly = relay_state(relays=2)
    badly.outlying_served = 0.1
    assert sustainability.equity(badly) < sustainability.equity(slightly)


def test_hard_mode_tightens_the_regional_gap_like_every_other_penalty():
    normal = relay_state(relays=2)
    normal.outlying_served = 0.0
    hard = relay_state(relays=2)
    hard.outlying_served = 0.0
    hard.hard_mode = True
    assert sustainability.equity(hard) < sustainability.equity(normal)


def test_the_regional_term_is_scale_neutral_because_served_is_already_a_ratio():
    small = relay_state(relays=1, population=20)
    small.outlying_served = 0.0
    big = relay_state(relays=1, population=200)
    big.outlying_served = 0.0
    small.buildings["shelter"] = 40
    big.buildings["shelter"] = 400
    big.buildings["hearth"] = 200
    assert sustainability._regional_gap_penalty(small, 0.8) == pytest.approx(
        sustainability._regional_gap_penalty(big, 0.8)
    )


def test_pre_relay_scores_are_byte_identical_to_before_this_era():
    """A Space Age settlement's equity must not change just because
    `outlying_served` exists."""
    state = sim.CityState(era="space")
    state.population = 30
    state.buildings["shelter"] = 10
    base = sustainability.equity(state)
    state.outlying_served = 0.0
    state.buildings["relay_stations"] = 5
    assert sustainability.equity(state) == base


def test_provisions_still_have_four_entries_in_the_relay_age():
    """Unlike Space Age, the Relay Age adds no basic provision at all."""
    state = relay_state()
    assert len(sustainability.provisions(state)) == 4


# --- research.py: tiers 15-16 --------------------------------------------------
RELAY_EARLY = ["relay_route_surveying", "regional_surplus_exchange", "regional_compact"]
RELAY_LATE = ["autonomous_hauling", "closed_supply_loops", "federated_holdings_charter"]


def test_relay_tiers_are_the_next_two_global_tiers_after_space():
    assert research.era_tiers("relay") == [15, 16]
    assert research.tier_era(16) == "relay"
    assert research.TOTAL_TIERS == 16


def test_relay_nodes_exist_in_the_right_tiers_one_per_branch():
    tree = research.build_tree()
    for node_id in RELAY_EARLY:
        assert tree.nodes[node_id].tier == 15 and tree.nodes[node_id].era == "relay"
    for node_id in RELAY_LATE:
        assert tree.nodes[node_id].tier == 16 and tree.nodes[node_id].era == "relay"
    assert {tree.nodes[n].branch for n in RELAY_EARLY} == set(research.BRANCHES)
    assert {tree.nodes[n].branch for n in RELAY_LATE} == set(research.BRANCHES)


def test_relay_nodes_are_gated_until_the_relay_age_is_reached():
    space_only = [n for n in research.NODES if research.NODES[n].era != "relay"]
    tree = research.build_tree(current_era="space", researched=space_only)
    for node_id in RELAY_EARLY + RELAY_LATE:
        assert not tree.is_available(node_id)
        assert any("Relay Age" in r for r in tree.missing_requirements(node_id))
    at_relay = research.build_tree(current_era="relay", researched=space_only)
    for node_id in RELAY_EARLY:
        assert at_relay.is_available(node_id), at_relay.missing_requirements(node_id)


def test_relay_early_nodes_chain_back_into_the_late_space_tier():
    tree = research.build_tree()
    assert tree.nodes["relay_route_surveying"].prerequisites == ("space_syntax_planning",)
    assert tree.nodes["regional_surplus_exchange"].prerequisites == ("full_cycle_reclamation",)
    assert tree.nodes["regional_compact"].prerequisites == ("off_world_founding_charter",)
    for node_id in ("space_syntax_planning", "full_cycle_reclamation", "off_world_founding_charter"):
        assert tree.nodes[node_id].tier == research.era_tiers("space")[1]


def test_the_community_affinity_chain_keeps_compounding_by_one():
    tree = research.build_tree()
    assert tree.nodes["off_world_founding_charter"].min_affinity == {"community": 12}
    assert tree.nodes["regional_compact"].min_affinity == {"community": 13}
    assert tree.nodes["federated_holdings_charter"].min_affinity == {"community": 14}


def test_relay_costs_exceed_the_previous_tier():
    tree = research.build_tree()
    space_costs = [n.cost for n in tree.nodes.values() if n.era == "space"]
    relay_early = [tree.nodes[n].cost for n in RELAY_EARLY]
    relay_late = [tree.nodes[n].cost for n in RELAY_LATE]
    assert min(relay_early) > max(c for n, c in ((n.node_id, n.cost) for n in tree.nodes.values() if n.era == "space" and n.tier == 13))
    assert min(relay_late) >= max(relay_early) - 30
    assert max(relay_late) > max(space_costs)


def test_relay_nodes_use_network_effects_not_a_new_growth_key():
    tree = research.build_tree()
    for node_id in RELAY_EARLY + RELAY_LATE:
        for key in tree.nodes[node_id].effects:
            assert key in sim.NEUTRAL_EFFECTS
            assert key not in ("pollution_output_mult", "sprawl_output_mult", "habitat_layout_bonus")
    assert "relay_bonus" in sim.NEUTRAL_EFFECTS
    assert "relay_bonus" in research.EFFECT_LABELS
    assert "relay throughput" in research.describe_effects(tree.nodes["relay_route_surveying"])


def test_the_shipped_tree_still_validates_with_relay_content():
    assert research.build_tree().validate() == []


def test_researching_a_relay_node_raises_the_effect_seam():
    tree = research.build_tree(current_era="relay", researched=list(research.NODES))
    assert tree.effects()["relay_bonus"] == pytest.approx(0.25 + 0.1 + 0.3)


# --- info_content.py ---------------------------------------------------------
def test_relay_info_page_has_real_sources_not_the_pending_placeholder():
    page = info_content.era_info_page("relay")
    assert page is not info_content._PENDING
    assert page["framing"] and page["mechanic_tie_in"]
    assert len(page["sources"]) == 4
    for source in page["sources"]:
        assert source["url"].startswith("https://")
        assert source["label"] and source["note"]


def test_relay_info_page_cites_the_regional_and_supply_line_sources():
    urls = [s["url"] for s in info_content.era_info_page("relay")["sources"]]
    assert any("sdgs.un.org/goals/goal11" in u for u in urls)
    assert any("Core%E2%80%93periphery" in u for u in urls)
    assert any("Commercial_Resupply_Services" in u for u in urls)
    assert any("Lunar_Gateway" in u for u in urls)


# --- transition.py: Space -> Relay ---------------------------------------------
def test_space_to_relay_requirements_are_defined():
    requirement = transition.TRANSITION_REQUIREMENTS["space"]
    assert requirement["to_era"] == "relay"
    assert requirement["min_population"] == 250
    assert requirement["min_tier"] == research.era_tiers("space")[-1]
    assert 250 in log.POPULATION_MILESTONES and 250 in log.POPULATION_MILESTONE_TEXT


def test_next_era_for_relay_is_none_and_this_is_now_the_true_end_of_the_arc():
    assert transition.next_era_for("relay") is None
    assert "relay" not in transition.TRANSITION_REQUIREMENTS
    assert sim.era_index("relay") == len(sim.ERA_ORDER) - 1


def test_the_space_to_relay_beat_is_bespoke_prose():
    text = transition.beat_text("space", "relay")
    assert not text.startswith("The settlement has crossed into")
    assert len(text) > 300


# --- end to end through game.py's real UI ---------------------------------------
def test_advance_era_button_enables_once_relay_ready_and_transitions_on_click(game_env):
    push_to_space(game_env)
    push_to_relay_ready(game_env)
    game_env.module.render()

    button = game_env.elements["advance-era-button"]
    assert button.disabled is False, transition.missing_requirements(
        game_env.state, game_env.module.tree, game_env.module.tree.effects()
    )
    button.dispatch("click", None)

    assert game_env.state.era == "relay"
    assert game_env.module.tree.current_era == "relay"
    assert game_env.module.campaign.furthest_era == "relay"


def test_after_transitioning_the_work_and_build_panels_show_wayfinders_and_relay_stations(game_env):
    push_to_relay(game_env)
    assert game_env.elements["wayfinders-name"].innerText == "Wayfinders"
    assert game_env.elements["relay_stations-name"].innerText == "Relay Stations"


def test_after_transitioning_the_info_panel_shows_relay_content(game_env):
    push_to_relay(game_env)
    game_env.elements["info-page-toggle-button"].dispatch("click", None)
    assert game_env.elements["info-page-framing"].innerText == info_content.era_info_page("relay")["framing"]


def test_after_transitioning_the_log_shows_all_seven_transition_beats(game_env):
    push_to_relay(game_env)
    rows = [e for e in game_env.module.chronicle.entries if e.kind == "transition"]
    assert len(rows) == 7
    assert rows[6].text == transition.TRANSITION_BEATS[("space", "relay")]


def test_after_transitioning_to_the_relay_age_the_button_reports_the_true_end_of_the_arc(game_env):
    push_to_relay(game_env)
    game_env.module.render()
    assert game_env.elements["advance-era-button"].disabled is True
    assert "Nothing more" in game_env.elements["era-progress-status-display"].innerText
    assert game_env.elements["advance-era-button"].innerText == "—"


def test_a_second_click_after_transitioning_to_relay_does_nothing(game_env):
    push_to_space(game_env)
    push_to_relay_ready(game_env)
    game_env.module.render()
    button = game_env.elements["advance-era-button"]
    button.dispatch("click", None)
    button.dispatch("click", None)
    assert game_env.state.era == "relay"


def test_the_ui_can_build_a_relay_and_assign_wayfinders(game_env):
    push_to_relay(game_env)
    state = game_env.state
    state.resources["materials"] = 500.0
    game_env.elements["relay_stations-build-button"].dispatch("click", None)
    assert state.buildings["relay_stations"] == 1
    state.allocation["foragers"] = 0
    state.allocation["gatherers"] = 0
    game_env.elements["wayfinders-add-button"].dispatch("click", None)
    assert state.allocation["wayfinders"] == 1


def test_season_report_narrates_an_undersupplied_holding(game_env):
    push_to_relay(game_env)
    state = game_env.state
    state.buildings["relay_stations"] = 2
    state.allocation["wayfinders"] = 0
    state.resources["surplus"] = 0.0
    game_env.advance_season()
    text = game_env.elements["season-report-display"].innerText.lower()
    assert "holdings" in text and "supplies" in text


def test_a_fully_supplied_season_is_not_narrated_as_a_gap(game_env):
    push_to_relay(game_env)
    state = game_env.state
    state.buildings["relay_stations"] = 1
    state.allocation["wayfinders"] = 6
    state.resources["surplus"] = 400.0
    game_env.advance_season()
    assert "holdings received only" not in game_env.elements["season-report-display"].innerText


# --- saves ---------------------------------------------------------------------
def test_save_round_trip_preserves_relay_state(game_env):
    push_to_relay(game_env)
    state = game_env.state
    state.allocation["wayfinders"] = 9
    state.buildings["relay_stations"] = 3
    state.outlying_served = 0.4
    fresh = save_reload(game_env.module, game_env.module.get_state())
    assert fresh.era == "relay"
    assert fresh.allocation["wayfinders"] == 9
    assert fresh.buildings["relay_stations"] == 3
    assert fresh.outlying_served == pytest.approx(0.4)


def test_an_old_save_without_relay_keys_loads_with_defaults():
    import save as save_mod

    campaign = save_mod.Campaign(sim.CityState(), research.build_tree())
    data = campaign.to_dict()
    city = data["current_state"]["city"]
    del city["outlying_served"]
    del city["allocation"]["wayfinders"]
    del city["buildings"]["relay_stations"]
    fresh = save_mod.Campaign(sim.CityState(), research.build_tree())
    assert fresh.load_dict(data) is True
    assert fresh.state.outlying_served == 1.0
    assert fresh.state.allocation["wayfinders"] == 0
    assert fresh.state.buildings["relay_stations"] == 0


@pytest.mark.parametrize("bad, expected", [(5.0, 1.0), (-3.0, 0.0), ("x", 1.0), (None, 1.0), (float("nan"), 1.0)])
def test_a_tampered_outlying_served_is_clamped_or_ignored(bad, expected):
    import save as save_mod

    campaign = save_mod.Campaign(sim.CityState(), research.build_tree())
    data = campaign.to_dict()
    data["current_state"]["city"]["outlying_served"] = bad
    fresh = save_mod.Campaign(sim.CityState(), research.build_tree())
    assert fresh.load_dict(data) is True
    assert fresh.state.outlying_served == expected


def test_a_revisit_of_an_earlier_era_does_not_leak_relay_state(game_env):
    push_to_relay(game_env)
    state = game_env.state
    state.buildings["relay_stations"] = 4
    campaign = game_env.module.campaign
    assert campaign.enter_revisit("space")
    assert state.era == "space"
    assert state.holdings_residents() == 0
    assert state.buildings["relay_stations"] == 0
    assert campaign.exit_revisit()
    assert state.era == "relay" and state.buildings["relay_stations"] == 4


# --- proxy-destruction discipline -------------------------------------------------
def test_rendering_the_work_and_build_panels_destroys_relay_proxies(game_env):
    push_to_relay(game_env)
    module = game_env.module
    module.render()
    work, build = module._work_button_proxies, module._building_button_proxies
    first_work, first_build = work[("wayfinders", "add")], build["relay_stations"]
    module.render()
    assert first_work.destroyed is True and first_build.destroyed is True
    assert work[("wayfinders", "add")].destroyed is False
    assert build["relay_stations"].destroyed is False


# --- visual.py / views.py / hamlet.py / trajectory.py ------------------------------
def test_visual_state_reports_the_holdings_only_once_they_exist():
    assert visual.visual_state(relay_state(relays=0), sim.NEUTRAL_EFFECTS)["holdings_served_ratio"] is None
    space = sim.CityState(era="space")
    assert visual.visual_state(space, sim.NEUTRAL_EFFECTS)["holdings_served_ratio"] is None
    built = relay_state(relays=2)
    built.outlying_served = 0.5
    vs = visual.visual_state(built, sim.NEUTRAL_EFFECTS)
    assert vs["holdings_served_ratio"] == 0.5
    assert vs["holdings_residents"] == 2 * sim.HOLDING_RESIDENTS_PER_RELAY
    assert vs["buildings"]["relay_stations"] == 2
    assert vs["era"] == "relay" and vs["era_label"] == "Relay Age"


def test_dashboard_shows_the_holdings_rows_from_the_relay_age():
    state = relay_state(relays=2, wayfinders=6, surplus=100.0)
    report = state.advance_season()
    sections = views.dashboard(state, sim.NEUTRAL_EFFECTS)
    rows = dict(row for section in sections if section["title"] == "Era pressures" for row in section["rows"])
    assert rows["Holdings' residents"] == str(2 * sim.HOLDING_RESIDENTS_PER_RELAY)
    assert "Holdings supplied" in rows
    assert report["outlying_served"] == 1.0
    earlier = views.dashboard(sim.CityState(era="space"), sim.NEUTRAL_EFFECTS)
    assert "Holdings supplied" not in dict(
        row for section in earlier if section["title"] == "Era pressures" for row in section["rows"]
    )


def test_the_civic_map_draws_a_district_and_a_distinct_glyph_for_relay_stations():
    assert views.GLYPH_SHAPES["relay_stations"] not in [
        shape for building, shape in views.GLYPH_SHAPES.items() if building != "relay_stations"
    ]
    svg = views.civic_map_svg(relay_state(relays=3))
    assert "Relay Stations" in svg


def test_the_hamlet_has_a_relay_station_for_the_new_era_only():
    ids_space = [s["id"] for s in hamlet.stations_for_era("space")]
    ids_relay = [s["id"] for s in hamlet.stations_for_era("relay")]
    assert "relay" not in ids_space and "relay" in ids_relay
    station = hamlet.STATIONS_BY_ID["relay"]
    assert station["role"] == "wayfinders" and station["building"] == "relay_stations"
    assert station["slot"] < hamlet.SLOT_COUNT


def test_the_trajectory_reference_is_honest_that_the_relay_age_has_no_data():
    assert trajectory.REFERENCE["relay"][2] is False
    assert trajectory.reference_index("relay") == trajectory.reference_index("space")


# --- achievements ---------------------------------------------------------------------
def test_seasons_are_longer_in_the_relay_age_than_in_space(game_env):
    game_env.state.era = "space"
    space_len = game_env.module.season_length()
    game_env.state.era = "relay"
    assert game_env.module.season_length() > space_len


def test_reached_relay_and_well_supplied_holdings_achievements(game_env):
    assert "reached_relay" not in game_env.module.achievement_ids_earned()
    push_to_relay(game_env)
    assert "reached_relay" in game_env.module.achievement_ids_earned()
    assert "well_supplied_holdings" not in game_env.module.achievement_ids_earned()

    state = game_env.state
    state.buildings["relay_stations"] = 1
    state.allocation["wayfinders"] = 6
    state.resources["surplus"] = 300.0
    game_env.advance_season()
    assert "well_supplied_holdings" in game_env.module.achievement_ids_earned()

    state.allocation["wayfinders"] = 0
    game_env.advance_season()
    assert "well_supplied_holdings" not in game_env.module.achievement_ids_earned()
