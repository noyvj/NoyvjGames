"""Milestone 13 -- sixth and FINAL era transition, Digital -> Space Age.

Space Age closes out Phase 3 entirely: it is the seventh and last entry in
sim.ERA_ORDER, and the only genuinely speculative era in the game. Per
CLAUDE.md's Milestone 13 build notes, its mechanic is deliberately NOT a
seventh copy of Industrial's pollution / Digital's sprawl shape -- "post-
scarcity off-world infrastructure" is treated as a genuinely different KIND
of question, not just a rescaled growth-vs-extraction one. Habitat
Architects and Habitat Rings never touch production, extraction, or growth
anywhere in sim.py; instead `habitat_capacity()` becomes a brand-new fourth
basic PROVISION (alongside food/shelter/culture) that sustainability.py's
`livability()` averages and `equity()` bounds by the worst-off value, from
Space Age on -- the first era-specific mechanic in the whole game to live
in that shared plumbing rather than beside it as a bolt-on penalty/bonus
function. Grounded in continuum-real-world-sources.md's Space Age section:
Big Think's survey of three real off-world design concepts; Planetizen's
framing of NASA's 1977 study as literally an urban-planning document;
Columbia University Press's academic history treating those designs as
real architecture; and the current (2025) Dagstuhl/SpaceCHI research on
modular habitat layout usability. Also covers the six new research nodes
chaining back into Digital's own late tier, the Space Age info-panel
content (four sources, including the current 2025 one), and -- the actual
point of this milestone, same as every prior era's own closing section --
driving the sixth and FINAL full transition (Digital -> Space Age) through
game.py's real UI, and confirming the "nothing more to reach" fallback now
fires because Space Age is the TRUE end of the arc, not merely "the next
era hasn't shipped yet."
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
    already exercises, plus shelter/hearth raised alongside population."""
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
    Industrial requirement."""
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
    """All the way to Industrial, clicking through every transition."""
    push_to_agrarian(game_env)
    push_to_classical(game_env)
    push_to_medieval(game_env)
    push_to_industrial_ready(game_env)
    game_env.module.render()
    game_env.elements["advance-era-button"].dispatch("click", None)


def push_to_digital_ready(game_env):
    """Continues past push_to_industrial() to satisfy every Industrial->
    Digital requirement."""
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


def push_to_space_ready(game_env):
    """Continues past push_to_digital() to satisfy every Digital-> Space
    Age requirement: tier 12 has to be UNLOCKED (two tier-11 nodes
    researched), which itself needs tier 11 unlocked (two tier-10 nodes
    researched first) -- push_to_digital_ready() only researched tier
    8/9 nodes, so tier 10 is merely unlocked, not researched, at that
    point. Population has to reach 150 (the new, final entry in
    log.POPULATION_MILESTONES); shelter/hearth are bumped up alongside it,
    the same trap every prior era's push-to-ready helper has had to
    repeat once for its own leg."""
    state = game_env.state
    tree = game_env.module.tree
    state.resources["knowledge"] = 10_000_000.0
    tree.research("sanitation_engineering", state.resources)  # tier 10, craft
    tree.research("assembly_lines", state.resources)  # tier 10, provision
    tree.research("data_driven_zoning", state.resources)  # tier 11, craft
    tree.research("smart_utilities", state.resources)  # tier 11, provision
    state.buildings["shelter"] = 40
    state.buildings["hearth"] = 20
    state.population = 150


def push_to_space(game_env):
    """All the way to Space Age, clicking through every transition."""
    push_to_digital(game_env)
    push_to_space_ready(game_env)
    game_env.module.render()
    game_env.elements["advance-era-button"].dispatch("click", None)


# --- sim.py: Habitat Architects / Habitat Rings -----------------------------
def test_architects_and_habitat_rings_exist_but_are_not_available_before_space():
    assert "architects" in sim.ROLES
    assert "habitat_rings" in sim.BUILDINGS
    for era in ("tribal", "agrarian", "classical", "medieval", "industrial", "digital"):
        assert "architects" not in sim.roles_for_era(era)
        assert "habitat_rings" not in sim.buildings_for_era(era)
    assert "architects" in sim.roles_for_era("space")
    assert "habitat_rings" in sim.buildings_for_era("space")
    # Cumulative, not replaced: Space Age still has every earlier role too.
    assert set(sim.roles_for_era("digital")).issubset(set(sim.roles_for_era("space")))
    assert set(sim.buildings_for_era("digital")).issubset(set(sim.buildings_for_era("space")))


def test_a_fresh_settlement_starts_with_zero_architects_and_habitat_rings():
    state = sim.CityState()
    assert state.allocation["architects"] == 0
    assert state.buildings["habitat_rings"] == 0


def test_space_is_the_true_last_era():
    """The one thing this milestone has to get right that no prior one
    did: Space Age is genuinely sim.ERA_ORDER's last entry, not just "the
    next era this build hasn't shipped yet." """
    assert sim.ERA_ORDER[-1] == "space"
    assert sim.ERA_LABEL["space"] == "Space Age"
    assert "space" in sim.IMPLEMENTED_ERAS


# --- sim.py: habitat_capacity() -- deliberately NOT a growth/production lever
def test_architects_produce_no_resource_of_their_own():
    """Like Administrators/Planners before them, Architects produce
    nothing directly -- assigning workers to Architects instead of any
    producing role should change nothing about food/materials/tools
    output."""
    no_architects = sim.CityState(era="space")
    no_architects.allocation = dict.fromkeys(sim.ROLES, 0)
    no_architects.allocation["foragers"] = 5

    with_architects = sim.CityState(era="space")
    with_architects.allocation = dict.fromkeys(sim.ROLES, 0)
    with_architects.allocation["foragers"] = 5
    with_architects.allocation["architects"] = 10

    report_a = no_architects.advance_season()
    report_b = with_architects.advance_season()

    assert report_a["food_gathered"] == pytest.approx(report_b["food_gathered"])
    assert report_a["materials_gathered"] == pytest.approx(report_b["materials_gathered"])
    assert report_a["tools_made"] == pytest.approx(report_b["tools_made"])


def test_habitat_rings_have_no_production_effect_of_their_own():
    """Deliberately like every prior era's infrastructure building: building
    Habitat Rings changes nothing about food/materials/tools output."""
    no_rings = sim.CityState(era="space")
    no_rings.allocation = dict.fromkeys(sim.ROLES, 0)
    no_rings.allocation["foragers"] = 5

    with_rings = sim.CityState(era="space")
    with_rings.allocation = dict.fromkeys(sim.ROLES, 0)
    with_rings.allocation["foragers"] = 5
    with_rings.buildings["habitat_rings"] = 4
    with_rings.resources["materials"] = no_rings.resources["materials"]

    report_a = no_rings.advance_season()
    report_b = with_rings.advance_season()

    assert report_a["food_gathered"] == pytest.approx(report_b["food_gathered"])
    assert report_a["materials_gathered"] == pytest.approx(report_b["materials_gathered"])
    assert report_a["tools_made"] == pytest.approx(report_b["tools_made"])


def test_habitat_rings_and_architects_have_no_effect_on_growth_or_extraction():
    """The central design check for this milestone: unlike pollution
    (Industrial) and sprawl (Digital), nothing about Habitat Rings or
    Architects should change growth_progress, births, extraction, or
    land_health at all -- this mechanic is deliberately NOT a seventh
    growth-side lever."""
    def make(rings, architects):
        state = sim.CityState(era="space")
        state.population = 30
        state.allocation = dict.fromkeys(sim.ROLES, 0)
        state.allocation["gatherers"] = 20
        state.allocation["architects"] = architects
        state.buildings["shelter"] = 400
        state.buildings["hearth"] = 400
        state.buildings["granary"] = 4000
        state.buildings["habitat_rings"] = rings
        state.resources["food"] = 200_000.0
        return state

    bare = make(rings=0, architects=0)
    fully_built = make(rings=10, architects=30)

    report_bare = bare.advance_season()
    report_built = fully_built.advance_season()

    assert report_bare["extraction"] == pytest.approx(report_built["extraction"])
    assert bare.land_health == pytest.approx(fully_built.land_health)
    assert report_bare["births"] == report_built["births"]
    assert bare.growth_progress == pytest.approx(fully_built.growth_progress)


def test_report_includes_habitat_fields_for_narration():
    state = sim.CityState(era="space")
    state.buildings["habitat_rings"] = 2
    state.allocation["architects"] = 3
    report = state.advance_season()
    assert report["habitat_rings"] == 2
    assert 0.0 <= report["habitat_layout_ratio"] <= 1.0


def test_habitat_capacity_has_no_effect_before_space():
    """Shouldn't be reachable (architects/habitat_rings can't be assigned/
    built before Space Age), but zero either way -- the same defensive
    era-gate discipline every prior era-specific mechanic in this file has
    been held to."""
    for era in ("tribal", "agrarian", "classical", "medieval", "industrial", "digital"):
        state = sim.CityState(era=era)
        state.buildings["habitat_rings"] = 10
        state.allocation["architects"] = 30
        assert state.habitat_capacity() == 0.0


def test_habitat_capacity_is_zero_with_no_rings_built():
    state = sim.CityState(era="space")
    state.allocation["architects"] = 10
    assert state.habitat_capacity() == 0.0


def test_habitat_capacity_scales_with_layout_quality_capped_at_one():
    """The Canal/Administrator staffing shape, reused a second time: a
    ring's usefulness scales with how many Architects have designed it,
    capped at 1.0 -- overstaffing a ring wastes design labor rather than
    compounding the bonus, the same cap test_canal_era coverage already
    proved once for Canals."""
    unstaffed = sim.CityState(era="space")
    unstaffed.buildings["habitat_rings"] = 2

    partially_staffed = sim.CityState(era="space")
    partially_staffed.buildings["habitat_rings"] = 2
    partially_staffed.allocation["architects"] = 3  # half of ARCHITECTS_PER_RING * 2

    fully_staffed = sim.CityState(era="space")
    fully_staffed.buildings["habitat_rings"] = 2
    fully_staffed.allocation["architects"] = sim.ARCHITECTS_PER_RING * 2

    overstaffed = sim.CityState(era="space")
    overstaffed.buildings["habitat_rings"] = 2
    overstaffed.allocation["architects"] = sim.ARCHITECTS_PER_RING * 2 * 5

    assert unstaffed.habitat_capacity() == 0.0
    assert 0.0 < partially_staffed.habitat_capacity() < fully_staffed.habitat_capacity()
    assert fully_staffed.habitat_capacity() == pytest.approx(
        2 * sim.RING_CAPACITY_PER_BUILDING
    )
    assert overstaffed.habitat_capacity() == pytest.approx(fully_staffed.habitat_capacity())


def test_habitat_layout_bonus_effect_increases_capacity():
    state = sim.CityState(era="space")
    state.buildings["habitat_rings"] = 2
    state.allocation["architects"] = sim.ARCHITECTS_PER_RING * 2

    plain = state.habitat_capacity()
    effects_boosted = dict(sim.NEUTRAL_EFFECTS)
    effects_boosted["habitat_layout_bonus"] = 0.5
    boosted = state.habitat_capacity(effects_boosted)

    assert boosted > plain
    assert boosted == pytest.approx(plain * 1.5)


def test_role_diversity_is_unaffected_by_architects_for_earlier_eras():
    """The same trap Milestone 8's build notes flagged for Farmers, and
    every subsequent era's own new role has had to re-check: adding a new
    key to the allocation dict must not silently change
    role_diversity()'s denominator for a settlement that hasn't unlocked
    that role yet."""
    for era in ("tribal", "agrarian", "classical", "medieval", "industrial", "digital"):
        assert "architects" not in sim.roles_for_era(era)
        state = sim.CityState(era=era)
        assert "architects" in state.allocation
        diversity_before = state.role_diversity()
        state.allocation["architects"] = 0  # no-op, already zero
        assert state.role_diversity() == pytest.approx(diversity_before)


# --- sustainability.py: habitat usability as a fourth PROVISION -------------
def test_habitat_usability_is_neutral_before_space():
    """1.0 (a neutral "not a problem here"), not 0.0 -- unlike every prior
    era's _xxx_penalty() function (which returns 0 pre-era, meaning "no
    penalty"), this is a PROVISION: its neutral value has to be the
    "everything's fine" end of its own 0..1 scale, or it would silently
    drag every pre-Space-Age livability()/equity() result down.
    """
    for era in ("tribal", "agrarian", "classical", "medieval", "industrial", "digital"):
        state = sim.CityState(era=era)
        assert sustainability.habitat_usability(state) == 1.0


def test_provisions_has_three_entries_before_space_and_four_from_space_on():
    before = sim.CityState(era="digital")
    assert len(sustainability.provisions(before)) == 3

    after = sim.CityState(era="space")
    assert len(sustainability.provisions(after)) == 4


def test_pre_space_livability_is_byte_identical_to_before_this_milestone():
    """The era-gating discipline this whole file has been held to since
    Agrarian: provisions() must return EXACTLY the same 3-item list for
    every pre-Space-Age era, not a 4th item merely neutralised at 1.0 --
    an unconditionally-appended 1.0 would still change the average
    whenever the other three provisions aren't already all 1.0
    themselves."""
    state = sim.CityState(era="digital")
    state.resources["food"] = 5.0  # deliberately not fully fed
    values_without_fourth = [
        sustainability.food_security(state),
        sustainability.shelter_adequacy(state),
        sustainability.social_provision(state),
    ]
    expected = sum(values_without_fourth) / len(values_without_fourth)
    assert sustainability.livability(state) == pytest.approx(expected)


def test_habitat_usability_is_zero_with_no_rings_built():
    state = sim.CityState(era="space")
    assert sustainability.habitat_usability(state) == 0.0


def test_habitat_usability_rises_with_layout_quality():
    state = sim.CityState(era="space")
    state.population = 60
    state.buildings["habitat_rings"] = 2

    none = sustainability.habitat_usability(state)

    state.allocation["architects"] = sim.ARCHITECTS_PER_RING * 2
    full = sustainability.habitat_usability(state)

    assert none == 0.0
    assert full > none


def test_habitat_usability_becomes_the_new_worst_off_provision_when_low():
    """Whitebox check that equity() actually reads the fourth provision
    through the shared plumbing, the same discipline every prior era's
    own adjustment was held to."""
    state = sim.CityState(era="space")
    state.population = 60
    state.buildings["habitat_rings"] = 0  # no rings at all -> usability 0.0

    values = sustainability.provisions(state)
    assert len(values) == 4
    assert min(values) == pytest.approx(sustainability.habitat_usability(state))
    assert sustainability.equity(state) < sustainability.livability(state)


def test_habitat_usability_does_not_need_a_ratio_the_growth_stocks_needed():
    """`habitat_capacity()`/population is already a ratio by construction
    (like public_works_coverage()'s own per-capita read), so doubling
    population and rings/architects together leaves the reading
    unchanged."""
    small = sim.CityState(era="space")
    small.population = 30
    small.buildings["habitat_rings"] = 2
    small.allocation["architects"] = sim.ARCHITECTS_PER_RING * 2

    big = sim.CityState(era="space")
    big.population = 300
    big.buildings["habitat_rings"] = 20
    big.allocation["architects"] = sim.ARCHITECTS_PER_RING * 20

    assert sustainability.habitat_usability(small) == pytest.approx(
        sustainability.habitat_usability(big)
    )


# --- research.py: the six new Space Age nodes -------------------------------
def test_space_nodes_are_gated_until_space_is_reached():
    tree = research.build_tree(current_era="digital")
    tree.researched = [
        "fire_keeping", "foraging_lore", "shared_hearth", "stone_knapping",
        "seasonal_rounds", "kinship_custom", "storage_craft", "banked_shelters",
        "elders_council", "plow_and_furrow", "seed_selection", "communal_granaries",
        "irrigation_channels", "crop_rotation", "market_custom", "canal_engineering",
        "managed_irrigation", "temple_administration", "monumental_masonry",
        "trade_networks", "civic_assembly", "guild_workshops", "trade_zoning",
        "municipal_charter", "master_guilds", "public_sanitation", "free_city_charter",
        "smoke_abatement", "steam_power", "factory_acts", "sanitation_engineering",
        "assembly_lines", "public_health_acts", "data_driven_zoning", "smart_utilities",
        "participatory_planning", "transit_oriented_design", "circular_resource_systems",
    ]
    assert tree.is_available("modular_habitat_design") is False
    assert "hasn't reached the Space Age era" in " ".join(
        tree.missing_requirements("modular_habitat_design")
    )


def test_space_nodes_become_reachable_once_the_era_is_reached():
    tree = research.build_tree(current_era="space")
    resources = {"knowledge": 10_000_000.0}
    for _ in range(len(tree.nodes)):
        available = tree.available_nodes()
        if not available:
            break
        for node in available:
            tree.research(node.node_id, resources)
    for node_id in (
        "modular_habitat_design", "closed_loop_life_support", "settlers_compact",
        "space_syntax_planning", "full_cycle_reclamation", "off_world_founding_charter",
    ):
        assert node_id in tree.researched


def test_space_nodes_chain_back_into_digitals_late_tier():
    """The same "early choices echo later, across the era boundary" proof
    Milestones 8-12 gave, now shown a sixth and final time for Digital->
    Space Age."""
    late_digital = set(
        n.node_id for n in research.NODE_LIST
        if n.era == "digital" and n.tier == research.era_tiers("digital")[1]
    )
    early_space = [
        n for n in research.NODE_LIST if n.era == "space" and n.tier == research.era_tiers("space")[0]
    ]
    assert len(early_space) == 3
    for node in early_space:
        assert set(node.prerequisites) & late_digital, (
            f"{node.node_id} should chain back into a late-Digital node"
        )


def test_off_world_founding_charter_needs_more_community_affinity_than_settlers_compact():
    off_world_founding_charter = research.NODES["off_world_founding_charter"]
    settlers_compact = research.NODES["settlers_compact"]
    digital_commons_charter = research.NODES["digital_commons_charter"]
    assert (
        off_world_founding_charter.min_affinity["community"]
        > settlers_compact.min_affinity["community"]
    )
    assert (
        settlers_compact.min_affinity["community"]
        > digital_commons_charter.min_affinity["community"]
    )


def test_space_nodes_grant_habitat_layout_bonus_not_a_growth_key():
    """Deliberately checking the ABSENCE of a growth-side effect key on
    these nodes -- proof at the content level, not only the mechanic
    level, that Space Age's research doesn't quietly reach for
    pollution_output_mult/sprawl_output_mult's shape."""
    for node_id in ("modular_habitat_design", "settlers_compact", "space_syntax_planning"):
        node = research.NODES[node_id]
        assert "habitat_layout_bonus" in node.effects
        assert "pollution_output_mult" not in node.effects
        assert "sprawl_output_mult" not in node.effects


def test_closed_loop_nodes_extend_the_extraction_efficiency_chain():
    """The capstone callback: Closed-Loop Life Support and Full-Cycle
    Reclamation reuse the SAME extraction_efficiency key Tribal's
    seasonal_rounds first introduced, rather than inventing a new "no more
    land" mechanic -- the land_health/extraction lineage's own natural
    endpoint, per CLAUDE.md's Milestone 13 build notes."""
    assert research.NODES["closed_loop_life_support"].effects.get("extraction_efficiency") < 0
    assert research.NODES["full_cycle_reclamation"].effects.get("extraction_efficiency") < 0


def test_space_tiers_are_the_next_two_global_tiers_after_digital():
    assert research.era_tiers("space") == [
        research.era_tiers("digital")[-1] + 1,
        research.era_tiers("digital")[-1] + 2,
    ]
    assert research.era_tiers("space") == [13, 14]


def test_space_is_the_final_era_in_the_tier_map():
    assert research.tier_era(14) == "space"
    assert research.TOTAL_TIERS == 14


def test_the_shipped_tree_still_validates_with_space_content():
    tree = research.build_tree()
    assert tree.validate() == []


# --- info_content.py: Space Age real-world sources --------------------------
def test_space_info_page_has_real_sources_not_the_pending_placeholder():
    page = info_content.era_info_page("space")
    assert len(page["sources"]) == 4
    for source in page["sources"]:
        assert source["url"].startswith("https://")
        assert source["label"]
        assert source["note"]


def test_space_info_page_includes_the_current_2025_dagstuhl_source():
    """The task's own instruction: ground this era in the current (2025)
    Dagstuhl/SpaceCHI source, not just the 1970s-era NASA material."""
    page = info_content.era_info_page("space")
    assert any("Dagstuhl" in source["label"] or "SpaceCHI" in source["label"] for source in page["sources"])


# --- transition.py: Digital -> Space Age requirements -----------------------
def test_digital_to_space_requirements_are_defined():
    requirement = transition.TRANSITION_REQUIREMENTS["digital"]
    assert requirement["to_era"] == "space"
    assert requirement["min_population"] == 150
    assert requirement["min_tier"] == research.era_tiers("digital")[-1]


def test_next_era_for_digital_is_space():
    assert transition.next_era_for("digital") == "space"


def test_next_era_for_space_is_none_and_this_is_the_true_end_of_the_arc():
    """Unlike every prior era's absence from TRANSITION_REQUIREMENTS (which
    meant "not shipped yet"), Space Age's absence means something
    genuinely different: it is sim.ERA_ORDER's actual last entry. Both
    reasons produce the same `None`, which is the behaviour under test --
    but this is the first time in the game's history that it's true for
    the second reason rather than the first."""
    assert transition.next_era_for("space") is None
    assert "space" not in transition.TRANSITION_REQUIREMENTS
    assert sim.era_index("space") == len(sim.ERA_ORDER) - 1


# --- end-to-end: driving the sixth and final transition through game.py ----
def test_advance_era_button_targets_space_once_digital_is_reached(game_env):
    push_to_digital(game_env)
    game_env.module.render()

    button = game_env.elements["advance-era-button"]
    assert button.disabled is True
    assert "Space Age" in game_env.elements["era-progress-status-display"].innerText


def test_advance_era_button_enables_once_space_ready_and_transitions_on_click(game_env):
    push_to_digital(game_env)
    push_to_space_ready(game_env)
    game_env.module.render()

    button = game_env.elements["advance-era-button"]
    assert button.disabled is False

    button.dispatch("click", None)

    state = game_env.state
    assert state.era == "space"
    assert game_env.module.tree.current_era == "space"
    assert game_env.module.campaign.furthest_era == "space"


def test_after_transitioning_the_work_and_build_panels_show_architects_and_habitat_rings(game_env):
    push_to_space(game_env)

    assert "architects-name" in game_env.elements
    assert "habitat_rings-name" in game_env.elements
    assert game_env.elements["architects-name"].innerText == "Habitat Architects"
    assert game_env.elements["habitat_rings-name"].innerText == "Habitat Rings"


def test_after_transitioning_the_info_panel_shows_space_content(game_env):
    push_to_space(game_env)

    game_env.elements["info-page-toggle-button"].dispatch("click", None)
    assert (
        game_env.elements["info-page-framing"].innerText
        == info_content.era_info_page("space")["framing"]
    )


def test_after_transitioning_the_log_shows_all_six_transition_beats(game_env):
    push_to_space(game_env)

    transition_rows = [e for e in game_env.module.chronicle.entries if e.kind == "transition"]
    assert len(transition_rows) == 6
    assert transition_rows[0].text == transition.TRANSITION_BEATS[("tribal", "agrarian")]
    assert transition_rows[1].text == transition.TRANSITION_BEATS[("agrarian", "classical")]
    assert transition_rows[2].text == transition.TRANSITION_BEATS[("classical", "medieval")]
    assert transition_rows[3].text == transition.TRANSITION_BEATS[("medieval", "industrial")]
    assert transition_rows[4].text == transition.TRANSITION_BEATS[("industrial", "digital")]
    assert transition_rows[5].text == transition.TRANSITION_BEATS[("digital", "space")]


def test_after_transitioning_to_space_age_the_advance_era_button_reports_the_true_end_of_the_arc(game_env):
    """The behaviour under test here is IDENTICAL to every prior era's
    "nothing more to reach" moment -- the same status text, the same
    disabled button -- but for the first time it's genuinely true rather
    than provisionally true: there is no Milestone 14 that will one day
    give Space Age a real transition the way this milestone just did for
    Digital. transition.next_era_for()/missing_requirements() need no new
    code to get this right, since a missing TRANSITION_REQUIREMENTS entry
    already meant "nothing more to reach" either way -- this test is what
    actually exercises that fallback path for a true ending for the first
    time."""
    push_to_space(game_env)
    game_env.module.render()

    assert game_env.elements["advance-era-button"].disabled is True
    assert "Nothing more" in game_env.elements["era-progress-status-display"].innerText
    assert game_env.elements["advance-era-button"].innerText == "—"


def test_a_second_click_after_transitioning_to_space_does_nothing(game_env):
    push_to_digital(game_env)
    push_to_space_ready(game_env)
    game_env.module.render()
    button = game_env.elements["advance-era-button"]
    button.dispatch("click", None)
    era_after_first = game_env.state.era

    button.dispatch("click", None)
    assert game_env.state.era == era_after_first


def test_season_report_narrates_habitat_layout_coverage(game_env):
    """Live verification of the visible effect of the new mechanic,
    matching the established narration pattern from Milestones 9-12 (the
    canal-staffing line, the public-works-coverage line, the pollution
    line, the sprawl line) -- but this one is a coverage ratio, not a
    lagged stock, so it can be exercised in a single season."""
    push_to_space(game_env)

    state = game_env.state
    state.buildings["habitat_rings"] = 4
    state.allocation["architects"] = 0  # unstaffed -> low layout ratio
    game_env.advance_season()

    assert "habitat layout" in game_env.elements["season-report-display"].innerText.lower()


def test_save_round_trip_preserves_space_state_including_habitat_rings(game_env):
    push_to_space(game_env)

    state = game_env.state
    state.allocation["architects"] = 12
    state.buildings["habitat_rings"] = 5

    saved = game_env.module.get_state()

    fresh = save_reload(game_env.module, saved)
    assert fresh.era == "space"
    assert fresh.allocation["architects"] == 12
    assert fresh.buildings["habitat_rings"] == 5


def test_an_old_save_missing_space_keys_loads_cleanly_with_defaults():
    """A save written by a build before Milestone 13 has no "architects"/
    "habitat_rings" entries in its city dict at all -- CITY_KEYED_DICTS'
    key-by-key restore should leave the live CityState's defaults (0) in
    place for both, the exact forward-compatibility standard every prior
    era addition has been held to. Unlike pollution/sprawl, this milestone
    added NO new CITY_FIELDS entry -- habitat_capacity() is a pure
    function of buildings/allocation/effects, not a lagged stock -- so
    there is no third field to check tolerance for here."""
    import research as research_mod
    import save as save_mod
    import sim as sim_mod

    old_style_allocation = {
        "foragers": 3, "gatherers": 2, "crafters": 0, "keepers": 0,
        "farmers": 0, "administrators": 2, "guildmasters": 3,
        "factory_workers": 4, "planners": 5,
    }
    old_style_buildings = {
        "shelter": 10, "granary": 0, "hearth": 5, "toolworks": 0,
        "farmland": 0, "canals": 1, "public_works": 2, "sanitation_works": 1,
        "transit_hubs": 2,
    }
    data = {
        "save_version": 1,
        "game": "continuum",
        "era_order": list(sim_mod.ERA_ORDER),
        "current_era": "digital",
        "furthest_era": "digital",
        "revisiting": None,
        "current_state": {
            "city": {
                "era": "digital",
                "season": 5,
                "population": 100,
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
    assert campaign.state.allocation["architects"] == 0
    assert campaign.state.buildings["habitat_rings"] == 0


# --- proxy-destruction discipline (constraint from CLAUDE.md) --------------
def test_rendering_the_work_panel_destroys_the_proxy_for_architects(game_env):
    push_to_space(game_env)

    module = game_env.module
    module.render()
    proxies = module._work_button_proxies
    key = ("architects", "add")
    assert key in proxies
    first_proxy = proxies[key]
    assert first_proxy.destroyed is False

    module.render()
    second_proxy = proxies[key]
    assert first_proxy.destroyed is True
    assert second_proxy.destroyed is False


def test_rendering_the_buildings_panel_destroys_the_proxy_for_habitat_rings(game_env):
    push_to_space(game_env)

    module = game_env.module
    module.render()
    proxies = module._building_button_proxies
    assert "habitat_rings" in proxies
    first_proxy = proxies["habitat_rings"]
    assert first_proxy.destroyed is False

    module.render()
    second_proxy = proxies["habitat_rings"]
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
