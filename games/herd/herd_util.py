"""Tiny shared helpers: the finite-number check, the safe int and the browser-storage read and write.
Part of the split of the old single-file game.py: see "File map" in games/herd/CLAUDE.md.
"""

import herd_runstate as runstate


def _read_local_storage_item(key):
    """Lazy `import js` so this module stays importable outside a real
    browser (the pytest fake `js` module has no localStorage at all,
    which this degrades to gracefully). Broad except on the actual read
    is deliberate: a real browser can refuse localStorage access entirely
    (private-browsing mode in some browsers), surfaced as a JS exception
    with no stable Python type to catch narrowly -- this feature is a
    nice-to-have, so it degrades to "no record yet" rather than crashing
    the module import."""
    try:
        import js  # noqa: PLC0415 — Pyodide-only import, deliberately lazy
    except ImportError:
        return None
    storage = getattr(js, "localStorage", None)
    if storage is None:
        return None
    try:
        return storage.getItem(key)
    except Exception:  # noqa: BLE001 — see docstring above
        return None


def _write_local_storage_item(key, value):
    if runstate.sandbox_active:  # GF-24: nothing the practice sandbox does is ever written to browser storage
        return
    try:
        import js  # noqa: PLC0415
    except ImportError:
        return
    storage = getattr(js, "localStorage", None)
    if storage is None:
        return
    try:
        storage.setItem(key, value)
    except Exception:  # noqa: BLE001 — see _read_local_storage_item's docstring
        pass


def _safe_int(value, default):
    """Non-negative int from untrusted save data, else default."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return default
    if value != value or value in (float("inf"), float("-inf")):
        return default
    return max(0, int(value))


def _is_finite_number(value):
    return (
        isinstance(value, (int, float)) and not isinstance(value, bool)
        and value == value and abs(value) != float("inf")
    )
