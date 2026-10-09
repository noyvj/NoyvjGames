# Logic Gates build status (handoff file)

Updated after each milestone. A new agent should read `planning/logic-gates-plan.md`, `CLAUDE.md` here, then this file.

## Done
- Milestone 1 Engine and level data: `chips.py`, `net.py`, `sim.py`, `levels*.py`, `check.py`; all 40 reference solutions verified; 150-ish tests.

- Milestone 2 Board UI: `game.py`, `state.py`, `render.py`, `words.py`, `achievements.py`, `info.py`, `index.html`, `style.css`, `settings.js`, `app.js`, favicon; checked live at 1440x900 and 360x740.

- Milestone 3 Chapters 2-3, hints, sandbox: levels 9-24, hint ladder (nudge/hint/answer + place answer), sandbox with truth-table log and The Sixteen; checked live; `tests/test_content.py`.

- Milestone 4 Chapters 4-5: levels 25-40 (adders, register, ALU, program counter, ROM, CPU core, second program, finale); play-through tests (own solutions and hint-ladder-only both reach 40/40); restore after leaving a level.

- Milestone 5 Standard kit: settings, tutorial, About (6 live-read sources dated 2026-10-09), changelog, shortcuts, accessibility tests (contrast, non-colour cues, labels), light theme checked live, compiled-circuit cache, built chips folded into a details list.

- Milestone 6 Achievements: `achievements.json` (14, generated from `achievements.py`), tests for manifest sync, goals, and an ordinary game that earns all 14.

## Next
- Milestone 7: Desktop boot (`pc-config.json`, `pc.css`, `pc.js`, generated `pc.html` via importlib `build()` only).

## Open problems
- None yet.

## Notes for whoever continues
- Commit only these paths: `git add games/logic-gates planning/logic-gates-plan.md && git commit -m "Logic Gates milestone N: <name>" -- games/logic-gates planning/logic-gates-plan.md`, then tag `logic-gates-milestone-0N`. Never push.
- Tests: `python3 -m pytest -q games/logic-gates`; lint: `python3 -m flake8 --extend-ignore=E501 games/logic-gates`.
