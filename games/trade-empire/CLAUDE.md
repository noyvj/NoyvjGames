# Trade Empire (working title) — Interstellar Trade Empire

*Slug: `trade-empire`. Title still open, same as SOL was before it shipped.*

## One-line pitch
Start with one ship and one trade route between two colonies; end up watching a self-operating economic machine move goods across a galaxy of interdependent worlds.

## Concept
A large-scale logistics and economic management game. The player founds a private interstellar trading corporation in an already-settled human space economy — no survival, no conquest, just growth, optimization, and the satisfaction of increasingly complex systems running well. Colonies are never self-sufficient by design: every world specializes (agriculture, mining, manufacturing, research, energy) and depends on imports for the rest. The player's job is spotting inefficiencies and solving logistics problems — first by hand, eventually by building automation systems that scale far past what any player could manage manually.

**Lore tie to SOL (flavor only, not mechanical):** this is the trade layer that emerges after SOL's worlds are terraformed and reach a sustainable state — the specific routes that appear once planets are stable enough to need exchange rather than just development. No shared code or systems between the two games; purely narrative connective tissue.

## Stack
- Python via Pyodide, same approach as SOL and the climate games. No build step.
- The 2D map (introduced mid-project, milestone 7) will need canvas draw calls — expect slightly thicker JS-glue boilerplate than SOL for that milestone specifically, still driven by Python logic underneath.

## Core constraints
- No idle/wait-timer mechanics — consistent with the house rule across all games on the site. (The Milestone 1 transit countdown is a short, active-session tick sequence like SOL's planet travel, not an idle-timer gate.)
- No external threats (piracy, combat, disasters) — tension comes purely from economics: unmet colony needs and market saturation, nothing else.
- Colonies are workforce/output pools with light flavor text, not simulated individuals — avoid drifting into city-builder territory.
- Manual control should stay genuinely viable and comfortable for several milestones before automation becomes necessary — automation is a payoff, not an early crutch.
- Visuals arrive in stages: text-only → simple node/line map → moving ships on the map. Don't jump ahead of that order. Milestone 1 is text-only by design.

## Core tension mechanics
1. **Evolving needs** — every colony has a need-set. Meeting needs increases how much surplus it can contribute to trade. Needs then evolve/expand as the colony develops further — there is no final "solved" state per colony, just an ongoing relationship between development and demand. (Not built yet — Milestone 1's two colonies have fixed, always-on needs; this arrives at Milestone 3/9.)
2. **Market saturation** — overproducing and dumping a single good crashes its price. Diversification and route-planning matter more than just maximizing one output. (Not built yet — Milestone 1 uses a flat per-good sell price; this arrives at Milestone 4.)

## Milestones
Same granularity as SOL's milestones — one clearly separable, demonstrable stage each. Not mapped to specific calendar weeks; build and tag whenever done, respecting the site's "something visible every 2 weeks" rule.

| # | Milestone | Content | Status |
|---|-----------|---------|--------|
| 1 | Core loop | Founding-contract intro, one ship, one manual route between two fixed colonies (Aurum Station ↔ Verdant Reach), profit ticks in on arrival | Done |
| 2 | Second route | Basic route-management UI, manual assignment across 2+ routes | Done |
| 3 | Colony need system v1 | Colonies have need-sets; output scales with needs met; minor flavor text per colony | Done |
| 4 | Market economics | Prices fluctuate with supply; overproducing a good crashes its price | Done |
| 5 | Manual scaling friction | More routes/colonies added — manual management gets genuinely busy, foreshadowing automation | Done |
| 6 | Automation v1 | First automation unlock — a route can run itself, limited slots/cost | Done |
| 7 | 2D map v1 | Colonies as nodes, routes as lines — first visual leap, still no moving ships | Done |
| 8 | Research tree v1 | Framework + early nodes; gates automation tiers and new ship types | Done |
| 9 | Evolving needs v2 | Needs meaningfully change/expand as colonies develop further | Done |
| 10 | Colony specialization | Worlds develop distinct strengths/weaknesses based on environment/history | Pending |
| 11 | Ships on the map | Automated routes render as moving dots along the map's lines | Pending |
| 12 | Fleet-level automation | Prioritization rules across many routes at once, not just per-route toggles | Pending |
| 13 | Galaxy scaling | Research-gated expansion to more systems/regions | Pending |
| 14 | Endgame | Fully automated economy visible at scale (hundreds of worlds, many ships); soft win-state, sandbox continues | Pending |

## Milestone 9 implementation notes
- Sustained delivery of a colony's primary need (`cumulative_delivered` crossing `DEVELOPMENT_THRESHOLD`, 100 units) develops it to level 2. `need_satisfaction` and its formula are completely untouched for undeveloped (level 1) colonies, so every Milestone 3/4/5 test keeps passing unchanged — development is purely additive.
- Once developed, a colony also wants `SECONDARY_NEED[colony_id]` — deliberately a good from the *other* need-cycle (a triangle colony's secondary reaches into the Cryo/Helion pair and vice versa), so growth creates new cross-cluster dependencies rather than just deepening the cycle a colony already belongs to.
- `output_multiplier()` averages both needs' satisfaction once developed — juggling two needs is genuinely harder than one, not a free unlock.
- Scope cut, documented rather than silently missing: `colony_needing()` (Milestone 6's automation) and `route_edges()` (Milestone 7's map) still only know about primary needs — an automated ship or the map won't route/show secondary-need deliveries. Manual play is the only way to develop a colony or feed its secondary need in this version.

## Milestone 8 implementation notes
- `research_points` is a separate currency from `total_profit`, accruing passively at `RESEARCH_PER_TICK` (0.5/tick) — research and trade are two distinct things to manage, not one pool spent two ways.
- Flat tree, no prerequisites — `RESEARCH_NODES` is a dict of 3 independent nodes: automation-slot expansion (`max_automated_ships()` now reads a bonus), fast ships (`travel_ticks()` replaces the raw `TRAVEL_TICKS` constant in `Ship.depart()`), and a hauler-class refit (`fleet_cargo_multiplier()` scales `Ship.load()`'s cargo qty). "New ship types" is interpreted as a fleet-wide cargo boost rather than spawning a literal new ship object, since there's no ship-purchasing system yet — a deliberate scope cut, not a gap.
- Reused Aftermath's established skill-tree UI pattern (status text + hide-on-unlock button + cost) for the research rows, rather than inventing a new one.

## Milestone 7 implementation notes
- Drawn entirely from Python via Pyodide's `js` module — `document.getElementById("map-canvas").getContext("2d")` returns a real JS canvas context, and its methods (arc, moveTo, lineTo, stroke, fillText, ...) are just ordinary method calls from Python. No separate JS glue file needed, despite the CLAUDE.md's original anticipation that canvas would require one.
- `route_edges()` reuses `colony_needing()` from Milestone 6's automation to produce one directed edge per colony — the visual is literally "what colony_needing() already knows," not new routing data.
- Static layout (`NODE_POSITIONS`, a hand-placed pentagon) and static edges — nothing moves yet; that's Milestone 11. Drawn once in `setup()`, not per-tick.
- Test harness gained a `FakeCanvasContext` (records draw calls instead of rendering) and `FakeElement.getContext()`, extending the existing fake-DOM pattern rather than adding a separate canvas-testing approach.

## Milestone 6 implementation notes
- Up to `MAX_AUTOMATED_SHIPS` (2 of 4) can be automated for a flat one-time `AUTOMATION_COST` (150), deducted from `total_profit` — the only wallet in this game.
- `colony_needing(good)` returns the one colony whose need matches a good — every good in this world's fixed cycles is needed by exactly one colony, so autopilot always has an unambiguous destination once loaded.
- `run_automation()` runs once per tick, after transit resolution: any automated, docked ship loads if empty or departs if loaded. Because it runs after that tick's `advance_transit()` calls, a ship that arrives this tick can reload the same tick — automation is snappier than the manual click-by-click loop.
- Manual Load/Depart controls hide once a ship is automated; there's no de-automate toggle in v1 (a deliberate scope cut — the unlock is a one-time purchase, not a pausable mode).
- Added an "Automate" button per ship and an "Automation slots: N/2 used" line in the ledger.

## Milestone 5 implementation notes
- No new mechanic — added a second colony pair (Cryo Vault produces Water/needs Energy, Helion Array produces Energy/needs Water — each needing exactly the other) and two more ships (3 at Ferrum, 4 at Cryo), purely for scale.
- Every existing system (need satisfaction, market prices, `other_colonies()`) already generalized to the larger roster with zero logic changes — only data (COLONIES, COLONY_FLAVOR, SELL_PRICE, market_multiplier, ships) grew.
- Any ship can reach any of the 5 colonies, not just its "own" pair — 4 ships x 5 colonies is a genuinely bigger manual-management surface than Milestone 2's 2x3, which is the entire point: this is what makes Milestone 6's automation worth having.

## Milestone 4 implementation notes
- Each good has a `market_multiplier` (starts 1.0) that drops 0.01 per unit sold and recovers 0.01/tick toward baseline, floored at 0.3. Sale profit reads `current_sell_price(good) = SELL_PRICE[good] * market_multiplier[good]`, replacing the flat price used since Milestone 1.
- Recovery runs continuously (once per real-time tick, ~1s), so prices bounce back reasonably fast if left alone — repeated back-to-back sales of the same good are what actually crashes it, not a single sale.
- Added a Market Prices panel (price/unit, % of baseline, meter bar per good) above the Colonies panel; prices below 70% of baseline get a red "crashed" style.

## Milestone 3 implementation notes
- Each colony now has a `ColonyState` (need_satisfaction 0..1, starts at 0.5) tracked separately from the static `COLONIES` metadata dict. Decays 0.01/tick; delivering N units of a colony's needed good raises it by N*0.05, capped at 1.0.
- Output scales with it: `cargo_capacity() = round(CARGO_CAPACITY * (0.5 + need_satisfaction))`, ranging 0.5x-1.5x. The starting 0.5 satisfaction maps to exactly 1.0x, so Milestone 1/2 balance is unchanged at the neutral point.
- `Ship.load()` reads cargo qty from the docked colony's current output; `Ship.advance_transit()` delivers to the destination's need only if the cargo good matches what that colony needs (wrong-good deliveries don't help).
- Added a Colonies panel (name, flavor text, need%, output multiplier, meter bar) above the ship panels.
- "Needs" still doesn't affect sell price (that's Milestone 4's market economics) — this milestone is purely about the need/output feedback loop.

## Milestone 2 implementation notes
- Added a third colony, Ferrum Forge (produces Machinery, needs Ore), turning the fixed Aurum<->Verdant pair into a genuine triangle: Ore feeds Ferrum, Machinery feeds Verdant, Grain feeds Aurum.
- Added a second ship. `Ship.depart()` now takes an explicit destination argument instead of auto-toggling to "the other colony" — the player picks from whichever colonies a ship isn't currently docked at, via one Depart-to-X button per option.
- Both ships tick, load, and depart fully independently; `total_profit`/`sale_log` stay shared/fleet-wide.
- "Needs" is still flavor only — Milestone 3 is what makes it mechanically matter (output scaling with needs met).

## Milestone 1 implementation notes
- Two fixed colonies: Aurum Station (produces Ore, needs Grain) and Verdant Reach (produces Grain, needs Ore). Ship starts docked at Aurum Station, empty.
- Loop: Load Cargo (fills to a fixed capacity with whatever the docked colony produces) → Depart (starts a 5-tick transit to the other colony) → on arrival, cargo auto-sells at a flat per-good price and the total profit ticks up.
- Fully manual — no automation, no persistent need-tracking, no market fluctuation. Those are explicitly later milestones (3, 4, 6), not missing pieces of this one.
- No hub link or ad-bar/PWA wiring yet — per the other games' pattern, hub integration is a late milestone (visual pass), not part of the core-loop milestone.
- 13 tests (`tests/test_core_loop.py`), fake-DOM/Pyodide harness copied from Canopy's pattern (`tests/fakes.py`, `tests/conftest.py`).

## Working conventions
- Commit + tag per milestone: `git commit -m "Milestone N: <name>"` then `git tag trade-empire-milestone-0N`.
- Update the Status column as work happens.
