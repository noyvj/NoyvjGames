"""render(): redraws the whole page from the live game, calling every panel's own render function."""

from js import document

import thaw_runstate as runstate
from thaw_achievements import record_skin_unlocks, render_skins, update_achievements_display
from thaw_flavour import render_glossary, render_headline, render_mascots
from thaw_graphs import (
    _melt_status_label, _render_policy_stance, _render_rescue, _render_restoration, _render_trend,
    mini_temp_graph_svg, render_secondary_region, render_worst_case_region,
)
from thaw_mechanics import (
    _render_forecast, _render_framing, _render_long_game, render_carbon_bank, render_crate,
    render_shared_research,
)
from thaw_model import SECONDARY_REGIONS, deg, output_income_per_unit, region, region_b, region_c
from thaw_pace import _maybe_update_pace, ghost_sentence, pace_values, render_pace
from thaw_panels import (
    render_climate_scientist, render_info_page, update_changelog_display, update_community_compare_panel,
)
from thaw_presets import (
    _render_hard_mode, best_region_identifier, best_region_message, render_confirm_threshold,
)
from thaw_readouts import (
    accel_sparkline_svg, ice_age_text, render_balance, render_highlights, render_rate_inspector,
    render_routing, render_temp_unit, session_note_text,
)
from thaw_records import (
    _maybe_update_climate_archive, _maybe_update_personal_best, render_climate_archive,
    render_personal_best,
)
from thaw_rules import (
    CATEGORIES, CATEGORY_ICON, CATEGORY_LABEL, DAMPENING_PER_MONITOR_UNIT, DAMPENING_PER_PRESERVE_UNIT,
    INVEST_COST, SECOND_WARMING_MILESTONE, TEMPERATURE_METER_MAX,
)
from thaw_runs import render_field_notes, render_hold_line
from thaw_saveparts import render_load_notice
from thaw_savestate import render_history_readout
from thaw_sciencelog import render_science_log
from thaw_timeline import outlook_lines, render_planner, render_replay, render_undo
from thaw_views import render_board, render_focus


def render():
    runstate._roll_token += 1  # GG-19: whatever is written below is final; a roll in flight must not overwrite it
    render_info_page()
    document.getElementById("round-display").innerText = f"Round {region.round_number}"
    document.getElementById("session-note").innerText = session_note_text()
    document.getElementById("funds-display").innerText = f"Funds: {region.funds:.0f}"
    document.getElementById("temperature-display").innerText = (
        f"Global temperature: {deg(region.temperature, plus=True)}"
    )
    # G9: the temperature bar visually caps at TEMPERATURE_METER_MAX
    # (+30°) even though temperature itself keeps climbing past it —
    # without this note a maxed-out bar reads as "capped for real,"
    # which understates how far past +30° a long, unmanaged session can
    # actually reach.
    cap_note_el = document.getElementById("temperature-cap-note")
    if region.temperature > TEMPERATURE_METER_MAX:
        cap_note_el.innerText = (
            f"(meter shown capped at {deg(TEMPERATURE_METER_MAX, 0, plus=True)} — actual temperature is "
            f"{deg(region.temperature, plus=True)})"
        )
        cap_note_el.hidden = False
    else:
        cap_note_el.hidden = True
    _render_trend("temperature-trend", region)
    _render_rescue("", region)
    _render_restoration("", region)
    _render_policy_stance()
    _render_forecast()
    _render_framing()
    _render_long_game()
    render_shared_research()
    render_carbon_bank()
    render_crate()
    render_routing()
    render_balance()
    render_rate_inspector()
    render_highlights()
    render_hold_line()
    render_field_notes()
    render_temp_unit()
    _render_hard_mode()
    render_confirm_threshold()
    document.getElementById("rise-rate-display").innerText = (
        f"Current warming rate: {deg(region.current_rise_rate(), 2)}/round"
    )
    melt_status_el = document.getElementById("melt-status-display")
    status = _melt_status_label(region)
    if status == "critical":
        melt_status_el.innerText = (
            "Permafrost melt has reached a critical, fast-compounding pace — the feedback "
            "loop is running away."
        )
    elif status == "melting":
        melt_status_el.innerText = (
            "Permafrost is actively melting — methane feedback is accelerating warming."
        )
    else:
        melt_status_el.innerText = "Permafrost stable — no feedback yet."
    status_suffix = {
        "stable": "",
        "melting": " melt-status--active",
        "critical": " melt-status--critical",
    }[status]
    melt_status_el.className = "comparison-message" + status_suffix

    game_el = document.getElementById("game")
    if region.just_started_melting:
        game_el.className = "tipping-flash"
        region.just_started_melting = False
    else:
        game_el.className = ""

    # G10: the one-tick "intervention delayed a further warming
    # milestone" callout — a separate banner from the tipping-flash
    # above, since it can fire many rounds after melt already started.
    milestone_delay_el = document.getElementById("milestone-delay-callout")
    if region.just_delayed_milestone:
        milestone_delay_el.innerText = (
            f"Your preservation & monitoring investments just delayed reaching "
            f"{deg(SECOND_WARMING_MILESTONE, 0, plus=True)} warming — the unmitigated counterfactual has "
            f"already passed it."
        )
        milestone_delay_el.hidden = False
        region.just_delayed_milestone = False
    else:
        milestone_delay_el.hidden = True

    # G12: one-time praise the round melt begins with protection already
    # in place -- can only ever fire once per region (melt starts once).
    preempt_el = document.getElementById("preemptive-callout")
    if region.just_preempted_melt:
        preempt_el.innerText = (
            f"Well done: {(region.dampening_at_melt_start or 0) * 100:.0f}% feedback dampening was "
            "already in place before melt began. Pre-emptive investment is the strongest "
            "lever there is."
        )
        preempt_el.hidden = False
        region.just_preempted_melt = False
    else:
        preempt_el.hidden = True

    # GG-20: "phew" -- an investment (or rescue) just pulled a region back from
    # a projected critical tier next round.
    phew_el = document.getElementById("phew-callout")
    pulled = [label for label, r in (("A", region), ("B", region_b), ("C", region_c)) if r.just_pulled_back]
    for _label, r in (("A", region), ("B", region_b), ("C", region_c)):
        r.just_pulled_back = False
    if pulled:
        phew_el.innerText = (
            f"Phew: without that last move Region {', '.join(pulled)} was on course to go critical "
            f"next round. It isn't now."
        )
        phew_el.hidden = False
    else:
        phew_el.hidden = True

    # G28: stability streak.
    streak_el = document.getElementById("tipping-streak-display")
    if region.tipping_events == 0:
        streak_el.innerText = (
            f"No tipping event yet: {region.rounds_since_tipping_event} rounds stable."
        )
    else:
        streak_el.innerText = (
            f"{region.rounds_since_tipping_event} rounds since the last tipping event "
            f"({region.tipping_events} so far)."
        )

    dampening_el = document.getElementById("dampening-display")
    dampening_el.innerText = f"Feedback dampening: {region.feedback_dampening_fraction() * 100:.0f}%"
    if region.just_invested_intervention:
        dampening_el.className = "status-line dampening-flash"
        region.just_invested_intervention = False
    else:
        dampening_el.className = "status-line"
    document.getElementById("intervention-feedback-display").innerText = (
        region.intervention_feedback_message()
    )
    acceleration_el = document.getElementById("acceleration-display")
    acceleration_el.innerText = region.acceleration_message()
    # G24: a brief pulse the instant the region crosses into the critical tier.
    if region.just_became_critical:
        acceleration_el.className = "comparison-message acceleration-pulse"
        region.just_became_critical = False
    else:
        acceleration_el.className = "comparison-message"
    document.getElementById("acceleration-bar").style.width = (
        f"{min(1.0, (region.acceleration_factor() - 1) / 2) * 100:.0f}%"
    )
    document.getElementById("trajectory-display").innerText = region.trajectory_message()

    document.getElementById("temperature-bar").style.width = (
        f"{min(1.0, region.temperature / TEMPERATURE_METER_MAX) * 100:.0f}%"
    )
    document.getElementById("graph").innerHTML = mini_temp_graph_svg(
        region.temperature_history, "Region A", region.dampening_history,
        pace=pace_values(len(region.temperature_history)), ghost_note=ghost_sentence(),
    )
    document.getElementById("acceleration-sparkline").innerHTML = accel_sparkline_svg(region.acceleration_history)
    document.getElementById("ice-age-display").innerText = ice_age_text(region)

    for category in CATEGORIES:
        document.getElementById(f"{category}-name").innerText = (
            f"{CATEGORY_ICON[category]} {CATEGORY_LABEL[category]}"
        )
        document.getElementById(f"{category}-count").innerText = str(region.capacity[category])
        invest_button = document.getElementById(f"{category}-invest-button")
        invest_button.innerText = f"Invest ({INVEST_COST[category]})"
        invest_button.disabled = region.funds < INVEST_COST[category]

    # G12: a small inline forecast of each investment's effect, so a
    # player can see what a click would do before making it rather than
    # inferring it from the constants tables in How to Play.
    # GG-23: hard mode hides these previews.
    document.getElementById("output-forecast").innerText = (
        "" if runstate.hard_mode else f"+{output_income_per_unit():g} funds/round"
    )
    document.getElementById("preserve-forecast").innerText = (
        "" if runstate.hard_mode else f"+{DAMPENING_PER_PRESERVE_UNIT * 100:.0f}% dampening"
    )
    document.getElementById("monitor-forecast").innerText = (
        "" if runstate.hard_mode else f"+{DAMPENING_PER_MONITOR_UNIT * 100:.0f}% dampening"
    )

    for prefix, r in SECONDARY_REGIONS.items():
        render_secondary_region(prefix, r)

    worst_case_panel = document.getElementById("worst-case-panel")
    worst_case_panel.hidden = not runstate.worst_case_region_revealed
    if runstate.worst_case_region_revealed:
        render_worst_case_region()
    worst_case_toggle = document.getElementById("worst-case-toggle-button")
    worst_case_toggle.innerText = (
        "Hide the worst-case region" if runstate.worst_case_region_revealed else "Reveal a worst-case region"
    )
    # G4: explain "worst case" before the player reveals it.
    worst_case_toggle.title = (
        "Region D is a fully automated stand-in for pure neglect: every round it spends "
        "everything on Output and never invests in Preservation or Monitoring. It shows "
        "what warming looks like if nobody intervenes."
    )
    # G30: first-reveal-only note that D needs no input.
    document.getElementById("d-intro-note").hidden = not (
        runstate.worst_case_region_revealed and not runstate.worst_case_intro_seen
    )

    # G19: scientist's log.
    render_science_log()

    # G2: an explicit "which region did best" comparison line, always
    # visible (not gated on an end-of-session state, since this game has
    # none) rather than only inferable by eyeballing three separate cards.
    document.getElementById("region-comparison-best-display").innerText = best_region_message()
    # G15: a hidden, machine-readable echo of the same comparison for the
    # plain-JS feedback-submission script below to fold into its rating
    # payload as an aggregate stat.
    document.getElementById("best-region-hidden").innerText = best_region_identifier()

    # G17: a next-round forecast, available as a hover tooltip on Advance
    # Round rather than a permanent line, since it's a "before you click"
    # preview rather than information about the current state.
    # G10: one combined tooltip covering all three managed regions, each
    # with its projected temperature after the coming round.
    if runstate.hard_mode:  # GG-23: no preview at all
        document.getElementById("advance-round-button").title = "Hard mode: no preview of the next round."
    else:
        document.getElementById("advance-round-button").title = "\n".join(
            ["Next round preview"]
            + [
                f"Region {label}: {deg(r.current_rise_rate(), 2, plus=True)} "
                f"(to {deg(r.temperature + r.current_rise_rate(), plus=True)})"
                for label, r in (("A", region), ("B", region_b), ("C", region_c))
            ]
            + [outlook_lines()]  # G-5: the 10-round outlook beside the next-round numbers
        )

    _maybe_update_personal_best()
    _maybe_update_climate_archive()
    _maybe_update_pace()
    render_pace()
    render_mascots()
    render_board()  # after the archive update so "best saved" is current
    render_focus()
    render_planner()
    render_load_notice()
    render_glossary()
    render_headline()
    render_replay()
    render_undo()
    render_personal_best()
    render_climate_archive()
    update_achievements_display()
    update_changelog_display()
    update_community_compare_panel()
    render_climate_scientist()
    render_history_readout()
    record_skin_unlocks()  # GG-18
    render_skins()
