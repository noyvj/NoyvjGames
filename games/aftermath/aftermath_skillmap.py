"""The skill map (layout, model, SVG build, render), the skill detail helpers and skill ranks earned by use."""

import math

import skill_tree as shared_skill_tree
from js import document
from pyodide.ffi import create_proxy

import aftermath_runstate as runstate
from aftermath_bonuses import (
    CATEGORY_DAMAGE_BONUS, adaptive_growth_bonus, starting_resilience_bonus, starting_resources_bonus,
)
from aftermath_pastruns import average_knowledge_per_run
from aftermath_persist import SKILL_PROGRESS_MAX, _el, save_meta
from aftermath_rules import (
    EVENT_BASE_DAMAGE, EVENT_CATEGORY, HELD_PREVENTED_FRACTION, SKILLS, entry_mitigation, entry_prevented,
)
from aftermath_runview import announce
from aftermath_skilltree import SKILL_MOVE_FEE
from aftermath_tools import (
    SKILL_GROUP, SKILL_GROUP_LABEL, skill_filter_summary, skill_filters_active, skill_matches,
)


# render() is defined in aftermath_renderer, which comes later in the module list; that module puts it here when it
# loads (see the end of aftermath_renderer.py). Calls below find it at run time.
render = None


def render_skill_move():
    """AN-13: the "Move a point" panel: one owned skill to another, for SKILL_MOVE_FEE knowledge."""
    panel = _el("skill-move")
    if panel is None:
        return
    owned = [s for s in SKILLS if s in runstate.skill_tree.unlocked]
    panel.hidden = not owned
    from_select, to_select = _el("skill-move-from"), _el("skill-move-to")
    if from_select is None or to_select is None:
        return
    keep_from, keep_to = from_select.value, to_select.value
    from_select.innerHTML = ""
    to_select.innerHTML = ""
    for skill_id in owned:
        option = document.createElement("option")
        option.value = skill_id
        option.innerText = f"{SKILLS[skill_id]['label']} (costs {SKILLS[skill_id]['cost']})"
        from_select.appendChild(option)
    for skill_id in SKILLS:
        if skill_id in runstate.skill_tree.unlocked:
            continue
        option = document.createElement("option")
        option.value = skill_id
        option.innerText = f"{SKILLS[skill_id]['label']} (costs {SKILLS[skill_id]['cost']})"
        to_select.appendChild(option)
    unowned = [s for s in SKILLS if s not in runstate.skill_tree.unlocked]
    from_select.value = keep_from if keep_from in owned else (owned[0] if owned else "")
    to_select.value = keep_to if keep_to in unowned else (unowned[0] if unowned else "")
    ok, reason = runstate.skill_tree.move_check(from_select.value, to_select.value) if owned and to_select.value else (False, "Nothing to move to.")
    button = _el("skill-move-button")
    if button is not None:
        button.disabled = not ok
    status = _el("skill-move-status")
    if status is not None and not runstate.skill_move_message:
        status.innerText = (f"Moving costs {SKILL_MOVE_FEE} knowledge on top of the difference in price. "
                            + ("" if ok else reason))


# ===========================================================================
# E-2 skill-tree map, E-11 skill ranks, GE-16 unlock reveal (2026-10-11).
#
# The rules come from the shared skill-tree module (shared/skill_tree.py, W-3): Aftermath's SKILLS are
# described to it as plain data (SKILL_TREE_DATA) and it answers status, tier and validity. The state is
# untouched: SkillTreeState (knowledge points, unlocked, lifetime_knowledge) and its storage format are
# exactly as before. The shared module counts "points earned minus spent", Aftermath keeps a spendable
# balance, so the map passes earned = balance + spent and the two always agree (a move or a reset never
# drifts them).
# ===========================================================================
SKILL_TREE_DATA = {
    "id": "aftermath",
    "title": "Aftermath skills",
    "currency": "knowledge",
    "branches": [{"id": key, "title": label} for key, label in SKILL_GROUP_LABEL.items()],
    "nodes": [
        {
            "id": skill_id,
            "branch": SKILL_GROUP.get(skill_id, ""),
            "cost": skill["cost"],
            "label": skill["label"],
            "description": skill["description"],
            "requires": list(skill.get("prereqs", [])),
        }
        for skill_id, skill in SKILLS.items()
    ],
}

SKILL_STATE_WORD = {
    "owned": "Owned",
    "available": "Available now",
    "unaffordable": "Not affordable yet",
    "locked": "Locked",
}
SKILL_STATE_GLYPH = {"owned": "✓", "available": "◆", "unaffordable": "◇", "locked": "▪"}


def _tree_owned():
    return sorted(s for s in runstate.skill_tree.unlocked if s in SKILLS)


def _tree_earned():
    """Knowledge 'ever given' as the shared module counts it: the balance in hand plus what the owned skills cost."""
    return runstate.skill_tree.knowledge_points + shared_skill_tree.spent(SKILL_TREE_DATA, _tree_owned())


def skill_status(skill_id):
    """owned / available / unaffordable / locked, from the shared module."""
    return shared_skill_tree.status(SKILL_TREE_DATA, _tree_owned(), skill_id, _tree_earned())


def skill_leads_to(skill_id):
    """The skills that list skill_id as a prerequisite, in catalogue order."""
    return [s for s, skill in SKILLS.items() if skill_id in skill.get("prereqs", [])]


def route_to(skill_id):
    """E-2: what it takes to reach a skill, in the order to buy it. A skill needs ALL of its prerequisites,
    so there is exactly one route (and so it is also the cheapest): every prerequisite, all the way down, that
    is not owned yet, then the skill itself. Sorted by tier (a prerequisite is always a lower tier) then
    catalogue order. An owned or unknown skill has no route."""
    if skill_id not in SKILLS or skill_id in runstate.skill_tree.unlocked:
        return []
    need, stack = set(), [skill_id]
    while stack:
        current = stack.pop()
        if current in need or current in runstate.skill_tree.unlocked:
            continue
        need.add(current)
        stack.extend(SKILLS[current].get("prereqs", []))
    order = list(SKILLS)
    return sorted(need, key=lambda s: (shared_skill_tree.tier_of(SKILL_TREE_DATA, s), order.index(s)))


def _runs_phrase(short):
    if short <= 0:
        return "affordable now"
    rate = average_knowledge_per_run()
    if not rate or rate <= 0:
        return "complete a run for an estimate of how long"
    runs = max(1, math.ceil(short / rate))
    return f"about {runs} more run{'s' if runs != 1 else ''} at your average of {rate:.1f} knowledge per run"


def route_info(skill_id):
    """The route as numbers: steps [{id, label, cost, running_total}], the total knowledge needed, the balance
    in hand and how much is still short."""
    steps, running = [], 0
    for step_id in route_to(skill_id):
        running += SKILLS[step_id]["cost"]
        steps.append({"id": step_id, "label": SKILLS[step_id]["label"], "cost": SKILLS[step_id]["cost"], "running_total": running})
    have = runstate.skill_tree.knowledge_points
    return {"steps": steps, "total": running, "have": have, "short": max(0, running - have)}


def route_text(skill_id):
    info = route_info(skill_id)
    if not info["steps"]:
        return ""
    parts = ", then ".join(f"{s['label']} ({s['cost']})" for s in info["steps"])
    if len(info["steps"]) == 1:
        return f"Unlock {parts}."
    return f"Route: {parts}."


# ---- layout: tiers left to right, rows in a fixed, crossing-light order -------------------------------
SKILL_MAP_ORDER = (
    "early_warning",
    "reinforced_infrastructure",
    "community_reserves",
    "adaptive_growth",
    "climate_hardening",
    "mutual_aid_network",
    "civic_preparedness",
)
MAP_NODE_W, MAP_NODE_H = 164, 100
MAP_GAP_X, MAP_GAP_Y = 72, 18
MAP_PAD = 28


def skill_map_layout():
    """{skill_id: (x, y, tier)} in map pixels. Tier is the column (the shared module's depth); rows follow
    SKILL_MAP_ORDER (any skill not listed goes last, so a future skill still lands somewhere); a column shorter
    than the tallest is centred."""
    listed = [s for s in SKILL_MAP_ORDER if s in SKILLS] + [s for s in SKILLS if s not in SKILL_MAP_ORDER]
    columns = {}
    for skill_id in listed:
        tier = shared_skill_tree.tier_of(SKILL_TREE_DATA, skill_id)
        columns.setdefault(tier, []).append(skill_id)
    tallest = max((len(ids) for ids in columns.values()), default=1)
    layout = {}
    for tier, ids in columns.items():
        offset = (tallest - len(ids)) * (MAP_NODE_H + MAP_GAP_Y) / 2
        for row, skill_id in enumerate(ids):
            x = MAP_PAD + (tier - 1) * (MAP_NODE_W + MAP_GAP_X)
            y = MAP_PAD + offset + row * (MAP_NODE_H + MAP_GAP_Y)
            layout[skill_id] = (int(x), int(y), tier)
    return layout


def skill_map_size():
    layout = skill_map_layout()
    width = max(x for x, _y, _t in layout.values()) + MAP_NODE_W + MAP_PAD
    height = max(y for _x, y, _t in layout.values()) + MAP_NODE_H + MAP_PAD
    return int(width), int(height)


# ---- state of the map (view state only; nothing is saved) -----------------------------------------------
skill_map_status_text = ""


def newly_available_children(skill_id):
    """GE-16: the skills that have skill_id as a prerequisite and whose prerequisites are ALL owned now (call
    after the skill is owned): the ones that just stopped being locked."""
    return [
        child for child in skill_leads_to(skill_id)
        if child not in runstate.skill_tree.unlocked and all(p in runstate.skill_tree.unlocked for p in SKILLS[child].get("prereqs", []))
    ]


def reveal_text(reveal=None):
    reveal = runstate.skill_map_reveal if reveal is None else reveal
    if not reveal:
        return ""
    label = SKILLS[reveal["skill"]]["label"]
    children = [SKILLS[c]["label"] for c in reveal["children"]]
    if children:
        return f"{label} unlocked. Now available: {', '.join(children)}."
    return f"{label} unlocked. No new skills open up from it."


def note_skill_reveal(skill_id):
    """GE-16: remember the skill that was just bought, mark the children it opened, and say so through the
    announcer (always as text, so it does not depend on the animation or on motion settings)."""
    if skill_id not in SKILLS or skill_id not in runstate.skill_tree.unlocked:
        return ""
    runstate.skill_map_reveal = {"skill": skill_id, "children": newly_available_children(skill_id)}
    text = reveal_text()
    announce(text)
    return text


def skill_map_filtered_out(skill_id):
    return not skill_matches(skill_id)


def skill_map_detail_text(skill_id=None):
    """The words for the selected skill: what it is, its state and, for a locked skill, the route and the total
    knowledge needed."""
    skill_id = runstate.skill_map_selected if skill_id is None else skill_id
    if skill_id not in SKILLS:
        return ("Select a skill to see what it needs. Arrow keys move between skills, Enter selects, plus and minus zoom, "
                "0 fits the map, Escape clears.")
    skill = SKILLS[skill_id]
    status = skill_status(skill_id)
    head = f"{skill['label']}: {skill['description']}."
    rank = skill_rank_line(skill_id)
    rank_part = f" {rank}." if rank and skill_id in runstate.skill_tree.unlocked else ""
    if status == "owned":
        leads = [SKILLS[c]["label"] for c in skill_leads_to(skill_id)]
        return f"{head} Yours already.{rank_part} " + (f"It leads to: {', '.join(leads)}." if leads else "Nothing else builds on it.")
    info = route_info(skill_id)
    have = runstate.skill_tree.knowledge_points
    if status == "available":
        return f"{head} You can unlock it now for {skill['cost']} knowledge (you have {have})."
    if status == "unaffordable":
        return (f"{head} Costs {skill['cost']} knowledge and you have {have}, so {info['short']} short: "
                f"{_runs_phrase(info['short'])}.")
    steps = ", then ".join(f"{s['label']} ({s['cost']})" for s in info["steps"])
    return (f"{head} Locked. The route is the only way in, because a skill needs all of its prerequisites: {steps}. "
            f"Total knowledge needed: {info['total']}; you have {have}, so {info['short']} short"
            f"{' (' + _runs_phrase(info['short']) + ')' if info['short'] else ''}.")


def skill_map_node_label(skill_id, route_ids=()):
    """The accessible name of a map node: everything the picture says, in words."""
    skill = SKILLS[skill_id]
    status = skill_status(skill_id)
    parts = [skill["label"], SKILL_STATE_WORD[status], f"cost {skill['cost']} knowledge",
             SKILL_GROUP_LABEL.get(SKILL_GROUP.get(skill_id), "")]
    needs = skill.get("prereqs", [])
    parts.append("needs " + ", ".join(SKILLS[p]["label"] + (" (owned)" if p in runstate.skill_tree.unlocked else "") for p in needs)
                 if needs else "no prerequisites")
    rank = skill_rank_short(skill_id)
    if rank:
        parts.append(rank)
    if skill_id in route_ids:
        parts.append(f"step {list(route_ids).index(skill_id) + 1} of {len(route_ids)} on the route")
    if runstate.skill_map_reveal and skill_id in runstate.skill_map_reveal["children"]:
        parts.append("now available")
    if skill_map_filtered_out(skill_id):
        parts.append("does not match the current filters")
    return ". ".join(p for p in parts if p)


def skill_map_model():
    """Everything the map shows, as data (the DOM code only applies it): per node its state, classes, accessible
    name and route step; per link its classes; plus the detail text. Pure given the game's state."""
    if runstate.skill_map_selected is not None and runstate.skill_map_selected not in SKILLS:
        runstate.skill_map_selected = None
    if runstate.skill_map_reveal and (runstate.skill_map_reveal["skill"] not in runstate.skill_tree.unlocked):
        runstate.skill_map_reveal = None
    layout = skill_map_layout()
    route = route_to(runstate.skill_map_selected) if runstate.skill_map_selected else []
    revealed = runstate.skill_map_reveal or {"skill": None, "children": []}
    nodes, links = {}, {}
    for skill_id in SKILLS:
        status = skill_status(skill_id)
        classes = ["skill-map-node", f"skill-map-node--{status}"]
        if skill_id == runstate.skill_map_selected:
            classes.append("skill-map-node--selected")
        if skill_id in route:
            classes.append("skill-map-node--route")
        if skill_map_filtered_out(skill_id):
            classes.append("skill-map-node--filtered")
        if skill_id == revealed["skill"]:
            classes.append("skill-map-node--just-bought")
        if skill_id in revealed["children"]:
            classes.append("skill-map-node--now-available")
        x, y, tier = layout[skill_id]
        nodes[skill_id] = {
            "status": status,
            "classes": classes,
            "x": x, "y": y, "tier": tier,
            "filtered": skill_map_filtered_out(skill_id),
            "step": route.index(skill_id) + 1 if skill_id in route else None,
            "label": skill_map_node_label(skill_id, route),
            "rank": skill_rank_short(skill_id),
        }
    for skill_id, skill in SKILLS.items():
        for pre in skill.get("prereqs", []):
            classes = ["skill-map-link"]
            if pre in runstate.skill_tree.unlocked and skill_id in runstate.skill_tree.unlocked:
                classes.append("skill-map-link--owned")
            if skill_id in route:
                classes.append("skill-map-link--route")
            if pre == revealed["skill"] and skill_id in revealed["children"]:
                classes.append("skill-map-link--lit")
            if nodes[pre]["filtered"] or nodes[skill_id]["filtered"]:
                classes.append("skill-map-link--filtered")
            links[(pre, skill_id)] = {"classes": classes}
    return {
        "nodes": nodes,
        "links": links,
        "route": route,
        "detail": skill_map_detail_text(),
        "reveal": reveal_text(),
        "summary": skill_filter_summary(),
    }


# ---- DOM: the map is built once, then updated in place (so keyboard focus and the pan/zoom survive) ----
_skill_map_parts = {}  # skill_id -> {"button", "glyph", "state", "rank", "step"}; "links" -> {(pre, id): element}

SVG_NS = "http://www.w3.org/2000/svg"


def _svg(tag):
    create_ns = getattr(document, "createElementNS", None)
    return create_ns(SVG_NS, tag) if create_ns is not None else document.createElement(tag)


def _span(css_class, text=""):
    span = document.createElement("span")
    span.className = css_class
    span.innerText = text
    return span


def _link_path(pre, skill_id, layout):
    x1 = layout[pre][0] + MAP_NODE_W
    y1 = layout[pre][1] + MAP_NODE_H / 2
    x2 = layout[skill_id][0]
    y2 = layout[skill_id][1] + MAP_NODE_H / 2
    bend = (x2 - x1) / 2
    return f"M {x1:.0f} {y1:.0f} C {x1 + bend:.0f} {y1:.0f}, {x2 - bend:.0f} {y2:.0f}, {x2 - 6:.0f} {y2:.0f}"


def build_skill_map():
    """Builds the nodes and links once. Every handler is wired here; render_skill_map() only changes
    classes and text afterwards."""
    canvas = _el("skill-map-canvas")
    if canvas is None or runstate._skill_map_built:
        return
    runstate._skill_map_built = True
    width, height = skill_map_size()
    canvas.innerHTML = ""
    canvas.style.width = f"{width}px"
    canvas.style.height = f"{height}px"
    layout = skill_map_layout()

    svg = _svg("svg")
    svg.setAttribute("class", "skill-map-links")
    svg.setAttribute("width", str(width))
    svg.setAttribute("height", str(height))
    svg.setAttribute("viewBox", f"0 0 {width} {height}")
    svg.setAttribute("aria-hidden", "true")
    defs = _svg("defs")
    marker = _svg("marker")
    marker.setAttribute("id", "skill-map-arrow")
    marker.setAttribute("viewBox", "0 0 10 10")
    marker.setAttribute("refX", "8")
    marker.setAttribute("refY", "5")
    marker.setAttribute("markerWidth", "7")
    marker.setAttribute("markerHeight", "7")
    marker.setAttribute("orient", "auto-start-reverse")
    arrow = _svg("path")
    arrow.setAttribute("d", "M 0 0 L 10 5 L 0 10 z")
    arrow.setAttribute("class", "skill-map-arrow")
    marker.appendChild(arrow)
    defs.appendChild(marker)
    svg.appendChild(defs)
    _skill_map_parts["links"] = {}
    for skill_id, skill in SKILLS.items():
        for pre in skill.get("prereqs", []):
            path = _svg("path")
            path.setAttribute("d", _link_path(pre, skill_id, layout))
            path.setAttribute("class", "skill-map-link")
            path.setAttribute("marker-end", "url(#skill-map-arrow)")
            path.setAttribute("data-from", pre)
            path.setAttribute("data-to", skill_id)
            svg.appendChild(path)
            _skill_map_parts["links"][(pre, skill_id)] = path
    canvas.appendChild(svg)

    for skill_id, skill in SKILLS.items():
        x, y, _tier = layout[skill_id]
        button = document.createElement("button")
        button.id = f"skill-map-node-{skill_id}"
        button.setAttribute("type", "button")
        button.setAttribute("data-skill", skill_id)
        button.setAttribute("tabindex", "-1")
        button.setAttribute("aria-pressed", "false")
        button.style.left = f"{x}px"
        button.style.top = f"{y}px"
        button.style.width = f"{MAP_NODE_W}px"
        button.style.height = f"{MAP_NODE_H}px"
        glyph = _span("skill-map-glyph")
        glyph.setAttribute("aria-hidden", "true")
        name = _span("skill-map-name", skill["label"])
        group = SKILL_GROUP_LABEL.get(SKILL_GROUP.get(skill_id), "")
        meta_line = _span("skill-map-meta", f"Cost {skill['cost']} · {group}" if group else f"Cost {skill['cost']}")
        state = _span("skill-map-state")
        rank = _span("skill-map-rank")
        step = _span("skill-map-step")
        for part in (glyph, name, meta_line, state, rank, step):
            button.appendChild(part)
        button.addEventListener("click", create_proxy(_make_skill_map_select(skill_id)))
        canvas.appendChild(button)
        _skill_map_parts[skill_id] = {"button": button, "glyph": glyph, "state": state, "rank": rank, "step": step}


def _make_skill_map_select(skill_id):
    def handler(event=None):
        select_skill_on_map(skill_id)
    return handler


def select_skill_on_map(skill_id):
    """Enter or a click on a node: select it. The detail line and the route follow; the node keeps keyboard
    focus because the nodes are updated in place."""
    if skill_id not in SKILLS:
        return False
    runstate.skill_map_selected = skill_id
    runstate.skill_map_reveal = None
    render()
    detail = skill_map_detail_text(skill_id)
    announce(detail)
    return True


def clear_skill_map_selection(event=None):
    runstate.skill_map_selected = None
    runstate.skill_map_reveal = None
    render()
    announce("Selection cleared.")
    return True


def render_skill_map():
    canvas = _el("skill-map-canvas")
    if canvas is None:
        return
    if not runstate._skill_map_built:
        build_skill_map()
    model = skill_map_model()
    viewport = _el("skill-map-viewport")
    keep = viewport.getAttribute("data-current") if viewport is not None else None
    usable = [s for s in SKILLS if not model["nodes"][s]["filtered"]]
    if keep not in usable:
        keep = runstate.skill_map_selected if runstate.skill_map_selected in usable else (usable[0] if usable else None)
        if viewport is not None and keep:
            viewport.setAttribute("data-current", keep)
    for skill_id, info in model["nodes"].items():
        parts = _skill_map_parts.get(skill_id)
        if parts is None:
            continue
        button = parts["button"]
        button.setAttribute("class", " ".join(info["classes"]))
        button.setAttribute("aria-label", info["label"])
        button.setAttribute("aria-pressed", "true" if skill_id == runstate.skill_map_selected else "false")
        button.setAttribute("tabindex", "0" if skill_id == keep else "-1")
        button.setAttribute("data-filtered", "true" if info["filtered"] else "false")
        button.setAttribute("data-status", info["status"])
        parts["glyph"].innerText = SKILL_STATE_GLYPH[info["status"]]
        parts["state"].innerText = SKILL_STATE_WORD[info["status"]]
        parts["rank"].innerText = info["rank"]
        if info["step"] is not None:
            parts["step"].innerText = f"Route step {info['step']}"
        elif runstate.skill_map_reveal and skill_id in runstate.skill_map_reveal["children"]:
            parts["step"].innerText = "Now available"
        elif runstate.skill_map_reveal and skill_id == runstate.skill_map_reveal["skill"]:
            parts["step"].innerText = "Just unlocked"
        else:
            parts["step"].innerText = ""
    for key, path in _skill_map_parts.get("links", {}).items():
        path.setAttribute("class", " ".join(model["links"][key]["classes"]))
    detail = _el("skill-map-detail")
    if detail is not None:
        detail.innerText = model["detail"]
    reveal = _el("skill-map-reveal")
    if reveal is not None:
        reveal.innerText = model["reveal"]
        reveal.hidden = not model["reveal"]
    summary = _el("skill-map-filter-summary")
    if summary is not None:
        summary.innerText = model["summary"]
    unlock = _el("skill-map-unlock-button")
    selected = runstate.skill_map_selected
    if unlock is not None:
        show = selected in SKILLS and skill_status(selected) == "available"
        unlock.hidden = not show
        if show:
            unlock.innerText = f"Unlock {SKILLS[selected]['label']} ({SKILLS[selected]['cost']})"
    pin = _el("skill-map-pin-button")
    if pin is not None:
        show = selected in SKILLS and selected not in runstate.skill_tree.unlocked
        pin.hidden = not show
        if show:
            pinned = selected in runstate.meta["pinned_skills"]
            pin.innerText = "\U0001F4CC Pinned" if pinned else "\U0001F4CD Pin"
    clear = _el("skill-map-clear-button")
    if clear is not None:
        clear.disabled = selected is None and not runstate.skill_map_reveal
    text_list = _el("skill-map-text")
    if text_list is not None:
        text_list.innerHTML = ""
        for line in skill_map_text_lines():
            item = document.createElement("li")
            item.innerText = line
            text_list.appendChild(item)
    clear_filters = _el("skill-map-filter-clear")
    if clear_filters is not None:
        clear_filters.hidden = not skill_filters_active()
    for skill_id in SKILLS:  # GE-16: the list highlights the same newly available skills
        row = _el(f"skill-{skill_id}-row")
        if row is not None:
            if runstate.skill_map_reveal and skill_id in runstate.skill_map_reveal["children"]:
                row.classList.add("skill-row--now-available")
            else:
                row.classList.remove("skill-row--now-available")


def skill_map_text_lines():
    """The plain-words version of the picture: one sentence per skill with its state, cost, what it needs and
    what it leads to."""
    lines = []
    for skill_id, skill in SKILLS.items():
        needs = skill.get("prereqs", [])
        needs_text = "needs " + " and ".join(SKILLS[p]["label"] for p in needs) if needs else "has no prerequisites"
        leads = [SKILLS[c]["label"] for c in skill_leads_to(skill_id)]
        leads_text = "leads to " + " and ".join(leads) if leads else "leads nowhere further"
        lines.append(
            f"{skill['label']} ({SKILL_GROUP_LABEL.get(SKILL_GROUP.get(skill_id), '')}): "
            f"{SKILL_STATE_WORD[skill_status(skill_id)].lower()}, cost {skill['cost']}, {needs_text}, {leads_text}."
        )
    return lines


# ---- E-11: skill ranks, earned by proven use --------------------------------------------------------------
# Three ranks per skill. Progress is counted ONCE when a run pays out (the same guard as knowledge, so
# reloading an old save cannot count twice), only for the skills owned at that moment, and only for real
# runs: a friend's challenge run and a player-built schedule do not count. The numbers come from fields the
# game already records for every run (the event log: type, damage, severity; and the final resilience, growth
# and resources). A rank is read from the stored count: it only goes up, is never lost (a reset or a move of a
# point keeps it), changes nothing in a run and is never needed to finish the game. No luck is involved: the
# same run always adds the same amount.
SKILL_RANK_NAMES = ("No rank yet", "Rank 1", "Rank 2", "Rank 3")
SKILL_BUILD_UNITS = 2  # a starting-build skill counts a run when you built this many units of your own on top of it
SKILL_RANK_RULES = {
    "early_warning": {
        "unit": "accurate previews",
        "thresholds": (10, 25, 50),
        "how": ("Every event you face with Early Warning Systems owned counts as one accurate preview: the damage in the "
                "Expected damage line is the exact figure the event then deals, so a preview you act on is accurate."),
    },
    "mutual_aid_network": {
        "unit": "events held",
        "thresholds": (8, 20, 40),
        "how": "Every event you face with Mutual Aid Network owned where your defences prevented at least half its damage.",
    },
    "climate_hardening": {
        "unit": "weather damage prevented",
        "thresholds": (100, 300, 600),
        "how": "Damage points prevented from Flood, Heatwave and Storm events while Climate Hardening is owned (base damage times severity, minus what got through).",
    },
    "civic_preparedness": {
        "unit": "unrest damage prevented",
        "thresholds": (50, 150, 300),
        "how": "Damage points prevented from Civil Unrest events while Civic Preparedness is owned.",
    },
    "reinforced_infrastructure": {
        "unit": "runs with 4+ resilience",
        "thresholds": (2, 5, 10),
        "how": "Runs that end with Resilience at 4 or more (the 2 it gives plus 2 units you built) while Reinforced Infrastructure is owned.",
    },
    "community_reserves": {
        "unit": "runs ending with 50+ resources",
        "thresholds": (2, 5, 10),
        "how": "Runs that end with at least 50 resources left (the reserve it gives, still standing) while Community Reserves is owned.",
    },
    "adaptive_growth": {
        "unit": "runs with 3+ growth",
        "thresholds": (2, 5, 10),
        "how": "Runs that end with Growth at 3 or more (the 1 it gives plus 2 units you built) while Adaptive Growth Practices is owned.",
    },
}


def skill_rank_progress(skill_id):
    return runstate.meta["skill_progress"].get(skill_id, 0) if skill_id in SKILLS else 0


def skill_rank(skill_id):
    rule = SKILL_RANK_RULES.get(skill_id)
    if rule is None:
        return 0
    count = skill_rank_progress(skill_id)
    return sum(1 for threshold in rule["thresholds"] if count >= threshold)


def skill_rank_gains(event_log, resilience, growth, resources, unlocked):
    """What one finished run adds to each OWNED skill's progress (a dict of whole numbers). Pure: the same
    inputs always give the same answer."""
    gains = {}
    log = [e for e in event_log if isinstance(e, dict) and e.get("type") in EVENT_BASE_DAMAGE]
    if "early_warning" in unlocked:
        gains["early_warning"] = len(log)
    if "mutual_aid_network" in unlocked:
        gains["mutual_aid_network"] = sum(
            1 for e in log if (entry_mitigation(e) or 0.0) + 1e-9 >= HELD_PREVENTED_FRACTION
        )
    for skill_id, (category, _amount) in CATEGORY_DAMAGE_BONUS.items():
        if skill_id in unlocked:
            gains[skill_id] = int(round(sum(entry_prevented(e) for e in log if EVENT_CATEGORY.get(e["type"]) == category)))
    if "reinforced_infrastructure" in unlocked:
        gains["reinforced_infrastructure"] = 1 if resilience >= starting_resilience_bonus({"reinforced_infrastructure"}) + SKILL_BUILD_UNITS else 0
    if "community_reserves" in unlocked:
        gains["community_reserves"] = 1 if resources >= starting_resources_bonus({"community_reserves"}) else 0
    if "adaptive_growth" in unlocked:
        gains["adaptive_growth"] = 1 if growth >= adaptive_growth_bonus({"adaptive_growth"}) + SKILL_BUILD_UNITS else 0
    return {skill_id: amount for skill_id, amount in gains.items() if amount > 0}


def record_skill_progress(run_state):
    """Adds a paid-out run to the skills' progress. Never raises (ranks are an extra, not part of the run)."""
    runstate.skill_ranks_just_gained = []
    try:
        if run_state.normalised or run_state.custom_events:
            return []
        owned = {s for s in runstate.skill_tree.unlocked if s in SKILLS}
        gains = skill_rank_gains(run_state.event_log, run_state.resilience_capacity, run_state.growth_capacity,
                                 run_state.resources, owned)
        before = {skill_id: skill_rank(skill_id) for skill_id in gains}
        for skill_id, amount in gains.items():
            runstate.meta["skill_progress"][skill_id] = min(SKILL_PROGRESS_MAX, skill_rank_progress(skill_id) + amount)
        if gains:
            save_meta()
        runstate.skill_ranks_just_gained = [(s, skill_rank(s)) for s in gains if skill_rank(s) > before[s]]
    except Exception:  # noqa: BLE001
        runstate.skill_ranks_just_gained = []
    return runstate.skill_ranks_just_gained


def skill_rank_pips(skill_id):
    rank = skill_rank(skill_id)
    return "●" * rank + "○" * (3 - rank)


def skill_rank_line(skill_id):
    """'Rank 1 of 3: 12/25 accurate previews toward rank 2', or '' for a skill with no progress yet."""
    rule = SKILL_RANK_RULES.get(skill_id)
    if rule is None:
        return ""
    count, rank = skill_rank_progress(skill_id), skill_rank(skill_id)
    if count <= 0 and skill_id not in runstate.skill_tree.unlocked:
        return ""
    label = SKILL_RANK_NAMES[rank] if rank == 0 else f"Rank {rank} of 3"
    if rank >= 3:
        return f"{skill_rank_pips(skill_id)} {label} (top rank): {count} {rule['unit']}"
    return f"{skill_rank_pips(skill_id)} {label}: {count}/{rule['thresholds'][rank]} {rule['unit']} toward rank {rank + 1}"


def skill_rank_short(skill_id):
    rule = SKILL_RANK_RULES.get(skill_id)
    if rule is None or (skill_rank_progress(skill_id) <= 0 and skill_id not in runstate.skill_tree.unlocked):
        return ""
    count, rank = skill_rank_progress(skill_id), skill_rank(skill_id)
    if rank >= 3:
        return f"{skill_rank_pips(skill_id)} Rank 3/3"
    return f"{skill_rank_pips(skill_id)} Rank {rank}/3 · {count}/{rule['thresholds'][rank]}"


def skill_ranks_total():
    """(ranks earned, ranks possible) across the whole tree, for the completion line."""
    return sum(skill_rank(s) for s in SKILLS), 3 * len(SKILLS)


def skill_ranks_summary_text():
    earned, possible = skill_ranks_total()
    return f"Skill ranks: {earned} of {possible} earned by using your skills (optional, nothing needs them)."


def skill_rank_callout_text():
    if not runstate.skill_ranks_just_gained:
        return ""
    parts = [f"{SKILLS[s]['label']} reached rank {rank}" for s, rank in runstate.skill_ranks_just_gained]
    return "Skill rank up: " + "; ".join(parts) + "."


def skill_rank_rule_lines():
    lines = []
    for skill_id in SKILLS:
        rule = SKILL_RANK_RULES[skill_id]
        a, b, c = rule["thresholds"]
        lines.append(f"{SKILLS[skill_id]['label']}: rank 1 at {a}, rank 2 at {b}, rank 3 at {c} {rule['unit']}. {rule['how']}")
    return lines


def render_skill_ranks():
    for skill_id in SKILLS:
        rank_el = _el(f"skill-{skill_id}-rank")
        if rank_el is not None:
            rank_el.innerText = skill_rank_line(skill_id)
    summary = _el("skill-ranks-summary")
    if summary is not None:
        summary.innerText = skill_ranks_summary_text()
    rules = _el("skill-rank-rules")
    if rules is not None and not rules.children:
        for line in skill_rank_rule_lines():
            item = document.createElement("li")
            item.innerText = line
            rules.appendChild(item)
