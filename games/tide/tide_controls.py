"""Output mix, sea scenario, coastline picker, settlement history and the programmes list."""

import math

from js import document

import tide_runstate as runstate
from tide_coastline import heritage_status_text
from tide_coasts import coast_storm_interval, heritage_sites
from tide_rules import (
    CITIZEN_SCIENCE_FACTS, COASTLINES, DIVERSIFY_COST, DIVERSIFY_MAX_LEVEL, HERITAGE_UNPROTECTED,
    MONITOR_COOLDOWN_SEASONS, MONITOR_COST, OUTPUT_MIX, RETREAT_COST, RETREAT_DAMAGE_CUT, RETREAT_MAX_STEPS,
)


def render_output_mix_controls():
    """D16: keeps the output-mix <select> showing whatever mix is
    actually live -- needed because load_state() can change output_mix
    from a code path other than the dropdown itself."""
    select = document.getElementById("output-mix-select")
    if select is not None:
        select.value = runstate.state.output_mix
    # D22: live preview of every mix's per-season trade-off at current
    # capacity, so the choice is informed before it's made.
    preview_el = document.getElementById("output-mix-preview")
    if preview_el is not None:
        parts = []
        for mix in OUTPUT_MIX:
            income, acidity = runstate.state.output_mix_preview(mix)
            parts.append(f"{mix.capitalize()}: {income:+.0f} funds, {acidity:+.1f} acidity")
        preview_el.innerText = "Per season at current capacity — " + " | ".join(parts)


def render_fish_recovery_banner():
    """D23: shown for the season a crashed fish stock finishes rebuilding."""
    banner = document.getElementById("fish-recovery-banner")
    if banner is None:
        return
    if runstate.state.recovery_celebrated_season and runstate.state.recovery_celebrated_season == runstate.state.season:
        banner.hidden = False
        banner.innerText = (
            "🎉 Recovery! The fish stock has rebuilt — the lag that delayed the "
            "damage also delayed the healing, and your cleaner choices got you here."
        )
        if runstate.state.acid_boss_result == "survived":  # GD-12: the full victory beat
            banner.innerText = ("\U0001F3C6 Victory! You braced for the Acid Tide and the fish stock rebuilt anyway: "
                                "the buffer you set aside is why the harbour is still full of life.")
    else:
        banner.hidden = True


def render_sea_scenario_controls():
    """D19: syncs the scenario <select>, locking it once play has begun."""
    select = document.getElementById("sea-scenario-select")
    if select is not None:
        select.value = runstate.state.sea_scenario
        select.disabled = bool(runstate.state.damage_log) or runstate.state.season != 1 or bool(runstate.state.daily)
    render_coastline_controls()


def coastline_blurb_text(coast_id):
    info = COASTLINES[coast_id]
    sites = " and ".join(site["name"].lower() for site in info["heritage"])
    weights = (f"Output income x{info['output']:g}, tourism x{info['tourism']:g}, aquaculture x{info['aquaculture']:g}; "
               f"storms every {info['storm_interval']} seasons" + (f", surges x{info['surge']:g}" if info["surge"] != 1.0 else ""))
    first = min(info["thresholds"])
    last = max(info["thresholds"])
    return (f"{info['blurb']} Rows flood at sea level {first:g} up to {last:g}. Heritage: {sites}. {weights}.")


def render_coastline_controls():
    """D-8: syncs the coastline <select> and its description; locked once play has begun, like the sea scenario."""
    select = document.getElementById("coastline-select")
    if select is not None:
        select.value = runstate.state.coastline
        select.disabled = bool(runstate.state.damage_log) or runstate.state.season != 1 or bool(runstate.state.daily)
    blurb = document.getElementById("coastline-blurb")
    if blurb is not None:
        blurb.innerText = coastline_blurb_text(runstate.state.coastline)


def render_settlement_history():
    """D29: the settlement's name field and chronicle."""
    heading = document.getElementById("settlement-heading")
    if heading is not None:
        heading.innerText = f"{runstate.state.display_name()} — chronicle"
    name_input = document.getElementById("settlement-name-input")
    if name_input is not None and name_input.value != runstate.state.settlement_name:
        name_input.value = runstate.state.settlement_name
    log_el = document.getElementById("settlement-chronicle")
    if log_el is not None:
        lines = runstate.state.chronicle_lines()
        log_el.innerHTML = (
            "<br>".join(lines) if lines else "Nothing to record yet — history starts as you play."
        )


def render_programmes():
    """D17 / D21 / D13 (and later additions): the collapsed "Coastal
    programmes" section's readouts and button states."""
    for i, site in enumerate(heritage_sites()):
        status_el = document.getElementById(f"heritage-status-{i}")
        if status_el is not None:
            status_el.innerText = heritage_status_text(site)
        button = document.getElementById(f"heritage-protect-{i}")
        if button is not None:
            button.innerText = f"Protect ({site['cost']})"
            button.disabled = not (
                runstate.state.heritage.get(site["id"]) == HERITAGE_UNPROTECTED
                and runstate.state.funds >= site["cost"]
                and not runstate.state.row_lost(site["row"])
            )
    monitor_button = document.getElementById("monitor-button")
    if monitor_button is not None:
        if runstate.state.monitoring_reports >= len(CITIZEN_SCIENCE_FACTS):
            monitor_button.innerText = "All monitoring reports collected"
        elif (
            runstate.state.monitoring_last_season
            and runstate.state.season - runstate.state.monitoring_last_season < MONITOR_COOLDOWN_SEASONS
        ):
            monitor_button.innerText = "Monitoring crews are out — report next season"
        else:
            monitor_button.innerText = f"Fund monitoring ({MONITOR_COST})"
        monitor_button.disabled = not runstate.state.can_monitor()
    monitor_log = document.getElementById("monitor-log")
    if monitor_log is not None:
        facts = runstate.state.revealed_facts()
        monitor_log.innerHTML = (
            "<br>".join(f"{i + 1}. {fact}" for i, fact in enumerate(facts))
            if facts
            else "No reports yet — each funded report reveals a real-world finding."
        )
    # D1 managed retreat.
    retreat_button = document.getElementById("retreat-button")
    if retreat_button is not None:
        retreat_button.innerText = (
            f"Managed retreat ({RETREAT_COST})"
            if len(runstate.state.retreat_rows) < RETREAT_MAX_STEPS
            else "Managed retreat complete"
        )
        retreat_button.disabled = not runstate.state.can_retreat()
    retreat_el = document.getElementById("retreat-status")
    if retreat_el is not None:
        steps = len(runstate.state.retreat_rows)
        retreat_el.innerText = (
            f"Retreat steps taken: {steps}/{RETREAT_MAX_STEPS} — sea-level damage cut a further "
            f"{steps * RETREAT_DAMAGE_CUT * 100:.0f}% (compounding with your tier), at the price of "
            f"{steps} row(s) of coast."
        )
    # D5 / D15 population, always visible in the status block.
    population_el = document.getElementById("population-display")
    if population_el is not None:
        population_el.innerText = runstate.state.population_text()
    # D11 diversification.
    for kind, cost in DIVERSIFY_COST.items():
        button = document.getElementById(f"diversify-{kind}-button")
        if button is not None:
            level = runstate.state.diversification[kind]
            button.innerText = (
                f"{kind.capitalize()} level {level}/{DIVERSIFY_MAX_LEVEL} — max"
                if level >= DIVERSIFY_MAX_LEVEL
                else f"{kind.capitalize()} level {level}/{DIVERSIFY_MAX_LEVEL} — upgrade ({cost})"
            )
            button.disabled = level >= DIVERSIFY_MAX_LEVEL or runstate.state.funds < cost
    diversify_el = document.getElementById("diversify-status")
    if diversify_el is not None:
        tourism, aquaculture = runstate.state.diversified_income()
        diversify_el.innerText = (
            f"Extra income per season: tourism {tourism:.1f}, aquaculture {aquaculture:.1f}. "
            "Neither depends on the lagged fish-yield crash; tourism fades as coast is lost."
        )
    # D27 checkpoint replay.
    checkpoint_el = document.getElementById("checkpoint-status")
    if checkpoint_el is not None:
        checkpoint_el.innerText = (
            f"Checkpoint set at Season {runstate.state.checkpoint['season']}."
            if runstate.state.checkpoint
            else "No checkpoint set."
        ) + (f" Replays so far: {runstate.state.replay_count}." if runstate.state.replay_count else "")
    replay_button = document.getElementById("replay-button")
    if replay_button is not None:
        replay_button.disabled = not runstate.state.can_replay()
    foresight_el = document.getElementById("foresight-display")
    if foresight_el is not None:
        foresight_el.innerText = runstate.state.foresight_text()
    storm_button = document.getElementById("storm-toggle-button")
    if storm_button is not None:
        storm_button.innerText = ("Storm seasons: On (set by the daily)" if runstate.state.daily
                                  else "Storm seasons: On (turn off)" if runstate.state.storm_mode else "Storm seasons: Off (turn on)")
        storm_button.disabled = bool(runstate.state.daily)
    storm_el = document.getElementById("storm-forecast")
    if storm_el is not None:
        storm_el.innerText = storm_forecast_text()
    bell_el = document.getElementById("storm-bell")  # GD-21
    if bell_el is not None:
        bell_el.innerHTML = storm_bell_svg() if runstate.state.storm_mode else ""


# GD-21 (2026-10-09): the forecast as a range. Real forecasts are uncertain, so the surge is shown as +/- STORM_UNCERTAINTY
# and each adaptation tier has the biggest surge it can fully turn back; the chance to overtop is the share of the range
# above that height (the range treated as evenly spread). A readout of the same numbers, never changing what a storm does.
STORM_UNCERTAINTY = 0.15
TIER_SURGE_CAPACITY = (0.0, 12.0, 22.0, 34.0, 48.0)  # indexed like ADAPTATION_TIERS


def storm_range():
    surge = runstate.state.storm_surge_strength()
    return surge * (1 - STORM_UNCERTAINTY), surge * (1 + STORM_UNCERTAINTY)


def storm_wall_capacity():
    return TIER_SURGE_CAPACITY[min(runstate.state.current_tier_index(), len(TIER_SURGE_CAPACITY) - 1)]


def overtop_chance():
    """0..1: how much of the forecast range is above what the current tier turns back."""
    low, high = storm_range()
    capacity = storm_wall_capacity()
    if capacity >= high:
        return 0.0
    if capacity <= low:
        return 1.0
    return (high - capacity) / (high - low)


def storm_bell_svg():
    """A small bell curve of the forecast range with a marker at the wall height, plus a text label (not colour alone)."""
    low, high = storm_range()
    width, height = 160, 54
    span_lo, span_hi = low - 0.5 * (high - low), high + 0.5 * (high - low)

    def x_of(value):
        return (value - span_lo) / (span_hi - span_lo) * width

    mid, sigma = (low + high) / 2, (high - low) / 4
    points = []
    for i in range(0, 41):
        value = span_lo + (span_hi - span_lo) * i / 40
        y = height - 6 - (height - 14) * math.exp(-((value - mid) ** 2) / (2 * sigma * sigma))
        points.append(f"{x_of(value):.1f},{y:.1f}")
    wall_x = min(width, max(0, x_of(storm_wall_capacity())))
    chance = round(overtop_chance() * 100)
    return (
        f'<svg viewBox="0 0 {width} {height}" class="storm-bell" role="img" aria-label="Surge {low:.0f} to {high:.0f}, {chance}% chance to overtop your seawalls">'
        f'<polyline points="{" ".join(points)}" fill="none" stroke="currentColor" stroke-width="2"/>'
        f'<line x1="{wall_x:.1f}" y1="2" x2="{wall_x:.1f}" y2="{height - 4}" stroke="currentColor" stroke-width="2" stroke-dasharray="4 3"/>'
        f'<text x="{min(width - 4, wall_x + 4):.1f}" y="12" font-size="9" fill="currentColor" text-anchor="{"end" if wall_x > width - 50 else "start"}">wall {storm_wall_capacity():.0f}</text></svg>'
    )


def storm_forecast_text():
    wait = runstate.state.seasons_until_storm()
    if wait is None and runstate.state.storm_mode:  # GD-5: a daily's storms are all behind you
        return "No more storms are forecast for this run."
    if wait is None:
        return (f"Storm seasons are off. Turn them on for a surge every {coast_storm_interval(runstate.state.coastline)} seasons "
                "that tests your adaptation tier.")
    surge = runstate.state.storm_surge_strength()
    held = surge * runstate.state.dampening_fraction()
    when = "this season's end" if wait == 0 else f"{wait} season(s) from now"
    low, high = storm_range()
    return (
        f"Forecast: a surge of {low:.0f}-{high:.0f} arrives at {when}, {round(overtop_chance() * 100)}% chance to overtop "
        f"{runstate.state.current_tier()['name']} (turns back up to {storm_wall_capacity():.0f}); your current tier would hold back "
        f"about {held:.0f} of a {surge:.0f} surge."
    )
