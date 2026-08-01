"""Milestone 6: visual pass — plant icons, emissions/score meter bars, and
event-severity-distinct styling on the disruption notification.
"""

ALWAYS_TRIGGER = lambda: 0.0
NEVER_TRIGGER = lambda: 0.999999


def test_plant_name_includes_icon(game_env):
    text = game_env.elements["coal-name"].innerText
    assert game_env.module.PLANT_ICON["coal"] in text
    assert "Coal" in text


def test_all_plant_types_get_named_with_icons(game_env):
    for plant_type in game_env.module.PLANT_TYPES:
        text = game_env.elements[f"{plant_type}-name"].innerText
        assert game_env.module.PLANT_ICON[plant_type] in text
        assert game_env.module.PLANT_LABEL[plant_type] in text


def test_emissions_bar_starts_empty(game_env):
    assert game_env.elements["emissions-bar"].style.width == "0%"


def test_emissions_bar_fills_with_emissions(game_env):
    game_env.build("coal")
    game_env.state.advance_round(rng=NEVER_TRIGGER)
    game_env.module.render()
    width = game_env.elements["emissions-bar"].style.width
    assert width != "0%"


def test_emissions_bar_caps_at_full(game_env):
    game_env.state.emissions = 999999.0
    game_env.module.render()
    assert game_env.elements["emissions-bar"].style.width == "100%"


def test_score_bar_matches_score(game_env):
    game_env.build("solar")
    game_env.state.advance_round(rng=NEVER_TRIGGER)
    game_env.module.render()
    assert game_env.elements["score-bar"].style.width == "100%"


def test_event_display_has_no_severity_class_when_no_event(game_env):
    assert game_env.elements["event-display"].className == "event-display"


def test_event_display_gets_warning_class_for_brownout(game_env):
    game_env.build("coal")
    game_env.state.emissions = 300.0  # low severity -> brownout only
    game_env.state.advance_round(rng=ALWAYS_TRIGGER)
    game_env.module.render()
    assert "event-display--warning" in game_env.elements["event-display"].className


def test_event_display_gets_danger_class_for_damage(game_env):
    game_env.build("coal")
    game_env.state.emissions = 2000.0  # high severity -> damage
    game_env.state.advance_round(rng=ALWAYS_TRIGGER)
    game_env.module.render()
    assert "event-display--danger" in game_env.elements["event-display"].className
