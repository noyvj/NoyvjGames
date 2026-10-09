# Robot Script

Seed: `planning/robot-script-plan.md` (Quick ideas round A3, TODO QI-3). Personal project, no BCM tag, working title. Built 2026-10-09 by a background agent.

## One-line pitch
Give a maintenance robot a short list of instructions to clear a room (Lightbot style): fewer steps earn better medals, nothing is timed, and a free sandbox opens at the end.

## Stack
- Pyodide Python, plain HTML/CSS, no build step. `game.py` is the single engine entry point (`handle(json) -> json`, `get_state()` / `load_state()` for the shared save widget); `app.js` is glue only. Room and robot are SVG strings built in Python (`render.py`) so their markup is unit-tested.
- Runs from any static server. No audio, ever. The playback animation is cosmetic and skippable; a run is computed instantly.

## Core constraints (do not violate without asking)
1. `run.run(layout, program)` is a pure deterministic function of its inputs: no clock, no randomness (a test scans the engine).
2. No timers, energy, grinding or progress loss; no roguelike, deck or card mechanics; no audio; no mandatory leaderboard; no all-good hero.
3. A failed run is never a dead end: the robot stops where it went wrong, says why in plain words, the list stays editable.
4. Every room has a reference solution (`ref`, text form of `dsl.py`) whose length is its par; tests run every one. Flat rooms (no loops) are also checked against the breadth-first solver (`tools/solver.py`) so par is the true minimum.
5. Medals: gold at or under par, silver within par plus a third (at least 2), bronze for a clear. Hints never touch a medal.
6. No colour-only encoding: every tile type has its own shape and a letter.

## Rules as built (milestone 1)
- Tiles: `.` floor, `#` wall, `E` exit, `p` part, `o` socket, `1 2 3` switches, `A B C` doors opened by switch 1/2/3, `> < ^ v` start and heading.
- Actions `F L R G P S`; blocks `rep N`, `until cond`, `if cond else`; routines `A` (calls nothing) and `B` (may call `A`). Conditions `blocked part socket switch carrying exit`, each optionally `!`-negated.
- Goals: exit (if the room has one), every socket filled (or the single part picked up when there are no sockets), every switch lit.
- A halt (wall, edge, shut door, impossible grab/place/switch) stops the run with a message; a runaway list is stopped after 2000 actions (`status "loop"`).
- Program size ("steps") = every instruction counted once, block headers and calls included, routine bodies included. Cap 40, nesting 3.

## Milestones
| # | Milestone | Content | Status |
|---|-----------|---------|--------|
| 1 | Engine | `dsl.py`, `room.py`, `run.py`, `rooms.py`, chapter 1 (7 rooms), `tools/solver.py`, tests | Done |
| 2 | Room UI | SVG room, structured editor, run/step/skip playback, result card, picker, favicon, settings, save contract | Planned |
| 3 | Chapters 2-3, medals, hints | 14 rooms, gating, hint ladder, three-goals strip, Scrap and the Workshop | Planned |
| 4 | Chapters 4-6 and the sandbox | 19 rooms (40), sandbox. First complete game | Planned |
| 5 | Standard kit | Opening screen, tutorial, About, What's New, keyboard help, light theme, accessibility | Planned |
| 6 | Achievements | 14 achievements, panel, toast, manifest | Planned |
| 7 | Desktop boot and wrap-up | `pc-config.json`, `pc.css`, `pc.js`, generated `pc.html`, docs | Planned |

## Working conventions
- Commit only this folder with a pathspec commit, then tag `robot-script-milestone-0N`. Hub registration is a separate later job (nothing outside this folder and `planning/robot-script-plan.md` is touched here).
- Tests: `python3 -m pytest -q games/robot-script`; lint: `python3 -m flake8 --extend-ignore=E501 games/robot-script`. Local Python is 3.9 (Pyodide runs 3.12): no 3.10+ syntax in engine code.
