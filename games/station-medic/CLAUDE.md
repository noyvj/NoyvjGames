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
| 5 | Standard kit | opening screen, tutorial, About with the fiction notice, What's New, keyboard help, confirm dialogs, light theme, accessibility pass | Done |
| 6 | Achievements | 14 achievements, panel, toast, manifest, reachability test | Done |
| 7 | Desktop boot and wrap-up | `pc-config.json`, `pc.css`, `pc.js`, generated `pc.html`, docs, changelog | Done |

## For the local AI (exact names; every one was checked against the code on 2026-10-18)
- **Files**: engine `game.py` (entry point, `Game` class, `handle`), `shift.py` (`Case`: the rules; `grade_of`, `grade_for`, `replay`), `solver.py`, `hints.py`, `lexicon.py` (conditions, signs, scans, treatments, items), `progress.py` (chapters, `ORDER`, totals), `codex.py` (the Record), `achievements.py`, `render.py` (portraits), `info.py`, `cast.py`, `casekit.py` + `cases_1.py`..`cases_8.py` (the 60 authored shifts); page `index.html`, `app.js` (the whole page; engine module list `ENGINE_MODULES` at its top), `settings.js`, `pc.js`, `pc-config.json`, generated `pc.html`.
- **Entry points** (the only Python the page calls): `handle(json_string) -> json_string`, `get_state()`, `load_state(proxy)` (it then calls `window.stationMedicRefresh()`). In JS use `send({action: ...})` or `act({action: ...})` (inside app.js; they render and save). Never read a Python variable from JS by name. The answer is the WHOLE view; a bad request gives `{"error": ...}` and the page shows "Something went wrong". `game.py`'s docstring leaves out `difficulty`.
- **Actions** (`handle`; an unknown name is `{"error": "unknown action ..."}`): `open` | `reset` | `pick {shift}` (id such as `"1-1"`) | `next` | `scan {p, t}` | `treat {p, x}` | `band {p}` | `robot {p}` | `isolate {p}` | `release {p}` | `comfort {p}` | `borrow {item}` | `restore` | `undo` | `hint` | `hint_do` | `difficulty {level}` (`easy`, `normal`, `hard`). `p`, `t`, `x`, `item` are whole numbers (patient, scan, treatment and shelf positions on this shift, from the view); anything else is refused with `ok: false`.
  A new action = a branch in `handle` (the `action in (...)` tuple is for patient actions that go through `Game.do`), the rule in `shift.Case.apply`, a test, a line in the docstring.
- **Top-level keys of the view** (`Game.view`): `ok message difficulty shift patients sheet cabinet log result rooms totals tally hint about goals achievements record`. `view.shift`: `id title intro chapter number of best best_name cost grade_now grade_now_name done borrowed scene patients_n`. Each `view.patients[i]`: `i name first role crew say signs notes closed outcome cost iso steady shaking readings matches fits certain risky portrait actions care`. `view.cabinet`: `items tests tx beds beds_used robots robots_used`. `view.hint`: `rung max` plus `nudge kind hint answer label` as the rung rises.
- **get_state() keys** (only non-defaults are written): `cur best run tally cured cures tests tiers achievements_earned` (`achievements_earned` is write-only). New save fields: only when non-default, validated in `Game.load` (a bad field falls back, never raises).
- **Page**: `render()` in app.js draws one view; hook after it with the `station-medic-rendered` event on `document` (`window.stationMedicView()` returns the last view). Main ids: `#shift-panel`, `#patients`, `#bedside`, `#scan-row`, `#treat-row`, `#care-row` (buttons carry `data-testid` `station-medic-scan-<t>`, `-treat-<x>`, `-patient-<i>`, `-comfort`, `-band`, `-robot`, `-isolate`), `#result-card`, `#next-button`, `#restore-button`, `#hint-button`, `#hint-do-button`, `#action-line`, `#cabinet-panel`, `#sheet-panel`, `#log-panel`, `#goals`, `#stats`; window panels `#shifts-panel`, `#record-panel`, `#achievements-panel`, `#changelog-panel`, `#settings-panel`, `#info-page-panel` (each opened by a `*-toggle-button`); `#engine-status` is empty when the engine is ready.
- **New panel / window**: markup + toggle button in `index.html`, wiring in app.js `wire()` (`wirePanelToggle(buttonId, panelId)`), drawing in `render()`; for the Desktop boot add `[panelId, toggleButtonId, title]` to `pc-config.json` `windows` (and an icon or menu id if wanted), then run `/usr/bin/python3 scripts/generate-pc-pages.py` (rewrites every game's `pc.html`; only this game's changes). `tests/test_desktop_boot.py` fails if `pc.html` is stale or a toolbar button is neither icon, menu entry nor window toggle. A new Python module goes into `ENGINE_MODULES` at the top of app.js (`tests/test_assets_and_shell.py` compares it with the `.py` files; `sw.js` is NOT edited by the AI).
- **New browser test**: copy `tests/test_example_browser.py` (uses `tests/browser_helpers.py`: `open_game(p, base)`; script errors are in `page.page_errors`).
- **Tests that pin things a task may change**: `test_pledge.py` (banned words, no real medicine, no death words, no timers), `test_game_handle.py` (view keys, save round trip, hint ladder), `test_cases.py` (every shift is fair), `test_whole_game.py` (all 60 shifts, all 14 achievements), `test_difficulty.py` (Normal must stay byte-identical), `test_assets_and_shell.py` (module list, ids), `test_desktop_boot.py`, `test_accessibility.py`, `test_achievements.py`.
- **Do not**: invent a view key or an action (copy from above); look up an id in JS that `index.html` or a JS builder does not create; use a clock, `random` or the network in the engine (a test scans for it); add a timer, energy, death or a real medical word; make a bad call a dead end (Restore, borrow and comfort care must always work).

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

## Milestone 5 notes
- Standard kit: shared opening screen (Continue / New Game / Saves), a 9-step tutorial (`TUTORIAL_STEPS` in app.js, reopened from the Tutorial button; `window.stationMedicTutorialSteps` lets the Desktop boot swap in its own steps), About with the fiction notice and pledge, What's New + banner, keyboard help (1 to 4 pick a patient), confirm dialogs for Restore, Comfort care and the whole-game reset, story toggle on the story lines, light theme.
- `tests/test_accessibility.py` computes contrast from the CSS variables in both themes and checks the shape/word cues (settled ring + dashed border + the word, seals with distinct borders, readings by border style, letters on shelves, struck-through ruled-out conditions).

## Milestone 6 notes
- `achievements.json` (the hub manifest) is generated from `achievements.py` and a test keeps them equal. The panel shows a number on every achievement (earned, or have/need), a toast announces a new one (also to screen readers), and `achievements_earned` is written to the save and never read back. `test_whole_game.py` proves all 14 can be earned and the Record filled from a clean save.

## Milestone 7 notes and pre-release checklist
- Desktop boot: the ward (patients, bedside, result, hints) is the stage; the cabinet, the sheet, the log and the tally are the side column; the stats strip and the three goals sit above the stage. `pc.html` is generated for this game only (`importlib` on `scripts/generate-pc-pages.py`, `build("station-medic", cfg)` written to `pc.html`); `python3 scripts/generate-pc-pages.py --check` and `python3 -m pytest -q shared/tests -k medic` pass. The Classic two-column grid in `style.css` is scoped to `html:not([data-layout="pc"])`.
- Hub registration (title card, `sw.js` precache, `game-*.json`, share cards, root CLAUDE.md row, dev logs) is not part of this folder. The owner's questions are the last section of `planning/station-medic-plan.md`.
- Manual checks worth a human pass: a screen reader walk through the patient cards and bedside actions, real-device touch on the small supply buttons, the Desktop tutorial steps, and the opening-screen "Switch to Desktop layout" button on a wide window.
- AN-6 (2026-10-11): every chapter is open from the start (`progress.OPEN_AT = 0`, `chapter_open` is always true; the Shifts panel has no locked state). A shift is done at any grade, so a Rough seal counts toward totals, goals and achievements; the chapter field in `achievements.ACHIEVEMENTS` is now only an ordering hint (all chapters open). Old saves load unchanged. Tests: `test_every_chapter_is_open_from_the_start_...`, `test_a_rough_shift_counts_as_done_...`.

## AN-17 (2026-10-11): difficulty choice (Easy / Normal / Hard)
- Owner answer Pq10. One shared start-of-game choice from `shared/difficulty.js` (`window.NoyvjDifficulty`, `shared/difficulty.css`, tests in `shared/tests/test_difficulty_browser.py`): a labelled radio group in `#difficulty-panel` / `#difficulty-slot` (a `<details>` open until a choice is made; in the Desktop boot it is the first block of the side column). Stored per browser and per game in `localStorage["difficulty:{slug}"]` (never in the save); `app.js` reads it at boot and on change and tells the engine with `{action: "difficulty", level}`; the engine keeps it in a module global (`difficulty`, default `"normal"`) that `reset` and `load_state` leave alone. Switching is allowed at any time (no mid-run lock needed in a puzzle game; `NoyvjDifficulty.setGuard` exists for a game that wants one).
- Design rule: difficulty changes only the surrounding pressure (help and medal bars), never the rules, the content or whether a puzzle can be finished. Normal is today's game: a test runs one scripted session with the level never told, told "normal", and after a detour through Hard and Easy, and requires byte-identical views and saves. Nothing is locked by any choice. Achievements and goals are always computed from the Normal records (so they stay reachable on Normal, and are the same whichever level was played).
- Seal bars (`shift.grade_for`): the cost of a shift is the same fact on every level. Normal: Clean at 0, Steady at 1 or 2 (unchanged `grade_of`); Easy: Clean at 1 or less, Steady at 3 or less; Hard: Clean at 0, Steady only at 1. Easy: the first hint press opens the nudge and the hint together. Hard: no answer step (`hint_do` refused, ladder capped at 2).
- Records: `best` is always judged from the cost with the Normal bars (so a finish on any level never lowers it, and the goals and achievements stay on Normal); Easy and Hard also keep `tiers {easy|hard: {shift: 1-3}}` in the save (validated: needs a Normal seal, Hard cannot beat it). Easy shows the better of its own seal and the Normal seal; Hard shows only Hard seals. A shift where `hint_do` ran this session earns no Hard seal (`Game.helped`, not saved, cleared by Restore).
- Tests: `tests/test_difficulty.py` (33).
