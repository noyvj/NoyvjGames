"""The Work and Build panels, the era-progress panel, Advance Era, and the Look Back (revisit) panel."""

from js import document
from pyodide.ffi import create_proxy

import consulting
import eastereggs
import heritage
import par
import sim
import transition

import continuum_runstate as runstate
from continuum_achievements import _check_new_achievements_for_toast
from continuum_base import _resting, _rewind_clear
from continuum_founders import _tick_play_time, play_seconds, record_motion, update_minutes_panel
from continuum_panels import _make_assign_handler, _make_build_handler, _make_unassign_handler
from continuum_techdebt import _easter_egg

render = None  # placeholder: continuum_renderer fills this in when it is imported (it comes later)

# Work/Build row buttons, keyed by (role-or-building, "add"/"remove"/
# "build"). Milestone 8 made these panels dynamic (built from
# sim.roles_for_era()/buildings_for_era() every render, same reason
# render_research() already is: a second era's roster can't be static
# markup) — which means they need the exact same "destroy the proxy this
# render is replacing" discipline render_research() already established,
# or Farmers/Farmland's buttons would leak a Pyodide proxy every render
# the same way an un-destroyed research proxy would.
_work_button_proxies = {}
_building_button_proxies = {}


def render_work():
    """The Work panel, rebuilt from `sim.roles_for_era(state.era)` every
    render — Tribal's four roles never disappear, a later era's roles are
    simply appended once reached (see sim.py's ERA_ROLES)."""
    idle = runstate.state.idle_workers()
    document.getElementById("idle-display").innerText = f"Unassigned: {idle}"

    container = document.getElementById("work-list")
    container.innerHTML = ""

    roles = sim.roles_for_era(runstate.state.era)
    live_roles = set(roles)
    for role in roles:
        row = document.createElement("div")
        row.className = "row"

        top = document.createElement("div")
        top.className = "row-top"
        # Emoji stays decoration, not data (matches the original static
        # markup's structure): a plain-text prefix on the outer span, with
        # the `{role}-name` id on an inner span holding just the label, so
        # anything reading that id's innerText (rendering, tests) still
        # gets the label alone.
        name = document.createElement("span")
        name.className = "row-name"
        name.innerText = f"{sim.ROLE_EMOJI[role]} "
        name_label = document.createElement("span")
        name_label.id = f"{role}-name"
        name_label.innerText = sim.ROLE_LABEL[role]
        name.appendChild(name_label)
        count = document.createElement("span")
        count.className = "row-count"
        count.id = f"{role}-count"
        count.innerText = str(runstate.state.allocation[role])
        top.appendChild(name)
        top.appendChild(count)
        row.appendChild(top)

        blurb = document.createElement("p")
        blurb.className = "row-blurb"
        blurb.id = f"{role}-blurb"
        blurb.innerText = sim.ROLE_BLURB[role]
        row.appendChild(blurb)

        actions = document.createElement("div")
        actions.className = "row-actions"

        remove_button = document.createElement("button")
        remove_button.id = f"{role}-remove-button"
        remove_button.className = "secondary"
        remove_button.innerText = "−"
        remove_button.disabled = runstate.state.allocation[role] <= 0
        remove_proxy = create_proxy(_make_unassign_handler(role))
        stale = _work_button_proxies.get((role, "remove"))
        if stale is not None:
            stale.destroy()
        _work_button_proxies[(role, "remove")] = remove_proxy
        remove_button.addEventListener("click", remove_proxy)
        actions.appendChild(remove_button)

        add_button = document.createElement("button")
        add_button.id = f"{role}-add-button"
        add_button.className = "secondary"
        add_button.innerText = "+"
        add_button.disabled = idle <= 0
        add_proxy = create_proxy(_make_assign_handler(role))
        stale = _work_button_proxies.get((role, "add"))
        if stale is not None:
            stale.destroy()
        _work_button_proxies[(role, "add")] = add_proxy
        add_button.addEventListener("click", add_proxy)
        actions.appendChild(add_button)

        row.appendChild(actions)
        container.appendChild(row)

    for key in list(_work_button_proxies):
        if key[0] not in live_roles:
            _work_button_proxies.pop(key).destroy()


def render_buildings():
    """The Build panel, rebuilt from `sim.buildings_for_era(state.era)`
    every render — same reasoning as render_work() above."""
    container = document.getElementById("buildings-list")
    container.innerHTML = ""

    buildings = sim.buildings_for_era(runstate.state.era)
    live_buildings = set(buildings)
    for building in buildings:
        row = document.createElement("div")
        row.className = "row"

        top = document.createElement("div")
        top.className = "row-top"
        name = document.createElement("span")
        name.className = "row-name"
        name.innerText = f"{sim.BUILDING_EMOJI[building]} "
        name_label = document.createElement("span")
        name_label.id = f"{building}-name"
        name_label.innerText = sim.BUILDING_LABEL[building]
        name.appendChild(name_label)
        count = document.createElement("span")
        count.className = "row-count"
        count.id = f"{building}-count"
        count.innerText = str(runstate.state.buildings[building])
        top.appendChild(name)
        top.appendChild(count)
        row.appendChild(top)

        blurb = document.createElement("p")
        blurb.className = "row-blurb"
        blurb.id = f"{building}-blurb"
        blurb.innerText = sim.BUILDING_BLURB[building]
        row.appendChild(blurb)

        actions = document.createElement("div")
        actions.className = "row-actions"
        button = document.createElement("button")
        button.id = f"{building}-build-button"
        button.className = "secondary"
        button.innerText = f"Build ({sim.BUILDING_COST[building]:.0f})"
        button.disabled = not runstate.state.can_build(building)
        proxy = create_proxy(_make_build_handler(building))
        stale = _building_button_proxies.get(building)
        if stale is not None:
            stale.destroy()
        _building_button_proxies[building] = proxy
        button.addEventListener("click", proxy)
        actions.appendChild(button)
        row.appendChild(actions)

        container.appendChild(row)

    for building in list(_building_button_proxies):
        if building not in live_buildings:
            _building_button_proxies.pop(building).destroy()


def render_era_progress(effects):
    """Milestone 7/8: shows whether the settlement is ready to leave its
    current era, and why not if it isn't — the same "doubles as the UI
    explanation and what tests assert against" pattern research.py's own
    locked-node reasons already use. The button only ever calls
    transition.attempt_transition(), which itself refuses cleanly if
    anything has changed between render and click (e.g. a revisit started
    in another tab of the same session)."""
    next_era = transition.next_era_for(runstate.state.era)
    button = document.getElementById("advance-era-button")
    status = document.getElementById("era-progress-status-display")
    reasons_el = document.getElementById("era-progress-reasons-display")

    if next_era is None:
        status.innerText = "Nothing more to reach from here yet."
        reasons_el.innerText = ""
        button.innerText = "—"
        button.disabled = True
        return

    ready = transition.transition_ready(runstate.state, runstate.tree, effects)
    status.innerText = (
        f"Ready to move into the {sim.ERA_LABEL[next_era]} era."
        if ready
        else f"Working toward the {sim.ERA_LABEL[next_era]} era."
    )
    reasons_el.innerText = " ".join(transition.missing_requirements(runstate.state, runstate.tree, effects))
    button.innerText = f"Advance to {sim.ERA_LABEL[next_era]}"
    button.disabled = not ready


def _record_par():
    """K-26: stores the run's season count and time the moment the last era is entered."""
    if runstate.campaign.furthest_era != par.final_era():
        return False
    return par.record(
        runstate.campaign.ui,
        max(1, int(runstate.state.season) - 1),
        play_seconds(),
        runstate.state.scenario,
        already_inherited=consulting.get(runstate.campaign.ui) is not None,
    )


def _log_heritage_left_behind():
    """K-5: the era just left stays standing as a heritage site; say so once, in the log."""
    if _resting() or runstate.campaign.revisiting is not None:
        return
    for site in heritage.sites_before(runstate.state.era, runstate.campaign.ui):
        if site["era"] == sim.ERA_ORDER[sim.era_index(runstate.state.era) - 1]:
            runstate.chronicle.log_challenge(
                runstate.state.season, runstate.state.era,
                f"{site['name']} is left standing at the edge of town: {site['blurb']} Keep it for the "
                "culture it gives, or clear it (see Heritage sites).",
            )


def on_advance_era(event=None):
    if transition.attempt_transition(runstate.campaign):
        _rewind_clear()
        runstate.chronicle.log_challenge(
            runstate.state.season, runstate.state.era,
            f"A doctrine can now be adopted for the {sim.ERA_LABEL[runstate.state.era]} era (see Doctrines).",
        )
        _tick_play_time()
        _record_par()
        record_motion("era", sim.ERA_LABEL[runstate.state.era] + " era")
        _easter_egg(eastereggs.on_era(runstate.campaign.ui, runstate.state.era))
        _log_heritage_left_behind()
        update_minutes_panel()
        render()
        _check_new_achievements_for_toast()


# --- "look back" at a completed era (Milestone 15 / K7) -----------------
# The save schema (save.py's Campaign.enter_revisit()/exit_revisit()) has
# supported this since Milestone 4, and it has been fully tested since —
# but no button anywhere ever called it: there was no revisit UI at all
# before this milestone. This section is that missing UI. It needs no new
# state-to-visual plumbing: get_visual_state() already reads directly off
# `state`, and enter_revisit()/exit_revisit() mutate `state` in place (the
# same object game.py's module-level `state` name points at), so the
# moment a revisit is entered here, the existing Three.js render layer
# (render3d.js, via _notify_visual_layer() at the end of render()) redraws
# the revisited era's own scene automatically — the K7 ask was really "the
# UI to reach this", not a rendering gap.
_revisit_button_proxies = {}


def render_revisit():
    """The Look Back panel — rebuilt every render(), the same reason every
    other dynamic panel in this file is: the list of revisitable eras grows
    over a playthrough and can't be static markup."""
    status = document.getElementById("revisit-status-display")
    container = document.getElementById("revisit-era-list")
    exit_button = document.getElementById("exit-revisit-button")
    banner = document.getElementById("revisit-active-banner")

    if runstate.campaign.revisiting is not None:
        era_label = sim.ERA_LABEL[runstate.campaign.revisiting]
        status.innerText = f"Looking back at the {era_label} era, exactly as it stood when you left it."
        banner.innerText = (
            f"You're looking back at the {era_label} era — nothing you do here "
            "affects your forward progress."
        )
        banner.hidden = False
        exit_button.hidden = False
    else:
        banner.hidden = True
        exit_button.hidden = True
        revisitable = runstate.campaign.revisitable_eras()
        status.innerText = (
            "No completed eras to look back on yet — finish your first era transition."
            if not revisitable
            else "Completed eras you can look back on:"
        )

    container.innerHTML = ""
    live_eras = set()
    if runstate.campaign.revisiting is None:
        for era in runstate.campaign.revisitable_eras():
            live_eras.add(era)
            row = document.createElement("div")
            row.className = "row"

            top = document.createElement("div")
            top.className = "row-top"
            name = document.createElement("span")
            name.className = "row-name"
            name.innerText = sim.ERA_LABEL[era]
            top.appendChild(name)
            row.appendChild(top)

            actions = document.createElement("div")
            actions.className = "row-actions"
            button = document.createElement("button")
            button.id = f"revisit-{era}-button"
            button.className = "secondary"
            button.innerText = "View"
            proxy = create_proxy(_make_enter_revisit_handler(era))
            stale = _revisit_button_proxies.get(era)
            if stale is not None:
                stale.destroy()
            _revisit_button_proxies[era] = proxy
            button.addEventListener("click", proxy)
            actions.appendChild(button)
            row.appendChild(actions)
            hint = heritage.preview_text(era, runstate.campaign.ui)
            if hint and not _resting():
                note = document.createElement("p")
                note.className = "row-blurb heritage-preview"
                note.innerText = hint
                row.appendChild(note)

            container.appendChild(row)

    for era in list(_revisit_button_proxies):
        if era not in live_eras:
            _revisit_button_proxies.pop(era).destroy()


def _make_enter_revisit_handler(era):
    def handler(event=None):
        if runstate.campaign.enter_revisit(era):
            _rewind_clear()
            render()
            _check_new_achievements_for_toast()
    return handler


def on_exit_revisit(event=None):
    if runstate.campaign.exit_revisit():
        render()
