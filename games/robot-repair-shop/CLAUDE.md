# Robot Repair Shop

Seed: `planning/robot-repair-shop-plan.md`. Personal project, no BCM tag, working title. Started 2026-10-13 with `scripts/new_game.py`.
Read the plan first: it holds the design every milestone follows. Then `BUILD-STATUS.md` here.

## One-line pitch
Source: the Quick ideas round (B2), owner-approved: "fix quirky robots by solving their fault puzzles; each repaired robot becomes a friend that gives you a gift later." Checked against `PLAYER-PROFILE.md`: robots, a helper and healer role, collecting one of each, quiet tragic-but-gentle characters with a robot that shows feeling, short wins into a slow arc, three goals, no timers, nothing lost, friendly welcome-back. Personal project, no BCM tag, working title. Related but distinct from Station Medic (hidden-cause deduction over patients) and Robot Script (programming): here each robot is a small wiring puzzle.

## Stack
- Pyodide Python, plain HTML/CSS, no build step. Engine modules are plain Python with no DOM (the Signal / Lexis
  pattern): `game.py` is the entry point (`handle(json) -> json`, plus `get_state()` / `load_state()` for the
  shared save widget); `app.js` is glue only.
- No audio files. Nothing timed, nothing lost, no luck needed for 100% (the site's standing rules).

## Milestones
| # | Milestone | Content | Status |
|---|-----------|---------|--------|
| 1 | Engine and checker | Wiring model, probes, parts, consistent-wiring search, shelf 1 (6 robots) with proofs | Not started |
| 2 | Bay UI | SVG patch bay, probe buttons, cable dragging and keyboard, Test Rig, save contract. Playable slice | Not started |
| 3 | Shelves 2-4 | 18 more robots, inverters and stuck wires, Friends shelf and visit queue | Not started |
| 4 | Shelves 5-6, gifts, hints, goals | 12 more robots (36), 36 gifts, hint ladder, three-goals strip. First complete game | Not started |
| 5 | Standard kit | Opening screen, tutorial, About with Sources, What's New, keyboard help, confirm dialogs, light theme, accessibility | Not started |
| 6 | Achievements | 14 achievements, panel and toast, manifest, reachability test | Not started |
| 7 | Desktop boot and wrap-up | `pc-config.json`, `pc.css`, `pc.js`, generated `pc.html`, docs, changelog | Not started |

## Working conventions
- Commit + tag per milestone: `git commit -m "Milestone N: <name>"` then `git tag robot-repair-shop-milestone-0N`.
- Update the Status column as work happens, and `BUILD-STATUS.md` after every milestone.
- Hub registration is a separate step (`games/robot-repair-shop/register.json`, then `scripts/register_game.py robot-repair-shop`).
