# Robot Script

Seed: `planning/robot-script-plan.md` (Quick ideas round A3, TODO QI-3). Personal project, no BCM tag, working title. Built 2026-10-09 by a background agent.

## One-line pitch
Give a maintenance robot a short list of instructions to clear a room (Lightbot style): fewer steps earn better medals, nothing is timed, and a free sandbox opens after the third chapter (AN-3).

## Stack
- Pyodide Python, plain HTML/CSS, no build step. `game.py` is the single engine entry point (`handle(json) -> json`, `get_state()` / `load_state()` for the shared save widget); the page script (`app-1-core.js` ... `app.js`) is glue only. Room and robot are SVG strings built in Python (`render.py`) so their markup is unit-tested.
- Runs from any static server. No audio, ever. The playback animation is cosmetic and skippable; a run is computed instantly.

## Core constraints (do not violate without asking)
1. `run.run(layout, program)` is a pure deterministic function of its inputs: no clock, no randomness (a test scans the engine).
2. No timers, energy, grinding or progress loss; no roguelike, deck or card mechanics; no audio; no mandatory leaderboard; no all-good hero.
3. A failed run is never a dead end: the robot stops where it went wrong, says why in plain words, the list stays editable.
4. Every room has a reference solution (`ref`, text form of `dsl.py`) whose length is its par; tests run every one. Flat rooms (no loops) are also checked against the breadth-first solver (`tools/solver.py`) so par is the true minimum.
5. Medals: gold at or under par, silver within par plus a third (at least 2), bronze for a clear. Hints never touch a medal.
6. No colour-only encoding: every tile type has its own shape and a letter.

## For the local AI (exact names; every one was checked against the code on 2026-10-18)
- **Files**: `game.py` entry point (`handle`, `get_state`, `load_state`, the `Game` class); `dsl.py` the instruction language (`ACTIONS`, `CONDS`, `ROUTINES`, `parse`, `check`, `to_text`); `room.py`, `run.py` (`run.run(layout, program)`, pure); `editor.py` the structured list editor (addresses like `main/2/2`); `rooms_*.py` the 40 frozen rooms + `rooms.py` (ORDER, BY_ID, DIFFICULTIES); `progress.py`, `hints.py`, `companion.py` (Scrap), `sandbox.py`, `render.py` (SVG strings), `achievements.py`, `info.py`; the page script, split into `app-1-core.js` ... `app.js` (see the File map below; `send(request, isEdit)` in `app-1-core.js` is the only way to the engine); `tools/` solver and author helper (not loaded by the page).
- **Entry points** (the only Python the page calls): `handle(json_string) -> json_string`, `get_state()`, `load_state(proxy)` (then `window.robotScriptRefresh()`). Never read a Python variable from JS by name. Every answer is the WHOLE view; a bad request gives `{"error": ...}`, a refused edit the view with `ok: false` and a `message`.
- **Actions** (`game.handle`): `open` | `reset` | `pick {room}` (a room id such as `wake-up`) | `next` | `sandbox` | `sbx_paint {x, y, tile}` | `sbx_preset {name}` (`open` `maze` `workshop`; both only inside the sandbox) | `insert {kind, n?, cond?}` (kind: `F L R G P S`, `rep` (n), `until` (cond), `if` (cond), `callA`, `callB`) | `cursor {list, index}` | `routine {name}` (`main` `A` `B`) | `remove {at}` | `move {at, delta}` (-1 or 1) | `count {at, n}` | `cond {at, cond}` (cond: `blocked part socket switch carrying exit`, optionally `!`-negated) | `undo` | `clear` | `load_best` | `hint` | `load_answer` | `difficulty {level}` (`easy` `normal` `hard`, set by the page, never saved) | `run` (the answer carries `run` with every frame).
  A new action = a branch in `game.handle` (an editing one goes through `ed = g.ed` and ends at `g.view(message, ok)`), the rule in the module for its area, a test in `tests/test_game_handle.py`, and a line in the docstring.
- **Top-level keys of the view** (`Game.view`): `ok message room program rooms sandbox totals tally difficulty hint scrap goals achievements about run`. `room`: `id name chapter number of sandbox intro nudge par silver gold best medal medal_name goals words start w h has_best svg` (`svg` only when the room changed); `program`: `routines active size cursor palette can_undo max conds`; `hint`: `rung next nudge hint answer max`; `sandbox`: `open current need tiles size presets`; `tally`: `runs halts written hints sbx_runs sbx_tiles`; `run` (null unless the action was `run`): `status message frames actions size par silver gold cleared goals at medal medal_name new_best best difficulty note normal_medal_name scrap_line part next next_name`.
- **get_state()** = `Game.to_dict()`: ONLY keys that differ from a fresh game (`cur best draft tally flags bumped rungs hbest sbx sdraft achievements_earned`); a saved best is re-run and re-checked on load. New save keys only when non-default, validated one field at a time in `Game.load` (never raise).
- **Page**: `render()` in `app-4-panels.js` draws `A.view`; hook after it. Palette buttons are `[data-testid=robot-script-add-<kind>]` inside `#palette`; the list is `#program`, its size line `#size-line`, errors `#edit-line`. Ids: `#room-panel`, `#room-holder`, `#run-button` (`#step-button #skip-button #rewind-button`), `#run-line`, `#result-card` (`#next-button`), `#hint-button` (`#hint-nudge #hint-hint #hint-answer`), `#answer-load-button`, `#undo-button`, `#clear-button`, `#best-button`, `#routine-tabs`, `#sandbox-box`, `#difficulty-slot`, stats `#stat-rooms #stat-gold #stat-parts #stat-runs`, tally `#stat-written #stat-hints ...` (inside a closed `<details id="tally">`: read `textContent`, not `innerText`), `#engine-status` (empty when ready). Panels `#rooms-panel #medals-panel #achievements-panel #workshop-panel #changelog-panel #settings-panel #info-page-panel`, each with a `#<name>-toggle-button`.
- **New panel / window**: markup + toggle button in `index.html`, wiring in `wire()` in `app.js`; for the Desktop boot add `[panelId, toggleButtonId, title]` to `pc-config.json` `windows` and run `/usr/bin/python3 scripts/generate-pc-pages.py` (`pc.html` is generated; `tests/test_desktop_boot.py` fails when it is stale or an id is missing). A new Python module goes into `ENGINE_MODULES` at the top of `app-1-core.js` (`tests/test_assets_and_shell.py`); `sw.js` is NOT edited by the AI.
- **New browser test**: copy `tests/test_example_browser.py` (uses `tests/browser_helpers.py`: `open_game(p, base)`; script errors are in `page.page_errors`).
- **Tests that pin things a task may change**: `test_rooms.py` (every room's reference solution is its par; flat rooms match the breadth-first solver), `test_run.py`, `test_dsl.py`, `test_editor.py`, `test_game_handle.py`, `test_render.py` (SVG markup), `test_pledge.py` (banned words, no clock or randomness, no audio), `test_chapters_hints_goals.py`, `test_difficulty.py`, `test_achievements.py` (perfect play earns all 14), `test_sandbox_and_whole_game.py`, `test_desktop_boot.py`, `test_accessibility.py`, `test_assets_and_shell.py`.
- **Do not**: invent a view key or an action (copy from above); look up an id in JS that `index.html` or a JS builder does not create; use a clock or `random` in the engine (`run.run` stays pure); change a room's layout or `ref` without `test_rooms.py` passing (par); make a failed run a dead end or any state colour-only.

## File map: the page script (LA-1e, 2026-10-22)
The old 49 KB `app.js` is cut into classic scripts that share ONE object, `window.RobotScriptApp` (called `A` inside each part; every part is its own function, so no new globals). They load in this order from `index.html`, next to each other, and `app.js` always loads last:
- `app-1-core.js` (creates the object): `ENGINE_MODULES`, save keys, `DIFF_TEXT`, `TILE`, `SPEED_MS`, `GLYPHS`, the shared state (`A.engine A.view A.roomId A.headDeg A.play A.playbackSpeed A.refocus A.sandboxTile A.PALETTE_SIG`), `$`/`el`/`setText`/`announce`/`showToast`/`plural`, `send(request, isEdit)`, `askThen`.
- `app-2-room.js`: stats, the room drawing (`applyFrame`, `initialFrame`, `markNode`, `renderGoals`, `renderRoomHead`) and run playback (`speedMs`, `stepFrame`, `invalidateRun`, `syncPlayButtons`, `advance`, `finishRun`, `startPlay`, `onRun`, `onStep`, `onSkip`, `onRewind`, breakpoints).
- `app-3-editor.js`: the list editor (`condSelect`, `smallButton`, `tools`, `buildList`, `buildNode`, `renderPalette`, `renderProgram`) and the keyboard (`onKey`).
- `app-4-panels.js`: About and What's New (`wirePanelToggle`, `loadChangelog`), the room picker and sandbox (`renderRooms`, `onRoomClick`), medals, goals, achievements, the workshop, hints, and `render()`.
- `app.js`: difficulty, long-press reordering (R4-RSMO-1), `wire()`, `TUTORIAL_STEPS`, `boot()`.
Rules for an edit: read and write shared state as `A.view`, `A.play` and so on, never a local copy; a function another part needs is exported as `A.name = name;` in the "what the other parts use" block at the end of its part, and a LATER part lists it in its `var x = A.x, ...` header (an earlier part calls it as `A.name()` at run time). `tests/test_script_parts.py` checks all of this; `tests/pagefiles.py` (`app_text()`) is how a test reads the page script; `tests/test_file_sizes.py` keeps every file under about 14,000 tokens and each part under 8,000.

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
- `game.handle(json)` returns the whole view; `room.svg` is sent only when the room changes (`svg_due`). A run returns `run` with every frame `[x, y, d, carry, partsMask, socketsMask, switchesMask, at]`; the page (`app-2-room.js`) plays them back (speed from `data-run-speed`, instant under reduced motion) and the engine has already recorded the result, so skipping the animation loses nothing.
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

## AN-17 (2026-10-11): difficulty choice (Easy / Normal / Hard)
- Owner answer Pq10. One shared start-of-game choice from `shared/difficulty.js` (`window.NoyvjDifficulty`, `shared/difficulty.css`, tests in `shared/tests/test_difficulty_browser.py`): a labelled radio group in `#difficulty-panel` / `#difficulty-slot` (a `<details>` open until a choice is made; in the Desktop boot it is the first block of the side column). Stored per browser and per game in `localStorage["difficulty:{slug}"]` (never in the save); `app.js` reads it at boot and on change and tells the engine with `{action: "difficulty", level}`; the engine keeps it in a module global (`difficulty`, default `"normal"`) that `reset` and `load_state` leave alone. Switching is allowed at any time (no mid-run lock needed in a puzzle game; `NoyvjDifficulty.setGuard` exists for a game that wants one).
- Design rule: difficulty changes only the surrounding pressure (help and medal bars), never the rules, the content or whether a puzzle can be finished. Normal is today's game: a test runs one scripted session with the level never told, told "normal", and after a detour through Hard and Easy, and requires byte-identical views and saves. Nothing is locked by any choice. Achievements and goals are always computed from the Normal records (so they stay reachable on Normal, and are the same whichever level was played).
- Medal bars (`rooms.limits`, `rooms.medal_for`): Normal gold at par, silver at par + max(2, par // 3) (unchanged); Easy both bars +2 steps; Hard gold at par, silver at par + max(1, par // 6). Easy: the first hint press opens the nudge and the hint together. Hard: no answer step (`load_answer` refused, ladder capped at 2, answer never shown).
- Records: `best` (fewest steps and the list) is the objective Normal record and every run, on any level, updates it as before; medals are derived from it (Easy and Normal read `best`, a looser bar is only another name for the same number). Hard keeps its own `hbest {room: steps}` (saved only when set, validated: the room needs a `best` entry and the value cannot be below it), so Hard medals only show for rooms cleared on Hard. A list loaded from the answer earns no Hard record until the editor is cleared (`Game.answered`, not saved). Scrap, the goals and the achievements follow the Normal medal.
- Tests: `tests/test_difficulty.py` (35).
