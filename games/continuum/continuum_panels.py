"""The log, sustainability and research panels, and the Work/Build/Study click-handler factories."""

from js import document
from pyodide.ffi import create_proxy

import eastereggs
import narrative_log
import research
import sim
import sustainability

import continuum_runstate as runstate
from continuum_achievements import _check_new_achievements_for_toast
from continuum_founders import record_motion, update_minutes_panel
from continuum_techdebt import _book_quick_build, _easter_egg

render = None  # placeholder: continuum_renderer fills this in when it is imported (it comes later)

# K6 -- branch quick-filter chips. Transient like the search query.
research_branch_filter = set()


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


def _build_log_row(entry):
    """One log row's DOM, handed to `narrative_log.render()` as its
    `build_row` callback (Z11) — byte-identical markup to what render_log()
    used to build inline, just factored out so the shared module can own
    the surrounding cap/empty-state/count loop instead of this game
    repeating it."""
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

    return row


def render_log():
    """The ongoing log (Milestone 6) — lightweight, skippable flavor text
    triggered by research unlocks, population thresholds, and livability
    shifts (which double as this game's diegetic feedback, per the design
    doc's Core system 4 — see log.py). Always visible, never a popup;
    rebuilt from `chronicle.entries` the same way render_research() rebuilds
    the research panel from the tree, for the same reason: a session's
    worth of rows can't be static markup.

    Z11: delegates the cap/empty-state/count-label loop to
    `narrative_log.render()` — this game's own reference integration for
    that shared component. Same player-visible behavior as before the
    migration (same 20-row cap, same newest-first order, same markup).
    """
    narrative_log.render(
        "log-list",
        runstate.chronicle.entries,
        _build_log_row,
        empty_text="Nothing to report yet.",
        max_visible=LOG_VISIBLE_ENTRIES,
        count_element_id="log-status-display",
        count_text=f"{len(runstate.chronicle.entries)} entries",
    )


def render_sustainability(effects):
    """The score panel — visible from season 1 of the first era, by design."""
    reading = sustainability.evaluate(runstate.state, effects)
    value = reading["score"]

    document.getElementById("score-display").innerText = (
        f"Sustainability: {value:.0f} / 100 — "
        f"{sustainability.score_label(value, sustainability.is_hard_mode(runstate.state))}"
    )
    document.getElementById("score-bar").style.width = f"{value:.0f}%"

    weakest = sustainability.weakest_component(runstate.state, effects)
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
        runstate.state, effects
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
    tree runs to sixteen tiers across eight eras, so static markup for it
    would be unmaintainable long before the Space Age. Locked nodes are
    listed too, with the reason they're locked — a tree the player can't
    see the shape of isn't a tree.
    """
    document.getElementById("research-status-display").innerText = (
        f"Knowledge: {runstate.state.resources['knowledge']:.1f} — "
        f"{len(runstate.tree.researched)} discoveries made"
    )

    # UI decluttering: only nodes the player can act on right now live in
    # the always-visible list; locked and already-known nodes sit in two
    # collapsed disclosures below it, which stay rebuilt every render.
    open_container = document.getElementById("research-list")
    locked_container = document.getElementById("research-locked-list")
    known_container = document.getElementById("research-known-list")
    open_container.innerHTML = ""
    locked_container.innerHTML = ""
    known_container.innerHTML = ""
    n_locked = n_known = 0

    query = runstate.research_search_query.strip().lower()
    live_node_ids = set()
    any_rendered = False
    for node in runstate.tree.visible_nodes():
        if query and not _research_node_matches(node, query):
            continue
        if research_branch_filter and node.branch not in research_branch_filter:
            continue
        any_rendered = True
        researched = runstate.tree.is_researched(node.node_id)
        available = runstate.tree.is_available(node.node_id)

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
        cost.innerText = "—" if researched else f"{runstate.tree.cost_of(node.node_id):g}"
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

        # K12: the exact numeric effect, on the row and as a tooltip.
        effect_text = research.describe_effects(node)
        row.title = f"Effect: {effect_text}"
        effect_line = document.createElement("p")
        effect_line.className = "research-effect"
        effect_line.innerText = f"Effect: {effect_text}"
        row.appendChild(effect_line)

        if not researched and not available:
            reasons = document.createElement("p")
            reasons.className = "research-locked-reason"
            reasons.innerText = " ".join(runstate.tree.missing_requirements(node.node_id))
            row.appendChild(reasons)
            # K23: a rough knowledge estimate when the tier gate is the blocker.
            estimate = research.unlock_estimate(runstate.tree, node.node_id)
            if estimate is not None:
                reasons.innerText += f" Roughly {estimate:.0f} knowledge to open and study this."

        actions = document.createElement("div")
        actions.className = "row-actions"
        button = document.createElement("button")
        button.id = f"research-{node.node_id}"
        button.className = "secondary"
        if researched:
            button.innerText = "Known"
            button.disabled = True
        else:
            button.innerText = f"Study ({runstate.tree.cost_of(node.node_id):g})"
            button.disabled = not (available and runstate.tree.can_afford(node.node_id, runstate.state.resources))
            live_node_ids.add(node.node_id)
            proxy = create_proxy(_make_research_handler(node.node_id))
            stale = _research_button_proxies.get(node.node_id)
            if stale is not None:
                stale.destroy()
            _research_button_proxies[node.node_id] = proxy
            button.addEventListener("click", proxy)
        actions.appendChild(button)
        row.appendChild(actions)

        if researched:
            known_container.appendChild(row)
            n_known += 1
        elif not available:
            locked_container.appendChild(row)
            n_locked += 1
        else:
            open_container.appendChild(row)

    _update_research_disclosures(query, n_locked, n_known)

    container = open_container
    if query and not any_rendered:
        empty = document.createElement("p")
        empty.className = "row-blurb"
        empty.innerText = f'No research nodes match "{runstate.research_search_query.strip()}".'
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


def _update_research_disclosures(query, n_locked, n_known):
    """Labels the two collapsed research disclosures with live counts, and
    (only while a search is active) opens any that hold a match so a
    search result is never hidden behind a closed toggle."""
    for prefix, count, noun in (
        ("research-locked", n_locked, "Locked"),
        ("research-known", n_known, "Known discoveries"),
    ):
        details = document.getElementById(f"{prefix}-details")
        document.getElementById(f"{prefix}-summary").innerText = f"{noun} ({count})"
        details.hidden = count == 0
        if query and count:
            details.open = True


def _research_node_matches(node, query):
    """K14 — the research tree search/filter. Matches against the node's
    name, blurb, and branch label, case-insensitively; `query` is already
    lower-cased and stripped by the caller."""
    haystack = f"{node.name} {node.blurb} {research.BRANCH_LABEL[node.branch]}".lower()
    return query in haystack


# --- handlers ----------------------------------------------------------
def _make_assign_handler(role):
    def handler(event=None):
        runstate.state.assign_worker(role)
        render()
        _check_new_achievements_for_toast()
    return handler


def _make_unassign_handler(role):
    def handler(event=None):
        runstate.state.unassign_worker(role)
        render()
        _check_new_achievements_for_toast()
    return handler


def _make_build_handler(building):
    def handler(event=None):
        if runstate.state.build(building):
            record_motion("build", sim.BUILDING_LABEL[building])
            quick = _book_quick_build(building)
            if runstate.campaign.revisiting is None:
                _easter_egg(eastereggs.on_build(runstate.campaign.ui, runstate.state, building, quick))
        update_minutes_panel()
        render()
        _check_new_achievements_for_toast()
    return handler


def _make_research_handler(node_id):
    def handler(event=None):
        if runstate.tree.research(node_id, runstate.state.resources):
            record_motion("research", runstate.tree.nodes[node_id].name)
            if runstate.campaign.revisiting is None:
                _easter_egg(eastereggs.on_research(runstate.campaign.ui, runstate.state, runstate.tree.nodes[node_id].tier))
        update_minutes_panel()
        runstate.chronicle.check_research(runstate.state, runstate.tree)
        render()
        _check_new_achievements_for_toast()
    return handler
