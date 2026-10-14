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
| 1 | Gimmick | **The tower sits in the middle of a living hedge-maze that overgrows and dies back each wave**, creating a somewhat new route every time, instead of merely lengthening the path. | Not started |
| 2 | Fixed or seeded maps | **Seeded** (procedural, deterministic per seed). The user noted map generation will be the hardest part and left the final call to me; I confirm seeded is possible, with the risks below. | Not started |
| 3 | Real-time or turn-based | **Turn-based waves**: time to reassess the map and set defences before each wave. | Not started |
| 4 | Endless or campaign | **Both**: an endless mode with a best-wave leaderboard and a campaign of finite levels. | Not started |
| 5 | Leaderboards | **Build leaderboards generally, opt-in.** The site already has an opt-in leaderboard backend (`app/leaderboards.py`, boards registered in its `BOARDS` dict, friendly not tamper-proof, one best row per account, test accounts excluded) and a shared client (`shared/leaderboard.js`, `window.NoyvjLeaderboard.report(game, board, score, detail)`, only submits when the player is signed in and has opted in). Last Line uses them; nothing new is needed on the backend beyond registering its boards. | Not started |
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
| 1 | Skeleton + deterministic sim | Folder, `rng.py`, fixed-step `step()`, one hardcoded map, one placeholder tower and enemy walking the path. Tests: step determinism, path traversal | Not started |
| 2 | Board rendering + placement | DOM grid, place/sell a placeholder tower, tick driver with pause/fast-forward. Tests via fake DOM, no real timers | Not started |
| 3 | Run/meta state + save | Serialise live entities, shared save widget, best-wave in meta. Tests: mid-wave round-trip resumes identically | Not started |
| 4 | Settings + confirm + content JSON | `settings.js`, confirm dialog, `content/*.json` loader and validation | Not started |
| 5 | Achievements + changelog | Catalog (~8), panel/toast, changelog panel, hub `script.js` line | Not started |
| 6 | Onboarding + mobile + perf | Tutorial steps, dock/HUD, colorblind audit, worst-case perf test, feedback prompt | Not started |
| 7 | Hub integration + ship | Card, favicon, `sw.js`, root CLAUDE.md row, generated JSONs, dev logs, live check at 375px | Not started |

## Working conventions
- Commit + tag per milestone: `git commit -m "Milestone N: <name>"` then `git tag last-line-milestone-0N`.
- Update the Status column as work happens, and `BUILD-STATUS.md` after every milestone.
- Hub registration is a separate step (`games/last-line/register.json`, then `scripts/register_game.py last-line`).
