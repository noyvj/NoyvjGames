# Robot Script build status (handoff file)

Updated after every milestone. Read `planning/robot-script-plan.md`, `CLAUDE.md` here, then this file. Hub registration is NOT part of this build.

## Done
- M1 Engine: dsl.py (program text/validation/size), room.py (layout + the single `step` rule), run.py (interpreter, frames), rooms.py + rooms_moving.py (7 rooms), tools/solver.py (BFS), 66 tests, flake8 clean.

- M2 Room UI: editor.py, render.py, progress.py, info.py, game.py, index.html, app.js, style.css, settings.js, changelog.json, favicon; 106 tests; checked live at 1440x900 and 360x740 (cleared a room, halted run shows the reason, no horizontal scroll).

## Next
- M3 Chapters 2-3 (14 rooms), hint ladder, three-goals strip, Scrap and the Workshop.

## Open problems / notes
- Local Python is 3.9: engine code avoids 3.10+ syntax.
- Max room side 10 cells and 64 cells in all (the plan said 8x8; corridor rooms are long and thin).
