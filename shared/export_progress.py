"""Shared "export my progress" helper — the portable-progress-code pattern.

`planning/TODO.md`'s Z8: before this module existed, Aftermath's E12
("export/import progress code" — skill tree, run history, legacy system,
achievement progress) and SOL's A17 ("export/import progress code for
lifetime stats") each hand-rolled their own base64(JSON) codec plus their
own copy of the same "did this even decode into something sane" checks.
Read both before writing this — they turned out to want two genuinely
different shapes, not one shape forced two ways:

1. **Flat numeric counters, monotonic merge** — SOL's A17 is the
   reference case: a short version-tagged prefix (`"SOLSTATS1:"`) plus a
   flat dict of named counters, re-imported by taking the max of each
   field against what's already on this device so a stale code from an
   older device can never undo newer progress.
2. **A structural bundle, replace-on-import** — Aftermath's E12 is the
   reference case: nested lists/dicts (skill tree, run history,
   achievement progress, ...) with no sensible per-field "max", where a
   valid code deliberately REPLACES local state outright.

This module factors out only what's identical in both — the base64<->JSON
codec, the "is this even a dict" structural check, and (for the flat-
counter shape) the numeric-field validation and the max-merge itself —
and leaves the field list, the bundle's own shape, and any bundle-specific
validation to each game, since those are genuinely game-specific. This is
the same shared-content/game-owns-its-data split `shared/info_page.py`
uses (shared rendering logic, each game keeps its own `INFO_PAGE` dict).

Loaded the same way as `shared/info_page.py`: each game's index.html
fetches this file's source and writes it into Pyodide's virtual
filesystem (as "export_progress.py", so `import export_progress` resolves
normally) before fetching and running the game's own game.py. Under
pytest, `sys.path` is pointed at the repo's `shared/` directory instead
(see any game's `tests/conftest.py`) — this module has no `js`/DOM
dependency at all, so it imports identically either way.
"""

import base64
import json
import math


def encode_progress_code(payload, prefix=""):
    """Serializes `payload` (any JSON-safe dict) into a copyable text code:
    `prefix` (kept in plain text) followed by the base64 of its JSON. The
    prefix lets a pasted-back code be sanity-checked (and, if it ever needs
    to change shape, version-checked) before attempting to decode it —
    matching SOL's own `"SOLSTATS1:"` tag.
    """
    raw = json.dumps(payload, sort_keys=True).encode("utf-8")
    return prefix + base64.b64encode(raw).decode("ascii")


def decode_progress_code(code, prefix="", bad_format_message=None):
    """Reverses `encode_progress_code`. Returns `(True, payload_dict)` on a
    structurally sound code, or `(False, message)` on anything else —
    missing/wrong prefix, broken base64, broken JSON, or a decoded value
    that isn't a dict.

    Never raises: a pasted code is untrusted, hand-typed/copy-pasted player
    input, and a bad paste is an expected, common failure mode that should
    fail soft with a status message, not crash the page (same reasoning
    Aftermath's original `import_progress_code` docstring already gave).
    """
    message = bad_format_message or "That doesn't look like a valid progress code."
    code = (code or "").strip()
    if prefix:
        if not code.startswith(prefix):
            return False, message
        code = code[len(prefix):]
    try:
        payload = json.loads(base64.b64decode(code).decode("utf-8"))
    except Exception:  # noqa: BLE001 -- deliberately broad, see docstring
        return False, message
    if not isinstance(payload, dict):
        return False, message
    return True, payload


def validate_numeric_fields(payload, fields):
    """True if every name in `fields` is present in `payload` as a finite,
    non-negative number. Covers the common "flat lifetime counters" shape
    (SOL's A17). `bool` is deliberately excluded even though it's a
    subclass of `int` in Python — `isinstance(True, (int, float))` is
    True, which would otherwise let a stray boolean silently pass as 0/1.
    """
    for name in fields:
        value = payload.get(name)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
            return False
    return True


def merge_counters_max(current, payload, fields):
    """Returns a new `{name: max(current[name], payload[name])}` dict for
    `fields` — the "counters only ever go up" merge semantics, so
    importing a stale code from an older device or an earlier point in
    this same session can never undo progress made elsewhere. `current`
    and `payload` must each already have every name in `fields`.
    """
    return {name: max(current[name], payload[name]) for name in fields}
