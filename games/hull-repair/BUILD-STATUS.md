# Hull Repair build status (handoff file)

Updated after every milestone. Read `planning/hull-repair-plan.md`, `CLAUDE.md` here, then this file. Hub registration is NOT part of this build.

## Done
- M1 Engine: rules.py, play.py, boards.py + boards_dock.py (deck 1, 8 boards), tools/solver.py (exhaustive, counts layouts), tools/gen.py (seeded board finder); every board proven to have exactly one restored layout; flake8 clean.

## Next
- M2 Board UI (render.py, game.py, index.html, app.js, style.css, settings.js, changelog.json, favicon, save contract).

## Open problems / notes
- Local Python is 3.9: engine code avoids 3.10+ syntax.
- Gen finds 7x7+ boards rarely with default settings; tune maxlen/max_lines when building decks 3-5.
