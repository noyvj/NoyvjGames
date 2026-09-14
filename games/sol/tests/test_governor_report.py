"""Tests for A11: a visible "governor efficiency" readout. Shows, per
currently-governed world (every real planet except current_planet):
production efficiency (the same production_multiplier() the ecology
penalty already applies every tick, just surfaced explicitly) and a
lifetime total of resources generated while that world was governed
(planet_state[...]["governed_resource_generated"], accumulated only when
a planet's automation produces while it ISN'T current_planet)."""


def _all_texts(element):
    texts = [element.innerText]
    for child in element.children:
        texts.extend(_all_texts(child))
    return texts


def test_panel_hidden_by_default(game_env):
    assert game_env.elements["governor-report-panel"].hidden is True


def test_toggle_opens_and_closes_the_panel(game_env):
    game_env.toggle_governor_report()
    assert game_env.elements["governor-report-panel"].hidden is False
    assert "Hide" in game_env.elements["governor-report-toggle-button"].innerText

    game_env.toggle_governor_report()
    assert game_env.elements["governor-report-panel"].hidden is True


def test_lists_every_other_real_planet_as_governed(game_env):
    module = game_env.module
    game_env.toggle_governor_report()
    texts = _all_texts(game_env.elements["governor-report-panel"])
    for planet in module.PLANETS:
        if planet == "Earth":
            continue
        display = module.PLANET_DISPLAY_NAMES.get(planet, planet)
        assert any(display in text for text in texts)
    assert not any("Earth" == text for text in texts)  # current_planet isn't "governed"


def test_shows_no_automation_yet_before_any_generator_exists(game_env):
    game_env.toggle_governor_report()
    texts = _all_texts(game_env.elements["governor-report-panel"])
    assert any("No automation yet" in text for text in texts)


def test_shows_efficiency_once_a_governed_world_has_a_generator(game_env):
    game_env.mars["generator_count"] = 1
    game_env.toggle_governor_report()
    texts = _all_texts(game_env.elements["governor-report-panel"])
    assert any("Efficiency: 100%" in text for text in texts)


def test_efficiency_reflects_the_low_ecology_penalty(game_env):
    game_env.mars["generator_count"] = 1
    game_env.mars["ecology_health"] = 5.0
    game_env.toggle_governor_report()
    texts = _all_texts(game_env.elements["governor-report-panel"])
    assert any("Efficiency: 75%" in text for text in texts)


def test_efficiency_zero_during_full_collapse(game_env):
    game_env.mars["generator_count"] = 1
    game_env.mars["ecology_health"] = 0.0
    game_env.toggle_governor_report()
    texts = _all_texts(game_env.elements["governor-report-panel"])
    assert any("Efficiency: 0%" in text for text in texts)


def test_generated_while_governed_accumulates_from_ticking(game_env):
    game_env.mars["generator_count"] = 1
    game_env.timers.tick_intervals(10)  # 1 second of production while Earth is current_planet
    assert game_env.mars["governed_resource_generated"] > 0.0

    game_env.toggle_governor_report()
    texts = _all_texts(game_env.elements["governor-report-panel"])
    assert any("Generated while governed" in text for text in texts)


def test_generated_while_governed_does_not_accumulate_for_current_planet(game_env):
    game_env.earth["generator_count"] = 1
    game_env.timers.tick_intervals(10)
    assert game_env.earth["governed_resource_generated"] == 0.0


def test_generated_while_governed_starts_accumulating_after_traveling_away(game_env):
    module = game_env.module
    module.unlocked_bodies.add("Mars")
    game_env.earth["generator_count"] = 1
    game_env.timers.tick_intervals(10)
    assert game_env.earth["governed_resource_generated"] == 0.0

    game_env.travel_to("Mars")
    game_env.timers.tick_intervals(10)
    assert game_env.earth["governed_resource_generated"] > 0.0


def test_total_row_sums_every_governed_worlds_generated_total(game_env):
    game_env.mars["generator_count"] = 1
    game_env.moon["generator_count"] = 1
    game_env.timers.tick_intervals(10)
    total = game_env.mars["governed_resource_generated"] + game_env.moon["governed_resource_generated"]

    game_env.toggle_governor_report()
    texts = _all_texts(game_env.elements["governor-report-panel"])
    assert any("Total generated across every governed world" in text for text in texts)
    assert total > 0.0


def test_panel_updates_live_on_tick_while_open(game_env):
    game_env.mars["generator_count"] = 1
    game_env.toggle_governor_report()
    texts_before = _all_texts(game_env.elements["governor-report-panel"])
    assert any("Generated while governed: 0 Water Ice" in text for text in texts_before)

    game_env.timers.tick_intervals(50)  # 5 seconds
    texts_after = _all_texts(game_env.elements["governor-report-panel"])
    assert not any("Generated while governed: 0 Water Ice" in text for text in texts_after)


def test_toggle_button_wired_up_by_setup(game_env):
    button = game_env.elements["governor-report-toggle-button"]
    assert "click" in button._listeners
    assert len(button._listeners["click"]) == 1
