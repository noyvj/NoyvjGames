# Dead Reckoning build status (handoff file)

Updated after each milestone. A new agent should read `planning/dead-reckoning-plan.md`, `CLAUDE.md` here, then this file.

## Done
- Milestone 1 Sim core: `geom.py`, `sim.py`, `charts.py` (demo chart only), `tools/textharness.py`, tests.

- Milestone 2 Chart SVG: `render.py`, `index.html`, `style.css`, `settings.js`, `app.js` (boot + chart draw), `game.py` (demo view), favicon, golden SVG tests.
- Milestone 3 Plan and sail: `game.py`, `state.py`, `progress.py`, `solver.py`, full planner/reveal UI in `index.html`/`app.js`.

- Milestone 4 Campaign chapters 1-2: `chartkit.py`, `charts_open.py`, `charts_wind.py`, `charts.py` (registry, chapters, gates), generated `pars.py`, picker, par reveal, captain's log, `tests/test_charts.py`.
- Milestone 5 Fixes and watch-by-watch: `fixes.py`, watch logic in `game.py`/`state.py`, `charts_fixes.py` (5 charts), watch UI.

- Milestone 6 Fog, tides, compass error: `charts_fog.py`, `charts_tides.py`, `charts_compass.py` (12 charts), anchor legs, found-hazard drawing rules, validators.

## Next
- Milestone 8 Practice generator (Milestone 7 Two ships is deferred, as the user confirmed): `gen.py`, seeded charts, solvability fuzz, shareable seeds.

## Open problems
- The shared `level-select.js` is not used (own picker instead). Ask the hub session whether to adopt it at registration time.
- Dev tip: the hub service worker and HTTP cache serve stale app.js; unregister the SW and `fetch(f, {cache: "reload"})` each file before reloading in the browser pane.

## Notes for whoever continues
- Commit only this folder with a pathspec commit: `git add games/dead-reckoning && git commit -m "..." -- games/dead-reckoning`, then tag `dead-reckoning-milestone-0N`.
- Run tests with `python3 -m pytest -q games/dead-reckoning`; lint with `python3 -m flake8 --extend-ignore=E501 games/dead-reckoning`.
