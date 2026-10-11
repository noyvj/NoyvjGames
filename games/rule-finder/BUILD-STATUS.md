# Rule Finder build status (handoff file)

Updated after every milestone. Read `planning/rule-finder-plan.md`, `CLAUDE.md` here, then this file. Hub registration (QI-5-R) is NOT part of this build.

## Done
- M1 Rule language and prover: `lang.py` (three domains, clause libraries, rules, tables, words), `tools/finder.py` (competitors, par-set finder, re-check), `tools/author.py` + `tools/build_cases.py` + `tools/specs.py`, `cases.py` + `cases_numbers.py` (drawer 1, 8 cases, all proved).

- M2 Sorter UI: `game.py`, `progress.py`, `index.html`, `app.js`, `style.css`, `settings.js`, `changelog.json`, favicon; item builders for numbers, shape strings and patterns (the last two exist in the page but no case uses them yet), gate animation, Rule Builder, near-miss counter-example, save contract; checked live at 1440x900 and 360x740 in dark and light.

- M3 Drawers 2-4: `cases_shapes.py`, `cases_two.py`, `cases_not.py` (24 cases, all proved), `codex.py`, `render.py` (wall map), codex panel and wall map in the page; 208 tests; checked live (map, codex, shape builder) at 1440x900 and 360x740.

- M4 Drawers 5-6 (patterns, odd gate: 16 more cases, 48 in all, all proved), `hints.py`, `achievements.py` (table + goals), hint ladder and goals strip in the page; 280 tests; checked live at 1440x900 and 360x740.

- M5 Standard kit: opening screen, tutorial, About (`info.py`), `sources.json`, keyboard help and builder keys, story toggle; 285 tests; checked live (opening screen, tutorial walk-through, About, shortcuts list) at 1440x900 dark and 360x740 light.

- M6 Achievements: manifest, panel, toast, share button, perfect-player reachability test; 294 tests; checked live (toast, panel) at 1440x900.

- M7 Desktop boot: `pc-config.json`, `pc.css`, `pc.js`, generated `pc.html`, `layout-pref.js`, desktop tests; shared `-k rule` tests and the generator check pass; 300 tests; checked live at 1440x900 (stage, side tally, Drawers window) and 360x740.

## Next
- Nothing in this folder. Hub registration (QI-5-R) is the hub session's job.

## Open problems / notes
- Local Python is 3.9: engine code avoids 3.10+ syntax.
