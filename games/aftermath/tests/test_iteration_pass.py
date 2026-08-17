"""Iteration pass: per-event severity variation (deterministic, off for
run 1), skill real-practice grounding text, and the context blurb.

Severity variation is deliberately off for run 1 specifically so it
doesn't disturb the run-1-vs-latest-run hope-angle comparison or any
of the many single-run exact-value tests elsewhere in this suite.
"""

import pytest


def test_first_run_has_run_number_one(game_env):
    assert game_env.run.run_number == 1


def test_event_severity_is_flat_for_run_one(game_env):
    for event_index in range(5):
        assert game_env.module.event_severity(1, event_index) == 1.0


def test_event_severity_varies_for_later_runs(game_env):
    severities = [game_env.module.event_severity(3, i) for i in range(5)]
    assert len(set(severities)) > 1
    for s in severities:
        assert game_env.module.SEVERITY_VARIATION_MIN <= s <= game_env.module.SEVERITY_VARIATION_MAX


def test_event_severity_is_reproducible_for_same_run_number(game_env):
    a = game_env.module.event_severity(4, 2)
    b = game_env.module.event_severity(4, 2)
    assert a == b


def test_new_run_increments_run_number(game_env):
    for _ in range(len(game_env.module.EVENT_SCHEDULE)):
        game_env.resolve_event()
    game_env.start_new_run()
    assert game_env.run.run_number == 2


def test_run_one_damage_values_unaffected_by_severity_system(game_env):
    game_env.resolve_event()
    # flood, no mitigation, run 1 -> severity locked at 1.0, same as before
    assert game_env.run.damage_taken == 40.0


def test_severity_label_thresholds(game_env):
    label = game_env.module.severity_label
    assert label(0.85) == "mild"
    assert label(1.0) == "typical"
    assert label(1.15) == "severe"


def test_render_shows_intensity_label_on_last_event(game_env):
    game_env.resolve_event()
    game_env.module.render()
    assert "typical intensity" in game_env.elements["last-event-display"].innerText


def test_render_shows_real_practice_text_for_each_skill(game_env):
    game_env.module.render()
    for skill_id in game_env.module.SKILLS:
        text = game_env.elements[f"skill-{skill_id}-practice"].innerText
        assert len(text) > 0
        assert text == game_env.module.SKILLS[skill_id]["real_practice"]
