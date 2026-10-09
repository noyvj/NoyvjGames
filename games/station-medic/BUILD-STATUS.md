# Station Medic build status (handoff file)

Updated after every milestone. Read `planning/station-medic-plan.md`, `CLAUDE.md` here, then this file. Hub registration is NOT part of this build.

## Done
- M1 Engine: lexicon.py (31 invented conditions, 4 scans, 8 treatments), shift.py (rules), solver.py (AND-OR fairness search), casekit.py, cases_1.py + cases_2.py (15 shifts), cast.py (names only), tools/check.py + tools/shrink.py; 30 tests, flake8 clean.

- M2 Infirmary UI: game.py, progress.py, hints.py, render.py (SVG busts and scene), info.py, index.html, app.js, style.css, settings.js, changelog.json, favicon; 62 tests incl. a pledge lint (real-medicine, death, timer words); checked live at 1440x900 and 360x740 (cure, scan, shift picker, no horizontal scroll).

- M3 Chapters 3-5 (cases_3/4/5: 24 shifts, 39 in all), cast beats + codex.py (the Record), achievements.py facts + goals strip, Record panel; 72 tests; checked live (cold room, goals, Record counts).

- M4 Chapters 6-8 (cases_6/7/8: 21 shifts, 60 in all), Tally beats, finale; every crew member has 13+ appearances; 77 tests incl. a whole-game test (all Clean, all 14 achievements, 100% Record); checked live (Tally steady, no horizontal scroll at 360).

## Next
- M5 standard kit: tutorial (steps in app.js + the opening-screen offer already works), About already has the fiction notice, keyboard help, confirm dialogs (restore and reset exist), accessibility tests (contrast, shapes), light-theme check, What's New entry.

## Open problems / notes
- Local Python is 3.9: engine code avoids 3.10+ syntax.
- Fairness is strict (every look-alike world must finish clean), so stocks are tight; use tools/shrink.py to find minimal stocks when authoring.
