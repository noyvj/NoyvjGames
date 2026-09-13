"""Milestone 9 — second full era transition, Agrarian -> Classical.

Covers the concrete Classical content this milestone had to invent (see
CLAUDE.md's Milestone 9 build notes for the design rationale): the
Administrators role and Canals building (and the deliberate two-way
dependency between them), the sustainability resilience adjustment for
over-investing in administration relative to what canals actually need
staffed, the six new research nodes chaining back into Agrarian's own late
tier, the Classical info-panel content, and — the actual point of this
milestone, same as Milestone 8's own closing section — driving a second
full transition (Agrarian -> Classical) through game.py's real UI, proving
the era-transition framework holds up a second time rather than having
been built to fit exactly one case.
"""

import pytest

import info_content
import research
import sim
import sustainability
import transition


def push_to_agrarian(game_env):
    """The exact Tribal->Agrarian conditions test_agrarian_era.py's own
    push_to_agrarian_ready() already exercises -- shared here as the first
    half of getting all the way to Classical."""
    state = game_env.state
    tree = game_env.module.tree
    state.resources["knowledge"] = 100.0
    tree.research("fire_keeping", state.resources)
    tree.research("foraging_lore", state.resources)
    state.population = 15
    game_env.module.render()
    game_env.elements["advance-era-button"].dispatch("click", None)


def push_to_classical_ready(game_env):
    """Continues past push_to_agrarian() to satisfy every Agrarian->
    Classical requirement: tier 3 has to have two nodes researched (to
    unlock tier 4, the "min_tier" requirement), and population has to reach
    25. Researching plow_and_furrow/seed_selection (tier 3) first requires
    tier 2 to already be unlocked, which two Tribal tier-1 discoveries
    already did back in push_to_agrarian(); it also requires their own
    tier-2 prerequisites (stone_knapping/seasonal_rounds) to actually be
    researched, not just tier 2 being open, since prerequisites are
    per-node, not per-tier."""
    state = game_env.state
    tree = game_env.module.tree
    state.resources["knowledge"] = 1000.0
    tree.research("stone_knapping", state.resources)
    tree.research("seasonal_rounds", state.resources)
    tree.research("plow_and_furrow", state.resources)
    tree.research("seed_selection", state.resources)
    state.population = 25


# --- sim.py: Administrators / Canals -------------------------------------
def test_administrators_and_canals_exist_but_are_not_available_before_classical(game_env):
    assert "administrators" in sim.ROLES
    assert "canals" in sim.BUILDINGS
    for era in ("tribal", "agrarian"):
        assert "administrators" not in sim.roles_for_era(era)
        assert "canals" not in sim.buildings_for_era(era)
    assert "administrators" in sim.roles_for_era("classical")
    assert "canals" in sim.buildings_for_era("classical")
    # Cumulative, not replaced: Classical still has every earlier role too.
    assert set(sim.roles_for_era("agrarian")).issubset(set(sim.roles_for_era("classical")))


def test_a_fresh_settlement_starts_with_zero_administrators_and_canals():
    state = sim.CityState()
    assert state.allocation["administrators"] == 0
    assert state.buildings["canals"] == 0


def test_an_unstaffed_canal_adds_nothing_to_food_output():
    """The doc's own Classical sources are explicit that canal management
    required coordinated labor, not just the canal itself -- so a canal
    with no administrators assigned should behave exactly like no canal at
    all, not like a half-working one."""
    no_canal = sim.CityState(era="classical")
    no_canal.allocation = dict.fromkeys(sim.ROLES, 0)
    no_canal.allocation["farmers"] = 4
    no_canal.resources["food"] = 0.0

    unstaffed_canal = sim.CityState(era="classical")
    unstaffed_canal.allocation = dict.fromkeys(sim.ROLES, 0)
    unstaffed_canal.allocation["farmers"] = 4
    unstaffed_canal.buildings["canals"] = 2
    unstaffed_canal.resources["food"] = 0.0

    no_canal_report = no_canal.advance_season()
    unstaffed_report = unstaffed_canal.advance_season()

    assert unstaffed_report["canal_staffing_ratio"] == 0.0
    assert unstaffed_report["food_gathered"] == pytest.approx(no_canal_report["food_gathered"])


def test_a_staffed_canal_boosts_farmer_food_output():
    unstaffed = sim.CityState(era="classical")
    unstaffed.population = 12
    unstaffed.allocation = dict.fromkeys(sim.ROLES, 0)
    unstaffed.allocation["farmers"] = 4
    unstaffed.buildings["canals"] = 2
    unstaffed.resources["food"] = 0.0

    staffed = sim.CityState(era="classical")
    staffed.population = 12
    staffed.allocation = dict.fromkeys(sim.ROLES, 0)
    staffed.allocation["farmers"] = 4
    staffed.allocation["administrators"] = 4  # exactly ADMINISTRATORS_PER_CANAL * canals
    staffed.buildings["canals"] = 2
    staffed.resources["food"] = 0.0

    unstaffed_report = unstaffed.advance_season()
    staffed_report = staffed.advance_season()

    assert staffed_report["canal_staffing_ratio"] == pytest.approx(1.0)
    assert staffed_report["food_gathered"] > unstaffed_report["food_gathered"]


def test_canal_staffing_ratio_is_capped_at_one_extra_administrators_dont_help_further():
    fully_staffed = sim.CityState(era="classical")
    fully_staffed.population = 12
    fully_staffed.resources["tools"] = fully_staffed.population  # saturate tool_factor identically below
    fully_staffed.allocation = dict.fromkeys(sim.ROLES, 0)
    fully_staffed.allocation["farmers"] = 4
    fully_staffed.allocation["administrators"] = 4
    fully_staffed.buildings["canals"] = 2
    fully_staffed.resources["food"] = 0.0

    over_staffed = sim.CityState(era="classical")
    over_staffed.population = 44
    over_staffed.resources["tools"] = over_staffed.population  # same reason -- isolate canal staffing only
    over_staffed.allocation = dict.fromkeys(sim.ROLES, 0)
    over_staffed.allocation["farmers"] = 4
    over_staffed.allocation["administrators"] = 40  # far more than the canals need
    over_staffed.buildings["canals"] = 2
    over_staffed.resources["food"] = 0.0

    fully_report = fully_staffed.advance_season()
    over_report = over_staffed.advance_season()

    assert fully_report["canal_staffing_ratio"] == pytest.approx(1.0)
    assert over_report["canal_staffing_ratio"] == pytest.approx(1.0)
    assert fully_report["food_gathered"] == pytest.approx(over_report["food_gathered"])


def test_canal_yield_bonus_from_research_increases_a_staffed_canals_output():
    effects_plain = dict(sim.NEUTRAL_EFFECTS)
    effects_boosted = dict(sim.NEUTRAL_EFFECTS)
    effects_boosted["canal_yield_bonus"] = 0.3

    plain = sim.CityState(era="classical")
    plain.population = 12
    plain.allocation = dict.fromkeys(sim.ROLES, 0)
    plain.allocation["farmers"] = 4
    plain.allocation["administrators"] = 4
    plain.buildings["canals"] = 2
    plain.resources["food"] = 0.0

    boosted = sim.CityState(era="classical")
    boosted.population = 12
    boosted.allocation = dict.fromkeys(sim.ROLES, 0)
    boosted.allocation["farmers"] = 4
    boosted.allocation["administrators"] = 4
    boosted.buildings["canals"] = 2
    boosted.resources["food"] = 0.0

    plain_report = plain.advance_season(effects_plain)
    boosted_report = boosted.advance_season(effects_boosted)

    assert boosted_report["food_gathered"] > plain_report["food_gathered"]


def test_canal_food_still_counts_toward_land_extraction():
    """Same constraint Milestone 8 held Farmers to: canal-boosted output
    isn't a separate economy exempt from the land's own limits."""
    state = sim.CityState(era="classical")
    state.population = 20
    state.allocation = dict.fromkeys(sim.ROLES, 0)
    state.allocation["farmers"] = 10
    state.allocation["administrators"] = 10
    state.buildings["canals"] = 5

    report = state.advance_season()
    assert report["extraction"] == report["food_gathered"]
    assert report["extraction"] > report["sustainable_yield"]


# --- sustainability.py: administrative overextension ----------------------
def test_administrator_overextension_has_no_resilience_effect_before_classical():
    state = sim.CityState()  # tribal
    state.allocation["administrators"] = 0  # can't even be assigned yet, but check anyway
    assert sustainability._administrative_overextension_penalty(state) == 0.0

    agrarian_state = sim.CityState(era="agrarian")
    agrarian_state.population = 20
    agrarian_state.allocation = dict.fromkeys(sim.ROLES, 0)
    agrarian_state.allocation["administrators"] = 20  # shouldn't be reachable, but zero either way
    assert sustainability._administrative_overextension_penalty(agrarian_state) == 0.0


def test_a_small_administrator_share_is_not_penalised():
    state = sim.CityState(era="classical")
    state.population = 20
    state.allocation = dict.fromkeys(sim.ROLES, 0)
    state.allocation["foragers"] = 18
    state.allocation["administrators"] = 2  # 10% of the workforce
    assert sustainability._administrative_overextension_penalty(state) == 0.0


def test_a_top_heavy_administration_costs_resilience_from_classical_on():
    """Isolated so the pre-existing role_diversity() term (which rewards
    spreading across more roles, administrators included) can't confound
    the comparison: both settlements split their workforce 50/50 across
    exactly two roles, so they have IDENTICAL diversity and IDENTICAL
    food/tool resilience inputs. The only difference is which second role
    the other half of the workforce sits in."""
    diversified_without_admin = sim.CityState(era="classical")
    diversified_without_admin.population = 20
    diversified_without_admin.allocation = dict.fromkeys(sim.ROLES, 0)
    diversified_without_admin.allocation["foragers"] = 10
    diversified_without_admin.allocation["gatherers"] = 10

    top_heavy = sim.CityState(era="classical")
    top_heavy.population = 20
    top_heavy.allocation = dict.fromkeys(sim.ROLES, 0)
    top_heavy.allocation["foragers"] = 10
    top_heavy.allocation["administrators"] = 10

    assert diversified_without_admin.role_diversity() == pytest.approx(top_heavy.role_diversity())
    assert sustainability.resilience(top_heavy) < sustainability.resilience(diversified_without_admin)


def test_administrative_overextension_penalty_is_exactly_what_resilience_subtracts():
    """Whitebox check that resilience() actually applies the penalty this
    function computes, rather than the two silently drifting apart."""
    state = sim.CityState(era="classical")
    state.population = 20
    state.allocation = dict.fromkeys(sim.ROLES, 0)
    state.allocation["foragers"] = 10
    state.allocation["administrators"] = 10

    penalty = sustainability._administrative_overextension_penalty(state)
    assert penalty > 0.0

    seasons_of_food = state.population * sim.FOOD_PER_PERSON * sim.BUFFER_SEASONS
    food_buffer = sustainability._ratio(state.resources["food"], seasons_of_food)
    tool_readiness = sustainability._ratio(state.resources["tools"], state.population)
    diversity = sustainability._clamp(state.role_diversity())
    expected = sustainability._clamp((food_buffer + tool_readiness + diversity) / 3.0 - penalty)

    assert sustainability.resilience(state) == pytest.approx(expected)


def test_administrator_overextension_penalty_is_ratio_based_not_a_raw_count():
    """Doubling population and administrators together shouldn't change the
    penalty -- same ratio-based rule Milestone 8's hoarding penalty used."""
    small = sim.CityState(era="classical")
    small.population = 10
    small.allocation = dict.fromkeys(sim.ROLES, 0)
    small.allocation["foragers"] = 5
    small.allocation["administrators"] = 5

    big = sim.CityState(era="classical")
    big.population = 20
    big.allocation = dict.fromkeys(sim.ROLES, 0)
    big.allocation["foragers"] = 10
    big.allocation["administrators"] = 10

    assert sustainability._administrative_overextension_penalty(
        small
    ) == sustainability._administrative_overextension_penalty(big)


# --- research.py: the six new Classical nodes ------------------------------
def test_classical_nodes_are_gated_until_classical_is_reached():
    tree = research.build_tree(current_era="agrarian")
    tree.researched = [
        "fire_keeping", "foraging_lore", "shared_hearth", "stone_knapping",
        "seasonal_rounds", "kinship_custom", "plow_and_furrow", "seed_selection",
        "communal_granaries", "irrigation_channels", "crop_rotation", "market_custom",
    ]
    assert tree.is_available("canal_engineering") is False
    assert "hasn't reached the Classical era" in " ".join(tree.missing_requirements("canal_engineering"))


def test_classical_nodes_become_reachable_once_the_era_is_reached():
    tree = research.build_tree(current_era="classical")
    resources = {"knowledge": 10_000.0}
    for _ in range(len(tree.nodes)):
        available = tree.available_nodes()
        if not available:
            break
        for node in available:
            tree.research(node.node_id, resources)
    for node_id in (
        "canal_engineering", "managed_irrigation", "temple_administration",
        "monumental_masonry", "trade_networks", "civic_assembly",
    ):
        assert node_id in tree.researched


def test_classical_nodes_chain_back_into_agrarians_late_tier():
    """The same "early choices echo later, across the era boundary" proof
    Milestone 8 gave for Tribal->Agrarian, now shown a second time for
    Agrarian->Classical."""
    late_agrarian = set(
        n.node_id for n in research.NODE_LIST if n.era == "agrarian" and n.tier == research.era_tiers("agrarian")[1]
    )
    early_classical = [n for n in research.NODE_LIST if n.era == "classical" and n.tier == research.era_tiers("classical")[0]]
    assert len(early_classical) == 3
    for node in early_classical:
        assert set(node.prerequisites) & late_agrarian, (
            f"{node.node_id} should chain back into a late-Agrarian node"
        )


def test_civic_assembly_needs_more_community_affinity_than_market_custom():
    civic_assembly = research.NODES["civic_assembly"]
    market_custom = research.NODES["market_custom"]
    assert civic_assembly.min_affinity["community"] > market_custom.min_affinity["community"]


def test_trade_networks_reuses_the_surplus_conversion_bonus_key():
    node = research.NODES["trade_networks"]
    assert node.effects.get("surplus_conversion_bonus") == 0.15


# --- info_content.py: Classical real-world sources -------------------------
def test_classical_info_page_has_real_sources_not_the_pending_placeholder():
    page = info_content.era_info_page("classical")
    assert len(page["sources"]) == 4
    for source in page["sources"]:
        assert source["url"].startswith("https://")
        assert source["label"]
        assert source["note"]


# --- end-to-end: driving a second transition through game.py's real UI ----
def test_advance_era_button_targets_classical_once_agrarian_is_reached(game_env):
    push_to_agrarian(game_env)
    game_env.module.render()

    button = game_env.elements["advance-era-button"]
    assert button.disabled is True
    assert "Classical" in game_env.elements["era-progress-status-display"].innerText


def test_advance_era_button_enables_once_classical_ready_and_transitions_on_click(game_env):
    push_to_agrarian(game_env)
    push_to_classical_ready(game_env)
    game_env.module.render()

    button = game_env.elements["advance-era-button"]
    assert button.disabled is False

    button.dispatch("click", None)

    state = game_env.state
    assert state.era == "classical"
    assert game_env.module.tree.current_era == "classical"
    assert game_env.module.campaign.furthest_era == "classical"


def test_after_transitioning_the_work_and_build_panels_show_administrators_and_canals(game_env):
    push_to_agrarian(game_env)
    push_to_classical_ready(game_env)
    game_env.module.render()
    game_env.elements["advance-era-button"].dispatch("click", None)

    assert "administrators-name" in game_env.elements
    assert "canals-name" in game_env.elements
    assert game_env.elements["administrators-name"].innerText == "Administrators"
    assert game_env.elements["canals-name"].innerText == "Canals"


def test_after_transitioning_the_info_panel_shows_classical_content(game_env):
    push_to_agrarian(game_env)
    push_to_classical_ready(game_env)
    game_env.module.render()
    game_env.elements["advance-era-button"].dispatch("click", None)

    game_env.elements["info-page-toggle-button"].dispatch("click", None)
    assert (
        game_env.elements["info-page-framing"].innerText
        == info_content.era_info_page("classical")["framing"]
    )


def test_after_transitioning_the_log_shows_both_transition_beats(game_env):
    push_to_agrarian(game_env)
    push_to_classical_ready(game_env)
    game_env.module.render()
    game_env.elements["advance-era-button"].dispatch("click", None)

    transition_rows = [e for e in game_env.module.chronicle.entries if e.kind == "transition"]
    assert len(transition_rows) == 2
    assert transition_rows[0].text == transition.TRANSITION_BEATS[("tribal", "agrarian")]
    assert transition_rows[1].text == transition.TRANSITION_BEATS[("agrarian", "classical")]


def test_after_transitioning_the_advance_era_button_reports_nothing_further_yet(game_env):
    """Classical -> Medieval has no requirements table entry yet (that's
    Milestone 10's job), so this really is the current end of the line,
    the same "nothing more to reach" state Agrarian briefly was in before
    this milestone gave it a real transition."""
    push_to_agrarian(game_env)
    push_to_classical_ready(game_env)
    game_env.module.render()
    game_env.elements["advance-era-button"].dispatch("click", None)
    game_env.module.render()

    assert game_env.elements["advance-era-button"].disabled is True
    assert "Nothing more" in game_env.elements["era-progress-status-display"].innerText


def test_a_second_click_after_transitioning_to_classical_does_nothing(game_env):
    push_to_agrarian(game_env)
    push_to_classical_ready(game_env)
    game_env.module.render()
    button = game_env.elements["advance-era-button"]
    button.dispatch("click", None)
    era_after_first = game_env.state.era

    button.dispatch("click", None)
    assert game_env.state.era == era_after_first


def test_season_report_narrates_an_understaffed_canal(game_env):
    push_to_agrarian(game_env)
    push_to_classical_ready(game_env)
    game_env.module.render()
    game_env.elements["advance-era-button"].dispatch("click", None)

    state = game_env.state
    state.resources["materials"] = 1000.0
    state.build("canals")
    state.allocation["administrators"] = 0  # deliberately unstaffed
    game_env.advance_season()

    assert "coordination" in game_env.elements["season-report-display"].innerText


def test_save_round_trip_preserves_classical_state_including_administrators(game_env):
    push_to_agrarian(game_env)
    push_to_classical_ready(game_env)
    game_env.module.render()
    game_env.elements["advance-era-button"].dispatch("click", None)

    state = game_env.state
    state.allocation["administrators"] = 6
    state.buildings["canals"] = 3

    saved = game_env.module.get_state()

    fresh = save_reload(game_env.module, saved)
    assert fresh.era == "classical"
    assert fresh.allocation["administrators"] == 6
    assert fresh.buildings["canals"] == 3


def test_an_old_save_missing_classical_keys_loads_cleanly_with_defaults():
    """A save written by a build before Milestone 9 has no "administrators"
    or "canals" entries in its city dict at all -- CITY_KEYED_DICTS'
    key-by-key restore (Milestone 4's audit fix) should leave the live
    CityState's defaults (0) in place for both rather than raising, the
    exact forward-compatibility standard every prior era addition has been
    held to."""
    import research as research_mod
    import save as save_mod
    import sim as sim_mod

    old_style_allocation = {"foragers": 3, "gatherers": 2, "crafters": 0, "keepers": 0, "farmers": 0}
    old_style_buildings = {"shelter": 2, "granary": 0, "hearth": 1, "toolworks": 0, "farmland": 0}
    data = {
        "save_version": 1,
        "game": "continuum",
        "era_order": list(sim_mod.ERA_ORDER),
        "current_era": "agrarian",
        "furthest_era": "agrarian",
        "revisiting": None,
        "current_state": {
            "city": {
                "era": "agrarian",
                "season": 3,
                "population": 12,
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
    assert campaign.state.allocation["administrators"] == 0
    assert campaign.state.buildings["canals"] == 0


# --- proxy-destruction discipline (constraint from CLAUDE.md) ------------
def test_rendering_the_work_panel_destroys_the_proxy_for_administrators(game_env):
    push_to_agrarian(game_env)
    push_to_classical_ready(game_env)
    game_env.module.render()
    game_env.elements["advance-era-button"].dispatch("click", None)

    module = game_env.module
    module.render()
    proxies = module._work_button_proxies
    key = ("administrators", "add")
    assert key in proxies
    first_proxy = proxies[key]
    assert first_proxy.destroyed is False

    module.render()
    second_proxy = proxies[key]
    assert first_proxy.destroyed is True
    assert second_proxy.destroyed is False


def test_rendering_the_buildings_panel_destroys_the_proxy_for_canals(game_env):
    push_to_agrarian(game_env)
    push_to_classical_ready(game_env)
    game_env.module.render()
    game_env.elements["advance-era-button"].dispatch("click", None)

    module = game_env.module
    module.render()
    proxies = module._building_button_proxies
    assert "canals" in proxies
    first_proxy = proxies["canals"]
    assert first_proxy.destroyed is False

    module.render()
    second_proxy = proxies["canals"]
    assert first_proxy.destroyed is True
    assert second_proxy.destroyed is False


def save_reload(module, saved_dict):
    """Same round-trip helper test_agrarian_era.py already uses: loads
    into a second, independent Campaign via a real JSON round-trip."""
    import copy
    import json

    import research as research_mod
    import save as save_mod
    import sim as sim_mod

    plain = json.loads(json.dumps(copy.deepcopy(saved_dict)))
    fresh_campaign = save_mod.Campaign(sim_mod.CityState(), research_mod.build_tree())
    assert fresh_campaign.load_dict(plain) is True
    return fresh_campaign.state
