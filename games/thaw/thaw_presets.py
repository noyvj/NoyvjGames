"""Strategy presets and the custom preset (G-20), the spend-confirmation threshold, hard mode (GG-23) and best-region messages."""

from js import document
from pyodide.ffi import create_proxy

import thaw_runstate as runstate
from thaw_bridge import _read_local_storage_item, _write_local_storage_item
from thaw_model import RegionState, deg, region, region_b, region_c, region_d
from thaw_rules import (
    CATEGORIES, CATEGORY_ICON, CATEGORY_LABEL, FORECAST_TOLERANCE, INVEST_COST, PLANNER_MAX_UNITS,
)


# G11: one-click preset strategies for Region B/C, so a player can set up
# a comparison strategy without manually clicking each category several
# times. Each preset spends as much of the region's *current* funds as
# it can afford in one go, repeatedly picking whichever weighted
# category is currently furthest behind its target share — a simple,
# deterministic way to approximate the named ratio without needing
# fractional investments (which don't exist in this game).
PRESET_WEIGHTS = {
    "growth": {"output": 1.0},
    "preservation": {"preserve": 0.6, "monitor": 0.4},
    "balanced": {"output": 1 / 3, "preserve": 1 / 3, "monitor": 1 / 3},
}


def preset_tooltip_text(preset_name):
    """Onboarding-tooltip audit fix: a preset button's own label ("Preset:
    Growth") names the strategy but not what clicking it actually does —
    it immediately spends everything the region can currently afford, in
    one go, rather than setting an ongoing policy. Built from
    PRESET_WEIGHTS directly so the tooltip text can't drift out of sync
    with the real weighting if it's ever tuned."""
    weights = PRESET_WEIGHTS[preset_name]
    if len(weights) == 1:
        (only_category,) = weights.keys()
        what = f"on {CATEGORY_LABEL[only_category]}"
    else:
        parts = [f"{CATEGORY_LABEL[c]} ({w * 100:.0f}%)" for c, w in weights.items()]
        what = "split roughly " + ", ".join(parts)
    return (
        f"Spends everything this region can currently afford right now, {what} "
        "— a one-time action, not an ongoing policy."
    )


def apply_preset(r, preset_name):
    """Applies one named preset's weighting to region `r`, spending as
    much as it can afford right now. Returns True if at least one
    investment was actually made (used by the caller to decide whether
    to flip preset_used_ever, and by tests to check a no-op call did
    nothing)."""
    weights = PRESET_WEIGHTS.get(preset_name)
    if not weights:
        return False
    invested_any = _run_preset(r, weights)
    if invested_any:
        runstate.preset_used_ever = True
    return invested_any


def _run_preset(r, weights):
    categories = list(weights.keys())
    spent = dict.fromkeys(categories, 0.0)
    invested_any = False
    while True:
        affordable = [c for c in categories if r.funds >= INVEST_COST[c]]
        if not affordable:
            break
        target = min(affordable, key=lambda c: spent[c] / weights[c])
        if not r.invest(target):
            break
        spent[target] += INVEST_COST[target]
        invested_any = True
    return invested_any


def preset_preview_text(r, preset_name):
    """G14: what clicking a preset would buy right now, computed on a
    scratch RegionState so nothing is committed. Used in the button's
    hover tooltip alongside the static explanation."""
    weights = PRESET_WEIGHTS.get(preset_name)
    if not weights:
        return ""
    scratch = RegionState()
    scratch.funds = r.funds
    if not _run_preset(scratch, weights):
        return "Right now: not enough funds for anything."
    parts = [
        f"{scratch.capacity[c]}x {CATEGORY_LABEL[c]}" for c in CATEGORIES if scratch.capacity[c]
    ]
    return "Right now this would buy: " + ", ".join(parts) + "."


# ===========================================================================
# G-20: one custom preset slot shared by Regions B and C. "Save this mix" copies the unit counts a
# region has built into the slot (so the player designs a mix by investing, then keeps it), and
# "Preset: Custom" spends a region's funds toward that same ratio exactly as the three named presets
# do. The slot is part of the save (only written once it holds a mix) and is validated on load.
# ===========================================================================


def custom_preset_weights():
    """The saved mix as the weights `_run_preset` takes, or None while the slot is empty."""
    if not runstate.custom_preset:
        return None
    return {c: float(n) for c, n in runstate.custom_preset.items() if n > 0} or None


def save_custom_preset(r):
    """Stores `r`'s current unit counts as the custom mix. False when the region has built nothing."""
    mix = {c: min(PLANNER_MAX_UNITS, int(r.capacity[c])) for c in CATEGORIES if r.capacity[c] > 0}
    if not mix:
        return False
    runstate.custom_preset = mix
    return True


def custom_preset_label():
    if not runstate.custom_preset:
        return "Preset: Custom (empty)"
    parts = " ".join(f"{CATEGORY_ICON[c]}{runstate.custom_preset[c]}" for c in CATEGORIES if c in runstate.custom_preset)
    return f"Preset: Custom ({parts})"


def custom_preset_tooltip_text():
    weights = custom_preset_weights()
    if not weights:
        return (
            "Empty. Build the mix you want in this region with the investment buttons, then press "
            "'Save this mix as Custom'. Regions B and C share the one slot."
        )
    total = sum(weights.values())
    parts = ", ".join(f"{CATEGORY_LABEL[c]} ({w / total * 100:.0f}%)" for c, w in weights.items())
    return (
        f"Spends everything this region can currently afford right now, split roughly {parts} "
        "— a one-time action, not an ongoing policy."
    )


def custom_preset_preview_text(r):
    weights = custom_preset_weights()
    if not weights:
        return ""
    scratch = RegionState()
    scratch.funds = r.funds
    if not _run_preset(scratch, weights):
        return "Right now: not enough funds for anything."
    parts = [f"{scratch.capacity[c]}x {CATEGORY_LABEL[c]}" for c in CATEGORIES if scratch.capacity[c]]
    return "Right now this would buy: " + ", ".join(parts) + "."


def apply_custom_preset(r):
    """Spends `r`'s funds toward the saved mix. Counts as using a preset for the achievement."""
    weights = custom_preset_weights()
    if not weights:
        return False
    invested_any = _run_preset(r, weights)
    if invested_any:
        runstate.preset_used_ever = True
    return invested_any


def _clean_custom_preset(raw):
    """A saved mix, or None if it is missing or has anything unreadable in it."""
    if not isinstance(raw, dict) or not raw:
        return None
    mix = {}
    for key, value in raw.items():
        if key not in CATEGORIES or isinstance(value, bool) or not isinstance(value, int):
            return None
        if not 1 <= value <= PLANNER_MAX_UNITS:
            return None
        mix[key] = value
    return mix


def render_custom_preset(prefix, r):
    button = document.getElementById(f"{prefix}-preset-custom-button")
    button.innerText = custom_preset_label()
    button.disabled = not runstate.custom_preset
    button.title = custom_preset_tooltip_text() + (
        " " + custom_preset_preview_text(r) if runstate.custom_preset and not runstate.hard_mode else ""
    )
    save = document.getElementById(f"{prefix}-preset-save-button")
    save.disabled = not any(r.capacity[c] > 0 for c in CATEGORIES)
    save.title = "Keeps the units this region has built as the shared Custom mix (replaces the old one)."


# ===========================================================================
# G-23: an optional "are you sure?" step for big spends. A Settings choice (Never, or ask whenever one
# click would spend more than 100, 150 or 250 funds) routed through the shared ConfirmDialog. It covers
# the one-click bulk spends: the four presets, and an emergency rescue. A single unit costs 20 or 25 so
# it is never asked. The choice is a per-browser preference (localStorage), not part of the save.
# ===========================================================================
CONFIRM_THRESHOLDS = (0, 100, 150, 250)  # 0 = never ask
CONFIRM_THRESHOLD_KEY = "thaw_confirm_threshold_v1"


def load_confirm_threshold():
    raw = _read_local_storage_item(CONFIRM_THRESHOLD_KEY)
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return 0
    return value if value in CONFIRM_THRESHOLDS else 0


def set_confirm_threshold(value):
    """Stores the choice; anything that is not one of CONFIRM_THRESHOLDS becomes 'never'."""
    try:
        value = int(value)
    except (TypeError, ValueError):
        value = 0
    runstate.confirm_threshold = value if value in CONFIRM_THRESHOLDS else 0
    _write_local_storage_item(CONFIRM_THRESHOLD_KEY, str(runstate.confirm_threshold))
    return runstate.confirm_threshold


def confirm_threshold_text():
    if not runstate.confirm_threshold:
        return "Big spends go ahead with one click."
    return f"You will be asked first whenever one click would spend more than {runstate.confirm_threshold} funds."


def _preset_spend(r, weights):
    """Funds a preset would spend right now, found on a scratch region so nothing is bought."""
    if not weights:
        return 0.0
    scratch = RegionState()
    scratch.funds = r.funds
    _run_preset(scratch, weights)
    return r.funds - scratch.funds


def _guard_spend(amount, message_template, action_id, on_confirm):
    """True when a confirm dialog was opened (on_confirm runs later, if the player agrees) and the caller
    must stop; False when the caller should simply go ahead now (no threshold, a small spend, or no
    dialog on this page, which is how the tests run)."""
    if not runstate.confirm_threshold or amount <= runstate.confirm_threshold:
        return False
    try:
        from js import window  # noqa: PLC0415 -- Pyodide-only, deliberately lazy
    except ImportError:
        return False
    dialog = getattr(window, "ConfirmDialog", None)
    if dialog is None:
        return False
    dialog.ask(
        id=action_id,
        message=message_template.format(amount=f"{amount:.0f}"),
        confirmLabel="Spend it",
        allowSkip=False,
        onConfirm=create_proxy(on_confirm),
    )
    return True


def render_confirm_threshold():
    select = document.getElementById("confirm-threshold-select")
    select.value = str(runstate.confirm_threshold)
    document.getElementById("confirm-threshold-note").innerText = confirm_threshold_text()


# ===========================================================================
# GG-23: an opt-in hard mode. Chosen before round 1 (like the long game), it takes away the previews:
# the Advance Round tooltip with its next-round and ten-round numbers, the "+8% dampening" style
# forecasts beside the invest buttons, the preset "this would buy" lines and the forecast planner.
# The warming rate, the dampening readout and every mechanic stay exactly as they are, so it is the
# same game read with less help. The optional forecast box becomes the way to test your own read of the
# numbers, and the recap ends with a reveal of how close the forecasts you locked in actually were.
# Nothing here is luck, nothing is timed, and it is never required.
# ===========================================================================


def can_toggle_hard_mode():
    return all(r.round_number == 1 for r in (region, region_b, region_c, region_d))


def set_hard_mode(enabled):
    """Turns hard mode on or off; only possible before the first round has been played."""
    if not can_toggle_hard_mode():
        return False
    runstate.hard_mode = bool(enabled)
    return True


def hard_mode_text():
    if runstate.hard_mode:
        return (
            "Hard mode is on: no next-round preview, no forecast numbers beside the invest buttons, no "
            "preset previews and no forecast planner. Your own forecasts (below) get a reveal in the recap."
        )
    return (
        "Hard mode is off. Turn it on before round 1 to play without the previews and test your own read of "
        "the numbers; the recap then reveals how close your forecasts were."
    )


def hard_mode_reveal_lines():
    """The end-of-run reveal (empty unless hard mode is on): how close the locked-in forecasts were."""
    if not runstate.hard_mode or region.round_number <= 1:
        return []
    if runstate.forecast_total <= 0:
        return [
            "Hard mode reveal: you did not lock in any forecast, so there is no guess to compare. "
            "The forecast box is how you test your own read of the numbers."
        ]
    average = runstate.forecast_miss_total / runstate.forecast_total
    plural = "" if runstate.forecast_total == 1 else "s"
    verdict = (
        "right on the money." if average <= FORECAST_TOLERANCE
        else "close; the warming rate on screen is all you need to do it exactly."
        if average <= 1.0
        else "a wide miss, but every forecast makes the next one easier to read."
    )
    return [
        f"Hard mode reveal: you locked in {runstate.forecast_total} forecast{plural}, {runstate.forecast_hits} on target. "
        f"On average you were {deg(average)} off the real figure: {verdict}"
    ]


def _render_hard_mode():
    button = document.getElementById("hard-mode-toggle-button")
    button.innerText = "Hard mode: on" if runstate.hard_mode else "Hard mode: off"
    button.disabled = not can_toggle_hard_mode()
    document.getElementById("hard-mode-display").innerText = hard_mode_text() + (
        "" if can_toggle_hard_mode() else " (Locked once the first round has been played.)"
    )


def best_region_identifier():
    """G2/G15: which of the three player-managed regions (never Region D
    — it's a deliberate worst-case baseline, not a competitor for
    "best") currently has the lowest temperature. Ties resolve to
    whichever region is listed first (Region A), which is an acceptable,
    documented tie-break rather than a meaningful ranking."""
    candidates = [("A", region), ("B", region_b), ("C", region_c)]
    best_label, _ = min(candidates, key=lambda pair: pair[1].temperature)
    return best_label


def best_region_message():
    """G2: an explicit end-of-session (or any-time) "which region did
    best" line, comparing current temperature across the three
    player-managed regions."""
    label = best_region_identifier()
    best = {"A": region, "B": region_b, "C": region_c}[label]
    cap = best.capacity
    return (
        f"Region {label} currently has the lowest temperature ({deg(best.temperature, plus=True)}) "
        f"among your three managed regions, with an investment mix of "
        f"{cap['preserve']} preserve / {cap['monitor']} monitor / {cap['output']} output."
    )
