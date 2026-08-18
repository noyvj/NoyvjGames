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
| 10 | Colony specialization | Worlds develop distinct strengths/weaknesses based on environment/history | Done |
| 11 | Ships on the map | Automated routes render as moving dots along the map's lines | Done |
| 12 | Fleet-level automation | Prioritization rules across many routes at once, not just per-route toggles | Done |
| 13 | Galaxy scaling | Research-gated expansion to more systems/regions | Done |
| 14 | Endgame | Fully automated economy visible at scale (hundreds of worlds, many ships); soft win-state, sandbox continues | Done — all 14 milestones complete |

## Milestone 14 implementation notes
- Scope interpretation, the biggest judgment call of this milestone: "hundreds of worlds, many ships" was read as a narrative/numeric payoff, not a literal request to simulate hundreds of individually-stateful, individually-rendered colonies. That would mean hundreds of DOM rows nobody could meaningfully interact with and a genuinely heavy render loop, for no real gameplay depth over the existing handful of well-simulated colonies — a worse experience, not a bigger one. Instead, reaching the endgame narrates the player's own automated pattern as having spread to an abstracted "background galaxy": a single growing world-count number and a matching trickle of passive revenue, explicitly flagged in-game as the "galaxy at scale" and documented here as a deliberate scope cut, the same way Milestone 8's ship-types cut and Milestone 9's automation/map cut were.
- `endgame_criteria_met()` requires the fleet's automation to be maxed out (`automated_ship_count() >= max_automated_ships()`), Fleet Priority switched on, and Galaxy Expansion unlocked. Deliberately *not* "all 4 ships automated" literally — the automation slot cap (2, or 3 with its own research node) sits below the 4-ship roster, so that literal reading would make the milestone unreachable under the systems Milestones 6–8 already built. "Fully automated" means fully using what you've unlocked.
- `endgame_reached` is a one-way sticky flag, not a live re-check of the criteria every tick — set once in `tick()` and never cleared, so a player who reaches it and then toggles Fleet Priority back off (the one reversible piece of the three criteria) doesn't lose the milestone. Confirmed by a dedicated test.
- Once reached, `ticks_since_endgame` counts up and `background_world_count()` grows at a fixed rate up to a cap (500), converting linearly to a small per-tick revenue trickle added to `total_profit` inside `tick()` — a real, if modest, mechanical reward for reaching the state, not just a cosmetic banner.
- UI follows the same hidden-until-relevant panel idiom used for the Kepler Cluster and stakeholder-style panels elsewhere on the site: a single `endgame-panel`, hidden by default, revealed by `render_endgame()`.
- Live verification surfaced a genuine gap between wall-clock wait time and the pace of automation-cost/research-cost accrual (150 credits per automated ship, 80 research points for Galaxy Expansion) — reaching the full endgame state live in a single verification pass wasn't practical within a reasonable number of tool round-trips. Verified instead via the full 180-test suite (which directly exercises `endgame_criteria_met()`, the sticky flag, background world growth and its cap, and the revenue trickle) plus a live check that the core tick/render loop remains healthy after this milestone's changes (research points climbing, ship transit countdown advancing, endgame panel correctly hidden by default) — consistent with how this same real-time-vs-tool-latency gap was handled in earlier milestones' live checks.

## Milestone 13 implementation notes
- Scope interpretation: "expansion to more systems/regions" became a second, self-contained three-good need-triangle (the Kepler Cluster) reachable only once the new "Galaxy Expansion" research node (cost 80, the priciest yet) is unlocked. It uses three brand-new goods (Rare Metals, Biomass, Isotopes) rather than reusing the home system's five — that's what keeps `colony_needing()`/`colony_producing()` single-valued across the whole galaxy without any special-casing, since good-namespaces between the two systems never overlap.
- Colony *metadata* (`EXPANSION_COLONIES`, merged into `ALL_COLONIES`) exists unconditionally from module load, same as the home system's `COLONIES` — but colony *state* (`ColonyState` instances in `colony_states`) is deliberately **not** created until the research actually unlocks it, inside `unlock_research()`. This was a real design correction, not just an implementation detail: eagerly creating Kepler's `ColonyState` from tick one would let it decay untouched forever and permanently win Milestone 12's `most_urgent_colony()` (which reads `colony_states` directly), sending Fleet Priority ships chasing a destination they can't reach. Deferring creation makes that structurally impossible rather than something to guard against with a special case — confirmed by a dedicated regression test (`test_fleet_priority_ignores_kepler_before_it_is_unlocked`) that ticks 50 times pre-unlock and asserts `most_urgent_colony()` never leaves the home system.
- New `active_colony_ids()` is the single source of truth for "what's reachable right now" (home system always, Kepler once unlocked) and is now what everything reachability-sensitive is scoped to: `route_edges()`, `render_map()`'s node/edge drawing, `Ship.other_colonies()`, and the validity checks inside `Ship.depart()`/`Ship.reposition()`. `colony_needing()`/`colony_producing()` deliberately stay scoped to the *static* `ALL_COLONIES` instead — a ship can only ever be carrying a Kepler good after it has already reached the Kepler Cluster, which itself requires the system to be unlocked, so those two lookups don't need to gate on reachability to stay correct.
- A developed Kepler colony's secondary need (Milestone 9's mechanic) reaches back into the *home* system rather than elsewhere within Kepler itself — Kepler only has one triangle, so there's no second sub-cycle to reach into internally. This is a deliberate, thematically-motivated choice: it's the mechanic that actually links the two systems together once a Kepler colony grows, giving multi-system logistics a real payoff rather than the two systems staying permanently isolated from each other.
- The map canvas widened from 300×300 to 460×300 (`CANVAS_WIDTH`/`CANVAS_HEIGHT` replacing the old single `CANVAS_SIZE`) to give the Kepler triangle its own visual space on the right, without moving any of the home system's five existing `NODE_POSITIONS` — avoids retroactively invalidating Milestone 11's ship-interpolation coordinates for any prior save state.
- UI additions follow the existing hidden-until-relevant idiom used elsewhere on the site (e.g. the climate games' stakeholder/coda panels) rather than dynamic DOM creation: a static `expansion-colonies-panel` and `expansion-market-panel` in `index.html`, toggled by `render()` based on `galaxy_expansion_unlocked()`. Depart buttons for the three Kepler colonies were added to all four ships' panels up front (12 new buttons total) and gated the same way the existing depart buttons already were, just with `colony_id in active_colony_ids()` added to the applicability check.
- Live verification hit a real caching gotcha worth noting: after editing `index.html`, `navigate` with `force: true` and even `window.location.reload()` both kept serving a stale cached copy (old title, missing new elements) against a fresh `game.py`, producing `'NoneType' object has no attribute 'innerText'` errors for ids that existed in the new HTML but not the stale cached one. A cache-busting query string (`?v=13`) on the URL resolved it immediately; opening a brand-new tab afterward confirmed zero console errors on a clean load.
- Live-verified: page loads error-free with the wider canvas, the map correctly shows only the original 5-node pentagon (no Kepler nodes/edges) while locked, and the general research-unlock code path (shared with the new node) still works correctly post-refactor by unlocking Fast Ships I live. Didn't wait out the full ~160 ticks (~160s) needed to accrue Galaxy Expansion's 80-point cost for a full live unlock click — that specific path is covered exhaustively by dedicated unit tests instead (unlock creates colony state, panel visibility flips, depart buttons appear, route edges update, cross-system secondary need resolves correctly).

## Milestone 12 implementation notes
- Scope interpretation: with the current fixed 5-colony/5-good world, every good is needed by exactly one colony (`colony_needing()` is single-valued), so a single automated ship on its own route has no destination choice to prioritize — "prioritization across routes" only becomes meaningful at the *fleet* level. Read it as: letting an idle automated ship abandon its home shuttle and reposition empty toward whichever producer feeds the fleet's most under-served colony, rather than blindly reloading its local produce every tick.
- `fleet_priority_enabled` is a module-level toggle, off by default, flipped by a new "Fleet Priority: OFF/ON" button. Off means Milestone 6's original automation behavior runs byte-for-byte unchanged — zero regression risk for every prior automation test.
- New `most_urgent_colony()` (`min` by `need_satisfaction`) and `colony_producing()` (reverse of the existing `colony_needing()`) are the only new lookups needed; `run_automation()` just checks, when an automated ship is docked and empty, whether fleet priority is on and the most urgent colony's producer differs from the ship's own location — if so it repositions there instead of loading locally.
- `Ship.depart()` was refactored to share a `_begin_transit()` helper with a new `Ship.reposition()` — reposition travels empty (no cargo required) but is only ever called from `run_automation()`'s fleet-priority branch, never from a player-facing button, so manual play still can't depart without cargo.
- `advance_transit()` needed a real fix here, not just new code: it assumed every arrival had cargo to sell/deliver, which crashed (`KeyError` on `cargo_good=None`) the moment an empty reposition trip completed. Fixed to skip the sale/delivery branch entirely when `cargo_good` is `None`, returning no sale result — caught by a test before it ever reached the browser.
- Verified live: enabled Fleet Priority, automated a ship sitting at a fully-fed colony, and watched it reposition empty to Aurum (the producer of Ferrum's ore, Ferrum having decayed to the fleet's most urgent need) then complete a full load → deliver → dock cycle on its own, confirmed via Ferrum's `cumulative_delivered` ticking up and the sale log.

## Milestone 11 implementation notes
- Every ship (not just automated ones — manual play stays useful on the map too) renders as a dot each render pass, interpolated between `NODE_POSITIONS[ship.origin]` and `NODE_POSITIONS[ship.destination]` using `ship.transit_total_ticks` — a value fixed at departure time, so Fast Ships research researched mid-flight can't retroactively distort a ship that already departed under the old travel time.
- `render_map()` moved from a one-time `setup()` call into `render()` itself, so the map redraws every tick along with everything else — ship dots actually move.
- Automated and manual ships get distinct dot colors (gold vs. white).
- Extended the M7 test harness pattern rather than replacing it: `ctx.calls` already logged every draw call, so ship-dot assertions just filter by radius (`SHIP_DOT_RADIUS` vs `NODE_RADIUS`) to tell colony circles and ship dots apart in the same log.

## Milestone 10 implementation notes
- `SPECIALIZATION` is a fixed, per-colony dict (output bonus + decay-rate multiplier) reflecting each colony's own flavor text — environmental, not a player choice. Activates automatically once `is_developed()` (Milestone 9's level-2 flag), reusing that gate rather than inventing a separate unlock/currency for it.
- Numbers deliberately vary per colony (Aurum's harsh mining outpost gets the strongest bonus and steepest decay penalty; Verdant's easy, fertile terraces get the mildest of each) rather than one bonus copy-pasted five times.
- `output_multiplier()` and `decay()` both stay byte-for-byte unchanged for undeveloped colonies — specialization layers on top of Milestone 9's averaged-needs formula rather than replacing it.

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
