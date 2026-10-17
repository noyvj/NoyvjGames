"""Reset Session confirm text and the reset button render (reset_session itself is in canopy_renderer)."""

from js import document
from pyodide.ffi import create_proxy

import canopy_runstate as runstate
from canopy_valuation import standing_forest_value


# B2 (planning/TODO.md "Per-game: Canopy"): a "reset session" option, folded
# together with B13's grid-size variant since both mean "rebuild the whole
# session from scratch" -- offering them as two separate controls would just
# mean two code paths doing almost the same thing. Deliberately a hard reset
# with no confirmation dialog: matches the site's "no dead-end states"
# philosophy (nothing here is a save file being destroyed -- that's what the
# separate save-code widget is for) and the shared confirm-dialog pattern
# the TODO's own site-wide goal describes is still just a design, not a
# built component, elsewhere in this file.
_KEEP_LAYOUT = object()  # reset_session(layout=...) default: keep the running layout (a setting that would clash drops it)
_KEEP_LEVEL = object()  # reset_session(level=...) default: keep the running level unless a setting is being changed
_KEEP_EXPEDITION = object()  # reset_session(expedition=...) default: Reset retries the Expedition; changing a setting leaves it


# B24: Reset Session asks first, but only when there is something to lose, and
# names exactly what is being given up (the current standing value and income).
# A session with nothing standing worth keeping resets immediately.
#
# UX-4 (2026-10-07): the confirmation used to be a "press the button twice
# within 5 seconds" two-step that only relabelled the toolbar button. Players
# reported that Reset Session "does nothing": the first press changes nothing
# but a long label on a button that can be scrolled off-screen on a phone, and
# on the Desktop boot the button lives in the Menu, which closes after the
# first press, so the second press never happened. It now uses the shared
# ConfirmDialog (a modal with Cancel / Reset session buttons), which works the
# same on both boots and cannot be missed. Where ConfirmDialog is not available
# (the pytest fake-DOM harness, or a page without confirm-dialog.js) the reset
# happens at once, same fall-through every other game's helper has.
RESET_CONFIRM_ID = "canopy-reset-session"


def reset_confirm_message():
    return (
        f"Reset this session? You will give up {standing_forest_value():.1f} standing value"
        f" and {runstate.total_income:.1f} income. Saves you have already made are not touched."
    )


def _confirm_dialog_ask(action_id, message, confirm_label, on_confirm):
    try:
        from js import window  # noqa: PLC0415 -- Pyodide-only, deliberately lazy
    except ImportError:
        on_confirm()
        return
    confirm_dialog = getattr(window, "ConfirmDialog", None)
    if confirm_dialog is None:
        on_confirm()
        return
    confirm_dialog.ask(
        id=action_id,
        message=message,
        confirmLabel=confirm_label,
        allowSkip=False,
        onConfirm=create_proxy(lambda: on_confirm()),
    )


def render_reset_button():
    """Kept so render() keeps the toolbar label constant (older builds relabelled
    the button while a two-step confirm was armed)."""
    button = document.getElementById("reset-session-button")
    if button is None:
        return
    if button.innerText != "\U0001F504 Reset Session":
        button.innerText = "\U0001F504 Reset Session"
