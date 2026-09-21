# Deep Descent — Groundwork Plan (baseline only)

**Status:** groundwork, pre-build. Written 2026-09-21 from `IMPROVEMENT-IDEAS-ROUND-2.md` section M item 10, answered "yes, same as 6."

**Shared baseline: see `overclock-plan.md` section 4 (full checklist) and section 5 (hub integration).** Apply it with slug `deep-descent`. This file lists only what is genre-specific.

## 1. Pitch and genre shape
Roguelite dungeon-crawler: procedurally generated floors, permadeath runs, loot and ability pickups that change each attempt's build. Exploration-and-combat fun; replayability comes from randomization alone. Fun-first; no BCM tag. Turn-based on a tile grid is the assumed shape (consistent with the user's note that real-time is a poor fit for how games load), but movement/combat rules are undecided.

## 2. Deliberately undecided (deferred to `IMPROVEMENT-IDEAS-ROUND-3.md`)
Theme/gimmick, combat rules, loot system, class/character choice. Open questions:
1. What is the hook (e.g. light/darkness, a rising hazard chasing you down, floors that remember your previous runs)?
2. Grid-step turn-based (roguelike classic), or room-to-room node navigation (closer to Overclock's map)?
3. How much meta-progression: pure permadeath, or a hub between runs that unlocks classes/items?
4. Fog of war and line-of-sight: yes or no (affects generation and rendering cost)?
5. Overlap check with Overclock: both are permadeath runs with loot, so how do these two feel distinct on the same hub?

## 3. Genre-specific technical foundation
- **Seeded floor generation (`rng.py` + `dungeon.py`):** `generate_floor(seed, depth)` is a pure function returning a plain dict (tile grid as list of strings, rooms, spawn points, stairs) so the same `run_seed + depth` always recreates the same floor. RNG state model as in `overclock-plan.md` section 3. Baseline generator is intentionally simple (rooms-and-corridors on a fixed ~40x24 grid); the algorithm can be swapped later without touching saves because saves store the seed and the mutable deltas (visited tiles, defeated actors, picked-up items), not necessarily the full grid.
- **Run/meta split:** `{"meta": {...}, "run": null | {"seed", "depth", "turn", "player", "floor_deltas", "rng"}}`, same rules as Overclock (permadeath folds into meta, achievements written not read back).
- **Turn loop skeleton:** `dispatch({"type": "move", "dir": ...})` returns an event list; after the player acts, every actor gets one turn in a stable order, then events go to log/achievements. Placeholder loop: walk to stairs, descend, die on depth N or by placeholder "step counter."
- **Content as JSON:** `content/actors.json`, `items.json`, `tiles.json`, `floor_params.json` (rooms per depth, density). Placeholders only.
- **Rendering: DOM, monospaced text-grid, not canvas.** Each tile is a `<span>` in a `<pre>`-like grid with glyph plus CSS class (roguelike ASCII look). Reasons: trivially testable in the fake DOM, accessible via an `aria-live` message log, cheap on mobile, and fits a "Python only, no build" ethos. Redraw by row diff. Canvas is a later option if a tile-art style is chosen, behind a `draw(state)` boundary.
- **Pyodide performance:** turn-based, so cost is floor generation and FOV. Target under ~50 ms for generation at 40x24; add a `test_worst_case_perf.py` for generation plus one full actor turn on a crowded floor. Precompute FOV lazily only if fog of war is chosen.
- **Input:** keyboard (arrows/WASD/vi keys) plus an on-screen D-pad through `shared/mobile-dock.js` on narrow screens; HUD mirrors HP/depth.
- **Colorblind rules (genre-specific):** actors and items distinguished by glyph and label, not tint; hazards have a distinct glyph plus pattern; a high-contrast tile mode is part of settings.
- **Confirm dialog targets:** Descend with unspent pickups (optional), Abandon run, Reset progress.
- **Achievements launch set:** first floor, depth 5/10/20, first item picked up, first win/death, N runs.

## 4. Milestones (baseline only)
Tag: `deep-descent-milestone-0N`.

| # | Milestone | Content | Status |
|---|-----------|---------|--------|
| 1 | Skeleton + seeded floor generator | Folder, `rng.py`, `generate_floor`, DOM text-grid render, player walks to stairs. Tests: same seed -> identical floor, connectivity of stairs | Not started |
| 2 | Turn loop + placeholder actor | `dispatch`, event list, one placeholder wandering actor, death ends the run. Tests: turn ordering, permadeath | Not started |
| 3 | Run/meta state + save | Seed plus deltas serialisation, shared save widget. Tests: mid-floor round-trip regenerates the identical floor | Not started |
| 4 | Settings + confirm + content JSON | `settings.js` (incl. high-contrast tiles), confirm dialog, content loader and validation | Not started |
| 5 | Achievements + changelog | Catalog (~8), panel/toast, changelog panel, hub `script.js` line | Not started |
| 6 | Onboarding + mobile + perf | Tutorial steps, D-pad dock/HUD, colorblind audit, generation perf test, feedback prompt | Not started |
| 7 | Hub integration + ship | Card, favicon, `sw.js`, root CLAUDE.md row, generated JSONs, dev logs, live check at 375px | Not started |

## 5. Milestones after the gimmick is chosen (stub)
Blocked on round-3 answers. Expected: real combat and loot systems, floor variety and biomes, class/build options, meta-progression, balance pass, visual pass, Pass 2/3. Not scoped here.
