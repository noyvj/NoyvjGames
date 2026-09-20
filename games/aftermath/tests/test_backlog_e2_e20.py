"""Per-game backlog items E2-E4, E6-E20 (planning/TODO.md's "Per-game:
Aftermath" checklist -- E1 is covered by the mobile-dock rollout, E5 is
parked in LATER.md). Each item gets at least one focused test on the
underlying logic, plus a render/DOM check where the item is UI-visible.
"""

import json


# ---------------------------------------------------------------------------
# E2/E3: a fourth and fifth skill-tree node, with a branching/prerequisite
# structure.
# ---------------------------------------------------------------------------
def test_five_skills_exist_with_prereqs_field(game_env):
    module = game_env.module
    assert len(module.SKILLS) == 7
    for skill in module.SKILLS.values():
        assert "prereqs" in skill


def test_mutual_aid_network_cannot_unlock_without_its_prereqs(game_env):
    game_env.skill_tree.add_knowledge(20)
    assert not game_env.skill_tree.can_unlock("mutual_aid_network")
    assert set(game_env.skill_tree.missing_prereqs("mutual_aid_network")) == {
        "reinforced_infrastructure",
        "community_reserves",
    }


def test_mutual_aid_network_unlockable_once_prereqs_met(game_env):
    game_env.skill_tree.add_knowledge(20)
    game_env.unlock_skill("reinforced_infrastructure")
    game_env.unlock_skill("community_reserves")
    assert game_env.skill_tree.missing_prereqs("mutual_aid_network") == []
    assert game_env.skill_tree.can_unlock("mutual_aid_network")
    game_env.unlock_skill("mutual_aid_network")
    assert "mutual_aid_network" in game_env.skill_tree.unlocked


def test_adaptive_growth_grants_starting_growth_capacity(game_env):
    game_env.skill_tree.add_knowledge(20)
    game_env.unlock_skill("adaptive_growth")
    game_env.start_new_run()
    assert game_env.run.growth_capacity == 1


def test_mutual_aid_network_adds_flat_mitigation(game_env):
    game_env.skill_tree.add_knowledge(20)
    game_env.unlock_skill("reinforced_infrastructure")
    game_env.unlock_skill("community_reserves")
    game_env.unlock_skill("mutual_aid_network")
    game_env.start_new_run()
    # reinforced_infrastructure -> +2 resilience capacity -> 10% mitigation,
    # plus mutual_aid_network's own flat +5%.
    assert round(game_env.run.mitigation_fraction(), 6) == 0.15


def test_render_shows_prereq_lock_reason(game_env):
    game_env.skill_tree.add_knowledge(20)
    game_env.module.render()
    status_text = game_env.elements["skill-mutual_aid_network-status"].innerText
    assert "requires" in status_text.lower()
    assert game_env.elements["skill-mutual_aid_network-unlock-button"].disabled


# ---------------------------------------------------------------------------
# E4: legacy system beyond the original single flavor-text line.
# ---------------------------------------------------------------------------
def test_legacy_event_counts_start_empty(game_env):
    assert game_env.module.legacy_event_counts == {}
    assert game_env.module.legacy_history_summary() == []


def test_legacy_event_counts_increment_on_run_completion(game_env):
    for _ in range(len(game_env.module.EVENT_SCHEDULE)):
        game_env.resolve_event()
    counts = game_env.module.legacy_event_counts
    assert counts["flood"] == 2  # flood appears twice in EVENT_SCHEDULE
    assert counts["heatwave"] == 1


def test_legacy_event_counts_accumulate_across_runs(game_env):
    for _ in range(len(game_env.module.EVENT_SCHEDULE)):
        game_env.resolve_event()
    game_env.start_new_run()
    for _ in range(len(game_env.module.EVENT_SCHEDULE)):
        game_env.resolve_event()
    assert game_env.module.legacy_event_counts["flood"] == 4


def test_legacy_history_summary_sorted_by_label_with_icons(game_env):
    for _ in range(len(game_env.module.EVENT_SCHEDULE)):
        game_env.resolve_event()
    summary = game_env.module.legacy_history_summary()
    labels = [entry["label"] for entry in summary]
    assert labels == sorted(labels)
    for entry in summary:
        assert entry["count"] > 0
        assert entry["icon"]


def test_render_populates_legacy_history_panel(game_env):
    for _ in range(len(game_env.module.EVENT_SCHEDULE)):
        game_env.resolve_event()
    game_env.module.render()
    assert len(game_env.elements["legacy-history-panel"].children) > 0


# ---------------------------------------------------------------------------
# E6: a third event category beyond weather/non-weather.
# ---------------------------------------------------------------------------
def test_civil_unrest_is_a_social_category_event(game_env):
    module = game_env.module
    assert "civil_unrest" in module.EVENT_SCHEDULE
    assert module.EVENT_CATEGORY["civil_unrest"] == "social"
    assert "civil_unrest" in module.EVENT_LABEL
    assert "civil_unrest" in module.EVENT_ICON
    assert "civil_unrest" in module.EVENT_BASE_DAMAGE


def test_schedule_front_and_length_unchanged_by_new_event(game_env):
    # Guards the balance-preserving choice of replacing a slot rather than
    # extending the schedule -- existing hope-angle tests are tuned to a
    # 7-event schedule.
    module = game_env.module
    assert len(module.EVENT_SCHEDULE) == 7
    assert module.EVENT_SCHEDULE[0] == "flood"
    assert module.EVENT_SCHEDULE[1] == "heatwave"
    assert module.EVENT_SCHEDULE[2] == "supply_chain"


# ---------------------------------------------------------------------------
# E7: reviewing a specific past run's event-by-event breakdown.
# ---------------------------------------------------------------------------
def test_run_log_history_starts_empty(game_env):
    assert game_env.module.run_log_history == []


def test_run_log_history_records_full_breakdown_on_completion(game_env):
    for _ in range(len(game_env.module.EVENT_SCHEDULE)):
        game_env.resolve_event()
    history = game_env.module.run_log_history
    assert len(history) == 1
    entry = history[0]
    assert entry["run_number"] == 1
    assert len(entry["event_log"]) == len(game_env.module.EVENT_SCHEDULE)
    assert entry["score"] == game_env.run.run_score()


def test_run_log_history_persists_to_local_storage(game_env):
    for _ in range(len(game_env.module.EVENT_SCHEDULE)):
        game_env.resolve_event()
    raw = game_env.local_storage.getItem(game_env.module.RUN_LOG_HISTORY_STORAGE_KEY)
    assert len(json.loads(raw)) == 1


def test_toggle_past_runs_shows_panel_with_run_cards(game_env):
    for _ in range(len(game_env.module.EVENT_SCHEDULE)):
        game_env.resolve_event()
    game_env.toggle_past_runs()
    assert not game_env.elements["past-runs-panel"].hidden
    assert len(game_env.elements["past-runs-panel"].children) == 1


def test_past_runs_panel_shows_placeholder_before_any_completion(game_env):
    game_env.toggle_past_runs()
    assert len(game_env.elements["past-runs-panel"].children) == 1  # the "no history yet" message


# ---------------------------------------------------------------------------
# E8/E16: expected-damage-this-event preview with numeric severity.
# ---------------------------------------------------------------------------
def test_expected_next_event_damage_matches_actual_resolution(game_env):
    module = game_env.module
    preview = module.expected_next_event_damage(game_env.run)
    assert preview is not None
    expected_damage, expected_severity = preview
    game_env.resolve_event()
    actual = game_env.run.event_log[-1]
    assert actual["severity"] == expected_severity
    assert round(actual["damage"], 6) == round(expected_damage, 6)


def test_expected_next_event_damage_none_once_run_complete(game_env):
    for _ in range(len(game_env.module.EVENT_SCHEDULE)):
        game_env.resolve_event()
    assert game_env.module.expected_next_event_damage(game_env.run) is None


def test_render_shows_expected_damage_line(game_env):
    game_env.module.render()
    text = game_env.elements["expected-damage-display"].innerText
    assert "Expected damage" in text
    assert "severity" in text


# ---------------------------------------------------------------------------
# E9: "X/Y skills unlocked" progress summary.
# ---------------------------------------------------------------------------
def test_skills_unlocked_display_updates(game_env):
    game_env.module.render()
    assert game_env.elements["skills-unlocked-display"].innerText == "0/7 skills unlocked"
    game_env.skill_tree.add_knowledge(20)
    game_env.unlock_skill("early_warning")
    assert game_env.elements["skills-unlocked-display"].innerText == "1/7 skills unlocked"


# ---------------------------------------------------------------------------
# E10: confirmation flash when an investment is spent.
# ---------------------------------------------------------------------------
def test_investing_resilience_flashes_resources_display(game_env):
    game_env.invest_resilience()
    assert "invest-flash" in game_env.elements["resources-display"].classList
    game_env.timers.flush()
    assert "invest-flash" not in game_env.elements["resources-display"].classList


def test_failed_investment_does_not_flash(game_env):
    game_env.run.resources = 0.0
    game_env.invest_resilience()
    assert "invest-flash" not in game_env.elements["resources-display"].classList


# ---------------------------------------------------------------------------
# E11: a proper end-of-run summary.
# ---------------------------------------------------------------------------
def test_run_summary_panel_hidden_mid_run(game_env):
    game_env.module.render()
    assert game_env.elements["run-summary-panel"].hidden


def test_run_summary_panel_populated_on_completion(game_env):
    for _ in range(len(game_env.module.EVENT_SCHEDULE)):
        game_env.resolve_event()
    panel = game_env.elements["run-summary-panel"]
    assert not panel.hidden
    # One stats line + one line per resolved event.
    assert len(panel.children) == 1 + len(game_env.module.EVENT_SCHEDULE)


# ---------------------------------------------------------------------------
# E12: export/import progress code.
# ---------------------------------------------------------------------------
def test_export_then_import_round_trips_skill_tree_and_history(game_env):
    game_env.skill_tree.add_knowledge(20)
    game_env.unlock_skill("early_warning")
    for _ in range(len(game_env.module.EVENT_SCHEDULE)):
        game_env.resolve_event()

    code = game_env.export_progress()
    assert code

    # A different, fresh module state should pick up the exported values.
    game_env.skill_tree.unlocked = set()
    game_env.skill_tree.knowledge_points = 0
    game_env.module.run_history.clear()

    assert game_env.module.import_progress_code(code) is True
    assert "early_warning" in game_env.module.skill_tree.unlocked
    assert len(game_env.module.run_history) == 1


def test_import_rejects_garbage_code(game_env):
    assert game_env.module.import_progress_code("not a real code") is False
    assert game_env.module.import_progress_code("") is False


def test_import_button_wires_up_status_message(game_env):
    code = game_env.export_progress()
    game_env.import_progress(code)
    assert "imported" in game_env.elements["progress-code-status"].innerText.lower()


def test_import_button_reports_failure_for_bad_paste(game_env):
    game_env.import_progress("garbage-not-base64!!")
    assert "couldn't" in game_env.elements["progress-code-status"].innerText.lower()


# ---------------------------------------------------------------------------
# E13: reset skill tree with an in-UI two-click confirmation.
# ---------------------------------------------------------------------------
def test_reset_skill_tree_requires_two_clicks(game_env):
    game_env.skill_tree.add_knowledge(20)
    game_env.unlock_skill("early_warning")
    assert game_env.skill_tree.knowledge_points == 15

    game_env.reset_skill_tree_click()  # first click just arms it
    assert game_env.skill_tree.unlocked == {"early_warning"}
    assert game_env.module.skill_tree_reset_pending is True

    game_env.reset_skill_tree_click()  # second click actually resets
    assert game_env.skill_tree.unlocked == set()
    assert game_env.skill_tree.knowledge_points == 20  # fully refunded
    assert game_env.module.skill_tree_reset_pending is False


def test_reset_skill_tree_pending_cleared_by_other_actions(game_env):
    game_env.skill_tree.add_knowledge(20)
    game_env.unlock_skill("early_warning")
    game_env.reset_skill_tree_click()
    assert game_env.module.skill_tree_reset_pending is True

    game_env.invest_resilience()
    assert game_env.module.skill_tree_reset_pending is False
    # A stray second click after the pending flag was cleared must not
    # reset -- it re-arms instead.
    game_env.reset_skill_tree_click()
    assert game_env.skill_tree.unlocked == {"early_warning"}


def test_reset_skill_tree_does_not_reduce_lifetime_knowledge(game_env):
    game_env.skill_tree.add_knowledge(20)
    game_env.unlock_skill("early_warning")
    game_env.reset_skill_tree_click()
    game_env.reset_skill_tree_click()
    assert game_env.skill_tree.lifetime_knowledge == 20


# ---------------------------------------------------------------------------
# E14: a prominent skill-unlock toast surfacing real-world grounding text.
# ---------------------------------------------------------------------------
def test_unlocking_a_skill_shows_its_grounding_text_in_a_toast(game_env):
    game_env.skill_tree.add_knowledge(20)
    game_env.unlock_skill("early_warning")
    toast = game_env.elements["skill-unlock-toast"]
    assert toast.hidden is False
    assert "Early Warning Systems" in game_env.elements["skill-unlock-toast-text"].innerText
    assert "early-warning networks" in game_env.elements["skill-unlock-toast-text"].innerText


def test_failed_unlock_attempt_does_not_show_toast(game_env):
    game_env.unlock_skill("early_warning")  # no knowledge points yet
    assert game_env.elements["skill-unlock-toast"].hidden is True


# ---------------------------------------------------------------------------
# E15: a settlement-art badge per unlocked skill.
# ---------------------------------------------------------------------------
def test_settlement_badge_toggles_on_unlock(game_env):
    game_env.module.render()
    assert "settlement-badge--earned" not in game_env.elements["settlement-badge-early_warning"].classList
    game_env.skill_tree.add_knowledge(20)
    game_env.unlock_skill("early_warning")
    assert "settlement-badge--earned" in game_env.elements["settlement-badge-early_warning"].classList
    # Unrelated skills stay unbadged.
    assert "settlement-badge--earned" not in game_env.elements["settlement-badge-adaptive_growth"].classList


# ---------------------------------------------------------------------------
# E17: "toughest run yet" comparison.
# ---------------------------------------------------------------------------
def test_toughest_run_yet_none_before_any_completion(game_env):
    assert game_env.module.toughest_run_yet() is None
    game_env.module.render()
    assert game_env.elements["toughest-run-display"].innerText == ""


def test_toughest_run_yet_identifies_lowest_scoring_run(game_env):
    game_env.module.run_history.extend([50.0, 5.0, 80.0])
    position, score = game_env.module.toughest_run_yet()
    assert score == 5.0
    assert position == 2
    game_env.module.render()
    assert "Toughest run yet" in game_env.elements["toughest-run-display"].innerText


# ---------------------------------------------------------------------------
# E18: optional extended-run mode.
# ---------------------------------------------------------------------------
def test_extended_run_doubles_schedule_length(game_env):
    module = game_env.module
    extended_run = module.RunState(run_number=1, extended=True)
    assert len(extended_run.schedule) == 2 * len(module.EVENT_SCHEDULE)
    assert not extended_run.is_complete()


def test_normal_run_defaults_to_non_extended(game_env):
    assert game_env.run.extended is False
    assert game_env.run.schedule is game_env.module.EVENT_SCHEDULE


def test_extended_run_toggle_checkbox_drives_start_new_run(game_env):
    for _ in range(len(game_env.module.EVENT_SCHEDULE)):
        game_env.resolve_event()
    game_env.elements["extended-run-toggle"].checked = True
    game_env.start_new_run()
    assert game_env.run.extended is True
    assert len(game_env.run.schedule) == 2 * len(game_env.module.EVENT_SCHEDULE)


def test_get_state_and_load_state_round_trip_extended_flag(game_env):
    module = game_env.module
    module.run = module.RunState(run_number=1, extended=True)
    data = module.get_state()
    assert data["extended"] is True

    module.run = module.RunState(run_number=1, extended=False)
    module.load_state(data)
    assert module.run.extended is True
    assert len(module.run.schedule) == 2 * len(module.EVENT_SCHEDULE)


def test_load_state_defaults_extended_to_false_for_old_save_codes(game_env):
    module = game_env.module
    data = module.get_state()
    del data["extended"]  # simulates a save code from before this field existed
    module.load_state(data)
    assert module.run.extended is False


# ---------------------------------------------------------------------------
# E19: distinct visual intensity per event severity.
# ---------------------------------------------------------------------------
def test_last_event_display_carries_a_severity_class(game_env):
    game_env.resolve_event()
    class_name = game_env.elements["last-event-display"].className
    assert "severity--" in class_name
    label = game_env.module.severity_label(game_env.run.event_log[-1]["severity"])
    assert f"severity--{label}" in class_name


def test_expected_damage_display_carries_a_severity_class(game_env):
    game_env.module.render()
    assert "severity--" in game_env.elements["expected-damage-display"].className


# ---------------------------------------------------------------------------
# E20: a live preview of the knowledge points a run will award.
# ---------------------------------------------------------------------------
def test_knowledge_preview_reflects_current_resources_mid_run(game_env):
    game_env.run.resources = 100.0
    game_env.module.render()
    text = game_env.elements["knowledge-preview-display"].innerText
    assert "5 knowledge points" in text  # 100 / 20


def test_knowledge_preview_cleared_once_run_complete(game_env):
    for _ in range(len(game_env.module.EVENT_SCHEDULE)):
        game_env.resolve_event()
    assert game_env.elements["knowledge-preview-display"].innerText == ""
