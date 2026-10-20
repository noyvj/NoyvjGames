"""render(): redraws the whole page from the live region, calling every panel's own render function."""

from js import document

import drift_runstate as runstate
from drift_achievements import _ever_reached_critical_strain, update_achievements_display
from drift_collection import render_collection_summary, render_skins
from drift_ledger import render_ledger
from drift_loading import render_load_note
from drift_messages import (
    ARRIVAL_STREAM_MAX_DOTS, CONTROL_REGION_TOOLTIP, SEVERITY_DENSITY_CALLOUT_TEXT, _render_coda_comparison,
    _simulate_control_region, arrival_stream_animation_duration, arrival_stream_dot_count,
    capacity_milestone_message, checkpoint_message, coda_control_message, coda_legacy_message,
    control_region_contrast_message, economic_health_reference_note, forecast_message,
    integration_turning_point_message, long_horizon_coda_message, maybe_flag_severity_density_change,
    net_positive_badge_text, recovery_badge_text, resettlement_benchmark_message, roi_message,
    session_milestone_message, strain_consequence_tooltip, thriving_callout_message,
    thriving_vignette_message, uganda_comparison_message, wellbeing_message,
)
from drift_model_region import region
from drift_newsview import news_headline, render_trend_graph, tab_title
from drift_pages import (
    _maybe_record_learning, _maybe_update_personal_best, render_info_page, render_learning,
    render_personal_best, render_real_world,
)
from drift_plans import render_civic_tools
from drift_regional import _sync_spillover, render_neighbor, render_policies, render_second_wave
from drift_report import render_batch3
from drift_rules import (
    ACCELERATED_SEVERITY_MULTIPLIER, CAPACITY_EFFECT_SUMMARY, CAPACITY_ICON, CAPACITY_LABEL, CAPACITY_TYPES,
    INVEST_COST, REALLOCATION_FUNDS_COST, REALLOCATION_LOSS_FRACTION, REALLOCATION_UNITS,
    THRIVING_WELLBEING_SCORE, subscore_arrow, subscore_sparkline,
)
from drift_tiers import _maybe_update_tier_best
from drift_trendgraph import wellbeing_band
from drift_undo import render_round_tools
from drift_visuals import (
    REGION_VISUAL_BUILDING_IDS, _pulse, region_visual_building_count, region_visual_height_scale,
    render_pending_pipeline, scaled_seconds, strain_consequence_message, strain_heartbeat_seconds,
)


def render():
    runstate.rewind_armed = False  # any other action cancels a half-confirmed rewind
    _sync_spillover()
    render_info_page()
    render_neighbor()
    render_policies()
    render_second_wave()
    render_real_world()
    _maybe_record_learning()
    render_learning()
    update_achievements_display()
    _maybe_update_personal_best()
    _maybe_update_tier_best()  # I-25
    render_personal_best()
    document.getElementById("round-display").innerText = f"Round {region.round_number}"
    document.getElementById("funds-display").innerText = f"Funds: {region.funds:.0f}"
    document.getElementById("total-capacity-display").innerText = (
        f"Total capacity: {region.total_capacity():.0f}"
    )
    # I19: persistent net-positive badge in the top status readouts.
    net_positive_badge = document.getElementById("net-positive-badge")
    badge_text = net_positive_badge_text(region)
    net_positive_badge.hidden = badge_text is None
    net_positive_badge.innerText = badge_text or ""

    document.getElementById("arrivals-display").innerText = (
        f"Arrivals this round: {region.arrivals_this_round():.0f} people "
        f"(background severity: {region.background_severity:.1f})"
    )
    # I16: arrival-dot stream density/speed tracking real arrivals.
    arrivals_now = region.arrivals_this_round()
    visible_dot_count = arrival_stream_dot_count(arrivals_now)
    dot_duration = arrival_stream_animation_duration(arrivals_now)
    for dot_index in range(1, ARRIVAL_STREAM_MAX_DOTS + 1):
        dot_el = document.getElementById(f"arrival-dot-{dot_index}")
        dot_el.hidden = dot_index > visible_dot_count
        dot_el.style.animationDuration = scaled_seconds(dot_duration)
    # I20: one-time callout once the stream's density has genuinely moved
    # since the severity toggle was first switched on.
    maybe_flag_severity_density_change(region, visible_dot_count)
    density_callout = document.getElementById("severity-density-callout")
    density_callout.hidden = not region.severity_density_callout_shown
    if region.severity_density_callout_shown:
        density_callout.innerText = SEVERITY_DENSITY_CALLOUT_TEXT
    document.getElementById("total-arrivals-display").innerText = (
        f"Total arrivals (lifetime): {region.total_arrivals:.0f} people"
    )
    document.getElementById("strain-display").innerText = (
        f"Strain: {region.strain_fraction() * 100:.0f}% ({region.strain_level()})"
    )
    strain_bar = document.getElementById("strain-bar")
    strain_bar.style.width = f"{region.strain_fraction() * 100:.0f}%"
    strain_bar.className = f"meter-fill meter-fill--strain strain-heartbeat strain--{region.strain_level()}"
    # GI-19: the readout and its bar pulse at a beat that follows the strain level.
    heartbeat = scaled_seconds(strain_heartbeat_seconds(region.strain_level()))
    strain_bar.style.animationDuration = heartbeat
    strain_display = document.getElementById("strain-display")
    strain_display.className = "status-line strain-heartbeat-text"
    strain_display.style.animationDuration = heartbeat
    # I6: one-line consequence description per strain level.
    document.getElementById("strain-consequence-display").innerText = strain_consequence_message(region)

    document.getElementById("integrated-display").innerText = (
        f"Integrated: {region.integrated_population:.0f} people "
        f"(contributing {region.integration_contribution():.0f} funds/round)"
    )
    document.getElementById("pending-display").innerText = (
        f"Pending integration: {region.pending_population():.0f} people"
    )
    render_pending_pipeline()
    turning_point_display = document.getElementById("integration-turning-point-display")
    turning_point_message = integration_turning_point_message(region)
    turning_point_display.hidden = turning_point_message is None
    turning_point_display.innerText = turning_point_message or ""

    # I3: explicit in-play comparison to the Uganda policy model.
    document.getElementById("uganda-comparison-display").innerText = uganda_comparison_message(region)
    # I9: real-world resettlement-outcome benchmark comparison.
    document.getElementById("resettlement-benchmark-display").innerText = resettlement_benchmark_message(
        region
    )

    document.getElementById("service-quality-display").innerText = (
        f"Service quality: {region.service_quality():.0f}"
    )
    document.getElementById("service-quality-bar").style.width = f"{region.service_quality():.0f}%"
    document.getElementById("economic-health-display").innerText = (
        f"Economic health: {region.economic_health():.0f}"
    )
    document.getElementById("economic-health-bar").style.width = f"{region.economic_health():.0f}%"
    # I20: economic health's funds-to-score scale reference point.
    document.getElementById("economic-health-reference-display").innerText = economic_health_reference_note()
    document.getElementById("social-cohesion-display").innerText = (
        f"Social cohesion: {region.social_cohesion():.0f}"
    )
    document.getElementById("social-cohesion-bar").style.width = f"{region.social_cohesion():.0f}%"
    document.getElementById("wellbeing-display").innerText = (
        f"Wellbeing score: {region.wellbeing_score():.0f}"
    )
    # I-22: short sources for the phone's sticky bar: round and funds (the coin stands for funds), strain, wellbeing with its band name.
    document.getElementById("hud-round-display").innerText = f"R{region.round_number} 💰 {region.funds:.0f}"
    document.getElementById("hud-strain-display").innerText = (
        f"{region.strain_fraction() * 100:.0f}% {region.strain_level()}"
    )
    document.getElementById("hud-wellbeing-display").innerText = (
        f"{region.wellbeing_score():.0f} {wellbeing_band(region.wellbeing_score())}"
    )
    document.getElementById("wellbeing-message-display").innerText = wellbeing_message(
        region.wellbeing_score()
    )

    # I5: one-time thriving-band callout.
    thriving_display = document.getElementById("thriving-callout-display")
    thriving_message = thriving_callout_message(region)
    thriving_display.hidden = thriving_message is None
    thriving_display.innerText = thriving_message or ""

    document.getElementById("checkpoint-display").innerText = checkpoint_message(region)

    # I11: periodic session-milestone summary.
    milestone_display = document.getElementById("session-milestone-display")
    milestone_message = session_milestone_message(region)
    milestone_display.hidden = milestone_message is None
    milestone_display.innerText = milestone_message or ""
    if region.milestone_just_updated:
        region.milestone_just_updated = False
        _pulse("session-milestone-display", "session-milestone--pulse")

    # I17: passive unmanaged control region, for contrast -- not enough
    # signal to show anything meaningful before at least one round has
    # completed.
    control_display = document.getElementById("control-region-contrast-display")
    if region.round_number > 1:
        control_region = _simulate_control_region(region.round_number, region.accelerated_severity_enabled, region.calendar_enabled)
        control_display.hidden = False
        control_display.innerText = control_region_contrast_message(control_region)
    else:
        control_display.hidden = True
        control_display.innerText = ""

    control_display.title = CONTROL_REGION_TOOLTIP  # I12

    # I28: what triggers the strain-consequence messages.
    document.getElementById("strain-consequence-display").title = strain_consequence_tooltip()
    # I9: capacity-planning forecast. I30: next capacity milestone.
    document.getElementById("forecast-display").innerText = forecast_message(region)
    document.getElementById("capacity-milestone-display").innerText = capacity_milestone_message(region)
    # I27: capacity-investment ROI.
    document.getElementById("roi-display").innerText = roi_message(region)
    # I16: recovery-path Model Region badge.
    recovery_badge = document.getElementById("recovery-badge")
    recovery_text = recovery_badge_text(region, _ever_reached_critical_strain())
    recovery_badge.hidden = recovery_text is None
    recovery_badge.innerText = recovery_text or ""
    # I11: thriving vignette.
    vignette_box = document.getElementById("thriving-vignette-box")
    vignette_text = thriving_vignette_message(region)
    vignette_box.hidden = vignette_text is None
    document.getElementById("thriving-vignette-display").innerText = vignette_text or ""
    # I24: per-sub-score trend arrows. I14: threshold number on the target marker.
    for key, arrow_id, target_id in (
        ("service", "service-quality-trend", "service-quality-target"),
        ("economy", "economic-health-trend", "economic-health-target"),
        ("cohesion", "social-cohesion-trend", "social-cohesion-target"),
    ):
        arrow_el = document.getElementById(arrow_id)
        arrow = subscore_arrow(region.subscore_log, key)
        arrow_el.innerText = arrow
        arrow_el.title = {"▲": "improving", "▶": "plateauing", "▼": "declining"}.get(arrow, "")
        document.getElementById(arrow_id.replace("-trend", "-spark")).innerHTML = subscore_sparkline(
            region.subscore_log, key
        )
        document.getElementById(target_id).innerText = (
            f"Thriving marker: {THRIVING_WELLBEING_SCORE:.0f}"
        )

    # I23: region name, I15 crisis start, I19 reallocation controls.
    crisis_button = document.getElementById("crisis-start-toggle-button")
    crisis_button.innerText = (
        "Crisis Start: ON" if region.crisis_start_enabled else "Crisis Start: OFF"
    )
    crisis_button.disabled = not region.can_toggle_crisis_start()
    crisis_button.title = (
        "Optional harder start, choosable only before round 1: begin with fewer funds and a "
        "backlog of people already arrived, to try recovering from behind."
    )
    if region.crisis_start_enabled:
        crisis_button.classList.add("active")
    else:
        crisis_button.classList.remove("active")
    document.getElementById("realloc-button").disabled = not (
        region.funds >= REALLOCATION_FUNDS_COST
        and any(region.capacity[t] >= REALLOCATION_UNITS for t in CAPACITY_TYPES)
    )
    document.getElementById("realloc-note").innerText = (
        f"Move {REALLOCATION_UNITS:.0f} capacity between types for {REALLOCATION_FUNDS_COST:.0f} funds; "
        f"{REALLOCATION_LOSS_FRACTION * 100:.0f}% of the moved capacity is lost in the transition."
    )
    # I5 coda legacy line, I21 side-by-side control comparison.
    document.getElementById("coda-legacy-display").innerText = coda_legacy_message(
        region.coda_legacy_choice
    )
    if runstate.coda_visible and region.has_long_horizon_story():
        document.getElementById("coda-control-display").innerText = coda_control_message(
            region, _simulate_control_region(region.round_number, region.accelerated_severity_enabled, region.calendar_enabled)
        )

    # I2: skyline building count/height tracking real capacity.
    visible_building_count = region_visual_building_count(region.total_capacity())
    building_height_scale = region_visual_height_scale(region.total_capacity())
    for index, building_id in enumerate(REGION_VISUAL_BUILDING_IDS):
        building_el = document.getElementById(f"region-visual-building-{building_id}")
        building_el.hidden = index >= visible_building_count
        building_el.style.transform = f"scaleY({building_height_scale:.2f})"

    # I1: strain/wellbeing trend graph (I-12 layers and event markers, I-16 range and crosshair).
    render_trend_graph()

    coda_button = document.getElementById("coda-button")
    coda_button.hidden = not region.has_long_horizon_story()
    coda_button.innerText = "Hide Long-Horizon Outcomes" if runstate.coda_visible else "View Long-Horizon Outcomes"
    # I15: one-time highlight/pulse the moment the coda first becomes
    # available -- consume-and-reset, so it only ever fires once.
    if region.coda_just_became_available:
        region.coda_just_became_available = False
        _pulse("coda-button", "coda-button--pulse")

    coda_section = document.getElementById("coda-section")
    coda_section.hidden = not (runstate.coda_visible and region.has_long_horizon_story())
    if runstate.coda_visible and region.has_long_horizon_story():
        document.getElementById("coda-message-display").innerText = long_horizon_coda_message(region)
        _render_coda_comparison(
            "service-quality", region.service_quality(), region.projected_service_quality()
        )
        _render_coda_comparison(
            "economic-health", region.economic_health(), region.projected_economic_health()
        )
        _render_coda_comparison(
            "social-cohesion", region.social_cohesion(), region.projected_social_cohesion()
        )
        document.getElementById("coda-wellbeing-display").innerText = (
            f"Projected long-horizon wellbeing: {region.projected_wellbeing_score():.0f} "
            f"(from {region.wellbeing_score():.0f} today)"
        )

    for capacity_type in CAPACITY_TYPES:
        document.getElementById(f"{capacity_type}-name").innerText = (
            f"{CAPACITY_ICON[capacity_type]} {CAPACITY_LABEL[capacity_type]}"
        )
        document.getElementById(f"{capacity_type}-count").innerText = (
            f"{region.capacity[capacity_type]:.0f}"
        )
        button = document.getElementById(f"{capacity_type}-invest-button")
        button.innerText = f"{CAPACITY_LABEL[capacity_type]} ({INVEST_COST[capacity_type]:.0f})"
        button.disabled = region.funds < INVEST_COST[capacity_type]
        # I7: one-line effect summary directly on each investment row.
        document.getElementById(f"{capacity_type}-effect-display").innerText = (
            CAPACITY_EFFECT_SUMMARY[capacity_type]
        )

    # I13: opt-in difficulty toggle -- purely reflects the current
    # setting, never touches strain/arrivals math directly (see
    # ACCELERATED_SEVERITY_MULTIPLIER's comment above).
    accelerated_button = document.getElementById("accelerated-severity-toggle-button")
    accelerated_button.innerText = (
        f"🔥 Accelerated Severity: ON ({ACCELERATED_SEVERITY_MULTIPLIER:.0f}x)"
        if region.accelerated_severity_enabled
        else "Accelerated Severity: OFF"
    )
    if region.accelerated_severity_enabled:
        accelerated_button.classList.add("active")
    else:
        accelerated_button.classList.remove("active")
    # Onboarding-tooltip coverage (planning/TODO.md, origin A14): this
    # toggle isn't in DRIFT_TUTORIAL_STEPS at all, so it's covered by
    # neither the one-time walkthrough nor the auto-generated How to Play
    # read-through (shared/tutorial.js builds that page from the same
    # steps array). The label alone ("Accelerated Severity: ON/OFF") never
    # says what it actually changes, so a returning player has nowhere to
    # find out. A `title` states the real effect directly from the same
    # constant the game logic uses.
    accelerated_button.title = (
        f"Optional difficulty variant: multiplies background displacement-pressure "
        f"severity growth by {ACCELERATED_SEVERITY_MULTIPLIER:.0f}x. Only affects how fast "
        f"arrival pressure rises — never your capacity or funds math directly."
    )
    render_skins()
    render_load_note()
    document.getElementById("news-ticker").innerText = news_headline(region)
    render_round_tools()
    render_civic_tools()
    render_ledger()
    render_collection_summary()
    render_batch3()
    # I-5: Non-visual mode tables and aria-live summary
    if runstate.non_visual_mode:
        nv_tables = document.getElementById("non-visual-tables")
        nv_tables.hidden = False

        status_body = document.getElementById("nv-status-body")
        status_body.innerHTML = (
            f"<tr><td>Round</td><td>{region.round_number}</td></tr>"
            f"<tr><td>Funds</td><td>{region.funds:.0f}</td></tr>"
            f"<tr><td>Total capacity</td><td>{region.total_capacity():.0f}</td></tr>"
            f"<tr><td>Strain</td><td>{region.strain_fraction() * 100:.0f}% ({region.strain_level()})</td></tr>"
            f"<tr><td>Integrated</td><td>{region.integrated_population:.0f}</td></tr>"
            f"<tr><td>Pending</td><td>{region.pending_population():.0f}</td></tr>"
        )

        arrival_body = document.getElementById("nv-arrival-body")
        current_arrivals = region.arrivals_this_round()
        visible_dots = arrival_stream_dot_count(current_arrivals)
        arrival_body.innerHTML = (
            f"<tr><td>Current round</td><td>{current_arrivals:.0f}</td><td>{visible_dots} dots</td></tr>"
        )
        if hasattr(region, "arrivals_log") and region.arrivals_log:
            for i, val in enumerate(reversed(region.arrivals_log[-5:])):
                arrival_body.innerHTML += f"<tr><td>Round {region.round_number - len(region.arrivals_log) + i + 1}</td><td>{val:.0f}</td><td>{arrival_stream_dot_count(val)} dots</td></tr>"

        gauges_body = document.getElementById("nv-gauges-body")
        sq_arrow = subscore_arrow(region.subscore_log, "service")
        eh_arrow = subscore_arrow(region.subscore_log, "economy")
        sc_arrow = subscore_arrow(region.subscore_log, "cohesion")
        gauges_body.innerHTML = (
            f"<tr><td>Service quality</td><td>{region.service_quality():.0f}</td><td>{sq_arrow}</td></tr>"
            f"<tr><td>Economic health</td><td>{region.economic_health():.0f}</td><td>{eh_arrow}</td></tr>"
            f"<tr><td>Social cohesion</td><td>{region.social_cohesion():.0f}</td><td>{sc_arrow}</td></tr>"
        )

        document.getElementById("non-visual-summary").innerText = (
            f"Round {region.round_number}. Funds: {region.funds:.0f}. "
            f"Strain: {region.strain_fraction() * 100:.0f}% ({region.strain_level()}). "
            f"Wellbeing: {region.wellbeing_score():.0f}."
        )
    else:
        document.getElementById("non-visual-tables").hidden = True

    document.title = tab_title()
