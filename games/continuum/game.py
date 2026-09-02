"""Continuum — a sustainable city across the ages.

Runs in-browser via Pyodide. This file is the browser layer only: it owns
the DOM, the event handlers, and the rendering. All of the actual thinking
lives in the engine modules that sit beside it —

    sim.py             city simulation core (population, resources, land)
    sustainability.py  the livability score (Milestone 2)
    research.py        the research tree engine (Milestone 3)
    save.py            the continuous-save / era-snapshot schema (Milestone 4)

— which is the separation the design doc's tech notes ask for, so that six
more eras of content land in the engines rather than in one tangled file.

Milestone 1: the Tribal-era season loop.
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

import research  # noqa: E402
import sim  # noqa: E402
import sustainability  # noqa: E402

from js import document  # noqa: E402
from pyodide.ffi import create_proxy  # noqa: E402


state = sim.CityState()
tree = research.build_tree(current_era=state.era)


def current_effects():
    """The aggregate modifiers applied to the simulation this season.

    The single seam through which research reaches both the simulation and
    the sustainability score — nothing else in the game reads the tree.
    """
    return tree.effects()


# --- narration ---------------------------------------------------------
def season_report_message(report):
    """One plain-language line summarising the season that just passed."""
    if report is None:
        return "The settlement is waiting on your word."

    parts = []
    if report["fed_fraction"] >= 1.0:
        parts.append("Everyone ate.")
    elif report["fed_fraction"] <= 0.0:
        parts.append("Nobody ate.")
    else:
        parts.append(f"Only {report['fed_fraction'] * 100:.0f}% of the settlement ate.")

    if report["deaths"]:
        parts.append(f"{report['deaths']} lost to hunger.")
    if report["births"]:
        parts.append(f"{report['births']} born.")
    if report["spoiled"] > 0.5:
        parts.append(f"{report['spoiled']:.0f} food spoiled for want of storage.")
    if report["extraction"] > report["sustainable_yield"]:
        parts.append("The land is being taken from faster than it recovers.")

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

    document.getElementById("land-health-display").innerText = (
        f"Land health: {state.land_health * 100:.0f}% — {land_health_message(state.land_health)}"
    )
    document.getElementById("land-health-bar").style.width = f"{state.land_health * 100:.0f}%"

    idle = state.idle_workers()
    for role in sim.ROLES:
        document.getElementById(f"{role}-count").innerText = str(state.allocation[role])
        document.getElementById(f"{role}-add-button").disabled = idle <= 0
        document.getElementById(f"{role}-remove-button").disabled = state.allocation[role] <= 0

    for building in sim.BUILDINGS:
        document.getElementById(f"{building}-count").innerText = str(state.buildings[building])
        button = document.getElementById(f"{building}-build-button")
        button.innerText = f"Build ({sim.BUILDING_COST[building]:.0f})"
        button.disabled = not state.can_build(building)

    document.getElementById("season-report-display").innerText = season_report_message(
        state.last_report
    )

    render_sustainability(effects)
    render_research()


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
            button.addEventListener("click", create_proxy(_make_research_handler(node.node_id)))
        actions.appendChild(button)
        row.appendChild(actions)

        container.appendChild(row)


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
        render()
    return handler


def on_advance_season(event=None):
    effects = current_effects()
    state.advance_season(effects)
    state.score_history.append(sustainability.score(state, effects))
    render()


def setup():
    for role in sim.ROLES:
        document.getElementById(f"{role}-add-button").addEventListener(
            "click", create_proxy(_make_assign_handler(role))
        )
        document.getElementById(f"{role}-remove-button").addEventListener(
            "click", create_proxy(_make_unassign_handler(role))
        )
    for building in sim.BUILDINGS:
        document.getElementById(f"{building}-build-button").addEventListener(
            "click", create_proxy(_make_build_handler(building))
        )
    document.getElementById("advance-season-button").addEventListener(
        "click", create_proxy(on_advance_season)
    )
    render()


setup()
