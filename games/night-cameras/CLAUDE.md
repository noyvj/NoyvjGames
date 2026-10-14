# Night Cameras

Seed: `planning/night-cameras-plan.md`. Personal project, no BCM tag, working title. Started 2026-10-13 with `scripts/new_game.py`.
Read the plan first: it holds the design every milestone follows. Then `BUILD-STATUS.md` here.

## One-line pitch
Source: the Quick ideas round (D3), owner-approved: "investigate odd events by switching between security cameras; no jump scares, and the answer is a deduction." Checked against `PLAYER-PROFILE.md`: loves Phasmophobia's investigate-and-learn feel and anomaly games, deduction, spatial and logic puzzles, helper role, dark moody, quiet, no timers, no jump scares, no gore, a hint ladder, easy to 100%, a bigger picture that fills in. Personal project, no BCM tag, working title. One-line pitch: a night desk with eight small monitors; something odd happened in the building and the footage, scrubbed frame by frame, tells you what, with a gentle answer every time.

## Stack
- Pyodide Python, plain HTML/CSS, no build step. Engine modules are plain Python with no DOM (the Signal / Lexis
  pattern): `game.py` is the entry point (`handle(json) -> json`, plus `get_state()` / `load_state()` for the
  shared save widget); `app.js` is glue only.
- No audio files. Nothing timed, nothing lost, no luck needed for 100% (the site's standing rules).

## Milestones
| # | Milestone | Content | Status |
|---|-----------|---------|--------|
| 1 | Engine | World graph, schedules, camera coverage, frame builder, hypothesis solver, chapter 1 (6 cases) with proofs and tests | Not started |
| 2 | Desk UI | Monitor wall, scrub bar, floor plan, notebook grid, answer and result card, save contract. Playable slice | Not started |
| 3 | Chapters 2-4, Night Book, hints | 18 more cases, Night Book, annex map, hint ladder, three-goals strip | Not started |
| 4 | Chapters 5-6 | 12 more cases (36 in all), camera-down cases, chained cases. First complete game | Not started |
| 5 | Standard kit | Opening screen, tutorial, settings, About, What's New, keyboard help, confirm dialogs, light theme, accessibility pass | Not started |
| 6 | Achievements | 14 achievements, panel and toast, manifest, reachability test | Not started |
| 7 | Desktop boot and wrap-up | `pc-config.json`, `pc.css`, `pc.js`, generated `pc.html`, docs, changelog | Not started |

## Working conventions
- Commit + tag per milestone: `git commit -m "Milestone N: <name>"` then `git tag night-cameras-milestone-0N`.
- Update the Status column as work happens, and `BUILD-STATUS.md` after every milestone.
- Hub registration is a separate step (`games/night-cameras/register.json`, then `scripts/register_game.py night-cameras`).
