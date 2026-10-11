# Rule Finder build status (handoff file)

Updated after every milestone. Read `planning/rule-finder-plan.md`, `CLAUDE.md` here, then this file. Hub registration (QI-5-R) is NOT part of this build.

## Done
- M1 Rule language and prover: `lang.py` (three domains, clause libraries, rules, tables, words), `tools/finder.py` (competitors, par-set finder, re-check), `tools/author.py` + `tools/build_cases.py` + `tools/specs.py`, `cases.py` + `cases_numbers.py` (drawer 1, 8 cases, all proved).

- M2 Sorter UI: `game.py`, `progress.py`, `index.html`, `app.js`, `style.css`, `settings.js`, `changelog.json`, favicon; item builders for numbers, shape strings and patterns (the last two exist in the page but no case uses them yet), gate animation, Rule Builder, near-miss counter-example, save contract; checked live at 1440x900 and 360x740 in dark and light.

## Next
- M3 Drawers 2-4 (24 cases), Rule Codex.

## Open problems / notes
- Local Python is 3.9: engine code avoids 3.10+ syntax.
