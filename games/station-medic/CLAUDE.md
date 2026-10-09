# Station Medic

Seed: `planning/station-medic-plan.md` (Quick ideas round B1, TODO QI-13). Personal project, no BCM tag, working title. Built 2026-10-09/10 by a background agent. Read `BUILD-STATUS.md` here first.

## One-line pitch
You are the only medic on Lowlight Station. Each shift a handful of crew arrive with signs; you choose scans and treatments from a small cabinet that restocks between shifts. A deduction and resource puzzle, never a race. Nobody dies on screen; a bad call costs a seal, and you can always restore the shift.

## Stack
- Pyodide Python, plain HTML/CSS, no build step. `game.py` is the single engine entry point (`handle(json) -> json`, `get_state()` / `load_state()` for the shared save widget); `app.js` is glue only. No audio, ever.
- Fiction notice: every condition, scan and treatment is invented. No real medicine, drug or disease names, no dosing, no death words (a lint test enforces it).

## Core constraints (do not violate without asking)
1. `Case.apply` is a pure function of the case, the state and the action: no clock, no randomness (a test scans the engine).
2. No timers, energy limits, grinding, loss of progress, roguelike or card mechanics, audio, mandatory leaderboard, all-good hero, on-screen death.
3. A bad call is never a dead end: Restore (free), borrow a supply (cost 1) and comfort care (cost 1) always work. Grades only rise.
4. Every authored shift must be FAIR (see below), checked by `solver.py` in the tests on every shift.
5. No colour-only encoding: supplies carry a letter, grades are words with different border styles.

## Rules as built (milestone 1)
- A `Case` (shift.py) compiles an authored shift (casekit `S`/`P`): a pool of conditions on the sheet, a stock dict (the shelves; a treatment is in play when its shelf is listed), the scans in play, beds (cold room), robots (Tally) and `maxc` (1 or 2 conditions per patient). Patients show ALL signs of their true condition(s); a scan reads positive if any true condition carries that finding.
- State is a tuple: `(stock, patients, borrowed)`, patient = `(closed, isolated, steady, readings, cured, cost, exposed, given)`. Actions: scan, treat, band, robot, isolate, release, comfort, borrow. Costs: ease 1, wasted treatment 1, comfort 1, borrow 1, reaction (chart note) 2, clash of two `heavy` treatments 2, contagious patient handled outside the cold room 2 (once). Grade: cost 0 clean (3), 1-2 steady (2), 3+ rough (1).
- Shaking patients need steadying (band or Tally) before a scan or treatment. The cold room holds `beds` patients and frees when its patient is settled.
- FAIR: `Solver` is an AND-OR search: a careful medic (scan only to split what still fits, treat when one set of conditions fits or one treatment cures every single-condition match, steady first, cold room before touching a possibly contagious patient) wins for EVERY set of look-alikes the signs allow, so no plan depends on luck. `tests/test_cases.py` also replays every possible world. `tools/check.py` and `tools/shrink.py` are authoring aids (tight shelves, minimal fair stocks).

## Milestones
See `planning/station-medic-plan.md` section 8 (the table is copied below and kept current).

| # | Milestone | Content | Status |
|---|-----------|---------|--------|
| 1 | Engine | lexicon, shift rules, solver, chapters 1-2 (15 shifts), tests | Done |
| 2 | Infirmary UI | ward, bedside panel, cabinet, sheet, log, result card, restore, save contract, favicon. Playable slice | Done |
| 3 | Chapters 3-5, hints, record | 24 more shifts, hint ladder, three-goals strip, crew files, Record (codex) | Done |
| 4 | Chapters 6-8 | 21 more shifts (60 in all), Tally, finale. First complete game | Done |
| 5 | Standard kit | opening screen, tutorial, About with the fiction notice, What's New, keyboard help, confirm dialogs, light theme, accessibility pass | Planned |
| 6 | Achievements | 14 achievements, panel, toast, manifest, reachability test | Planned |
| 7 | Desktop boot and wrap-up | `pc-config.json`, `pc.css`, `pc.js`, generated `pc.html`, docs, changelog | Planned |

## Working conventions
- Commit only this folder and the plan with a pathspec commit, then tag `station-medic-milestone-0N`. Hub registration is a separate later job.
- Tests: `python3 -m pytest -q games/station-medic`; lint: `python3 -m flake8 --extend-ignore=E501 games/station-medic`. Local Python is 3.9 (Pyodide runs 3.12): no 3.10+ syntax in engine code.

## Engine and page notes (milestone 2)
- `game.handle(json)` returns the whole view every time (patients with portraits and per-button availability, sheet, cabinet, log, result, shifts list, totals, tally, hint). `app.js` only draws it; the selected patient is page state.
- Save (`get_state`): `cur`, `best {shift: 1-3}`, `run {shift: [action tokens]}` (each unfinished shift keeps its actions and is replayed and re-checked on load), `tally`, `flags`, `cured`/`cures`/`tests` (the Record's facts); only non-default keys.
- Hints (`hints.py`) come from the solver's best move for the state on screen: nudge, hint, answer, then `hint_do` performs it (or restores if a clean finish is gone). A test follows the hints through every shift and expects Clean.
- Settings: text size, "Rule out for me" (dims and strikes through sheet conditions that cannot fit the selected patient; default on), reduce motion, effects, high contrast, theme. All per device, not in the save.

## Milestone 3 notes
- Chapters: 1 Quiet Hours (7), 2 The Second Look (8), 3 Chart Notes (8, `cases_3.py`), 4 Shared Shelves (8, roll and vials serve a scan and a treatment), 5 The Cold Room (8, beds). Stocks were found with `tools/shrink.py` and written with `tools/setstock.py`; every shift must have at least one tight shelf (test).
- The Record (`codex.py`): conditions (first cured), scans (first run), treatments (first cure), crew files (a beat is told when the shift it belongs to is done; beat k belongs to that crew member's `cast.BEAT_AT[k]`-th appearance in authored order), Tally's beats (shifts with robots), station notes (a chapter's shifts all done). All derived from `best`, `cured`, `cures`, `tests` in the save. Opens with the fiction notice.
- `achievements.py` holds the 14 achievements (facts, need, chapter gate) and `goals()` (the three always-visible, any-order goals); the in-game panel, toast and `achievements.json` manifest arrive in milestone 6. `achievements_earned` is already written to the save and never read back.

## Milestone 4 notes
- 60 shifts: 7, 8, 8, 8, 8, 8, 7, 6. Chapter 6 teaches shaking patients (bands from `band` on the shelf, Tally from 6-4: `robots=1` steadies one patient for free), chapter 7 two-condition patients (`maxc=2`, heavy clashes), chapter 8 mixes everything and its last shift closes the year.
- Tally's five beats are told on the 1st, 4th, 8th, 12th and 16th shift where Tally is on duty (`codex.TALLY_AT`). Every crew member appears at least 13 times so all six of their beats are reachable (test).
- `tests/test_whole_game.py` plays all 60 shifts with the hint ladder (all Clean), then fills the last Record pages, and expects all 14 achievements and a 100% Record: the game is completable from a clean save.
