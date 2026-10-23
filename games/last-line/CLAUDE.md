# Last Line

Seed: `planning/last-line-plan.md`. Personal project, no BCM tag, working title. Started 2026-10-13 with `scripts/new_game.py`.
Read the plan first: it holds the design every milestone follows. Then `BUILD-STATUS.md` here.

## One-line pitch
Classic tower defense: place and upgrade defenses along a winding path against escalating waves; chase a personal-best wave-survived count. Arcade-strategy fun, leaderboard-friendly, no narrative or lesson. Fun-first; no BCM tag.

## Stack
- Pyodide Python, plain HTML/CSS, no build step. Engine modules are plain Python with no DOM (the Signal / Lexis
  pattern): `game.py` is the entry point (`handle(json) -> json`, plus `get_state()` / `load_state()` for the
  shared save widget); `app.js` is glue only.
- No audio files. Nothing timed, nothing lost, no luck needed for 100% (the site's standing rules).

## Milestones
| # | Milestone | Content | Status |
|---|-----------|---------|--------|
| 1 | Seeded maze generator | `base_maze`, connectivity, braiding, pads, gates, property tests, timing report. Text/ASCII print of a map | Not started |
| 2 | Living hedge + forecast | `hedge_state`, `repair`, novelty check, forecast markers, tests over 1,000 seeds x 200 waves | Not started |
| 3 | Wave resolver | `resolve_wave` (fixed-step sim inside), one placeholder tower and enemy, event log. Tests: determinism, bounded log | Not started |
| 4 | Board UI + replay | DOM grid, pads, build/sell, forecast display, Send wave, log replay with 1x/2x/4x/pause/skip | Not started |
| 5 | Endless run + save | Rosters (3 towers, 4 enemies), economy, lives, endless scaling, `{meta, run}` save with seed + wave, shared save widget. **First complete, playable game** | Not started |
| 6 | Settings + confirm + content JSON | As baseline milestone 4 | Not started |
| 7 | Campaign | Level list with authored seeds and parameters, stars, level select, mechanics introduced every fifth level | Not started |
| 8 | Leaderboard | Register the board in `app/leaderboards.py`, `shared/leaderboard.js` include, run-end report, opt-in copy | Not started |
| 9 | Achievements + changelog | As baseline milestone 5 | Not started |
| 10 | Onboarding + mobile + perf | As baseline milestone 6; the tutorial must teach the forecast markers | Not started |
| 11 | Hub integration + ship | As baseline milestone 7 | Not started |
| 12 | Pass 2 | Prune verb, more towers and enemies, scouting upgrade, second growth style, optional weekly seed board, visual pass | Not started |

## Working conventions
- Commit + tag per milestone: `git commit -m "Milestone N: <name>"` then `git tag last-line-milestone-0N`.
- Update the Status column as work happens, and `BUILD-STATUS.md` after every milestone.
- Hub registration is a separate step (`games/last-line/register.json`, then `scripts/register_game.py last-line`).
