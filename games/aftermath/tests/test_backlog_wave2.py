"""Per-game backlog wave 2 (planning/TODO.md "Per-game: Aftermath"):
E2, E4-E8, E10, E12-E14, E16, E18, E20, E22, E24-E26, E28, E30a/b."""

import json

from .test_confirm_dialog import install_fake_confirm_dialog


def _finish_run(env):
    while not env.run.is_complete():
        env.resolve_event()


def _text(env, id_):
    return env.elements[id_].innerText


# E2 ----------------------------------------------------------------------
def test_toast_duration_scales_with_grounding_text_and_is_clamped(game_env):
    m = game_env.module
    durations = {sid: m.skill_toast_duration_ms(sid) for sid in m.SKILLS}
    assert all(m.SKILL_TOAST_MIN_MS <= d <= m.SKILL_TOAST_MAX_MS for d in durations.values())
    longest = max(m.SKILLS, key=lambda s: len(m.SKILLS[s]["real_practice"]))
    shortest = min(m.SKILLS, key=lambda s: len(m.SKILLS[s]["real_practice"]))
    assert durations[longest] >= durations[shortest]


def test_unlock_toast_timer_uses_scaled_duration(game_env):
    game_env.skill_tree.add_knowledge(10)
    game_env.unlock_skill("early_warning")
    delays = [d for _cb, d in game_env.timers.pending]
    assert game_env.module.skill_toast_duration_ms("early_warning") in delays


# E4 / E25 ----------------------------------------------------------------
def test_runs_completed_counter_always_rendered(game_env):
    assert _text(game_env, "runs-completed-display") == "Runs completed: 0"
    _finish_run(game_env)
    assert _text(game_env, "runs-completed-display") == "Runs completed: 1"


def test_settlement_name_persists_and_shows_in_counter(game_env):
    game_env.elements["settlement-name-input"].value = "  New Haven  "
    game_env.elements["settlement-name-input"].dispatch("change", None)
    assert _text(game_env, "runs-completed-display").startswith("New Haven — ")
    stored = json.loads(game_env.local_storage.getItem("aftermath_meta_v1"))
    assert stored["settlement_name"] == "New Haven"


def test_settlement_name_is_length_capped_and_malformed_meta_is_safe(game_env):
    m = game_env.module
    m.set_settlement_name("x" * 200)
    assert len(m.meta["settlement_name"]) == m.SETTLEMENT_NAME_MAX
    assert m._sanitize_meta("garbage") == m._default_meta()
    assert m._sanitize_meta({"pinned_skills": "nope", "settlement_name": 5})["pinned_skills"] == []


# E6 ----------------------------------------------------------------------
def test_extended_toggle_label_shows_event_count(game_env):
    m = game_env.module
    assert str(len(m.EVENT_SCHEDULE) * 2) in _text(game_env, "extended-run-toggle-label")


# E8 / E28 ----------------------------------------------------------------
def test_first_zero_score_run_shows_reassurance_once(game_env):
    m = game_env.module
    game_env.run.resources = 0
    game_env.run.event_index = len(game_env.run.schedule) - 1
    game_env.resolve_event()
    assert game_env.run.is_complete()
    assert "skill tree persists" in _text(game_env, "callout-display")
    assert game_env.elements["callout-display"].hidden is False
    assert m.meta["seen_negative_tip"] is True
    game_env.start_new_run()
    assert game_env.elements["callout-display"].hidden is True
    game_env.run.resources = 0
    game_env.run.event_index = len(game_env.run.schedule) - 1
    game_env.resolve_event()
    assert _text(game_env, "callout-display") == ""


def test_harsh_severity_callout_fires_once_when_beyond_base_spread(game_env):
    m = game_env.module
    game_env.skill_tree.unlocked = set(m.SKILLS)
    game_env.start_new_run()
    for _ in range(len(game_env.run.schedule)):
        game_env.resolve_event()
        if m.meta["seen_harsh_callout"]:
            break
    if any(e["severity"] > m.SEVERITY_VARIATION_MAX for e in game_env.run.event_log):
        assert "harder than a first-run event" in m.HARSH_SEVERITY_CALLOUT
        assert m.meta["seen_harsh_callout"] is True


def test_harsh_callout_does_not_fire_within_base_spread(game_env):
    m = game_env.module

    class R:
        event_log = [{"severity": 1.1}]

        def is_complete(self):
            return False

    m._maybe_trigger_callouts(R())
    assert m.callout_message == ""
    R.event_log = [{"severity": 1.2}]
    m._maybe_trigger_callouts(R())
    assert "harder" in m.callout_message
    assert m.meta["seen_harsh_callout"] is True


# E5 ----------------------------------------------------------------------
def test_generational_memory_references_a_past_run_at_same_slot(game_env):
    m = game_env.module
    _finish_run(game_env)
    game_env.start_new_run()
    texts = []
    for _ in range(len(game_env.run.schedule)):
        texts.append(m.generational_memory_text(game_env.run))
        game_env.run.event_index += 1
    joined = " ".join(t for t in texts if t)
    assert "Memory of Run #1" in joined


def test_no_generational_memory_without_history(game_env):
    assert game_env.module.generational_memory_text(game_env.run) == ""


# E7 ----------------------------------------------------------------------
def test_lifetime_runs_widen_severity_spread_up_to_a_cap(game_env):
    m = game_env.module
    assert m.lifetime_severity_widening(0) == 0
    assert m.lifetime_severity_widening(5) > 0
    assert m.lifetime_severity_widening(10_000) == m.SEVERITY_LIFETIME_RANGE_CAP
    lo0, hi0 = m.severity_bounds(0, 0)
    lo1, hi1 = m.severity_bounds(0, 10)
    assert lo1 < lo0 and hi1 > hi0
    assert abs((lo1 + hi1) / 2 - 1.0) < 1e-9


# E10 ---------------------------------------------------------------------
def test_toughest_run_shows_its_event_sequence(game_env):
    _finish_run(game_env)
    text = _text(game_env, "toughest-run-display")
    assert "Toughest run yet" in text and "Flood" in text and "→" in text


def test_toughest_sequence_is_none_without_detailed_log(game_env):
    m = game_env.module
    m.run_history.append(12.0)
    assert m.toughest_run_sequence() is None
    assert m.toughest_run_text().startswith("Toughest run yet: Run #1 scored 12")


# E12 ---------------------------------------------------------------------
def test_toughest_badge_needs_a_surviving_severe_average_run(game_env):
    m = game_env.module
    assert m.toughest_survived_run_badge_earned() is False
    m.run_log_history.append({"score": 10, "event_log": [{"severity": 1.3}] * 3})
    assert m.toughest_survived_run_badge_earned() is True
    m.run_log_history[:] = [{"score": 0, "event_log": [{"severity": 1.3}] * 3}]
    assert m.toughest_survived_run_badge_earned() is False
    m.run_log_history[:] = [{"score": 10, "event_log": [{"severity": 1.3}] * 3}]
    m.render()
    assert "settlement-badge--earned" in game_env.elements["settlement-badge-toughest"].classList


# E13 ---------------------------------------------------------------------
def test_extended_run_gets_epilogue_normal_run_does_not(game_env):
    m = game_env.module
    _finish_run(game_env)
    assert m.extended_epilogue_text(game_env.run) == ""
    game_env.elements["extended-run-toggle"].checked = True
    game_env.start_new_run()
    assert m.extended_epilogue_text(game_env.run) == ""  # not complete yet
    _finish_run(game_env)
    assert m.extended_epilogue_text(game_env.run).startswith("Epilogue")
    kids = game_env.elements["run-summary-panel"].children
    assert any(getattr(k, "className", "") == "run-epilogue" for k in kids)


# E14 / E20 ---------------------------------------------------------------
def test_expected_damage_shows_range_containing_the_estimate(game_env):
    m = game_env.module
    low, high = m.expected_damage_range(game_env.run)
    damage, _ = m.expected_next_event_damage(game_env.run)
    assert low <= damage + 1e-9 <= high + 1e-9 or game_env.run.run_number == 1
    assert "range" in _text(game_env, "expected-damage-display")


def test_severity_tooltip_explains_skill_effect(game_env):
    m = game_env.module
    assert "Run 1" in m.severity_tooltip_text(1)
    tip = m.severity_tooltip_text(3)
    assert "unlocked skill" in tip and "0.85" in tip
    game_env.start_new_run()
    assert game_env.elements["expected-damage-display"].title


# E16 / E24 ---------------------------------------------------------------
def test_record_runs_flagged_and_first_run_never_is(game_env):
    m = game_env.module
    m.run_log_history[:] = [{"score": s} for s in (10, 5, 30, 20, 40)]
    assert m.new_record_run_indexes() == {2, 4}


def test_past_runs_panel_marks_record_card_and_shows_category_icons(game_env):
    m = game_env.module
    log = [{"type": "flood", "damage": 10, "severity": 1.0}, {"type": "civil_unrest", "damage": 5, "severity": 1.0}]
    m.run_log_history[:] = [
        {"run_number": 1, "score": 10, "resilience_capacity": 0, "growth_capacity": 0, "knowledge_earned": 1, "event_log": log},
        {"run_number": 2, "score": 50, "resilience_capacity": 0, "growth_capacity": 0, "knowledge_earned": 2, "event_log": log},
    ]
    game_env.toggle_past_runs()
    cards = game_env.elements["past-runs-panel"].children
    assert cards[0].className == "past-run-card past-run-card--record"
    assert cards[1].className == "past-run-card"
    lines = [c.innerText for c in cards[0].children[1:]]
    assert lines[0].startswith("🌦️") and lines[1].startswith("👥")


# E18 ---------------------------------------------------------------------
def test_knowledge_preview_bumps_only_when_it_increases(game_env):
    m = game_env.module
    m.render()
    game_env.timers.flush()
    assert "knowledge-bump" not in game_env.elements["knowledge-preview-display"].classList
    game_env.run.resources += 100
    m.render()
    assert "knowledge-bump" in game_env.elements["knowledge-preview-display"].classList
    game_env.timers.flush()
    assert "knowledge-bump" not in game_env.elements["knowledge-preview-display"].classList


# E22 -----------------------------------------------------------------
# Z22 cross-game audit: the refund total used to show on the reset
# button's own second-click label; now that the reset routes through the
# shared ConfirmDialog (see tests/test_confirm_dialog.py), it shows in
# the dialog's message instead.
def test_reset_confirm_shows_refund_total(game_env):
    game_env.skill_tree.add_knowledge(10)
    game_env.unlock_skill("early_warning")  # cost 5, leaves 5
    fake_window = install_fake_confirm_dialog()

    game_env.reset_skill_tree_click()

    message = fake_window.ConfirmDialog.calls[0]["message"]
    assert "10 knowledge points" in message
    assert game_env.module.reset_refund_amount() == 5

    fake_window.ConfirmDialog.confirm()
    assert game_env.skill_tree.knowledge_points == 10


# E26 ---------------------------------------------------------------------
def test_export_shows_human_readable_summary(game_env):
    _finish_run(game_env)
    game_env.export_progress()
    status = _text(game_env, "progress-code-status")
    assert "Contains:" in status and "1 run completed" in status and "skills unlocked" in status


def test_export_import_round_trips_meta(game_env):
    game_env.module.set_settlement_name("Harbor")
    game_env.module.toggle_pin_skill("early_warning")
    code = game_env.export_progress()
    game_env.module.set_settlement_name("Other")
    game_env.module.meta["pinned_skills"].clear()
    game_env.import_progress(code)
    assert game_env.module.meta["settlement_name"] == "Harbor"
    assert game_env.module.meta["pinned_skills"] == ["early_warning"]


# E30a / E30b -------------------------------------------------------------
def test_eta_needs_history_then_estimates_runs(game_env):
    m = game_env.module
    assert m.runs_until_affordable("early_warning") is None
    assert "Complete a run" in _text(game_env, "skill-early_warning-eta")
    m.run_history.extend([100, 100])
    game_env.skill_tree.lifetime_knowledge = 4  # avg 2/run
    game_env.skill_tree.knowledge_points = 1
    assert m.runs_until_affordable("early_warning") == 2  # needs 4, ceil(4/2)
    game_env.skill_tree.knowledge_points = 5
    assert m.runs_until_affordable("early_warning") == 0


def test_pin_toggle_persists_and_summary_line_tracks_pinned_only(game_env):
    m = game_env.module
    game_env.elements["skill-early_warning-pin-button"].dispatch("click", None)
    assert m.meta["pinned_skills"] == ["early_warning"]
    assert "Early Warning Systems" in _text(game_env, "pinned-skills-display")
    assert "Adaptive" not in _text(game_env, "pinned-skills-display")
    assert json.loads(game_env.local_storage.getItem("aftermath_meta_v1"))["pinned_skills"] == ["early_warning"]
    game_env.elements["skill-early_warning-pin-button"].dispatch("click", None)
    assert _text(game_env, "pinned-skills-display") == ""


def test_pin_hidden_once_unlocked_and_cannot_pin_unlocked(game_env):
    game_env.skill_tree.add_knowledge(10)
    game_env.unlock_skill("early_warning")
    assert game_env.elements["skill-early_warning-pin-button"].hidden is True
    assert game_env.module.toggle_pin_skill("early_warning") is False


# ---------------------------------------------------------------------------
# E1/E3: seventh-node skill-tree expansion -- weather vs social-shock branches.
# ---------------------------------------------------------------------------
def test_specialization_nodes_have_branch_prereqs(game_env):
    m = game_env.module
    assert m.SKILLS["civic_preparedness"]["prereqs"] == ["community_reserves"]
    assert set(m.SKILLS["climate_hardening"]["prereqs"]) == {"reinforced_infrastructure", "early_warning"}
    game_env.skill_tree.add_knowledge(50)
    assert not game_env.skill_tree.can_unlock("civic_preparedness")
    game_env.unlock_skill("community_reserves")
    assert game_env.skill_tree.can_unlock("civic_preparedness")


def test_civic_preparedness_only_reduces_social_events(game_env):
    m = game_env.module
    base_social = m.EVENT_BASE_DAMAGE["civil_unrest"]
    game_env.skill_tree.unlocked.add("civic_preparedness")
    r = m.RunState()
    assert abs(r.mitigation_for("civil_unrest") - 0.35) < 1e-9
    assert r.mitigation_for("flood") == 0
    r.event_index = len(r.schedule) - 1  # civil_unrest slot
    before = r.resources
    r.resolve_next_event()
    assert abs((before - r.resources) - base_social * 0.65) < 1e-6


def test_climate_hardening_reduces_weather_and_stays_capped(game_env):
    m = game_env.module
    game_env.skill_tree.unlocked.update({"climate_hardening"})
    r = m.RunState()
    assert abs(r.mitigation_for("storm") - 0.20) < 1e-9
    assert r.mitigation_for("supply_chain") == 0
    r.resilience_capacity = 100
    assert r.mitigation_for("storm") == m.MAX_MITIGATION


def test_expected_damage_preview_matches_resolution_with_specialization(game_env):
    m = game_env.module
    game_env.skill_tree.unlocked.update({"climate_hardening", "civic_preparedness"})
    r = m.RunState(run_number=4)
    for _ in range(len(r.schedule)):
        predicted, _sev = m.expected_next_event_damage(r)
        before = r.resources
        r.resolve_next_event()
        assert abs(r.event_log[-1]["damage"] - predicted) < 1e-9
        assert before >= 0


def test_new_skills_render_rows_and_badges(game_env):
    game_env.skill_tree.add_knowledge(30)
    game_env.unlock_skill("community_reserves")
    game_env.unlock_skill("civic_preparedness")
    assert "unlocked" in _text(game_env, "skill-civic_preparedness-status")
    assert "settlement-badge--earned" in game_env.elements["settlement-badge-civic_preparedness"].classList
    assert "requires" in _text(game_env, "skill-climate_hardening-status")


# ---------------------------------------------------------------------------
# E15: build-diversity achievements.
# ---------------------------------------------------------------------------
def _complete_with(env, resilience, growth):
    env.run.resilience_capacity = resilience
    env.run.growth_capacity = growth
    env.run.event_index = len(env.run.schedule) - 1
    env.resolve_event()


def test_deep_specialist_and_broad_generalist_both_reward(game_env):
    m = game_env.module
    _complete_with(game_env, 6, 0)
    ids = m.achievement_ids_earned()
    assert "deep_specialist" in ids and "broad_generalist" not in ids and "both_paths" not in ids
    game_env.start_new_run()
    _complete_with(game_env, 3, 3)
    ids = m.achievement_ids_earned()
    assert {"deep_specialist", "broad_generalist", "both_paths"} <= set(ids)


def test_lopsided_but_not_deep_run_earns_neither(game_env):
    _complete_with(game_env, 2, 1)
    ids = game_env.module.achievement_ids_earned()
    assert "deep_specialist" not in ids and "broad_generalist" not in ids
