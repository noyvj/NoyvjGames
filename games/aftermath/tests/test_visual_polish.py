"""Milestone 7: visual pass — event icons, a mitigation meter bar, and a
"last event" readout.
"""


def test_next_event_shows_icon(game_env):
    text = game_env.elements["next-event-display"].innerText
    assert game_env.module.EVENT_ICON["flood"] in text


def test_last_event_is_empty_before_any_event_resolves(game_env):
    assert game_env.elements["last-event-display"].innerText == ""


def test_last_event_shows_type_and_damage_after_resolving(game_env):
    game_env.resolve_event()
    text = game_env.elements["last-event-display"].innerText
    assert game_env.module.EVENT_ICON["flood"] in text
    assert "40" in text


def test_last_event_updates_to_most_recent(game_env):
    game_env.resolve_event()
    game_env.resolve_event()
    text = game_env.elements["last-event-display"].innerText
    assert game_env.module.EVENT_LABEL["heatwave"] in text


def test_mitigation_bar_starts_empty(game_env):
    assert game_env.elements["mitigation-bar"].style.width == "0%"


def test_mitigation_bar_reflects_resilience_capacity(game_env):
    game_env.invest_resilience()
    assert game_env.elements["mitigation-bar"].style.width == "5%"


def test_mitigation_bar_caps_at_max(game_env):
    game_env.run.resilience_capacity = 1000
    game_env.module.render()
    assert game_env.elements["mitigation-bar"].style.width == "85%"
