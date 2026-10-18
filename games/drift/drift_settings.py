"""Confirm large moves, the manual-save nudge and glossary popovers."""

from js import document
from pyodide.ffi import create_proxy

import drift_runstate as runstate
from drift_model_region import region
from drift_pages import _read_local_storage_item
from drift_rules import (
    CAPACITY_LABEL, POLICIES, REALLOCATION_FUNDS_COST, REALLOCATION_LOSS_FRACTION, REALLOCATION_UNITS,
)
from drift_tiers import _now_ms


# ---- I-28: confirm large moves -------------------------------------------------------------------
CONFIRM_STORAGE_KEY = "drift_confirm_threshold_v1"
CONFIRM_CHOICES = (0, 25, 50, 75)  # 0 = never ask; otherwise ask when a move uses more than this percent


def _load_confirm_threshold():
    raw = _read_local_storage_item(CONFIRM_STORAGE_KEY)
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return 0
    return value if value in CONFIRM_CHOICES else 0


runstate.confirm_threshold = _load_confirm_threshold()


def confirm_threshold_text():
    if not runstate.confirm_threshold:
        return "Never asks. Every purchase and move goes straight through."
    return (
        f"Asks first when a policy purchase uses more than {runstate.confirm_threshold}% of your funds, or a reallocation moves "
        f"more than {runstate.confirm_threshold}% of that type's capacity or costs more than {runstate.confirm_threshold}% of your funds, "
        "and shows the cost."
    )


def policy_move_share(policy):
    return region.policy_cost(policy) / region.funds if region.funds > 0 else 0.0


def realloc_move_share(from_type):
    capacity = region.capacity.get(from_type, 0.0)
    cap_share = REALLOCATION_UNITS / capacity if capacity > 0 else 0.0
    funds_share = REALLOCATION_FUNDS_COST / region.funds if region.funds > 0 else 0.0
    return max(cap_share, funds_share)


def _guard_large_move(share, message, action_id, on_confirm):
    """True when a confirm dialog was opened (on_confirm runs later if the player agrees) and the caller must
    stop; False when the caller should go ahead now (no threshold, a small move, or no dialog on the page)."""
    if not runstate.confirm_threshold or share * 100 <= runstate.confirm_threshold:
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
        message=message,
        confirmLabel="Go ahead",
        allowSkip=False,
        onConfirm=create_proxy(on_confirm),
    )
    return True


def policy_confirm_message(policy):
    cost = region.policy_cost(policy)
    return (
        f"Fund {POLICIES[policy]['label']} to level {region.policy_level[policy] + 1} for {cost:.0f} of your "
        f"{region.funds:.0f} funds ({policy_move_share(policy) * 100:.0f}%)? A policy level is permanent."
    )


def realloc_confirm_message(from_type, to_type):
    kept = REALLOCATION_UNITS * (1 - REALLOCATION_LOSS_FRACTION)
    return (
        f"Move {REALLOCATION_UNITS:.0f} {CAPACITY_LABEL[from_type]} capacity (of {region.capacity[from_type]:.0f}) to "
        f"{CAPACITY_LABEL[to_type]}? It costs {REALLOCATION_FUNDS_COST:.0f} of your {region.funds:.0f} funds and "
        f"{REALLOCATION_LOSS_FRACTION * 100:.0f}% of the moved capacity is lost, so {CAPACITY_LABEL[to_type]} gains {kept:.0f}."
    )


def render_confirm_threshold():
    document.getElementById("confirm-threshold-select").value = str(runstate.confirm_threshold)
    document.getElementById("confirm-threshold-note").innerText = confirm_threshold_text()


# ---- I-27: manual-save nudge -----------------------------------------------------------------------
SAVE_NUDGE_ROUNDS = 10
SAVED_AT_KEY = "savedat:drift"  # written by shared/save-widget.js after every successful save


def _saved_at_ms():
    raw = _read_local_storage_item(SAVED_AT_KEY)
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return 0
    return value if value > 0 else 0


runstate._last_seen_saved_at = _saved_at_ms()


def _note_save_activity():
    """If the save widget has stamped a newer save time since we last looked, a save just happened: the
    rounds-since-save count restarts from the current round."""
    current = _saved_at_ms()
    if current != runstate._last_seen_saved_at:
        runstate._last_seen_saved_at = current
        runstate.save_baseline_round = region.round_number


def _ago_text(milliseconds):
    seconds = max(0.0, milliseconds / 1000.0)
    if seconds < 45:
        return "just now"
    if seconds < 5400:
        return f"{max(1, round(seconds / 60))} min ago"
    if seconds < 129600:
        return f"{round(seconds / 3600)} h ago"
    return f"{round(seconds / 86400)} d ago"


def rounds_since_save():
    return region.round_number - max(runstate.save_baseline_round, runstate.nudge_snooze_round)


def save_nudge_text():
    """The gentle reminder, or '' while fewer than SAVE_NUDGE_ROUNDS rounds have passed since the last save."""
    rounds = rounds_since_save()
    if rounds <= SAVE_NUDGE_ROUNDS:
        return ""
    saved_at = _saved_at_ms()
    when = f"saved {_ago_text(_now_ms() - saved_at)}" if saved_at else "not saved in this browser yet"
    return (
        f"You have played {rounds} rounds since this region was last saved ({when}). "
        "The save button keeps it safe whenever you are ready."
    )


def render_save_nudge():
    _note_save_activity()
    text = save_nudge_text()
    document.getElementById("save-nudge-box").hidden = not text
    document.getElementById("save-nudge").innerText = text


# ---- I-29: glossary popovers -----------------------------------------------------------------------
GLOSSARY = {
    "capacity": {
        "label": "Capacity",
        "text": "Capacity is the housing, integration services and infrastructure your region has built. Total capacity is set "
                "against everyone who has arrived: whatever it fails to cover becomes strain.",
        "real_story": True,
    },
    "strain": {
        "label": "Strain",
        "text": "Strain is the share of everyone who has arrived that your capacity does not yet cover. It cuts your income each "
                "round and stays in your service-quality average even after you catch up.",
        "real_story": False,
    },
    "integration": {
        "label": "Integration",
        "text": "Integration is when a waiting arrival becomes an integrated resident, with language, work and education access. "
                "Only Integration Services moves people across, and integrated people then contribute funds back.",
        "real_story": True,
    },
    "control": {
        "label": "Control region",
        "text": "The control region is a passive copy of your region with the same pressure and no investment. Its dotted grey line "
                "on the trend graph shows what would have happened without your choices.",
        "real_story": False,
    },
}
GLOSSARY_ORDER = ("capacity", "strain", "integration", "control")


def _show_glossary(term, pin=False):
    runstate.glossary_open = term
    runstate.glossary_pinned = pin or (runstate.glossary_pinned and runstate.glossary_open == term)
    render_glossary()


def render_glossary():
    pop = document.getElementById("glossary-pop")
    for term in GLOSSARY_ORDER:
        button = document.getElementById(f"glossary-{term}-button")
        button.setAttribute("aria-expanded", "true" if term == runstate.glossary_open else "false")
        if term == runstate.glossary_open:
            button.classList.add("active")
        else:
            button.classList.remove("active")
    pop.hidden = runstate.glossary_open is None
    if runstate.glossary_open is None:
        return
    entry = GLOSSARY[runstate.glossary_open]
    document.getElementById("glossary-pop-text").innerText = f"{entry['label']}: {entry['text']}"
    document.getElementById("glossary-more-button").hidden = not entry["real_story"]
