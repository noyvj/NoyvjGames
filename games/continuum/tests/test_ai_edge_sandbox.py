"""Edge-case tests for continuum sandbox.py."""
import sim
import sandbox


def test_clean_era_valid_passes_through():
    """Valid era strings are returned unchanged."""
    for era in sim.ERA_ORDER:
        assert sandbox.clean_era(era) == era


def test_clean_era_invalid_falls_back():
    """Invalid, empty, or whitespace-only strings fall back to the first era."""
    assert sandbox.clean_era("") == sim.FIRST_ERA
    assert sandbox.clean_era("nonsense") == sim.FIRST_ERA
    assert sandbox.clean_era("  ") == sim.FIRST_ERA


def test_new_campaign_valid_era_initializes_state():
    """A valid era creates a campaign with the correct state and tree."""
    for era in sim.ERA_ORDER:
        campaign = sandbox.new_campaign(era)
        assert campaign.state.era == era
        assert campaign.furthest_era == era
        assert campaign.tree.current_era == era


def test_new_campaign_invalid_era_falls_back():
    """An invalid era string falls back to the first era."""
    campaign = sandbox.new_campaign("invalid_era")
    assert campaign.state.era == sim.FIRST_ERA
    assert campaign.furthest_era == sim.FIRST_ERA


def test_relief_clamps_below_thresholds():
    """relief() raises sub-threshold resources and stats to their defined floors/ceilings."""
    campaign = sandbox.new_campaign("tribal")
    state = campaign.state

    # Push everything below thresholds
    state.resources["materials"] = 0.0
    state.resources["tools"] = 0.0
    state.resources["knowledge"] = 0.0
    state.land_health = 0.0
    state.pollution = 1.0
    state.sprawl = 1.0
    state.fed_fraction = 0.0
    state.population = sandbox.MIN_PEOPLE - 10

    sandbox.relief(state)

    assert state.resources["materials"] >= sandbox.MATERIALS_FLOOR
    assert state.resources["tools"] >= sandbox.TOOLS_FLOOR
    assert state.resources["knowledge"] >= sandbox.KNOWLEDGE_FLOOR
    assert state.land_health >= sandbox.LAND_FLOOR
    assert state.pollution <= sandbox.POLLUTION_CEILING
    assert state.sprawl <= sandbox.SPRAWL_CEILING
    assert state.fed_fraction == 1.0
    assert state.population >= sandbox.MIN_PEOPLE


def test_era_choices_returns_all_eras():
    """era_choices() returns a list containing every era in sim.ERA_ORDER."""
    assert set(sandbox.era_choices()) == set(sim.ERA_ORDER)
