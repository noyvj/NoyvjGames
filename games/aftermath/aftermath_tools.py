"""Skill tree search and filter chips, named allocation presets, the save health badge, the purchase route planner and the plain-text schedule."""

import math

from js import document
from pyodide.ffi import create_proxy

import aftermath_runstate as runstate
from aftermath_pastruns import average_knowledge_per_run
from aftermath_persist import (
    PRESET_MAX, PRESET_NAME_MAX, PRESET_UNITS_MAX, _clean_name, _el, _storage_state, _units, save_meta,
    storage_health,
)
from aftermath_rules import RESILIENCE_COST, SKILLS
from aftermath_runview import schedule_strip_entries


# render() is defined in aftermath_renderer, which comes later in the module list; that module puts it here when it
# loads (see the end of aftermath_renderer.py). Calls below find it at run time.
render = None


# ---------------------------------------------------------------------------
# Round-3 batch 2 (2026-10-10): E-19 tree search/filters, E-25 allocation presets, E-30 save
# health badge, E-3 purchase route planner, E-13 schedule builder, E-4 shareable run codes and the
# last E-5 pieces (plain-text schedule). Each section says what it owns.
# ---------------------------------------------------------------------------


# ---- E-19: skill tree search and filter chips ------------------------------
SKILL_GROUP = {
    "reinforced_infrastructure": "starting",
    "community_reserves": "starting",
    "adaptive_growth": "starting",
    "early_warning": "mitigation",
    "mutual_aid_network": "mitigation",
    "climate_hardening": "weather",
    "civic_preparedness": "social",
}
SKILL_GROUP_LABEL = {"weather": "Weather", "social": "Social", "mitigation": "All events", "starting": "Starting build"}
SKILL_STATUS_FILTERS = (("all", "All"), ("affordable", "Affordable"), ("pinned", "Pinned"), ("owned", "Owned"))
SKILL_GROUP_FILTERS = (("any", "Any type"),) + tuple(SKILL_GROUP_LABEL.items())


def skill_matches(skill_id, query=None, status=None, group=None):
    """True when the skill passes the search words (every word must appear in its name, effect,
    real-world note or type), the status chip (Affordable = can be unlocked right now, Pinned,
    Owned) and the type chip."""
    query = runstate.skill_search_text if query is None else query
    status = runstate.skill_filter_status if status is None else status
    group = runstate.skill_filter_group if group is None else group
    skill = SKILLS[skill_id]
    owned = skill_id in runstate.skill_tree.unlocked
    if status == "owned" and not owned:
        return False
    if status == "affordable" and not runstate.skill_tree.can_unlock(skill_id):
        return False
    if status == "pinned" and not (skill_id in runstate.meta["pinned_skills"] and not owned):
        return False
    if group != "any" and SKILL_GROUP.get(skill_id) != group:
        return False
    words = str(query or "").casefold().split()
    if words:
        haystack = " ".join(
            [skill["label"], skill["description"], skill["real_practice"], SKILL_GROUP_LABEL.get(SKILL_GROUP.get(skill_id), "")]
        ).casefold()
        if not all(word in haystack for word in words):
            return False
    return True


def visible_skill_ids():
    return [skill_id for skill_id in SKILLS if skill_matches(skill_id)]


def skill_filters_active():
    return bool(runstate.skill_search_text.strip()) or runstate.skill_filter_status != "all" or runstate.skill_filter_group != "any"


def skill_filter_summary():
    shown = len(visible_skill_ids())
    if shown == 0:
        return "No skills match. Clear the search or pick All."
    if not skill_filters_active():
        return f"Showing all {len(SKILLS)} skills."
    return f"Showing {shown} of {len(SKILLS)} skills."


def set_skill_filter(kind, value):
    if kind == "status" and value in dict(SKILL_STATUS_FILTERS):
        runstate.skill_filter_status = value
    elif kind == "group" and value in dict(SKILL_GROUP_FILTERS):
        runstate.skill_filter_group = value
    else:
        return False
    return True


def clear_skill_filters():
    runstate.skill_search_text, runstate.skill_filter_status, runstate.skill_filter_group = "", "all", "any"
    for input_id in ("skill-search-input", "skill-map-search-input"):
        search = _el(input_id)
        if search is not None:
            search.value = ""


def _make_skill_filter_handler(kind, value):
    def handler(event=None):
        set_skill_filter(kind, value)
        render()
    return handler


SKILL_CHIP_HOLDERS = ("skill-filter-chips", "skill-map-chips")  # E-2: the map window carries its own copy of the same chips


def build_skill_filter_chips():
    """Builds the chip buttons once (so keyboard focus survives every render), in the skill list's filter bar and
    in the map's, which act on the same filter state."""
    for holder_id in SKILL_CHIP_HOLDERS:
        holder = _el(holder_id)
        if holder is None:
            continue
        holder.innerHTML = ""
        for kind, options in (("status", SKILL_STATUS_FILTERS), ("group", SKILL_GROUP_FILTERS)):
            group_el = document.createElement("div")
            group_el.className = "skill-filter-group"
            group_el.setAttribute("role", "group")
            group_el.setAttribute("aria-label", "Show by status" if kind == "status" else "Show by type")
            for value, label in options:
                chip = document.createElement("button")
                chip.className = "secondary skill-filter-chip"
                chip.setAttribute("type", "button")
                chip.setAttribute("data-filter-kind", kind)
                chip.setAttribute("data-filter-value", value)
                chip.setAttribute("aria-pressed", "false")
                chip.innerText = label
                chip.addEventListener("click", create_proxy(_make_skill_filter_handler(kind, value)))
                group_el.appendChild(chip)
            holder.appendChild(group_el)


def render_skill_filters():
    for holder_id in SKILL_CHIP_HOLDERS:
        holder = _el(holder_id)
        if holder is None:
            continue
        for group_el in holder.children:
            for chip in group_el.children:
                kind = chip.getAttribute("data-filter-kind")
                value = chip.getAttribute("data-filter-value")
                active = (runstate.skill_filter_status if kind == "status" else runstate.skill_filter_group) == value
                chip.setAttribute("aria-pressed", "true" if active else "false")
                if active:
                    chip.classList.add("selected")
                else:
                    chip.classList.remove("selected")
    for input_id in ("skill-search-input", "skill-map-search-input"):  # the two boxes always show the same words
        box = _el(input_id)
        if box is not None and str(box.value or "") != runstate.skill_search_text:
            box.value = runstate.skill_search_text
    visible = set(visible_skill_ids())
    for skill_id in SKILLS:
        row = _el(f"skill-{skill_id}-row")
        if row is not None:
            row.hidden = skill_id not in visible
    summary = _el("skill-filter-summary")
    if summary is not None:
        summary.innerText = skill_filter_summary()
    clear = _el("skill-filter-clear")
    if clear is not None:
        clear.hidden = not skill_filters_active()


# ---- E-25: named allocation presets -----------------------------------------


def preset_text(preset):
    parts = []
    if preset["resilience"]:
        parts.append(f"{preset['resilience']} resilience")
    if preset["growth"]:
        parts.append(f"{preset['growth']} growth")
    return f"{preset['name']}: {', '.join(parts)}"


def _preset_named(name):
    key = _clean_name(name, PRESET_NAME_MAX).casefold()
    for preset in runstate.meta["presets"]:
        if preset["name"].casefold() == key:
            return preset
    return None


def save_preset(name, resilience, growth):
    """Adds or replaces (same name, any case) a preset. Returns (ok, message)."""
    name = _clean_name(name, PRESET_NAME_MAX)
    if not name:
        return False, "Give the preset a name."
    try:
        resilience, growth = int(resilience), int(growth)
    except (TypeError, ValueError):
        return False, "Units must be whole numbers."
    if _units(resilience) is None or _units(growth) is None:
        return False, f"Units must be between 0 and {PRESET_UNITS_MAX}."
    if resilience + growth < 1:
        return False, "Choose at least one unit of resilience or growth."
    existing = _preset_named(name)
    if existing is None and len(runstate.meta["presets"]) >= PRESET_MAX:
        return False, f"You can keep up to {PRESET_MAX} presets. Delete one first."
    entry = {"name": name, "resilience": resilience, "growth": growth}
    if existing is None:
        runstate.meta["presets"].append(entry)
    else:
        runstate.meta["presets"][runstate.meta["presets"].index(existing)] = entry
    save_meta()
    return True, f"{'Updated' if existing else 'Saved'} preset: {preset_text(entry)}."


def delete_preset(name):
    existing = _preset_named(name)
    if existing is None:
        return False
    runstate.meta["presets"].remove(existing)
    save_meta()
    return True


def apply_preset(name, run_state=None):
    """Buys a preset's units as ONE undoable click: resilience first (stopping at the 85% cap),
    then growth, each limited by the resources in hand. Returns (message, bought_resilience,
    bought_growth)."""
    run_state = run_state or runstate.run
    preset = _preset_named(name)
    if preset is None:
        return "That preset no longer exists.", 0, 0
    if run_state.is_complete():
        return "This run is over: start a new run to use a preset.", 0, 0
    bought_r, bought_g = run_state.invest_preset(preset["resilience"], preset["growth"])
    if bought_r == preset["resilience"] and bought_g == preset["growth"]:
        return f"Applied {preset['name']}: bought {bought_r} resilience, {bought_g} growth.", bought_r, bought_g
    if not bought_r and not bought_g:
        return f"{preset['name']}: nothing bought, not enough resources.", 0, 0
    reasons = []
    if bought_r < preset["resilience"]:
        reasons.append("resilience is at its 85% cap" if run_state.resilience_units_to_cap() == 0 and run_state.resources >= RESILIENCE_COST else "not enough resources")
    if bought_g < preset["growth"] and "not enough resources" not in reasons:
        reasons.append("not enough resources")
    return (
        f"Applied {preset['name']} in part: bought {bought_r} of {preset['resilience']} resilience and "
        f"{bought_g} of {preset['growth']} growth ({'; '.join(reasons)}).",
        bought_r,
        bought_g,
    )


def this_turn_allocation(run_state=None):
    """(resilience, growth) units bought since the last event: what 'Use this turn' copies."""
    run_state = run_state or runstate.run
    resilience = growth = 0
    for kind, units in run_state.allocation_history:
        if kind == "resilience":
            resilience += units
        elif kind == "growth":
            growth += units
        else:  # a preset click
            resilience += units[0]
            growth += units[1]
    return resilience, growth


def _int_or_zero(text):
    try:
        return int(str(text).strip() or 0)
    except ValueError:
        return -1


def render_presets():
    presets = runstate.meta["presets"]
    if runstate.preset_selected and _preset_named(runstate.preset_selected) is None:
        runstate.preset_selected = ""
    if not runstate.preset_selected and presets:
        runstate.preset_selected = presets[0]["name"]
    row = _el("preset-apply-row")
    if row is not None:
        row.hidden = not presets or runstate.run.is_complete()
    select = _el("preset-select")
    if select is not None:
        select.innerHTML = ""
        for preset in presets:
            option = document.createElement("option")
            option.value = preset["name"]
            option.innerText = preset_text(preset)
            select.appendChild(option)
        select.value = runstate.preset_selected
    apply_button = _el("preset-apply-button")
    if apply_button is not None:
        apply_button.disabled = not presets or runstate.run.is_complete()
    listing = _el("preset-list")
    if listing is not None:
        listing.innerHTML = ""
        if not presets:
            empty = document.createElement("li")
            empty.innerText = "No presets yet. Buy some units, press Use this turn, name it and Save."
            listing.appendChild(empty)
        for preset in presets:
            item = document.createElement("li")
            item.className = "preset-item"
            label = document.createElement("span")
            label.className = "preset-item-label"
            label.innerText = preset_text(preset)
            item.appendChild(label)
            for action, text, extra in (("apply", "Apply", ""), ("delete", "Delete", " preset-delete")):
                button = document.createElement("button")
                button.className = "secondary preset-item-button" + extra
                button.setAttribute("type", "button")
                button.setAttribute("data-action", action)
                button.setAttribute("data-name", preset["name"])
                button.setAttribute("aria-label", f"{text} preset {preset['name']}")
                button.innerText = text
                button.disabled = action == "apply" and runstate.run.is_complete()
                item.appendChild(button)
            listing.appendChild(item)
    status = _el("preset-status")
    if status is not None:
        status.innerText = runstate.preset_status_text


# ---- E-30: save health badge --------------------------------------------------


def render_save_health():
    badge = _el("save-health")
    if badge is None:
        return
    state, text = storage_health()
    badge.setAttribute("data-state", state)
    last = _storage_state["last_ok"]
    badge.setAttribute("data-saved-at", str(int(last * 1000)) if last is not None else "")
    text_el = _el("save-health-text")
    if text_el is not None:
        text_el.innerText = text
    export_button = _el("save-health-export-button")
    if export_button is not None:
        export_button.hidden = state not in ("failed", "unsaved")
    alert = _el("save-health-alert")
    if alert is not None and state != runstate.save_health_announced:
        # A polite live region, written only when the state changes, so the ticking age never talks.
        alert.innerText = text if state in ("failed", "unsaved") else ("Progress is saving again." if runstate.save_health_announced in ("failed", "unsaved") else "")
    runstate.save_health_announced = state


# ---- E-3: purchase route planner ----------------------------------------------
def purchase_route(pinned=None):
    """Ordered skill ids to buy for the pinned skills: each pinned skill (in pin order) preceded
    by any prerequisite not yet owned or already in the list, so the order always respects the
    tree. Owned skills are skipped."""
    pinned = list(runstate.meta["pinned_skills"]) if pinned is None else list(pinned)
    order = []

    def visit(skill_id):
        if skill_id not in SKILLS or skill_id in runstate.skill_tree.unlocked or skill_id in order:
            return
        for prereq in SKILLS[skill_id].get("prereqs", []):
            visit(prereq)
        order.append(skill_id)

    for skill_id in pinned:
        visit(skill_id)
    return order


def route_rows():
    """One row per step: the skill, its cost, the running total, how many more knowledge points
    that total still needs beyond what is in hand and the estimated further runs (None while no
    run has been completed, since there is no earning rate yet)."""
    pinned = set(runstate.meta["pinned_skills"])
    rate = average_knowledge_per_run()
    rows, running = [], 0
    for skill_id in purchase_route():
        cost = SKILLS[skill_id]["cost"]
        running += cost
        short = max(0, running - runstate.skill_tree.knowledge_points)
        if short == 0:
            runs = 0
        elif rate and rate > 0:
            runs = max(1, math.ceil(short / rate))
        else:
            runs = None
        rows.append(
            {
                "skill_id": skill_id,
                "label": SKILLS[skill_id]["label"],
                "cost": cost,
                "running_total": running,
                "short": short,
                "runs": runs,
                "prerequisite_only": skill_id not in pinned,
            }
        )
    return rows


def route_row_text(index, row):
    when = "affordable now" if row["runs"] == 0 else (
        "complete a run for an estimate" if row["runs"] is None
        else f"about {row['runs']} more run{'s' if row['runs'] != 1 else ''}"
    )
    extra = " (needed first)" if row["prerequisite_only"] else ""
    return (
        f"{index}. {row['label']}{extra}: {row['cost']} knowledge, running total {row['running_total']}, "
        f"{when}"
    )


def route_summary_text():
    rows = route_rows()
    if not rows:
        return "Pin skills to plan a route."
    total = rows[-1]["running_total"]
    have = runstate.skill_tree.knowledge_points
    last = rows[-1]
    if last["runs"] == 0:
        ending = "you can afford the whole route now."
    elif last["runs"] is None:
        ending = "complete a run to estimate how long it will take."
    else:
        ending = f"about {last['runs']} more run{'s' if last['runs'] != 1 else ''} at your average of {average_knowledge_per_run():.1f} knowledge per run."
    return f"Route total {total} knowledge, {have} in hand: {ending}"


def render_route_planner():
    panel = _el("route-planner")
    if panel is None:
        return
    rows = route_rows()
    panel.hidden = not rows
    listing = _el("route-list")
    if listing is not None:
        listing.innerHTML = ""
        for index, row in enumerate(rows, start=1):
            item = document.createElement("li")
            item.className = "route-step" + (" route-step--prereq" if row["prerequisite_only"] else "")
            item.innerText = route_row_text(index, row)
            listing.appendChild(item)
    summary = _el("route-summary")
    if summary is not None:
        summary.innerText = route_summary_text()
    title = _el("route-planner-summary")
    if title is not None:
        title.innerText = f"Purchase route ({len(rows)} step{'s' if len(rows) != 1 else ''})" if rows else "Purchase route"


# ---- E-5: plain-text schedule --------------------------------------------------
def schedule_plain_text(run_state=None):
    """The whole schedule as words, one line, no colours or icons needed."""
    run_state = run_state or runstate.run
    parts = []
    for entry in schedule_strip_entries(run_state):
        if entry["state"] == "done":
            note = f"faced, {entry['damage']:.0f} damage"
        elif entry["state"] == "next":
            note = f"next, about {entry['damage']:.0f} damage"
        else:
            note = f"upcoming, about {entry['damage']:.0f} damage"
        parts.append(f"{entry['number']}. {entry['label']} ({note})")
    return "; ".join(parts) + "."


def render_schedule_text():
    text_el = _el("schedule-text")
    if text_el is not None:
        text_el.innerText = schedule_plain_text(runstate.run)
