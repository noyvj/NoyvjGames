# Evidence Hunt build status (handoff file)

Updated after every milestone. Read `planning/evidence-hunt-plan.md`, `CLAUDE.md` here, then this file. Hub registration is NOT part of this build.

## Done
- M1 Engine: lexicon.py (6 evidence, 12 kinds, 6 behaviours, 6 features, 8 keepsakes, room types), houses.py (18 layouts), casework.py (rules), solver.py (fairness, validate, careful plan), casekit.py, cases_1..5.py (all 40 authored cases, generated from tools/), progress.py, tests (35).

- M2 Case UI: game.py, render.py, hints.py, info.py, index.html, app.js, style.css, settings.js, changelog.json, favicon; 76 tests; checked live at 1440x900 and 360x740 (walk, pack, read, wrong name, right name, no horizontal scroll).

- M3 Guide and hints: codex.py (37 pages), achievements.py (14 facts + goals), Guide panel, three-goals strip, cover-the-sheet toggle, keepsake return, guide-pages stat; 87 tests incl. a whole-game run (40 Clean, 12 complete spirit pages, 37-page guide); Guide panel and goals checked live.

## Next
- M4 Sandbox and finale: gen.py (codes EH<d>-<base36>), generator with rejection by the solver, Practice button/panel, tally `sandbox`, tests.

## Open problems / notes
- Local Python is 3.9: engine code avoids 3.10+ syntax.
- To rework a case: edit `tools/specs.py` / `tools/texts.py`, run `python3 tools/build_cases.py`, run the tests.
