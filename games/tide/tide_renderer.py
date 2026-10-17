"""render(): redraws the whole page from the live game, calling every panel's own render function."""

from js import document

import tide_runstate as runstate
from tide_achievements import _sync_earned_and_toast, update_achievements_display
from tide_almanac import almanac_sync, render_almanac, render_planner
from tide_chrome import (
    render_fish_warning_banner, render_graph_controls, update_session_summary_display, update_tab_status,
)
from tide_coastline import (
    damage_saved_message, damage_trend_message, render_coastline, render_coastline_comparison,
    render_scrubber,
)
from tide_controls import (
    render_fish_recovery_banner, render_output_mix_controls, render_programmes,
    render_sea_scenario_controls, render_settlement_history,
)
from tide_daily import daily_check_complete, render_daily
from tide_events import render_acid_boss, render_brace, render_chess, render_postcard
from tide_flavour import (
    render_crew, render_critters_and_quip, render_delta_popover, render_market, render_scene_theme,
)
from tide_graphs import render_graphs
from tide_libraryview import render_library
from tide_panels import (
    _maybe_update_best_coastline_saved, render_best_coastline_saved, render_info_page,
    update_changelog_display,
)
from tide_readouts import (
    acidity_past_text, plain, render_afford, render_forecast, render_goal, render_hard_lag_toggle,
    render_quiet, render_sister,
)
from tide_rules import CATEGORIES, FISH_DAMAGE_SCALE, INVEST_LABELS, TIER_BADGES, sea_level_wave_cue_duration
from tide_savestate import render_coastline_community
from tide_seasonflow import render_balance, render_run_extras
from tide_ticker import render_ledger, render_live_ticker, render_ticker_history
from tide_workshop import render_autosaves, render_workshop


def render_tide_oct9():
    render_forecast()
    render_afford()
    render_goal()
    render_quiet()
    render_balance()
    render_run_extras()
    render_critters_and_quip()
    render_scene_theme()
    render_delta_popover()
    render_market()
    render_crew()
    render_autosaves()
    render_workshop()
    render_postcard()
    render_acid_boss()
    render_brace()
    render_chess()


def render():
    daily_check_complete()  # GD-5
    render_info_page()
    render_sister()
    document.getElementById("season-display").innerText = f"Season {runstate.state.season}"
    document.getElementById("funds-display").innerText = f"Funds: {runstate.state.funds:.0f}"
    document.getElementById("acidity-display").innerText = f"Ocean acidity: {runstate.state.acidity:.1f}"
    document.getElementById("acidity-past-display").innerText = acidity_past_text()
    acidity_fraction = min(1.0, runstate.state.acidity / FISH_DAMAGE_SCALE)
    document.getElementById("acidity-bar").style.width = f"{acidity_fraction * 100:.0f}%"

    fish_yield = runstate.state.fish_yield_multiplier()
    document.getElementById("fish-yield-display").innerText = f"Fishing yield: {fish_yield * 100:.0f}%"
    document.getElementById("fish-yield-bar").style.width = f"{fish_yield * 100:.0f}%"
    render_fish_warning_banner()
    render_fish_recovery_banner()
    survived_el = document.getElementById("seasons-survived-display")
    if survived_el is not None:
        survived_el.innerText = f"Seasons survived: {max(0, runstate.state.season - 1)}"
    document.getElementById("sea-level-display").innerText = f"Sea level: {runstate.state.sea_level:.0f}"
    document.getElementById("damage-display").innerText = (
        f"Cumulative damage: {runstate.state.cumulative_damage:.0f}"
    )
    document.getElementById("damage-saved-display").innerText = damage_saved_message(runstate.state.damage_saved())
    document.getElementById("damage-trend-display").innerText = damage_trend_message(runstate.state.damage_trend())
    tier = runstate.state.current_tier()
    document.getElementById("adaptation-tier-display").innerText = plain(
        f"Adaptation tier: {tier['name']} ({tier['dampening'] * 100:.0f}% damage dampening)"
    )
    document.getElementById("adaptation-tier-progress").innerText = plain(runstate.state.next_tier_progress_text())

    # D3: seasons until the next currently-unflooded row goes under.
    next_flood_el = document.getElementById("next-flood-display")
    if next_flood_el is not None:
        remaining = runstate.state.next_flood_estimate()
        next_flood_el.innerText = (
            "Every coastline row is already flooded."
            if remaining <= 0
            else f"Next row floods in an estimated {remaining} season(s)."
        )

    # D12: the single worst season played so far.
    worst_el = document.getElementById("worst-season-display")
    if worst_el is not None:
        worst = runstate.state.worst_season()
        cause = runstate.state.worst_season_cause()
        worst_el.innerText = (
            f"Worst season: Season {worst[0]} ({worst[1]:.0f} damage)"
            + (f" — {cause}." if cause else ".")
            if worst
            else "Worst season: none yet."
        )

    render_coastline()
    render_coastline_comparison()

    # D4: a numeric then-vs-now companion to the visual comparison grids.
    then_vs_now_el = document.getElementById("then-vs-now-display")
    if then_vs_now_el is not None:
        then_vs_now_el.innerText = runstate.state.then_vs_now_text()

    # D6: "what if you'd invested earlier" counterfactual replay.
    counterfactual_el = document.getElementById("counterfactual-display")
    if counterfactual_el is not None:
        counterfactual_el.innerText = runstate.state.counterfactual_message()

    # D13: cross-session personal-best coastline-damage-saved record.
    _maybe_update_best_coastline_saved()
    render_best_coastline_saved()

    # D15 / D7: the trend graphs (range, markers, crosshair data, compared session).
    render_graph_controls()
    render_graphs()
    consequence_text = document.getElementById("delayed-consequence-text")
    if consequence_text is not None:
        consequence_text.innerText = runstate.state.delayed_consequence_text()
    # D8: this season's tide.
    tide_el = document.getElementById("tide-indicator")
    if tide_el is not None:
        tide_el.innerText = runstate.state.tide_text()
    render_settlement_history()

    sea_level_bar = document.getElementById("sea-level-bar")
    sea_level_bar.style.width = f"{runstate.state.sea_level_fraction() * 100:.0f}%"

    # D4: decorative wave/tide cue next to the meter -- speed only, never
    # touches the meter's own width/text above.
    wave_cue = document.getElementById("sea-level-wave-cue")
    if wave_cue is not None:
        duration = sea_level_wave_cue_duration(runstate.state.sea_level_fraction())
        wave_cue.style.animationDuration = f"{duration:.2f}s"

    render_live_ticker()
    render_ticker_history()

    for category in CATEGORIES:
        document.getElementById(f"{category}-count").innerText = str(runstate.state.capacity[category])
        invest_button = document.getElementById(f"{category}-invest-button")
        invest_button.innerText = f"Invest ({runstate.state.invest_cost(category)})"
        invest_button.disabled = runstate.state.funds < runstate.state.invest_cost(category)
        # D-7: three buttons all reading "Invest (30)" are ambiguous to a screen reader.
        invest_button.setAttribute(
            "aria-label", plain(f"Invest {runstate.state.invest_cost(category)} funds in {INVEST_LABELS[category]}")
        )

    render_output_mix_controls()
    render_sea_scenario_controls()
    badge = document.getElementById("adaptation-tier-badge")
    if badge is not None:
        badge.innerText = TIER_BADGES[runstate.state.current_tier_index()]
        badge.title = f"Current tier: {runstate.state.current_tier()['name']}"
    render_hard_lag_toggle()
    render_programmes()
    update_achievements_display()
    update_changelog_display()
    update_session_summary_display()
    render_ledger()
    render_scrubber()
    render_library()
    render_daily()
    render_planner()
    almanac_sync()
    render_almanac()
    update_tab_status()
    render_tide_oct9()
    render_coastline_community()  # R-30
    _sync_earned_and_toast()


# Late binding: tide_libraryview calls render() but comes earlier in the module list, so it gets it from here.
import tide_libraryview
tide_libraryview.render = render


# Late binding: tide_flavour calls render() but comes earlier in the module list, so it gets it from here.
import tide_flavour
tide_flavour.render = render
