"""The optional Hamlet view (U2) and the Desktop HUD chips: capability checks, chips, town panel and render_hamlet."""

from js import document
from pyodide.ffi import create_proxy

import challenges
import forecast
import hamlet
import naming
import research
import sim
import sustainability
import transition

import continuum_runstate as runstate
from continuum_base import _js_window, _pc_layout, current_effects
from continuum_founders import settlement_name
from continuum_panels import (
    _make_assign_handler, _make_build_handler, _make_research_handler, _make_unassign_handler,
)
from continuum_progress import on_advance_era
from continuum_scenario import _scenario_locked
from continuum_views import _make_start_challenge_handler, on_abandon_challenge

render = None  # placeholder: continuum_renderer fills this in when it is imported (it comes later)

# ===========================================================================
# U2: the optional Hamlet view (desktop only, off by default).
#
# A "Hearth and Hamlet"-style way to play: the controls live INSIDE the
# scene as clickable buildings, one per "thing" (see hamlet.py for the
# station list and what a station is), instead of the Work / Build /
# Research panels. This whole section is the DOM half; it owns no game
# rules. Every button below is wired to the exact same handler factory the
# ordinary panels use (`_make_assign_handler`, `_make_unassign_handler`,
# `_make_build_handler`, `_make_research_handler`,
# `_make_start_challenge_handler`, `on_advance_era`, ...), wrapped only to
# say what happened to a screen reader.
#
# Design calls worth knowing:
#   - The overlay is plain DOM (real <button>s), not 3D picking. hamlet.js
#     projects each chip onto its building in the 3D scene and also lets a
#     click on the 3D building itself press that same button, so mouse,
#     keyboard and screen reader all go through one code path. With no
#     WebGL, or with the 2D view chosen, the chips simply sit at their flat
#     top-down positions (the percentages set below) -- the mode still works.
#   - Chips are built once per era and then UPDATED IN PLACE on every
#     render. Seasons now tick on a clock, so a rebuild-everything render
#     would drop keyboard focus every few seconds.
#   - The ordinary Work / Build / Research / Civic / Era Progress panels are
#     hidden by CSS (the `hamlet-on` class on #game), not removed: they keep
#     rendering underneath, so switching the mode off is instant and lossless.
#   - A browser preference (localStorage), not part of the save, same category
#     as the text-size and reduce-motion settings.
# ===========================================================================
HAMLET_STORAGE_KEY = "continuum-hamlet-view"
# Wide enough to hold the stage, and a mouse-like pointer: this is a
# desktop-only pilot, so a phone or a touch tablet never sees the toggle.
HAMLET_MEDIA_QUERY = "(min-width: 960px) and (hover: hover) and (pointer: fine)"

_hamlet_els = {}           # station id -> dict of that chip's elements
_hamlet_proxies = []       # click proxies for the chips (destroyed on rebuild)

_hamlet_town_proxies = []
_hamlet_town_els = {}


def _hamlet_storage_get():
    window = _js_window()
    if window is None:
        return None
    try:
        return window.localStorage.getItem(HAMLET_STORAGE_KEY)
    except Exception:
        return None


def _hamlet_storage_set(value):
    window = _js_window()
    if window is None:
        return False
    try:
        window.localStorage.setItem(HAMLET_STORAGE_KEY, value)
        return True
    except Exception:
        return False


def _hamlet_capable():
    """True when this browser can host the hamlet: a desktop-class screen
    and pointer. Without a `window` (the test harness) it is simply True."""
    window = _js_window()
    if window is None:
        return True
    try:
        return bool(window.matchMedia(HAMLET_MEDIA_QUERY).matches)
    except Exception:
        return False


def hamlet_active():
    return runstate.hamlet_on and _hamlet_capable()


def on_toggle_hamlet(event=None):
    runstate.hamlet_on = not runstate.hamlet_on
    _hamlet_storage_set("on" if runstate.hamlet_on else "off")
    render()
    _hamlet_say(
        "Hamlet view on. Click a building to use it." if hamlet_active()
        else "Hamlet view off."
    )


def on_hamlet_capability_change(event=None):
    """Called by hamlet.js when the screen crosses the desktop threshold
    (a resized window), so the mode switches on or off without a reload."""
    render()


def _hamlet_say(text):
    """One short line into the polite live region."""
    try:
        document.getElementById("hamlet-live").innerText = text
    except KeyError:
        pass


def _hamlet_el(tag, cls=None, text=None, element_id=None):
    element = document.createElement(tag)
    if cls:
        element.className = cls
    if text is not None:
        element.innerText = text
    if element_id:
        element.id = element_id
    return element


def _hamlet_wire(button, handler):
    proxy = create_proxy(handler)
    _hamlet_proxies.append(proxy)
    button.addEventListener("click", proxy)


def _hamlet_set_blocked(button, blocked):
    """Blocked buttons stay focusable (aria-disabled, not `disabled`), so a
    keyboard or screen-reader user can still land on a building and hear why
    it cannot be used right now."""
    button.setAttribute("aria-disabled", "true" if blocked else "false")
    if blocked:
        button.classList.add("hamlet-blocked")
    else:
        button.classList.remove("hamlet-blocked")


def _make_hamlet_assign_handler(role, label):
    inner = _make_assign_handler(role)

    def handler(event=None):
        before = runstate.state.allocation[role]
        inner(event)
        after = runstate.state.allocation[role]
        _hamlet_say(
            f"{label}: {after} working." if after != before
            else f"No one is idle to assign to {label}."
        )
    return handler


def _make_hamlet_unassign_handler(role, label):
    inner = _make_unassign_handler(role)

    def handler(event=None):
        before = runstate.state.allocation[role]
        inner(event)
        after = runstate.state.allocation[role]
        _hamlet_say(
            f"{label}: {after} working." if after != before
            else f"Nobody is working at {label}."
        )
    return handler


def _make_hamlet_build_handler(building):
    inner = _make_build_handler(building)

    def handler(event=None):
        before = runstate.state.buildings[building]
        inner(event)
        after = runstate.state.buildings[building]
        label = sim.BUILDING_LABEL[building]
        _hamlet_say(
            f"Built {label}. You now have {after}." if after != before
            else f"Not enough materials for {label}: it costs {sim.BUILDING_COST[building]:.0f}."
        )
    return handler


def _make_hamlet_research_handler(node_id):
    inner = _make_research_handler(node_id)

    def handler(event=None):
        was_known = runstate.tree.is_researched(node_id)
        inner(event)
        name = runstate.tree.nodes[node_id].name
        _hamlet_say(
            f"Studied {name}." if (runstate.tree.is_researched(node_id) and not was_known)
            else f"Not enough knowledge to study {name} yet."
        )
    return handler


def _make_hamlet_town_handler():
    def handler(event=None):
        runstate.hamlet_town_open = not runstate.hamlet_town_open
        _hamlet_town_button_state()
        _hamlet_render_town(current_effects(), force=True)
        _hamlet_say("Town Centre open." if runstate.hamlet_town_open else "Town Centre closed.")
    return handler


def _hamlet_close_town(event=None):
    runstate.hamlet_town_open = False
    _hamlet_town_button_state()
    _hamlet_render_town(current_effects(), force=True)
    _hamlet_focus(f"hamlet-{hamlet.TOWN_ID}-main")


def _hamlet_town_button_state():
    els = _hamlet_els.get(hamlet.TOWN_ID)
    if els:
        els["main"].setAttribute("aria-expanded", "true" if runstate.hamlet_town_open else "false")
        if runstate.hamlet_town_open:
            els["chip"].classList.add("hamlet-chip--open")
        else:
            els["chip"].classList.remove("hamlet-chip--open")


def _hamlet_focus(element_id):
    """Puts keyboard focus back on `element_id` if it still exists."""
    try:
        target = document.getElementById(element_id)
        if target is not None:
            target.focus()
            return True
    except Exception:
        pass
    return False


def _hamlet_active_id():
    try:
        active = getattr(document, "activeElement", None)
        return active.id if active is not None and active.id else None
    except Exception:
        return None


def _hamlet_build_chips(stations):
    """(Re)builds every chip. Only runs when the set of stations changes,
    i.e. on entering the mode and on each new era."""
    for proxy in _hamlet_proxies:
        proxy.destroy()
    del _hamlet_proxies[:]
    _hamlet_els.clear()
    container = document.getElementById("hamlet-chips")
    container.innerHTML = ""

    for station in stations:
        sid = station["id"]
        chip = _hamlet_el("div", "hamlet-chip", element_id=f"hamlet-chip-{sid}")
        chip.setAttribute("role", "group")
        chip.setAttribute("data-station", sid)
        chip.setAttribute("data-shape", station["shape"])
        x, z = hamlet.position(station)
        chip.setAttribute("data-hx", str(x))
        chip.setAttribute("data-hz", str(z))
        chip.setAttribute("data-count", "0")

        main = _hamlet_el("button", "hamlet-main", element_id=f"hamlet-{sid}-main")
        main.setAttribute("type", "button")
        icon = _hamlet_el("span", "hamlet-icon", station["emoji"])
        icon.setAttribute("aria-hidden", "true")
        name = _hamlet_el("span", "hamlet-name", station["label"])
        count = _hamlet_el("span", "hamlet-count")
        main.appendChild(icon)
        main.appendChild(name)
        main.appendChild(count)
        chip.appendChild(main)

        sub = _hamlet_el("span", "hamlet-sub")
        els = {"chip": chip, "main": main, "count": count, "sub": sub,
               "unassign": None, "build": None}

        if station["kind"] == "town":
            _hamlet_wire(main, _make_hamlet_town_handler())
            main.setAttribute("aria-expanded", "false")
            main.setAttribute("aria-controls", "hamlet-town-panel")
            chip.appendChild(sub)
        else:
            role, building = station["role"], station["building"]
            if role:
                # A workplace: [-] [caption] [+ build cost, pairs only] under
                # the building, so the whole control sits in one compact row.
                actions = _hamlet_el("div", "hamlet-actions")
                _hamlet_wire(main, _make_hamlet_assign_handler(role, station["label"]))
                minus = _hamlet_el("button", "hamlet-mini", "−", f"hamlet-{sid}-unassign")
                minus.setAttribute("type", "button")
                minus.setAttribute("aria-label", f"Take one worker off {sim.ROLE_LABEL[role]}")
                _hamlet_wire(minus, _make_hamlet_unassign_handler(role, station["label"]))
                actions.appendChild(minus)
                els["unassign"] = minus
                actions.appendChild(sub)
                if building:
                    buy = _hamlet_el("button", "hamlet-mini hamlet-buy", "", f"hamlet-{sid}-build")
                    buy.setAttribute("type", "button")
                    _hamlet_wire(buy, _make_hamlet_build_handler(building))
                    actions.appendChild(buy)
                    els["build"] = buy
                chip.appendChild(actions)
            else:
                _hamlet_wire(main, _make_hamlet_build_handler(building))
                chip.appendChild(sub)
        _hamlet_els[sid] = els
        container.appendChild(chip)
    runstate._hamlet_built_key = tuple(s["id"] for s in stations)


def _hamlet_update_chips(stations, effects):
    for station in stations:
        view = hamlet.station_view(station, runstate.state, effects)
        els = _hamlet_els[station["id"]]
        chip, main = els["chip"], els["main"]
        els["count"].innerText = view["count_text"]
        els["sub"].innerText = view["sub_text"]
        els["sub"].hidden = not view["sub_text"]
        chip.setAttribute("data-count", str(view["count"] or 0))
        main.setAttribute("aria-label", view["aria_label"])
        main.title = view["title"]
        _hamlet_set_blocked(main, not view["primary_ok"])
        left, top = hamlet.flat_percent(view["x"], view["z"])
        chip.style.left = f"{left}%"
        chip.style.top = f"{top}%"
        chip.style.zIndex = str(int(50 + view["z"] * 10))
        if els["unassign"] is not None:
            _hamlet_set_blocked(els["unassign"], not view["can_unassign"])
        if els["build"] is not None:
            els["build"].innerText = f"＋{view['cost']:.0f}"
            els["build"].setAttribute(
                "aria-label",
                f"Build one more {sim.BUILDING_LABEL[station['building']]} for {view['cost']:.0f} materials",
            )
            _hamlet_set_blocked(els["build"], not view["can_build"])
    _hamlet_town_button_state()


def _hamlet_update_hud(effects):
    housing = runstate.state.housing_capacity(effects)
    score = sustainability.score(runstate.state, effects)
    label = sustainability.score_label(score, sustainability.is_hard_mode(runstate.state))
    resources = runstate.state.resources
    document.getElementById("hamlet-hud").innerText = (
        f"👥 {runstate.state.population}/{housing:.0f}  ·  🍖 {resources['food']:.0f}/"
        f"{runstate.state.food_storage_capacity(effects):.0f}  ·  🪵 {resources['materials']:.0f}  ·  "
        f"🔧 {resources['tools']:.1f}  ·  💡 {resources['knowledge']:.1f}  ·  "
        f"idle {runstate.state.idle_workers()}  ·  {sim.ERA_LABEL[runstate.state.era]}, season {runstate.state.season}  ·  "
        f"score {score:.0f} ({label})"
    )


# --- Desktop boot: the readouts as a HUD in the scene --------------------------------
# On the Desktop boot (pc.html) the side column of readouts is gone: the same numbers are
# drawn as a row of chips over the scene, and each chip opens a small dropdown with the
# detail and the trend ("+1 person per season"). The trend comes from forecast.py, a probe
# of the next season on a copy of the state, so it is exactly what the next season will do
# if nothing changes. The old readout elements keep updating (they are only moved out of
# the layout), and the Classic page never builds any of this.
PC_HUD_CHIPS = (
    ("population", "\U0001F465", "People"),
    ("food", "\U0001F356", "Food"),
    ("materials", "\U0001FAB5", "Materials"),
    ("tools", "\U0001F527", "Tools"),
    ("knowledge", "\U0001F4A1", "Knowledge"),
    ("sustainability", "\U0001F331", "Sustainability"),
)
_pc_hud_els = {}


def _pc_hud_build():
    stage = document.getElementById("hamlet-stage")
    bar = document.createElement("div")
    bar.id = "pc-hud"
    bar.className = "pc-hud"
    bar.setAttribute("role", "group")
    bar.setAttribute("aria-label", "Settlement readouts")
    for key, icon, label in PC_HUD_CHIPS:
        wrap = document.createElement("div")
        wrap.className = "pc-dropdown-wrap"
        toggle = document.createElement("button")
        toggle.type = "button"
        toggle.className = "pc-hud-chip"
        toggle.setAttribute("data-pc-dropdown", "1")
        toggle.setAttribute("aria-expanded", "false")
        toggle.setAttribute("aria-label", f"{label}: details and trend")
        icon_el = document.createElement("span")
        icon_el.className = "pc-hud-icon"
        icon_el.innerText = icon
        value_el = document.createElement("span")
        value_el.className = "pc-hud-value"
        caret = document.createElement("span")
        caret.className = "pc-hud-caret"
        caret.innerText = "\u25BE"
        toggle.appendChild(icon_el)
        toggle.appendChild(value_el)
        toggle.appendChild(caret)
        dropdown = document.createElement("div")
        dropdown.className = "pc-dropdown"
        dropdown.hidden = True
        dropdown.setAttribute("role", "group")
        dropdown.setAttribute("aria-label", f"{label} detail")
        wrap.appendChild(toggle)
        wrap.appendChild(dropdown)
        bar.appendChild(wrap)
        _pc_hud_els[key] = {"toggle": toggle, "value": value_el, "dropdown": dropdown}
    era = document.createElement("span")
    era.className = "pc-hud-era"
    bar.appendChild(era)
    _pc_hud_els["_era"] = {"el": era}
    setup = document.createElement("button")
    setup.type = "button"
    setup.className = "pc-hud-chip pc-hud-setup"
    setup.id = "pc-hud-setup"
    setup.title = "Pick the starting scenario before the first season"
    setup.addEventListener("click", create_proxy(_pc_hud_open_setup))
    bar.appendChild(setup)
    _pc_hud_els["_setup"] = {"el": setup}
    stage.appendChild(bar)


def _pc_hud_open_setup(event=None):
    opener = document.getElementById("pc-open-pc-setup-panel")
    if opener is not None:
        opener.click()


def _pc_hud_fill(dropdown, title, lines):
    dropdown.innerHTML = ""
    heading = document.createElement("strong")
    heading.innerText = title
    dropdown.appendChild(heading)
    for text in lines:
        row = document.createElement("p")
        row.innerText = text
        dropdown.appendChild(row)


def _pc_hud_update(effects):
    if not _pc_hud_els:
        _pc_hud_build()
    housing = runstate.state.housing_capacity(effects)
    resources = runstate.state.resources
    values = {
        "population": f"{runstate.state.population}/{housing:.0f}",
        "food": f"{resources['food']:.0f}/{runstate.state.food_storage_capacity(effects):.0f}",
        "materials": f"{resources['materials']:.0f}",
        "tools": f"{resources['tools']:.1f}",
        "knowledge": f"{resources['knowledge']:.1f}",
    }
    try:
        preview = forecast.preview(runstate.state, effects)
    except Exception:
        preview = None
    reading = sustainability.evaluate(runstate.state, effects)
    score = reading["score"]
    label = sustainability.score_label(score, sustainability.is_hard_mode(runstate.state))
    values["sustainability"] = f"{score:.0f}"
    for key, icon, name in PC_HUD_CHIPS:
        els = _pc_hud_els[key]
        els["value"].innerText = values[key]
        if key == "sustainability":
            lines = [f"{label}, {score:.0f} out of 100"]
            for component in sustainability.COMPONENTS:
                lines.append(f"{sustainability.COMPONENT_LABEL[component]}: {reading['components'][component]:.0f}")
            lines.append(sustainability.score_note(runstate.state, effects))
        elif preview is not None:
            lines = forecast.lines(key, preview[key])
            if key == "food":
                lines.append(f"Land health {runstate.state.land_health * 100:.0f}%")
        else:
            lines = ["Trend unavailable right now."]
        _pc_hud_fill(els["dropdown"], name, lines)
    _pc_hud_els["_era"]["el"].innerText = naming.with_name(
        settlement_name(),
        f"{sim.ERA_LABEL[runstate.state.era]}, season {runstate.state.season}  \u00B7  idle {runstate.state.idle_workers()}",
    )
    setup = _pc_hud_els["_setup"]["el"]
    show_setup = not _scenario_locked()
    setup.hidden = not show_setup
    if show_setup:
        setup.innerText = f"\U0001F3D5 {sim.scenario_config(runstate.state.scenario)['label']} \u00B7 change"


def _hamlet_town_signature(effects):
    nodes = hamlet.researchable_nodes(runstate.tree)
    research_part = tuple((n.node_id, runstate.tree.can_afford(n.node_id, runstate.state.resources)) for n in nodes)
    active_line = challenges.status_text(runstate.state)
    civic_part = (
        ("active", active_line) if active_line
        else ("offered", tuple(challenges.offered(runstate.state, effects)) if runstate.campaign.revisiting is None else ())
    )
    next_era = transition.next_era_for(runstate.state.era)
    ready = next_era is not None and transition.transition_ready(runstate.state, runstate.tree, effects)
    reasons = tuple(transition.missing_requirements(runstate.state, runstate.tree, effects)) if next_era else ()
    return (runstate.hamlet_town_open, runstate.state.era, research_part, hamlet.locked_count(runstate.tree),
            civic_part, next_era, ready, reasons)


def _hamlet_town_button(parent, button_id, text, aria_label, handler, blocked=False):
    button = _hamlet_el("button", "hamlet-mini hamlet-town-button", text, button_id)
    button.setAttribute("type", "button")
    button.setAttribute("aria-label", aria_label)
    proxy = create_proxy(handler)
    _hamlet_town_proxies.append(proxy)
    button.addEventListener("click", proxy)
    _hamlet_set_blocked(button, blocked)
    parent.appendChild(button)
    return button


def _hamlet_render_town(effects, force=False):
    """The Town Centre panel: research, civic challenges, era advance -- the
    non-per-building actions. Dynamic lists are rebuilt only when their
    signature changes, and focus is put back afterwards."""
    panel = document.getElementById("hamlet-town-panel")
    panel.hidden = not runstate.hamlet_town_open
    if not runstate.hamlet_town_open:
        runstate._hamlet_town_key = None
        return
    key = _hamlet_town_signature(effects)
    if not force and key == runstate._hamlet_town_key and _hamlet_town_els:
        _hamlet_town_els["knowledge"].innerText = f"Knowledge: {runstate.state.resources['knowledge']:.1f}"
        return
    runstate._hamlet_town_key = key
    previous_focus = _hamlet_active_id()

    for proxy in _hamlet_town_proxies:
        proxy.destroy()
    del _hamlet_town_proxies[:]
    _hamlet_town_els.clear()
    panel.innerHTML = ""
    panel.setAttribute("role", "region")
    panel.setAttribute("aria-label", "Town Centre: research, civic challenges, next era")
    panel.setAttribute("tabindex", "-1")

    head = _hamlet_el("div", "hamlet-town-head")
    head.appendChild(_hamlet_el("strong", None, f"{hamlet.TOWN_EMOJI} {hamlet.TOWN_LABEL}"))
    _hamlet_town_button(head, "hamlet-town-close", "Close", "Close the Town Centre panel",
                        _hamlet_close_town)
    panel.appendChild(head)
    knowledge = _hamlet_el("p", "hamlet-town-line",
                           f"Knowledge: {runstate.state.resources['knowledge']:.1f}", "hamlet-town-knowledge")
    panel.appendChild(knowledge)
    _hamlet_town_els["knowledge"] = knowledge

    # --- research ---
    panel.appendChild(_hamlet_el("h3", "hamlet-town-heading", "Research"))
    nodes = hamlet.researchable_nodes(runstate.tree)
    if not nodes:
        panel.appendChild(_hamlet_el("p", "hamlet-town-line", "Nothing to study right now."))
    for node in nodes:
        row = _hamlet_el("div", "hamlet-town-row")
        effect = research.describe_effects(node)
        affordable = runstate.tree.can_afford(node.node_id, runstate.state.resources)
        row.appendChild(_hamlet_el(
            "span", "hamlet-town-name", f"{node.name} · {research.BRANCH_LABEL[node.branch]}"))
        row.title = f"{node.blurb} Effect: {effect}"
        _hamlet_town_button(
            row, f"hamlet-study-{node.node_id}", f"Study {runstate.tree.cost_of(node.node_id):g}",
            f"Study {node.name}: {runstate.tree.cost_of(node.node_id):g} knowledge. Effect: {effect}."
            + ("" if affordable else " Not enough knowledge yet."),
            _make_hamlet_research_handler(node.node_id), blocked=not affordable)
        panel.appendChild(row)
    locked = hamlet.locked_count(runstate.tree)
    if locked:
        panel.appendChild(_hamlet_el("p", "hamlet-town-line hamlet-town-dim", f"{locked} more still locked."))

    # --- civic challenges ---
    panel.appendChild(_hamlet_el("h3", "hamlet-town-heading", "Civic challenges"))
    active_line = challenges.status_text(runstate.state)
    if active_line:
        panel.appendChild(_hamlet_el("p", "hamlet-town-line", active_line))
        row = _hamlet_el("div", "hamlet-town-row")
        _hamlet_town_button(row, "hamlet-challenge-abandon", "Abandon",
                            "Abandon the active civic challenge", on_abandon_challenge)
        panel.appendChild(row)
    elif runstate.campaign.revisiting is not None:
        panel.appendChild(_hamlet_el("p", "hamlet-town-line hamlet-town-dim",
                                     "Not available while looking back."))
    else:
        offered = challenges.offered(runstate.state, effects)
        if not offered:
            panel.appendChild(_hamlet_el("p", "hamlet-town-line hamlet-town-dim",
                                         "None on offer right now."))
        for cid in offered:
            spec = challenges.CHALLENGES[cid]
            row = _hamlet_el("div", "hamlet-town-row")
            row.appendChild(_hamlet_el("span", "hamlet-town-name",
                                       f"{spec['label']} ({spec['seasons']} seasons)"))
            row.title = f"{spec['blurb']} Reward: +{challenges.reward_for(runstate.state.era):.0f} knowledge."
            _hamlet_town_button(row, f"hamlet-challenge-{cid}", "Accept",
                                f"Accept the civic challenge {spec['label']}. {spec['blurb']}",
                                _make_start_challenge_handler(cid))
            panel.appendChild(row)

    # --- next era ---
    panel.appendChild(_hamlet_el("h3", "hamlet-town-heading", "Next era"))
    next_era = transition.next_era_for(runstate.state.era)
    if next_era is None:
        panel.appendChild(_hamlet_el("p", "hamlet-town-line hamlet-town-dim",
                                     "Nothing more to reach from here yet."))
    else:
        ready = transition.transition_ready(runstate.state, runstate.tree, effects)
        reasons = " ".join(transition.missing_requirements(runstate.state, runstate.tree, effects))
        panel.appendChild(_hamlet_el(
            "p", "hamlet-town-line",
            f"Ready to move into the {sim.ERA_LABEL[next_era]} era." if ready
            else f"Working toward the {sim.ERA_LABEL[next_era]} era. {reasons}"))
        row = _hamlet_el("div", "hamlet-town-row")
        _hamlet_town_button(row, "hamlet-advance-era", f"Advance to {sim.ERA_LABEL[next_era]}",
                            f"Advance to the {sim.ERA_LABEL[next_era]} era", on_advance_era,
                            blocked=not ready)
        panel.appendChild(row)

    if previous_focus and previous_focus.startswith("hamlet-") and previous_focus != f"hamlet-{hamlet.TOWN_ID}-main":
        if not _hamlet_focus(previous_focus):
            panel.focus()


def render_hamlet(effects=None):
    """Draws (or, when the mode is off, quietly hides) the Hamlet view. Off
    by default: with the mode off this only sets the toggle button and leaves
    every existing panel exactly as it was."""
    if effects is None:
        effects = current_effects()
    capable = _hamlet_capable()
    active = runstate.hamlet_on and capable
    toggle = document.getElementById("hamlet-toggle-button")
    toggle.hidden = (not capable) or _pc_layout()
    toggle.innerText = f"🏘 Hamlet view: {'On' if runstate.hamlet_on else 'Off'}"
    toggle.setAttribute("aria-pressed", "true" if runstate.hamlet_on else "false")
    document.getElementById("game").classList.toggle("hamlet-on", active)
    document.getElementById("hamlet-stage").hidden = not active
    if not active:
        return

    stations = hamlet.stations_for_era(runstate.state.era)
    if runstate._hamlet_built_key != tuple(s["id"] for s in stations):
        _hamlet_build_chips(stations)
    _hamlet_update_chips(stations, effects)
    _hamlet_update_hud(effects)
    if _pc_layout():
        _pc_hud_update(effects)
    _hamlet_render_town(effects)
