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
    visual.py          state -> visual data contract for the Three.js layer (Phase 5)

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

import json
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
import visual  # noqa: E402

from js import document, setTimeout  # noqa: E402
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

# Milestone 17 (K14) — the research tree search/filter query. Transient UI
# state, not saved: unlike info_page_open (which rides campaign.ui because
# a toggle's open/closed state is worth restoring on load), a text query
# has no reason to survive a reload, so it's a plain module-level string,
# always "" on a fresh module load. achievements_open (below) is the same
# category — also never saved.
research_search_query = ""


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
    # Industrial+ (Milestone 11): unlike every earlier narration line above,
    # this one calls out a real GROWTH consequence, not only a resource or
    # resilience one -- pollution is directly slowing next season's growth,
    # per the Economic Journal source's "measurably reduced long-run city
    # growth" finding (see sim.py's pollution constants and
    # sustainability._industrial_pollution_penalty()).
    if report.get("pollution", 0.0) > 0.3:
        parts.append(
            f"Industrial smoke hangs over the settlement ({report['pollution'] * 100:.0f}% "
            "pollution) — growth is slower for it, and it isn't doing the sustainability "
            "score any favors either."
        )
    # Digital+ (Milestone 12): a second growth-adjacent narration line,
    # deliberately worded differently from pollution's above -- sprawl
    # doesn't slow growth directly, it makes the SAME extraction land
    # harder on the land (see sim.py's SPRAWL_EXTRACTION_PENALTY_WEIGHT),
    # which is what actually threatens growth if it pushes land health down
    # far enough.
    if report.get("sprawl", 0.0) > 0.3:
        parts.append(
            f"The settlement is spreading out faster than it's filling in ({report['sprawl'] * 100:.0f}% "
            "sprawl) — the same production is leaning harder on the land for it, and it isn't "
            "doing the sustainability score any favors either."
        )
    # Space Age+ (Milestone 13): unlike every narration line above,
    # habitat_layout_ratio isn't a lagged stock that builds up over time --
    # it's a coverage ratio recomputed fresh each season from current rings/
    # architects, the same shape Classical's canal-staffing line and
    # Medieval's public-works-coverage line already narrate. Only narrated
    # once there's at least one ring built to have an opinion about, the
    # same "only narrate a real gap" discipline those two lines follow.
    if report.get("habitat_rings", 0) > 0 and report.get("habitat_layout_ratio", 1.0) < 1.0:
        layout_pct = report["habitat_layout_ratio"] * 100
        parts.append(
            f"Off-world habitat layout is only serving {layout_pct:.0f}% of the settlement well — "
            "the rest live somewhere the design doesn't really work for them."
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
    render_revisit()
    update_achievements_display()
    _notify_visual_layer()


def get_visual_state():
    """Phase 5's data contract for the Three.js render layer — see
    visual.py. Exposed as a plain module-level function (same shape as
    get_state()/load_state() below) so render3d.js can call it through
    Pyodide's globals the same way the shared save widget calls those two.
    Returns a plain dict; pyodide's toJs() (called from JS) turns it into
    a plain JS object, mirroring the save widget's own contract.
    """
    return visual.visual_state(state, current_effects())


def _notify_visual_layer():
    """Tells render3d.js the 2D state just moved, so it can redraw the 3D
    scene to match — called at the end of every render(), i.e. after any
    assignment, build, research, season-advance, era-transition, or
    save/load.

    Deliberately lazy and defensive, the same `getattr(window, name, None)`
    pattern champ-de-mots' own `_dispatch_report()` uses for its network
    call: `js.window` doesn't exist under the pytest fake-DOM harness (only
    `js.document` is faked — see tests/conftest.py), so this is a silent
    no-op there, and it's equally a silent no-op in a real browser whenever
    render3d.js hasn't installed the hook — Three.js failed to load, WebGL
    isn't available, or the player has switched to the 2D fallback view.
    The 2D UI's own render() must never depend on this call succeeding,
    which is exactly why this function swallows both failure modes instead
    of asserting either dependency exists.
    """
    try:
        from js import window
    except ImportError:
        return
    hook = getattr(window, "continuumOnRender", None)
    if hook is not None:
        hook()


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

    if campaign.revisiting is not None:
        era_label = sim.ERA_LABEL[campaign.revisiting]
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
        revisitable = campaign.revisitable_eras()
        status.innerText = (
            "No completed eras to look back on yet — finish your first era transition."
            if not revisitable
            else "Completed eras you can look back on:"
        )

    container.innerHTML = ""
    live_eras = set()
    if campaign.revisiting is None:
        for era in campaign.revisitable_eras():
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

            container.appendChild(row)

    for era in list(_revisit_button_proxies):
        if era not in live_eras:
            _revisit_button_proxies.pop(era).destroy()


def _make_enter_revisit_handler(era):
    def handler(event=None):
        if campaign.enter_revisit(era):
            render()
            _check_new_achievements_for_toast()
    return handler


def on_exit_revisit(event=None):
    if campaign.exit_revisit():
        render()


# ===========================================================================
# Achievements (ACHIEVEMENTS-SYSTEM-DESIGN.md) — following SOL's reference
# integration exactly. See CLAUDE.md's Milestone 15 build notes for the
# full catalog-design reasoning.
# ===========================================================================
#
# "Derive, don't track" holds for every entry here: every achievement is a
# pure function of state this game already persists (era progress via
# campaign.furthest_era, the full score_history, the research tree's own
# researched list, and the season loop's own last_report ratios) — no new
# tracked state was needed except `campaign.has_revisited` (save.py), added
# via the same five-step defensive pattern SOL's own visited_bodies used
# (safe default, mutated only at the real event, saved, defensive fallback
# on load, no backfill needed here since no pre-existing save could already
# be "mid-revisit but the flag says no").
ACHIEVEMENTS_FILENAME = "achievements.json"


def _read_achievements_json():
    """Same loading contract as SOL's `_read_achievements_json()`/Le Champ
    de Mots' `_read_json_asset()`: the boot script fetches achievements.json
    and hands it to Python as a window global before this file runs; the
    pytest harness's fake `js` module has no such attribute, so this falls
    through to reading the file straight off disk."""
    try:
        import js  # noqa: PLC0415 — Pyodide-only import, deliberately lazy
    except ImportError:
        js = None

    raw = getattr(js, "ACHIEVEMENTS_JSON", None) if js is not None else None
    if raw is not None:
        return str(raw)

    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, ACHIEVEMENTS_FILENAME), encoding="utf-8") as handle:
        return handle.read()


# Defensive per SOL's own note: achievements are additive, not core
# gameplay, so a boot-script regression here degrades to "no achievements
# catalog" rather than taking down the whole module import.
try:
    ACHIEVEMENTS = json.loads(_read_achievements_json())["achievements"]
except (ValueError, OSError, NameError, KeyError):
    ACHIEVEMENTS = []

# Branch-depth threshold for the three "Tradition" achievements — roughly
# half of any one branch's ~14-16 nodes (see CLAUDE.md), deep enough to
# mean real, sustained investment in one branch rather than a few early
# freebies.
BRANCH_SPECIALIST_THRESHOLD = 8
EQUITY_CHAMPION_MIN_POPULATION = 25
A_REAL_CITY_POPULATION = 100
# sustainability.components() returns each component on a 0..1 scale, NOT
# the 0..100 scale evaluate()/the UI display (evaluate() multiplies by 100
# for the headline readout) -- a real bug caught by this milestone's own
# test suite before it shipped (both thresholds below were first written as
# 90/85, which no settlement could ever satisfy). Named here, once, so a
# future edit can't reintroduce the same off-by-100 mistake by hand.
EQUITY_CHAMPION_MIN_EQUITY = 0.90
BUILT_TO_LAST_MIN_RESILIENCE = 0.85


def _ever_thriving():
    if state.score_history and max(state.score_history) >= 85:
        return True
    return sustainability.score(state, current_effects()) >= 85


def _ever_recovered_from_collapse():
    """True if the score ever fell into Collapsing (<30) and later, at some
    later point in the same history, recovered to Steady or better (>=70).
    Reads state.score_history — one entry per completed season, in order,
    never truncated — so this is a real historical check, not a live one,
    unlike several of the checks below that only have a live signal to
    read."""
    lowest_seen = None
    for value in state.score_history:
        if lowest_seen is not None and lowest_seen < 30 and value >= 70:
            return True
        if lowest_seen is None or value < lowest_seen:
            lowest_seen = value
    return False


def _era_reached(era):
    return sim.era_index(campaign.furthest_era) >= sim.era_index(era)


def _full_coordination():
    report = state.last_report or {}
    return report.get("canals", 0) > 0 and report.get("canal_staffing_ratio", 0.0) >= 1.0


def _nobody_exposed():
    report = state.last_report or {}
    return report.get("public_works", 0) > 0 and report.get("public_works_coverage_ratio", 0.0) >= 1.0


def _well_designed_rings():
    report = state.last_report or {}
    return report.get("habitat_rings", 0) > 0 and report.get("habitat_layout_ratio", 0.0) >= 1.0


# Each checker is a zero-argument predicate read fresh off live state —
# nothing here is cached or hand-flagged, matching SOL's own discipline.
ACHIEVEMENT_CHECKS = {
    "reached_agrarian": lambda: _era_reached("agrarian"),
    "reached_classical": lambda: _era_reached("classical"),
    "reached_medieval": lambda: _era_reached("medieval"),
    "reached_industrial": lambda: _era_reached("industrial"),
    "reached_digital": lambda: _era_reached("digital"),
    "reached_space": lambda: _era_reached("space"),
    "thriving_once": _ever_thriving,
    "phoenix_settlement": _ever_recovered_from_collapse,
    "provision_specialist": lambda: tree.affinity("provision") >= BRANCH_SPECIALIST_THRESHOLD,
    "community_specialist": lambda: tree.affinity("community") >= BRANCH_SPECIALIST_THRESHOLD,
    "craft_specialist": lambda: tree.affinity("craft") >= BRANCH_SPECIALIST_THRESHOLD,
    "root_and_branch": lambda: len(tree.researched) >= len(tree.nodes),
    "equity_champion": lambda: (
        state.population >= EQUITY_CHAMPION_MIN_POPULATION
        and sustainability.components(state, current_effects())["equity"] >= EQUITY_CHAMPION_MIN_EQUITY
    ),
    "built_to_last": lambda: (
        sustainability.components(state, current_effects())["resilience"] >= BUILT_TO_LAST_MIN_RESILIENCE
    ),
    "full_coordination": _full_coordination,
    "nobody_exposed": _nobody_exposed,
    "well_designed_rings": _well_designed_rings,
    "a_real_city": lambda: state.population >= A_REAL_CITY_POPULATION,
    "looking_back": lambda: campaign.has_revisited,
}

# Progress readouts, only for achievements with a natural numeric scale-up —
# a plain earned/not-yet is the honest shape for the rest (era-reached,
# phoenix, the coordination/coverage achievements are all one-shot).
ACHIEVEMENT_PROGRESS = {
    "provision_specialist": lambda: (tree.affinity("provision"), BRANCH_SPECIALIST_THRESHOLD),
    "community_specialist": lambda: (tree.affinity("community"), BRANCH_SPECIALIST_THRESHOLD),
    "craft_specialist": lambda: (tree.affinity("craft"), BRANCH_SPECIALIST_THRESHOLD),
    "root_and_branch": lambda: (len(tree.researched), len(tree.nodes)),
    "a_real_city": lambda: (state.population, A_REAL_CITY_POPULATION),
}


def achievement_ids_earned():
    """Every achievement id currently satisfied, in catalog order — the
    value that rides the existing save/sync mechanism via get_state()'s
    "achievements_earned" field. Always recomputed, never itself a save
    input (see get_state() below)."""
    return [entry["id"] for entry in ACHIEVEMENTS if ACHIEVEMENT_CHECKS[entry["id"]]()]


def achievements_summary():
    """The full catalog, in order, each annotated with earned status and
    (where one exists) a live progress readout."""
    earned_ids = set(achievement_ids_earned())
    summary = []
    for entry in ACHIEVEMENTS:
        progress_fn = ACHIEVEMENT_PROGRESS.get(entry["id"])
        summary.append(
            {
                "id": entry["id"],
                "label": entry["label"],
                "description": entry["description"],
                "earned": entry["id"] in earned_ids,
                "progress": progress_fn() if progress_fn else None,
            }
        )
    return summary


achievements_open = False


def on_toggle_achievements(event=None):
    global achievements_open
    achievements_open = not achievements_open
    update_achievements_display()


def update_achievements_display():
    toggle = document.getElementById("achievements-toggle-button")
    panel = document.getElementById("achievements-panel")
    earned_count = len(achievement_ids_earned())
    toggle.innerText = (
        f"Hide Achievements ({earned_count}/{len(ACHIEVEMENTS)})"
        if achievements_open
        else f"🏆 Achievements ({earned_count}/{len(ACHIEVEMENTS)})"
    )
    panel.hidden = not achievements_open
    if not achievements_open:
        return

    panel.innerHTML = ""
    for entry in achievements_summary():
        card = document.createElement("div")
        card.className = "achievement-card achievement-card--earned" if entry["earned"] else "achievement-card"

        label = document.createElement("p")
        label.className = "achievement-card-label"
        label.innerText = f"🏆 {entry['label']}" if entry["earned"] else entry["label"]
        card.appendChild(label)

        description = document.createElement("p")
        description.className = "achievement-card-description"
        description.innerText = entry["description"]
        card.appendChild(description)

        if not entry["earned"] and entry["progress"] is not None:
            current, target = entry["progress"]
            progress = document.createElement("p")
            progress.className = "achievement-card-progress"
            progress.innerText = f"{current} of {target}"
            card.appendChild(progress)

        panel.appendChild(card)

    # Hub-dashboard link (ACHIEVEMENTS-SYSTEM-DESIGN.md §5) — signed-in
    # players can see Continuum's progress alongside every other game's
    # there. Relative path, no leading "/" (site-level milestone 7's
    # GitHub Pages subpath fix), rebuilt each open since the panel is
    # cleared first.
    hub_link = document.createElement("a")
    hub_link.innerText = "View the hub-wide achievements dashboard →"
    hub_link.href = "../../index.html#account-achievements-dashboard"
    hub_link.className = "achievements-hub-link"
    panel.appendChild(hub_link)


# --- unlock toast ---------------------------------------------------------
# A snapshot of which achievement ids were already earned as of the last
# seed point, so an action handler's post-render check can tell "newly
# earned by that action" apart from "already earned before this page/save
# load" and only toast for the former. Seeded (never diffed against empty)
# by setup() and load_state() — never by render() itself, since render() is
# also what setup()/load_state() call before seeding — so a save that
# already has several achievements earned never floods the player with a
# toast per achievement the instant it loads.
_achievements_seen_ids = set()


def _seed_achievement_toast_baseline():
    global _achievements_seen_ids
    _achievements_seen_ids = set(achievement_ids_earned())


def _display_toast(message):
    toast = document.getElementById("achievement-toast")
    text = document.getElementById("achievement-toast-text")
    text.innerText = message
    toast.hidden = False
    toast.classList.add("visible")

    def _hide(*args):
        toast.hidden = True
        toast.classList.remove("visible")
        proxy.destroy()

    proxy = create_proxy(_hide)
    setTimeout(proxy, 4000)


def _check_new_achievements_for_toast():
    """Called after render() from every action handler that could plausibly
    newly earn an achievement (assign/unassign/build/research/season
    advance/era transition/enter revisit) — never from render() itself, for
    the same reason _seed_achievement_toast_baseline() above exists."""
    global _achievements_seen_ids
    earned_now = set(achievement_ids_earned())
    newly = earned_now - _achievements_seen_ids
    if newly:
        by_id = {entry["id"]: entry for entry in ACHIEVEMENTS}
        labels = [by_id[aid]["label"] for aid in newly if aid in by_id]
        if labels:
            if len(labels) == 1:
                _display_toast(f"🏆 Achievement unlocked: {labels[0]}")
            else:
                _display_toast(f"🏆 {len(labels)} achievements unlocked: " + ", ".join(labels))
    _achievements_seen_ids = earned_now


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

# Phase 5 colorblind-safety audit: log.py's "livability-up"/"livability-
# down" kinds used to be told apart only by their .log-row--* border color
# (see style.css) — a plain green/red pair, which is exactly the hue
# distinction deuteranopia/protanopia can't reliably make. This icon
# prefix is a second, color-independent signal for the same distinction,
# the same "decoration, not data" role sim.ROLE_EMOJI already plays for
# the Work panel. Every other kind is left unprefixed (research/population/
# transition already read unambiguously from their own text).
LOG_KIND_ICON = {
    "livability-up": "▲ ",
    "livability-down": "▼ ",
}


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
        icon = LOG_KIND_ICON.get(entry.kind, "")
        tag.innerText = f"{icon}{sim.ERA_LABEL.get(entry.era, entry.era)} · Season {entry.season}"
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

    query = research_search_query.strip().lower()
    live_node_ids = set()
    any_rendered = False
    for node in tree.visible_nodes():
        if query and not _research_node_matches(node, query):
            continue
        any_rendered = True
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

    if query and not any_rendered:
        empty = document.createElement("p")
        empty.className = "row-blurb"
        empty.innerText = f'No research nodes match "{research_search_query.strip()}".'
        container.appendChild(empty)

    # Nodes that no longer need a Study button this render (just researched,
    # no longer visible, or filtered out by the search box) still have
    # their old proxy sitting in the tracking dict — destroy and drop it
    # rather than leaking it forever. A filtered-out node is deliberately
    # never given a fresh proxy in the loop above, so it can't leak a live
    # listener behind an invisible row either.
    for node_id in list(_research_button_proxies):
        if node_id not in live_node_ids:
            _research_button_proxies.pop(node_id).destroy()


def _research_node_matches(node, query):
    """K14 — the research tree search/filter. Matches against the node's
    name, blurb, and branch label, case-insensitively; `query` is already
    lower-cased and stripped by the caller."""
    haystack = f"{node.name} {node.blurb} {research.BRANCH_LABEL[node.branch]}".lower()
    return query in haystack


# --- handlers ----------------------------------------------------------
def _make_assign_handler(role):
    def handler(event=None):
        state.assign_worker(role)
        render()
        _check_new_achievements_for_toast()
    return handler


def _make_unassign_handler(role):
    def handler(event=None):
        state.unassign_worker(role)
        render()
        _check_new_achievements_for_toast()
    return handler


def _make_build_handler(building):
    def handler(event=None):
        state.build(building)
        render()
        _check_new_achievements_for_toast()
    return handler


def _make_research_handler(node_id):
    def handler(event=None):
        tree.research(node_id, state.resources)
        chronicle.check_research(state, tree)
        render()
        _check_new_achievements_for_toast()
    return handler


def on_advance_season(event=None):
    effects = current_effects()
    state.advance_season(effects)
    state.score_history.append(sustainability.score(state, effects))
    chronicle.check_population(state)
    chronicle.check_livability(state, effects)
    render()
    _check_new_achievements_for_toast()


# --- the shared save widget's contract ---------------------------------
# SAVE-BUTTON-INTEGRATION.md: shared/save-widget.js drives every game in the
# hub through exactly these two functions and never looks inside the dict,
# so Continuum's era-snapshot/revisit structure needs no widget changes —
# see save.py for the schema itself.
def get_state():
    campaign.ui["info_page_open"] = info_page_open
    data = campaign.to_dict()
    # Milestone 15 (ACHIEVEMENTS-SYSTEM-DESIGN.md): a write-only projection,
    # not part of Campaign's own save schema — always recomputed fresh here,
    # never read back in load_state() below.
    data["achievements_earned"] = achievement_ids_earned()
    return data


def load_state(data):
    global info_page_open
    if not campaign.load_dict(data):
        return False
    info_page_open = bool(campaign.ui.get("info_page_open", False))
    render()
    _seed_achievement_toast_baseline()
    return True


def on_research_search_input(event=None):
    global research_search_query
    research_search_query = document.getElementById("research-search-input").value
    render_research()


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
    document.getElementById("achievements-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_achievements)
    )
    document.getElementById("exit-revisit-button").addEventListener(
        "click", create_proxy(on_exit_revisit)
    )
    document.getElementById("research-search-input").addEventListener(
        "input", create_proxy(on_research_search_input)
    )
    # Belt-and-suspenders: the toast starts hidden via the static `hidden`
    # attribute in index.html, but every other stateful element in this
    # file (panels, buttons) has its shown/hidden state actively driven by
    # code rather than left to rely on markup alone — setting it here too
    # means the toast's default state doesn't depend on the static HTML
    # attribute ever being present or correct.
    document.getElementById("achievement-toast").hidden = True
    render()
    _seed_achievement_toast_baseline()


setup()
