# Last Line — Groundwork Plan (baseline only)

**Status:** groundwork, pre-build. Written 2026-09-21 from `IMPROVEMENT-IDEAS-ROUND-2.md` section M item 7, answered "yes, same as 6."

**Shared baseline: see `overclock-plan.md` section 4 (full checklist: save, settings, achievements, changelog, tutorial, confirm dialog, mobile dock/HUD, colorblind rules, info/About panel, test harness, feedback) and section 5 (hub integration).** Do all of that here, substituting slug `last-line`, `data-game-slug="last-line"`, `games/last-line/` in `sw.js`, `favicon-last-line.svg`. This file lists only what is genre-specific.

## 1. Pitch and genre shape
Classic tower defense: place and upgrade defenses along a winding path against escalating waves; chase a personal-best wave-survived count. Arcade-strategy fun, leaderboard-friendly, no narrative or lesson. Fun-first; no BCM tag.

## 2. Deliberately undecided (deferred to `IMPROVEMENT-IDEAS-ROUND-3.md`)
Theme/gimmick (user: "same as 6", i.e. wants a special hook), tower roster, enemy roster, damage/economy numbers, map count. Open questions:
1. What is the gimmick that differentiates it (e.g. the path can be rerouted, towers decay, a shared resource with the player's own "last line" unit)?
2. Fixed handcrafted maps, or seeded procedurally generated paths?
3. Real-time waves, or wave-by-wave turn-based (see section 3, this is the biggest technical fork)?
4. Endless mode with a best-wave leaderboard only, or also a campaign of finite levels?
5. Is a hub-wide leaderboard wanted (needs a backend table, currently no such thing beyond ratings/saves)?

## 3. Genre-specific technical foundation
- **Time model is the key constraint.** The user noted (M9) that time-based things are hard with how games load, so default to a **tick-driven simulation stepped by a fixed-step `step(dt_ticks)` in pure Python** and driven by JS `requestAnimationFrame`/`setTimeout` calling into Python at a coarse rate (e.g. 10 ticks/sec, not 60). Sim is deterministic given seed + player actions, so tests call `step()` in a loop with no timers. Provide a **Fast-forward / Pause / "Send next wave"** control from day one; a pause-only wave-by-wave mode is the fallback if real-time proves too heavy.
- **Seeded RNG and meta/run split:** same `rng.py` and `{"meta":..., "run":...}` state shape as `overclock-plan.md` section 3. `run` holds tick, wave index, placed towers, enemy list, RNG state; `meta` holds best wave and unlocks. Saving mid-wave must serialise all live entities as plain dicts (no object graphs).
- **Content as JSON:** `content/towers.json`, `enemies.json`, `waves.json`, `maps.json` (grid dims, path waypoints, buildable cells). Placeholder: one map, one tower, one enemy.
- **Rendering: DOM grid for the board, not canvas, at baseline.** A CSS grid of buttons (say 12x8 cells) keeps placement accessible, keyboard-operable, mobile-tappable and testable in the fake DOM. Enemies/projectiles are absolutely positioned `div`s updated per tick via `transform`. Reassess canvas only if entity counts exceed ~150 and profiling shows DOM cost; a `renderer` boundary (`draw(state)`) keeps that swap cheap. Never render per Python tick: batch state to JS once per animation frame.
- **Pyodide performance:** budget the sim step to a few ms at the worst-case entity count; add a `test_worst_case_perf.py` (Thaw already has the pattern) that steps a synthetic 200-enemy wave and asserts a time ceiling. Avoid per-tick allocation-heavy code; pathing is precomputed from waypoints once per map.
- **Mobile dock:** the tower build/upgrade panel is the dock content; the board must stay visible above it. HUD mirrors lives + wave + gold.
- **Colorblind rules (genre-specific):** tower types and enemy types differ by shape/icon and letter, not color; range circles use dashed vs solid outlines; health bars have numeric option.
- **Confirm dialog targets:** Sell tower, Abandon run, Reset progress.
- **Achievements launch set:** first tower, first wave cleared, wave 10/25/50 reached, first upgrade, perfect wave (no leaks), etc.

## 4. Milestones (baseline only)
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

## 5. Milestones after the gimmick is chosen (stub)
Blocked on round-3 answers. Expected: real tower/enemy rosters, wave scripting, economy balance, upgrade trees, multiple maps, the chosen gimmick, optional leaderboard backend, visual pass, Pass 2/3. Not scoped here.
