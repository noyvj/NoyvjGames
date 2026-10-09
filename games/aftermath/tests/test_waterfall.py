"""E-18: the damage waterfall (how the last event's damage was worked out)."""

import pytest


def _lines(game_env):
    return [c.innerText for c in game_env.elements["damage-waterfall-body"].children if c.className == "waterfall-line"]


def test_hidden_until_an_event_is_faced(game_env):
    assert game_env.elements["damage-waterfall"].hidden is True
    game_env.resolve_event()
    assert game_env.elements["damage-waterfall"].hidden is False


def test_breakdown_adds_up_to_the_actual_damage(game_env):
    m = game_env.module
    for _ in range(4):
        game_env.invest_resilience()
    game_env.module.skill_tree.unlocked.update({"early_warning", "climate_hardening"})
    m.societal_memory.add("weather")
    game_env.resolve_event()
    b = m.run.last_breakdown
    assert b["final"] == pytest.approx(m.run.event_log[-1]["damage"])
    prevented = sum(s["damage"] for s in b["sources"]) - b["cap_added_back"]
    assert b["unmitigated"] - prevented == pytest.approx(b["final"])


def test_every_source_is_listed_with_its_share(game_env):
    m = game_env.module
    game_env.invest_resilience()
    game_env.invest_resilience()
    m.skill_tree.unlocked.add("early_warning")
    game_env.resolve_event()
    lines = _lines(game_env)
    assert lines[0] == "Base damage: 40"
    assert any(line.startswith("Severity 1.00") for line in lines)
    assert any(line.startswith("Resilience investment: −4 (10%") for line in lines)
    assert any(line.startswith("Early Warning Systems: −4 (10%") for line in lines)
    assert lines[-1] == f"Damage taken: {m.run.event_log[-1]['damage']:.0f}"


def test_the_cap_is_shown_when_it_takes_effect(game_env):
    m = game_env.module
    m.run.resilience_capacity = 25  # 125% raw
    game_env.resolve_event()
    b = m.run.last_breakdown
    assert b["mitigation"] == pytest.approx(m.MAX_MITIGATION)
    assert b["cap_added_back"] > 0
    assert any(line.startswith("Mitigation cap (85%)") for line in _lines(game_env))
    assert b["final"] == pytest.approx(40 * 0.15)


def test_bar_segments_cover_the_whole_damage_and_have_a_text_label(game_env):
    m = game_env.module
    game_env.invest_resilience()
    game_env.resolve_event()
    segments = m.waterfall_segments(m.run.last_breakdown)
    assert sum(share for _, share, _ in segments) == pytest.approx(1.0)
    bar = game_env.elements["damage-waterfall-body"].children[0]
    assert bar.getAttribute("role") == "img"
    assert "Damage taken" in bar.getAttribute("aria-label")


def test_no_breakdown_after_a_load_or_a_new_run(game_env):
    m = game_env.module
    game_env.resolve_event()
    snapshot = m.get_state()
    m.load_state(snapshot)
    assert m.run.last_breakdown is None and game_env.elements["damage-waterfall"].hidden is True
    for _ in range(6):
        game_env.resolve_event()
    game_env.start_new_run()
    assert game_env.elements["damage-waterfall"].hidden is True


def test_category_skill_and_memory_are_separate_lines(game_env):
    m = game_env.module
    m.skill_tree.unlocked.add("civic_preparedness")
    m.societal_memory.add("social")
    m.run.event_index = 6  # civil unrest
    m.run.event_log = [{"type": "flood", "damage": 0.0, "severity": 1.0}] * 6
    game_env.resolve_event()
    labels = [s["label"] for s in m.run.last_breakdown["sources"]]
    assert labels == ["Category skill", "Societal memory"]


def test_saved_state_has_no_new_field(game_env):
    game_env.resolve_event()
    assert "last_breakdown" not in game_env.module.get_state()
