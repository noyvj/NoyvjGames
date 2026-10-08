# Dead Reckoning build status (handoff file)

Updated after each milestone. A new agent should read `planning/dead-reckoning-plan.md`, `CLAUDE.md` here, then this file.

## Done
- Milestone 1 Sim core: `geom.py`, `sim.py`, `charts.py` (demo chart only), `tools/textharness.py`, tests.

- Milestone 2 Chart SVG: `render.py`, `index.html`, `style.css`, `settings.js`, `app.js` (boot + chart draw), `game.py` (demo view), favicon, golden SVG tests.
- Milestone 3 Plan and sail: `game.py`, `state.py`, `progress.py`, `solver.py`, full planner/reveal UI in `index.html`/`app.js`.

## Next
- Milestone 4 Campaign chapters 1-2 (12 authored charts in `charts*.py`, par plans, chart validator tests, chart picker, Next chart, Show the par plan).

## Open problems
- None yet.

## Notes for whoever continues
- Commit only this folder with a pathspec commit: `git add games/dead-reckoning && git commit -m "..." -- games/dead-reckoning`, then tag `dead-reckoning-milestone-0N`.
- Run tests with `python3 -m pytest -q games/dead-reckoning`; lint with `python3 -m flake8 --extend-ignore=E501 games/dead-reckoning`.
