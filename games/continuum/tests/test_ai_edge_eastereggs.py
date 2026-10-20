"""Edge-case tests for eastereggs.py."""

import eastereggs as ee
import sim


def test_seen_handles_none_and_empty_dict():
    assert ee.seen(None) == []
    assert ee.seen({}) == []


def test_seen_truncates_long_lists():
    ui = {ee.KEY: ["legacy_server"] * 20}
    result = ee.seen(ui)
    assert len(result) <= len(ee.ORDER) * 2
    assert result == ["legacy_server"]


def test_seen_ignores_junk_types():
    ui = {ee.KEY: [1, None, "invalid_key", 3.14]}
    assert ee.seen(ui) == []


def test_on_era_returns_none_for_non_digital_eras():
    ui = {}
    for era in ("tribal", "agrarian", "industrial"):
        assert ee.on_era(ui, era) is None


def test_on_build_respects_era_and_building_type():
    state = sim.CityState(era="tribal")
    ui = {}
    assert ee.on_build(ui, state, "shelter") is None

    state.era = "digital"
    assert ee.on_build(ui, state, "shelter") is None
    assert ee.on_build(ui, state, "transit_hubs")[0] == "guild_hall"
    assert ee.on_build(ui, state, "shelter", quick=True)[0] == "friday_shortcut"


def test_on_research_clamps_by_tier():
    state = sim.CityState(era="digital")
    ui = {}
    assert ee.on_research(ui, state, 10) is None
    assert ee.on_research(ui, state, 11)[0] == "meeting_rule"


def test_on_refactor_checks_era_index():
    state = sim.CityState(era="tribal")
    ui = {}
    assert ee.on_refactor(ui, state) is None

    state.era = "digital"
    assert ee.on_refactor(ui, state)[0] == "workaround_funeral"


def test_on_season_checks_threshold():
    state = sim.CityState(era="digital")
    ui = {}
    assert ee.on_season(ui, state, 9) is None
    assert ee.on_season(ui, state, 10)[0] == "blameless_outage"
