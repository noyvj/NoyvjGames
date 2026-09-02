"""Milestone 2 — sustainability / livability score.

The design doc's explicit warning is the spine of this file: the score has
to reflect *decision quality*, not city size. "A tribal settlement can be
more sustainable than a poorly-planned industrial one." So the tests below
aren't only "does the arithmetic work" — several of them exist purely to
pin down that a small, well-run settlement out-scores a large, badly-run
one, and that scaling a settlement up without changing how it is run moves
the score not at all.
"""

import pytest

import sim
import sustainability


def _settlement(**overrides):
    """A CityState built to order, for scoring in isolation."""
    state = sim.CityState()
    buildings = overrides.pop("buildings", None)
    resources = overrides.pop("resources", None)
    allocation = overrides.pop("allocation", None)
    for key, value in overrides.items():
        setattr(state, key, value)
    if buildings:
        state.buildings.update(buildings)
    if resources:
        state.resources.update(resources)
    if allocation:
        state.allocation = dict.fromkeys(sim.ROLES, 0)
        state.allocation.update(allocation)
    return state


def careful_settlement():
    """Small, fed, housed, sheltered, diversified, living within the land."""
    return _settlement(
        population=8,
        fed_fraction=1.0,
        land_health=1.0,
        last_extraction=10.0,
        last_sustainable_yield=sim.LAND_SUSTAINABLE_YIELD,
        buildings={"shelter": 3, "granary": 1, "hearth": 2, "toolworks": 0},
        resources={"food": 48.0, "materials": 20.0, "tools": 8.0, "knowledge": 0.0},
        allocation={"foragers": 2, "gatherers": 2, "crafters": 2, "keepers": 2},
    )


def extractive_settlement():
    """Five times the people, stripping the land, half of them unhoused."""
    return _settlement(
        population=40,
        fed_fraction=0.7,
        land_health=0.4,
        last_extraction=90.0,
        last_sustainable_yield=sim.LAND_SUSTAINABLE_YIELD,
        buildings={"shelter": 4, "granary": 0, "hearth": 1, "toolworks": 2},
        resources={"food": 10.0, "materials": 200.0, "tools": 5.0, "knowledge": 0.0},
        allocation={"foragers": 40, "gatherers": 0, "crafters": 0, "keepers": 0},
    )


# --- the headline property --------------------------------------------
def test_a_small_careful_settlement_beats_a_large_extractive_one(game_env):
    careful = sustainability.score(careful_settlement())
    extractive = sustainability.score(extractive_settlement())

    assert careful > extractive
    # Not a photo finish — the gap should be obvious to a player.
    assert careful - extractive > 30


def test_score_is_independent_of_settlement_size(game_env):
    """Scaling everything up in proportion changes nothing about how well
    the settlement is run, so it must not change the score."""
    small = careful_settlement()
    large = _settlement(
        population=32,
        fed_fraction=1.0,
        land_health=1.0,
        # The land is deliberately *not* scaled up with the settlement — it
        # is a fixed common resource, and taking more from it is a real
        # penalty. Both settlements are held under its limit here so this
        # test isolates the size question rather than re-testing extraction.
        last_extraction=10.0,
        last_sustainable_yield=sim.LAND_SUSTAINABLE_YIELD,
        buildings={"shelter": 12, "granary": 4, "hearth": 8, "toolworks": 0},
        resources={"food": 192.0, "materials": 80.0, "tools": 32.0, "knowledge": 0.0},
        allocation={"foragers": 8, "gatherers": 8, "crafters": 8, "keepers": 8},
    )

    assert sustainability.score(large) == pytest.approx(sustainability.score(small))


def test_growing_the_population_alone_does_not_raise_the_score(game_env):
    """Population growth with no matching infrastructure should *hurt* —
    the same shelters and hearths now serve more people."""
    before = careful_settlement()
    after = careful_settlement()
    after.population = 20

    assert sustainability.score(after) < sustainability.score(before)


# --- components --------------------------------------------------------
def test_every_component_is_reported_and_bounded(game_env):
    for settlement in (careful_settlement(), extractive_settlement(), sim.CityState()):
        components = sustainability.components(settlement)
        assert set(components) == set(sustainability.COMPONENTS)
        for value in components.values():
            assert 0.0 <= value <= 1.0
        assert 0.0 <= sustainability.score(settlement) <= 100.0


def test_starvation_drives_livability_down(game_env):
    fed = careful_settlement()
    hungry = careful_settlement()
    hungry.fed_fraction = 0.3

    assert sustainability.components(hungry)["livability"] < sustainability.components(fed)["livability"]


def test_overcrowding_drives_livability_down(game_env):
    housed = careful_settlement()
    crowded = careful_settlement()
    crowded.buildings["shelter"] = 1  # 8 people, room for 4

    assert (
        sustainability.components(crowded)["livability"]
        < sustainability.components(housed)["livability"]
    )


def test_social_infrastructure_raises_livability(game_env):
    bare = careful_settlement()
    bare.buildings["hearth"] = 0
    warm = careful_settlement()

    assert sustainability.components(warm)["livability"] > sustainability.components(bare)["livability"]


def test_over_extraction_drives_resource_balance_down(game_env):
    within = careful_settlement()
    over = careful_settlement()
    over.last_extraction = over.last_sustainable_yield * 3

    assert sustainability.components(over)["balance"] < sustainability.components(within)["balance"]


def test_degraded_land_drives_resource_balance_down(game_env):
    healthy = careful_settlement()
    stripped = careful_settlement()
    stripped.land_health = sim.MIN_LAND_HEALTH

    assert (
        sustainability.components(stripped)["balance"]
        < sustainability.components(healthy)["balance"]
    )


def test_food_stores_and_tool_stock_raise_resilience(game_env):
    lean = careful_settlement()
    lean.resources["food"] = 0.0
    lean.resources["tools"] = 0.0
    stocked = careful_settlement()

    assert (
        sustainability.components(stocked)["resilience"]
        > sustainability.components(lean)["resilience"]
    )


def test_a_one_job_settlement_is_less_resilient_than_a_diversified_one(game_env):
    diversified = careful_settlement()
    monoculture = careful_settlement()
    monoculture.allocation = dict.fromkeys(sim.ROLES, 0)
    monoculture.allocation["foragers"] = 8

    assert (
        sustainability.components(monoculture)["resilience"]
        < sustainability.components(diversified)["resilience"]
    )


def test_equity_tracks_the_least_met_need_not_the_average(game_env):
    """A settlement that is lavishly housed but half-starved is not
    equitable, however good its average looks."""
    balanced = _settlement(
        population=8,
        fed_fraction=0.7,
        buildings={"shelter": 2, "granary": 0, "hearth": 1, "toolworks": 0},
    )
    lopsided = _settlement(
        population=8,
        fed_fraction=0.4,
        buildings={"shelter": 10, "granary": 0, "hearth": 10, "toolworks": 0},
    )

    assert sustainability.components(lopsided)["equity"] < sustainability.components(balanced)["equity"]


# --- the research seam --------------------------------------------------
def test_research_effects_move_the_score(game_env):
    """Milestone 3's tree reaches the score through the same effects dict
    the simulation uses — proving the seam works before the tree exists."""
    settlement = careful_settlement()
    # Leave headroom in both components for a bonus to actually show up.
    settlement.fed_fraction = 0.6
    settlement.resources["tools"] = 0.0

    base = sustainability.components(settlement)
    communal = sustainability.components(settlement, {"equity_bonus": 0.25})
    prepared = sustainability.components(settlement, {"resilience_bonus": 0.25})

    assert communal["equity"] > base["equity"]
    assert prepared["resilience"] > base["resilience"]
    assert sustainability.score(settlement, {"equity_bonus": 0.25}) > sustainability.score(settlement)


def test_extra_shelter_capacity_from_research_counts_as_housing(game_env):
    settlement = careful_settlement()
    settlement.population = 16  # outgrown its three shelters

    base = sustainability.components(settlement)
    with_bonus = sustainability.components(settlement, {"housing_bonus": 8.0})

    assert with_bonus["livability"] > base["livability"]


# --- integration with the season loop ----------------------------------
def test_the_score_is_recorded_every_season(game_env):
    state = game_env.state
    assert state.score_history == []

    game_env.advance_season(3)

    assert len(state.score_history) == 3
    for value in state.score_history:
        assert 0.0 <= value <= 100.0


def test_a_careless_playthrough_scores_worse_than_a_careful_one(game_env):
    """The doc asks for score calculation across sample decision sequences:
    two runs from the identical starting settlement, differing only in the
    decisions made."""
    state = game_env.state

    # Careless: everyone forages, nothing gets built, the land gets stripped.
    state.allocation = dict.fromkeys(sim.ROLES, 0)
    state.allocation["foragers"] = state.population
    for _ in range(12):
        state.population = 30  # keep piling people onto the same land
        state.allocation["foragers"] = 30
        state.advance_season()
    careless_score = sustainability.score(state)
    careless_population = state.population

    # Careful: a spread of work, shelter and hearths built, land left alone.
    careful = sim.CityState()
    careful.allocation = {"foragers": 2, "gatherers": 2, "crafters": 1, "keepers": 1}
    for season in range(12):
        careful.resources["materials"] += 20.0  # stand in for a gatherer-heavy run
        if season % 3 == 0:
            careful.build("shelter")
        if season == 4:
            careful.build("hearth")
        if season == 6:
            careful.build("granary")
        careful.advance_season()
    careful_score = sustainability.score(careful)

    assert careful_score > careless_score
    # And the careful settlement is the *smaller* one, which is the point.
    assert careful.population < careless_population


def test_the_ui_shows_the_score_and_its_components(game_env):
    game_env.advance_season()

    assert "Sustainability" in game_env.elements["score-display"].innerText
    assert game_env.elements["score-bar"].style.width.endswith("%")
    for component in sustainability.COMPONENTS:
        text = game_env.elements[f"{component}-display"].innerText
        assert sustainability.COMPONENT_LABEL[component] in text
    assert game_env.elements["score-note-display"].innerText != ""
