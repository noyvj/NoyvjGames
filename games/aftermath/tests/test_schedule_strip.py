"""E-17: the schedule strip (every event of the run, with details)."""

import pytest


def _chips(game_env):
    return game_env.elements["schedule-strip"].children


def test_strip_has_one_chip_per_event_and_marks_the_next(game_env):
    m = game_env.module
    chips = _chips(game_env)
    assert len(chips) == len(m.run.schedule) == 7
    assert "schedule-chip--next" in chips[0].className
    assert all("schedule-chip--upcoming" in c.className for c in chips[1:])
    assert chips[0].innerText.startswith("▶ 1 ")
    assert "Flood" in chips[0].innerText


def test_every_chip_carries_its_category_class_and_a_text_detail(game_env):
    m = game_env.module
    for chip, event_type in zip(_chips(game_env), m.run.schedule):
        assert f"event-category--{m.EVENT_CATEGORY[event_type]}" in chip.className
        assert chip.title and chip.getAttribute("aria-label") == chip.title
        assert chip.getAttribute("data-detail") == chip.title
        assert chip.getAttribute("tabindex") == "0"


def test_facing_an_event_turns_its_chip_into_a_done_chip_with_the_real_damage(game_env):
    m = game_env.module
    game_env.resolve_event()
    chips = _chips(game_env)
    assert "schedule-chip--done" in chips[0].className and chips[0].innerText.startswith("✓ 1 ")
    assert "schedule-chip--next" in chips[1].className
    logged = m.run.event_log[0]["damage"]
    assert f"Faced: {logged:.0f} damage" in chips[0].title


def test_upcoming_damage_is_exact_and_follows_the_current_build(game_env):
    m = game_env.module
    before = m.schedule_strip_entries(m.run)[2]  # Supply-chain disruption
    game_env.invest_resilience()
    after = m.schedule_strip_entries(m.run)[2]
    assert after["damage"] < before["damage"]
    assert after["damage"] == pytest.approx(
        m.EVENT_BASE_DAMAGE["supply_chain"] * after["severity"] * (1 - m.run.mitigation_for("supply_chain"))
    )


def test_the_category_bonus_is_named_in_the_detail(game_env):
    m = game_env.module
    m.skill_tree.unlocked.add("climate_hardening")
    m.render()
    flood = _chips(game_env)[0].title
    assert "20% category bonus" in flood
    assert "no category bonus" in _chips(game_env)[2].title  # supply chain


def test_the_detail_line_defaults_to_the_next_event_and_run_end_says_so(game_env):
    m = game_env.module
    detail = game_env.elements["schedule-detail"]
    assert detail.innerText == _chips(game_env)[0].title
    assert detail.getAttribute("data-default") == detail.innerText
    for _ in range(7):
        game_env.resolve_event()
    assert m.run.is_complete()
    assert "Run complete" in detail.innerText
    assert all("schedule-chip--done" in c.className for c in _chips(game_env))


def test_extended_run_shows_every_event_and_a_new_scenario_changes_the_strip(game_env):
    m = game_env.module
    game_env.elements["scenario-select"].value = "heat_season"
    game_env.elements["scenario-select"].dispatch("change", None)
    assert "Heat-Health Emergency" in _chips(game_env)[1].innerText
    m.run = m.RunState(extended=True)
    m.render()
    assert len(_chips(game_env)) == 14


def test_strip_survives_a_load_without_a_log_entry_for_every_index(game_env):
    m = game_env.module
    m.load_state({
        "run_number": 2, "event_index": 2, "resources": 100.0, "resilience_capacity": 0,
        "growth_capacity": 0, "damage_taken": 0.0, "event_log": [],
    })
    chips = _chips(game_env)
    assert len(chips) == 7
    # no log to read for events 1-2: they show as upcoming rather than crashing
    assert "schedule-chip--upcoming" in chips[0].className
    assert "schedule-chip--next" in chips[2].className
