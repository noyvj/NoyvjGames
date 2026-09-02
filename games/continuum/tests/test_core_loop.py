"""Milestone 1 — core city simulation loop (Tribal era only).

Covers the resource/population update logic the design doc asks for:
worker allocation, production, consumption, population growth and
starvation, tool wear, building costs/capacities, and the land-health
feedback loop that later milestones' sustainability score reads from.

The whole season loop is deliberately deterministic (no RNG anywhere in
the simulation core) — events and variability are Phase 2/3 work, and
keeping the engine deterministic is what makes seven eras' worth of
behaviour testable at all.
"""

import pytest

import sim


def test_starting_state_is_a_small_tribal_settlement(game_env):
    state = game_env.state
    assert state.era == "tribal"
    assert state.season == 1
    assert state.population == sim.START_POPULATION
    assert state.resources["food"] == sim.START_FOOD
    assert state.resources["materials"] == sim.START_MATERIALS
    assert state.land_health == 1.0
    assert sum(state.allocation.values()) <= state.population


def test_workers_cannot_be_assigned_beyond_the_population(game_env):
    state = game_env.state
    idle_at_start = state.idle_workers()
    assert idle_at_start > 0

    game_env.assign("crafters", idle_at_start)
    assert state.idle_workers() == 0
    assert state.allocation["crafters"] == idle_at_start

    game_env.assign("crafters")  # one too many
    assert state.allocation["crafters"] == idle_at_start
    assert state.idle_workers() == 0


def test_unassigning_workers_floors_at_zero_and_frees_them(game_env):
    state = game_env.state
    assigned = state.allocation["gatherers"]
    assert assigned > 0

    game_env.unassign("gatherers", assigned + 3)
    assert state.allocation["gatherers"] == 0
    assert state.idle_workers() == state.population - sum(state.allocation.values())


def test_foragers_produce_food_and_the_settlement_eats_it(game_env):
    state = game_env.state
    start_food = state.resources["food"]

    report = state.advance_season()

    expected_gathered = (
        state.allocation["foragers"] * sim.FOOD_PER_FORAGER * report["tool_factor"]
    )
    assert report["food_gathered"] == pytest.approx(expected_gathered)
    assert report["food_consumed"] == pytest.approx(sim.START_POPULATION * sim.FOOD_PER_PERSON)
    assert report["fed_fraction"] == 1.0
    assert state.resources["food"] == pytest.approx(
        start_food + report["food_gathered"] - report["food_consumed"]
    )


def test_a_food_shortfall_starves_part_of_the_population(game_env):
    state = game_env.state
    state.resources["food"] = 0.0
    for role in sim.ROLES:
        state.allocation[role] = 0
    state.allocation["gatherers"] = state.population

    report = state.advance_season()

    assert report["fed_fraction"] == 0.0
    assert report["deaths"] > 0
    assert state.population < sim.START_POPULATION
    assert state.population >= sim.MIN_POPULATION


def test_population_never_drops_below_the_minimum(game_env):
    state = game_env.state
    state.resources["food"] = 0.0
    for role in sim.ROLES:
        state.allocation[role] = 0

    for _ in range(20):
        state.advance_season()

    assert state.population == sim.MIN_POPULATION


def test_a_sustained_food_surplus_grows_the_population(game_env):
    state = game_env.state
    assert state.population < state.housing_capacity()

    grew = False
    for _ in range(6):
        report = state.advance_season()
        state.resources["food"] = 40.0  # keep a healthy surplus each season
        if report["births"]:
            grew = True
    assert grew
    assert state.population > sim.START_POPULATION


def test_growth_is_blocked_when_there_is_no_housing_headroom(game_env):
    state = game_env.state
    state.population = state.housing_capacity()
    state.resources["food"] = 500.0

    for _ in range(6):
        report = state.advance_season()
        state.resources["food"] = 500.0
        assert report["births"] == 0

    assert state.population == state.housing_capacity()
    assert state.growth_progress == 0.0


def test_gatherers_produce_materials_and_crafters_turn_them_into_tools(game_env):
    state = game_env.state
    for role in sim.ROLES:
        state.allocation[role] = 0
    state.allocation["gatherers"] = 3
    state.allocation["crafters"] = 2
    start_materials = state.resources["materials"]

    report = state.advance_season()

    assert report["materials_gathered"] > 0
    assert report["tools_made"] > 0
    # Toolmaking consumes materials, so the net materials gain is smaller
    # than the gross harvest.
    net_materials = state.resources["materials"] - start_materials
    assert net_materials == pytest.approx(
        report["materials_gathered"] - report["tools_made"] * sim.MATERIALS_PER_TOOL
    )


def test_tools_wear_out_when_nobody_is_crafting(game_env):
    state = game_env.state
    state.resources["tools"] = 10.0
    state.allocation["crafters"] = 0

    state.advance_season()

    assert state.resources["tools"] == pytest.approx(10.0 * (1 - sim.TOOL_DECAY_RATE))


def test_tools_raise_every_gathering_yield(game_env):
    state = game_env.state
    state.resources["tools"] = 0.0
    without_tools = state.advance_season()["food_gathered"]

    state.resources["tools"] = float(state.population)  # one tool per person
    assert state.tool_factor() == pytest.approx(1 + sim.TOOL_EFFECT)  # capped at one per person
    with_tools = state.advance_season()["food_gathered"]

    assert with_tools > without_tools


def test_keepers_produce_knowledge(game_env):
    state = game_env.state
    for role in sim.ROLES:
        state.allocation[role] = 0
    state.allocation["keepers"] = 2

    report = state.advance_season()

    assert report["knowledge_made"] == pytest.approx(2 * sim.KNOWLEDGE_PER_KEEPER)
    assert state.resources["knowledge"] == pytest.approx(report["knowledge_made"])


def test_over_extraction_degrades_the_land(game_env):
    state = game_env.state
    state.population = 30
    for role in sim.ROLES:
        state.allocation[role] = 0
    state.allocation["foragers"] = 20
    state.allocation["gatherers"] = 10

    report = state.advance_season()

    assert report["extraction"] > report["sustainable_yield"]
    assert state.land_health < 1.0


def test_land_recovers_when_harvest_stays_within_its_limit(game_env):
    state = game_env.state
    state.land_health = 0.5
    for role in sim.ROLES:
        state.allocation[role] = 0
    state.allocation["foragers"] = 1

    report = state.advance_season()

    assert report["extraction"] < report["sustainable_yield"]
    assert state.land_health > 0.5


def test_degraded_land_cuts_yields(game_env):
    state = game_env.state
    healthy = state.advance_season()["food_gathered"]

    state.land_health = 0.5
    state.resources["tools"] = 0.0
    degraded = state.advance_season()["food_gathered"]

    assert degraded < healthy


def test_land_health_stays_within_bounds(game_env):
    state = game_env.state
    state.population = 40
    for role in sim.ROLES:
        state.allocation[role] = 0
    state.allocation["foragers"] = 40

    for _ in range(40):
        state.advance_season()
        state.population = 40
        state.allocation["foragers"] = 40

    assert state.land_health >= sim.MIN_LAND_HEALTH
    assert state.land_health <= 1.0


def test_building_costs_materials_and_raises_capacity(game_env):
    state = game_env.state
    state.resources["materials"] = 500.0
    before_capacity = state.housing_capacity()

    assert state.build("shelter") is True

    assert state.buildings["shelter"] == 3
    assert state.resources["materials"] == pytest.approx(500.0 - sim.BUILDING_COST["shelter"])
    assert state.housing_capacity() == before_capacity + sim.SHELTER_CAPACITY


def test_building_is_refused_without_the_materials(game_env):
    state = game_env.state
    state.resources["materials"] = 0.0

    assert state.build("granary") is False
    assert state.buildings["granary"] == 0


def test_granaries_raise_food_storage_and_surplus_above_it_spoils(game_env):
    state = game_env.state
    base_capacity = state.food_storage_capacity()
    state.resources["food"] = base_capacity + 100.0

    report = state.advance_season()

    assert report["spoiled"] > 0
    assert state.resources["food"] == pytest.approx(base_capacity)

    state.resources["materials"] = 500.0
    state.build("granary")
    assert state.food_storage_capacity() == base_capacity + sim.GRANARY_STORAGE


def test_allocation_is_clamped_when_the_population_shrinks(game_env):
    state = game_env.state
    state.allocation["foragers"] = state.population
    state.allocation["gatherers"] = 0
    state.population = 2
    state.resources["food"] = 200.0

    state.advance_season()

    assert sum(state.allocation.values()) <= state.population
    assert state.idle_workers() >= 0


def test_advancing_a_season_ticks_the_counter_and_records_a_report(game_env):
    state = game_env.state
    assert state.season == 1

    game_env.advance_season()

    assert state.season == 2
    assert state.last_report is not None
    for key in (
        "food_gathered",
        "materials_gathered",
        "tools_made",
        "knowledge_made",
        "food_consumed",
        "fed_fraction",
        "spoiled",
        "births",
        "deaths",
        "extraction",
        "sustainable_yield",
        "tool_factor",
    ):
        assert key in state.last_report


def test_ui_renders_the_current_settlement(game_env):
    game_env.advance_season()
    state = game_env.state

    assert game_env.elements["season-display"].innerText == f"Season {state.season}"
    assert str(state.population) in game_env.elements["population-display"].innerText
    assert game_env.elements["foragers-count"].innerText == str(state.allocation["foragers"])
    assert game_env.elements["shelter-count"].innerText == str(state.buildings["shelter"])
    assert game_env.elements["season-report-display"].innerText != ""


def test_build_buttons_disable_when_materials_run_out(game_env):
    game_env.state.resources["materials"] = 0.0
    game_env.module.render()

    assert game_env.elements["shelter-build-button"].disabled is True

    game_env.state.resources["materials"] = 500.0
    game_env.module.render()

    assert game_env.elements["shelter-build-button"].disabled is False
