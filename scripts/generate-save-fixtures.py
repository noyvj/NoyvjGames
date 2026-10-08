#!/usr/bin/env python3
"""Regenerate the save fixtures that shared/tests/test_migrate.py loads (TODO Z-9).

For every game this boots the game headlessly the way its own tests do (see
shared/tests/smoke_support.py), then writes two real `get_state()` results under
shared/tests/fixtures/saves/:

    <game>.fresh.json   the state of a brand-new game, before anything was done
    <game>.json         the state after a seeded random play-through (a representative mid-game save)

The play-through is deterministic (fixed seed, a fixed number of steps), but the state a game
returns can still contain today's date or a version stamp, so a regenerated file may differ from
the committed one. Treat the committed fixtures as HISTORY: when a game changes its save shape,
do NOT regenerate its fixture over the old shape. Keep the old file (rename it, e.g.
`grid.v0.json`) and add the new shape beside it, so the migration test keeps proving old saves
still load. Only regenerate to add a missing game or when a fixture is deliberately being replaced.

Usage:
    python3 scripts/generate-save-fixtures.py            # write only the files that do not exist
    python3 scripts/generate-save-fixtures.py --force    # overwrite
    python3 scripts/generate-save-fixtures.py grid tide  # only these games
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "shared" / "tests"))

import smoke_support as ss  # noqa: E402

OUT = ROOT / "shared" / "tests" / "fixtures" / "saves"
SEED = 20261008
STEPS = {"champ-de-mots": 120, "drift": 120, "thaw": 120}   # slow get_state(), keep the walk short
DEFAULT_STEPS = 200


def capture(slug):
    """Return (fresh_state, played_state) for one game."""
    steps = STEPS.get(slug, DEFAULT_STEPS)
    if slug in ss.FAKE_DOM_GAMES:
        with ss.fake_dom_game(slug) as env:
            fresh = json.loads(json.dumps(env.module.get_state()))
            result = ss.fuzz_fake_dom(env, seed=SEED, steps=steps, check_every=steps)
            played = json.loads(json.dumps(env.module.get_state()))
    else:
        with ss.engine_game(slug) as (call, get_state, next_request):
            fresh = json.loads(json.dumps(get_state()))
            result = ss.fuzz_requests(call, get_state, next_request, seed=SEED, steps=steps, check_every=steps)
            played = json.loads(json.dumps(get_state()))
    if result["errors"]:
        raise SystemExit("%s: the play-through failed, not writing a fixture: %s" % (slug, result["errors"][0]))
    return fresh, played


def main(argv):
    force = "--force" in argv
    wanted = [a for a in argv if not a.startswith("--")] or ss.ALL_GAMES
    OUT.mkdir(parents=True, exist_ok=True)
    for slug in wanted:
        fresh_path, played_path = OUT / (slug + ".fresh.json"), OUT / (slug + ".json")
        if not force and fresh_path.exists() and played_path.exists():
            print("%-14s exists, skipped (use --force)" % slug)
            continue
        fresh, played = capture(slug)
        for path, state in ((fresh_path, fresh), (played_path, played)):
            path.write_text(json.dumps(state, indent=1, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf8")
        print("%-14s wrote %6d + %6d bytes" % (slug, fresh_path.stat().st_size, played_path.stat().st_size))


if __name__ == "__main__":
    main(sys.argv[1:])
