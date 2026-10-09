# Hull Repair

Seed: `planning/hull-repair-plan.md` (Quick ideas round A2, TODO QI-2). Personal project, no BCM tag, working title. Built 2026-10-09/10 by a background agent.

## One-line pitch
Flow-Free-style routing of power and pipes across a damaged space-station hull: every board repairs one room on a station map, so the puzzles form a bigger picture.

## Stack
- Pyodide Python, plain HTML/CSS, no build step. `game.py` is the single engine entry point (`handle(json) -> json`, `get_state()` / `load_state()` for the shared save widget); `app.js` is glue only. Board, lines and map are SVG strings built in Python (`render.py`) so their markup is unit-tested.
- Runs from any static server. No audio, ever. Python 3.9 locally (Pyodide 3.12): no 3.10+ syntax in engine code.

## Core constraints (do not violate without asking)
1. Rules, validation and solving are pure and deterministic: no clock, no randomness in the engine (a test scans it). `tools/gen.py` uses a seeded `random` to FIND boards; its output is frozen in `boards_*.py`.
2. No timers, energy, grinding or progress loss; no roguelike, deck or card mechanics; no audio; no mandatory leaderboard; no all-good hero.
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
| 4 | Decks 4-5 | 16 boards (40 in all) with valves and mixers. First complete game | Planned |
| 5 | Standard kit | Opening screen, tutorial, About, What's New, keyboard help, confirm dialogs, light theme, accessibility pass | Planned |
| 6 | Achievements | 14 achievements, panel and toast, manifest, reachability test | Planned |
| 7 | Desktop boot and wrap-up | `pc-config.json`, `pc.css`, `pc.js`, generated `pc.html`, docs, changelog | Planned |

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
