# Last Line — Groundwork Plan (baseline only)

**Status:** groundwork, pre-build. Written 2026-09-21 from `IMPROVEMENT-IDEAS-ROUND-2.md` section M item 7, answered "yes, same as 6."

**Shared baseline: see `overclock-plan.md` section 4 (full checklist: save, settings, achievements, changelog, tutorial, confirm dialog, mobile dock/HUD, colorblind rules, info/About panel, test harness, feedback) and section 5 (hub integration).** Do all of that here, substituting slug `last-line`, `data-game-slug="last-line"`, `games/last-line/` in `sw.js`, `favicon-last-line.svg`. This file lists only what is genre-specific.

## Decisions (2026-09-27, from Round 3 answers)
Source: `IMPROVEMENT-IDEAS-ROUND-3.md` Part 4, section T. Where these contradict text further down, this section wins; sections 2, 4 and 5 below are marked superseded and section 3 is amended.

| # | Question | Decision |
|---|----------|----------|
| 1 | Gimmick | **The tower sits in the middle of a living hedge-maze that overgrows and dies back each wave**, creating a somewhat new route every time, instead of merely lengthening the path. |
| 2 | Fixed or seeded maps | **Seeded** (procedural, deterministic per seed). The user noted map generation will be the hardest part and left the final call to me; I confirm seeded is possible, with the risks below. |
| 3 | Real-time or turn-based | **Turn-based waves**: time to reassess the map and set defences before each wave. |
| 4 | Endless or campaign | **Both**: an endless mode with a best-wave leaderboard and a campaign of finite levels. |
| 5 | Leaderboards | **Build leaderboards generally, opt-in.** The site already has an opt-in leaderboard backend (`app/leaderboards.py`, boards registered in its `BOARDS` dict, friendly not tamper-proof, one best row per account, test accounts excluded) and a shared client (`shared/leaderboard.js`, `window.NoyvjLeaderboard.report(game, board, score, detail)`, only submits when the player is signed in and has opted in). Last Line uses them; nothing new is needed on the backend beyond registering its boards. |

### Design of the living hedge-maze
- **The map.** A grid maze of **hedge** cells and **open** cells. The **tower** stands in the centre chamber. Enemies enter from **gates** on the outer edge (1 to 3 by level) and walk the shortest open route to the tower (deterministic tie-breaking). Fixed features never change: gates, the tower, and **tower pads** (stone plinths, 10 to 16 per map) embedded in the maze where defences can be built.
- **Defences do not block the path.** They are built on pads only. This is deliberate: the user's complaint is games that just lengthen the path by walling it, so the route changes only because the hedge changes. The player's decisions are which pads to fill and upgrade given the route **forecast**.
- **Growth and dieback each wave.** Between waves, hedge cells grow and die back according to a seeded schedule. The result is a new route, not just a longer one.
- **Forecast.** Because growth is a pure function of the seed and wave number, the game can show next wave's maze (and later, with a scouting upgrade, two waves ahead). The build phase always shows "budding" and "withering" markers on the cells that will change, so the player plans against a known future. Uncertainty comes from what the wave contains, not from the map.
- **Player levers, small at launch.** Build and upgrade defences on pads; sell them; and one hedge verb per level ("prune" one budding cell before it grows, costing gold and limited by shears) added as a second-wave feature once the base is fun.

### Seeded map generation (the hardest part, planned first)
Three separate pure functions, all deterministic from `seed`:
1. **`base_maze(seed, params)`**: recursive-backtracker or similar spanning-tree maze on an odd-sized grid (about 21x21), then **braided** (a seeded fraction of dead ends opened) so there are loops and therefore alternative routes; centre chamber carved; gates placed on the boundary; pads placed beside corridors, chosen so every stretch of corridor is covered by at least a target number of pads.
2. **`hedge_state(seed, wave)`**: random access, not sequential. Each hedge-able cell has its own seeded phase; `alive(cell, wave)` comes from a hashed function of (cell seed, wave) with hysteresis so cells do not flicker every wave. Being random-access means endless wave 200 is the same cost as wave 2 and saves need only `seed` and `wave`.
3. **`repair(state)`**: after computing a state, a breadth-first search checks that every gate has an open route to the tower. If not, the smallest deterministic set of cells nearest the blocked gate is forced open. Another check rejects a state whose shortest routes are identical to the previous wave's (route **novelty**), forcing a change so the maze stays "somewhat new".
- **Fairness metrics** checked at generation: route length within a min and max, coverage of pads over each route, no pad permanently useless (must be within range of the route in at least some waves).
- **Why this is the hard part, honestly.** It is a constraint problem (connectivity, novelty, coverage) with a determinism requirement and a Pyodide speed budget. Property tests over thousands of seeds are the safety net (below). Generation must stay fast because every new run and every campaign level starts with it; target a small fraction of a second for map + first forecast (not yet measured; Milestone 1 measures).
- **Campaign levels** use fixed authored seeds plus authored parameters (size, gate count, wave list, growth rate), so they are reproducible and hand-tuned; **endless** uses a fresh random seed per run, shown as a code so it can be replayed.

### Turn-based wave flow (resolves the old real-time fork)
- **Build phase:** untimed. Look at the forecast, spend gold on pads, press **Send wave**.
- **Wave phase:** the whole wave is **resolved in one pure Python call** (`resolve_wave(state) -> event_log`) using a fixed-step sim internally. The UI then **replays the event log** at a chosen speed (1x, 2x, 4x, pause, skip to end). Because rendering only replays a log, nothing in the game depends on real-time precision, the sim is exactly testable, and a paused or backgrounded tab cannot change the outcome.
- **Trade-off, stated honestly:** the player cannot act mid-wave. That is what "turn-based" means here and it is what the user asked for, but it makes the forecast and clear feedback essential, and removes the option of an emergency mid-wave ability. Between-wave decisions must carry all the depth.
- After the wave: hedge changes, income, the next forecast.

### Modes and leaderboards
- **Endless:** waves keep coming with seeded scaling; the score is the **best wave reached**. Board: `("last-line", "endless_best_wave")`, order desc, low 1, high a generous cap (register in `app/leaderboards.py` at build time; the module docstring says adding a board is one `BOARDS` entry, no schema change). Client: one `shared/leaderboard.js` include with `data-game-id="last-line" data-board="endless_best_wave" data-order="desc"`, and the game calls `NoyvjLeaderboard.report("last-line", "endless_best_wave", wave, detail)` at run end. Opt-in only; scores are client-supplied, so it is a friendly board. Because endless seeds differ per run, note on the board that waves are not perfectly comparable; a later fixed "weekly seed" board would fix that.
- **Campaign:** about 12 levels at launch, every fifth level introducing a new mechanic or mode (matches the site's standing Level Select decision, TODO-NEXT W-1). Star rating per level; optional board for total stars is not planned.
- Personal-best badge via `shared/personal-best.css`.

### Testing additions (map generation)
- 10,000-seed property tests for `base_maze`: every gate connects to the tower, pads exist and are reachable-adjacent, size and gate count match params.
- `hedge_state` for waves 1 to 200 on 1,000 seeds: always connected after repair, consecutive waves differ in shortest route at least a minimum fraction of the time, deterministic across calls and order (random access equals sequential).
- Generation time ceiling test (Thaw's perf-test pattern).
- Wave replay: `resolve_wave` twice gives the same log; the log length is bounded.
- Leaderboard: report is a no-op when signed out or opted out (client behaviour already covered by the shared script; test only the game's call sites).

### Revised milestone order (replaces the baseline table in section 4)
Generation comes first because it is the hardest and riskiest piece. Tag: `last-line-milestone-0N`. Milestones 1-5 ship a complete endless game.

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

### Still to decide (my proposals, changeable)
Tower and enemy rosters and numbers; hedge theme naming (garden estate?); whether "prune" ships at launch (proposed: no); campaign length; starting map size. None blocks Milestones 1-3.

## 1. Pitch and genre shape
Classic tower defense: place and upgrade defenses along a winding path against escalating waves; chase a personal-best wave-survived count. Arcade-strategy fun, leaderboard-friendly, no narrative or lesson. Fun-first; no BCM tag.

## 2. Deliberately undecided (SUPERSEDED 2026-09-27: questions 1-5 are answered in the Decisions section; tower/enemy rosters and numbers remain open)
Theme/gimmick (user: "same as 6", i.e. wants a special hook), tower roster, enemy roster, damage/economy numbers, map count. Open questions:
1. What is the gimmick that differentiates it (e.g. the path can be rerouted, towers decay, a shared resource with the player's own "last line" unit)?
2. Fixed handcrafted maps, or seeded procedurally generated paths?
3. Real-time waves, or wave-by-wave turn-based (see section 3, this is the biggest technical fork)?
4. Endless mode with a best-wave leaderboard only, or also a campaign of finite levels?
5. Is a hub-wide leaderboard wanted (needs a backend table, currently no such thing beyond ratings/saves)?

## 3. Genre-specific technical foundation
- **AMENDED 2026-09-27: superseded by the turn-based wave flow in the Decisions section (whole wave resolved in one call, then replayed from an event log); the fixed-step tick sim below now runs inside `resolve_wave`, not driven by a browser timer.** Original text: **Time model is the key constraint.** The user noted (M9) that time-based things are hard with how games load, so default to a **tick-driven simulation stepped by a fixed-step `step(dt_ticks)` in pure Python** and driven by JS `requestAnimationFrame`/`setTimeout` calling into Python at a coarse rate (e.g. 10 ticks/sec, not 60). Sim is deterministic given seed + player actions, so tests call `step()` in a loop with no timers. Provide a **Fast-forward / Pause / "Send next wave"** control from day one; a pause-only wave-by-wave mode is the fallback if real-time proves too heavy.
- **Seeded RNG and meta/run split:** same `rng.py` and `{"meta":..., "run":...}` state shape as `overclock-plan.md` section 3. `run` holds tick, wave index, placed towers, enemy list, RNG state; `meta` holds best wave and unlocks. Saving mid-wave must serialise all live entities as plain dicts (no object graphs).
- **Content as JSON:** `content/towers.json`, `enemies.json`, `waves.json`, `maps.json` (grid dims, path waypoints, buildable cells). Placeholder: one map, one tower, one enemy.
- **Rendering: DOM grid for the board, not canvas, at baseline.** A CSS grid of buttons (say 12x8 cells) keeps placement accessible, keyboard-operable, mobile-tappable and testable in the fake DOM. Enemies/projectiles are absolutely positioned `div`s updated per tick via `transform`. Reassess canvas only if entity counts exceed ~150 and profiling shows DOM cost; a `renderer` boundary (`draw(state)`) keeps that swap cheap. Never render per Python tick: batch state to JS once per animation frame.
- **Pyodide performance:** budget the sim step to a few ms at the worst-case entity count; add a `test_worst_case_perf.py` (Thaw already has the pattern) that steps a synthetic 200-enemy wave and asserts a time ceiling. Avoid per-tick allocation-heavy code; pathing is precomputed from waypoints once per map.
- **Mobile dock:** the tower build/upgrade panel is the dock content; the board must stay visible above it. HUD mirrors lives + wave + gold.
- **Colorblind rules (genre-specific):** tower types and enemy types differ by shape/icon and letter, not color; range circles use dashed vs solid outlines; health bars have numeric option.
- **Confirm dialog targets:** Sell tower, Abandon run, Reset progress.
- **Achievements launch set:** first tower, first wave cleared, wave 10/25/50 reached, first upgrade, perfect wave (no leaks), etc.

## 4. Milestones (baseline only; SUPERSEDED in ordering by the revised table in the Decisions section)
Tag: `last-line-milestone-0N`.

| # | Milestone | Content | Status |
|---|-----------|---------|--------|
| 1 | Skeleton + deterministic sim | Folder, `rng.py`, fixed-step `step()`, one hardcoded map, one placeholder tower and enemy walking the path. Tests: step determinism, path traversal | Not started |
| 2 | Board rendering + placement | DOM grid, place/sell a placeholder tower, tick driver with pause/fast-forward. Tests via fake DOM, no real timers | Not started |
| 3 | Run/meta state + save | Serialise live entities, shared save widget, best-wave in meta. Tests: mid-wave round-trip resumes identically | Not started |
| 4 | Settings + confirm + content JSON | `settings.js`, confirm dialog, `content/*.json` loader and validation | Not started |
| 5 | Achievements + changelog | Catalog (~8), panel/toast, changelog panel, hub `script.js` line | Not started |
| 6 | Onboarding + mobile + perf | Tutorial steps, dock/HUD, colorblind audit, worst-case perf test, feedback prompt | Not started |
| 7 | Hub integration + ship | Card, favicon, `sw.js`, root CLAUDE.md row, generated JSONs, dev logs, live check at 375px | Not started |

## 5. Milestones after the gimmick is chosen (SUPERSEDED 2026-09-27: see the revised milestone order)
Was: blocked on round-3 answers. Expected: real tower/enemy rosters, wave scripting, economy balance, upgrade trees, multiple maps, the chosen gimmick, optional leaderboard backend, visual pass, Pass 2/3. Not scoped here.
