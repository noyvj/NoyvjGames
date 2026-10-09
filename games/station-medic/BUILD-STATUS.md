# Station Medic build status (handoff file)

Updated after every milestone. Read `planning/station-medic-plan.md`, `CLAUDE.md` here, then this file. Hub registration is NOT part of this build.

## Done
- M1 Engine: lexicon.py (31 invented conditions, 4 scans, 8 treatments), shift.py (rules), solver.py (AND-OR fairness search), casekit.py, cases_1.py + cases_2.py (15 shifts), cast.py (names only), tools/check.py + tools/shrink.py; 30 tests, flake8 clean.

## Next
- M2: game.py (handle/get_state/load_state), progress.py, render.py (SVG), index.html, app.js, style.css, settings.js, changelog.json, favicon, view tests; live check at 1440x900 and 360x740.

## Open problems / notes
- Local Python is 3.9: engine code avoids 3.10+ syntax.
- Fairness is strict (every look-alike world must finish clean), so stocks are tight; use tools/shrink.py to find minimal stocks when authoring.
