"""Small browser helpers: localStorage read and write."""


def _read_local_storage_item(key):
    """Lazy `import js` (same convention as _read_achievements_json())
    so this file stays importable outside a real browser. Broad except on
    the actual read below is deliberate: a real browser can refuse
    localStorage access entirely (private-browsing mode in some
    browsers), surfaced as a JS exception with no stable Python type to
    catch narrowly -- this feature is a nice-to-have, so it degrades to
    "no personal best recorded" rather than crashing the module import."""
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


# Read with .get(), and merge `capacity` key-by-key into the live dict
# rather than replacing it wholesale: `data` may be a hand-edited/
# truncated save code, or simply a payload from a different build of this
# game with a different field set (a save made before some future field
# existed, or capacity category added/removed). Every field used to be
# read with a bare data["..."], so a single missing key raised partway
# through the assignments — leaving some fields already overwritten with
# the save's values and others still at whatever they were before the
# call, a worse outcome than either a clean load or a clean failure. The
# capacity dict specifically wants a key-by-key merge (not just a
# missing-field default) because render() and every invest-cost lookup
# index state.capacity[category] unconditionally for every category in
# CATEGORIES — a wholesale-replaced dict missing a category would crash
# the very next render, not just look wrong (same reasoning as
# Continuum's CITY_KEYED_DICTS).
# REVIEW(patterns): uses defensive data.get(key, default)/isinstance checks
# throughout, returning False on malformed input — diverges from the direct
# data["key"] indexing convention every other game's load_state uses
# (aftermath, canopy, drift, grid, herd, loop, thaw all raise KeyError on a
# malformed/missing field instead). Not documented as an intentional
# deviation in this file's CLAUDE.md.
def _clamped_int(value, low, high):
    """Save-field validator: a real int (not bool) clamped to [low, high],
    else `low`."""
    if isinstance(value, bool) or not isinstance(value, int):
        return low
    return max(low, min(high, value))


def _finite_number(value, low, high):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and value == value
        and low <= value <= high
    )
