"""The legacy history, scar tiers, the mentor, Past Runs (notes, sort, filter, archive, compare), improvement streaks and expected-damage helpers, ETA and pinned skills."""

import math

from js import document, localStorage

import aftermath_runstate as runstate
from aftermath_bonuses import (
    DEFAULT_LOOK, entry_look, entry_seconds, fastest_run_number, format_duration, look_label,
)
from aftermath_persist import (
    RUN_NOTES_MAX, RUN_NOTE_MAX_CHARS, SETTLEMENT_NAME_MAX, run_log_history, save_meta, skill_tree_strength,
)
from aftermath_rules import (
    DEFAULT_SCENARIO, EVENT_BASE_DAMAGE, EVENT_CATEGORY, EVENT_ICON, EVENT_LABEL, GROWTH_COST,
    GROWTH_INCOME_PER_UNIT, RESILIENCE_COST, SCENARIOS, SEVERITY_LIFETIME_RANGE_CAP,
    SEVERITY_VARIATION_RANGE_PER_SKILL, SKILLS, adjusted_score, adjusted_text, severity_bounds,
    severity_label,
)


# ===========================================================================
# E4: legacy-system expansion (beyond the original single flavor-text line
# above). legacy_message() and the ever-weathered `legacy_events` set are
# untouched -- this is an additive, more detailed view built from the new
# per-event-type `legacy_event_counts`.
# ===========================================================================
def legacy_history_summary():
    """Every event type this settlement has ever weathered, with how many
    times, sorted by label for a stable display order. Empty entries
    (count 0, which shouldn't occur but would if a saved dict somehow had
    a zero) are skipped."""
    return [
        {
            "type": event_type,
            "label": EVENT_LABEL[event_type],
            "icon": EVENT_ICON[event_type],
            "count": count,
        }
        for event_type, count in sorted(runstate.legacy_event_counts.items(), key=lambda pair: EVENT_LABEL[pair[0]])
        if count > 0
    ]


# ===========================================================================
# V-CD-6: legacy weathering scars -- a genuinely visual marker on the
# settlement itself, referencing prior-run history, addressing the
# completion-audit finding that E4 above only ever produced a text chip
# row (legacy_history_summary()), not any visual marker on the settlement
# as the original Pass-2 idea described. One scar per event *category*
# (not one per exact event type -- six more rooftop-style dots stacked on
# top of the eight skill/toughest badges the settlement already carries
# would be exactly the crowding problem the UI-decluttering pass above
# was written to avoid), escalating through three tiers as that
# category's aggregated legacy_event_counts total climbs. Purely derived
# from already-persisted legacy_event_counts -- no new storage key.
# ===========================================================================
LEGACY_SCAR_CATEGORIES = ("weather", "non-weather", "social", "health")
LEGACY_SCAR_TIER_THRESHOLDS = (1, 3, 6)  # cumulative count needed for tier 1 / 2 / 3


def legacy_category_totals():
    """Aggregate legacy_event_counts (per exact event type, cross-run) up
    to the three event categories, so the settlement's ground shows one
    scar per category rather than one per exact event type. Always
    returns all three categories, 0 where nothing of that category has
    ever been weathered yet."""
    totals = {category: 0 for category in LEGACY_SCAR_CATEGORIES}
    for event_type, count in runstate.legacy_event_counts.items():
        category = EVENT_CATEGORY.get(event_type)
        if category in totals:
            totals[category] += count
    return totals


def legacy_scar_tier(count):
    """0 (no scar yet) through 3 (heaviest), from how many times this
    settlement has weathered that category across every run ever
    played."""
    tier = 0
    for threshold in LEGACY_SCAR_TIER_THRESHOLDS:
        if count >= threshold:
            tier += 1
    return tier


def legacy_scar_tiers():
    return {category: legacy_scar_tier(total) for category, total in legacy_category_totals().items()}


# ===========================================================================
# E7: reviewing a specific past run's full event-by-event breakdown, from
# the new run_log_history persisted alongside (not instead of) the
# existing run_history score-only list.
# ===========================================================================


# E27: the resilience mentor. An OPTIONAL guided mode (off by default, saved per
# browser, distinct from the one-time tutorial): one inline suggestion, right
# where the decision is made, that reads the live run and says what it would
# do and why. Advice only: it never acts for the player and never changes any
# number. Rules are checked in order and the first that applies wins.
MENTOR_STORAGE_KEY = "aftermath_mentor_v1"


def load_mentor_enabled():
    return localStorage.getItem(MENTOR_STORAGE_KEY) == "1"


def mentor_suggestion(run_state):
    """The single most useful piece of advice for this moment, as one sentence."""
    if run_state.is_complete():
        return (
            "The run is over. Spend the knowledge you earned in the skill tree: even a rough run "
            "always leaves the next one a little stronger."
        )
    event_type = run_state.next_event_type()
    label = EVENT_LABEL[event_type]
    expected, _severity = expected_next_event_damage(run_state)
    resilience_cost = RESILIENCE_COST
    if run_state.event_index == 0 and run_state.resilience_capacity == 0 and run_state.growth_capacity == 0:
        return (
            f"Start by choosing a balance. Resilience ({resilience_cost} resources) cuts the damage of every shock; "
            f"growth ({GROWTH_COST} resources) earns {GROWTH_INCOME_PER_UNIT} more each round. "
            f"A {label} is coming first."
        )
    if expected >= run_state.resources:
        if run_state.resources >= resilience_cost:
            return (
                f"Careful: the coming {label} would take about {expected:.0f} and you have {run_state.resources:.0f}. "
                f"Put resources into resilience now to shrink the hit."
            )
        return (
            f"The coming {label} could take about {expected:.0f} of your {run_state.resources:.0f}. "
            f"You can't afford resilience right now, so brace: the run still teaches something."
        )
    if run_state.resilience_capacity == 0:
        return (
            f"You have no resilience yet, so the {label} lands at full force (about {expected:.0f}). "
            f"One resilience purchase would already soften every shock after it."
        )
    if run_state.growth_capacity == 0 and run_state.event_index >= 2 and run_state.resources >= GROWTH_COST:
        return (
            "You have no growth: every event drains a pool that never refills. One growth unit "
            f"pays back {GROWTH_INCOME_PER_UNIT} each round."
        )
    events_left = len(run_state.schedule) - run_state.event_index
    return (
        f"You're in a steady position. The {label} should cost about {expected:.0f}; "
        f"{events_left} event(s) remain, so keep some resources in reserve."
    )


def render_mentor():
    toggle = document.getElementById("mentor-toggle")
    hint = document.getElementById("mentor-hint")
    toggle.checked = runstate.mentor_enabled
    hint.hidden = not runstate.mentor_enabled
    hint.innerText = f"\U0001F9ED Mentor: {mentor_suggestion(runstate.run)}" if runstate.mentor_enabled else ""


CATEGORY_ICON = {"weather": "🌦️", "non-weather": "🏗️", "social": "👥", "health": "🩺"}


def _render_event_breakdown_lines(container, event_log, show_category=False):
    for entry in event_log:
        line = document.createElement("p")
        line.className = (
            f"past-run-event event-category--{EVENT_CATEGORY[entry['type']]} "
            f"severity--{severity_label(entry['severity'])}"
        )
        category = EVENT_CATEGORY[entry["type"]]
        category_prefix = f"{CATEGORY_ICON[category]} " if show_category else ""
        if show_category:
            line.title = f"{category.replace('-', ' ')} event"
        line.innerText = (
            f"{category_prefix}{EVENT_ICON[entry['type']]} {EVENT_LABEL[entry['type']]} — "
            f"{entry['damage']:.0f} damage ({severity_label(entry['severity'])} intensity)"
        )
        container.appendChild(line)


def new_record_run_indexes():
    """E16: indexes into run_log_history of runs whose score beat every
    earlier run's (the first run is never a 'record' -- nothing to beat).
    Those cards get a one-shot CSS flourish when the panel is opened."""
    records = set()
    best = None
    for index, entry in enumerate(run_log_history):
        if not isinstance(entry, dict):
            continue  # a damaged stored entry never breaks the list
        if entry.get("neighbour_aid"):  # R-31: a run helped by neighbour aid is never a record and sets no bar
            continue
        score = entry.get("score", 0)
        if best is not None and score > best:
            records.add(index)
        if best is None or score > best:
            best = score
    return records


# ---- E-22 / E-21 / E-20: notes, sort, filter, archive and compare in Past Runs ----
# All view state lives in memory (it is a way of looking at the list, not progress).
# The notes and the archive list live in `meta`, so they ride the progress export.
PAST_RUN_SORTS = ("newest", "oldest", "score_high", "score_low", "score_adjusted", "mode", "fastest")


def run_mode(entry):
    """What kind of run a logged run was, worked out from its event log (the log has
    no scenario field): the scenario whose schedule it matches (or None) and whether it
    is an Extended Run (the schedule twice over)."""
    types = [e.get("type") for e in (entry.get("event_log") or []) if isinstance(e, dict)]
    custom = entry.get("custom_schedule")  # E-13: runs on a built schedule are tagged when logged
    if isinstance(custom, str) and custom:
        return {"scenario": None, "extended": False, "custom": custom}
    length = len(SCENARIOS[DEFAULT_SCENARIO]["schedule"])
    extended = len(types) == 2 * length and types[:length] == types[length:]
    base = types[:length] if extended else types
    scenario = next((key for key, spec in SCENARIOS.items() if spec["schedule"] == base), None)
    return {"scenario": scenario, "extended": extended}


def run_mode_label(entry):
    mode = run_mode(entry)
    if mode.get("custom"):
        return f"Custom schedule: {mode['custom']}"
    label = SCENARIOS[mode["scenario"]]["label"] if mode["scenario"] else "Custom schedule"
    return label + (", extended" if mode["extended"] else "")


def run_note(run_number):
    return runstate.meta["run_notes"].get(str(run_number), "")


def set_run_note(run_number, text):
    """E-22: keeps a short note for a completed run (cleared by an empty string)."""
    text = str(text or "").strip()[:RUN_NOTE_MAX_CHARS]
    if not text:
        runstate.meta["run_notes"].pop(str(run_number), None)
    elif str(run_number) in runstate.meta["run_notes"] or len(runstate.meta["run_notes"]) < RUN_NOTES_MAX:
        runstate.meta["run_notes"][str(run_number)] = text
    save_meta()
    return text


def set_run_archived(run_number, archived):
    """E-21: archiving only hides a run from the default list; its score, its knowledge
    points and every stat built from it are untouched."""
    current = set(runstate.meta["archived_runs"])
    if archived:
        current.add(run_number)
    else:
        current.discard(run_number)
    runstate.meta["archived_runs"] = sorted(current)
    save_meta()


def past_runs_view(history=None):
    """The run log entries that pass the current filter, in the current sort order
    (each as (position in run_log_history, entry))."""
    history = run_log_history if history is None else history
    archived = set(runstate.meta["archived_runs"])
    rows = []
    for index, entry in enumerate(history):
        if not isinstance(entry, dict) or "run_number" not in entry:
            continue
        if entry["run_number"] in archived and not runstate.past_runs_show_archived:
            continue
        mode = run_mode(entry)
        if runstate.past_runs_filter == "custom" and not (mode.get("custom") or mode["scenario"] is None):
            continue
        if runstate.past_runs_filter == "extended" and not mode["extended"]:
            continue
        if runstate.past_runs_filter == "standard" and mode["extended"]:
            continue
        if runstate.past_runs_filter.startswith("scenario:") and mode["scenario"] != runstate.past_runs_filter.split(":", 1)[1]:
            continue
        rows.append((index, entry))
    if runstate.past_runs_sort == "oldest":
        rows.sort(key=lambda r: r[0])
    elif runstate.past_runs_sort == "score_high":
        rows.sort(key=lambda r: (-r[1].get("score", 0), -r[0]))
    elif runstate.past_runs_sort == "score_low":
        rows.sort(key=lambda r: (r[1].get("score", 0), -r[0]))
    elif runstate.past_runs_sort == "score_adjusted":  # E-9
        rows.sort(key=lambda r: (-adjusted_score(r[1].get("score", 0), r[1].get("event_log")), -r[0]))
    elif runstate.past_runs_sort == "mode":
        rows.sort(key=lambda r: (run_mode_label(r[1]), -r[0]))
    elif runstate.past_runs_sort == "fastest":  # GE-23: timed runs first, quickest at the top; untimed runs follow, newest first
        rows.sort(key=lambda r: (entry_seconds(r[1]) is None, entry_seconds(r[1]) or 0, -r[0]))
    else:
        rows.sort(key=lambda r: -r[0])
    return rows


def _run_by_number(run_number):
    for entry in run_log_history:
        if isinstance(entry, dict) and entry.get("run_number") == run_number:
            return entry
    return None


def compare_runs_rows(entry_a, entry_b):
    """E-20: the two runs side by side: a header row, a stats row each for score, damage,
    resilience, growth and knowledge (with the difference), then the events in order with
    the damage difference on the one that was harsher."""
    rows = []
    for label, key, fmt in (
        ("Score", "score", "{:.0f}"),
        ("Damage taken", "damage_taken", "{:.0f}"),
        ("Resilience", "resilience_capacity", "{:.0f}"),
        ("Growth", "growth_capacity", "{:.0f}"),
        ("Knowledge earned", "knowledge_earned", "{:.0f}"),
    ):
        a, b = entry_a.get(key, 0), entry_b.get(key, 0)
        diff = b - a
        sign = "+" if diff > 0 else "\u2212"
        change = f" ({sign}{fmt.format(abs(diff))})" if abs(diff) >= 0.5 else " (same)"
        rows.append({
            "kind": "stat",
            "left": f"{label}: {fmt.format(a)}",
            "right": f"{label}: {fmt.format(b)}{change}",
            "different": abs(diff) >= 0.5,
        })
    log_a, log_b = entry_a.get("event_log") or [], entry_b.get("event_log") or []
    for position in range(max(len(log_a), len(log_b))):
        ea = log_a[position] if position < len(log_a) else None
        eb = log_b[position] if position < len(log_b) else None

        def describe(event, other):
            if event is None:
                return "(no event)"
            text = f"{position + 1}. {EVENT_ICON[event['type']]} {EVENT_LABEL[event['type']]}: {event['damage']:.0f} damage"
            if other is not None and other["type"] == event["type"] and abs(event["damage"] - other["damage"]) >= 0.5:
                text += " (harsher)" if event["damage"] > other["damage"] else " (gentler)"
            elif other is not None and other["type"] != event["type"]:
                text += " (different event)"
            return text

        rows.append({
            "kind": "event",
            "left": describe(ea, eb),
            "right": describe(eb, ea),
            "different": ea is None or eb is None or ea["type"] != eb["type"] or abs(ea["damage"] - eb["damage"]) >= 0.5,
        })
    return rows


def compare_summary_text(entry_a, entry_b):
    diff = entry_b.get("score", 0) - entry_a.get("score", 0)
    if abs(diff) < 0.5:
        return f"Run #{entry_a['run_number']} and Run #{entry_b['run_number']} finished with the same score."
    better, worse = (entry_b, entry_a) if diff > 0 else (entry_a, entry_b)
    return f"Run #{better['run_number']} scored {abs(diff):.0f} more than Run #{worse['run_number']}."


def render_past_run_compare():
    box = document.getElementById("past-runs-compare")
    if box is None:
        return
    box.innerHTML = ""
    entries = [_run_by_number(n) for n in runstate.past_runs_compare]
    entries = [e for e in entries if e is not None]
    if len(entries) < 2:
        box.hidden = True
        return
    box.hidden = False
    entry_a, entry_b = entries[0], entries[1]
    heading = document.createElement("p")
    heading.className = "past-run-title"
    heading.innerText = "Side by side: " + compare_summary_text(entry_a, entry_b)
    box.appendChild(heading)
    grid = document.createElement("div")
    grid.className = "compare-grid"
    for entry in (entry_a, entry_b):
        head = document.createElement("p")
        head.className = "compare-head"
        head.innerText = f"Run #{entry['run_number']} ({run_mode_label(entry)})"
        grid.appendChild(head)
    for row in compare_runs_rows(entry_a, entry_b):
        for side in ("left", "right"):
            cell = document.createElement("p")
            cell.className = f"compare-cell compare-cell--{row['kind']}" + (" compare-cell--different" if row["different"] else "")
            cell.innerText = row[side]
            grid.appendChild(cell)
    box.appendChild(grid)


def streak_log_indexes():
    """GE-22: positions in run_log_history that belong to the current improvement streak
    (empty below STREAK_MIN)."""
    scores = [e.get("score", 0) for e in run_log_history if isinstance(e, dict)]
    streak = improvement_streak(scores)
    if streak < STREAK_MIN:
        return set()
    return set(range(len(scores) - streak, len(scores)))


def _past_run_card(index, entry, is_record):
    run_number = entry["run_number"]
    card = document.createElement("div")
    card.className = "past-run-card past-run-card--record" if is_record else "past-run-card"
    if run_number in runstate.meta["archived_runs"]:
        card.className += " past-run-card--archived"
    if index in streak_log_indexes():
        card.className += " past-run-card--streak"
    title = document.createElement("p")
    title.className = "past-run-title"
    title.innerText = (
        f"{'🏆 ' if is_record else ''}{'🔥 ' if index in streak_log_indexes() else ''}Run #{run_number} — score {entry['score']:.0f} "
        f"({adjusted_text(entry['score'], entry.get('event_log'))}; resilience {entry['resilience_capacity']}, growth {entry['growth_capacity']}, "
        f"+{entry['knowledge_earned']} knowledge)"
        f" · {run_mode_label(entry)}"
        + (f" · neighbour aid +{entry['neighbour_aid']:.0f}" if entry.get("neighbour_aid") else "")  # R-31
        + (f" · {look_label(entry_look(entry))}" if entry_look(entry) != DEFAULT_LOOK else "")  # GE-25
        + (f" · \u23f1 {format_duration(entry_seconds(entry))}{' (fastest)' if run_number == fastest_run_number() else ''}" if entry_seconds(entry) is not None else "")  # GE-23
        + (" · archived" if run_number in runstate.meta["archived_runs"] else "")
    )
    card.appendChild(title)
    _render_event_breakdown_lines(card, entry["event_log"], show_category=True)
    note = document.createElement("input")
    note.className = "past-run-note-input"
    note.setAttribute("type", "text")
    note.setAttribute("maxlength", str(RUN_NOTE_MAX_CHARS))
    note.setAttribute("placeholder", "Add a note about this run")
    note.setAttribute("aria-label", f"Note for run {run_number}")
    note.setAttribute("data-action", "note")
    note.setAttribute("data-run", str(run_number))
    note.value = run_note(run_number)
    card.appendChild(note)
    actions = document.createElement("div")
    actions.className = "past-run-actions"
    compare_label = document.createElement("label")
    compare_label.className = "past-run-compare-label"
    compare_box = document.createElement("input")
    compare_box.setAttribute("type", "checkbox")
    compare_box.setAttribute("data-action", "compare")
    compare_box.setAttribute("data-run", str(run_number))
    compare_box.checked = run_number in runstate.past_runs_compare
    compare_label.appendChild(compare_box)
    compare_text = document.createElement("span")
    compare_text.innerText = " Compare"
    compare_label.appendChild(compare_text)
    actions.appendChild(compare_label)
    archive_button = document.createElement("button")
    archive_button.className = "secondary past-run-archive-button"
    archive_button.setAttribute("type", "button")
    archive_button.setAttribute("data-action", "archive")
    archive_button.setAttribute("data-run", str(run_number))
    archive_button.innerText = "Unarchive" if run_number in runstate.meta["archived_runs"] else "Archive"
    actions.appendChild(archive_button)
    card.appendChild(actions)
    return card


# ---- GE-22: run-improvement streak --------------------------------------------
STREAK_MIN = 2


def record_flags(scores):
    """For each score in completion order: did it beat every earlier run? (The first
    run has nothing to beat, so it is never a record.)"""
    flags, best = [], None
    for score in scores:
        flags.append(best is not None and score > best)
        if best is None or score > best:
            best = score
    return flags


def improvement_streak(scores):
    """How many of the most recent runs, in a row, each beat the best before them."""
    count = 0
    for flag in reversed(record_flags(scores)):
        if not flag:
            break
        count += 1
    return count


def streak_text(scores=None):
    scores = runstate.run_history if scores is None else scores
    streak = improvement_streak(scores)
    if streak < STREAK_MIN:
        return ""
    return f"\U0001F525 Improvement streak: {streak} runs in a row beat your previous best."


def render_past_runs_panel():
    toggle = document.getElementById("past-runs-toggle-button")
    panel = document.getElementById("past-runs-panel")
    toggle.innerText = "Hide Past Runs" if runstate.past_runs_open else f"📜 Review Past Runs ({len(run_log_history)})"
    panel.hidden = not runstate.past_runs_open
    if not runstate.past_runs_open:
        return
    listing = document.getElementById("past-runs-list")
    controls = document.getElementById("past-runs-controls")
    if listing is None:
        return  # a cached older page without the list container
    listing.innerHTML = ""
    if controls is not None:
        controls.hidden = not run_log_history
    render_past_run_compare()
    if not run_log_history:
        empty = document.createElement("p")
        empty.innerText = "No detailed run history yet — complete a run to start building one."
        listing.appendChild(empty)
        return

    record_indexes = new_record_run_indexes()
    rows = past_runs_view()
    status = document.getElementById("past-runs-status")
    if status is not None:
        hidden_count = len(run_log_history) - len(rows)
        status.innerText = f"Showing {len(rows)} of {len(run_log_history)} runs." + (
            " Archived and filtered-out runs keep their score and knowledge." if hidden_count else ""
        )
    if not rows:
        empty = document.createElement("p")
        empty.innerText = "No runs match this view. Change the filter or show archived runs."
        listing.appendChild(empty)
        return
    for index, entry in rows:
        listing.appendChild(_past_run_card(index, entry, index in record_indexes))


# ===========================================================================
# E8/E16: an "expected damage this event" preview, with the underlying
# severity multiplier shown numerically rather than just mild/typical/
# severe -- both derived from the exact same deterministic formula
# resolve_next_event() itself will use, so the preview is exact, not a
# rough estimate.
# ===========================================================================
def expected_next_event_damage(run_state):
    """Returns (damage, severity) for run_state's next scheduled event, or
    None once the run is already complete."""
    if run_state.is_complete():
        return None
    event_type = run_state.next_event_type()
    severity = run_state.severity_at(run_state.event_index)
    damage = EVENT_BASE_DAMAGE[event_type] * severity * (1 - run_state.mitigation_for(event_type))
    return damage, severity


def expected_damage_range(run_state):
    """E14: (low, high) damage for the next event across the whole
    severity band this settlement can face (min/max multiplier at the
    current skill level and career length). The center estimate above is
    exact for this run number; the range shows how much a different run
    number could swing the same event."""
    event_type = run_state.next_event_type()
    if run_state.normalised:
        # E-4: the draw is fixed, so the number is exact.
        exact = EVENT_BASE_DAMAGE[event_type] * run_state.severity_at(run_state.event_index) * (1 - run_state.mitigation_for(event_type))
        return exact, exact
    if run_state.run_number <= 1:
        exact = EVENT_BASE_DAMAGE[event_type] * (1 - run_state.mitigation_for(event_type))
        return exact, exact
    low_sev, high_sev = severity_bounds(skill_tree_strength())
    base = EVENT_BASE_DAMAGE[event_type] * (1 - run_state.mitigation_for(event_type))
    return base * low_sev, base * high_sev


def severity_tooltip_text(run_number):
    """E20: how skill-tree strength (and career length) affect severity."""
    strength = skill_tree_strength()
    low, high = severity_bounds(strength)
    if run_number <= 1:
        return "Run 1 is always exactly 1.00× severity. From run 2 onward, severity varies per event."
    return (
        f"Severity multiplier varies between {low:.2f}× and {high:.2f}×. Base spread is 0.85×–1.15×; "
        f"each unlocked skill (you have {strength}) widens it by {SEVERITY_VARIATION_RANGE_PER_SKILL:.2f} "
        f"each side, and each completed run adds a little more (up to {SEVERITY_LIFETIME_RANGE_CAP:.2f}). "
        f"The center stays 1.00× — a stronger tree faces bigger swings, not a higher average."
    )


# ===========================================================================
# E17: "toughest run yet" -- the lowest-scoring completed run. run_history
# is a flat list of scores in completion order (no run_number stored
# alongside each), so the displayed "Run #N" is that run's *position* in
# the list, not necessarily its literal run_number -- these coincide for
# the overwhelmingly common case (runs completed in strict numeric order)
# and only diverge in the rare stale-reload edge case the save-system
# double-award guard already documents elsewhere in this file. Good enough
# for a flavor comparison; run_log_history (E7) has the exact run_number
# for any run a player wants to inspect precisely.
# ===========================================================================
def toughest_run_yet():
    if not runstate.run_history:
        return None
    worst_score = min(runstate.run_history)
    return runstate.run_history.index(worst_score) + 1, worst_score


def toughest_run_sequence():
    """E10: the event sequence of the toughest run yet, as a list of
    {"type", "damage", "severity"} dicts, pulled from run_log_history (the
    detailed per-run log) by matching the toughest score. None if there's
    no detailed log for it (e.g. progress imported from a code, which
    carries scores only)."""
    toughest = toughest_run_yet()
    if toughest is None:
        return None
    for entry in run_log_history:
        if abs(entry.get("score", -1) - toughest[1]) < 1e-9 and entry.get("event_log"):
            return entry["event_log"]
    return None


def toughest_run_text():
    toughest = toughest_run_yet()
    if toughest is None:
        return ""
    text = f"Toughest run yet: Run #{toughest[0]} scored {toughest[1]:.0f}"
    sequence = toughest_run_sequence()
    if sequence:
        text += f" ({adjusted_text(toughest[1], sequence)})"  # E-9
    if sequence:
        parts = [f"{EVENT_ICON[e['type']]} {EVENT_LABEL[e['type']]}" for e in sequence if e["type"] in EVENT_LABEL]
        text += " — " + " → ".join(parts)
    return text


def average_severity(event_log):
    if not event_log:
        return 1.0
    return sum(e.get("severity", 1.0) for e in event_log) / len(event_log)


def _report_hardest_schedule(run_state):
    """E23: a run that ended with resources left feeds its average event
    severity to the shared opt-in leaderboard widget (which only submits for
    an opted-in, signed-in player and remembers the personal best). Run 1 is
    always exactly 1.00x, so only the harsher later runs can climb the board."""
    if run_state.resources <= 0 or not run_state.event_log:
        return
    if run_state.aid_given:  # R-31: a run that received neighbour aid never competes on the board
        return
    try:
        from js import window  # noqa: PLC0415 -- Pyodide-only, deliberately lazy
    except ImportError:
        return
    board = getattr(window, "NoyvjLeaderboard", None)
    if board is not None:
        board.report(
            "aftermath", "hardest_schedule", round(average_severity(run_state.event_log), 3),
            f"run {run_state.run_number}",
        )


def toughest_survived_run_badge_earned():
    """E12: a settlement-art badge for having come through a run whose
    average event severity was harsh ('severe' band) without ending at zero
    resources -- a personal-best-style marker for surviving a genuinely
    tough schedule, separate from the per-skill badges."""
    for entry in run_log_history:
        if entry.get("neighbour_aid"):  # R-31: a run helped by neighbour aid does not count
            continue
        if entry.get("score", 0) > 0 and severity_label(average_severity(entry.get("event_log", []))) == "severe":
            return True
    return False


def toughest_badge_title():
    """E-9: the badge's tooltip. Earned: names the run and shows the raw and adjusted score;
    not yet: says what earns it."""
    for entry in run_log_history:
        if entry.get("neighbour_aid"):  # R-31
            continue
        if entry.get("score", 0) > 0 and severity_label(average_severity(entry.get("event_log", []))) == "severe":
            return (
                f"Survived a run at severe average intensity: run {entry.get('run_number', '?')} scored "
                f"{entry['score']:.0f} ({adjusted_text(entry['score'], entry.get('event_log'))})"
            )
    return "Survived a run at severe average intensity (not earned yet)"


def runs_completed_text():
    name = runstate.meta["settlement_name"]
    prefix = f"{name} — " if name else ""
    return f"{prefix}Runs completed: {len(runstate.run_history)}"


# E30a/E30b: "X runs until affordable" estimate + pinned skills.
def average_knowledge_per_run():
    runs = len(runstate.run_history)
    if runs <= 0:
        return None
    return runstate.skill_tree.lifetime_knowledge / runs


def runs_until_affordable(skill_id):
    """Estimated number of further completed runs before skill_id becomes
    affordable at the average lifetime knowledge-earn rate. 0 if already
    affordable, None if there's no earn-rate data yet (no runs completed)."""
    needed = SKILLS[skill_id]["cost"] - runstate.skill_tree.knowledge_points
    if needed <= 0:
        return 0
    rate = average_knowledge_per_run()
    if not rate or rate <= 0:
        return None
    return max(1, math.ceil(needed / rate))


def _eta_text(skill_id):
    runs = runs_until_affordable(skill_id)
    if runs is None:
        return "Complete a run for an estimate"
    if runs == 0:
        return "Affordable now"
    return f"~{runs} run{'s' if runs != 1 else ''} until affordable"


def toggle_pin_skill(skill_id):
    if skill_id not in SKILLS or skill_id in runstate.skill_tree.unlocked:
        return False
    if skill_id in runstate.meta["pinned_skills"]:
        runstate.meta["pinned_skills"].remove(skill_id)
    else:
        runstate.meta["pinned_skills"].append(skill_id)
    save_meta()
    return True


def pinned_skills_text():
    pinned = [sid for sid in runstate.meta["pinned_skills"] if sid in SKILLS and sid not in runstate.skill_tree.unlocked]
    if not pinned:
        return ""
    return "📌 Saving toward: " + "; ".join(f"{SKILLS[sid]['label']} ({_eta_text(sid)})" for sid in pinned)


def set_settlement_name(name):
    runstate.meta["settlement_name"] = (name or "").strip()[:SETTLEMENT_NAME_MAX]
    save_meta()
