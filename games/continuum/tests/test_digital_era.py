"""Milestone 12 — fifth full era transition, Industrial -> Digital.

Covers the concrete Digital content this milestone had to invent (see
CLAUDE.md's Milestone 12 build notes for the design rationale): the Urban
Planners role and Transit Hubs building, the `sprawl` mechanic that is this
era's real point -- grounded in continuum-real-world-sources.md's National
Geographic source on urban areas growing 1.28x faster than their
populations (2000-2014). Unlike Industrial's pollution (which scales
GROWTH_RATE directly), sprawl deliberately reaches growth through the
EXISTING land_health/extraction pathway Phase 1 already built -- a
different lever, not a second copy of the same one -- and it also costs
equity in the sustainability score, grounded in the ECLAC source's "1.1
billion in slum-like conditions" figure. Also covers the six new research
nodes chaining back into Industrial's own late tier, the Digital
info-panel content (five sources, including the dedicated "Current Day"
one), and -- the actual point of this milestone, same as Milestones 8-11's
own closing sections -- driving a fifth full transition (Industrial ->
Digital) through game.py's real UI, proving the era-transition framework
holds up a fifth time.
"""

import pytest

import info_content
import research
import sim
import sustainability
import transition


def push_to_agrarian(game_env):
    """Same Tribal->Agrarian conditions every prior era's test file already
    exercises."""
    state = game_env.state
    tree = game_env.module.tree
    state.resources["knowledge"] = 100.0
    tree.research("fire_keeping", state.resources)
    tree.research("foraging_lore", state.resources)
    state.population = 15
    game_env.module.render()
    game_env.elements["advance-era-button"].dispatch("click", None)


def push_to_classical(game_env):
    """Same Agrarian->Classical conditions every prior era's test file
    already exercises, clicking through rather than only satisfying the
    requirements."""
    state = game_env.state
    tree = game_env.module.tree
    state.resources["knowledge"] = 1000.0
    tree.research("stone_knapping", state.resources)
    tree.research("seasonal_rounds", state.resources)
    tree.research("plow_and_furrow", state.resources)
    tree.research("seed_selection", state.resources)
    state.population = 25
    game_env.module.render()
    game_env.elements["advance-era-button"].dispatch("click", None)


def push_to_medieval(game_env):
    """Continues past push_to_classical() and clicks through to Medieval --
    the same Classical->Medieval conditions every prior era's test file
    already exercises, plus shelter/hearth raised alongside population
    (the trap test_medieval_era.py's build notes flagged: a population
    jump onto unbuilt capacity craters the score below the transition's
    own "Strained" floor)."""
    state = game_env.state
    tree = game_env.module.tree
    state.resources["knowledge"] = 10_000.0
    tree.research("irrigation_channels", state.resources)  # tier 4, craft
    tree.research("crop_rotation", state.resources)  # tier 4, provision
    tree.research("canal_engineering", state.resources)  # tier 5, craft
    tree.research("managed_irrigation", state.resources)  # tier 5, provision
    state.buildings["shelter"] = 10
    state.buildings["hearth"] = 5
    state.population = 40
    game_env.module.render()
    game_env.elements["advance-era-button"].dispatch("click", None)


def push_to_industrial_ready(game_env):
    """Continues past push_to_medieval() to satisfy every Medieval->
    Industrial requirement, the same conditions test_industrial_era.py's
    own push_to_industrial_ready() exercises."""
    state = game_env.state
    tree = game_env.module.tree
    state.resources["knowledge"] = 100_000.0
    tree.research("monumental_masonry", state.resources)  # tier 6, craft
    tree.research("trade_networks", state.resources)  # tier 6, provision
    tree.research("guild_workshops", state.resources)  # tier 7, craft
    tree.research("trade_zoning", state.resources)  # tier 7, provision
    state.buildings["shelter"] = 16
    state.buildings["hearth"] = 8
    state.population = 60


def push_to_industrial(game_env):
    """All the way to Industrial, clicking through every transition -- the
    same sequence test_industrial_era.py's own push_to_industrial()
    exercises."""
    push_to_agrarian(game_env)
    push_to_classical(game_env)
    push_to_medieval(game_env)
    push_to_industrial_ready(game_env)
    game_env.module.render()
    game_env.elements["advance-era-button"].dispatch("click", None)


def push_to_digital_ready(game_env):
    """Continues past push_to_industrial() to satisfy every Industrial->
    Digital requirement: tier 10 has to be UNLOCKED (two tier-9 nodes
    researched), which itself needs tier 9 unlocked (two tier-8 nodes
    researched first) -- push_to_industrial_ready() only researched tier
    6/7 nodes, so tier 8 is merely unlocked, not researched, at that point.
    Population has to reach 100 (the last of log.POPULATION_MILESTONES);
    shelter/hearth are bumped up alongside it, the same trap every prior
    era's push-to-ready helper has had to repeat once for its own leg."""
    state = game_env.state
    tree = game_env.module.tree
    state.resources["knowledge"] = 1_000_000.0
    tree.research("master_guilds", state.resources)  # tier 8, craft
    tree.research("public_sanitation", state.resources)  # tier 8, provision
    tree.research("smoke_abatement", state.resources)  # tier 9, craft
    tree.research("steam_power", state.resources)  # tier 9, provision
    state.buildings["shelter"] = 27
    state.buildings["hearth"] = 14
    state.population = 100


def push_to_digital(game_env):
    """All the way to Digital, clicking through every transition."""
    push_to_industrial(game_env)
    push_to_digital_ready(game_env)
    game_env.module.render()
    game_env.elements["advance-era-button"].dispatch("click", None)


# --- sim.py: Urban Planners / Transit Hubs ---------------------------------
def test_planners_and_transit_hubs_exist_but_are_not_available_before_digital():
    assert "planners" in sim.ROLES
    assert "transit_hubs" in sim.BUILDINGS
    for era in ("tribal", "agrarian", "classical", "medieval", "industrial"):
        assert "planners" not in sim.roles_for_era(era)
        assert "transit_hubs" not in sim.buildings_for_era(era)
    assert "planners" in sim.roles_for_era("digital")
    assert "transit_hubs" in sim.buildings_for_era("digital")
    # Cumulative, not replaced: Digital still has every earlier role too.
    assert set(sim.roles_for_era("industrial")).issubset(set(sim.roles_for_era("digital")))
    assert set(sim.buildings_for_era("industrial")).issubset(set(sim.buildings_for_era("digital")))


def test_a_fresh_settlement_starts_with_zero_planners_and_transit_hubs():
    state = sim.CityState()
    assert state.allocation["planners"] == 0
    assert state.buildings["transit_hubs"] == 0


def test_a_fresh_settlement_starts_with_zero_sprawl():
    state = sim.CityState()
    assert state.sprawl == 0.0


def test_planners_produce_no_resource_of_their_own():
    """Deliberately the first ROLE in the whole game that produces nothing
    at all -- the role-side mirror of Public Works/Sanitation Works being
    buildings that don't produce (see CLAUDE.md's Milestone 12 build
    notes). Assigning workers to Planners instead of any producing role
    should change nothing about food/materials/tools output."""
    no_planners = sim.CityState(era="digital")
    no_planners.allocation = dict.fromkeys(sim.ROLES, 0)
    no_planners.allocation["foragers"] = 5

    with_planners = sim.CityState(era="digital")
    with_planners.allocation = dict.fromkeys(sim.ROLES, 0)
    with_planners.allocation["foragers"] = 5
    with_planners.allocation["planners"] = 10

    report_a = no_planners.advance_season()
    report_b = with_planners.advance_season()

    assert report_a["food_gathered"] == pytest.approx(report_b["food_gathered"])
    assert report_a["materials_gathered"] == pytest.approx(report_b["materials_gathered"])
    assert report_a["tools_made"] == pytest.approx(report_b["tools_made"])


def test_transit_hubs_have_no_production_effect_of_their_own():
    """Deliberately like Public Works/Sanitation Works: building Transit
    Hubs changes nothing about food/materials/tools output."""
    no_transit = sim.CityState(era="digital")
    no_transit.allocation = dict.fromkeys(sim.ROLES, 0)
    no_transit.allocation["foragers"] = 5

    with_transit = sim.CityState(era="digital")
    with_transit.allocation = dict.fromkeys(sim.ROLES, 0)
    with_transit.allocation["foragers"] = 5
    with_transit.buildings["transit_hubs"] = 4
    with_transit.resources["materials"] = no_transit.resources["materials"]

    report_a = no_transit.advance_season()
    report_b = with_transit.advance_season()

    assert report_a["food_gathered"] == pytest.approx(report_b["food_gathered"])
    assert report_a["materials_gathered"] == pytest.approx(report_b["materials_gathered"])
    assert report_a["tools_made"] == pytest.approx(report_b["tools_made"])


def test_report_includes_sprawl_field_for_narration():
    state = sim.CityState(era="digital")
    state.buildings["shelter"] = 50
    state.buildings["granary"] = 400
    state.resources["food"] = 5000.0
    report = state.advance_season()
    assert 0.0 <= report["sprawl"] <= 1.0


# --- sim.py: the sprawl mechanic itself -------------------------------------
def test_sprawl_has_no_effect_before_digital():
    """Shouldn't be reachable (planners/transit_hubs can't be assigned/
    built before Digital), but zero either way -- the same defensive
    era-gate discipline every prior era-specific mechanic in this file has
    been held to. Growth-friendly conditions are given deliberately, so
    this isn't just "nothing happened at all" for an unrelated reason."""
    for era in ("tribal", "agrarian", "classical", "medieval", "industrial"):
        state = sim.CityState(era=era)
        state.buildings["shelter"] = 50
        state.buildings["granary"] = 400
        state.resources["food"] = 5000.0
        state.advance_season()
        assert state.sprawl == 0.0


def test_sprawl_accumulates_from_unmanaged_population_growth():
    """The production side of the mechanic: sprawl isn't produced by an
    allocated role the way pollution is (see CLAUDE.md's Milestone 12
    build notes for why) -- it's produced by population growth itself
    outpacing density investment, the direct mechanical read of the
    National Geographic source."""
    state = sim.CityState(era="digital")
    state.allocation = dict.fromkeys(sim.ROLES, 0)
    state.population = 30
    state.buildings["shelter"] = 400
    state.buildings["hearth"] = 400
    state.buildings["granary"] = 4000
    state.resources["food"] = 200_000.0
    assert state.sprawl == 0.0
    for _ in range(3):
        state.advance_season()
    assert state.population > 30  # growth actually happened
    assert state.sprawl > 0.0


def test_sprawl_decays_on_its_own_with_no_population_growth():
    state = sim.CityState(era="digital")
    state.sprawl = 0.5
    state.buildings["shelter"] = 0  # no room to grow -- isolates decay alone
    state.advance_season()
    assert state.sprawl < 0.5


def test_sprawl_is_clamped_between_zero_and_one():
    heavy = sim.CityState(era="digital")
    heavy.allocation = dict.fromkeys(sim.ROLES, 0)
    heavy.population = 30
    heavy.buildings["shelter"] = 5000
    heavy.buildings["hearth"] = 5000
    heavy.buildings["granary"] = 40000
    heavy.resources["food"] = 2_000_000.0
    for _ in range(30):
        heavy.advance_season()
    assert 0.0 <= heavy.sprawl <= 1.0

    clean = sim.CityState(era="digital")
    for _ in range(20):
        clean.advance_season()
    assert 0.0 <= clean.sprawl <= 1.0


def test_planners_reduce_sprawl_accumulation_holding_everything_else_fixed():
    """Isolated the way Milestone 11's sanitation-works test isolated its
    own comparison: same starting sprawl and no growth this season (no
    housing headroom) -- the only difference is how many Planners are
    assigned."""
    def make(planners):
        state = sim.CityState(era="digital")
        state.allocation = dict.fromkeys(sim.ROLES, 0)
        state.allocation["planners"] = planners
        state.sprawl = 0.5
        state.buildings["shelter"] = 0
        return state

    unmanaged = make(0)
    managed = make(5)

    unmanaged.advance_season()
    managed.advance_season()

    assert unmanaged.sprawl > managed.sprawl


def test_transit_hubs_reduce_sprawl_accumulation_holding_everything_else_fixed():
    """Same isolation as the Planners test above, varying Transit Hubs
    instead."""
    def make(transit_hubs):
        state = sim.CityState(era="digital")
        state.allocation = dict.fromkeys(sim.ROLES, 0)
        state.sprawl = 0.5
        state.buildings["transit_hubs"] = transit_hubs
        state.buildings["shelter"] = 0
        return state

    unmanaged = make(0)
    managed = make(3)

    unmanaged.advance_season()
    managed.advance_season()

    assert unmanaged.sprawl > managed.sprawl


def test_sprawl_output_mult_effect_reduces_sprawl_produced():
    def make():
        state = sim.CityState(era="digital")
        state.allocation = dict.fromkeys(sim.ROLES, 0)
        state.population = 30
        state.buildings["shelter"] = 50
        state.buildings["hearth"] = 50
        state.buildings["granary"] = 400
        state.resources["food"] = 10_000.0
        return state

    plain = make()
    reduced = make()
    effects_reduced = dict(sim.NEUTRAL_EFFECTS)
    effects_reduced["sprawl_output_mult"] = 0.5

    for _ in range(3):
        plain.advance_season()
        reduced.advance_season(effects_reduced)

    assert plain.sprawl > 0.0
    assert reduced.sprawl < plain.sprawl


def test_transit_bonus_effect_increases_absorption():
    """Same isolation style as test_sanitation_bonus_effect_increases_
    absorption in test_industrial_era.py: seed a nonzero sprawl directly
    and disable growth this season, so only the absorption math is being
    compared."""
    def make():
        state = sim.CityState(era="digital")
        state.allocation = dict.fromkeys(sim.ROLES, 0)
        state.sprawl = 0.5
        state.buildings["transit_hubs"] = 1
        state.buildings["shelter"] = 0
        return state

    plain = make()
    boosted = make()
    effects_boosted = dict(sim.NEUTRAL_EFFECTS)
    effects_boosted["transit_bonus"] = 1.0

    plain.advance_season()
    boosted.advance_season(effects_boosted)

    assert plain.sprawl > 0.0
    assert boosted.sprawl < plain.sprawl


def test_role_diversity_is_unaffected_by_planners_for_earlier_eras():
    """The same trap Milestone 8's own build notes flagged for Farmers,
    and Milestone 11 re-checked for Factory Workers: adding a new key to
    the allocation dict must not silently change role_diversity()'s
    denominator for a settlement that hasn't unlocked that role yet."""
    for era in ("tribal", "agrarian", "classical", "medieval", "industrial"):
        assert "planners" not in sim.roles_for_era(era)
        state = sim.CityState(era=era)
        assert "planners" in state.allocation
        diversity_before = state.role_diversity()
        state.allocation["planners"] = 0  # no-op, already zero
        assert state.role_diversity() == pytest.approx(diversity_before)


# --- sim.py: sprawl's growth-side consequence -- the actual point ----------
def test_sprawl_amplifies_extraction_holding_everything_else_fixed():
    """The isolated, single-season proof of the growth-side mechanic:
    same allocation, same tools, same land health -- the ONLY difference
    is the sprawl stock read at the start of the season (sprawl itself is
    a lagged stock, same as pollution -- see sim.py's own comments -- so
    this season's extraction check reads whatever `sprawl` was already
    set to, not anything advance_season() produces mid-call). Deliberately
    a DIFFERENT lever from pollution's direct GROWTH_RATE multiplier: this
    scales `extraction` itself, the same quantity land_health has been
    gating growth from since Phase 1."""
    def make(sprawl):
        state = sim.CityState(era="digital")
        state.allocation = dict.fromkeys(sim.ROLES, 0)
        state.allocation["gatherers"] = 20
        state.sprawl = sprawl
        return state

    clean = make(0.0)
    fully_sprawled = make(1.0)

    report_clean = clean.advance_season()
    report_sprawled = fully_sprawled.advance_season()

    assert report_sprawled["extraction"] > report_clean["extraction"]
    assert report_sprawled["extraction"] == pytest.approx(
        report_clean["extraction"] * (1.0 + sim.SPRAWL_EXTRACTION_PENALTY_WEIGHT)
    )


def test_sprawl_measurably_hurts_growth_compared_to_a_managed_settlement():
    """The mechanical heart of Milestone 12, played out over many seasons:
    two settlements identical in every way except Urban Planner/Transit
    Hub investment. The unmanaged one lets sprawl climb high enough to
    amplify its own extraction past what the land can sustain, degrading
    land_health past GROWTH_MIN_LAND_HEALTH's own hard gate -- the same
    "provably outscores" bar the design doc holds the whole sustainability
    system to (see CLAUDE.md's Core system 3), now demonstrated for
    sprawl's own, differently-shaped growth consequence."""
    def make(planners, transit_hubs):
        state = sim.CityState(era="digital")
        state.population = 30
        state.allocation = dict.fromkeys(sim.ROLES, 0)
        state.allocation["gatherers"] = 60
        state.allocation["planners"] = planners
        state.buildings["shelter"] = 400
        state.buildings["hearth"] = 400
        state.buildings["granary"] = 4000
        state.buildings["transit_hubs"] = transit_hubs
        state.resources["food"] = 200_000.0
        return state

    sprawling = make(planners=0, transit_hubs=0)
    managed = make(planners=30, transit_hubs=10)

    for _ in range(180):
        sprawling.advance_season()
        managed.advance_season()

    assert sprawling.sprawl > managed.sprawl
    assert managed.land_health > sprawling.land_health
    assert sprawling.land_health <= sim.GROWTH_MIN_LAND_HEALTH
    assert managed.population > sprawling.population


# --- sustainability.py: sprawl's equity cost --------------------------------
def test_urban_sprawl_penalty_has_no_effect_before_digital():
    for era in ("tribal", "agrarian", "classical", "medieval", "industrial"):
        state = sim.CityState(era=era)
        state.sprawl = 1.0  # shouldn't be reachable, but zero either way
        assert sustainability._urban_sprawl_penalty(state) == 0.0


def test_urban_sprawl_penalty_is_zero_with_no_sprawl():
    state = sim.CityState(era="digital")
    assert sustainability._urban_sprawl_penalty(state) == 0.0


def test_urban_sprawl_penalty_increases_with_sprawl_then_caps():
    state = sim.CityState(era="digital")

    state.sprawl = 0.0
    none = sustainability._urban_sprawl_penalty(state)

    state.sprawl = 0.5
    partial = sustainability._urban_sprawl_penalty(state)

    state.sprawl = 1.0
    full = sustainability._urban_sprawl_penalty(state)

    assert none == 0.0
    assert 0.0 < partial < full
    assert full == pytest.approx(sustainability.URBAN_SPRAWL_PENALTY_WEIGHT)


def test_urban_sprawl_penalty_is_exactly_what_equity_subtracts():
    """Whitebox check that equity() actually applies the penalty this
    function computes, the same discipline Milestones 9-11 already used
    for their own era-specific adjustments."""
    state = sim.CityState(era="digital")
    state.sprawl = 0.6

    penalty = sustainability._urban_sprawl_penalty(state)
    assert penalty > 0.0

    values = sustainability.provisions(state)
    worst = min(values)
    spread = max(values) - worst
    expected = sustainability._clamp(
        worst * (1.0 - sustainability.EQUITY_SPREAD_PENALTY * spread) - penalty
    )

    assert sustainability.equity(state) == pytest.approx(expected)


def test_urban_sprawl_penalty_does_not_need_a_ratio_the_other_adjustments_needed():
    """`state.sprawl` is already a 0..1 ratio-like stock (see sim.py's
    build-up/decay model), the same reason Industrial's pollution penalty
    didn't need extra ratio work either -- doubling population changes
    nothing about this penalty on its own."""
    small = sim.CityState(era="digital")
    small.population = 15
    small.sprawl = 0.4

    big = sim.CityState(era="digital")
    big.population = 150
    big.sprawl = 0.4

    assert sustainability._urban_sprawl_penalty(small) == pytest.approx(
        sustainability._urban_sprawl_penalty(big)
    )


# --- research.py: the six new Digital nodes ---------------------------------
def test_digital_nodes_are_gated_until_digital_is_reached():
    tree = research.build_tree(current_era="industrial")
    tree.researched = [
        "fire_keeping", "foraging_lore", "shared_hearth", "stone_knapping",
        "seasonal_rounds", "kinship_custom", "storage_craft", "banked_shelters",
        "elders_council", "plow_and_furrow", "seed_selection", "communal_granaries",
        "irrigation_channels", "crop_rotation", "market_custom", "canal_engineering",
        "managed_irrigation", "temple_administration", "monumental_masonry",
        "trade_networks", "civic_assembly", "guild_workshops", "trade_zoning",
        "municipal_charter", "master_guilds", "public_sanitation", "free_city_charter",
        "smoke_abatement", "steam_power", "factory_acts", "sanitation_engineering",
        "assembly_lines",
    ]
    assert tree.is_available("data_driven_zoning") is False
    assert "hasn't reached the Digital era" in " ".join(
        tree.missing_requirements("data_driven_zoning")
    )


def test_digital_nodes_become_reachable_once_the_era_is_reached():
    tree = research.build_tree(current_era="digital")
    resources = {"knowledge": 1_000_000.0}
    for _ in range(len(tree.nodes)):
        available = tree.available_nodes()
        if not available:
            break
        for node in available:
            tree.research(node.node_id, resources)
    for node_id in (
        "data_driven_zoning", "smart_utilities", "participatory_planning",
        "transit_oriented_design", "circular_resource_systems", "digital_commons_charter",
    ):
        assert node_id in tree.researched


def test_digital_nodes_chain_back_into_industrials_late_tier():
    """The same "early choices echo later, across the era boundary" proof
    Milestones 8-11 gave, now shown a fifth time for Industrial->
    Digital."""
    late_industrial = set(
        n.node_id for n in research.NODE_LIST
        if n.era == "industrial" and n.tier == research.era_tiers("industrial")[1]
    )
    early_digital = [
        n for n in research.NODE_LIST if n.era == "digital" and n.tier == research.era_tiers("digital")[0]
    ]
    assert len(early_digital) == 3
    for node in early_digital:
        assert set(node.prerequisites) & late_industrial, (
            f"{node.node_id} should chain back into a late-Industrial node"
        )


def test_digital_commons_charter_needs_more_community_affinity_than_participatory_planning():
    digital_commons_charter = research.NODES["digital_commons_charter"]
    participatory_planning = research.NODES["participatory_planning"]
    public_health_acts = research.NODES["public_health_acts"]
    assert digital_commons_charter.min_affinity["community"] > participatory_planning.min_affinity["community"]
    assert participatory_planning.min_affinity["community"] > public_health_acts.min_affinity["community"]


def test_data_driven_zoning_and_transit_oriented_design_grant_the_transit_bonus_key():
    assert research.NODES["data_driven_zoning"].effects.get("transit_bonus") == 0.2
    assert research.NODES["transit_oriented_design"].effects.get("transit_bonus") == 0.3


def test_participatory_planning_and_transit_oriented_design_grant_the_sprawl_output_mult_key():
    assert research.NODES["participatory_planning"].effects.get("sprawl_output_mult") == -0.1
    assert research.NODES["transit_oriented_design"].effects.get("sprawl_output_mult") == -0.15


def test_digital_tiers_are_the_next_two_global_tiers_after_industrial():
    assert research.era_tiers("digital") == [
        research.era_tiers("industrial")[-1] + 1,
        research.era_tiers("industrial")[-1] + 2,
    ]


def test_the_shipped_tree_still_validates_with_digital_content():
    tree = research.build_tree()
    assert tree.validate() == []


def test_sprawl_output_mult_effect_key_is_floored_at_zero_by_the_tree():
    """The multiplier-floor list in research.py's effects() should include
    sprawl_output_mult now, the same discipline pollution_output_mult was
    held to -- no accumulation of research bonuses can drive it negative."""
    tree = research.build_tree(current_era="digital")
    tree.researched = ["participatory_planning", "transit_oriented_design"]
    # Fabricate an absurd extra delta directly to prove the floor, rather
    # than trusting the two shipped nodes alone stay within [0, 1].
    tree.nodes["participatory_planning"].effects["sprawl_output_mult"] = -5.0
    assert tree.effects()["sprawl_output_mult"] == 0.0


# --- info_content.py: Digital real-world sources ----------------------------
def test_digital_info_page_has_real_sources_not_the_pending_placeholder():
    page = info_content.era_info_page("digital")
    assert len(page["sources"]) == 5
    for source in page["sources"]:
        assert source["url"].startswith("https://")
        assert source["label"]
        assert source["note"]


def test_digital_info_page_includes_a_distinct_current_day_source():
    """The task's own instruction: a fifth, dedicated "right now" source,
    distinct from the era's four broader definitional/historical ones."""
    page = info_content.era_info_page("digital")
    assert any("Current Day" in source["label"] for source in page["sources"])


# --- transition.py: Industrial -> Digital requirements ----------------------
def test_industrial_to_digital_requirements_are_defined():
    requirement = transition.TRANSITION_REQUIREMENTS["industrial"]
    assert requirement["to_era"] == "digital"
    assert requirement["min_population"] == 100
    assert requirement["min_tier"] == research.era_tiers("industrial")[-1]


def test_next_era_for_industrial_is_digital():
    assert transition.next_era_for("industrial") == "digital"


# --- end-to-end: driving a fifth transition through game.py's real UI ------
def test_advance_era_button_targets_digital_once_industrial_is_reached(game_env):
    push_to_industrial(game_env)
    game_env.module.render()

    button = game_env.elements["advance-era-button"]
    assert button.disabled is True
    assert "Digital" in game_env.elements["era-progress-status-display"].innerText


def test_advance_era_button_enables_once_digital_ready_and_transitions_on_click(game_env):
    push_to_industrial(game_env)
    push_to_digital_ready(game_env)
    game_env.module.render()

    button = game_env.elements["advance-era-button"]
    assert button.disabled is False

    button.dispatch("click", None)

    state = game_env.state
    assert state.era == "digital"
    assert game_env.module.tree.current_era == "digital"
    assert game_env.module.campaign.furthest_era == "digital"


def test_after_transitioning_the_work_and_build_panels_show_planners_and_transit_hubs(game_env):
    push_to_digital(game_env)

    assert "planners-name" in game_env.elements
    assert "transit_hubs-name" in game_env.elements
    assert game_env.elements["planners-name"].innerText == "Urban Planners"
    assert game_env.elements["transit_hubs-name"].innerText == "Transit Hubs"


def test_after_transitioning_the_info_panel_shows_digital_content(game_env):
    push_to_digital(game_env)

    game_env.elements["info-page-toggle-button"].dispatch("click", None)
    assert (
        game_env.elements["info-page-framing"].innerText
        == info_content.era_info_page("digital")["framing"]
    )


def test_after_transitioning_the_log_shows_all_five_transition_beats(game_env):
    push_to_digital(game_env)

    transition_rows = [e for e in game_env.module.chronicle.entries if e.kind == "transition"]
    assert len(transition_rows) == 5
    assert transition_rows[0].text == transition.TRANSITION_BEATS[("tribal", "agrarian")]
    assert transition_rows[1].text == transition.TRANSITION_BEATS[("agrarian", "classical")]
    assert transition_rows[2].text == transition.TRANSITION_BEATS[("classical", "medieval")]
    assert transition_rows[3].text == transition.TRANSITION_BEATS[("medieval", "industrial")]
    assert transition_rows[4].text == transition.TRANSITION_BEATS[("industrial", "digital")]


def test_after_transitioning_the_advance_era_button_now_targets_space(game_env):
    """Milestone 13 gave Digital -> Space Age a real transition, the same
    "stale end of the line" update every prior era's own test file already
    needed once (Milestones 8-12 each hit this)."""
    push_to_digital(game_env)
    game_env.module.render()

    assert game_env.elements["advance-era-button"].disabled is True
    assert "Space Age" in game_env.elements["era-progress-status-display"].innerText


def test_a_second_click_after_transitioning_to_digital_does_nothing(game_env):
    push_to_industrial(game_env)
    push_to_digital_ready(game_env)
    game_env.module.render()
    button = game_env.elements["advance-era-button"]
    button.dispatch("click", None)
    era_after_first = game_env.state.era

    button.dispatch("click", None)
    assert game_env.state.era == era_after_first


def test_season_report_narrates_sprawl_leaning_on_the_land(game_env):
    """Live verification of the visible effect of the new growth-consequence
    mechanic, matching the established narration pattern from Milestones
    9-11 (the canal-staffing line, the public-works-coverage line, the
    industrial-pollution line)."""
    push_to_digital(game_env)

    state = game_env.state
    state.allocation = dict.fromkeys(sim.ROLES, 0)
    state.allocation["gatherers"] = 20
    state.sprawl = 0.9
    game_env.advance_season()

    assert "spreading out" in game_env.elements["season-report-display"].innerText.lower()


def test_save_round_trip_preserves_digital_state_including_sprawl(game_env):
    push_to_digital(game_env)

    state = game_env.state
    state.allocation["planners"] = 9
    state.buildings["transit_hubs"] = 3
    state.sprawl = 0.37

    saved = game_env.module.get_state()

    fresh = save_reload(game_env.module, saved)
    assert fresh.era == "digital"
    assert fresh.allocation["planners"] == 9
    assert fresh.buildings["transit_hubs"] == 3
    assert fresh.sprawl == pytest.approx(0.37)


def test_an_old_save_missing_digital_keys_loads_cleanly_with_defaults():
    """A save written by a build before Milestone 12 has no "planners"/
    "transit_hubs" entries in its city dict, and no "sprawl" field at all
    -- CITY_KEYED_DICTS' key-by-key restore should leave the live
    CityState's defaults (0) in place for the first two, and CITY_FIELDS'
    missing-field tolerance should leave `sprawl` at its CityState.
    __init__ default (0.0), the exact forward-compatibility standard every
    prior era addition has been held to."""
    import research as research_mod
    import save as save_mod
    import sim as sim_mod

    old_style_allocation = {
        "foragers": 3, "gatherers": 2, "crafters": 0, "keepers": 0,
        "farmers": 0, "administrators": 2, "guildmasters": 3,
        "factory_workers": 4,
    }
    old_style_buildings = {
        "shelter": 10, "granary": 0, "hearth": 5, "toolworks": 0,
        "farmland": 0, "canals": 1, "public_works": 2, "sanitation_works": 1,
    }
    data = {
        "save_version": 1,
        "game": "continuum",
        "era_order": list(sim_mod.ERA_ORDER),
        "current_era": "industrial",
        "furthest_era": "industrial",
        "revisiting": None,
        "current_state": {
            "city": {
                "era": "industrial",
                "season": 5,
                "population": 60,
                "allocation": old_style_allocation,
                "buildings": old_style_buildings,
            },
            "research": [],
        },
        "parked_state": None,
        "era_snapshots": {},
        "ui": {},
    }

    campaign = save_mod.Campaign(sim_mod.CityState(), research_mod.build_tree())
    assert campaign.load_dict(data) is True
    assert campaign.state.allocation["planners"] == 0
    assert campaign.state.buildings["transit_hubs"] == 0
    assert campaign.state.sprawl == 0.0


# --- proxy-destruction discipline (constraint from CLAUDE.md) ------------
def test_rendering_the_work_panel_destroys_the_proxy_for_planners(game_env):
    push_to_digital(game_env)

    module = game_env.module
    module.render()
    proxies = module._work_button_proxies
    key = ("planners", "add")
    assert key in proxies
    first_proxy = proxies[key]
    assert first_proxy.destroyed is False

    module.render()
    second_proxy = proxies[key]
    assert first_proxy.destroyed is True
    assert second_proxy.destroyed is False


def test_rendering_the_buildings_panel_destroys_the_proxy_for_transit_hubs(game_env):
    push_to_digital(game_env)

    module = game_env.module
    module.render()
    proxies = module._building_button_proxies
    assert "transit_hubs" in proxies
    first_proxy = proxies["transit_hubs"]
    assert first_proxy.destroyed is False

    module.render()
    second_proxy = proxies["transit_hubs"]
    assert first_proxy.destroyed is True
    assert second_proxy.destroyed is False


def save_reload(module, saved_dict):
    """Same round-trip helper every prior era's test file already uses:
    loads into a second, independent Campaign via a real JSON round-trip."""
    import copy
    import json

    import research as research_mod
    import save as save_mod
    import sim as sim_mod

    plain = json.loads(json.dumps(copy.deepcopy(saved_dict)))
    fresh_campaign = save_mod.Campaign(sim_mod.CityState(), research_mod.build_tree())
    assert fresh_campaign.load_dict(plain) is True
    return fresh_campaign.state
