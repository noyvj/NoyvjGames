# Evidence Hunt build status (handoff file)

Updated after every milestone. Read `planning/evidence-hunt-plan.md`, `CLAUDE.md` here, then this file. Hub registration is NOT part of this build.

## Done
- M1 Engine: lexicon.py (6 evidence, 12 kinds, 6 behaviours, 6 features, 8 keepsakes, room types), houses.py (18 layouts), casework.py (rules), solver.py (fairness, validate, careful plan), casekit.py, cases_1..5.py (all 40 authored cases, generated from tools/), progress.py, tests (35).

- M2 Case UI: game.py, render.py, hints.py, info.py, index.html, app.js, style.css, settings.js, changelog.json, favicon; 76 tests; checked live at 1440x900 and 360x740 (walk, pack, read, wrong name, right name, no horizontal scroll).

## Next
- M3 Guide and hints: the field guide (codex.py), three-goals strip (achievements facts), Guide panel, keepsake return in the result card, cover-the-sheet toggle, guide-pages stat.

## Open problems / notes
- Local Python is 3.9: engine code avoids 3.10+ syntax.
- To rework a case: edit `tools/specs.py` / `tools/texts.py`, run `python3 tools/build_cases.py`, run the tests.
