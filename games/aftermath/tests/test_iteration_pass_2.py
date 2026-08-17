"""Iteration Pass 2: diversified event types (two non-weather shocks —
supply-chain disruption, infrastructure failure — added to the same
scheduled-event structure) and a legacy system (each completed run
records which event types this settlement has weathered, referenced as
persistent flavor text rather than a mechanical bonus).
"""


def test_schedule_includes_non_weather_events(game_env):
    assert "supply_chain" in game_env.module.EVENT_SCHEDULE
    assert "infrastructure_failure" in game_env.module.EVENT_SCHEDULE


def test_first_two_scheduled_events_unchanged(game_env):
    # Pass 1 tests hardcode event_log[0]/[1] as flood/heatwave — confirm
    # the extension didn't disturb the front of the schedule.
    assert game_env.module.EVENT_SCHEDULE[0] == "flood"
    assert game_env.module.EVENT_SCHEDULE[1] == "heatwave"


def test_non_weather_events_have_labels_icons_and_damage(game_env):
    for event_type in ("supply_chain", "infrastructure_failure"):
        assert event_type in game_env.module.EVENT_LABEL
        assert event_type in game_env.module.EVENT_ICON
        assert event_type in game_env.module.EVENT_BASE_DAMAGE


def test_event_category_tags_weather_and_non_weather(game_env):
    assert game_env.module.EVENT_CATEGORY["flood"] == "weather"
    assert game_env.module.EVENT_CATEGORY["storm"] == "weather"
    assert game_env.module.EVENT_CATEGORY["supply_chain"] == "non-weather"
    assert game_env.module.EVENT_CATEGORY["infrastructure_failure"] == "non-weather"


def test_render_applies_category_class_to_next_event(game_env):
    game_env.module.render()
    assert "event-category--weather" in game_env.elements["next-event-display"].className


def test_render_applies_non_weather_category_class_after_resolving_to_it(game_env):
    # Schedule index 2 is supply_chain.
    game_env.resolve_event()
    game_env.resolve_event()
    game_env.module.render()
    assert "event-category--non-weather" in game_env.elements["next-event-display"].className


def test_legacy_starts_empty(game_env):
    assert game_env.module.legacy_events == set()


def test_legacy_message_before_any_run_completes(game_env):
    text = game_env.module.legacy_message()
    assert "first trial" in text


def test_legacy_records_event_types_on_run_completion(game_env):
    for _ in range(len(game_env.module.EVENT_SCHEDULE)):
        game_env.resolve_event()
    assert game_env.module.legacy_events == set(game_env.module.EVENT_SCHEDULE)


def test_legacy_persists_to_local_storage_on_run_completion(game_env):
    for _ in range(len(game_env.module.EVENT_SCHEDULE)):
        game_env.resolve_event()
    import json
    raw = game_env.local_storage.getItem(game_env.module.LEGACY_STORAGE_KEY)
    assert set(json.loads(raw)) == set(game_env.module.EVENT_SCHEDULE)


def test_legacy_message_after_run_completion_names_event_types(game_env):
    for _ in range(len(game_env.module.EVENT_SCHEDULE)):
        game_env.resolve_event()
    text = game_env.module.legacy_message()
    assert "Flood" in text
    assert "Supply-Chain Disruption" in text


def test_render_shows_legacy_message(game_env):
    game_env.module.render()
    assert len(game_env.elements["legacy-display"].innerText) > 0


def test_load_legacy_events_survives_a_fresh_module_load(game_env):
    for _ in range(len(game_env.module.EVENT_SCHEDULE)):
        game_env.resolve_event()
    reloaded = game_env.module.load_legacy_events()
    assert reloaded == set(game_env.module.EVENT_SCHEDULE)
