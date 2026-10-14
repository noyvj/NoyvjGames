# Deep Descent

Seed: `planning/deep-descent-plan.md`. Personal project, no BCM tag, working title. Started 2026-10-13 with `scripts/new_game.py`.
Read the plan first: it holds the design every milestone follows. Then `BUILD-STATUS.md` here.

## One-line pitch
Roguelite dungeon-crawler: procedurally generated floors, permadeath runs, loot and ability pickups that change each attempt's build. Exploration-and-combat fun; replayability comes from randomization alone. Fun-first; no BCM tag. Turn-based on a tile grid is the assumed shape (consistent with the user's note that real-time is a poor fit for how games load), but movement/combat rules are undecided.

## Stack
- Pyodide Python, plain HTML/CSS, no build step. Engine modules are plain Python with no DOM (the Signal / Lexis
  pattern): `game.py` is the entry point (`handle(json) -> json`, plus `get_state()` / `load_state()` for the
  shared save widget); `app.js` is glue only.
- No audio files. Nothing timed, nothing lost, no luck needed for 100% (the site's standing rules).

## Milestones
| # | Milestone | Content | Status |
|---|-----------|---------|--------|
| 1 | Skeleton + seeded floor generator | Folder, `rng.py`, `generate_floor`, DOM text-grid render, player walks to stairs. Tests: same seed -> identical floor, connectivity of stairs | Not started |
| 2 | Turn loop + placeholder actor | `dispatch`, event list, one placeholder wandering actor, death ends the run. Tests: turn ordering, permadeath | Not started |
| 3 | Run/meta state + save | Seed plus deltas serialisation, shared save widget. Tests: mid-floor round-trip regenerates the identical floor | Not started |
| 4 | Settings + confirm + content JSON | `settings.js` (incl. high-contrast tiles), confirm dialog, content loader and validation | Not started |
| 5 | Achievements + changelog | Catalog (~8), panel/toast, changelog panel, hub `script.js` line | Not started |
| 6 | Onboarding + mobile + perf | Tutorial steps, D-pad dock/HUD, colorblind audit, generation perf test, feedback prompt | Not started |
| 7 | Hub integration + ship | Card, favicon, `sw.js`, root CLAUDE.md row, generated JSONs, dev logs, live check at 375px | Not started |

## Working conventions
- Commit + tag per milestone: `git commit -m "Milestone N: <name>"` then `git tag deep-descent-milestone-0N`.
- Update the Status column as work happens, and `BUILD-STATUS.md` after every milestone.
- Hub registration is a separate step (`games/deep-descent/register.json`, then `scripts/register_game.py deep-descent`).
