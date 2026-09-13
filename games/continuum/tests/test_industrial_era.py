"""Milestone 11 — fourth full era transition, Medieval -> Industrial.

Covers the concrete Industrial content this milestone had to invent (see
CLAUDE.md's Milestone 11 build notes for the design rationale): the Factory
Workers role and Sanitation Works building, the `pollution` mechanic that
is this era's real point -- the first era-specific adjustment in the whole
game with a GROWTH-side mechanical consequence, not only a sustainability-
score one, grounded in continuum-real-world-sources.md's Economic Journal
source showing industrial pollution measurably reduced long-run city
growth historically -- the six new research nodes chaining back into
Medieval's own late tier, the Industrial info-panel content, and -- the
actual point of this milestone, same as Milestones 8-10's own closing
sections -- driving a fourth full transition (Medieval -> Industrial)
through game.py's real UI, proving the era-transition framework holds up a
fourth time.
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
    the same Classical->Medieval conditions test_medieval_era.py's own
    push_to_medieval_ready() exercises, plus shelter/hearth raised
    alongside population (the trap test_medieval_era.py's build notes
    flagged: a population jump onto unbuilt capacity craters the score
    below the transition's own "Strained" floor)."""
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
    Industrial requirement: tier 8 has to be UNLOCKED (two tier-7 nodes
    researched), which itself needs tier 7 unlocked (two tier-6 nodes
    researched first) -- push_to_medieval() already researched two tier-5
    nodes (canal_engineering/managed_irrigation), which is enough to
    unlock tier 6. Population has to reach 60; shelter/hearth are bumped
    up alongside it, the same trap test_medieval_era.py's own build notes
    flagged and this file's own push_to_medieval() already had to repeat
    once for the Classical->Medieval leg."""
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


# --- sim.py: Factory Workers / Sanitation Works ---------------------------
def test_factory_workers_and_sanitation_works_exist_but_are_not_available_before_industrial():
    assert "factory_workers" in sim.ROLES
    assert "sanitation_works" in sim.BUILDINGS
    for era in ("tribal", "agrarian", "classical", "medieval"):
        assert "factory_workers" not in sim.roles_for_era(era)
        assert "sanitation_works" not in sim.buildings_for_era(era)
    assert "factory_workers" in sim.roles_for_era("industrial")
    assert "sanitation_works" in sim.buildings_for_era("industrial")
    # Cumulative, not replaced: Industrial still has every earlier role too.
    assert set(sim.roles_for_era("medieval")).issubset(set(sim.roles_for_era("industrial")))
    assert set(sim.buildings_for_era("medieval")).issubset(set(sim.buildings_for_era("industrial")))


def test_a_fresh_settlement_starts_with_zero_factory_workers_and_sanitation_works():
    state = sim.CityState()
    assert state.allocation["factory_workers"] == 0
    assert state.buildings["sanitation_works"] == 0


def test_a_fresh_settlement_starts_with_zero_pollution():
    state = sim.CityState()
    assert state.pollution == 0.0


def test_factory_workers_produce_more_materials_per_person_than_gatherers():
    gatherers_only = sim.CityState(era="industrial")
    gatherers_only.allocation = dict.fromkeys(sim.ROLES, 0)
    gatherers_only.allocation["gatherers"] = 5

    factory_workers_only = sim.CityState(era="industrial")
    factory_workers_only.allocation = dict.fromkeys(sim.ROLES, 0)
    factory_workers_only.allocation["factory_workers"] = 5

    gatherers_report = gatherers_only.advance_season()
    factory_report = factory_workers_only.advance_season()

    assert factory_report["materials_gathered"] > gatherers_report["materials_gathered"]


def test_materials_yield_mult_effect_applies_to_factory_worker_output_too():
    """Same shared-economy discipline Farmers/Canals/Guildmasters were held
    to: a Factory Worker is not a separate economy research can't touch."""
    plain = sim.CityState(era="industrial")
    plain.allocation = dict.fromkeys(sim.ROLES, 0)
    plain.allocation["factory_workers"] = 4

    effects_boosted = dict(sim.NEUTRAL_EFFECTS)
    effects_boosted["materials_yield_mult"] = 1.5

    plain_report = plain.advance_season()

    boosted = sim.CityState(era="industrial")
    boosted.allocation = dict.fromkeys(sim.ROLES, 0)
    boosted.allocation["factory_workers"] = 4
    boosted_report = boosted.advance_season(effects_boosted)

    assert boosted_report["materials_gathered"] > plain_report["materials_gathered"]


def test_sanitation_works_has_no_production_effect_of_its_own():
    """Deliberately like Public Works: building Sanitation Works changes
    nothing about food/materials/tools output. Unlike Public Works, though,
    it DOES change something else in the season loop -- pollution -- which
    is exactly the point (see CLAUDE.md's Milestone 11 build notes for why
    that's a deliberate divergence from the Public Works precedent, not an
    oversight)."""
    no_sanitation = sim.CityState(era="industrial")
    no_sanitation.allocation = dict.fromkeys(sim.ROLES, 0)
    no_sanitation.allocation["foragers"] = 5

    with_sanitation = sim.CityState(era="industrial")
    with_sanitation.allocation = dict.fromkeys(sim.ROLES, 0)
    with_sanitation.allocation["foragers"] = 5
    with_sanitation.buildings["sanitation_works"] = 3
    with_sanitation.resources["materials"] = no_sanitation.resources["materials"]

    report_a = no_sanitation.advance_season()
    report_b = with_sanitation.advance_season()

    assert report_a["food_gathered"] == pytest.approx(report_b["food_gathered"])
    assert report_a["materials_gathered"] == pytest.approx(report_b["materials_gathered"])
    assert report_a["tools_made"] == pytest.approx(report_b["tools_made"])


def test_report_includes_pollution_field_for_narration():
    state = sim.CityState(era="industrial")
    state.allocation["factory_workers"] = 3
    report = state.advance_season()
    assert 0.0 <= report["pollution"] <= 1.0


# --- sim.py: the pollution mechanic itself ---------------------------------
def test_pollution_has_no_effect_before_industrial():
    """Shouldn't be reachable (factory_workers can't be assigned before
    Industrial), but zero either way -- the same defensive era-gate
    discipline every prior era-specific mechanic in this file has been
    held to."""
    for era in ("tribal", "agrarian", "classical", "medieval"):
        state = sim.CityState(era=era)
        state.allocation["factory_workers"] = 10  # shouldn't be reachable
        state.advance_season()
        assert state.pollution == 0.0


def test_pollution_accumulates_from_factory_workers_with_no_sanitation():
    state = sim.CityState(era="industrial")
    state.allocation = dict.fromkeys(sim.ROLES, 0)
    state.allocation["factory_workers"] = 5
    assert state.pollution == 0.0
    state.advance_season()
    assert state.pollution > 0.0


def test_pollution_decays_on_its_own_with_no_factory_workers():
    state = sim.CityState(era="industrial")
    state.pollution = 0.5
    state.advance_season()
    assert state.pollution < 0.5


def test_pollution_is_clamped_between_zero_and_one():
    heavy = sim.CityState(era="industrial")
    heavy.allocation = dict.fromkeys(sim.ROLES, 0)
    heavy.allocation["factory_workers"] = 500
    for _ in range(20):
        heavy.advance_season()
    assert 0.0 <= heavy.pollution <= 1.0

    clean = sim.CityState(era="industrial")
    for _ in range(20):
        clean.advance_season()
    assert clean.pollution >= 0.0


def test_sanitation_works_reduces_pollution_accumulation_holding_everything_else_fixed():
    """Isolated the way Milestone 9's admin-overextension test and
    Milestone 10's public-works test isolated their own comparisons: same
    factory-worker count -- the only difference is Sanitation Works
    building count."""
    def make(sanitation_works):
        state = sim.CityState(era="industrial")
        state.allocation = dict.fromkeys(sim.ROLES, 0)
        state.allocation["factory_workers"] = 8
        state.buildings["sanitation_works"] = sanitation_works
        return state

    unmitigated = make(0)
    mitigated = make(6)

    unmitigated.advance_season()
    mitigated.advance_season()

    assert unmitigated.pollution > mitigated.pollution


def test_sanitation_bonus_effect_increases_absorption():
    # Only 1 Sanitation Works against 8 Factory Workers, so the plain run
    # leaves real pollution behind for the boosted run to visibly beat --
    # too much sanitation for the factory-worker count would clamp both to
    # zero and hide the effect being tested.
    state = sim.CityState(era="industrial")
    state.allocation = dict.fromkeys(sim.ROLES, 0)
    state.allocation["factory_workers"] = 8
    state.buildings["sanitation_works"] = 1

    effects_boosted = dict(sim.NEUTRAL_EFFECTS)
    effects_boosted["sanitation_bonus"] = 0.5

    plain = sim.CityState(era="industrial")
    plain.allocation = dict.fromkeys(sim.ROLES, 0)
    plain.allocation["factory_workers"] = 8
    plain.buildings["sanitation_works"] = 1

    plain.advance_season()
    state.advance_season(effects_boosted)

    assert plain.pollution > 0.0
    assert state.pollution < plain.pollution


def test_pollution_output_mult_effect_reduces_pollution_produced():
    plain = sim.CityState(era="industrial")
    plain.allocation = dict.fromkeys(sim.ROLES, 0)
    plain.allocation["factory_workers"] = 8

    reduced = sim.CityState(era="industrial")
    reduced.allocation = dict.fromkeys(sim.ROLES, 0)
    reduced.allocation["factory_workers"] = 8

    effects_reduced = dict(sim.NEUTRAL_EFFECTS)
    effects_reduced["pollution_output_mult"] = 0.5

    plain.advance_season()
    reduced.advance_season(effects_reduced)

    assert reduced.pollution < plain.pollution


# --- sim.py: the growth-side consequence -- the actual point ---------------
def test_pollution_reduces_growth_progress_holding_everything_else_fixed():
    """The isolated, single-season proof of the growth-side mechanic: same
    population, same housing, same food surplus, same land health -- the
    ONLY difference is the pollution stock read at the start of the season
    (pollution itself is a lagged stock -- see sim.py's own comments -- so
    this season's growth reads whatever `pollution` was already set to,
    not anything advance_season() produces mid-call). A soft, proportional
    cost (POLLUTION_GROWTH_PENALTY_WEIGHT), deliberately not land_health's
    hard gate -- see that constant's own comment for why."""
    def make(pollution):
        state = sim.CityState(era="industrial")
        state.population = 20
        state.allocation = dict.fromkeys(sim.ROLES, 0)
        state.buildings["shelter"] = 50
        state.buildings["granary"] = 50
        state.resources["food"] = 5000.0
        state.pollution = pollution
        return state

    clean = make(0.0)
    fully_polluted = make(1.0)

    clean.advance_season()
    fully_polluted.advance_season()

    assert clean.growth_progress > fully_polluted.growth_progress
    assert fully_polluted.growth_progress == pytest.approx(
        clean.growth_progress * (1.0 - sim.POLLUTION_GROWTH_PENALTY_WEIGHT)
    )


def test_pollution_measurably_slows_growth_compared_to_a_mitigated_settlement():
    """The mechanical heart of Milestone 11, played out over many seasons
    rather than isolated to one: per continuum-real-world-sources.md's
    Economic Journal source, industrial pollution measurably reduced
    long-run city growth historically -- a real, provable cost, not just a
    moral one. Two settlements identical in every way except Sanitation
    Works investment; only the mitigated one keeps pollution near zero,
    and only it ends up with a bigger population after the same number of
    seasons -- the same "provably outscores" bar the design doc holds the
    whole sustainability system to (see CLAUDE.md's Core system 3), now
    demonstrated for a real growth number rather than only the score."""
    def make(sanitation_works):
        state = sim.CityState(era="industrial")
        state.population = 20
        state.allocation = dict.fromkeys(sim.ROLES, 0)
        state.allocation["factory_workers"] = 10
        state.buildings["shelter"] = 200
        state.buildings["granary"] = 200
        state.buildings["sanitation_works"] = sanitation_works
        state.resources["food"] = 5000.0
        state.resources["materials"] = 0.0
        return state

    polluting = make(sanitation_works=0)
    mitigated = make(sanitation_works=6)

    for _ in range(25):
        polluting.advance_season()
        mitigated.advance_season()

    assert polluting.pollution > mitigated.pollution
    assert mitigated.population > polluting.population


def test_role_diversity_is_unaffected_by_factory_workers_for_earlier_eras():
    """The same trap Milestone 8's own build notes flagged for Farmers:
    adding a new key to the allocation dict must not silently change
    role_diversity()'s denominator for a settlement that hasn't unlocked
    that role yet. Already fixed at the root by role_diversity() scoping
    to roles_for_era() rather than the flat ROLES list -- this is a direct
    regression check for that fix holding a fourth time, not a new
    mechanism."""
    for era in ("tribal", "agrarian", "classical", "medieval"):
        assert "factory_workers" not in sim.roles_for_era(era)
        state = sim.CityState(era=era)
        # A fresh CityState's allocation dict already carries a
        # "factory_workers": 0 entry (cumulative roles -- see sim.py), so
        # this exercises the real shape a save/settlement actually has.
        assert "factory_workers" in state.allocation
        diversity_before = state.role_diversity()
        state.allocation["factory_workers"] = 0  # no-op, already zero
        assert state.role_diversity() == pytest.approx(diversity_before)


# --- sustainability.py: pollution's environmental balance cost -------------
def test_industrial_pollution_penalty_has_no_effect_before_industrial():
    for era in ("tribal", "agrarian", "classical", "medieval"):
        state = sim.CityState(era=era)
        state.pollution = 1.0  # shouldn't be reachable, but zero either way
        assert sustainability._industrial_pollution_penalty(state) == 0.0


def test_industrial_pollution_penalty_is_zero_with_no_pollution():
    state = sim.CityState(era="industrial")
    assert sustainability._industrial_pollution_penalty(state) == 0.0


def test_industrial_pollution_penalty_increases_with_pollution_then_caps():
    state = sim.CityState(era="industrial")

    state.pollution = 0.0
    none = sustainability._industrial_pollution_penalty(state)

    state.pollution = 0.5
    partial = sustainability._industrial_pollution_penalty(state)

    state.pollution = 1.0
    full = sustainability._industrial_pollution_penalty(state)

    assert none == 0.0
    assert 0.0 < partial < full
    assert full == pytest.approx(sustainability.INDUSTRIAL_POLLUTION_PENALTY_WEIGHT)


def test_industrial_pollution_penalty_is_exactly_what_balance_subtracts():
    """Whitebox check that balance() actually applies the penalty this
    function computes, the same discipline Milestones 9-10 already used
    for their own era-specific adjustments."""
    state = sim.CityState(era="industrial")
    state.pollution = 0.6

    penalty = sustainability._industrial_pollution_penalty(state)
    assert penalty > 0.0

    extraction = state.last_extraction
    limit = state.last_sustainable_yield
    harvest = 1.0 if extraction <= limit or extraction <= 0 else sustainability._clamp(limit / extraction)
    expected = sustainability._clamp(
        (sustainability._clamp(state.land_health) + harvest) / 2.0 - penalty
    )

    assert sustainability.balance(state) == pytest.approx(expected)


def test_industrial_pollution_penalty_does_not_need_a_ratio_the_other_adjustments_needed():
    """`state.pollution` is already a 0..1 ratio-like stock (see sim.py's
    build-up/decay model), unlike the raw counts/shares the Agrarian,
    Classical and Medieval adjustments all had to turn into a ratio
    themselves -- doubling population changes nothing about this penalty,
    since population never enters the calculation at all."""
    small = sim.CityState(era="industrial")
    small.population = 15
    small.pollution = 0.4

    big = sim.CityState(era="industrial")
    big.population = 150
    big.pollution = 0.4

    assert sustainability._industrial_pollution_penalty(
        small
    ) == pytest.approx(sustainability._industrial_pollution_penalty(big))


# --- research.py: the six new Industrial nodes -----------------------------
def test_industrial_nodes_are_gated_until_industrial_is_reached():
    tree = research.build_tree(current_era="medieval")
    tree.researched = [
        "fire_keeping", "foraging_lore", "shared_hearth", "stone_knapping",
        "seasonal_rounds", "kinship_custom", "storage_craft", "banked_shelters",
        "elders_council", "plow_and_furrow", "seed_selection", "communal_granaries",
        "irrigation_channels", "crop_rotation", "market_custom", "canal_engineering",
        "managed_irrigation", "temple_administration", "monumental_masonry",
        "trade_networks", "civic_assembly", "guild_workshops", "trade_zoning",
        "municipal_charter", "master_guilds", "public_sanitation", "free_city_charter",
    ]
    assert tree.is_available("smoke_abatement") is False
    assert "hasn't reached the Industrial era" in " ".join(tree.missing_requirements("smoke_abatement"))


def test_industrial_nodes_become_reachable_once_the_era_is_reached():
    tree = research.build_tree(current_era="industrial")
    resources = {"knowledge": 100_000.0}
    for _ in range(len(tree.nodes)):
        available = tree.available_nodes()
        if not available:
            break
        for node in available:
            tree.research(node.node_id, resources)
    for node_id in (
        "smoke_abatement", "steam_power", "factory_acts",
        "sanitation_engineering", "assembly_lines", "public_health_acts",
    ):
        assert node_id in tree.researched


def test_industrial_nodes_chain_back_into_medievals_late_tier():
    """The same "early choices echo later, across the era boundary" proof
    Milestones 8-10 gave, now shown a fourth time for Medieval->
    Industrial."""
    late_medieval = set(
        n.node_id for n in research.NODE_LIST if n.era == "medieval" and n.tier == research.era_tiers("medieval")[1]
    )
    early_industrial = [n for n in research.NODE_LIST if n.era == "industrial" and n.tier == research.era_tiers("industrial")[0]]
    assert len(early_industrial) == 3
    for node in early_industrial:
        assert set(node.prerequisites) & late_medieval, (
            f"{node.node_id} should chain back into a late-Medieval node"
        )


def test_public_health_acts_needs_more_community_affinity_than_factory_acts():
    public_health_acts = research.NODES["public_health_acts"]
    factory_acts = research.NODES["factory_acts"]
    free_city_charter = research.NODES["free_city_charter"]
    assert public_health_acts.min_affinity["community"] > factory_acts.min_affinity["community"]
    assert factory_acts.min_affinity["community"] > free_city_charter.min_affinity["community"]


def test_smoke_abatement_and_sanitation_engineering_grant_the_pollution_output_mult_key():
    assert research.NODES["smoke_abatement"].effects.get("pollution_output_mult") == -0.15
    assert research.NODES["sanitation_engineering"].effects.get("pollution_output_mult") == -0.15


def test_sanitation_engineering_and_public_health_acts_grant_the_sanitation_bonus_key():
    assert research.NODES["sanitation_engineering"].effects.get("sanitation_bonus") == 0.25
    assert research.NODES["public_health_acts"].effects.get("sanitation_bonus") == 0.15


def test_industrial_tiers_are_the_next_two_global_tiers_after_medieval():
    assert research.era_tiers("industrial") == [
        research.era_tiers("medieval")[-1] + 1,
        research.era_tiers("medieval")[-1] + 2,
    ]


def test_the_shipped_tree_still_validates_with_industrial_content():
    tree = research.build_tree()
    assert tree.validate() == []


# --- info_content.py: Industrial real-world sources ------------------------
def test_industrial_info_page_has_real_sources_not_the_pending_placeholder():
    page = info_content.era_info_page("industrial")
    assert len(page["sources"]) == 4
    for source in page["sources"]:
        assert source["url"].startswith("https://")
        assert source["label"]
        assert source["note"]


# --- transition.py: Medieval -> Industrial requirements --------------------
def test_medieval_to_industrial_requirements_are_defined():
    requirement = transition.TRANSITION_REQUIREMENTS["medieval"]
    assert requirement["to_era"] == "industrial"
    assert requirement["min_population"] == 60
    assert requirement["min_tier"] == research.era_tiers("medieval")[-1]


def test_next_era_for_medieval_is_industrial():
    assert transition.next_era_for("medieval") == "industrial"


# --- end-to-end: driving a fourth transition through game.py's real UI ----
def test_advance_era_button_targets_industrial_once_medieval_is_reached(game_env):
    push_to_agrarian(game_env)
    push_to_classical(game_env)
    push_to_medieval(game_env)
    game_env.module.render()

    button = game_env.elements["advance-era-button"]
    assert button.disabled is True
    assert "Industrial" in game_env.elements["era-progress-status-display"].innerText


def test_advance_era_button_enables_once_industrial_ready_and_transitions_on_click(game_env):
    push_to_agrarian(game_env)
    push_to_classical(game_env)
    push_to_medieval(game_env)
    push_to_industrial_ready(game_env)
    game_env.module.render()

    button = game_env.elements["advance-era-button"]
    assert button.disabled is False

    button.dispatch("click", None)

    state = game_env.state
    assert state.era == "industrial"
    assert game_env.module.tree.current_era == "industrial"
    assert game_env.module.campaign.furthest_era == "industrial"


def test_after_transitioning_the_work_and_build_panels_show_factory_workers_and_sanitation_works(game_env):
    push_to_industrial(game_env)

    assert "factory_workers-name" in game_env.elements
    assert "sanitation_works-name" in game_env.elements
    assert game_env.elements["factory_workers-name"].innerText == "Factory Workers"
    assert game_env.elements["sanitation_works-name"].innerText == "Sanitation Works"


def test_after_transitioning_the_info_panel_shows_industrial_content(game_env):
    push_to_industrial(game_env)

    game_env.elements["info-page-toggle-button"].dispatch("click", None)
    assert (
        game_env.elements["info-page-framing"].innerText
        == info_content.era_info_page("industrial")["framing"]
    )


def test_after_transitioning_the_log_shows_all_four_transition_beats(game_env):
    push_to_industrial(game_env)

    transition_rows = [e for e in game_env.module.chronicle.entries if e.kind == "transition"]
    assert len(transition_rows) == 4
    assert transition_rows[0].text == transition.TRANSITION_BEATS[("tribal", "agrarian")]
    assert transition_rows[1].text == transition.TRANSITION_BEATS[("agrarian", "classical")]
    assert transition_rows[2].text == transition.TRANSITION_BEATS[("classical", "medieval")]
    assert transition_rows[3].text == transition.TRANSITION_BEATS[("medieval", "industrial")]


def test_after_transitioning_the_advance_era_button_reports_nothing_further_yet(game_env):
    """Industrial -> Digital has no requirements table entry yet (that's a
    later milestone's job), so this really is the current end of the line
    -- the same "nothing more to reach" state Medieval was briefly in
    before this milestone gave it a real transition."""
    push_to_industrial(game_env)
    game_env.module.render()

    assert game_env.elements["advance-era-button"].disabled is True
    assert "Nothing more" in game_env.elements["era-progress-status-display"].innerText


def test_a_second_click_after_transitioning_to_industrial_does_nothing(game_env):
    push_to_agrarian(game_env)
    push_to_classical(game_env)
    push_to_medieval(game_env)
    push_to_industrial_ready(game_env)
    game_env.module.render()
    button = game_env.elements["advance-era-button"]
    button.dispatch("click", None)
    era_after_first = game_env.state.era

    button.dispatch("click", None)
    assert game_env.state.era == era_after_first


def test_season_report_narrates_pollution_slowing_growth(game_env):
    """Live verification of the visible effect of the new growth-consequence
    mechanic, matching the established narration pattern from Milestones
    9-10 (the canal-staffing line, the public-works-coverage line)."""
    push_to_industrial(game_env)

    state = game_env.state
    state.allocation = dict.fromkeys(sim.ROLES, 0)
    state.allocation["factory_workers"] = 20
    state.pollution = 0.9
    game_env.advance_season()

    assert "pollution" in game_env.elements["season-report-display"].innerText.lower()


def test_save_round_trip_preserves_industrial_state_including_pollution(game_env):
    push_to_industrial(game_env)

    state = game_env.state
    state.allocation["factory_workers"] = 7
    state.buildings["sanitation_works"] = 2
    state.pollution = 0.42

    saved = game_env.module.get_state()

    fresh = save_reload(game_env.module, saved)
    assert fresh.era == "industrial"
    assert fresh.allocation["factory_workers"] == 7
    assert fresh.buildings["sanitation_works"] == 2
    assert fresh.pollution == pytest.approx(0.42)


def test_an_old_save_missing_industrial_keys_loads_cleanly_with_defaults():
    """A save written by a build before Milestone 11 has no
    "factory_workers"/"sanitation_works" entries in its city dict, and no
    "pollution" field at all -- CITY_KEYED_DICTS' key-by-key restore should
    leave the live CityState's defaults (0) in place for the first two,
    and CITY_FIELDS' missing-field tolerance should leave `pollution` at
    its CityState.__init__ default (0.0), the exact forward-compatibility
    standard every prior era addition has been held to."""
    import research as research_mod
    import save as save_mod
    import sim as sim_mod

    old_style_allocation = {
        "foragers": 3, "gatherers": 2, "crafters": 0, "keepers": 0,
        "farmers": 0, "administrators": 2, "guildmasters": 3,
    }
    old_style_buildings = {
        "shelter": 10, "granary": 0, "hearth": 5, "toolworks": 0,
        "farmland": 0, "canals": 1, "public_works": 2,
    }
    data = {
        "save_version": 1,
        "game": "continuum",
        "era_order": list(sim_mod.ERA_ORDER),
        "current_era": "medieval",
        "furthest_era": "medieval",
        "revisiting": None,
        "current_state": {
            "city": {
                "era": "medieval",
                "season": 5,
                "population": 40,
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
    assert campaign.state.allocation["factory_workers"] == 0
    assert campaign.state.buildings["sanitation_works"] == 0
    assert campaign.state.pollution == 0.0


# --- proxy-destruction discipline (constraint from CLAUDE.md) ------------
def test_rendering_the_work_panel_destroys_the_proxy_for_factory_workers(game_env):
    push_to_industrial(game_env)

    module = game_env.module
    module.render()
    proxies = module._work_button_proxies
    key = ("factory_workers", "add")
    assert key in proxies
    first_proxy = proxies[key]
    assert first_proxy.destroyed is False

    module.render()
    second_proxy = proxies[key]
    assert first_proxy.destroyed is True
    assert second_proxy.destroyed is False


def test_rendering_the_buildings_panel_destroys_the_proxy_for_sanitation_works(game_env):
    push_to_industrial(game_env)

    module = game_env.module
    module.render()
    proxies = module._building_button_proxies
    assert "sanitation_works" in proxies
    first_proxy = proxies["sanitation_works"]
    assert first_proxy.destroyed is False

    module.render()
    second_proxy = proxies["sanitation_works"]
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
