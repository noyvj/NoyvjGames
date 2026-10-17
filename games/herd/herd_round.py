"""Round play helpers: the bulk-buy stepper, the herd-size slider, the round-delta chips, undo, pace and save nudges.
Part of the split of the old single-file game.py: see "File map" in games/herd/CLAUDE.md.
"""

import time

from js import document, setTimeout
from pyodide.ffi import create_proxy

import herd_runstate as runstate
from herd_rules import (
    DECOUPLING_MEASURES, DELTA_FADE_MS, DELTA_KEYS, MIN_COUPLING_RATIO, SAVE_NUDGE_EVERY, UNDO_PENALTY_FUNDS,
)
from herd_model import clone_farm
from herd_visuals import genetics_rings_html, poultry_compare_html, render_season_calendar
from herd_pasture import hall_of_fame_html


BULK_BUTTON_IDS = {1: "bulk-1-button", 5: "bulk-5-button", "max": "bulk-max-button"}
BULK_HINT = "Tip: x5 and Max buy several units at once; the button shows the total cost first."


def bulk_button_label(key, name, single_cost, cost_format):
    """(label, disabled) for a Grow Herd or decoupling button under the current bulk mode.
    Mode 1 keeps the exact old label and rules."""
    units, total = runstate.farm.bulk_plan(key, runstate.bulk_mode)
    single = f"{name} ({format(single_cost, cost_format)})"
    if runstate.bulk_mode == 1:
        return single, units == 0
    if units == 0:
        if key in DECOUPLING_MEASURES and runstate.farm._efficiency_coupling_ratio() <= MIN_COUPLING_RATIO + 1e-9:
            return f"{name} (maxed out)", True
        return single, True
    return f"{name} x{units} ({total:g} total)", False


def bulk_note_message():
    if runstate.bulk_mode == 1:
        return BULK_HINT
    units, total = runstate.farm.bulk_plan("herd", runstate.bulk_mode)
    if units == 0:
        return "Grow Herd: nothing is affordable (or the cap blocks it) at this step size."
    before = runstate.farm.methane_this_round()
    after = before + units * runstate.farm.coupling_ratio()
    return (
        f"Grow Herd x{units} costs {total:g} in total; methane/round {before:.2f} → {after:.2f} ↑ "
        f"(herd {runstate.farm.herd_size} → {runstate.farm.herd_size + units})."
    )


def render_bulk_stepper():
    for mode, element_id in BULK_BUTTON_IDS.items():
        button = document.getElementById(element_id)
        selected = mode == runstate.bulk_mode
        button.setAttribute("aria-pressed", "true" if selected else "false")
        if selected:
            button.classList.add("selected")
        else:
            button.classList.remove("selected")
    document.getElementById("bulk-note").innerText = bulk_note_message()


# ---- R4-HEMO-8: herd-size slider (phone view) ---------------------------------------------
def herd_slider_plan(target):
    """What growing the herd to `target` would do, worked out on a scratch copy so nothing
    changes: (units bought, their total cost, methane per round after, income per round after).
    Stops at the funds or the regional cap, the same way Grow Herd does."""
    scratch = clone_farm(runstate.farm)
    units = 0
    while scratch.herd_size < target and scratch.grow_herd():
        units += 1
    return units, runstate.farm.funds - scratch.funds, scratch.methane_this_round(), scratch.income_breakdown()["total"]


def _herd_slider_target():
    """The slider's value, kept between the herd now and the herd the funds allow."""
    room = runstate.farm.bulk_plan("herd", "max")[0]
    try:
        value = int(float(getattr(document.getElementById("herd-size-slider"), "value", runstate.farm.herd_size)))
    except (TypeError, ValueError):
        value = runstate.farm.herd_size
    return max(runstate.farm.herd_size, min(value, runstate.farm.herd_size + room))


def render_herd_slider():
    slider = document.getElementById("herd-size-slider")
    room = runstate.farm.bulk_plan("herd", "max")[0]
    target = _herd_slider_target()
    slider.min = str(runstate.farm.herd_size)
    slider.max = str(runstate.farm.herd_size + room)
    slider.value = str(target)
    slider.disabled = room == 0
    units, cost, methane, income = herd_slider_plan(target)
    document.getElementById("herd-slider-value").innerText = str(runstate.farm.herd_size + units)
    document.getElementById("herd-slider-methane").innerText = (
        f"Methane per round: {runstate.farm.methane_this_round():.2f} \u2192 {methane:.2f}"
    )
    document.getElementById("herd-slider-income").innerText = (
        f"Income per round: {runstate.farm.income_breakdown()['total']:.1f} \u2192 {income:.1f}"
    )
    button = document.getElementById("herd-slider-buy-button")
    button.disabled = units == 0
    button.innerText = (
        f"Grow to {runstate.farm.herd_size + units} ({cost:g} funds)" if units else "Move the handle to plan a herd"
    )


def on_herd_slider_input(event=None):
    render_herd_slider()


def round_deltas(funds_before, methane_before, welfare_before, pressure_before):
    """How the four headline numbers moved over the round that just finished."""
    return {
        "funds": runstate.farm.funds - funds_before,
        "methane": runstate.farm.methane - methane_before,
        "welfare": runstate.farm.welfare() - welfare_before,
        "pressure": (runstate.farm.pressure_fraction() - pressure_before) * 100,
    }


def delta_chip_text(key, delta):
    """Shape plus sign plus words, never colour alone: up triangle, down triangle or a square for no change."""
    arrow = "▲" if delta > 1e-9 else ("▼" if delta < -1e-9 else "■")
    if key == "funds":
        return f"{arrow} Funds {delta:+.0f}"
    if key == "methane":
        return f"{arrow} Methane {delta:+.1f}"
    if key == "welfare":
        return f"{arrow} Welfare {delta:+.0f}"
    return f"{arrow} Pressure {delta:+.1f} pts"


def _delta_is_good(key, delta):
    if abs(delta) <= 1e-9:
        return None
    return delta > 0 if key in ("funds", "welfare") else delta < 0


def render_delta_chips():
    strip = document.getElementById("round-delta-strip")
    strip.hidden = not runstate.last_deltas
    for key in DELTA_KEYS:
        chip = document.getElementById(f"delta-chip-{key}")
        if key not in runstate.last_deltas:
            chip.hidden = True
            continue
        delta = runstate.last_deltas[key]
        chip.hidden = False
        chip.innerText = delta_chip_text(key, delta)
        pinned = key in runstate.delta_pinned
        chip.setAttribute("aria-pressed", "true" if pinned else "false")
        chip.title = "Pinned: click to let it fade." if pinned else "Click to pin this change so it stays."
        good = _delta_is_good(key, delta)
        for name, on in (
            ("delta-chip--good", good is True), ("delta-chip--bad", good is False),
            ("delta-chip--pinned", pinned), ("delta-chip--faded", runstate.delta_faded and not pinned),
        ):
            if on:
                chip.classList.add(name)
            else:
                chip.classList.remove(name)


def _schedule_delta_fade():
    runstate.delta_token += 1
    runstate.delta_faded = False
    token = runstate.delta_token

    def _fade(*args):
        if token == runstate.delta_token:
            runstate.delta_faded = True
            render_delta_chips()
        proxy.destroy()

    proxy = create_proxy(_fade)
    setTimeout(proxy, DELTA_FADE_MS)


def _make_delta_pin_handler(key):
    def handler(event=None):
        if key in runstate.delta_pinned:
            runstate.delta_pinned.discard(key)
        else:
            runstate.delta_pinned.add(key)
        render_delta_chips()
    return handler


# ---- GF-18 undo the last round ----------------------------------------------------------
UNDO_NOTE_READY = (
    f"Rewind to just before the last Advance Round. Once per game, costs {UNDO_PENALTY_FUNDS} funds; "
    "purchases made since are undone too."
)


def can_undo():
    if runstate.sandbox_active:
        return False
    snapshot = runstate.farm.undo_snapshot
    return (
        not runstate.farm.undo_used and isinstance(snapshot, dict)
        and snapshot.get("funds", 0) >= UNDO_PENALTY_FUNDS
    )


def undo_note_message():
    if runstate.farm.undo_used:
        return "You have used this game's undo."
    if runstate.farm.undo_snapshot is None:
        return f"Undo is ready after you advance a round (once per game, costs {UNDO_PENALTY_FUNDS} funds)."
    if not can_undo():
        return f"Not enough funds before that round to pay the {UNDO_PENALTY_FUNDS}-fund undo fee."
    return UNDO_NOTE_READY


def render_undo():
    document.getElementById("undo-round-button").disabled = not can_undo()
    document.getElementById("undo-note").innerText = undo_note_message()


# ---- F-28 pace note and save nudge ------------------------------------------------------
session_started = time.time()


def pace_note_message():
    if runstate.session_rounds <= 0:
        return ""
    minutes = max(0, int((time.time() - session_started) // 60))
    return (
        f"This sitting: {runstate.session_rounds} round{'s' if runstate.session_rounds != 1 else ''}, "
        f"about {minutes} min."
    )


def save_nudge_message():
    """A gentle prompt every SAVE_NUDGE_EVERY rounds played in one sitting, else empty."""
    if runstate.session_rounds > 0 and runstate.session_rounds % SAVE_NUDGE_EVERY == 0:
        return (
            f"{runstate.session_rounds} rounds this sitting. A good moment to save and take a break: "
            "the Save button keeps this farm safe."
        )
    return ""


def render_round_extras():
    """Everything the round-4 batch draws, run from render()."""
    render_bulk_stepper()
    render_herd_slider()
    render_delta_chips()
    render_undo()
    render_season_calendar()
    document.getElementById("genetics-rings").innerHTML = genetics_rings_html()
    document.getElementById("poultry-compare").innerHTML = poultry_compare_html()
    document.getElementById("hall-of-fame-list").innerHTML = hall_of_fame_html()
    note = pace_note_message()
    pace = document.getElementById("pace-note")
    pace.innerText = note
    pace.hidden = not note


def round_announcement(funds_before, methane_before):
    """Plain sentence for the aria-live region after Advance Round."""
    change = runstate.farm.funds - funds_before
    added = runstate.farm.methane - methane_before
    text = (
        f"Round {runstate.farm.round_number - 1} done. Funds {runstate.farm.funds:.0f}, {'up' if change >= 0 else 'down'} "
        f"{abs(change):.0f}. Methane added {added:.1f}, total {runstate.farm.methane:.0f}. Herd {runstate.farm.herd_size}."
    )
    if runstate.farm.last_round_perfect:
        text += f" Perfect round, streak {runstate.farm.perfect_streak}."
    return text
