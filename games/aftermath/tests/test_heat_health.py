"""FY-3: a fourth event category ("health", first event type heat_mortality).

The Classic mix is deliberately untouched, so every test here is either about
the new Heat season scenario that carries the new event, or about proving the
older saves, codex and achievements still behave."""

import json

import pytest


def _select_scenario(game_env, name):
    game_env.elements["scenario-select"].value = name
    game_env.elements["scenario-select"].dispatch("change", None)


# ---- schedule ---------------------------------------------------------------
def test_classic_schedule_is_unchanged_and_has_no_health_event(game_env):
    m = game_env.module
    assert m.EVENT_SCHEDULE == ["flood", "heatwave", "supply_chain", "storm", "infrastructure_failure", "flood", "civil_unrest"]
    assert "heat_mortality" not in m.EVENT_SCHEDULE
    assert m.run.scenario == "classic"


def test_heat_season_is_a_seven_event_schedule_with_two_heat_health_emergencies(game_env):
    m = game_env.module
    schedule = m.SCENARIOS["heat_season"]["schedule"]
    assert len(schedule) == 7 and schedule.count("heat_mortality") == 2
    assert m.RunState(scenario="heat_season").schedule == schedule
    assert m.RunState(scenario="heat_season", extended=True).schedule == schedule * 2


def test_only_the_heat_season_scenario_contains_the_new_event(game_env):
    m = game_env.module
    carriers = [name for name, spec in m.SCENARIOS.items() if "heat_mortality" in spec["schedule"]]
    assert carriers == ["heat_season"]


def test_the_scenario_selector_swaps_in_the_heat_season(game_env):
    m = game_env.module
    _select_scenario(game_env, "heat_season")
    assert m.run.scenario == "heat_season"
    assert "heat-health" in game_env.elements["scenario-blurb"].innerText


# ---- category, damage, mitigation -------------------------------------------
def test_new_event_is_fully_described(game_env):
    m = game_env.module
    assert m.EVENT_CATEGORY["heat_mortality"] == "health"
    for table in (m.EVENT_LABEL, m.EVENT_ICON, m.EVENT_BASE_DAMAGE, m.REAL_WORLD_EXAMPLES):
        assert "heat_mortality" in table
    assert m.CATEGORY_ICON["health"]
    assert set(m.EVENT_CATEGORY) == set(m.EVENT_LABEL)


def test_heat_health_damage_uses_general_mitigation_only(game_env):
    m = game_env.module
    r = m.RunState(scenario="heat_season")
    r.event_index = 1  # the first heat_mortality
    r.resilience_capacity = 4  # 20% general mitigation
    r.resolve_next_event()
    entry = r.event_log[-1]
    assert entry["type"] == "heat_mortality"
    assert entry["damage"] == pytest.approx(m.EVENT_BASE_DAMAGE["heat_mortality"] * 0.8)


def test_skill_tree_specialisations_do_not_touch_the_health_category(game_env):
    m = game_env.module
    m.skill_tree.unlocked.update({"civic_preparedness", "climate_hardening"})
    assert m.category_mitigation_bonus("heat_mortality") == 0
    m.skill_tree.unlocked.add("early_warning")
    r = m.RunState(scenario="heat_season")
    assert r.mitigation_for("heat_mortality") == pytest.approx(0.10)


def test_a_ruinous_health_run_forms_a_health_societal_memory(game_env):
    m = game_env.module
    log = [{"type": "heat_mortality", "damage": 90.0, "severity": 1.0}, {"type": "flood", "damage": 10.0, "severity": 1.0}]
    assert m.worst_damage_category(log) == "health"
    assert m.record_societal_memory(log, 0.0) == "health"
    assert "health" in m.societal_memory
    assert m.category_mitigation_bonus("heat_mortality") == pytest.approx(0.25)
    assert m.category_mitigation_bonus("flood") == 0
    assert "health" in m.load_societal_memory()  # survives a reload


def test_older_societal_memory_still_loads(game_env):
    m = game_env.module
    m.localStorage.setItem(m.SOCIETAL_MEMORY_STORAGE_KEY, json.dumps(["weather", "social", "bogus"]))
    assert m.load_societal_memory() == {"weather", "social"}


# ---- codex and achievements ---------------------------------------------------
def test_codex_has_seven_pages_and_the_new_one_says_how_to_find_it(game_env):
    m = game_env.module
    done, total = m.codex_completion()
    assert (done, total) == (0, 7)
    row = next(r for r in m.codex_entries() if r["type"] == "heat_mortality")
    assert row["category"] == "health" and row["faced"] == 0
    assert "Heat season" in m.codex_stats_text(row)
    flood = next(r for r in m.codex_entries() if r["type"] == "flood")
    assert "scenario" not in m.codex_stats_text(flood)


def test_facing_a_heat_health_emergency_fills_its_page_and_unlocks_the_note(game_env):
    m = game_env.module
    _select_scenario(game_env, "heat_season")
    game_env.resolve_event()
    game_env.resolve_event()  # the first heat_mortality
    row = next(r for r in m.codex_entries() if r["type"] == "heat_mortality")
    assert row["faced"] == 1 and row["example"]["title"] == "The 1995 Chicago heat wave"
    assert row["example"]["read"] == "2026-10-09"


def test_a_complete_old_codex_keeps_seen_it_all_and_the_new_page_has_its_own_achievement(game_env):
    m = game_env.module
    m.legacy_events.update(m.CODEX_CORE_TYPES)  # a player who finished the original six pages
    earned = m.achievement_ids_earned()
    assert "codex_complete" in earned
    assert "codex_full_record" not in earned and "heat_health_faced" not in earned
    # the six-page player is now 6/7 on the codex, but still holds the older badge
    assert m.codex_completion() == (6, 7)
    entry = next(a for a in m.achievements_summary() if a["id"] == "codex_complete")
    assert entry["progress"] == (6, 6) and entry["earned"]
    m.legacy_events.add("heat_mortality")
    earned = m.achievement_ids_earned()
    assert {"codex_complete", "codex_full_record", "heat_health_faced"} <= set(earned)
    full = next(a for a in m.achievements_summary() if a["id"] == "codex_full_record")
    assert full["progress"] == (7, 7)


def test_new_achievements_exist_in_the_catalog(game_env):
    m = game_env.module
    ids = {a["id"] for a in m.ACHIEVEMENTS}
    assert {"heat_health_faced", "codex_full_record", "codex_complete"} <= ids
    assert all(a["id"] in m.ACHIEVEMENT_CHECKS for a in m.ACHIEVEMENTS)


# ---- legacy, stats, scars -------------------------------------------------------
def test_completing_a_heat_season_records_legacy_counts_scars_and_stats(game_env):
    m = game_env.module
    _select_scenario(game_env, "heat_season")
    for _ in range(7):
        game_env.resolve_event()
    assert m.run.is_complete()
    assert m.legacy_event_counts["heat_mortality"] == 2
    assert m.legacy_category_totals()["health"] == 2
    assert m.legacy_scar_tiers()["health"] == 1
    m.render()
    assert "settlement-legacy-scar--tier-1" in game_env.elements["settlement-legacy-scar-health"].classList._classes
    stats = m.lifetime_stats()
    assert stats["category_damage"]["health"] > 0
    assert any(item["type"] == "heat_mortality" for item in stats["matchups"])
    assert "Heat-Health Emergency" in m.legacy_message()


def test_health_damage_row_is_hidden_in_stats_until_it_has_damage(game_env):
    for _ in range(7):
        game_env.resolve_event()
    game_env.module.on_toggle_stats()
    texts = []

    def walk(el):
        texts.append(el.innerText)
        for child in el.children:
            walk(child)

    walk(game_env.elements["stats-panel"])
    joined = " ".join(texts)
    assert "Weather" in joined and "Health" not in joined


def test_old_legacy_counts_without_the_new_type_still_load(game_env):
    m = game_env.module
    m.localStorage.setItem(m.LEGACY_COUNTS_STORAGE_KEY, json.dumps({"flood": 3, "civil_unrest": 1}))
    counts = m.load_legacy_event_counts()
    assert counts == {"flood": 3, "civil_unrest": 1}
    assert m.legacy_scar_tier(m.legacy_category_totals()["health"]) == 0


# ---- save round trip ------------------------------------------------------------
def test_heat_season_save_round_trip(game_env):
    m = game_env.module
    _select_scenario(game_env, "heat_season")
    game_env.resolve_event()
    game_env.resolve_event()
    snapshot = json.loads(json.dumps(m.get_state()))
    assert snapshot["scenario"] == "heat_season"
    assert snapshot["event_log"][1]["type"] == "heat_mortality"
    game_env.start_new_run()
    m.load_state(snapshot)
    assert m.run.scenario == "heat_season"
    assert m.run.event_index == 2
    assert m.run.next_event_type() == "supply_chain"
    assert m.run.event_log[1]["type"] == "heat_mortality"
    # the loaded run can be played to the end and still pays out
    while not m.run.is_complete():
        game_env.resolve_event()
    assert m.run.is_complete()


def test_a_classic_save_from_before_this_change_loads_unchanged(game_env):
    m = game_env.module
    old_save = {
        "run_number": 3, "event_index": 2, "resources": 150.0, "resilience_capacity": 1,
        "growth_capacity": 1, "damage_taken": 60.0,
        "event_log": [{"type": "flood", "damage": 40.0, "severity": 1.0}, {"type": "heatwave", "damage": 20.0, "severity": 1.0}],
    }
    assert m.load_state(old_save) is True
    assert m.run.scenario == "classic" and m.run.schedule == m.EVENT_SCHEDULE
    assert m.run.next_event_type() == "supply_chain"
    assert "scenario" not in m.get_state()


def test_current_run_is_shown_with_the_new_category_class(game_env):
    _select_scenario(game_env, "heat_season")
    game_env.resolve_event()
    assert "event-category--health" in game_env.elements["next-event-display"].className
    game_env.resolve_event()
    assert "event-category--health" in game_env.elements["last-event-display"].className
    assert "Heat-Health Emergency" in game_env.elements["last-event-display"].innerText
