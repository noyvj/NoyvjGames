# Robot Script build status (handoff file)

Updated after every milestone. Read `planning/robot-script-plan.md`, `CLAUDE.md` here, then this file. Hub registration is NOT part of this build.

## Done
- M1 Engine: dsl.py (program text/validation/size), room.py (layout + the single `step` rule), run.py (interpreter, frames), rooms.py + rooms_moving.py (7 rooms), tools/solver.py (BFS), 66 tests, flake8 clean.

## Next
- M2 Room UI.

## Open problems / notes
- Local Python is 3.9: engine code avoids 3.10+ syntax.
- Max room side 10 cells and 64 cells in all (the plan said 8x8; corridor rooms are long and thin).
