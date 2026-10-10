# Evidence Hunt

Seed: `planning/evidence-hunt-plan.md` (Quick ideas round D5, TODO QI-29). Personal project, no BCM tag, working title. Built 2026-10-10 by a background agent. Read `BUILD-STATUS.md` here first. SOLO only; co-op by invite code is parked.

## One-line pitch
A quiet investigator's notebook. Each case is a haunted house drawn as a dark floor plan; you pack a few pieces of equipment, walk the rooms, take readings that come back as text, and deduce which of twelve invented spirit kinds is in the house. A solved case ends with a warm note about who the spirit was.

## Stack
- Pyodide Python, plain HTML/CSS, no build step. `game.py` is the single engine entry point (`handle(json) -> json`, `get_state()` / `load_state()` for the shared save widget); `app.js` is glue only. No audio, ever.
- Fiction notice: the spirits, rules and houses are all invented.

## Core constraints (do not violate without asking)
1. `Case.apply` is a pure function of the case, the state and the action: no clock, no randomness (a test scans the engine).
2. No timers, energy limits, grinding, loss of progress, roguelike or card mechanics, audio, mandatory leaderboard, jump scares, gore or on-screen harm.
3. A wrong name is never a dead end: the notebook stays, you can name again, and Restore is free. Seals only rise.
4. Every authored case must be FAIR (see below), checked by `solver.py` in the tests on every case.
5. No colour-only encoding: a reading is a word plus a border style, a restless room is a word plus a mark.

## Rules as built (milestone 1)
- Six evidence (cold, charge, script, lights, prints, glow), each read with one piece of equipment (same index). Twelve kinds in `lexicon.py`, each with exactly 3 evidence and 2 behaviours (tidy, mover, shy, curious, fond = exactly one restless room, roamer = two or more).
- A `Case` (casework.py) compiles an authored dict (casekit `C`): a house layout (`houses.py`), the sheet (pool), the truth (1 or 2 kinds), restless rooms per presence, room features (each fools one reading), an optional keepsake (masks its room, looking gives one more line of testimony), the kit size and the client's account lines (behaviour, room or None).
- State tuple: kit bitmask, room, read, trips, wrong, solved, covered, looked, returned, entered bitmask, notes (6 cells per room: 0 unknown, 1 clear, 2 positive, 3 doubtful). Actions: pack, van, go, use, look, accuse, cover, return. Cost = wrong accusations + extra trips; seal 0 Clean, 1-2 Steady, 3+ Rough.
- FAIR: `solver.analyse` finds every bag of at most `kit` pieces that tells the remaining candidates apart in the restless room(s) (using only readings the features do not spoil). `validate` also needs the true kind to survive the file's own testimony and the answer to be unique once everything is read. `next_action` is the careful plan (enter every room, look at the keepsake, pack the smallest working bag, read, name); a test follows it through every case and expects Clean.
- Authoring aids in `tools/`: `specs.py` (skeletons), `design.py` (finds a sheet and account), `texts.py` (the words), `build_cases.py` (writes `cases_1..5.py`). The chapter files are plain data and are what the game reads.

## Milestones
See `planning/evidence-hunt-plan.md` section 8 (the table is copied below and kept current).

| # | Milestone | Content | Status |
|---|-----------|---------|--------|
| 1 | Engine | lexicon, houses, case rules, solver, all 40 cases, tests | Done |
| 2 | Case UI | floor plan, kit, notebook, accuse, restore, save contract, favicon. Playable slice | Done |
| 3 | Guide and hints | hint ladder, three-goals strip, field guide, keepsake return | Done |
| 4 | Sandbox and finale | seeded codes, generator. First complete game | Planned |
| 5 | Standard kit | opening screen, tutorial, About with the fiction notice, What's New, keyboard help, confirm dialogs, light theme, accessibility | Planned |
| 6 | Achievements | 14 achievements, panel, toast, manifest, reachability test | Planned |
| 7 | Desktop boot | `pc-config.json`, `pc.css`, `pc.js`, generated `pc.html`, docs | Planned |

## Working conventions
- Commit only this folder and the plan with a pathspec commit, then tag `evidence-hunt-milestone-0N`. Hub registration is a separate later job.
- Tests: `python3 -m pytest -q games/evidence-hunt`; lint: `python3 -m flake8 --extend-ignore=E501 games/evidence-hunt`. Local Python is 3.9 (Pyodide runs 3.12): no 3.10+ syntax in engine code.

## Engine and page notes (milestone 2)
- `game.handle(json)` returns the whole view every time (house floors with per-room state, bag, current room, notebook, accounts, could-be groups, sheet, accuse options, log, result, chapters, totals, tally, hint, about). `app.js` only draws it; the picked suspects are page state.
- The view never says which rooms are restless before you walk in (`restless` is null until entered), and `could` stays empty until a restless room has been entered. A test checks both.
- Save (`get_state`): `cur`, `best {case: 1-3}`, `run {case: [action tokens]}` (each unfinished case keeps its actions and is replayed and re-checked on load), `tally`, `met` (kinds named), `seen` (kind -> evidence confirmed, written only when a case is solved so the guide never leaks the truth), `ev`, `eq`, `kept`, `mem`; only non-default keys. Every field is validated on its own.
- `app.js` builds the floor plan and the bag once per case and updates them in place (focus stays on a tapped room); rebuilt button rows go through `keepFocus`.
- Settings (`settings.js`): text size, "Rule out for me" (dims and strikes through suspects the notebook has ruled out; default on), reduce motion, effects, high contrast, theme. All per device, not in the save.
- Layout: `#side-col` wraps the notebook, sheet, log and tally; Classic is two columns from 900px.

## Milestone 3 notes
- The field guide (`codex.py`): Spirits (12; filed when first named, COMPLETE when positive readings in solved cases have confirmed all three of its evidence, then it shows "(complete)"), Evidence (6, first positive reading), Equipment (6, first use), Keepsakes (8, returned), House notes (5, a chapter's cases all done) = 37 pages. All derived from the save's facts (`met`, `seen`, `ev`, `eq`, `kept`, `best`). `seen` is only written at solve time so the guide never gives the answer away mid-case.
- Keepsake return: a button on the result card, and the `return` action also works later from any solved case (best seal above 0), so a reload after solving never loses it.
- "Cover the sheet" (`cover` action, a token in the run): hides the evidence and habit lines of kinds whose guide page is complete. The set of distinct authored cases solved with it covered is `mem` (the From Memory achievement).
- `achievements.py` holds the 14 achievements (facts, need, chapter gate) and `goals()` (the three always-visible, any-order goals); the in-game panel, toast and `achievements.json` manifest arrive in milestone 6. `achievements_earned` is already written to the save and never read back.
- `tests/helpers.py`: `solve_with_hints` (the careful plan through the JSON entry point) and `solve_thoroughly` (a player who knows the answer: packs the truth's own evidence, one trip per presence). `test_whole_game.py` plays all 40 cases Clean with the hints, replays every case thoroughly, returns every keepsake and expects 12 complete spirit pages and a full 37-page guide.
