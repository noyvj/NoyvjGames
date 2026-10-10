# Hull Repair

Seed: `planning/hull-repair-plan.md` (Quick ideas round A2, TODO QI-2). Personal project, no BCM tag, working title. Built 2026-10-09/10 by a background agent.

## One-line pitch
Flow-Free-style routing of power and pipes across a damaged space-station hull: every board repairs one room on a station map, so the puzzles form a bigger picture.

## Stack
- Pyodide Python, plain HTML/CSS, no build step. `game.py` is the single engine entry point (`handle(json) -> json`, `get_state()` / `load_state()` for the shared save widget); `app.js` is glue only. Board, lines and map are SVG strings built in Python (`render.py`) so their markup is unit-tested.
- Runs from any static server. No audio files, ever; the only sound is the optional generated palette below (off by default). Python 3.9 locally (Pyodide 3.12): no 3.10+ syntax in engine code.

## Core constraints (do not violate without asking)
1. Rules, validation and solving are pure and deterministic: no clock, no randomness in the engine (a test scans it). `tools/gen.py` uses a seeded `random` to FIND boards; its output is frozen in `boards_*.py`.
2. No timers, energy, grinding or progress loss; no roguelike, deck or card mechanics; no audio files (optional generated tones only, see Sound); no mandatory leaderboard; no all-good hero.
3. A failed or wrong drawing is never a dead end: lines can be trimmed, cut, undone or cleared; hints are free; states only go up.
4. Every board has exactly one restored layout (every line joined, every open cell covered), stored in `sol`, and the solver proves it in tests.
5. No colour-only encoding: every line has its own port shape and letter.

## Rules as built
- Cells: `.` open, `#` hole, `=` bridge, `^ > v <` valve, `A-H` source port, `a-h` sink port, `1-3` mixer (board `mixers` {"1": "AB"} names the two lines that end there). Lines are lists of (x, y) cells started on a port; `rules.check_layout` is the one judge of legality.
- Status: 0 open, 1 patched (every line joined), 2 restored (and every open cell covered). A bridge cell needs one line across it to count as covered; a valve and a mixer must be passed or reached.
- `play.Drawing` applies a touch (`begin`, `move`*, `end`): drag from a port to lay a line, drag back over your own line to trim, drag into another line to cut it, tap the end of a line (or the far port of a joined line) to take one cell back; bridges and valves force straight moves; a line may start on its sink port.

## Milestones
| # | Milestone | Content | Status |
|---|-----------|---------|--------|
| 1 | Engine | `rules.py`, `play.py`, `tools/solver.py`, `tools/gen.py`, `boards.py` + deck 1 (8 boards), tests | Done |
| 2 | Board UI | SVG board, pointer and keyboard drawing, result card, board picker, favicon, settings, save contract | Done |
| 3 | Decks 2-3, map, log, hints | 16 boards, deck gating, station map, repair log, hint ladder, three-goals strip | Done |
| 4 | Decks 4-5 | 16 boards (40 in all) with valves and mixers. First complete game | Done |
| 5 | Standard kit | Opening screen, tutorial, About, What's New, keyboard help, confirm dialogs, light theme, accessibility pass | Done |
| 6 | Achievements | 14 achievements, panel and toast, manifest, reachability test | Done |
| 7 | Desktop boot and wrap-up | `pc-config.json`, `pc.css`, `pc.js`, generated `pc.html`, docs, changelog | Done |

## Working conventions
- Commit only this folder and the plan with a pathspec commit, then tag `hull-repair-milestone-0N`. Hub registration is a separate later job.
- Tests: `python3 -m pytest -q games/hull-repair`; lint: `python3 -m flake8 --extend-ignore=E501 games/hull-repair`.
- Finding boards: `python3 tools/gen.py W H [--holes x,y ...] [--bridges x,y ...] [--valves N] [--mixers N] --seeds 1-40`, then freeze the chosen seeds into a `boards_*.py` file.

## Engine and page notes (milestone 2)
- `game.handle(json)` returns the whole view; `board.svg` is sent only when the board changes (`svg_due`), `layer` (the lines layer, `render.lines_svg`) every time. The page replaces only `<g id="hr-lines">`.
- A touch is `begin {x,y}`, `move {cells}`, `end`; the engine records a better layout at `end` (`_record`) and returns a `result` (patched or restored, empty cells left, next board). Undo/clear/clear_line also re-record.
- Save (`get_state`): `cur`, `best {board: "A0102;B..."}` (re-judged by `rules.decode`/`rules.status` on load), `draft {board: text}`, `tally` (laid, erased, undos), `flags` (bridge, valve, mix, retry); only non-default keys.
- Keyboard: arrows move a cursor, Enter/Space picks a line up and puts it down, Backspace takes a cell back, Escape lets go, Z undoes. Pointer: pointer capture on `#board-holder`, `touch-action: none`.

## Milestone 3 notes
- Decks: 1 plain (`boards_dock.py`), 2 holes (`boards_crew.py`), 3 bridges (`boards_engineering.py`); a deck opens at 5 patched rooms of the one before (`progress.py`). Every bridge board really crosses on a bridge (tested).
- Hints (`hints.py`): rung 1 nudge, rung 2 hint (ghost of the opening cells of the most constrained long line), rung 3 answer (ghost of every line, `load_answer` lays it, undoable). Free, saved per board in `rungs`, never touch a status.
- Station map (`render.station_svg`): five decks of eight rooms, state by shape (cracked / dashed ring / check mark) as well as light; clicking a room opens it. Repair log (`logbook.py`): one quiet line per room (all 40 written), found when the room is patched.
- Goals strip: `achievements.goals` gives the next three unearned achievements that can be worked on now (facts only; the manifest, panel and toast arrive in milestone 6).
- Board finding: `tools/gen.py` widens the letter set while searching (up to 14 lines), then merges lines back down while the layout stays unique, so 6x6 and 7x7 boards with 6 to 8 lines come out fast. 8x8 and 9x9 are much rarer (see BUILD-STATUS).

## Milestone 4 notes
- Deck 4 (`boards_life.py`): 7x7 and 8x8 boards with valves (every board has load-bearing valves; a test checks at least three boards become ambiguous without theirs). Deck 5 (`boards_core.py`): mixers, with valves, bridges and holes mixed in; six 8x8 and two 9x9 boards (9x9 within the 8-line cap is rare for the generator, so those two lean on valves and holes).
- The valve is drawn above the lines so its arrow stays readable. The solver prunes with a degree check per open cell, an isolated-region check and a reachability check; every board is proven in about a second in tests. The slow check (`fill=False`, connect-only) is not run per board.
- Generator tools: `tools/gen.py` (seeded; `make(params, seed)`), `FAIL` counters say why a seed failed.

## Milestone 5 notes
- Standard kit as in Robot Script: opening screen, 8-step tutorial (`TUTORIAL_STEPS`; the Desktop boot will replace them through `window.HULL_REPAIR_PC_TUTORIAL_STEPS`), About from `info.py` (invented place, no real-world facts, so no sources to date), What's New + banner, keyboard help (`?`), reset confirm dialog, story toggle on `.story-text` (the repair-log lines), light theme (contrast tested for every line colour in both themes), `tests/test_pledge.py` (banned words, no clock or randomness, one cosmetic timeout, no audio, every action moves a visible number).

## Milestone 6 notes
- `achievements.py` holds the table and the facts; `achievements.json` is the hub manifest (id, label, description; a test keeps them equal). `achievements_earned` is written to the save and never read back. Panel and toast in `app.js` use the hub hooks (`data-achievement-id`, `data-achievement-label`); the share button comes from `shared/achievement-share.js`. A test plays all 40 boards from the stored layouts, takes a line back once and climbs the ladder once, and checks all 14 are earned.

## Milestone 7 notes and pre-release checklist
- Desktop boot: the board is the stage, the tally is the side column, the stats strip and the three goals sit above the stage; Station, Repair log, Achievements, What's New, Settings and About open as windows. `pc.html` is generated for this game only (`importlib` on `scripts/generate-pc-pages.py`, `build("hull-repair", cfg)` written to `pc.html`); `python3 scripts/generate-pc-pages.py --check` and `python3 -m pytest -q shared/tests -k hull` pass.
- Hub registration (title card, `sw.js` precache, `game-*.json`, root CLAUDE.md row, share cards, dev logs) is still to do and is not part of this folder. The owner's questions are the last section of `planning/hull-repair-plan.md`.
- Manual checks worth a human pass: real-device touch drawing (drag with a finger, tap the end of a line), a screen-reader walk through the keyboard cursor, and the opening-screen "Switch to Desktop layout" button on a wide window.

## Sound (AU-2, 2026-10-11)
- Optional generated tones from `shared/sfx.js` (Web Audio, no files; off by default; the Settings panel mounts `NoyvjSfx.control()` in `#sfx-setting-slot`). Cues are called only from `app.js` `soundFor()` after the engine answers, never from the Python engine: `confirm` when a line becomes joined, `click_low` when a joined or started line is cut, taken back or cleared, `bell` when a room becomes fully restored. Nothing is communicated by sound alone, and the About pledge says so. The Sources page lists "Generated sound (Web Audio)".
