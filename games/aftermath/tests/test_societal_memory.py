"""E29: societal memory (a ruinous run leaves a permanent, unique defence)."""

import json

import pytest


def _finish_ruinous_run(game_env, schedule=None):
    m = game_env.module
    if schedule is not None:
        m.run.schedule = list(schedule)
    m.run.resources = 1.0
    m.run.growth_capacity = 0
    while not m.run.is_complete():
        m.run.resources = min(m.run.resources, 1.0)
        m.run.resolve_next_event()


def test_starts_with_no_memories(game_env):
    m = game_env.module
    assert m.societal_memory == set()
    m.render()
    assert game_env.elements["societal-memory-display"].innerText == ""


def test_a_ruinous_run_forms_a_memory_of_its_worst_category(game_env):
    m = game_env.module
    _finish_ruinous_run(game_env, ["storm"] * 7)
    assert m.societal_memory == {"weather"}


def test_worst_category_is_by_total_damage(game_env):
    m = game_env.module
    log = [
        {"type": "flood", "damage": 10.0}, {"type": "heatwave", "damage": 10.0},
        {"type": "supply_chain", "damage": 25.0}, {"type": "infrastructure_failure", "damage": 5.0},
    ]
    assert m.worst_damage_category(log) == "non-weather"  # 30 vs 20 weather
    assert m.worst_damage_category([]) is None
    assert m.worst_damage_category([{"type": "civil_unrest", "damage": 1.0}]) == "social"


def test_a_run_that_survives_forms_no_memory(game_env):
    m = game_env.module
    assert m.record_societal_memory([{"type": "flood", "damage": 5.0}], m.VERY_BAD_RUN_SCORE + 1) is None
    assert m.societal_memory == set()


def test_the_threshold_is_inclusive(game_env):
    m = game_env.module
    assert m.record_societal_memory([{"type": "flood", "damage": 5.0}], m.VERY_BAD_RUN_SCORE) == "weather"


def test_an_already_remembered_category_is_not_reported_again(game_env):
    m = game_env.module
    log = [{"type": "flood", "damage": 5.0}]
    assert m.record_societal_memory(log, 0.0) == "weather"
    assert m.record_societal_memory(log, 0.0) is None


def test_memory_reduces_damage_from_its_category(game_env):
    m = game_env.module
    before = m.category_mitigation_bonus("supply_chain")
    m.societal_memory.add("non-weather")
    assert m.category_mitigation_bonus("supply_chain") == pytest.approx(before + m.SOCIETAL_MEMORY_BONUS["non-weather"])
    assert m.category_mitigation_bonus("flood") == 0  # weather untouched


def test_non_weather_memory_is_the_strongest_because_the_tree_offers_nothing_for_it(game_env):
    m = game_env.module
    assert m.SOCIETAL_MEMORY_BONUS["non-weather"] > m.SOCIETAL_MEMORY_BONUS["weather"]
    assert not any(cat == "non-weather" for cat, _ in m.CATEGORY_DAMAGE_BONUS.values())


def test_it_stacks_with_the_tree_but_never_reaches_immunity(game_env):
    m = game_env.module
    m.societal_memory.add("weather")
    m.skill_tree.unlocked.add("climate_hardening")
    assert m.category_mitigation_bonus("flood") == pytest.approx(0.20 + m.SOCIETAL_MEMORY_BONUS["weather"])
    assert m.run.mitigation_for("flood") <= m.MAX_MITIGATION


def test_a_memory_lowers_real_damage_in_a_later_run(game_env):
    m = game_env.module
    run = m.RunState()
    run.schedule = ["supply_chain"]
    run.resolve_next_event()
    plain = run.event_log[0]["damage"]
    m.societal_memory.add("non-weather")
    run2 = m.RunState()
    run2.schedule = ["supply_chain"]
    run2.resolve_next_event()
    assert run2.event_log[0]["damage"] < plain


def test_it_persists_and_reloads(game_env):
    m = game_env.module
    m.record_societal_memory([{"type": "supply_chain", "damage": 9.0}], 0.0)
    stored = m.localStorage.getItem(m.SOCIETAL_MEMORY_STORAGE_KEY)
    assert json.loads(stored) == ["non-weather"]
    assert m.load_societal_memory() == {"non-weather"}


def test_loading_ignores_bad_storage(game_env):
    m = game_env.module
    for raw in ("not json", "{}", "7", '["bogus", 3, null, "weather"]', "null"):
        m.localStorage.setItem(m.SOCIETAL_MEMORY_STORAGE_KEY, raw)
        loaded = m.load_societal_memory()
        assert loaded <= set(m.SOCIETAL_MEMORY_BONUS)
    m.localStorage.setItem(m.SOCIETAL_MEMORY_STORAGE_KEY, '["bogus", 3, null, "weather"]')
    assert m.load_societal_memory() == {"weather"}


def test_display_announces_once_then_lists(game_env):
    m = game_env.module
    m.memory_just_formed = "social"
    m.societal_memory.add("social")
    text = m.societal_memory_message()
    assert "left a mark" in text and "15%" in text and "Societal memory: social" in text
    again = m.societal_memory_message()
    assert "left a mark" not in again and "Societal memory: social" in again


def test_a_full_ruinous_run_shows_the_callout_in_the_page(game_env):
    m = game_env.module
    m.run.schedule = ["supply_chain"] * 7
    m.run.resources = 1.0
    while not m.run.is_complete():
        m.run.resources = 1.0
        m.run.resolve_next_event()
    m.render()
    assert "left a mark" in game_env.elements["societal-memory-display"].innerText


def test_memory_is_per_browser_not_part_of_the_save(game_env):
    m = game_env.module
    m.societal_memory.add("weather")
    assert "societal_memory" not in json.dumps(m.get_state())
