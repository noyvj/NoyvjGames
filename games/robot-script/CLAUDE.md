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
| 2 | Room UI | SVG room (`render.py`), structured editor (`editor.py`), run/step/skip playback, result card with medal, room picker, favicon, settings, save contract (`game.py`) | Done |
| 3 | Chapters 2-3, medals, hints | 14 rooms (Turning checked against the solver, Loops checked to need the loop), gating at 5 of 7, hint ladder (`hints.py`), three-goals strip (`achievements.py` facts), Scrap and the Workshop (`companion.py`) | Done |
| 4 | Chapters 4-6 and the sandbox | 19 rooms (40 in all: `rooms_routines.py`, `rooms_branches.py`, `rooms_capstone.py`; routine rooms drawn around their reference with `tools/author.py`) and the free sandbox (`sandbox.py`). First complete game | Done |
| 5 | Standard kit | Opening screen, tutorial, About, What's New, keyboard help, light theme, accessibility | Planned |
| 6 | Achievements | 14 achievements, panel, toast, manifest | Planned |
| 7 | Desktop boot and wrap-up | `pc-config.json`, `pc.css`, `pc.js`, generated `pc.html`, docs | Planned |

## Working conventions
- Commit only this folder with a pathspec commit, then tag `robot-script-milestone-0N`. Hub registration is a separate later job (nothing outside this folder and `planning/robot-script-plan.md` is touched here).
- Tests: `python3 -m pytest -q games/robot-script`; lint: `python3 -m flake8 --extend-ignore=E501 games/robot-script`. Local Python is 3.9 (Pyodide runs 3.12): no 3.10+ syntax in engine code.

## Engine and page notes (milestone 2)
- `game.handle(json)` returns the whole view; `room.svg` is sent only when the room changes (`svg_due`). A run returns `run` with every frame `[x, y, d, carry, partsMask, socketsMask, switchesMask, at]`; app.js plays them back (speed from `data-run-speed`, instant under reduced motion) and the engine has already recorded the result, so skipping the animation loses nothing.
- Save (`get_state`): `cur`, `best {room: {n, t}}` (re-run and re-checked on load), `draft {room: text}`, `tally`, `flags`, `bumped`; only non-default keys. A room with a best and no draft opens with its best list in the editor.
- The editor works on addresses (`main/2/2` = the body of the block at index 2 of main; an `if` has bodies 2 and 3) and refuses anything `dsl.check` rejects; gap buttons are `data-touch-exempt` (dense list).

## Milestone 3 notes
- Chapter 2 rooms are flat: their par is the breadth-first minimum (tested). Chapter 3 rooms are each shorter with `rep` than any flat list (tested against the solver).
- Hints: `hint` climbs one rung per call (nudge, hint, answer), saved per room in `rungs`; `load_answer` needs rung 3. Hints never touch a medal.
- Scrap: one part per room (40 in `companion.PARTS`, ten zones); the finish follows the room's medal; drawing and list are computed from `best`. Lines sit behind the story toggle (`.scrap-line`, `.story-text`).
- Goals strip: the next three unearned achievements whose chapter is open (`achievements.goals`); the achievements themselves (panel, toast, manifest) arrive in milestone 6.

## Milestone 4 notes
- 40 rooms: 7 + 7 + 7 + 7 + 7 + 5. From chapter 3 on every reference is shorter than the shortest flat list (tested with the solver), and chapters 3-5 must use their own tool (repeat, call, until/if). Chapter 6 mixes everything.
- `tools/author.py` (dev only): expands a reference (repeats and calls, no conditionals) and draws the room where exactly that walk works; conditional rooms were drawn from an equivalent flat walk and verified with the conditional reference.
- Sandbox: id `sandbox`, 8x8, opens once every room of the last chapter is cleared (`progress.sandbox_open`). Saved as `sbx` (rows, only when not the default), `sdraft` (the unfinished list) and `cur: "sandbox"`; tally keys `sbx_runs` and `sbx_tiles`. Painting works by tapping the room or by column/row fields (the keyboard path). Presets: open, maze, workshop.
- A perfect-play test clears all 40 rooms with gold from the references and checks every achievement is reachable.
