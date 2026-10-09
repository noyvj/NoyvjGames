# Logic Gates build status (handoff file)

Updated after each milestone. A new agent should read `planning/logic-gates-plan.md`, `CLAUDE.md` here, then this file.

## Done
- Milestone 1 Engine and level data: `chips.py`, `net.py`, `sim.py`, `levels*.py`, `check.py`; all 40 reference solutions verified; 150-ish tests.

- Milestone 2 Board UI: `game.py`, `state.py`, `render.py`, `words.py`, `achievements.py`, `info.py`, `index.html`, `style.css`, `settings.js`, `app.js`, favicon; checked live at 1440x900 and 360x740.

## Next
- Milestone 3: hint ladder and sandbox are already in the engine; verify in the browser, add sequence-level UI checks, more tests.

## Open problems
- None yet.

## Notes for whoever continues
- Commit only these paths: `git add games/logic-gates planning/logic-gates-plan.md && git commit -m "Logic Gates milestone N: <name>" -- games/logic-gates planning/logic-gates-plan.md`, then tag `logic-gates-milestone-0N`. Never push.
- Tests: `python3 -m pytest -q games/logic-gates`; lint: `python3 -m flake8 --extend-ignore=E501 games/logic-gates`.
