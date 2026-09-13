"""Continuum — a sustainable city across the ages.

Runs in-browser via Pyodide. This file is the browser layer only: it owns
the DOM, the event handlers, and the rendering. All of the actual thinking
lives in the engine modules that sit beside it —

    sim.py             city simulation core (population, resources, land)
    sustainability.py  the livability score (Milestone 2)
    research.py        the research tree engine (Milestone 3)
    save.py            the continuous-save / era-snapshot schema (Milestone 4)
    info_content.py    real-world info-panel content, keyed by era (Milestone 5)
    log.py             the ongoing log / diegetic feedback system (Milestone 6)

— which is the separation the design doc's tech notes ask for, so that six
more eras of content land in the engines rather than in one tangled file.
`info_page.py` (the render/toggle logic itself) is `shared/info_page.py`,
the same module the 8 climate-quartet games use — fetched into Pyodide's
virtual filesystem by index.html the same way canopy's boot script does.

Phase 1 complete: the Tribal-era season loop, the sustainability panel, the
research panel, the collapsed real-world info panel, and the shared save
widget's get_state()/load_state() contract. Phase 2's log and era-transition
systems land here too, since both are things the player reads.
"""

import os
import sys

# index.html writes the engine modules into Pyodide's virtual filesystem
# (the working directory) before running this file; make sure that
# directory is importable. Harmless under pytest, where conftest.py has
# already put the game directory on the path.
_HERE = os.getcwd()
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import info_content  # noqa: E402
import info_page  # noqa: E402
import research  # noqa: E402
import save  # noqa: E402
import sim  # noqa: E402
import sustainability  # noqa: E402
import transition  # noqa: E402

from js import document  # noqa: E402
from pyodide.ffi import create_proxy  # noqa: E402


campaign = save.Campaign(sim.CityState(), research.build_tree())
# Module-level aliases for the two live engine objects. The save system
# always restores *into* these objects rather than replacing them, so these
# names stay valid across a load.
state = campaign.state
tree = campaign.tree
chronicle = campaign.log

# Milestone 5 — collapsed by default, per the design doc's Core system 6.
# Not one of CITY_FIELDS/tree state, so it rides in campaign.ui instead
# (get_state()/load_state() below), exactly what that save field is for.
info_page_open = False


def current_effects():
    """The aggregate modifiers applied to the simulation this season.

    The single seam through which research reaches both the simulation and
    the sustainability score — nothing else in the game reads the tree.
    """
    return tree.effects()


# --- narration ---------------------------------------------------------
def season_report_message(report):
    """One plain-language line summarising the season that just passed.

    Read with `.get()` rather than `[]` because `last_report` is a saved
    field: a loaded save can carry a report written by an earlier build of
    the season loop, and narrating one line of flavour text is not worth
    taking the whole render down over a key that didn't exist yet.
    """
    if not isinstance(report, dict):
        return "The settlement is waiting on your word."

    fed = report.get("fed_fraction", 1.0)
    parts = []
    if fed >= 1.0:
        parts.append("Everyone ate.")
    elif fed <= 0.0:
        parts.append("Nobody ate.")
    else:
        parts.append(f"Only {fed * 100:.0f}% of the settlement ate.")

    if report.get("deaths"):
        parts.append(f"{report['deaths']} lost to hunger.")
    if report.get("births"):
        parts.append(f"{report['births']} born.")
    if report.get("spoiled", 0.0) > 0.5:
        parts.append(f"{report['spoiled']:.0f} food spoiled for want of storage.")
    if report.get("surplus_banked", 0.0) > 0.5:
        parts.append(f"{report['surplus_banked']:.0f} preserved as trade surplus.")
    if report.get("extraction", 0.0) > report.get("sustainable_yield", float("inf")):
        parts.append("The land is being taken from faster than it recovers.")
    # Classical+ (Milestone 9): a canal only delivers what it's built for if
    # Administrators actually staff it -- narrate the gap so an under-staffed
    # canal reads as a real, visible cost rather than a silent one.
    if report.get("canals", 0) > 0 and report.get("canal_staffing_ratio", 1.0) < 1.0:
        staffing_pct = report["canal_staffing_ratio"] * 100
        parts.append(f"Canals running at {staffing_pct:.0f}% coordination — more administrators needed.")
    # Medieval+ (Milestone 10): Public Works isn't staffed the way a canal
    # is, but it still has a visible gap worth narrating -- unlike the
    # canal line above (a production shortfall), this is a resilience
    # warning: the settlement hasn't paid ahead of a shock for everyone.
    if report.get("public_works", 0) > 0 and report.get("public_works_coverage_ratio", 1.0) < 1.0:
        coverage_pct = report["public_works_coverage_ratio"] * 100
        parts.append(
            f"Public works cover {coverage_pct:.0f}% of the settlement — "
            "the rest would be exposed if a bad season hit."
        )

    return " ".join(parts)


def land_health_message(land_health):
    if land_health >= 0.9:
        return "The land around the settlement is untouched."
    if land_health >= 0.65:
        return "The land shows some wear."
    if land_health >= 0.4:
        return "The land is thinning — the foraging is worse than it was."
    return "The land is stripped. Little grows back."


# --- render ------------------------------------------------------------
def render():
    effects = current_effects()

    document.getElementById("era-display").innerText = f"{sim.ERA_LABEL[state.era]} era"
    document.getElementById("season-display").innerText = f"Season {state.season}"

    housing = state.housing_capacity(effects)
    document.getElementById("population-display").innerText = f"People: {state.population}"
    document.getElementById("housing-display").innerText = (
        f"Shelter for {housing:.0f}"
        + (" — overcrowded" if state.population > housing else "")
    )
    document.getElementById("idle-display").innerText = f"Unassigned: {state.idle_workers()}"

    storage = state.food_storage_capacity(effects)
    document.getElementById("food-display").innerText = (
        f"Food: {state.resources['food']:.0f} / {storage:.0f}"
    )
    document.getElementById("materials-display").innerText = (
        f"Materials: {state.resources['materials']:.0f}"
    )
    document.getElementById("tools-display").innerText = f"Tools: {state.resources['tools']:.1f}"
    document.getElementById("knowledge-display").innerText = (
        f"Knowledge: {state.resources['knowledge']:.1f}"
    )
    # Surplus (Milestone 8, Agrarian+): shown once there's a nonzero amount
    # or the settlement has actually reached an era that can bank it, so a
    # Tribal-only playthrough never sees a "Surplus: 0.0" line that means
    # nothing yet.
    surplus_line = document.getElementById("surplus-display")
    if sim.era_index(state.era) >= sim.era_index("agrarian") or state.resources["surplus"] > 0:
        surplus_line.hidden = False
        surplus_line.innerText = f"Surplus: {state.resources['surplus']:.1f}"
    else:
        surplus_line.hidden = True

    document.getElementById("land-health-display").innerText = (
        f"Land health: {state.land_health * 100:.0f}% — {land_health_message(state.land_health)}"
    )
    document.getElementById("land-health-bar").style.width = f"{state.land_health * 100:.0f}%"

    document.getElementById("season-report-display").innerText = season_report_message(
        state.last_report
    )

    render_work()
    render_buildings()
    render_sustainability(effects)
    render_research()
    render_info_page()
    render_log()
    render_era_progress(effects)


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
    idle = state.idle_workers()
    document.getElementById("idle-display").innerText = f"Unassigned: {idle}"

    container = document.getElementById("work-list")
    container.innerHTML = ""

    roles = sim.roles_for_era(state.era)
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
        count.innerText = str(state.allocation[role])
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
        remove_button.disabled = state.allocation[role] <= 0
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

    buildings = sim.buildings_for_era(state.era)
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
        count.innerText = str(state.buildings[building])
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
        button.disabled = not state.can_build(building)
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
    next_era = transition.next_era_for(state.era)
    button = document.getElementById("advance-era-button")
    status = document.getElementById("era-progress-status-display")
    reasons_el = document.getElementById("era-progress-reasons-display")

    if next_era is None:
        status.innerText = "Nothing more to reach from here yet."
        reasons_el.innerText = ""
        button.innerText = "—"
        button.disabled = True
        return

    ready = transition.transition_ready(state, tree, effects)
    status.innerText = (
        f"Ready to move into the {sim.ERA_LABEL[next_era]} era."
        if ready
        else f"Working toward the {sim.ERA_LABEL[next_era]} era."
    )
    reasons_el.innerText = " ".join(transition.missing_requirements(state, tree, effects))
    button.innerText = f"Advance to {sim.ERA_LABEL[next_era]}"
    button.disabled = not ready


def on_advance_era(event=None):
    if transition.attempt_transition(campaign):
        render()


def render_info_page():
    """The collapsed-by-default real-world-sources panel (Milestone 5).

    Rendering itself is the same shared/info_page.py used by all 8 climate
    quartet games — Continuum's only addition is picking which era's
    content dict to hand it, via info_content.era_info_page(), so the
    panel always shows sources for whatever era the settlement is
    currently in (including while revisiting a completed one) without
    this function needing to change as later eras ship.
    """
    info_page.render(info_content.era_info_page(state.era), info_page_open)


def on_toggle_info_page(event=None):
    global info_page_open
    info_page_open = info_page.toggle(info_page_open)
    render_info_page()


# Rendered entries, newest first, capped independently of how many
# Chronicle keeps for the save file (`log.MAX_ENTRIES`) so a long session
# doesn't grow the DOM without bound.
LOG_VISIBLE_ENTRIES = 20


def render_log():
    """The ongoing log (Milestone 6) — lightweight, skippable flavor text
    triggered by research unlocks, population thresholds, and livability
    shifts (which double as this game's diegetic feedback, per the design
    doc's Core system 4 — see log.py). Always visible, never a popup;
    rebuilt from `chronicle.entries` the same way render_research() rebuilds
    the research panel from the tree, for the same reason: a session's
    worth of rows can't be static markup.
    """
    document.getElementById("log-status-display").innerText = (
        f"{len(chronicle.entries)} entries"
    )

    container = document.getElementById("log-list")
    container.innerHTML = ""

    if not chronicle.entries:
        empty = document.createElement("p")
        empty.className = "row-blurb"
        empty.innerText = "Nothing to report yet."
        container.appendChild(empty)
        return

    for entry in reversed(chronicle.entries[-LOG_VISIBLE_ENTRIES:]):
        row = document.createElement("div")
        row.className = f"row log-row log-row--{entry.kind}"

        top = document.createElement("div")
        top.className = "row-top"
        tag = document.createElement("span")
        tag.className = "row-name"
        tag.innerText = f"{sim.ERA_LABEL.get(entry.era, entry.era)} · Season {entry.season}"
        top.appendChild(tag)
        row.appendChild(top)

        text = document.createElement("p")
        text.className = "row-blurb"
        text.innerText = entry.text
        row.appendChild(text)

        container.appendChild(row)


def render_sustainability(effects):
    """The score panel — visible from season 1 of the first era, by design."""
    reading = sustainability.evaluate(state, effects)
    value = reading["score"]

    document.getElementById("score-display").innerText = (
        f"Sustainability: {value:.0f} / 100 — {sustainability.score_label(value)}"
    )
    document.getElementById("score-bar").style.width = f"{value:.0f}%"

    weakest = sustainability.weakest_component(state, effects)
    for component in sustainability.COMPONENTS:
        element = document.getElementById(f"{component}-display")
        element.innerText = (
            f"{sustainability.COMPONENT_LABEL[component]}: "
            f"{reading['components'][component]:.0f}"
        )
        element.className = (
            "component-line component-line--weakest"
            if component == weakest
            else "component-line"
        )

    document.getElementById("score-note-display").innerText = sustainability.score_note(
        state, effects
    )


# Study-button click handlers, keyed by node_id. render_research() rebuilds
# every row (and mints a fresh create_proxy() for every unresearched node)
# on every render; a Pyodide proxy isn't garbage-collected on its own, so
# without tracking the previous render's proxy here and destroying it before
# its replacement is created, they'd accumulate unboundedly for the life of
# the page — a real, slow memory leak over a play session.
_research_button_proxies = {}


def render_research():
    """The research panel, rebuilt from the tree each render.

    Node rows are built in code rather than written into index.html: the
    tree runs to fourteen tiers across seven eras, so static markup for it
    would be unmaintainable long before the Space Age. Locked nodes are
    listed too, with the reason they're locked — a tree the player can't
    see the shape of isn't a tree.
    """
    document.getElementById("research-status-display").innerText = (
        f"Knowledge: {state.resources['knowledge']:.1f} — "
        f"{len(tree.researched)} discoveries made"
    )

    container = document.getElementById("research-list")
    container.innerHTML = ""

    live_node_ids = set()
    for node in tree.visible_nodes():
        researched = tree.is_researched(node.node_id)
        available = tree.is_available(node.node_id)

        row = document.createElement("div")
        row.className = "row research-row"
        if researched:
            row.className = "row research-row research-row--done"
        elif not available:
            row.className = "row research-row research-row--locked"

        top = document.createElement("div")
        top.className = "row-top"
        name = document.createElement("span")
        name.className = "row-name"
        name.innerText = ("✓ " if researched else "") + node.name
        cost = document.createElement("span")
        cost.className = "row-count"
        cost.innerText = "—" if researched else f"{node.cost:.0f}"
        top.appendChild(name)
        top.appendChild(cost)
        row.appendChild(top)

        meta = document.createElement("p")
        meta.className = "research-meta"
        meta.innerText = f"{research.BRANCH_LABEL[node.branch]} · Tier {node.tier}"
        row.appendChild(meta)

        blurb = document.createElement("p")
        blurb.className = "row-blurb"
        blurb.innerText = node.blurb
        row.appendChild(blurb)

        if not researched and not available:
            reasons = document.createElement("p")
            reasons.className = "research-locked-reason"
            reasons.innerText = " ".join(tree.missing_requirements(node.node_id))
            row.appendChild(reasons)

        actions = document.createElement("div")
        actions.className = "row-actions"
        button = document.createElement("button")
        button.id = f"research-{node.node_id}"
        button.className = "secondary"
        if researched:
            button.innerText = "Known"
            button.disabled = True
        else:
            button.innerText = f"Study ({node.cost:.0f})"
            button.disabled = not (available and tree.can_afford(node.node_id, state.resources))
            live_node_ids.add(node.node_id)
            proxy = create_proxy(_make_research_handler(node.node_id))
            stale = _research_button_proxies.get(node.node_id)
            if stale is not None:
                stale.destroy()
            _research_button_proxies[node.node_id] = proxy
            button.addEventListener("click", proxy)
        actions.appendChild(button)
        row.appendChild(actions)

        container.appendChild(row)

    # Nodes that no longer need a Study button this render (just researched,
    # or no longer visible) still have their old proxy sitting in the
    # tracking dict — destroy and drop it rather than leaking it forever.
    for node_id in list(_research_button_proxies):
        if node_id not in live_node_ids:
            _research_button_proxies.pop(node_id).destroy()


# --- handlers ----------------------------------------------------------
def _make_assign_handler(role):
    def handler(event=None):
        state.assign_worker(role)
        render()
    return handler


def _make_unassign_handler(role):
    def handler(event=None):
        state.unassign_worker(role)
        render()
    return handler


def _make_build_handler(building):
    def handler(event=None):
        state.build(building)
        render()
    return handler


def _make_research_handler(node_id):
    def handler(event=None):
        tree.research(node_id, state.resources)
        chronicle.check_research(state, tree)
        render()
    return handler


def on_advance_season(event=None):
    effects = current_effects()
    state.advance_season(effects)
    state.score_history.append(sustainability.score(state, effects))
    chronicle.check_population(state)
    chronicle.check_livability(state, effects)
    render()


# --- the shared save widget's contract ---------------------------------
# SAVE-BUTTON-INTEGRATION.md: shared/save-widget.js drives every game in the
# hub through exactly these two functions and never looks inside the dict,
# so Continuum's era-snapshot/revisit structure needs no widget changes —
# see save.py for the schema itself.
def get_state():
    campaign.ui["info_page_open"] = info_page_open
    return campaign.to_dict()


def load_state(data):
    global info_page_open
    if not campaign.load_dict(data):
        return False
    info_page_open = bool(campaign.ui.get("info_page_open", False))
    render()
    return True


def setup():
    # Work/Build row buttons are wired inside render_work()/render_buildings()
    # themselves now (Milestone 8) — those rows are rebuilt every render, the
    # same as the research panel's Study buttons already were, so wiring them
    # here would just be wiring buttons that don't exist yet.
    document.getElementById("advance-season-button").addEventListener(
        "click", create_proxy(on_advance_season)
    )
    document.getElementById("info-page-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_info_page)
    )
    document.getElementById("advance-era-button").addEventListener(
        "click", create_proxy(on_advance_era)
    )
    render()


setup()
