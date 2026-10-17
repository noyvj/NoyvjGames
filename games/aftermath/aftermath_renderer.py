"""render(): redraws the whole page from the live game, calling every panel's own render function."""

from js import document

import aftermath_runstate as runstate
from aftermath_achievements import (
    legacy_message, progress_comparison, progress_message, societal_memory_message,
    update_achievements_display,
)
from aftermath_bonuses import entry_aid, growth_income_now, render_neighbour_aid
from aftermath_challenges import challenge_result_text, render_builder, render_challenge, render_ghost
from aftermath_chronicle import render_chronicle, render_founding
from aftermath_codex import (
    INVEST_STEPS, growth_step_label, render_codex_panel, render_stats_panel, resilience_button_label,
    set_invest_step,
)
from aftermath_flourish import (
    render_achievement_strip, render_dock_resources, render_hit_number, render_mood_strip,
    render_settlement_look,
)
from aftermath_panels import (
    _flash_element, extended_epilogue_text, generational_memory_text, render_info_page, render_real_world,
    update_changelog_display,
)
from aftermath_pastruns import (
    _eta_text, _render_event_breakdown_lines, expected_damage_range, expected_next_event_damage,
    legacy_history_summary, legacy_scar_tiers, pinned_skills_text, render_mentor, render_past_runs_panel,
    runs_completed_text, severity_tooltip_text, streak_text, toughest_badge_title, toughest_run_text,
    toughest_run_yet, toughest_survived_run_badge_earned,
)
from aftermath_persist import curriculum_message
from aftermath_rules import (
    EVENT_CATEGORY, EVENT_ICON, EVENT_LABEL, EVENT_SCHEDULE, SCENARIOS, SKILLS, adjusted_text,
    severity_label,
)
from aftermath_runview import (
    epitaph_hidden, epitaph_text, flawless_hint_text, knowledge_breakdown_lines, knowledge_preview_detail,
    render_damage_popup, render_damage_waterfall, render_run_timer, render_schedule_strip, skill_helps_text,
    update_tab_title,
)
from aftermath_skillmap import (
    render_skill_map, render_skill_move, render_skill_ranks, skill_rank_callout_text,
)
from aftermath_tools import (
    render_presets, render_route_planner, render_save_health, render_schedule_text, render_skill_filters,
)


# ---- GE-18 / E-15 handlers ---------------------------------------------


def _make_step_handler(step):
    def handler(event=None):
        set_invest_step(step)
        render()
    return handler


def render():
    render_info_page()
    update_achievements_display()
    render_achievement_strip()  # E-31
    render_past_runs_panel()
    render_codex_panel()
    render_stats_panel()
    render_damage_popup()
    update_tab_title()
    update_changelog_display()
    document.getElementById("legacy-display").innerText = legacy_message()
    document.getElementById("societal-memory-display").innerText = societal_memory_message()
    render_mentor()
    render_ghost()  # Z-3d
    render_real_world()
    render_schedule_strip()
    render_schedule_text()  # E-5
    render_damage_waterfall()
    render_skill_filters()  # E-19
    render_presets()  # E-25
    render_route_planner()  # E-3
    render_builder()  # E-13
    render_skill_move()  # AN-13
    render_skill_ranks()  # E-11
    render_skill_map()  # E-2 / GE-16
    render_founding()  # GE-10
    render_mood_strip()  # GE-20
    render_settlement_look()  # GE-25
    render_hit_number()  # GE-14
    render_run_timer()  # GE-23
    render_dock_resources()  # E-26
    render_chronicle()  # E-7
    render_challenge()  # E-4
    document.getElementById("curriculum-display").innerText = curriculum_message()
    document.getElementById("resources-display").innerText = f"Resources: {runstate.run.resources:.0f}"
    document.getElementById("resilience-display").innerText = f"Resilience: {runstate.run.resilience_capacity}"
    document.getElementById("growth-display").innerText = (
        f"Growth: {runstate.run.growth_capacity} (+{growth_income_now(runstate.run.growth_capacity)} resources/event)"
    )
    document.getElementById("runs-completed-display").innerText = runs_completed_text()  # E4/E25
    document.getElementById("settlement-badge-toughest").classList.remove("settlement-badge--earned")
    badge = document.getElementById("settlement-badge-toughest")
    badge.title = toughest_badge_title()  # E-9
    if toughest_survived_run_badge_earned():  # E12
        badge.classList.add("settlement-badge--earned")
    callout_el = document.getElementById("callout-display")
    callout_el.innerText = runstate.callout_message
    callout_el.hidden = not runstate.callout_message
    memory_el = document.getElementById("generational-memory-display")
    memory_text = generational_memory_text(runstate.run)
    memory_el.innerText = memory_text
    memory_el.hidden = not memory_text
    document.getElementById("extended-run-toggle-label").innerText = (
        f"Extended Run ({len(EVENT_SCHEDULE) * 2} events instead of {len(EVENT_SCHEDULE)})"  # E6
    )

    # E4: legacy-history chips (additive to the legacy-display flavor line
    # above).
    history_panel = document.getElementById("legacy-history-panel")
    history_panel.innerHTML = ""
    for entry in legacy_history_summary():
        chip = document.createElement("span")
        chip.className = "legacy-history-chip"
        chip.innerText = f"{entry['icon']} {entry['label']} ×{entry['count']}"
        history_panel.appendChild(chip)

    # V-CD-6: legacy weathering scars -- one CSS tier class per category,
    # driven by the same legacy_event_counts as the chip row above.
    for category, tier in legacy_scar_tiers().items():
        scar_el = document.getElementById(f"settlement-legacy-scar-{category}")
        if scar_el is None:
            continue  # a cached older page without this category's scar (service worker serves stale HTML once)
        for t in (1, 2, 3):
            scar_el.classList.remove(f"settlement-legacy-scar--tier-{t}")
        if tier:
            scar_el.classList.add(f"settlement-legacy-scar--tier-{tier}")

    run_summary_panel = document.getElementById("run-summary-panel")

    if runstate.run.is_complete():
        document.getElementById("progress-display").innerText = "Run complete"
        document.getElementById("next-event-display").innerText = "No more events this run."
        document.getElementById("expected-damage-display").innerText = ""
        document.getElementById("flawless-hint-display").innerText = ""
        document.getElementById("knowledge-preview-display").innerText = ""
        document.getElementById("run-summary-display").innerText = (
            challenge_result_text(runstate.run) if runstate.run.normalised else
            f"Score: {runstate.run.run_score():.0f} — "
            f"earned {runstate.run.knowledge_points_earned()} resilience knowledge point"
            f"{'s' if runstate.run.knowledge_points_earned() != 1 else ''}."
        )
        # E11: a proper end-of-run summary -- final stats plus the exact
        # event-by-event breakdown, not just the one-line score above.
        run_summary_panel.hidden = False
        run_summary_panel.innerHTML = ""
        stats = document.createElement("p")
        stats.className = "run-summary-stats"
        stats.innerText = (
            f"Final resilience: {runstate.run.resilience_capacity} · Final growth: {runstate.run.growth_capacity} · "
            f"Total damage taken: {runstate.run.damage_taken:.0f} · Score {runstate.run.run_score():.0f}, "
            f"{adjusted_text(runstate.run.run_score(), runstate.run.event_log)}"  # E-9
        )
        run_summary_panel.appendChild(stats)
        _render_event_breakdown_lines(run_summary_panel, runstate.run.event_log)
        # E-23: where the knowledge points came from.
        breakdown = document.createElement("div")
        breakdown.className = "knowledge-breakdown"
        breakdown_heading = document.createElement("p")
        breakdown_heading.className = "knowledge-breakdown-heading"
        breakdown_heading.innerText = "Knowledge earned this run"
        breakdown.appendChild(breakdown_heading)
        for text in knowledge_breakdown_lines(runstate.run):
            line = document.createElement("p")
            line.className = "knowledge-breakdown-line"
            line.innerText = text
            breakdown.appendChild(line)
        if not runstate.run.normalised:  # E-4: a challenge run earns no knowledge, so no breakdown
            run_summary_panel.appendChild(breakdown)
        rank_text = skill_rank_callout_text() if not runstate.run.normalised else ""  # E-11
        if rank_text:
            rank_el = document.createElement("p")
            rank_el.className = "skill-rank-callout"
            rank_el.innerText = "\u2b50 " + rank_text
            run_summary_panel.appendChild(rank_el)
        if not runstate.run.normalised and not epitaph_hidden():  # GE-21
            epitaph_el = document.createElement("p")
            epitaph_el.className = "run-epitaph"
            epitaph_el.innerText = epitaph_text(runstate.run)
            run_summary_panel.appendChild(epitaph_el)
        epilogue = extended_epilogue_text(runstate.run) if not runstate.run.normalised else ""
        if epilogue:
            epilogue_el = document.createElement("p")
            epilogue_el.className = "run-epilogue"
            epilogue_el.innerText = epilogue
            run_summary_panel.appendChild(epilogue_el)
    else:
        document.getElementById("run-summary-display").innerText = ""
        run_summary_panel.hidden = True
        run_summary_panel.innerHTML = ""
        document.getElementById("progress-display").innerText = (
            f"Event {runstate.run.event_index + 1} of {len(runstate.run.schedule)}"
        )
        next_type = runstate.run.next_event_type()
        next_event_el = document.getElementById("next-event-display")
        next_event_el.innerText = f"Next: {EVENT_ICON[next_type]} {EVENT_LABEL[next_type]}"
        next_event_el.className = f"status-line event-category--{EVENT_CATEGORY[next_type]}"

        # E8/E16: expected-damage-this-event preview, numeric severity band.
        damage, severity = expected_next_event_damage(runstate.run)
        expected_el = document.getElementById("expected-damage-display")
        low, high = expected_damage_range(runstate.run)
        expected_el.innerText = (
            f"Expected damage: ~{damage:.0f} ({severity:.2f}× severity, {severity_label(severity)}; "
            f"range {low:.0f}–{high:.0f})"
        )
        expected_el.className = f"status-line severity--{severity_label(severity)}"
        expected_el.title = (
            "Challenge runs use a fixed severity pattern shared with the friend who made the code."
            if runstate.run.normalised else severity_tooltip_text(runstate.run.run_number)
        )
        document.getElementById("flawless-hint-display").innerText = flawless_hint_text(runstate.run)  # GE-15

        # E20: a live preview of the knowledge points a run would award
        # if it ended right now.
        knowledge_now = runstate.run.knowledge_points_earned()
        preview_el = document.getElementById("knowledge-preview-display")
        preview_el.innerText = (
            "Challenge runs earn no knowledge points." if runstate.run.normalised else
            f"If the run ended now: {knowledge_now} knowledge point{'s' if knowledge_now != 1 else ''}"
            + knowledge_preview_detail(runstate.run)  # E-23
        )
        if runstate.last_knowledge_preview is not None and knowledge_now > runstate.last_knowledge_preview:
            _flash_element("knowledge-preview-display", 900, "knowledge-bump")  # E18
        runstate.last_knowledge_preview = knowledge_now

    render_neighbour_aid()  # R-31
    last_event_el = document.getElementById("last-event-display")
    if runstate.run.event_log:
        last = runstate.run.event_log[-1]
        last_event_el.innerText = (
            f"Last: {EVENT_ICON[last['type']]} {EVENT_LABEL[last['type']]} "
            f"— {last['damage']:.0f} damage ({severity_label(last['severity'])} intensity)"
            + (f" · neighbours sent +{entry_aid(last):.0f}" if entry_aid(last) else "")  # R-31
        )
        # E19: distinct visual intensity per event severity, alongside the
        # pre-existing weather/non-weather/social category class.
        last_event_el.className = (
            f"status-line event-category--{EVENT_CATEGORY[last['type']]} "
            f"severity--{severity_label(last['severity'])}"
        )
    else:
        last_event_el.innerText = ""
        last_event_el.className = "status-line"

    document.getElementById("mitigation-bar").style.width = f"{runstate.run.mitigation_fraction() * 100:.0f}%"

    resilience_button = document.getElementById("resilience-invest-button")
    resilience_button.innerText = resilience_button_label(runstate.run, runstate.invest_step)
    resilience_button.disabled = runstate.run.is_complete() or runstate.run.step_units("resilience", runstate.invest_step) < 1

    growth_button = document.getElementById("growth-invest-button")
    growth_button.innerText = growth_step_label(runstate.run, runstate.invest_step)
    growth_button.disabled = runstate.run.is_complete() or runstate.run.step_units("growth", runstate.invest_step) < 1

    for step in INVEST_STEPS:  # E-15
        step_button = document.getElementById(f"step-{'max' if step == 'max' else 'x' + str(step)}-button")
        step_button.setAttribute("aria-pressed", "true" if step == runstate.invest_step else "false")
        if step == runstate.invest_step:
            step_button.classList.add("selected")
        else:
            step_button.classList.remove("selected")
    undo_button = document.getElementById("undo-allocation-button")  # GE-18
    undo_button.innerText = f"↶ Undo ({runstate.run.undo_count()})"
    undo_button.disabled = runstate.run.undo_count() < 1 or runstate.run.is_complete()

    # E-24: the copy button is available once an event has been faced.
    document.getElementById("run-summary-actions").hidden = not runstate.run.event_log

    resolve_button = document.getElementById("resolve-event-button")
    resolve_button.disabled = runstate.run.is_complete()

    document.getElementById("new-run-button").hidden = not runstate.run.is_complete()
    render_save_health()  # E-30
    document.getElementById("extended-run-toggle-wrapper").hidden = not runstate.run.is_complete()
    # E17a: the scenario can be picked before a run's first event or between runs.
    document.getElementById("scenario-wrapper").hidden = (
        not (runstate.run.is_complete() or runstate.run.event_index == 0) or (runstate.run.normalised and not runstate.run.is_complete())
    )
    scenario_select = document.getElementById("scenario-select")
    if runstate.run.event_index == 0 and not runstate.run.is_complete():
        scenario_select.value = runstate.run.scenario
    document.getElementById("scenario-blurb").innerText = (
        f"Custom schedule: {runstate.run.custom_name or 'built by you'} ({len(runstate.run.schedule)} events)." if (runstate.run.custom_events and not runstate.run.is_complete())
        else SCENARIOS[scenario_select.value if scenario_select.value in SCENARIOS else runstate.run.scenario]["blurb"]
    )
    document.getElementById("progress-comparison-display").innerText = progress_message(
        progress_comparison()
    )

    streak_el = document.getElementById("improvement-streak-display")  # GE-22
    if streak_el is not None:
        streak_el.innerText = streak_text()
        streak_el.hidden = not streak_el.innerText

    # E17: toughest run yet.
    toughest = toughest_run_yet()
    toughest_el = document.getElementById("toughest-run-display")
    toughest_el.innerText = toughest_run_text() if toughest else ""

    document.getElementById("knowledge-points-display").innerText = (
        f"Resilience knowledge: {runstate.skill_tree.knowledge_points}"
    )

    # E9: visible "X/Y skills unlocked" progress summary.
    document.getElementById("skills-unlocked-display").innerText = (
        f"{len(runstate.skill_tree.unlocked)}/{len(SKILLS)} skills unlocked"
    )

    # E13: reset-skill-tree button (Z22: gated behind the shared
    # ConfirmDialog, which itself states the refund amount in its message
    # -- see on_reset_skill_tree()).
    reset_button = document.getElementById("reset-skill-tree-button")
    reset_button.disabled = not runstate.skill_tree.unlocked

    document.getElementById("pinned-skills-display").innerText = pinned_skills_text()  # E30b
    for skill_id, skill in SKILLS.items():
        eta_el = document.getElementById(f"skill-{skill_id}-eta")
        pin_button = document.getElementById(f"skill-{skill_id}-pin-button")
        if skill_id in runstate.skill_tree.unlocked:
            eta_el.innerText = ""
            pin_button.hidden = True
        else:
            eta_el.innerText = ("Now available. " if runstate.skill_map_reveal and skill_id in runstate.skill_map_reveal["children"] else "") + _eta_text(skill_id)  # E30a / GE-16
            pin_button.hidden = False
            pinned = skill_id in runstate.meta["pinned_skills"]
            pin_button.innerText = "📌 Pinned" if pinned else "📍 Pin"
            pin_button.title = "Unpin this skill" if pinned else "Pin this skill to track how many runs until you can afford it"
        status_el = document.getElementById(f"skill-{skill_id}-status")
        practice_el = document.getElementById(f"skill-{skill_id}-practice")
        unlock_button = document.getElementById(f"skill-{skill_id}-unlock-button")
        practice_el.innerText = skill["real_practice"]
        helps_el = document.getElementById(f"skill-{skill_id}-helps")  # E-29
        if helps_el is not None:
            helps_el.innerText = skill_helps_text(skill_id)

        # E15: a settlement-art badge per unlocked skill.
        badge = document.getElementById(f"settlement-badge-{skill_id}")
        if skill_id in runstate.skill_tree.unlocked:
            badge.classList.add("settlement-badge--earned")
        else:
            badge.classList.remove("settlement-badge--earned")

        if skill_id in runstate.skill_tree.unlocked:
            status_el.innerText = f"{skill['label']} — unlocked ({skill['description']})"
            unlock_button.hidden = True
        else:
            missing = runstate.skill_tree.missing_prereqs(skill_id)
            if missing:
                # E3: branching/prerequisite structure -- tell the player
                # what's still locking this skill rather than just
                # disabling the button with no explanation.
                required = ", ".join(SKILLS[prereq]["label"] for prereq in missing)
                status_el.innerText = f"{skill['label']} — {skill['description']} (requires {required})"
                unlock_button.hidden = False
                unlock_button.innerText = f"Unlock ({skill['cost']})"
                unlock_button.disabled = True
            else:
                status_el.innerText = f"{skill['label']} — {skill['description']}"
                unlock_button.hidden = False
                unlock_button.innerText = f"Unlock ({skill['cost']})"
                unlock_button.disabled = not runstate.skill_tree.can_unlock(skill_id)


# Late binding: aftermath_tools calls render() but comes earlier in the module list, so it gets it from here.
import aftermath_tools
aftermath_tools.render = render


# Late binding: aftermath_challenges calls render() but comes earlier in the module list, so it gets it from here.
import aftermath_challenges
aftermath_challenges.render = render


# Late binding: aftermath_skillmap calls render() but comes earlier in the module list, so it gets it from here.
import aftermath_skillmap
aftermath_skillmap.render = render
