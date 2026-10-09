# Hull Repair build status (handoff file)

Updated after every milestone. Read `planning/hull-repair-plan.md`, `CLAUDE.md` here, then this file. Hub registration is NOT part of this build.

## Done
- M1 Engine: rules.py, play.py, boards.py + boards_dock.py (deck 1, 8 boards), tools/solver.py (exhaustive, counts layouts), tools/gen.py (seeded board finder); every board proven to have exactly one restored layout; flake8 clean.

- M2 Board UI: render.py, progress.py, game.py, index.html, app.js, style.css, settings.js, changelog.json, favicon; 112 tests; checked live at 1440x900-ish pane and 360x740 (drag, keyboard, restored card, no horizontal scroll).

## Next
- M3 Decks 2-3 (32 more boards needs generator tuning for holes and bridges), station map, repair log, hint ladder, goals strip (achievement facts).

## Open problems / notes
- Local Python is 3.9: engine code avoids 3.10+ syntax.
- Gen finds 7x7+ boards rarely with default settings; tune maxlen/max_lines when building decks 3-5.
