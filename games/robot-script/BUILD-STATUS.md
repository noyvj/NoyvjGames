# Robot Script build status (handoff file)

Updated after every milestone. Read `planning/robot-script-plan.md`, `CLAUDE.md` here, then this file. Hub registration is NOT part of this build.

## Done
- M1 Engine: dsl.py (program text/validation/size), room.py (layout + the single `step` rule), run.py (interpreter, frames), rooms.py + rooms_moving.py (7 rooms), tools/solver.py (BFS), 66 tests, flake8 clean.

- M2 Room UI: editor.py, render.py, progress.py, info.py, game.py, index.html, app.js, style.css, settings.js, changelog.json, favicon; 106 tests; checked live at 1440x900 and 360x740 (cleared a room, halted run shows the reason, no horizontal scroll).

- M3 Chapters 2-3 (rooms_turning.py, rooms_loops.py), hints.py, achievements.py (facts + goals only), companion.py, Workshop panel, goals strip; 155 tests; checked live (loop room built with nested repeats in the UI, cleared gold, Scrap part and line shown).

- M4 Chapters 4-6 (19 rooms, 40 in all), tools/author.py, sandbox.py + sandbox UI; 230 tests (26 skipped = flat-minimum checks that do not apply to compressed rooms); live check: conditional room built in the editor, sandbox opened from the Rooms panel and painted.

- M5 Standard kit: tutorial + hook for the Desktop steps, accessibility and pledge tests, light-theme contrast fixes; 254 tests; opening screen and tutorial offer verified live.

- M6 Achievements: achievements.json, panel, toast; 260 tests; checked live (First Light toast, panel with share).

- M7 Desktop boot: pc-config.json, pc.css, pc.js, generated pc.html, desktop tests; shared pc tests -k robot pass; 266 tests collected.

- AN-3 (2026-10-11): sandbox opens after chapter 3 (Loops); tinkerer goal gated on the sandbox, not on chapter 6; tests updated.

## Next
- Nothing in this folder. Hub registration is the hub session's job (title card, sw.js, game-*.json, CLAUDE.md row, dev logs); the plan's last section lists questions for the owner.

## Open problems / notes
- Local Python is 3.9: engine code avoids 3.10+ syntax.
- Max room side 10 cells and 64 cells in all (the plan said 8x8; corridor rooms are long and thin).
