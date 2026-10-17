"""The optional 'ask before a big purchase' check: the threshold setting, the confirm message and the guarded purchase helper.
Part of the split of the old single-file game.py: see "File map" in games/herd/CLAUDE.md.
"""

from pyodide.ffi import create_proxy

import herd_runstate as runstate
from herd_util import _read_local_storage_item


# F-18: an optional "ask before a big purchase" setting. The Settings select (settings.js) keeps the
# threshold in localStorage as a percentage of current funds; 0 means off, which is the default.
CONFIRM_THRESHOLD_KEY = "herd-confirm-percent"
CONFIRM_THRESHOLD_CHOICES = (0, 25, 50, 75)


def confirm_threshold_percent():
    raw = _read_local_storage_item(CONFIRM_THRESHOLD_KEY)
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return 0
    return value if value in CONFIRM_THRESHOLD_CHOICES else 0


def purchase_needs_confirm(cost):
    """True when the setting is on and this purchase costs more than the chosen share of the
    funds the farm has right now."""
    percent = confirm_threshold_percent()
    return percent > 0 and cost > 0 and runstate.farm.funds > 0 and cost > runstate.farm.funds * percent / 100.0 + 1e-9


def big_purchase_message(label, cost):
    share = cost / runstate.farm.funds * 100 if runstate.farm.funds > 0 else 100
    return (
        f"{label} costs {cost:.0f} funds, {share:.0f}% of the {runstate.farm.funds:.0f} you have. "
        f"You asked to be checked before any purchase above {confirm_threshold_percent()}% of your funds."
    )


def _guarded_purchase(label, cost, action):
    """Runs `action` straight away, or after the shared confirm dialog when the F-18 setting says
    this purchase is big. The dialog has no "don't ask again" box (the setting itself is the way
    to turn it off)."""
    if purchase_needs_confirm(cost):
        _confirm_dialog_ask(
            action_id="herd-big-purchase",
            message=big_purchase_message(label, cost),
            confirm_label="Buy",
            on_confirm=action,
            allow_skip=False,
        )
    else:
        action()


def _confirm_dialog_ask(action_id, message, confirm_label, on_confirm, allow_skip=True):
    """Routes a guarded action through the shared shared/confirm-dialog.js
    widget when it's available, or runs the action immediately when it
    isn't -- same lazy `from js import window`/getattr-default shape as
    every other optional-JS-hook call in this hub (Grid's own copy of
    this helper, continuum's `_notify_visual_layer()`, champ-de-mots'
    `_dispatch_report()`). The pytest fake-DOM harness's `js` module only
    ever fakes `document`/`setTimeout` (see conftest.py's
    `_install_pyodide_fakes`), never `window`, so `from js import window`
    raises ImportError there and this falls straight through to calling
    on_confirm() synchronously -- which is exactly what every existing
    plant-pivot-invest test in this suite already expects."""
    try:
        from js import window  # noqa: PLC0415 -- Pyodide-only, deliberately lazy
    except ImportError:
        on_confirm()
        return
    confirm_dialog = getattr(window, "ConfirmDialog", None)
    if confirm_dialog is None:
        on_confirm()
        return
    kwargs = {}
    if not allow_skip:
        kwargs["allowSkip"] = False
    confirm_dialog.ask(
        id=action_id,
        message=message,
        confirmLabel=confirm_label,
        onConfirm=create_proxy(on_confirm),
        **kwargs,
    )
