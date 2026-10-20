"""Edge-case tests for save.py: limits, empty input, clamping, and rejection."""

import sim
import save


def test_restore_city_with_empty_data_leaves_state_unchanged():
    state = sim.CityState()
    original_pop = state.population
    save.restore_city(state, {})
    assert state.population == original_pop


def test_restore_city_clamps_population_to_minimum():
    state = sim.CityState()
    save.restore_city(state, {"population": -1000})
    assert state.population == sim.MIN_POPULATION


def test_restore_city_clamps_growth_progress_to_max():
    state = sim.CityState()
    save.restore_city(state, {"growth_progress": 999.0})
    assert state.growth_progress == save.GROWTH_PROGRESS_MAX


def test_campaign_advance_to_era_rejects_invalid_era():
    campaign = save.Campaign()
    result = campaign.advance_to_era("bogus_era")
    assert result is False
    assert campaign.state.era == "tribal"


def test_campaign_enter_revisit_rejects_unreplayed_era():
    campaign = save.Campaign()
    result = campaign.enter_revisit("agrarian")
    assert result is False


def test_campaign_load_dict_rejects_wrong_game_id():
    campaign = save.Campaign()
    data = {"game": "other_game", "save_version": 1}
    assert campaign.load_dict(data) is False
