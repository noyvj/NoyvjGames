# Hull Repair build status (handoff file)

Updated after every milestone. Read `planning/hull-repair-plan.md`, `CLAUDE.md` here, then this file. Hub registration is NOT part of this build.

## Done
- M1 Engine: rules.py, play.py, boards.py + boards_dock.py (deck 1, 8 boards), tools/solver.py (exhaustive, counts layouts), tools/gen.py (seeded board finder); every board proven to have exactly one restored layout; flake8 clean.

- M2 Board UI: render.py, progress.py, game.py, index.html, app.js, style.css, settings.js, changelog.json, favicon; 112 tests; checked live at 1440x900-ish pane and 360x740 (drag, keyboard, restored card, no horizontal scroll).

- M3 Decks 2-3 (16 boards: holes, bridges), station map, repair log (all 40 lines written), hint ladder, goals strip; 172 tests; checked live (map, deck 2 board with holes, hint ghosts, answer ghost).

- M4 Decks 4-5: 16 more boards (40 in all; deck 4 valves, deck 5 mixers), 227 tests, every board proven unique; checked live (9x9 Emergency Bridge with mixer, valves, holes; answer laid).

## Next
- M5 Standard kit (opening screen, tutorial, About, What's New banner, keyboard help, confirm dialogs, story toggle, light theme and accessibility pass).

## Open problems / notes
- Local Python is 3.9: engine code avoids 3.10+ syntax.
- Gen finds 7x7+ boards rarely with default settings; tune maxlen/max_lines when building decks 3-5.
- Only two 9x9 boards exist (the generator rarely finds unique 9x9 within 8 lines); deck 5 is mostly 8x8.
