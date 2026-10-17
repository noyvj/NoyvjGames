"""Tree species choice, forest switching and Survey mode (plan clears and replants, then commit)."""

import copy

import canopy_runstate as runstate
from canopy_helpers import (
    _el, _read_local_storage_item, _svg_text, _write_local_storage_item, plot_coordinate_label,
)
from canopy_realworld import render_grid_size_select
from canopy_rules import (
    BARE, RECOVERY_TICKS, SPECIES, SPECIES_MANGROVE, SPECIES_STANDARD, STAKEHOLDER_DECLINE_RELATIONS_DELTA,
    STAKEHOLDER_KIND_CLEAR, VALID_ACTIONS,
)
from canopy_summary import counterfactual_standing_value
from canopy_valuation import standing_forest_value


# GB-6 UI: the picker next to Replant. The choice is remembered on this device.
SPECIES_CHOICE_KEY = "canopy_species_choice_v1"
runstate.species_choice = SPECIES_STANDARD


def load_species_choice():
    value = _read_local_storage_item(SPECIES_CHOICE_KEY)
    runstate.species_choice = value if value in SPECIES and value != SPECIES_MANGROVE else SPECIES_STANDARD


def on_species_change(event=None):
    select = _el("species-select")
    value = getattr(select, "value", SPECIES_STANDARD)
    runstate.species_choice = value if value in SPECIES and value != SPECIES_MANGROVE else SPECIES_STANDARD
    _write_local_storage_item(SPECIES_CHOICE_KEY, runstate.species_choice)
    render_species_note()


def render_species_note():
    note = _el("species-note")
    if note is not None:
        spec = SPECIES[runstate.species_choice]
        note.innerText = f"{spec['label']}: {spec['note']}. Standing species mix gives +5% growth per extra species."
    select = _el("species-select")
    if select is not None:
        select.value = runstate.species_choice


# B-15 (2026-10-11): named local forests. The shared save widget (shared/save-widget.js) lets a browser that is not
# signed in keep up to three named forests, each with its own save code. Difficulty, grid size, pace and challenge
# are part of every save (current_difficulty, current_grid_size, ...), so each forest keeps its own simply by being
# saved and loaded. What the widget needs from the game: a way to start a fresh forest, and a way to refresh the
# page after the species choice (the one remembered per-forest browser setting) was swapped under it.
FOREST_PROFILE_KEYS = (SPECIES_CHOICE_KEY,)


def after_forest_switch():
    """Called by the save widget once another forest is open: re-reads the remembered species and shows every
    setting control as the loaded forest has it."""
    load_species_choice()
    render_species_note()
    render_grid_size_select()
    return True


survey_queue = []  # [{"kind": "clear" | "replant" | "decline", "plot": int}]


def _survey_find(kind, plot):
    for item in survey_queue:
        if item["kind"] == kind and item["plot"] == plot:
            return item
    return None


def survey_can_queue(kind, plot):
    """(allowed, reason) judged against the state the plan would leave the plot in."""
    if not (0 <= plot < len(runstate.plots)):
        return False, "No such plot."
    state = runstate.plots[plot].state
    cleared_in_plan = _survey_find("clear", plot) is not None
    replanted_in_plan = _survey_find("replant", plot) is not None
    if kind == "clear":
        if plot == runstate.heart_tree_index:
            return False, "The Heart Tree is never felled."
        if replanted_in_plan or "clear" not in VALID_ACTIONS[state] or cleared_in_plan:
            return False, "That plot cannot be cleared in this plan."
        return True, ""
    if kind == "replant":
        if replanted_in_plan or not (state == BARE or cleared_in_plan):
            return False, "Only a bare plot can be replanted."
        return True, ""
    if kind == "decline":
        request = runstate.pending_stakeholder_request
        if request is None or request.get("kind", STAKEHOLDER_KIND_CLEAR) != STAKEHOLDER_KIND_CLEAR:
            return False, "There is no clear request to decline."
        return (_survey_find("decline", request["plot_index"]) is None), "Already in the plan."
    return False, "Unknown action."


def survey_projection():
    """What the plan would do. Pure: reads the live forest, changes nothing."""
    income, value_loss, soil, replants, declines = 0.0, 0.0, [], 0, 0
    for item in survey_queue:
        plot = runstate.plots[item["plot"]]
        if item["kind"] == "clear":
            income += plot.value
            value_loss += plot.value
            twin = copy.copy(plot)
            twin.clear()
            soil.append((plot_coordinate_label(item["plot"]), round(twin.productivity_multiplier() * 100)))
        elif item["kind"] == "replant":
            replants += 1
        elif item["kind"] == "decline":
            declines += 1
    standing_now = standing_forest_value()
    ideal = counterfactual_standing_value()
    return {
        "income": income, "value_loss": value_loss, "standing_now": standing_now,
        "standing_after": standing_now - value_loss, "ideal": ideal,
        "gap_now": max(0.0, ideal - standing_now), "gap_after": max(0.0, ideal - (standing_now - value_loss)),
        "soil": soil, "replants": replants, "declines": declines,
        "relations_delta": STAKEHOLDER_DECLINE_RELATIONS_DELTA * declines,
    }


def survey_projection_text():
    if not survey_queue:
        return "Nothing planned yet: with Survey on, Clear, Replant and the decline button add to the plan instead of acting."
    p = survey_projection()
    parts = []
    if p["income"] or p["value_loss"]:
        parts.append(f"Income +{p['income']:.1f}; standing value {p['standing_now']:.1f} to {p['standing_after']:.1f}")
        parts.append(f"gap to the left-standing forest ({p['ideal']:.1f}) {p['gap_now']:.1f} to {p['gap_after']:.1f}")
    if p["soil"]:
        parts.append("soil after clearing: " + ", ".join(f"{label} {pct}%" for label, pct in p["soil"]))
    if p["replants"]:
        parts.append(f"{p['replants']} replant{'s' if p['replants'] != 1 else ''} (each recovers in {RECOVERY_TICKS} ticks once time runs)")
    if p["declines"]:
        parts.append(f"decline the request (community relations {p['relations_delta']:+d})")
    return "; ".join(parts) + "."


def survey_queue_lines():
    labels = {"clear": "Clear", "replant": "Replant", "decline": "Decline the request on"}
    return [f"{i + 1}. {labels[item['kind']]} {plot_coordinate_label(item['plot'])}" for i, item in enumerate(survey_queue)]


def _leave_survey_mode():
    runstate.survey_mode = False
    survey_queue.clear()
    runstate._last_tick_clock = None  # the long pause must not look like a lagging device to the performance guard


def render_survey():
    toggle, panel = _el("survey-toggle-button"), _el("survey-panel")
    if toggle is not None:
        toggle.innerText = "Cancel survey and resume" if runstate.survey_mode else "\U0001F50D Survey (pause and plan)"
        toggle.setAttribute("aria-pressed", "true" if runstate.survey_mode else "false")
    if panel is None:
        return
    panel.hidden = not runstate.survey_mode
    if not runstate.survey_mode:
        return
    status = _el("survey-status")
    if status is not None:
        status.innerText = "Survey mode: time is paused. Nothing you queue happens until you commit."
    queue = _el("survey-queue")
    if queue is not None:
        queue.innerHTML = "".join(f"<li>{_svg_text(line)}</li>" for line in survey_queue_lines())
    summary = _el("survey-projection")
    if summary is not None:
        summary.innerText = survey_projection_text()
    for button_id, enabled in (("survey-commit-button", bool(survey_queue)), ("survey-remove-button", bool(survey_queue)),
                               ("survey-decline-button", survey_can_queue("decline", runstate.pending_stakeholder_request["plot_index"] if runstate.pending_stakeholder_request else 0)[0] if runstate.pending_stakeholder_request else False)):
        button = _el(button_id)
        if button is not None:
            button.disabled = not enabled
