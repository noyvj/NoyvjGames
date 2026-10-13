# Circuit Playground

Seed: `planning/circuit-playground-plan.md`. Personal project, no BCM tag, working title. Started 2026-10-13 with `scripts/new_game.py`.
Read the plan first: it holds the design every milestone follows. Then `BUILD-STATUS.md` here.

## One-line pitch
Source: the Quick ideas round (G6), owner-approved: "a free sandbox for building circuits with live voltage readouts." Checked against `PLAYER-PROFILE.md`: electronics and physics named as interests, computers and science fiction, collecting every part, sandbox plus optional goals, three goals visible, easy to 100%, effects toggleable, "more game than teaching", no timers, nothing lost. Personal project, no BCM tag, working title. One-line pitch: a quiet workbench where you drop batteries, resistors, lamps and switches on a board, wire them up and read the volts and amps on every part, with small optional workbench jobs to give it direction.

## Stack
- Pyodide Python, plain HTML/CSS, no build step. Engine modules are plain Python with no DOM (the Signal / Lexis
  pattern): `game.py` is the entry point (`handle(json) -> json`, plus `get_state()` / `load_state()` for the
  shared save widget); `app.js` is glue only.
- No audio files. Nothing timed, nothing lost, no luck needed for 100% (the site's standing rules).

## Milestones
| # | Milestone | Content | Status |
|---|-----------|---------|--------|
| 1 | Engine | Parts, nets, nodal solver, diode and capacitor steps, Kirchhoff property tests, reference circuits | Not started |
| 2 | Bench UI | SVG board, part drawer, wire drawing, live readouts, undo and clear, save contract. Playable slice (the sandbox) | Not started |
| 3 | Jobs and Discoveries | 30 Workbench jobs, 20 Discoveries, Workshop Wall, hint ladder, three-goals strip | Not started |
| 4 | Parts and polish | Remaining parts (potentiometer, push button, capacitor Step), warnings, Parts Drawer. First complete game | Not started |
| 5 | Standard kit | Opening screen, tutorial, settings, About with live-read sources, What's New, keyboard help, light theme, accessibility pass | Not started |
| 6 | Achievements | 14 achievements, panel and toast, manifest, reachability test | Not started |
| 7 | Desktop boot and wrap-up | `pc-config.json`, `pc.css`, `pc.js`, generated `pc.html`, docs, changelog | Not started |

## Working conventions
- Commit + tag per milestone: `git commit -m "Milestone N: <name>"` then `git tag circuit-playground-milestone-0N`.
- Update the Status column as work happens, and `BUILD-STATUS.md` after every milestone.
- Hub registration is a separate step (`games/circuit-playground/register.json`, then `scripts/register_game.py circuit-playground`).
