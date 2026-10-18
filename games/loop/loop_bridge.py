"""Browser bridges (window, LoopSettings getters, haptics, clipboard, confirm dialog): all optional, all safe under pytest."""

from pyodide.ffi import create_proxy


def _copy_to_clipboard(text):
    """Best effort: True when the browser accepted it. Never raises."""
    try:
        from js import navigator  # noqa: PLC0415 -- Pyodide-only, deliberately lazy
        navigator.clipboard.writeText(text)
        return True
    except Exception:  # noqa: BLE001 -- no clipboard (tests, insecure page): the text is shown instead
        return False


def _window():
    """The browser window, or None under pytest (the fake `js` module only fakes document and
    setTimeout). One lazy import in one place, like the other optional bridges below."""
    try:
        from js import window  # noqa: PLC0415 -- Pyodide-only, deliberately lazy
    except ImportError:
        return None
    return window


def _setting_number(name, default=0):
    """A number read from a LoopSettings getter (settings.js), or `default` when the bridge is
    missing or returns something odd. Browser preferences only, never part of a save."""
    window = _window()
    getter = getattr(getattr(window, "LoopSettings", None), name, None) if window is not None else None
    if getter is None:
        return default
    try:
        value = float(getter())
    except (TypeError, ValueError):
        return default
    return value if value == value else default


def _setting_flag(name, default=False):
    """A yes/no read from a LoopSettings getter (settings.js); `default` without the bridge (pytest)."""
    window = _window()
    getter = getattr(getattr(window, "LoopSettings", None), name, None) if window is not None else None
    if getter is None:
        return default
    try:
        return bool(getter())
    except (TypeError, ValueError):
        return default


def _haptic(pattern):
    """GH-29: a short vibration when the player has switched it on (settings.js decides; silent otherwise)."""
    window = _window()
    settings = getattr(window, "LoopSettings", None) if window is not None else None
    buzz = getattr(settings, "haptic", None)
    if buzz is not None:
        try:
            buzz(pattern)
        except Exception:  # noqa: BLE001 -- a vibration must never break a purchase
            pass


def _confirm_dialog_ask(action_id, message, confirm_label, on_confirm):
    """Routes a guarded action through the shared shared/confirm-dialog.js
    widget when it's available, or runs the action immediately when it
    isn't -- same lazy `from js import window`/getattr-default shape as
    Grid's/Herd's/Trade Empire's own `_confirm_dialog_ask()` helpers. The
    pytest fake-DOM harness's `js` module only ever fakes `document`/
    `setTimeout` (see tests/conftest.py), never `window`, so `from js
    import window` raises ImportError there and this falls straight
    through to calling on_confirm() synchronously -- which is exactly
    what the existing reset-chain test already expects."""
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
        onConfirm=create_proxy(on_confirm),
    )
