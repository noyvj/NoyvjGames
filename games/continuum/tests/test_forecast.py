"""The one-season forecast behind the HUD dropdowns (forecast.py).

Pure engine tests, no DOM. The two things that matter most: the forecast must
never change the real settlement, and what it predicts must be exactly what
the real season then does (it runs the real `advance_season` on a copy, so
these tests are what stops anyone later "optimising" it into an
approximation).
"""

import copy

import pytest

import forecast
import sim


def make_state(era="tribal", population=10, **allocation):
    state = sim.CityState(era=era)
    state.population = population
    for role in state.allocation:
        state.allocation[role] = 0
    state.allocation.update(allocation)
    return state


def snapshot(state):
    return copy.deepcopy(vars(state))


def all_lines(state, effects=None):
    view = forecast.preview(state, effects)
    return [line for key in forecast.KEYS for line in forecast.lines(key, view[key])]


# --- preview: shape -------------------------------------------------------

def test_preview_has_exactly_the_documented_keys():
    view = forecast.preview(sim.CityState())
    assert tuple(view) == forecast.KEYS
    assert set(view["population"]) == {
        "now", "housing", "delta", "births", "deaths", "idle", "growth_before", "growth_after"}
    assert set(view["food"]) == {
        "now", "capacity", "delta", "gathered", "consumed", "spoiled", "fed_fraction"}
    assert set(view["materials"]) == {"now", "delta", "gathered", "spent_on_tools"}
    assert set(view["tools"]) == {"now", "delta"}
    assert set(view["knowledge"]) == {"now", "delta"}
    assert set(view["land_health"]) == {"now", "delta", "extraction", "sustainable_yield"}


# --- preview: purity ------------------------------------------------------

def test_preview_never_mutates_the_real_state():
    state = make_state(population=12, foragers=4, gatherers=3, crafters=2)
    state.last_report = {"season": 0, "marker": "keep me"}
    before = snapshot(state)
    forecast.preview(state)
    assert snapshot(state) == before
    assert state.season == 1
    assert state.last_report == {"season": 0, "marker": "keep me"}


def test_preview_does_not_mutate_effects():
    state = make_state(foragers=3)
    effects = dict(sim.NEUTRAL_EFFECTS)
    effects["food_yield_mult"] = 1.5
    before = copy.deepcopy(effects)
    forecast.preview(state, effects)
    assert effects == before


def test_preview_is_repeatable():
    state = make_state(population=9, foragers=5, gatherers=2)
    assert forecast.preview(state) == forecast.preview(state)


def test_preview_honours_effects():
    state = make_state(foragers=4)
    plain = forecast.preview(state)
    boosted = forecast.preview(state, {"food_yield_mult": 2.0})
    assert boosted["food"]["gathered"] == pytest.approx(plain["food"]["gathered"] * 2)


# --- preview: matches the real season --------------------------------------

def assert_matches_real_season(state, effects=None):
    view = forecast.preview(state, effects)
    real = copy.deepcopy(state)
    before = copy.deepcopy(real.resources)
    pop_before = real.population
    land_before = real.land_health
    report = real.advance_season(effects)

    assert view["population"]["delta"] == real.population - pop_before
    assert view["population"]["births"] == report["births"]
    assert view["population"]["deaths"] == report["deaths"]
    for key in ("food", "materials", "tools", "knowledge"):
        assert view[key]["now"] == before[key]
        assert view[key]["delta"] == pytest.approx(real.resources[key] - before[key])
    assert view["food"]["gathered"] == pytest.approx(report["food_gathered"])
    assert view["food"]["consumed"] == pytest.approx(report["food_consumed"])
    assert view["food"]["spoiled"] == pytest.approx(report["spoiled"])
    assert view["food"]["fed_fraction"] == pytest.approx(report["fed_fraction"])
    assert view["materials"]["gathered"] == pytest.approx(report["materials_gathered"])
    assert view["materials"]["spent_on_tools"] == pytest.approx(
        report["tools_made"] * sim.MATERIALS_PER_TOOL)
    assert view["land_health"]["now"] == land_before
    assert view["land_health"]["delta"] == pytest.approx(real.land_health - land_before)
    assert view["land_health"]["extraction"] == pytest.approx(report["extraction"])
    assert view["land_health"]["sustainable_yield"] == pytest.approx(
        report["sustainable_yield"])


def test_deltas_match_the_real_season_in_a_working_settlement():
    state = make_state(population=8, foragers=3, gatherers=2, crafters=2, keepers=1)
    state.resources["food"] = 40
    assert_matches_real_season(state)


def test_deltas_match_with_research_effects():
    state = make_state(population=8, foragers=3, gatherers=2, keepers=2)
    effects = dict(sim.NEUTRAL_EFFECTS)
    effects.update(food_yield_mult=1.3, knowledge_mult=1.5, housing_bonus=4.0)
    assert_matches_real_season(state, effects)


def test_materials_spent_on_tools_comes_from_crafting():
    state = make_state(population=8, gatherers=2, crafters=3)
    view = forecast.preview(state)
    assert view["materials"]["spent_on_tools"] > 0
    assert view["materials"]["delta"] == pytest.approx(
        view["materials"]["gathered"] - view["materials"]["spent_on_tools"])


def test_knowledge_delta_comes_from_keepers():
    assert forecast.preview(make_state(keepers=3))["knowledge"]["delta"] == pytest.approx(
        3 * sim.KNOWLEDGE_PER_KEEPER)
    assert forecast.preview(make_state(foragers=3))["knowledge"]["delta"] == 0


# --- population cases ------------------------------------------------------

def test_starvation_shrinks_the_population():
    state = make_state(population=20)  # nobody foraging
    state.resources["food"] = 5.0
    view = forecast.preview(state)
    assert view["population"]["delta"] < 0
    assert view["population"]["deaths"] > 0
    assert view["food"]["fed_fraction"] < 1.0
    text = forecast.lines("population", view["population"])
    assert text[0] == f"-{-view['population']['delta']} people per season (not enough food)"
    food_text = forecast.lines("food", view["food"])
    assert any("hungry" in line for line in food_text)


def test_growth_is_one_person():
    state = make_state(population=6, foragers=6)
    state.resources["food"] = 40.0
    state.growth_progress = 0.9
    view = forecast.preview(state)
    assert view["population"]["delta"] == 1
    assert view["population"]["births"] == 1
    assert forecast.lines("population", view["population"])[0] == (
        "+1 person per season (1 born, 0 lost)")


def test_growth_of_two_uses_the_plural():
    view = {"now": 6, "housing": 20.0, "delta": 2, "births": 2, "deaths": 0, "idle": 0}
    assert forecast.lines("population", view)[0] == "+2 people per season (2 born, 0 lost)"


def test_single_death_is_singular():
    view = {"now": 6, "housing": 20.0, "delta": -1, "births": 0, "deaths": 1, "idle": 0}
    assert forecast.lines("population", view)[0] == "-1 person per season (not enough food)"


def test_no_change_wording():
    view = {"now": 6, "housing": 20.0, "delta": 0, "births": 0, "deaths": 0, "idle": 0}
    assert forecast.lines("population", view)[0] == "No change per season"


def test_housing_full_line():
    state = make_state(population=8, foragers=8)  # 2 shelters x 4 = 8
    view = forecast.preview(state)
    assert view["population"]["housing"] == 8
    assert "Shelter for 8, housing is full" in forecast.lines("population", view["population"])


def test_housing_room_line():
    state = make_state(population=6, foragers=6)
    text = forecast.lines("population", forecast.preview(state)["population"])
    assert "Shelter has room for 2 more" in text


def test_idle_worker_wording():
    def idle_line(idle):
        view = {"now": 6, "housing": 20.0, "delta": 0, "births": 0, "deaths": 0, "idle": idle}
        return forecast.lines("population", view)[-1]

    assert idle_line(0) == "No idle workers"
    assert idle_line(1) == "1 idle worker"
    assert idle_line(2) == "2 idle workers"


# --- other stats -----------------------------------------------------------

def test_food_line_format_and_storage():
    view = {"now": 20.0, "capacity": 30.0, "delta": 4.0, "gathered": 8.0,
            "consumed": 4.0, "spoiled": 0.0, "fed_fraction": 1.0}
    assert forecast.lines("food", view) == [
        "+4.0 per season: 8.0 gathered, 4.0 eaten, 0.0 spoiled",
        "Storage 20 of 30",
    ]


def test_food_spoilage_note():
    view = {"now": 28.0, "capacity": 30.0, "delta": 2.0, "gathered": 12.0,
            "consumed": 4.0, "spoiled": 6.0, "fed_fraction": 1.0}
    text = forecast.lines("food", view)
    assert any("storage ceiling" in line for line in text)
    assert not any("hungry" in line for line in text)


def test_materials_tools_knowledge_lines():
    assert forecast.lines(
        "materials", {"now": 5.0, "delta": 5.0, "gathered": 8.0, "spent_on_tools": 3.0}
    ) == ["+5.0 per season: 8.0 gathered, 3.0 used for tools"]
    assert forecast.lines("tools", {"now": 2.0, "delta": 0.6}) == ["+0.6 per season"]
    assert forecast.lines("knowledge", {"now": 0.0, "delta": 1.2}) == ["+1.2 per season"]
    zero = forecast.lines("knowledge", {"now": 0.0, "delta": 0.0})
    assert zero == ["No change per season", "Keepers produce knowledge"]


def test_land_health_lines():
    steady = {"now": 1.0, "delta": 0.0, "extraction": 10.0, "sustainable_yield": 26.0}
    assert forecast.lines("land_health", steady) == ["Land health 100%, steady"]

    wearing = {"now": 0.8, "delta": -0.03, "extraction": 30.0, "sustainable_yield": 26.0}
    text = forecast.lines("land_health", wearing)
    assert text[0] == "-3 points per season (harvest is above what the land sustains)"
    assert "Land health 80%" in text

    healing = {"now": 0.5, "delta": 0.02, "extraction": 10.0, "sustainable_yield": 26.0}
    assert forecast.lines("land_health", healing)[0] == "+2 points per season (recovering)"

    one = {"now": 0.5, "delta": 0.01, "extraction": 10.0, "sustainable_yield": 26.0}
    assert forecast.lines("land_health", one)[0] == "+1 point per season (recovering)"


def test_land_pinned_at_its_floor_still_warns_about_the_harvest():
    view = {"now": sim.MIN_LAND_HEALTH, "delta": 0.0, "extraction": 40.0,
            "sustainable_yield": 26.0}
    text = forecast.lines("land_health", view)
    assert text[0].endswith("steady")
    assert len(text) == 2


def test_overharvest_lowers_land_health_for_real():
    state = make_state(population=30, foragers=15, gatherers=15)
    view = forecast.preview(state)["land_health"]
    assert view["extraction"] > view["sustainable_yield"]
    assert view["delta"] < 0
    assert "harvest is above" in forecast.lines("land_health", view)[0]


def test_resting_land_recovers_for_real():
    state = make_state(population=6, foragers=3)
    state.land_health = 0.5
    view = forecast.preview(state)["land_health"]
    assert view["delta"] > 0
    assert "recovering" in forecast.lines("land_health", view)[0]


# --- robustness ------------------------------------------------------------

@pytest.mark.parametrize("era", sim.ERA_ORDER)
def test_every_era_previews_and_matches_the_real_season(era):
    allocation = {}
    for earlier in sim.ERA_ORDER[: sim.era_index(era) + 1]:
        allocation[sim.ERA_ROLES[earlier][0]] = 2
    state = make_state(era=era, population=30, **allocation)
    state.resources["food"] = 80.0
    state.resources["surplus"] = 20.0
    for building in sim.buildings_for_era(era):
        state.buildings[building] += 1
    before = snapshot(state)
    assert_matches_real_season(state)
    assert snapshot(state) == before
    for line in all_lines(state):
        assert line


def test_all_workers_idle():
    state = make_state(population=10)
    view = forecast.preview(state)
    assert view["population"]["idle"] == 10
    assert view["food"]["gathered"] == 0
    assert "10 idle workers" in forecast.lines("population", view["population"])


def test_empty_settlement():
    state = make_state(population=0)
    state.resources["food"] = 0.0
    view = forecast.preview(state)
    assert view["population"]["delta"] == 0
    assert view["population"]["idle"] == 0
    assert all_lines(state)


def test_a_probe_that_raises_is_not_swallowed():
    state = make_state(foragers=2)
    state.allocation = None  # broken on purpose
    with pytest.raises(Exception):
        forecast.preview(state)


# --- lines -----------------------------------------------------------------

def test_unknown_key_gives_no_lines():
    assert forecast.lines("nonsense", {}) == []
    assert forecast.lines("", {}) == []


@pytest.mark.parametrize("era", sim.ERA_ORDER)
def test_lines_are_short_plain_text(era):
    state = make_state(era=era, population=25, foragers=4, gatherers=3, keepers=1)
    for line in all_lines(state):
        assert isinstance(line, str)
        assert line.strip()
        assert "—" not in line and "–" not in line
        assert "!" not in line
    for key in forecast.KEYS:
        count = len(forecast.lines(key, forecast.preview(state)[key]))
        assert 1 <= count <= 4


def test_no_negative_zero_or_empty_signs():
    view = {"now": 1.0, "delta": -0.01, "gathered": 0.0, "spent_on_tools": 0.0}
    assert forecast.lines("materials", view)[0].startswith("No change")
    assert "-0.0" not in " ".join(forecast.lines("tools", {"now": 1.0, "delta": -0.04}))


def test_a_building_birth_is_mentioned_when_the_population_delta_is_zero():
    view = {"now": 6, "housing": 8.0, "delta": 0, "births": 0, "deaths": 0, "idle": 0,
            "growth_before": 0.2, "growth_after": 0.4}
    first = forecast.lines("population", view)[0]
    assert "growth is building" in first and "birth" in first
    full = dict(view, housing=6.0)   # no room: growth cannot turn into a birth
    assert forecast.lines("population", full)[0] == "No change per season"
    stalled = dict(view, growth_after=0.2)
    assert forecast.lines("population", stalled)[0] == "No change per season"
