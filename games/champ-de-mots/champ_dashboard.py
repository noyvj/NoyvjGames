"""The progress dashboard, the spaced-repetition explainer, the grammar deep-dive and the cultural notes panel.
Part of the split of the old single-file game.py: see "File map" in games/champ-de-mots/CLAUDE.md.
"""

from js import document
from pyodide.ffi import create_proxy

import champ_runstate as runstate
from champ_rules import (
    AUTOMATION_INTERVAL_DAYS, BLOOMING_INTERVAL_DAYS, COMBO_BONUS_PER_STEP,
    CONFIDENT_WRONG_PENALTY_MULTIPLIER, DEFAULT_EASE, EASE_CORRECT_BONUS, EASE_INCORRECT_PENALTY,
    FIRST_INTERVAL_DAYS, MAX_COMBO_BONUS, MAX_EASE, MIN_EASE, PRACTICE_MODES, PRACTICE_MODE_CAP,
    RESET_INTERVAL_DAYS, SECOND_INTERVAL_DAYS, UNSURE_WRONG_PENALTY_MULTIPLIER,
)
from champ_catalog import CULTURAL_NOTES_BY_SEQUENCE
from champ_model import state
from champ_grading import ERROR_PATTERN_LABELS, ERROR_PATTERN_ORDER, weeds_confusions_for
from champ_labels import STAGE_ICON, STAGE_LABEL
from champ_util import _element
from champ_stats import (
    dashboard_days_since_last_touch, dashboard_row_mastery, dashboard_stage_distribution,
    dashboard_weakest_topics,
)
from champ_points import QUEST_REWARD_POINTS, practice_score, quest_lines, quest_summary_text
from champ_leech import (
    export_weak_items_anki, export_weak_items_csv, leech_plots, leech_summary_text, session_highlights_text,
    weak_items,
)


# render() is defined in champ_renderer, which comes later in the module list; champ_renderer puts it here when it
# loads (see the end of champ_renderer.py). Calls below find it at run time.
render = None


# ===========================================================================
# L15: an optional grammar deep-dive for grammar plots -- everything the game
# already knows about a topic, gathered in one place beyond the terse
# in-practice rule. Derived entirely from catalog data and existing helpers
# (no hand-written text to drift): the full rule, every example, the known
# look-alikes it is easy to mix up with, and where the plot stands.
# ===========================================================================
DEEP_DIVE_NO_RULE = "This topic has no written rule yet; the examples below are the pattern."


def grammar_deep_dive(plot):
    """Plain data for the deep-dive panel, or None for a non-grammar plot."""
    if plot is None or plot.topic_type != "grammar":
        return None
    due = ""
    if plot.next_due is not None:
        days = plot.next_due - state.current_day
        due = "due now" if days <= 0 else f"next due in {days} day{'s' if days != 1 else ''}"
    return {
        "title": plot.topic_title,
        "rule": plot.rule or DEEP_DIVE_NO_RULE,
        "has_rule": bool(plot.rule),
        "examples": [(item["fr"], item["en"]) for item in plot.items],
        "confusions": weeds_confusions_for(plot),
        "stage": STAGE_LABEL[plot.stage],
        "due": due,
    }


def on_toggle_deepdive(event=None):
    runstate.deepdive_open = not runstate.deepdive_open
    render_deepdive()


def render_deepdive():
    toggle = _element("practice-deepdive-button")
    panel = _element("practice-deepdive")
    plot = state.plots_by_id.get(runstate.current_question["plot_id"]) if runstate.practice_open and runstate.current_question else None
    data = grammar_deep_dive(plot)
    if data is None:
        toggle.hidden = True
        panel.hidden = True
        return
    toggle.hidden = False
    toggle.innerText = "Hide grammar deep-dive" if runstate.deepdive_open else "\U0001F4D8 Grammar deep-dive"
    toggle.setAttribute("aria-expanded", "true" if runstate.deepdive_open else "false")
    panel.hidden = not runstate.deepdive_open
    if not runstate.deepdive_open:
        return
    panel.innerHTML = ""

    def line(class_name, text):
        node = document.createElement("p")
        node.className = class_name
        node.innerText = text
        panel.appendChild(node)

    line("deepdive-title", data["title"])
    line("deepdive-rule", data["rule"])
    line("deepdive-heading", "Examples")
    for fr, en in data["examples"]:
        line("deepdive-example", f"{fr} \u2014 {en}")
    if data["confusions"]:
        line("deepdive-heading", "Easy to mix up with")
        line("deepdive-confusions", ", ".join(f"\u201c{c}\u201d" for c in data["confusions"]))
    status = data["stage"] + (f" \u00b7 {data['due']}" if data["due"] else "")
    line("deepdive-status", "Where this plot stands: " + status)


def on_toggle_dashboard(event=None):
    runstate.dashboard_open = not runstate.dashboard_open
    render()


def srs_explanation_lines():
    """L23 -- a plain-language account of the scheduler, built from the real
    constants above so it can never drift from what actually runs."""
    return [
        f"Every plot has a review interval and an ease score (starts at {DEFAULT_EASE}, always kept between {MIN_EASE} and {MAX_EASE}).",
        f"Your first correct answer schedules the next review {FIRST_INTERVAL_DAYS} day out and your second {SECOND_INTERVAL_DAYS} days out.",
        "From the third correct answer on, the interval grows by its ease score each time (and always by at least one day).",
        f"Each correct answer nudges ease up by {EASE_CORRECT_BONUS}; each wrong answer drops it by {EASE_INCORRECT_PENALTY} and sends the plot back to a {RESET_INTERVAL_DAYS}-day interval with its streak reset.",
        f"Combo bonus: each answer in a correct row shortens the wait a little more, {int(COMBO_BONUS_PER_STEP * 100)}% per step, capped at {int(MAX_COMBO_BONUS * 100)}%.",
        f"Confidence: tagging 'Sure' before a wrong answer makes that penalty {CONFIDENT_WRONG_PENALTY_MULTIPLIER}x; tagging 'Not sure' makes it {UNSURE_WRONG_PENALTY_MULTIPLIER}x. It never changes what a correct answer does.",
        f"Growth stages follow the interval: Blooming from {BLOOMING_INTERVAL_DAYS} days, Automated from {AUTOMATION_INTERVAL_DAYS} days. A plot never visibly shrinks back a stage.",
    ]


def render_srs_explainer():
    details = _element("srs-explainer")
    details.hidden = not runstate.dashboard_open
    body = _element("srs-explainer-body")
    body.innerHTML = ""
    for line in srs_explanation_lines():
        item = document.createElement("p")
        item.className = "srs-explainer-line"
        item.innerText = line
        body.appendChild(item)


dashboard_proxies = []


def _destroy_dashboard_proxies():
    for proxy in dashboard_proxies:
        proxy.destroy()
    dashboard_proxies.clear()


def _dashboard_line(panel, class_name, text):
    line = document.createElement("p")
    line.className = class_name
    line.innerText = text
    panel.appendChild(line)
    return line


def _dashboard_button(panel, label, handler):
    button = document.createElement("button")
    button.className = "secondary dashboard-action"
    button.type = "button"
    button.innerText = label
    proxy = create_proxy(handler)
    button.addEventListener("click", proxy)
    dashboard_proxies.append(proxy)
    panel.appendChild(button)
    return button


def _render_dashboard_extras(panel):
    """Round 3 batch 2: today's daily goals, the stubborn weeds, the weak-items
    export and this session's highlights."""
    _dashboard_line(panel, "dashboard-heading", quest_summary_text())
    for text, progress, target, done in quest_lines():
        mark = "Done" if done else f"{progress} of {target}"
        _dashboard_line(panel, "dashboard-practice-row", f"{text} — {mark}")
    _dashboard_line(
        panel,
        "dashboard-empty",
        f"Each finished goal earns {QUEST_REWARD_POINTS} practice points. Goals change with the in-game day; nothing carries over or runs out.",
    )

    _dashboard_line(panel, "dashboard-heading", "Stubborn weeds and weak items")
    _dashboard_line(panel, "dashboard-practice-row", leech_summary_text())
    for plot in leech_plots()[:5]:
        _dashboard_line(panel, "dashboard-weakest-topic", f"{plot.label} (wk {plot.sequence}), missed {plot.fail_run} in a row")
    weak_count = len(weak_items())
    _dashboard_line(
        panel,
        "dashboard-practice-row",
        f"{weak_count} weak item{'s' if weak_count != 1 else ''} ready to export (stubborn weeds, mix-ups, last-missed and phrasebook plots).",
    )
    _dashboard_button(panel, "Download weak items (CSV)", export_weak_items_csv)
    _dashboard_button(panel, "Download for Anki (tab-separated)", export_weak_items_anki)

    highlights = session_highlights_text()
    if highlights:
        _dashboard_line(panel, "dashboard-heading", "Session highlights")
        _dashboard_line(panel, "dashboard-practice-row", highlights)


def render_dashboard():
    panel = _element("dashboard-panel")
    toggle = _element("dashboard-toggle-button")
    toggle.innerText = "Hide progress dashboard" if runstate.dashboard_open else "Progress dashboard"
    panel.hidden = not runstate.dashboard_open
    render_srs_explainer()
    if not runstate.dashboard_open:
        return

    _destroy_dashboard_proxies()
    panel.innerHTML = ""

    since = dashboard_days_since_last_touch()
    since_line = document.createElement("p")
    since_line.className = "dashboard-since"
    if since is None:
        since_line.innerText = "Nothing watered yet."
    elif since == 0:
        since_line.innerText = "Last watered something today."
    elif since == 1:
        since_line.innerText = "Last watered something 1 day ago."
    else:
        since_line.innerText = f"Last watered something {since} days ago."
    panel.appendChild(since_line)

    health_heading = document.createElement("p")
    health_heading.className = "dashboard-heading"
    health_heading.innerText = "Farm health"
    panel.appendChild(health_heading)
    for stage, count, percent in dashboard_stage_distribution():
        health_row = document.createElement("p")
        health_row.className = "dashboard-health-row"
        health_row.innerText = f"{STAGE_ICON[stage]} {STAGE_LABEL[stage].split(' — ')[0]}: {count} ({percent:.0f}%)"
        health_bar = document.createElement("span")
        health_bar.className = "dashboard-health-bar"
        health_bar.style.width = f"{percent:.1f}%"
        health_row.appendChild(health_bar)
        panel.appendChild(health_row)

    mastery_heading = document.createElement("p")
    mastery_heading.className = "dashboard-heading"
    mastery_heading.innerText = "Mastery by week"
    panel.appendChild(mastery_heading)
    mastery_list = document.createElement("div")
    mastery_list.className = "dashboard-mastery-list"
    for row in state.rows:
        if not state.is_row_unlocked(row.sequence):
            continue
        line = document.createElement("p")
        line.className = "dashboard-mastery-row"
        line.innerText = f"{row.label} — {dashboard_row_mastery(row.sequence):.0f}%"
        mastery_list.appendChild(line)
    panel.appendChild(mastery_list)

    weakest_heading = document.createElement("p")
    weakest_heading.className = "dashboard-heading"
    weakest_heading.innerText = "Could use more water"
    panel.appendChild(weakest_heading)
    weakest = dashboard_weakest_topics()
    if not weakest:
        empty = document.createElement("p")
        empty.className = "dashboard-empty"
        empty.innerText = "Nothing stands out yet — water a few plots first."
        panel.appendChild(empty)
    else:
        weakest_list = document.createElement("div")
        weakest_list.className = "dashboard-weakest-list"
        for entry in weakest:
            line = document.createElement("p")
            line.className = "dashboard-weakest-topic"
            line.innerText = f"{entry['title']} (wk {entry['sequence']})"
            weakest_list.appendChild(line)
        panel.appendChild(weakest_list)

    practice_heading = document.createElement("p")
    practice_heading.className = "dashboard-heading"
    practice_heading.innerText = f"Practice progress — {practice_score()} {'point' if practice_score() == 1 else 'points'}"
    panel.appendChild(practice_heading)
    practice_list = document.createElement("div")
    practice_list.className = "dashboard-practice-list"
    for mode, label in PRACTICE_MODES.items():
        entry = runstate.practice_ledger[mode]
        line = document.createElement("p")
        line.className = "dashboard-practice-row"
        if entry["total"]:
            accuracy = round(entry["correct"] / entry["total"] * 100)
            line.innerText = (
                f"{label} — {entry['correct']} of {entry['total']} correct ({accuracy}%) · "
                f"{entry['points']}/{PRACTICE_MODE_CAP} points"
            )
        else:
            line.innerText = f"{label} — not played yet"
        practice_list.appendChild(line)
    panel.appendChild(practice_list)

    _render_dashboard_extras(panel)

    patterns_heading = document.createElement("p")
    patterns_heading.className = "dashboard-heading"
    patterns_heading.innerText = "Common patterns"
    panel.appendChild(patterns_heading)
    present_patterns = [p for p in ERROR_PATTERN_ORDER if runstate.error_pattern_counts.get(p)]
    if not present_patterns:
        empty = document.createElement("p")
        empty.className = "dashboard-empty"
        empty.innerText = "No wrong typed answers yet — nothing to spot a pattern in."
        panel.appendChild(empty)
    else:
        patterns_list = document.createElement("div")
        patterns_list.className = "dashboard-patterns-list"
        for pattern in present_patterns:
            line = document.createElement("p")
            line.className = "dashboard-pattern-row"
            count = runstate.error_pattern_counts[pattern]
            times = "time" if count == 1 else "times"
            line.innerText = f"{ERROR_PATTERN_LABELS[pattern]} — {count} {times}"
            patterns_list.appendChild(line)
        panel.appendChild(patterns_list)


def on_toggle_cultural_notes(event=None):
    runstate.cultural_notes_open = not runstate.cultural_notes_open
    render()


def render_cultural_notes():
    panel = _element("cultural-notes-panel")
    toggle = _element("cultural-notes-toggle-button")
    toggle.innerText = "Hide cultural notes" if runstate.cultural_notes_open else "Cultural notes"
    panel.hidden = not runstate.cultural_notes_open
    if not runstate.cultural_notes_open:
        return

    panel.innerHTML = ""
    # Only rows already unlocked -- same spoiler-avoidance posture as
    # proficiency tests and bonus sections, which are also gated to
    # unlocked weeks rather than previewing content the syllabus hasn't
    # reached yet.
    visible = [
        (row, CULTURAL_NOTES_BY_SEQUENCE[row.sequence])
        for row in state.rows
        if row.sequence in CULTURAL_NOTES_BY_SEQUENCE and state.is_row_unlocked(row.sequence)
    ]
    if not visible:
        empty = document.createElement("p")
        empty.className = "cultural-note-empty"
        empty.innerText = "No cultural notes for the weeks you've unlocked yet."
        panel.appendChild(empty)
        return

    for row, note in visible:
        entry = document.createElement("div")
        entry.className = "cultural-note"
        heading = document.createElement("p")
        heading.className = "cultural-note-week"
        heading.innerText = row.label
        body = document.createElement("p")
        body.className = "cultural-note-text"
        body.innerText = note
        entry.appendChild(heading)
        entry.appendChild(body)
        panel.appendChild(entry)
