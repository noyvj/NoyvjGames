# Dead Reckoning build status (handoff file)

Updated after each milestone. A new agent should read `planning/dead-reckoning-plan.md`, `CLAUDE.md` here, then this file.

## Done
- Milestone 1 Sim core: `geom.py`, `sim.py`, `charts.py` (demo chart only), `tools/textharness.py`, tests.

## Next
- Milestone 2 Chart SVG (`render.py`).

## Open problems
- None yet.

## Notes for whoever continues
- Commit only this folder with a pathspec commit: `git add games/dead-reckoning && git commit -m "..." -- games/dead-reckoning`, then tag `dead-reckoning-milestone-0N`.
- Run tests with `python3 -m pytest -q games/dead-reckoning`; lint with `python3 -m flake8 --extend-ignore=E501 games/dead-reckoning`.
