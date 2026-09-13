"""Milestone 10 — third full era transition, Classical -> Medieval.

Covers the concrete Medieval content this milestone had to invent (see
CLAUDE.md's Milestone 10 build notes for the design rationale): the
Guildmasters role and Public Works building (and why, unlike Canals, Public
Works deliberately has NO staffing dependency), the sustainability
resilience BONUS for investing in public-works coverage ahead of a bad
season (a genuinely new shape — the tree's first bonus rather than another
penalty), the six new research nodes chaining back into Classical's own
late tier, the Medieval info-panel content, and — the actual point of this
milestone, same as Milestones 8-9's own closing sections — driving a third
full transition (Classical -> Medieval) through game.py's real UI, proving
the era-transition framework holds up a third time.
"""

import pytest

import info_content
import research
import sim
import sustainability
import transition


def push_to_agrarian(game_env):
    """Same Tribal->Agrarian conditions test_agrarian_era.py's/
    test_classical_era.py's own helpers already exercise."""
    state = game_env.state
    tree = game_env.module.tree
    state.resources["knowledge"] = 100.0
    tree.research("fire_keeping", state.resources)
    tree.research("foraging_lore", state.resources)
    state.population = 15
    game_env.module.render()
    game_env.elements["advance-era-button"].dispatch("click", None)


def push_to_classical(game_env):
    """Continues past push_to_agrarian() and actually clicks through to
    Classical -- test_classical_era.py's push_to_classical_ready() only
    satisfies the requirements without clicking, since that milestone
    tested the click itself separately; here we need to actually be
    standing in Classical before pushing on toward Medieval."""
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


def push_to_medieval_ready(game_env):
    """Continues past push_to_classical() to satisfy every Classical->
    Medieval requirement: tier 6 has to be UNLOCKED (two tier-5 nodes
    researched), which itself needs tier 5 unlocked (two tier-4 nodes
    researched first), and population has to reach 40. Shelter/hearth are
    bumped up alongside population -- without it, a population of 40
    dropped onto Classical's small starting shelter/hearth stock craters
    the equity and livability components hard enough to leave the score
    below "Strained", which the transition also requires."""
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


def push_to_medieval(game_env):
    """All the way to Medieval, clicking through every transition."""
    push_to_agrarian(game_env)
    push_to_classical(game_env)
    push_to_medieval_ready(game_env)
    game_env.module.render()
    game_env.elements["advance-era-button"].dispatch("click", None)


# --- sim.py: Guildmasters / Public Works ----------------------------------
def test_guildmasters_and_public_works_exist_but_are_not_available_before_medieval():
    assert "guildmasters" in sim.ROLES
    assert "public_works" in sim.BUILDINGS
    for era in ("tribal", "agrarian", "classical"):
        assert "guildmasters" not in sim.roles_for_era(era)
        assert "public_works" not in sim.buildings_for_era(era)
    assert "guildmasters" in sim.roles_for_era("medieval")
    assert "public_works" in sim.buildings_for_era("medieval")
    # Cumulative, not replaced: Medieval still has every earlier role too.
    assert set(sim.roles_for_era("classical")).issubset(set(sim.roles_for_era("medieval")))
    assert set(sim.buildings_for_era("classical")).issubset(set(sim.buildings_for_era("medieval")))


def test_a_fresh_settlement_starts_with_zero_guildmasters_and_public_works():
    state = sim.CityState()
    assert state.allocation["guildmasters"] == 0
    assert state.buildings["public_works"] == 0


def test_guildmasters_produce_more_tools_per_person_than_crafters():
    crafters_only = sim.CityState(era="medieval")
    crafters_only.allocation = dict.fromkeys(sim.ROLES, 0)
    crafters_only.allocation["crafters"] = 5
    crafters_only.resources["materials"] = 1000.0

    guildmasters_only = sim.CityState(era="medieval")
    guildmasters_only.allocation = dict.fromkeys(sim.ROLES, 0)
    guildmasters_only.allocation["guildmasters"] = 5
    guildmasters_only.resources["materials"] = 1000.0

    crafters_report = crafters_only.advance_season()
    guildmasters_report = guildmasters_only.advance_season()

    assert guildmasters_report["tools_made"] > crafters_report["tools_made"]


def test_toolworks_bonus_applies_to_guildmaster_tool_output_too():
    """Same shared-economy discipline Farmers/Canals were held to: a
    Guildmaster is not exempt from the same Knapping Site multiplier a
    Crafter already gets."""
    plain = sim.CityState(era="medieval")
    plain.allocation = dict.fromkeys(sim.ROLES, 0)
    plain.allocation["guildmasters"] = 4
    plain.resources["materials"] = 1000.0

    with_toolworks = sim.CityState(era="medieval")
    with_toolworks.allocation = dict.fromkeys(sim.ROLES, 0)
    with_toolworks.allocation["guildmasters"] = 4
    with_toolworks.buildings["toolworks"] = 2
    with_toolworks.resources["materials"] = 1000.0

    plain_report = plain.advance_season()
    boosted_report = with_toolworks.advance_season()

    assert boosted_report["tools_made"] > plain_report["tools_made"]


def test_public_works_coverage_is_zero_with_no_buildings():
    state = sim.CityState(era="medieval")
    assert state.public_works_coverage() == 0.0


def test_public_works_coverage_scales_with_building_count():
    state = sim.CityState(era="medieval")
    state.buildings["public_works"] = 3
    assert state.public_works_coverage() == pytest.approx(3 * sim.PUBLIC_WORKS_COVERAGE_PER_BUILDING)


def test_public_works_bonus_effect_increases_coverage():
    state = sim.CityState(era="medieval")
    state.buildings["public_works"] = 2
    plain = state.public_works_coverage()

    effects_boosted = dict(sim.NEUTRAL_EFFECTS)
    effects_boosted["public_works_bonus"] = 0.25
    boosted = state.public_works_coverage(effects_boosted)

    assert boosted == pytest.approx(plain * 1.25)


def test_report_includes_public_works_fields_for_narration():
    state = sim.CityState(era="medieval")
    state.buildings["public_works"] = 1
    report = state.advance_season()
    assert report["public_works"] == 1
    assert 0.0 <= report["public_works_coverage_ratio"] <= 1.0


def test_public_works_has_no_production_effect_of_its_own():
    """Deliberately different from Farmland/Canals: building Public Works
    changes nothing about food/materials/tools output. It's read only by
    sustainability.py's resilience(), never by the season loop's own
    production math."""
    no_public_works = sim.CityState(era="medieval")
    no_public_works.allocation = dict.fromkeys(sim.ROLES, 0)
    no_public_works.allocation["foragers"] = 5

    with_public_works = sim.CityState(era="medieval")
    with_public_works.allocation = dict.fromkeys(sim.ROLES, 0)
    with_public_works.allocation["foragers"] = 5
    with_public_works.buildings["public_works"] = 3
    with_public_works.resources["materials"] = no_public_works.resources["materials"]

    report_a = no_public_works.advance_season()
    report_b = with_public_works.advance_season()

    assert report_a["food_gathered"] == pytest.approx(report_b["food_gathered"])
    assert report_a["materials_gathered"] == pytest.approx(report_b["materials_gathered"])
    assert report_a["tools_made"] == pytest.approx(report_b["tools_made"])


# --- sustainability.py: public-works shock resilience ---------------------
def test_public_works_resilience_bonus_has_no_effect_before_medieval():
    for era in ("tribal", "agrarian", "classical"):
        state = sim.CityState(era=era)
        state.buildings["public_works"] = 10  # shouldn't be reachable, but zero either way
        assert sustainability._public_works_resilience_bonus(state) == 0.0


def test_public_works_resilience_bonus_is_zero_with_no_public_works():
    state = sim.CityState(era="medieval")
    assert sustainability._public_works_resilience_bonus(state) == 0.0


def test_public_works_resilience_bonus_increases_with_coverage_then_caps():
    state = sim.CityState(era="medieval")
    state.population = 30

    state.buildings["public_works"] = 0
    none = sustainability._public_works_resilience_bonus(state)

    state.buildings["public_works"] = 1
    partial = sustainability._public_works_resilience_bonus(state)

    state.buildings["public_works"] = 10  # far more coverage than population needs
    full = sustainability._public_works_resilience_bonus(state)

    assert none == 0.0
    assert 0.0 < partial < full
    assert full == pytest.approx(sustainability.PUBLIC_WORKS_RESILIENCE_BONUS_WEIGHT)


def test_public_works_resilience_bonus_is_exactly_what_resilience_adds():
    """Whitebox check that resilience() actually applies the bonus this
    function computes, rather than the two silently drifting apart -- the
    same discipline Milestone 9's admin-overextension test already used."""
    state = sim.CityState(era="medieval")
    state.population = 20
    state.buildings["public_works"] = 2

    bonus = sustainability._public_works_resilience_bonus(state)
    assert bonus > 0.0

    seasons_of_food = state.population * sim.FOOD_PER_PERSON * sim.BUFFER_SEASONS
    food_buffer = sustainability._ratio(state.resources["food"], seasons_of_food)
    tool_readiness = sustainability._ratio(state.resources["tools"], state.population)
    diversity = sustainability._clamp(state.role_diversity())
    admin_penalty = sustainability._administrative_overextension_penalty(state)
    expected = sustainability._clamp(
        (food_buffer + tool_readiness + diversity) / 3.0 - admin_penalty + bonus
    )

    assert sustainability.resilience(state) == pytest.approx(expected)


def test_public_works_resilience_bonus_is_ratio_based_not_a_raw_count():
    """Doubling population and public-works buildings together shouldn't
    change the bonus -- same ratio-based rule every prior era-specific
    adjustment in this file has been held to."""
    small = sim.CityState(era="medieval")
    small.population = 15
    small.buildings["public_works"] = 1

    big = sim.CityState(era="medieval")
    big.population = 30
    big.buildings["public_works"] = 2

    assert sustainability._public_works_resilience_bonus(
        small
    ) == pytest.approx(sustainability._public_works_resilience_bonus(big))


def test_public_works_investment_increases_resilience_holding_everything_else_fixed():
    """Isolated the way Milestone 9's admin-overextension test isolated its
    own comparison: same population, same allocation, same resources --
    the only difference is Public Works building count. Unlike the
    Classical penalty, this mechanic never touches `allocation` at all, so
    there's no role_diversity() interaction to guard against here -- worth
    stating explicitly rather than leaving it to be rediscovered."""
    without = sim.CityState(era="medieval")
    without.population = 20
    without.allocation = dict.fromkeys(sim.ROLES, 0)
    without.allocation["foragers"] = 10
    without.allocation["gatherers"] = 10

    with_investment = sim.CityState(era="medieval")
    with_investment.population = 20
    with_investment.allocation = dict.fromkeys(sim.ROLES, 0)
    with_investment.allocation["foragers"] = 10
    with_investment.allocation["gatherers"] = 10
    with_investment.buildings["public_works"] = 3

    assert without.role_diversity() == pytest.approx(with_investment.role_diversity())
    assert sustainability.resilience(with_investment) > sustainability.resilience(without)


# --- research.py: the six new Medieval nodes ------------------------------
def test_medieval_nodes_are_gated_until_medieval_is_reached():
    tree = research.build_tree(current_era="classical")
    tree.researched = [
        "fire_keeping", "foraging_lore", "shared_hearth", "stone_knapping",
        "seasonal_rounds", "kinship_custom", "plow_and_furrow", "seed_selection",
        "communal_granaries", "irrigation_channels", "crop_rotation", "market_custom",
        "canal_engineering", "managed_irrigation", "temple_administration",
        "monumental_masonry", "trade_networks", "civic_assembly",
    ]
    assert tree.is_available("guild_workshops") is False
    assert "hasn't reached the Medieval era" in " ".join(tree.missing_requirements("guild_workshops"))


def test_medieval_nodes_become_reachable_once_the_era_is_reached():
    tree = research.build_tree(current_era="medieval")
    resources = {"knowledge": 10_000.0}
    for _ in range(len(tree.nodes)):
        available = tree.available_nodes()
        if not available:
            break
        for node in available:
            tree.research(node.node_id, resources)
    for node_id in (
        "guild_workshops", "trade_zoning", "municipal_charter",
        "master_guilds", "public_sanitation", "free_city_charter",
    ):
        assert node_id in tree.researched


def test_medieval_nodes_chain_back_into_classicals_late_tier():
    """The same "early choices echo later, across the era boundary" proof
    Milestones 8-9 gave, now shown a third time for Classical->Medieval."""
    late_classical = set(
        n.node_id for n in research.NODE_LIST if n.era == "classical" and n.tier == research.era_tiers("classical")[1]
    )
    early_medieval = [n for n in research.NODE_LIST if n.era == "medieval" and n.tier == research.era_tiers("medieval")[0]]
    assert len(early_medieval) == 3
    for node in early_medieval:
        assert set(node.prerequisites) & late_classical, (
            f"{node.node_id} should chain back into a late-Classical node"
        )


def test_free_city_charter_needs_more_community_affinity_than_municipal_charter():
    free_city_charter = research.NODES["free_city_charter"]
    municipal_charter = research.NODES["municipal_charter"]
    civic_assembly = research.NODES["civic_assembly"]
    assert free_city_charter.min_affinity["community"] > municipal_charter.min_affinity["community"]
    assert municipal_charter.min_affinity["community"] > civic_assembly.min_affinity["community"]


def test_municipal_charter_and_free_city_charter_grant_the_public_works_bonus_key():
    assert research.NODES["municipal_charter"].effects.get("public_works_bonus") == 0.25
    assert research.NODES["free_city_charter"].effects.get("public_works_bonus") == 0.15


def test_medieval_tiers_are_the_next_two_global_tiers_after_classical():
    assert research.era_tiers("medieval") == [
        research.era_tiers("classical")[-1] + 1,
        research.era_tiers("classical")[-1] + 2,
    ]


# --- info_content.py: Medieval real-world sources -------------------------
def test_medieval_info_page_has_real_sources_not_the_pending_placeholder():
    page = info_content.era_info_page("medieval")
    assert len(page["sources"]) == 4
    for source in page["sources"]:
        assert source["url"].startswith("https://")
        assert source["label"]
        assert source["note"]


# --- transition.py: Classical -> Medieval requirements --------------------
def test_classical_to_medieval_requirements_are_defined():
    requirement = transition.TRANSITION_REQUIREMENTS["classical"]
    assert requirement["to_era"] == "medieval"
    assert requirement["min_population"] == 40
    assert requirement["min_tier"] == research.era_tiers("classical")[-1]


def test_next_era_for_classical_is_medieval():
    assert transition.next_era_for("classical") == "medieval"


# --- end-to-end: driving a third transition through game.py's real UI -----
def test_advance_era_button_targets_medieval_once_classical_is_reached(game_env):
    push_to_agrarian(game_env)
    push_to_classical(game_env)
    game_env.module.render()

    button = game_env.elements["advance-era-button"]
    assert button.disabled is True
    assert "Medieval" in game_env.elements["era-progress-status-display"].innerText


def test_advance_era_button_enables_once_medieval_ready_and_transitions_on_click(game_env):
    push_to_agrarian(game_env)
    push_to_classical(game_env)
    push_to_medieval_ready(game_env)
    game_env.module.render()

    button = game_env.elements["advance-era-button"]
    assert button.disabled is False

    button.dispatch("click", None)

    state = game_env.state
    assert state.era == "medieval"
    assert game_env.module.tree.current_era == "medieval"
    assert game_env.module.campaign.furthest_era == "medieval"


def test_after_transitioning_the_work_and_build_panels_show_guildmasters_and_public_works(game_env):
    push_to_medieval(game_env)

    assert "guildmasters-name" in game_env.elements
    assert "public_works-name" in game_env.elements
    assert game_env.elements["guildmasters-name"].innerText == "Guildmasters"
    assert game_env.elements["public_works-name"].innerText == "Public Works"


def test_after_transitioning_the_info_panel_shows_medieval_content(game_env):
    push_to_medieval(game_env)

    game_env.elements["info-page-toggle-button"].dispatch("click", None)
    assert (
        game_env.elements["info-page-framing"].innerText
        == info_content.era_info_page("medieval")["framing"]
    )


def test_after_transitioning_the_log_shows_all_three_transition_beats(game_env):
    push_to_medieval(game_env)

    transition_rows = [e for e in game_env.module.chronicle.entries if e.kind == "transition"]
    assert len(transition_rows) == 3
    assert transition_rows[0].text == transition.TRANSITION_BEATS[("tribal", "agrarian")]
    assert transition_rows[1].text == transition.TRANSITION_BEATS[("agrarian", "classical")]
    assert transition_rows[2].text == transition.TRANSITION_BEATS[("classical", "medieval")]


def test_after_transitioning_the_advance_era_button_reports_nothing_further_yet(game_env):
    """Medieval -> Industrial has no requirements table entry yet (that's
    a later milestone's job), so this really is the current end of the
    line -- the same "nothing more to reach" state Classical was briefly
    in before this milestone gave it a real transition."""
    push_to_medieval(game_env)
    game_env.module.render()

    assert game_env.elements["advance-era-button"].disabled is True
    assert "Nothing more" in game_env.elements["era-progress-status-display"].innerText


def test_a_second_click_after_transitioning_to_medieval_does_nothing(game_env):
    push_to_agrarian(game_env)
    push_to_classical(game_env)
    push_to_medieval_ready(game_env)
    game_env.module.render()
    button = game_env.elements["advance-era-button"]
    button.dispatch("click", None)
    era_after_first = game_env.state.era

    button.dispatch("click", None)
    assert game_env.state.era == era_after_first


def test_season_report_narrates_undercovered_public_works(game_env):
    push_to_medieval(game_env)

    state = game_env.state
    state.resources["materials"] = 1000.0
    state.build("public_works")  # one building, population is well above coverage
    state.population = 100
    game_env.advance_season()

    assert "cover" in game_env.elements["season-report-display"].innerText.lower()


def test_save_round_trip_preserves_medieval_state_including_guildmasters(game_env):
    push_to_medieval(game_env)

    state = game_env.state
    state.allocation["guildmasters"] = 5
    state.buildings["public_works"] = 4

    saved = game_env.module.get_state()

    fresh = save_reload(game_env.module, saved)
    assert fresh.era == "medieval"
    assert fresh.allocation["guildmasters"] == 5
    assert fresh.buildings["public_works"] == 4


def test_an_old_save_missing_medieval_keys_loads_cleanly_with_defaults():
    """A save written by a build before Milestone 10 has no "guildmasters"
    or "public_works" entries in its city dict at all -- CITY_KEYED_DICTS'
    key-by-key restore should leave the live CityState's defaults (0) in
    place for both rather than raising, the exact forward-compatibility
    standard every prior era addition has been held to."""
    import research as research_mod
    import save as save_mod
    import sim as sim_mod

    old_style_allocation = {
        "foragers": 3, "gatherers": 2, "crafters": 0, "keepers": 0,
        "farmers": 0, "administrators": 2,
    }
    old_style_buildings = {
        "shelter": 2, "granary": 0, "hearth": 1, "toolworks": 0,
        "farmland": 0, "canals": 1,
    }
    data = {
        "save_version": 1,
        "game": "continuum",
        "era_order": list(sim_mod.ERA_ORDER),
        "current_era": "classical",
        "furthest_era": "classical",
        "revisiting": None,
        "current_state": {
            "city": {
                "era": "classical",
                "season": 5,
                "population": 30,
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
    assert campaign.state.allocation["guildmasters"] == 0
    assert campaign.state.buildings["public_works"] == 0


# --- proxy-destruction discipline (constraint from CLAUDE.md) ------------
def test_rendering_the_work_panel_destroys_the_proxy_for_guildmasters(game_env):
    push_to_medieval(game_env)

    module = game_env.module
    module.render()
    proxies = module._work_button_proxies
    key = ("guildmasters", "add")
    assert key in proxies
    first_proxy = proxies[key]
    assert first_proxy.destroyed is False

    module.render()
    second_proxy = proxies[key]
    assert first_proxy.destroyed is True
    assert second_proxy.destroyed is False


def test_rendering_the_buildings_panel_destroys_the_proxy_for_public_works(game_env):
    push_to_medieval(game_env)

    module = game_env.module
    module.render()
    proxies = module._building_button_proxies
    assert "public_works" in proxies
    first_proxy = proxies["public_works"]
    assert first_proxy.destroyed is False

    module.render()
    second_proxy = proxies["public_works"]
    assert first_proxy.destroyed is True
    assert second_proxy.destroyed is False


def save_reload(module, saved_dict):
    """Same round-trip helper test_agrarian_era.py/test_classical_era.py
    already use: loads into a second, independent Campaign via a real JSON
    round-trip."""
    import copy
    import json

    import research as research_mod
    import save as save_mod
    import sim as sim_mod

    plain = json.loads(json.dumps(copy.deepcopy(saved_dict)))
    fresh_campaign = save_mod.Campaign(sim_mod.CityState(), research_mod.build_tree())
    assert fresh_campaign.load_dict(plain) is True
    return fresh_campaign.state
