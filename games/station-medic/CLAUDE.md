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
| 2 | Infirmary UI | ward, bedside panel, cabinet, sheet, log, result card, restore, save contract, favicon. Playable slice | Planned |
| 3 | Chapters 3-5, hints, record | 24 more shifts, hint ladder, three-goals strip, crew files, Record (codex) | Planned |
| 4 | Chapters 6-8 | 21 more shifts (60 in all), Tally, finale. First complete game | Planned |
| 5 | Standard kit | opening screen, tutorial, About with the fiction notice, What's New, keyboard help, confirm dialogs, light theme, accessibility pass | Planned |
| 6 | Achievements | 14 achievements, panel, toast, manifest, reachability test | Planned |
| 7 | Desktop boot and wrap-up | `pc-config.json`, `pc.css`, `pc.js`, generated `pc.html`, docs, changelog | Planned |

## Working conventions
- Commit only this folder and the plan with a pathspec commit, then tag `station-medic-milestone-0N`. Hub registration is a separate later job.
- Tests: `python3 -m pytest -q games/station-medic`; lint: `python3 -m flake8 --extend-ignore=E501 games/station-medic`. Local Python is 3.9 (Pyodide runs 3.12): no 3.10+ syntax in engine code.
