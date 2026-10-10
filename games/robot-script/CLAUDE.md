# Robot Script

Seed: `planning/robot-script-plan.md` (Quick ideas round A3, TODO QI-3). Personal project, no BCM tag, working title. Built 2026-10-09 by a background agent.

## One-line pitch
Give a maintenance robot a short list of instructions to clear a room (Lightbot style): fewer steps earn better medals, nothing is timed, and a free sandbox opens after the third chapter (AN-3).

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
| 3 | Chapters 2-3, medals, hints | 14 rooms (Turning checked against the solver, Loops checked to need the loop), no chapter gating (AN-5: was 5 of 7 cleared), hint ladder (`hints.py`), three-goals strip (`achievements.py` facts), Scrap and the Workshop (`companion.py`) | Done |
| 4 | Chapters 4-6 and the sandbox | 19 rooms (40 in all: `rooms_routines.py`, `rooms_branches.py`, `rooms_capstone.py`; routine rooms drawn around their reference with `tools/author.py`) and the free sandbox (`sandbox.py`). First complete game | Done |
| 5 | Standard kit | Opening screen, save widget, tutorial (9 steps), About with the pledge, What's New + banner, keyboard help, confirm dialogs (reset, sandbox preset), settings (text size, run speed, reduce motion, effects, high contrast, theme), contrast and shape tests, pledge tests | Done |
| 6 | Achievements | 14 achievements (`achievements.py` + `achievements.json`, `achievements_earned` written to the save and never read back), panel with progress numbers, toast, share button via the shared script; perfect-play test earns all 14 | Done |
| 7 | Desktop boot and wrap-up | `pc-config.json`, `pc.css`, `pc.js` (Desktop tutorial), `pc.html` generated for this game only, desktop tests, docs, changelog | Done |

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
- Scrap: one part per room (40 in `companion.PARTS` plus 2 in `companion.NEW_PARTS` keyed by room id, 42 in ten zones); the finish follows the room's medal; drawing and list are computed from `best`. Lines sit behind the story toggle (`.scrap-line`, `.story-text`).
- Goals strip: the next three unearned achievements whose chapter is open (`achievements.goals`); the achievements themselves (panel, toast, manifest) arrive in milestone 6.

## Milestone 4 notes
- 42 rooms since AN-4 (was 40): 9 + 7 + 7 + 7 + 7 + 5. From chapter 3 on every reference is shorter than the shortest flat list (tested with the solver), and chapters 3-5 must use their own tool (repeat, call, until/if). Chapter 6 mixes everything.
- `tools/author.py` (dev only): expands a reference (repeats and calls, no conditionals) and draws the room where exactly that walk works; conditional rooms were drawn from an equivalent flat walk and verified with the conditional reference.
- Sandbox: id `sandbox`, 8x8, opens once every room of the third chapter (Loops, `progress.SANDBOX_AFTER = 2`) is cleared (`progress.sandbox_open`; AN-3, 2026-10-11, was the last chapter). The "Tinkerer" goal is offered only while the sandbox is open (`achievements.SANDBOX` gate). Saved as `sbx` (rows, only when not the default), `sdraft` (the unfinished list) and `cur: "sandbox"`; tally keys `sbx_runs` and `sbx_tiles`. Painting works by tapping the room or by column/row fields (the keyboard path). Presets: open, maze, workshop.
- A perfect-play test clears all 42 rooms with gold from the references and checks every achievement is reachable.

## Milestone 5 notes
- `tests/test_accessibility.py` computes contrast from the CSS variables (both themes) for text, controls, and every room object against the floor; `tests/test_pledge.py` scans for banned words, clocks and randomness, counts the only two interval timers (cosmetic playback), and checks that a stopped run never costs the list or a medal and that every action moves a visible number.
- About page states no real-world facts (invented deck, invented drone), so there are no sources to date on screen.

## Milestone 7 notes and pre-release checklist
- Desktop boot: the room is the stage, the list editor and tally are the side column, the stats strip and the three goals sit above the stage. `pc.html` is generated (`importlib` on `scripts/generate-pc-pages.py`, `build("robot-script", cfg)` written to `pc.html`); `python3 scripts/generate-pc-pages.py --check` and `python3 -m pytest -q shared/tests -k robot` pass. The Classic desktop grid in `style.css` is scoped to `html:not([data-layout="pc"])` so it cannot fight the shell.
- Hub registration (title card, `sw.js` precache, `game-*.json`, root CLAUDE.md row, dev logs) is still to do and is not part of this folder. The owner's questions are the last section of `planning/robot-script-plan.md`.
- Manual checks worth a human pass: real-device touch on the list editor (gap buttons are small by design), a screen reader walk through the list editor, and the opening-screen "Switch to Desktop layout" button on a wide window.

## AN-5 (2026-10-11): every room open from the start
- Owner answer Rs5. `progress.chapter_open` is always true for a real chapter and `room_open` is true for any known room id; nothing about an unlock was ever stored in a save (opening was computed from `best`), so old saves load unchanged. The rooms view no longer carries `open`/`need`/`prev_name`; `achievements.goals(facts, count, sandbox)` gates only the Tinkerer goal on the sandbox (the achievement tuple's last field is `gate`, `""` or `"sandbox"`). The Locked styling, toasts and "N rooms of X" text are gone from `app.js`/`index.html`/`style.css`.

## AN-4 (2026-10-11): turning from room 4 of chapter 1
- Owner answer Rs4. Chapter 1 is now 9 rooms: Wake Up, Long Hall, Stop Short (rooms 1-3 stay straight lines, no Left/Right in the toolbox), then two new rooms, Face the Pad (`R F F`, par 3: the robot starts facing a wall) and Left at the Corner (`F F L F`, par 4), then the four older rooms (First Switch, First Delivery, In Order, The Shaft). From room 4 on every chapter 1 toolbox is `F L R` plus whatever the room already had. The older four keep their ids and layouts untouched so any saved best (a straight list) still clears them; they simply also allow turning now. Pars are still the breadth-first minimum (the existing flat-room test), and a new test checks each new room really needs its turn.
- Scrap: the two new rooms carry the extra Treads parts (Idler wheel, Drive sprocket) from `companion.NEW_PARTS`, so no older room's part changed (Treads zone is 6 parts). Totals are 42 rooms and 42 parts.
- Not in this folder, to be updated by the hub session: any hub title card / roadmap text that says "40 rooms".
