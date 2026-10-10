# Evidence Hunt build status (handoff file)

Updated after every milestone. Read `planning/evidence-hunt-plan.md`, `CLAUDE.md` here, then this file. Hub registration is NOT part of this build.

## Done
- M1 Engine: lexicon.py (6 evidence, 12 kinds, 6 behaviours, 6 features, 8 keepsakes, room types), houses.py (18 layouts), casework.py (rules), solver.py (fairness, validate, careful plan), casekit.py, cases_1..5.py (all 40 authored cases, generated from tools/), progress.py, tests (35).

## Next
- M2 Case UI: index.html, app.js, style.css, settings.js, render.py, game.py (`handle`, `get_state`, `load_state`), changelog.json, favicon, tests.

## Open problems / notes
- Local Python is 3.9: engine code avoids 3.10+ syntax.
- To rework a case: edit `tools/specs.py` / `tools/texts.py`, run `python3 tools/build_cases.py`, run the tests.
