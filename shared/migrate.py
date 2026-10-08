"""Shared save-schema versioning and migration harness (planning/TODO.md Z-9).

Every game's `get_state()` returns a plain dict (JSON-friendly) that the save widget stores and
`load_state(data)` reads back. When a game changes the SHAPE of that dict, old saves must still
load. This module is the one place that knows how: a registry of small per-game migration
functions, chained by `migrate()`.

The convention
--------------
* A save may carry an integer under the key `schema_version` (SCHEMA_VERSION_KEY).
* A save WITHOUT that key is version 0. Every save written before this harness existed is
  version 0, and while a game has no migrations registered a version-0 save loads UNCHANGED:
  `migrate()` returns the very same dict and adds nothing to it.
* A game's current schema version is `CURRENT_VERSIONS[game]` (default 0). To change a game's
  save shape:
    1. register a function that turns version N into version N+1 (see `register` below);
    2. raise `CURRENT_VERSIONS["<game>"]` to N+1;
    3. have the game's `get_state()` call `stamp("<game>", state)` so new saves carry the number
       (until step 3 a game keeps writing unversioned saves, which is fine: they read as version
       0 and are migrated forward on load).
  Add a fixture of the old shape under `shared/tests/fixtures/saves/` first, so the test proves
  the chain still reads it.
* These version numbers are separate from the ones some games already keep for their own
  reasons (Le Champ de Mots' `version`, Continuum's `save_version`, a few export formats).
  Those stay as they are; a migration may read them but `schema_version` is the harness's key.

Failure handling
----------------
`migrate()` raises `MigrationError` when a save cannot be read: it is not a dict, its
`schema_version` is not a non-negative integer, it is NEWER than this build understands, a step
in the chain is missing, or a step raised. The error carries the game, the version it stopped at
and the original save, so a caller can show a "could not read this save, here is the raw code"
screen instead of silently resetting the player. `safe_migrate()` is the non-raising form for
that screen: `(ok, save, failure)` where `failure` is `failure_report(...)`'s dict (with the raw
save as JSON text ready to copy). The screen itself is part of the save widget (not built here).

Pure Python 3, no imports from the games, safe to import inside Pyodide next to `info_page.py`.
Migration functions must not mutate their argument: `migrate()` hands each one a deep copy.
"""

import copy
import json

SCHEMA_VERSION_KEY = "schema_version"

# game slug -> the schema version its newest saves have. Games with no entry are at version 0
# (nothing has ever changed shape), so their unversioned saves are already current.
CURRENT_VERSIONS = {}

# (game, from_version) -> function(dict) -> dict (the save at from_version + 1)
_REGISTRY = {}


class MigrationError(Exception):
    """A save could not be brought to the current schema version."""

    def __init__(self, message, game=None, version=None, save=None):
        super().__init__(message)
        self.game = game
        self.version = version      # the version the chain had reached when it stopped
        self.save = save            # the ORIGINAL save, untouched, for the raw-code screen


def current_version(game):
    return CURRENT_VERSIONS.get(game, 0)


def register(game, from_version):
    """Decorator: `@register("grid", 0)` marks the function as the step from version 0 to 1.

    The function receives a deep copy of the save and returns the migrated dict (it may edit
    and return its argument). `migrate()` sets `schema_version` itself after each step, so the
    function must not bother. Registering the same (game, from_version) twice is an error: two
    steps for one hop would make the chain depend on import order."""
    if not isinstance(from_version, int) or from_version < 0:
        raise ValueError("from_version must be a non-negative integer")

    def wrap(fn):
        key = (game, from_version)
        if key in _REGISTRY:
            raise ValueError("a migration for %r from version %d is already registered" % key)
        _REGISTRY[key] = fn
        return fn

    return wrap


def registered(game):
    """Sorted list of the from-versions that have a migration for this game."""
    return sorted(v for (g, v) in _REGISTRY if g == game)


def audit(game=None):
    """Problems with the registry, as strings (empty when it is consistent): every version from 0
    up to the game's current version must have exactly one step, and no step may sit at or beyond
    the current version. Call it from a test whenever a game raises its CURRENT_VERSIONS entry."""
    problems = []
    games = [game] if game else sorted(set(CURRENT_VERSIONS) | {g for g, _ in _REGISTRY})
    for g in games:
        top = current_version(g)
        steps = registered(g)
        for v in range(top):
            if v not in steps:
                problems.append("%s: no migration from version %d to %d" % (g, v, v + 1))
        for v in steps:
            if v >= top:
                problems.append("%s: migration from version %d is at or beyond the current version %d" % (g, v, top))
    return problems


def version_of(save):
    """The save's schema version: the integer under `schema_version`, or 0 when it is absent.
    Raises MigrationError for a value that is not a non-negative integer (bool included)."""
    if not isinstance(save, dict):
        raise MigrationError("a save must be a JSON object, got %s" % type(save).__name__, save=save)
    if SCHEMA_VERSION_KEY not in save:
        return 0
    value = save[SCHEMA_VERSION_KEY]
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise MigrationError("schema_version must be a non-negative integer, got %r" % (value,), version=None, save=save)
    return value


def stamp(game, state):
    """Add the game's current `schema_version` to a state dict about to be saved (in place; also
    returned). A game whose version is still 0 is left unstamped so its saves stay byte-identical
    to the ones written before this harness existed."""
    if current_version(game) > 0:
        state[SCHEMA_VERSION_KEY] = current_version(game)
    return state


def migrate(game, save, target=None):
    """Bring `save` up to `target` (default: the game's current version) by chaining the
    registered steps. Returns a dict; the argument is never modified.

    * Already current (including every unversioned save of a version-0 game): the SAME dict is
      returned, unchanged, with no key added.
    * Older: each step runs on a deep copy, `schema_version` is set after it, and the migrated
      dict is returned.
    * Newer than this build knows, or a step missing or failing: raises MigrationError."""
    goal = current_version(game) if target is None else target
    start = version_of(save)
    if start == goal:
        return save
    if start > goal:
        raise MigrationError(
            "this save is schema version %d but this build of %s only understands up to %d; "
            "it was probably written by a newer version of the game" % (start, game, goal),
            game=game, version=start, save=save)
    work = copy.deepcopy(save)
    version = start
    while version < goal:
        step = _REGISTRY.get((game, version))
        if step is None:
            raise MigrationError("no migration from schema version %d to %d for %s" % (version, version + 1, game),
                                 game=game, version=version, save=save)
        try:
            result = step(work)
        except Exception as exc:  # noqa: BLE001 -- any failure in a step is a failed migration
            raise MigrationError("migration of %s from version %d failed: %s: %s"
                                 % (game, version, type(exc).__name__, exc),
                                 game=game, version=version, save=save) from exc
        if not isinstance(result, dict):
            raise MigrationError("migration of %s from version %d returned %s, not a dict"
                                 % (game, version, type(result).__name__), game=game, version=version, save=save)
        version += 1
        work = result
        work[SCHEMA_VERSION_KEY] = version
    return work


def failure_report(error):
    """Everything a 'could not read this save' screen needs, as plain data."""
    try:
        raw = json.dumps(error.save, sort_keys=True, separators=(",", ":"), default=str)
    except (TypeError, ValueError):
        raw = repr(error.save)
    return {"game": error.game, "stopped_at_version": error.version, "message": str(error), "raw": raw}


def safe_migrate(game, save, target=None):
    """Non-raising form for the load path: `(True, migrated_save, None)` or
    `(False, None, failure_report(...))`. The caller shows the failure's `message` and `raw`
    (to copy) and must NOT overwrite the stored save or start a fresh game."""
    try:
        return True, migrate(game, save, target), None
    except MigrationError as exc:
        if exc.game is None:
            exc.game = game
        return False, None, failure_report(exc)
