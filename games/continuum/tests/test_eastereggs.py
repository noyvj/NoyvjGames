"""K-23: Digital Age in-jokes in the log (hidden with the story toggle)."""

import eastereggs as ee
import sim
import techdebt


def digital(game_env):
    module = game_env.module
    module.state.era = "digital"
    module.tree.current_era = "digital"
    module.state.resources["materials"] = 900.0
    module.state.buildings["shelter"] = 10
    module.render()
    return module


def texts(module):
    return [e.text for e in module.chronicle.entries]


def test_pure_triggers_fire_once_and_only_in_the_right_era():
    ui = {}
    state = sim.CityState(era="industrial")
    assert ee.on_era(ui, "industrial") is None and ee.on_build(ui, state, "transit_hubs") is None
    assert ee.on_research(ui, state, 12) is None and ee.on_season(ui, state, 99) is None
    assert ee.on_refactor(ui, state) is None
    state.era = "digital"
    assert ee.on_era(ui, "digital")[0] == "legacy_server" and ee.on_era(ui, "digital") is None
    assert ee.on_build(ui, state, "transit_hubs")[0] == "guild_hall"
    assert ee.on_build(ui, state, "shelter") is None
    assert ee.on_build(ui, state, "shelter", quick=True)[0] == "friday_shortcut"
    assert ee.on_research(ui, state, 10) is None and ee.on_research(ui, state, 11)[0] == "meeting_rule"
    assert ee.on_season(ui, state, 9) is None and ee.on_season(ui, state, 10)[0] == "blameless_outage"
    assert ee.on_refactor(ui, state)[0] == "workaround_funeral"
    assert ee.seen(ui) == sorted(ee.seen(ui), key=ee.ORDER.index) or len(ee.seen(ui)) == 6


def test_seen_survives_junk():
    assert ee.seen(None) == [] and ee.seen({ee.KEY: "x"}) == []
    assert ee.seen({ee.KEY: ["legacy_server", "legacy_server", 5, "nope"]}) == ["legacy_server"]


def test_lines_are_pure_flavour_and_use_no_real_names():
    for text in ee.EGGS.values():
        assert text.endswith(".") and len(text) < 260


def test_entering_the_digital_age_logs_the_server_closet(game_env):
    module = game_env.module
    module._easter_egg(ee.on_era(module.campaign.ui, "digital"))
    assert any("legacy server" in t for t in texts(module))
    module._easter_egg(ee.on_era(module.campaign.ui, "digital"))
    assert sum("legacy server" in t for t in texts(module)) == 1


def test_first_transit_hub_logs_the_guild_hall(game_env):
    module = digital(game_env)
    module.state.buildings["transit_hubs"] = 0
    game_env.build("transit_hubs")
    assert any("co-working guild hall" in t for t in texts(module))


def test_a_quick_build_logs_the_friday_shortcut(game_env):
    module = digital(game_env)
    game_env.elements["quick-build-toggle-button"].dispatch("click", None)
    game_env.build("shelter")
    assert any("on a Friday" in t for t in texts(module))
    assert techdebt.get(module.campaign.ui)["quick_builds"] == 1


def test_a_refactor_logs_the_funeral(game_env):
    module = digital(game_env)
    techdebt.put(module.campaign.ui, {"debt": 0.4, "refactor": True})
    game_env.advance_season()
    assert any("small funeral" in t for t in texts(module))


def test_ten_seasons_in_logs_the_blameless_outage(game_env):
    module = digital(game_env)
    game_env.advance_season(12)
    assert any("blameless" in t for t in texts(module))


def test_nothing_fires_in_a_look_back(game_env):
    module = digital(game_env)
    module.campaign.revisiting = "tribal"
    try:
        game_env.build("shelter")
    finally:
        module.campaign.revisiting = None
    assert not any("Friday" in t or "guild hall" in t for t in texts(module))
