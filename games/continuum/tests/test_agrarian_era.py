"""Milestone 8 — first full era transition, Tribal -> Agrarian.

Covers the concrete Agrarian content this milestone had to invent (see
CLAUDE.md's Milestone 8 build notes for the design rationale): the Farmers
role and Farmland building, the `surplus` resource fed by spoilage
conversion, the sustainability equity adjustment surplus hoarding costs,
the six new research nodes, the Agrarian info-panel content, and — the
actual point of this milestone — driving a full Tribal->Agrarian
transition through game.py's real UI (the Era Progress button), not just
through transition.attempt_transition() directly the way Milestone 7's own
tests did.
"""

import info_content
import research
import sim
import sustainability
import transition


def push_to_agrarian_ready(game_env):
    """Pushes a live game_env's settlement past every Tribal->Agrarian
    requirement, the same conditions tests/test_transition_system.py
    already exercises directly against a bare Campaign."""
    state = game_env.state
    tree = game_env.module.tree
    state.resources["knowledge"] = 100.0
    tree.research("fire_keeping", state.resources)
    tree.research("foraging_lore", state.resources)
    state.population = 15


# --- sim.py: Farmers / Farmland / surplus --------------------------------
def test_farmers_and_farmland_exist_but_are_not_available_in_tribal(game_env):
    assert "farmers" in sim.ROLES
    assert "farmland" in sim.BUILDINGS
    assert "farmers" not in sim.roles_for_era("tribal")
    assert "farmland" not in sim.buildings_for_era("tribal")
    assert "farmers" in sim.roles_for_era("agrarian")
    assert "farmland" in sim.buildings_for_era("agrarian")
    # Cumulative, not replaced: Agrarian still has every Tribal role too.
    assert set(sim.roles_for_era("tribal")).issubset(set(sim.roles_for_era("agrarian")))


def test_a_fresh_settlement_starts_with_zero_farmers_and_farmland():
    state = sim.CityState()
    assert state.allocation["farmers"] == 0
    assert state.buildings["farmland"] == 0
    assert state.resources["surplus"] == 0.0


def test_farmers_produce_more_food_than_foragers_before_any_building_bonus():
    """Grounded in the doc's real-world sources: settled agriculture was a
    genuine productivity jump over foraging."""
    assert sim.FOOD_PER_FARMER > sim.FOOD_PER_FORAGER


def test_farmland_boosts_farmer_food_output():
    plain = sim.CityState(era="agrarian")
    plain.allocation = dict.fromkeys(sim.ROLES, 0)
    plain.allocation["farmers"] = 4
    plain.resources["food"] = 0.0

    farmed = sim.CityState(era="agrarian")
    farmed.allocation = dict.fromkeys(sim.ROLES, 0)
    farmed.allocation["farmers"] = 4
    farmed.buildings["farmland"] = 2
    farmed.resources["food"] = 0.0

    plain.advance_season()
    farmed.advance_season()

    assert farmed.last_report["food_gathered"] > plain.last_report["food_gathered"]


def test_farmer_output_still_scales_with_land_health_and_tools():
    """Agriculture is better, not exempt from the land's own limits --
    Milestone 8's own design constraint (see CLAUDE.md build notes)."""
    healthy = sim.CityState(era="agrarian")
    healthy.allocation = dict.fromkeys(sim.ROLES, 0)
    healthy.allocation["farmers"] = 3
    healthy.land_health = 1.0

    degraded = sim.CityState(era="agrarian")
    degraded.allocation = dict.fromkeys(sim.ROLES, 0)
    degraded.allocation["farmers"] = 3
    degraded.land_health = 0.3

    healthy_report = healthy.advance_season()
    degraded_report = degraded.advance_season()

    assert healthy_report["food_gathered"] > degraded_report["food_gathered"]


def test_farmer_food_counts_toward_land_extraction():
    """Farmers aren't a separate economy -- their harvest pressures the
    same shared land as foraging."""
    state = sim.CityState(era="agrarian")
    state.allocation = dict.fromkeys(sim.ROLES, 0)
    state.allocation["farmers"] = 10  # enough to comfortably exceed the sustainable yield

    report = state.advance_season()
    assert report["extraction"] == report["food_gathered"]  # no gatherers assigned this run
    assert report["extraction"] > report["sustainable_yield"]


# --- sim.py: surplus conversion (Agrarian+) -------------------------------
def test_tribal_era_never_banks_surplus_only_spoils():
    state = sim.CityState()  # era="tribal"
    state.resources["food"] = 1000.0  # force well past storage capacity
    report = state.advance_season()
    assert report["surplus_banked"] == 0.0
    assert state.resources["surplus"] == 0.0
    assert report["spoiled"] > 0.0


def test_agrarian_era_converts_some_spoilage_into_surplus():
    state = sim.CityState(era="agrarian")
    state.resources["food"] = 1000.0
    report = state.advance_season()

    assert report["surplus_banked"] > 0.0
    assert state.resources["surplus"] == report["surplus_banked"]
    # Nothing banked is also spoiled -- the two must add back to what would
    # have spoiled with no conversion at all.
    storage = state.food_storage_capacity(sim.NEUTRAL_EFFECTS)
    would_spoil = 1000.0 - storage  # rough upper bound before this season's harvest
    assert report["spoiled"] < would_spoil + report["food_gathered"]


def test_surplus_conversion_bonus_from_research_increases_the_banked_share():
    effects_plain = dict(sim.NEUTRAL_EFFECTS)
    effects_boosted = dict(sim.NEUTRAL_EFFECTS)
    effects_boosted["surplus_conversion_bonus"] = 0.3

    plain = sim.CityState(era="agrarian")
    plain.resources["food"] = 1000.0
    boosted = sim.CityState(era="agrarian")
    boosted.resources["food"] = 1000.0

    plain_report = plain.advance_season(effects_plain)
    boosted_report = boosted.advance_season(effects_boosted)

    assert boosted_report["surplus_banked"] > plain_report["surplus_banked"]


# --- sustainability.py: surplus hoarding penalty --------------------------
def test_surplus_has_no_equity_effect_before_agrarian():
    state = sim.CityState()  # tribal
    state.resources["surplus"] = 10_000.0  # absurd amount, shouldn't matter yet
    assert sustainability._surplus_hoarding_penalty(state) == 0.0


def test_hoarded_surplus_costs_equity_from_agrarian_on():
    base = sim.CityState(era="agrarian")
    hoarding = sim.CityState(era="agrarian")
    hoarding.resources["surplus"] = 1000.0  # far above any reasonable per-capita share

    assert sustainability.equity(hoarding) < sustainability.equity(base)


def test_surplus_hoarding_penalty_is_ratio_based_not_a_raw_count():
    """Doubling population and surplus together shouldn't change the
    penalty -- same ratio-based rule as every other sustainability input."""
    small = sim.CityState(era="agrarian")
    small.population = 10
    small.resources["surplus"] = 100.0

    big = sim.CityState(era="agrarian")
    big.population = 20
    big.resources["surplus"] = 200.0

    assert sustainability._surplus_hoarding_penalty(small) == sustainability._surplus_hoarding_penalty(big)


# --- research.py: the six new Agrarian nodes ------------------------------
def test_agrarian_nodes_are_gated_until_agrarian_is_reached():
    tree = research.build_tree(current_era="tribal")
    tree.researched = ["fire_keeping", "foraging_lore", "shared_hearth", "stone_knapping", "seasonal_rounds"]
    assert tree.is_available("plow_and_furrow") is False
    assert "hasn't reached the Agrarian era" in " ".join(tree.missing_requirements("plow_and_furrow"))


def test_agrarian_nodes_become_reachable_once_the_era_is_reached():
    tree = research.build_tree(current_era="agrarian")
    resources = {"knowledge": 10_000.0}
    for _ in range(len(tree.nodes)):
        available = tree.available_nodes()
        if not available:
            break
        for node in available:
            tree.research(node.node_id, resources)
    for node_id in ("plow_and_furrow", "seed_selection", "communal_granaries",
                     "irrigation_channels", "crop_rotation", "market_custom"):
        assert node_id in tree.researched


def test_market_custom_grants_the_surplus_conversion_bonus():
    node = research.NODES["market_custom"]
    assert node.effects.get("surplus_conversion_bonus") == 0.2


# --- info_content.py: Agrarian real-world sources -------------------------
def test_agrarian_info_page_has_real_sources_not_the_pending_placeholder():
    page = info_content.era_info_page("agrarian")
    assert len(page["sources"]) == 4
    for source in page["sources"]:
        assert source["url"].startswith("https://")
        assert source["label"]
        assert source["note"]


# --- end-to-end: driving the transition through game.py's real UI --------
def test_advance_era_button_is_disabled_until_ready(game_env):
    button = game_env.elements["advance-era-button"]
    assert button.disabled is True
    assert "Tribal" not in game_env.elements["era-progress-status-display"].innerText
    assert game_env.elements["era-progress-reasons-display"].innerText != ""


def test_advance_era_button_enables_once_ready_and_transitions_on_click(game_env):
    push_to_agrarian_ready(game_env)
    game_env.module.render()

    button = game_env.elements["advance-era-button"]
    assert button.disabled is False
    assert "Agrarian" in game_env.elements["era-progress-status-display"].innerText

    button.dispatch("click", None)

    state = game_env.state
    assert state.era == "agrarian"
    assert game_env.module.tree.current_era == "agrarian"
    assert game_env.module.campaign.furthest_era == "agrarian"


def test_after_transitioning_the_work_and_build_panels_show_farmers_and_farmland(game_env):
    push_to_agrarian_ready(game_env)
    game_env.module.render()
    game_env.elements["advance-era-button"].dispatch("click", None)

    assert "farmers-name" in game_env.elements
    assert "farmland-name" in game_env.elements
    assert game_env.elements["farmers-name"].innerText == "Farmers"
    assert game_env.elements["farmland-name"].innerText == "Farmland"


def test_after_transitioning_the_info_panel_shows_agrarian_content(game_env):
    push_to_agrarian_ready(game_env)
    game_env.module.render()
    game_env.elements["advance-era-button"].dispatch("click", None)

    game_env.elements["info-page-toggle-button"].dispatch("click", None)
    assert (
        game_env.elements["info-page-framing"].innerText
        == info_content.era_info_page("agrarian")["framing"]
    )


def test_after_transitioning_the_log_shows_the_transition_beat(game_env):
    push_to_agrarian_ready(game_env)
    game_env.module.render()
    game_env.elements["advance-era-button"].dispatch("click", None)

    transition_rows = [
        e for e in game_env.module.chronicle.entries if e.kind == "transition"
    ]
    assert len(transition_rows) == 1
    assert transition_rows[0].text == transition.TRANSITION_BEATS[("tribal", "agrarian")]


def test_after_transitioning_the_advance_era_button_points_at_the_next_era(game_env):
    """Since Milestone 9, Agrarian isn't the end of the line either — the
    button should immediately start reporting progress toward Classical
    rather than "nothing more to reach," since transition.py now has an
    entry for Agrarian too. (Before Milestone 9 this asserted the opposite;
    see that milestone's CLAUDE.md build notes.) The freshly-arrived
    settlement isn't ready yet -- push_to_agrarian_ready() only satisfies
    the OLD Tribal->Agrarian bar (population 15), not Agrarian->Classical's
    higher one (population 25) -- so the button should still be disabled."""
    push_to_agrarian_ready(game_env)
    game_env.module.render()
    game_env.elements["advance-era-button"].dispatch("click", None)
    game_env.module.render()

    assert game_env.elements["advance-era-button"].disabled is True
    assert "Classical" in game_env.elements["era-progress-status-display"].innerText


def test_a_second_click_after_transitioning_does_nothing(game_env):
    push_to_agrarian_ready(game_env)
    game_env.module.render()
    button = game_env.elements["advance-era-button"]
    button.dispatch("click", None)
    era_after_first = game_env.state.era

    button.dispatch("click", None)  # button is now disabled/relabelled, but nothing stops a stray dispatch
    assert game_env.state.era == era_after_first


def test_surplus_display_is_hidden_in_a_fresh_tribal_game(game_env):
    assert game_env.elements["surplus-display"].hidden is True


def test_surplus_display_shows_once_agrarian_banks_something(game_env):
    push_to_agrarian_ready(game_env)
    game_env.module.render()
    game_env.elements["advance-era-button"].dispatch("click", None)

    state = game_env.state
    state.resources["food"] = 1000.0
    game_env.advance_season()

    assert game_env.elements["surplus-display"].hidden is False
    assert "Surplus" in game_env.elements["surplus-display"].innerText


def test_save_round_trip_preserves_agrarian_state_including_farmers(game_env):
    push_to_agrarian_ready(game_env)
    game_env.module.render()
    game_env.elements["advance-era-button"].dispatch("click", None)

    state = game_env.state
    state.allocation["farmers"] = 3
    state.buildings["farmland"] = 1
    state.resources["surplus"] = 42.0

    saved = game_env.module.get_state()

    fresh = save_reload(game_env.module, saved)
    assert fresh.era == "agrarian"
    assert fresh.allocation["farmers"] == 3
    assert fresh.buildings["farmland"] == 1
    assert fresh.resources["surplus"] == 42.0


def test_an_old_save_missing_agrarian_keys_loads_cleanly_with_defaults():
    """Every era from Classical on has its own version of this test (see
    e.g. `test_classical_era.py`'s `test_an_old_save_missing_classical_keys_
    loads_cleanly_with_defaults`); Agrarian itself never got one of its own
    (Phase 4 audit finding -- a coverage gap, not a bug: the underlying
    mechanism is `save.py`'s CITY_KEYED_DICTS key-by-key restore, already
    exercised generically by `test_save_system.py`'s
    `test_load_state_tolerates_a_save_whose_keyed_dicts_are_short`, and
    confirmed here to hold for Agrarian's own `farmers`/`farmland`/`surplus`
    keys specifically). A save written by a build before Milestone 8 has no
    `farmers` allocation entry, no `farmland` building entry, and no
    `surplus` resource entry at all."""
    import research as research_mod
    import save as save_mod
    import sim as sim_mod

    old_style_allocation = {"foragers": 3, "gatherers": 2, "crafters": 0, "keepers": 0}
    old_style_buildings = {"shelter": 2, "granary": 0, "hearth": 1, "toolworks": 0}
    old_style_resources = {"food": 10.0, "materials": 5.0, "tools": 1.0, "knowledge": 0.0}
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
                "resources": old_style_resources,
            },
            "research": [],
        },
        "parked_state": None,
        "era_snapshots": {},
        "ui": {},
    }

    campaign = save_mod.Campaign(sim_mod.CityState(), research_mod.build_tree())
    assert campaign.load_dict(data) is True
    assert campaign.state.allocation["farmers"] == 0
    assert campaign.state.buildings["farmland"] == 0
    assert campaign.state.resources["surplus"] == 0.0
    campaign.state.advance_season()  # would have raised KeyError before Milestone 4's audit


# --- proxy-destruction discipline (constraint from CLAUDE.md) ------------
def test_rendering_the_work_panel_destroys_the_proxy_it_replaces(game_env):
    """render_work() rebuilds every row (and mints fresh create_proxy()
    handlers) every render, same as render_research() always has — the
    audit fix that pattern needed once already (see the Phase 1 build
    notes) has to hold for Milestone 8's new dynamic panels too."""
    module = game_env.module
    module.render()
    proxies = module._work_button_proxies
    key = ("foragers", "add")
    assert key in proxies
    first_proxy = proxies[key]
    assert first_proxy.destroyed is False

    module.render()
    second_proxy = proxies[key]
    assert first_proxy.destroyed is True
    assert second_proxy.destroyed is False
    assert first_proxy is not second_proxy


def test_rendering_the_buildings_panel_destroys_the_proxy_it_replaces(game_env):
    module = game_env.module
    module.render()
    proxies = module._building_button_proxies
    assert "shelter" in proxies
    first_proxy = proxies["shelter"]
    assert first_proxy.destroyed is False

    module.render()
    second_proxy = proxies["shelter"]
    assert first_proxy.destroyed is True
    assert second_proxy.destroyed is False


def test_work_proxies_for_a_role_gained_on_transition_do_not_leak(game_env):
    """Farmers' buttons don't exist before Agrarian, so there's nothing to
    destroy for them until the settlement actually reaches that era --
    confirms the "drop keys no longer live" half of the cleanup loop
    handles a role that just APPEARED, not just one that disappeared."""
    push_to_agrarian_ready(game_env)
    game_env.module.render()
    game_env.elements["advance-era-button"].dispatch("click", None)

    proxies = game_env.module._work_button_proxies
    assert ("farmers", "add") in proxies
    assert ("farmers", "remove") in proxies
    assert proxies[("farmers", "add")].destroyed is False


def save_reload(module, saved_dict):
    """Loads `saved_dict` into a second, independent Campaign the same way
    the real widget round-trips through JSON -- proves the save doesn't
    depend on any in-memory object identity from the original playthrough."""
    import copy
    import json

    import research as research_mod
    import save as save_mod
    import sim as sim_mod

    plain = json.loads(json.dumps(copy.deepcopy(saved_dict)))
    fresh_campaign = save_mod.Campaign(sim_mod.CityState(), research_mod.build_tree())
    assert fresh_campaign.load_dict(plain) is True
    return fresh_campaign.state
