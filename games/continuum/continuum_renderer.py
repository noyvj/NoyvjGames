"""render(): redraws the whole page from the settlement. It calls every update_* function, and the handler modules before it call it back through a late-bound `render` placeholder."""

from js import document

import sandbox
import sim

import continuum_runstate as runstate
from continuum_achievements import update_achievements_display
from continuum_advisors import update_advisors_panel
from continuum_archive import update_found_display, update_postmortem_panel, update_summary_panel
from continuum_base import _notify_visual_layer, current_effects, land_health_message, season_report_message
from continuum_beyond import update_beyond_panel
from continuum_challenge import update_challenge_panel
from continuum_citizens import update_citizens_panel, update_neighbours_panel, update_spotlight_card
from continuum_clock import render_clock
from continuum_dynasty import update_doctrines_panel, update_dynasty_panel, update_rewind_button
from continuum_geography import update_geography_panel
from continuum_hamlet import render_hamlet
from continuum_heritage import update_heritage_panel
from continuum_infopanels import render_info_page
from continuum_orders import update_orders_panel
from continuum_panels import render_log, render_research, render_sustainability
from continuum_progress import render_buildings, render_era_progress, render_revisit, render_work
from continuum_scenario import update_consulting_display, update_hard_mode_display, update_scenario_display
from continuum_techdebt import update_techdebt_display
from continuum_timelapse import update_timelapse_panel
from continuum_views import render_insights, update_views_panel


def render():
    effects = current_effects()
    if runstate.sandbox_active:  # Z-18: stocks are topped up after every action too, so nothing is ever short
        sandbox.relief(runstate.state, effects)
    render_clock()

    document.getElementById("era-display").innerText = f"{sim.ERA_LABEL[runstate.state.era]} era"
    document.getElementById("season-display").innerText = f"Season {runstate.state.season}"

    housing = runstate.state.housing_capacity(effects)
    document.getElementById("population-display").innerText = f"People: {runstate.state.population}"
    document.getElementById("housing-display").innerText = (
        f"Shelter for {housing:.0f}"
        + (" — overcrowded" if runstate.state.population > housing else "")
    )
    document.getElementById("idle-display").innerText = f"Unassigned: {runstate.state.idle_workers()}"

    storage = runstate.state.food_storage_capacity(effects)
    document.getElementById("food-display").innerText = (
        f"Food: {runstate.state.resources['food']:.0f} / {storage:.0f}"
    )
    document.getElementById("materials-display").innerText = (
        f"Materials: {runstate.state.resources['materials']:.0f}"
    )
    document.getElementById("tools-display").innerText = f"Tools: {runstate.state.resources['tools']:.1f}"
    document.getElementById("knowledge-display").innerText = (
        f"Knowledge: {runstate.state.resources['knowledge']:.1f}"
    )
    # Surplus (Milestone 8, Agrarian+): shown once there's a nonzero amount
    # or the settlement has actually reached an era that can bank it, so a
    # Tribal-only playthrough never sees a "Surplus: 0.0" line that means
    # nothing yet.
    surplus_line = document.getElementById("surplus-display")
    if sim.era_index(runstate.state.era) >= sim.era_index("agrarian") or runstate.state.resources["surplus"] > 0:
        surplus_line.hidden = False
        surplus_line.innerText = f"Surplus: {runstate.state.resources['surplus']:.1f}"
    else:
        surplus_line.hidden = True

    document.getElementById("land-health-display").innerText = (
        f"Land health: {runstate.state.land_health * 100:.0f}% — {land_health_message(runstate.state.land_health)}"
    )
    document.getElementById("land-health-bar").style.width = f"{runstate.state.land_health * 100:.0f}%"

    document.getElementById("season-report-display").innerText = season_report_message(
        runstate.state.last_report
    )

    render_work()
    render_buildings()
    render_sustainability(effects)
    render_research()
    render_info_page()
    render_log()
    render_era_progress(effects)
    render_revisit()
    update_achievements_display()
    update_scenario_display()
    update_hard_mode_display()
    update_techdebt_display()
    update_challenge_panel()
    update_timelapse_panel()
    update_advisors_panel()
    update_summary_panel()
    update_postmortem_panel()
    update_views_panel(effects)
    update_consulting_display()
    update_found_display()
    update_dynasty_panel()
    update_doctrines_panel()
    update_citizens_panel()
    update_spotlight_card()
    update_neighbours_panel()
    update_orders_panel()
    update_heritage_panel()
    update_beyond_panel()
    update_geography_panel()
    update_rewind_button()
    render_insights(effects)
    render_hamlet(effects)
    _notify_visual_layer()


# Late-bound name: these modules come before this one and call render(), so each holds a `render = None`
# placeholder. Now that it exists, fill them all in (tests/test_module_list.py checks this wiring).
import continuum_founders
import continuum_archive
import continuum_dynasty
import continuum_beyond
import continuum_techdebt
import continuum_heritage
import continuum_savestate
import continuum_citizens
import continuum_panels
import continuum_challenge
import continuum_geography
import continuum_progress
import continuum_views
import continuum_scenario
import continuum_hamlet
import continuum_advance
import continuum_advisors

_RENDER_USERS = (
    continuum_founders,
    continuum_archive,
    continuum_dynasty,
    continuum_beyond,
    continuum_techdebt,
    continuum_heritage,
    continuum_savestate,
    continuum_citizens,
    continuum_panels,
    continuum_challenge,
    continuum_geography,
    continuum_progress,
    continuum_views,
    continuum_scenario,
    continuum_hamlet,
    continuum_advance,
    continuum_advisors,
)
for _user in _RENDER_USERS:
    _user.render = render
del _user
