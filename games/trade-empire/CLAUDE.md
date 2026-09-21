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

## Visual pass: space theme (site-wide overhaul)
Brought this game onto the site's shared space-themed visual language (already shipped on the hub and SOL) — a decorative-only pass, no gameplay/logic changes:
- Added `../../shared/space-bg.css` + the `<div class="space-bg">…</div>` starfield/nebula markup right after `<body>` in `index.html`, matching SOL's exact pattern.
- Every `.section` (Research, Trade Routes/map, Market Prices, Colonies, each of the 4 ship panels, Fleet Priority, Ledger, and the hidden Endgame panel) now gets the glass-panel treatment — translucent gradient fill, `backdrop-filter: blur(14px)`, violet-tinted border, soft drop shadow — instead of a flat solid `#14161f` box, so the starfield reads through around/behind each panel rather than one giant card swallowing it.
- `<h1>` got the same gradient-glow text treatment as the hub/SOL (`background-clip: text` gradient + soft `text-shadow`); sub-headings (`.panel-label`, `.colony-name`, `.ship-label`, etc.) were deliberately left as plain text for hierarchy, per the design brief.
- All `button.secondary` variants (base blue-gray, research teal, depart green, automate purple) went from flat solid backgrounds to two-stop gradients of the same hue with a glossy inset top highlight, plus a `hover { filter: brightness(1.1) }` state; existing `:disabled` and `:active` (this game's press-feedback state — there's no `.pressed` class here, just `:active:not(:disabled)`) rules were re-skinned with darker gradients, not removed.
- `.meter`/`.meter-fill` kept their exact fill colors (including the crashed-market red and the green need-bars) but gained an inset track shadow and a matching-hue glow (`box-shadow`) on the fill — width/fill logic in `game.py` untouched.
- Flat gray borders (`.map-canvas`, `.section`) switched to the shared `rgba(140, 160, 255, 0.12–0.18)` violet tint.
- **Deliberately left alone:** the canvas-drawn map colors (`NODE_COLOR`, `EDGE_COLOR`, `LABEL_COLOR`, `AUTOMATED_SHIP_COLOR`/`MANUAL_SHIP_COLOR` in `game.py`) and `.market-price--crashed`'s red — these encode real game state (which ship is automated, which market crashed) rather than being decorative chrome, so only their surrounding panel/canvas backdrop changed, never the hues themselves. `#endgame-panel`'s green border was kept the same hue, just softened to a translucent tint to match the glass style. No CSS class/id was renamed — `game.py`'s DOM lookups are all still exact matches.
- No selector renamed, no test changed. Full suite (181 tests) verified green before and after. Live-verified via a local static server: starfield/nebula render, all panels show the glass treatment, gradient title renders, and the core loop (Load Cargo → Depart → in-transit countdown) was exercised end-to-end with zero console errors.

## Post-Milestone-14 audit fixes
- **Map label collision bug (found and fixed):** `render_map()` labeled every node with `name.split()[0]`, which is unique for the home system (Aurum/Verdant/Ferrum/Cryo/Helion) but not for the Kepler Cluster — "Kepler Alpha", "Kepler Beta", and "Kepler Gamma" all share the literal first word "Kepler", so all three map nodes rendered the identical label once Galaxy Expansion was unlocked, despite sitting at three distinct positions. Fixed with a small `MAP_LABEL_OVERRIDE` dict + `colony_map_label()` helper that gives the three Kepler nodes explicit short labels ("Kep. Alpha"/"Kep. Beta"/"Kep. Gamma") while leaving the home system's existing labels untouched. Caught by a new regression test (`test_kepler_map_labels_are_distinct_once_unlocked` in `tests/test_galaxy_scaling.py`) written first to confirm the collision, then fixed.
- **Hub-link path bug (found and fixed):** `index.html`'s favicon (`/icons/icon-192.png`) and back-link (`href="/"`) used absolute root-relative paths, which 404 under GitHub Pages' `/NoyvjGames/` subpath — every other game on the site uses `../../icons/icon-192.png` and `../../index.html` instead. This game isn't hub-linked yet so no ordinary player traffic was hitting it, but fixed for correctness/consistency ahead of the eventual hub link.

## Mobile needs-strip (implemented)
Follow-up audit (per Canopy's `shared/mobile-dock.js` fix) checking whether this — the largest, most panel-heavy game on the hub — had the same "select something, scroll away to act on it" mobile problem. Measured at a 375px viewport: `#colonies-panel` (the panel showing which colony needs what, the exact fact needed to pick the right `Depart to ...` button) sits 1000-1900px above the four ship panels, more than two screens of scrolling apart with no way to see both at once.

Docking the full `#colonies-panel` wasn't practical — it's over 1000px tall itself (flavor text + dev-level readout per colony) and would swallow most of a phone screen. Instead added a new, much smaller `#mobile-needs-strip` section (in `index.html`, between `#colonies-panel` and `#ship-1-panel`): one horizontally-scrollable chip per colony, e.g. "Aurum: needs Grain 46%", populated by a small new `render_needs_strip()` in `game.py` (called from `render()`, reuses the existing `colony_map_label()` short-name helper from the map-label fix above). `shared/mobile-dock.js` (used as-is, not modified) reparents this strip to a fixed bar pinned `bottom: 50px` below the 640px breakpoint — matching Canopy's convention, sitting above where this game's ad-bar will land once it's hub-linked. Above the breakpoint it behaves like any other `.section`, in normal document flow, no different from before this change. `tests/conftest.py`'s `ELEMENT_IDS` gained one id per colony (`mobile-needs-strip-<id>`) so the fake-DOM harness can resolve the new lookups — a data-only addition, no new test functions, suite held at 181/181.

Live-verified at 375×812: loaded Ship 1 with Ore at Aurum, confirmed the strip (staying pinned through a full scroll down past Ship 3) read "Ferrum: needs Ore" without leaving the ship panel, clicked "Depart to Ferrum Forge," watched the ship correctly enter transit — the pick-a-destination loop now fits on one screen. Confirmed un-docking at a genuine 1280px width (not just a cleared/narrow emulated viewport): `position` back to `static`, panel back between `#colonies-panel` and `#ship-1-panel` in normal flow.

## Achievements (implemented)

19 achievements added per the hub-wide framework (`planning/ACHIEVEMENTS-SYSTEM-DESIGN.md`), following SOL's reference integration: `achievements.json` catalog, `game.py`'s checkers/`achievement_ids_earned()`/panel-render logic, an in-game toggle + panel, an unlock toast, and `achievements_earned` riding `get_state()` (never read back on load). Spans first sale/automation, fleet management (Fleet Priority on, a repositioning event), research unlocks, colony development (home system + Kepler Cluster), profit milestones, market recovery, and the full-scale endgame. Also finished off `index.html`/`style.css` wiring (toggle button, panel, toast markup/styles, the `achievements.json` fetch into `window.ACHIEVEMENTS_JSON`) and `tests/conftest.py`/`tests/fakes.py` gaps (missing element ids, a `FakeProxy` with no `.destroy()`) left over from a prior session's partial pass, plus 34 new tests in `tests/test_achievements.py` driving every achievement through real game systems. Full suite: 225/225 (191 existing + 34 new) at the time it landed.

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

## Colorblind-safety audit (implemented as J18, confirmed here)

Audited as part of the site-wide colorblind-safety audit (`planning/TODO.md`, Okabe-Ito-palette method per Continuum's Phase 5, redundant-cue method per Canopy's B9, audit-only method per Tide/Aftermath/Herd/Thaw/Loop's own precedent). Per the task's own starting point, checked `render_map()`'s automated-vs-manual ship-dot differentiation (J18) first.

- **J18, automated (`AUTOMATED_SHIP_COLOR` gold `#e0c34c`) vs. manual (`MANUAL_SHIP_COLOR` near-white `#e8e9f0`) ship dots — already fixed, prior to this dispatch, in the J6-J20 gap-closing pass.** Confirmed the fix in `render_map()`: an automated ship draws as a diamond (`moveTo`/`lineTo` forming a rhombus) while a manual ship draws as a circle (`arc`) — the code comment marks this explicitly: "J18 — colorblind-safe differentiation: a diamond, not just a different hue, so automated-vs-manual doesn't rely on color perception at all." Gold vs. near-white also isn't a deuteranopia/protanopia confusion pair to begin with (it's a hue/lightness jump, not a red-green pair), so this was doubly safe even before the shape fix. `planning/TODO.md`'s per-game J18 line was already checked off; this dispatch checked off the separate site-wide colorblind-audit line for Trade Empire that folds J18 in.
- **`.market-price--crashed` (red)** — not a violation: a single-state modifier on the default price-line color, not paired against a contrasting "healthy" color, and the line's own text already states the exact percentage ("X% of baseline") regardless of the color.
- **`.ship-status--idle-warning` (amber `#e0b34c`)** — not a violation: same single-state-callout shape as the market-crashed case, and `ship_status_text()`'s own text already describes the idle state in words.
- **`FLEET_PRIORITY_TARGET_COLOR` (pink) ring, `NODE_COLOR`/`EDGE_COLOR`/`LABEL_COLOR`** — single-purpose decorative/informational colors, no paired good/bad or automated/manual-style state riding on any of them.
- The generic `.meter-fill` (colony need bars, market price bars) has no per-state color modifier at all — one fill color for every bar, so there's no pair to confuse.

No CSS or `game.py` change made by this dispatch (J18's fix predates it). Full pytest suite (unchanged) stays green since nothing was touched.

## Settings panel (implemented)

Site-wide goal (`planning/TODO.md`, origin A9): one panel per game consolidating text-scale and animation/motion controls. **No sound toggle** — this hub has no audio implemented anywhere yet (`planning/LATER.md`'s "Standing question: what can you actually do with audio?"), so a toggle for it would control nothing real.

A new `⚙️ Settings` toggle button in the toolbar (after Summary) opens `#settings-panel`, containing:
- **Text size** — decrease/reset/increase buttons (A−/A/A+), scaling `--text-scale` on the root element (0.85–1.5, step 0.1), same range/step Continuum's Phase 5 `accessibility.js` established first.
- **Reduce Motion** — a toggle button adding/removing `.reduce-motion` on `<html>`, which forces every animation/transition already in `style.css` (the meter shimmer, dome pulse, ship-glow keyframes) to be effectively instantaneous — a global override, layered on top of the existing per-animation `@media (prefers-reduced-motion: reduce)` rules that only respect the OS-level setting, not an in-game player choice.

**`settings.js` is a new standalone file, deliberately independent of Pyodide/`game.py`** — same documented exception this hub already established for Continuum's `accessibility.js`: a browser-level UI preference, not game/save state, so it's persisted to `localStorage` (`trade-empire-text-scale`, `trade-empire-reduced-motion`) rather than riding `get_state()`/`load_state()`. It works even before Pyodide finishes booting.

Verified live: toggling both controls updates the page immediately with zero console errors, and both settings survive a full page reload via `localStorage`. Full pytest suite (225 tests) unaffected — this feature touches no Python.

## Shared confirmation-dialog integration (J19, site-wide goal)

`planning/TODO.md`'s J19 line explicitly asked to check real click
frequency before wiring anything in — skip or soften if spending
research points/automation credits turns out to be a common, low-stakes
action rather than a rare one. **Investigated first, gated after
confirming it's genuinely rare:**

- **Automating a ship** (`automate_ship()`, 150 credits): capped at
  `max_automated_ships()` — base `MAX_AUTOMATED_SHIPS` (2), +1 from the
  `automation_slot` research node, +1 more from `automation_slot_2`, for
  a hard ceiling of 4 — exactly the size of the fixed ship roster. It's
  also a one-time, irreversible purchase per ship (Milestone 6's own
  notes: "there's no de-automate toggle in v1... the unlock is a
  one-time purchase, not a pausable mode"). So this button can be
  clicked **at most 4 times, ever, across an entire playthrough.**
- **Unlocking research** (`unlock_research()`): `RESEARCH_NODES` has
  exactly **6 entries total**, each unlockable exactly once ever — the
  unlock button hides itself once its node unlocks (Milestone 8's
  documented UI pattern), with no re-lock or refund path. So this button
  can be clicked **at most 6 times, ever.**

Combined, that's at most ~10 clicks in an entire playthrough — nowhere
near the repeated Load Cargo/Depart core loop this task's own caveat was
worried about. Both are also genuinely high-stakes: irreversible spends
of currencies that take real session time to accrue (research points at
0.5/tick; the priciest node, Outer Reaches, costs 200 — a very long
accrual). **Conclusion: gate both, not skip or soften** — this is
exactly the rare/high-stakes shape the shared pattern exists for, not
the common/low-stakes shape the caveat warned against.

Both `_make_automate_handler()` and `_make_research_handler()` in
`game.py` now route through `shared/confirm-dialog.js`'s
`ConfirmDialog.ask()` (pre-action confirm only, per the shared pattern's
own shape) before calling `automate_ship()`/`unlock_research()`. Each
ship and each research node gets its own confirm id
(`trade-empire-automate-ship-<id>` / `trade-empire-research-<node_id>`),
so a player's "don't ask again" choice is per-target, not global.
Covered by 5 new tests in `tests/test_confirm_dialog.py` (fake
`js.window.ConfirmDialog`, same technique as Grid's C14/Herd's F16 —
the real fake-DOM harness's `js` module never provides `window` by
default).

Live-verified in a real browser: unlocked Fast Ships I -> dialog showed
"Unlock Fast Ships I for 15 research points? -1 tick travel time,
fleet-wide." with an "Unlock it" confirm label; Cancel left it
unresearched; a second attempt with "don't ask me again" checked ->
Unlock it -> research landed and the skip flag persisted. Separately,
automating Ship 1 -> dialog showed "Automate this ship for 150 credits?
This is permanent -- there's no way to de-automate it afterward." with
an "Automate it" label -> confirmed -> `ships["1"].automated` became
`True` and `total_profit` dropped from 1000 to 850 as expected. Zero new
console errors. Full 230/230 pytest suite (225 existing + 5 new)
unaffected.

## "What's New" changelog panel (implemented)

Site-wide goal (`planning/TODO.md`, origin K16): a small `changelog.json`
(flat list of `{"date", "entry"}`, same loading contract as
`achievements.json` — fetched into the Pyodide boot sequence and handed to
`game.py` as a window global, filesystem fallback for the pytest harness)
rendered in a hidden-until-opened panel behind a new "📋 What's New"
toolbar button, same idiom as the achievements/settings panels
(`on_toggle_changelog()`/`update_changelog_display()`, matching this
file's own `on_toggle_achievements()`/`update_achievements_display()`
almost exactly, including their defensive `if toggle is None or panel is
None: return` guard). Entries render newest-first.

Populated with 9 real, dated highlights spanning all 14 milestones
(collapsed into one entry, since they all landed the same day) plus the
notable post-milestone work above (space-theme pass, mobile needs-strip,
achievements, colorblind audit, settings panel, J19 confirm-dialogs) —
dates cross-checked against `git log` where this file didn't already carry
one.

10 new tests in `tests/test_changelog.py` (catalog/JSON sanity, toggle
open/close, label text, newest-first ordering, rendered content) —
240/240 tests green. Verified live: panel opens, shows the real entries
newest-first, zero console errors.

## Onboarding-tooltip coverage check (site-wide goal, planning/TODO.md, origin A14)

Audited whether a returning player who's skipped or forgotten the
tutorial (`TRADE_EMPIRE_TUTORIAL_STEPS`'s spotlight walkthrough) can
still make sense of the permanent UI's non-obvious parts, on top of the
persistent, reachable-any-time `#howto-toggle-button`/`#howto-panel`.
This game had zero `title=`/`aria-label` attributes in `game.py` going
in (the 4 in `index.html` are all Settings-panel boilerplate shared with
every other game), so investigated properly rather than assuming the
existing four section-level `.info-toggle` icons (Research, Market
Prices, Colonies, Fleet Priority) plus the Ledger's Automation info-toggle
were the whole picture.

Most of the permanent UI already covers itself well, at multiple layers:
- The four section-level `.info-toggle` icons (Research, Market Prices,
  Colonies, Fleet Priority) plus the Ledger's Automation info-toggle
  permanently explain the research-points-are-a-second-currency split,
  the price-crash/recovery mechanic, the need-satisfaction output-scaling
  formula, Fleet Priority's idle-reposition behavior, and the automation-
  slot cap — matching the site's established section-level pattern.
- `ship_status_text()` dynamically states exactly what's going on with
  every ship every render (in-transit ETA, automated-and-running, loaded-
  and-awaiting-destination, idle-too-long warning) — a stronger, always-
  current form of explanation than a static tooltip.
- Every action button already states its cost/effect inline in its own
  label (`Automate (150)`, `Research (30)`, `Purchase Ship (400)`), and
  research nodes needing a prerequisite already said so in their label
  text (`"...+1 more automation slot (requires Automation Expansion)"`)
  — but only in the static `index.html` placeholder shown before Pyodide
  finishes loading.
- The Rift Colonies (Milestone 13's third system, gated behind the
  "Outer Reaches" research node) reuse the exact same need/produce/
  develop mechanic as the home system and the Kepler Cluster, both
  already explained elsewhere — unlike SOL's Sky Cities gap (a genuinely
  new dual-cost mechanic), this isn't a new mechanic needing its own
  explanation, just more colonies using one already covered.

**Real gap found and fixed:** `render_research()` overwrote that
placeholder text every render with `RESEARCH_NODES[node_id]["description"]`
alone, which never mentions a node's `"requires"` prerequisite at all. So
the moment Pyodide finished loading, the "(requires Automation
Expansion)" / "(requires Galaxy Expansion)" hint vanished from the live
DOM for `automation_slot_2` and `outer_reaches` — confirmed live via a
local server (`research_points = 200; render()` left both nodes' status
text identical whether or not their prerequisite was unlocked, with the
unlock button simply disabled and no reason given anywhere permanent). A
returning player sitting on plenty of research points with a locked,
unexplained button is exactly the scenario this audit exists to catch —
the same shape as Aftermath's own `missing_prereqs()` fix, just never
applied here since this tree only grew its first prerequisite edge at
Milestone 13 (J7's note: "the tree gets its first real prerequisite
edge"), after the tutorial copy was already written.

**Fixed:** `render_research()` (`game.py`) now appends
`" (requires {prereq_label})"` to a gated node's status text whenever its
`requires` node isn't yet unlocked, reading the prerequisite's own label
from `RESEARCH_NODES` so the two strings can't drift out of sync, and
drops the note the moment the prerequisite is satisfied. No new DOM
elements, no `index.html` change — the static placeholder text was
already correct, this just makes the same information survive every
subsequent render instead of only the pre-Pyodide flash.

Verified: 2 new tests in `tests/test_research_tree.py`
(`test_render_states_missing_prereq_on_gated_node`,
`test_render_drops_missing_prereq_note_once_satisfied`) — full suite
240 → 242, all green. Live-verified via `hub-dev-server`: with
`research_points = 200` and no prior unlocks, both
`research-automation_slot_2-status` and `research-outer_reaches-status`
read the corrected "(requires ...)" text on the live DOM and the unlock
buttons stayed correctly disabled; zero console errors attributable to
this change (one pre-existing `ERR_FAILED` network error is the
placeholder AdSense client ID failing to load, unrelated to and
unaffected by this fix, same as every other game's ad-bar).

## UI decluttering pass (2026-09-20)

Audited as the closing item of `planning/TODO.md`'s "Big standalone features" section (the user's own note: "everything looks very crowded... making sections either collapsible or other 'screens' within a game could help"). This game is explicitly named in that task's own brief as the likely-crowded case — "just fun," not a teaching game, but with "a lot of panels (fleet, market, colonies, research)" — so it got a real look rather than a quick pass, including a live check at `hub-dev-server` at real desktop width (1280px; this game's mobile-needs-strip fix above already covers the narrow-viewport case).

Most of the panel count is legitimate, not clutter: the Kepler/Rift expansion sub-panels stay `hidden` until their research unlocks them, the endgame panel stays `hidden` until reached, and the toolbar's secondary panels (How to Play, Achievements, What's New, Settings, Summary) are already hidden-until-opened. The six ship panels are each genuinely checked every turn (load/depart is the core loop) so collapsing any of them would hide exactly the "player checks every turn" content the task's own guidance says to leave alone — same reasoning for Market Prices (a per-sale decision) and Colonies (a per-depart decision).

**Real crowding found and fixed, scoped to one panel:** the Research panel always rendered all 6 node rows (`.research-row`, each with its own status line and unlock button) directly under the `Research points: N` line, regardless of whether any node was affordable or relevant yet. This game's own J19 audit (above) already established, independently of this pass, that these unlock buttons are clicked **at most ~6 times in an entire playthrough** — "nowhere near the repeated Load Cargo/Depart core loop" — making this list exactly the "rarely-touched breakdown" shape the site-wide `<details>` pattern targets, not information a player needs on every render. Wrapped the 6 rows in a new `<details class="research-nodes-toggle">` with `<summary>Research nodes (6)</summary>`, **collapsed by default** (unlike Drift's same-day open-by-default fix — this is an occasional action list, not core framing a first-time player needs to see unprompted). `Research points: N` itself stays outside the toggle, unaffected, so the one number players do glance at every round still renders every render. Same `<details>`/`<summary>` idiom as Tide's `.ticker-history-toggle`; new `.research-nodes-toggle` CSS added to `style.css` matching the existing `.info-toggle` palette. No id renamed, `#research-panel > .panel-label::before`'s direct-child selector confirmed unaffected (only `.research-row` elements moved, not `.panel-label`), and no `game.py` change — `render_research()` still targets the same element ids via `getElementById`. Live-verified at 1280px: collapsed by default shows just the points line + summary, expands to all 6 rows with unlock buttons rendering their real prices/disabled-state correctly, collapses back cleanly, zero new console errors. Full pytest suite (242 tests) unaffected — pure HTML/CSS change.

## Round-2 backlog pass, wave 1 (2026-09-20)
Built (planning/TODO.md J-items): J2 (trend arrow on route profitability, from `good_profit_recent`), J4 (labeled "now" marker + tooltip on the price sparkline), J6 (map-canvas hover text explaining the Fleet Priority ring), J12 (Reset name button per ship), J13 (Galaxy overview section in Summary), J14 (veteran hauler badge after 5 round trips on one route; `route_key`/`route_legs` per ship), J18 (automate-button permanence tooltip), J20 (crash recovery ETA tooltip), J24 (avg needs-met % beside colony sparkline), J25 (Fleet efficiency section in Summary; `total_earned` per ship), J26 (locked research tooltip), J30 (map legend). J8 already existed (idle warning text states the exact tick count). New save fields (`route_key`, `route_legs`, `total_earned`, `good_profit_recent`) default safely for old saves. 255 tests.
Left for later: J1, J3, J5, J7, J9, J10, J11, J15, J16, J17, J19, J21, J22, J23, J27, J29 (larger mechanics/visuals).

## Sale-spark burst (J22, implemented)

`planning/TODO.md`'s J22: "A small particle/spark effect on a successful
high-value sale." Purely decorative -- `tick()` only reacts to a sale
*after* `total_profit` is already updated and `sale_log` already
appended, so the effect can never change or delay the actual sale
numbers.

**Threshold: `SALE_SPARK_THRESHOLD = 200` credits.** Reasoning worked
backward from this game's own economy numbers rather than picking a
round number blind: a home-system sale (Ore/Grain/Machinery/Water/
Energy, base `SELL_PRICE` 5-10 credits/unit) tops out around 180 credits
even at full colony development *and* full Milestone-10 specialization
(the best case, Forge World's Machinery: 18 units x 10 credits/unit) --
*without* the Hauler Refit research (`fleet_cargo_multiplier()`, +50%
cargo). Clearing 200 credits therefore takes real, earned progress: the
Hauler Refit unlock, a well-developed/specialized colony, or selling one
of the pricier Kepler/Rift-tier goods (Isotopes 18, Crystal 20,
Antimatter 26 credits/unit) outright. That keeps the very first, very
ordinary sales a new player makes from ever triggering it, while still
making it a recurring mid-game treat rather than a once-a-playthrough
rarity gated behind the endgame.

**Visual treatment:** six small glowing dots (`.sale-spark-0` through
`-5`, fixed clock-face directions via `--spark-x`/`--spark-y` custom
properties rather than randomized inline styles, so the burst is
deterministic and testable) burst outward from the profit readout and
fade over a single 700ms `te-sale-spark` CSS keyframe animation --
matching this game's existing `te-`-prefixed keyframe naming
(`te-meter-shimmer`, `te-dome-pulse`, `te-ship-glow`) and its established
`ease-out`/`forwards` idiom. Respects motion preferences the same way
those three do: an explicit `@media (prefers-reduced-motion: reduce)`
override turns the animation off at the OS level, and the Settings
panel's `.reduce-motion` class (site-wide manual override, see the
"Settings panel" section above) already catches it for free via that
class's existing `animation-duration: 0.001ms !important` rule -- no
per-animation reduced-motion code needed for the in-game toggle.

**Implementation shape, and a real bug live verification caught:**
`_spark_burst_high_value_sale()` (`game.py`) creates the six spans and
removes them again after `SALE_SPARK_DURATION_MS` (700) via
`setTimeout(create_proxy(...), ...)` -- the same one-shot create/time/
remove-after-timeout pattern as Canopy's `_flash_personal_best_badge()`
and this file's own achievement/notice toasts, just creating transient
elements instead of toggling a class on a persistent one. The first
implementation appended those spans directly into `#profit-display`
(the element `render()` already wrote `Total profit: N credits` into via
`.innerText`) -- unit tests against the fake-DOM harness passed, because
that harness's `innerText` was a plain attribute that didn't clear
`.children` on assignment. A live check in a real browser (Pyodide,
`hub-dev-server`) caught what the fake DOM couldn't: on a real
`Element`, assigning `.innerText` replaces all child nodes, so
`render()`'s very next per-tick update wiped the just-created sparks out
before they ever got a frame to paint -- the effect fired but was never
actually visible.

Fixed by splitting `#profit-display` into two children: `#profit-
display-text` (the span `render()` now targets) and a sibling `#sale-
spark-container` (a zero-size, centered overlay the spark burst appends
into instead) -- `index.html`'s only markup change. Also hardened
`tests/fakes.py`'s `FakeElement.innerText` into a real property whose
setter clears `.children`, matching real-DOM `.innerText`/`.innerHTML`
semantics (the latter already worked this way), so this exact bug shape
would be caught by the unit suite in the future, not just live
verification. `tests/test_sale_spark.py` (8 tests) covers: the burst
creates 6 elements with the right classes, it doesn't disturb
`#profit-display-text`'s own content, elements are removed once the fake
timer fires, an ordinary sale (80 credits) doesn't trigger it, a sale one
credit under/exactly at the threshold (192/200 credits) don't/do
trigger, and a clearly high-value sale (320 credits) both triggers and
still cleans up. Full suite 255 -> 263.

Live-verified end to end via `hub-dev-server` and Pyodide directly
(`window.pyodide.runPython(...)`, calling the real gameplay path --
loading a ship, forcing a 40-unit Ore cargo, departing, then ticking it
to arrival): confirmed `#sale-spark-container` gains exactly 6 children
immediately on a 320-credit sale, `#profit-display-text` updates to the
correct total in the same tick without disturbing them, the children are
gone again ~1 second later, and zero console errors throughout. (Pixel
screenshots of this were inconclusive purely because the Browser pane
was hidden on the host side for this session -- `document.hidden` was
`true` in the tab throughout -- not because of anything in the feature
itself; the DOM/console-level checks above are the real verification.)

## Working conventions
- Commit + tag per milestone: `git commit -m "Milestone N: <name>"` then `git tag trade-empire-milestone-0N`.
- Update the Status column as work happens.

- 2026-09-21: J11 -- route readout shows avg profit per trip (new `good_trip_count`, saved; absent in old saves so the average is omitted). Mobile-dock `html body` padding fix (V-AB-2); achievements hub link now anchors to the dashboard (V-AB-5).

## Save-portability audit fix (Z25, 2026-09-21)

Site-wide `planning/TODO.md` Z25 audit (confirm every game's save-code
payload is still a reasonable size). Built a driver script against this
game's own `tests/conftest.py` `GameEnv` (purchase + automate every ship,
unlock all research, then run 5000 real `tick()` calls -- ~83 simulated
minutes at this game's `TICK_INTERVAL_MS=1000`, a realistic "left it
running automated for a long session" case since this game explicitly has
no idle/wait-timer gate but *does* auto-tick via `setInterval` regardless
of player presence) and measured `len(json.dumps(get_state()))`.

**Found a real issue:** `sale_log` (comment: "most recent sale message,
for the status line") is appended to on every single sale inside `tick()`
with no cap at all, unlike every sibling rolling-history field in this
file (`good_profit_recent` capped at `2 * ROUTE_TREND_WINDOW`,
`price_history`/`need_history` capped at `TREND_HISTORY_MAX_POINTS`) --
and confirmed by grep that only `sale_log[-1]` is ever read anywhere
(`render()`'s status line, and its own regression test in
`tests/test_core_loop.py`). At 5000 ticks this alone was ~100KB of a
~110KB total payload -- squarely the "hundreds of KB, worth flagging"
range this audit's own threshold calls out, and it scales without bound
the longer an automated session runs.

**Fixed:** added `SALE_LOG_MAX_ENTRIES = 20` and a
`del sale_log[:-SALE_LOG_MAX_ENTRIES]` right after the existing append in
`tick()`, matching the `del recent[:-2 * ROUTE_TREND_WINDOW]` idiom
already used two lines above it for `good_profit_recent`. 20 is generous
above the "only the last one is read" actual need, in case a future
feature wants a short recent-sales view, same margin this file's other
rolling-history caps already give themselves. `load_state()` was left
restoring `sale_log` without its own truncation (matching
`good_profit_recent`/`price_history`/`need_history`'s existing
load-time behavior, none of which truncate on load either) -- an
oversized loaded save self-heals on the very next `tick()`, so no
correctness gap exists between load and the first tick.

Re-measured after the fix: the identical 5000-tick session's payload
dropped from ~110,566 bytes to 11,000 bytes (`sale_log` itself:
100,576 -> 1,010 bytes). Every other field was already within reason
(ships/colony_states/market_multiplier/research are all bounded by fixed
counts, not per-tick growth).

Verified: full 265/265 pytest suite green (no test asserted `sale_log`'s
length or read anything but its last entry), `flake8 games/trade-empire
--extend-ignore=E501` clean on `game.py` itself (two pre-existing E741
findings in `tests/test_backlog_wave.py` predate and are unrelated to
this change).
## Screen-reader accessibility audit (Z15, site-wide goal, planning/TODO.md)

Static-analysis audit (grepping/reading `index.html`/`game.py`, no live screen
reader in this environment — same audit-only method the colorblind-safety
passes already established for this hub) of the achievements and settings
panels: toggle-button accessible names, panel role/heading semantics, focus
order on open/close, keyboard reachability of interactive elements, and
checkbox/label association.

**No real gap found — no change made.** This game's settings panel is a
short two-row control block (text-size buttons + a "Reduce Motion: On/Off"
toggle button, each row already carrying its own visible `<span
class="settings-row-label">`) rather than the longer checkbox-based panel
some other games in this hub have — there's no separate panel-title heading
element, but nothing in it needs one: each control already names itself via
its own visible label text and the button's own state-reflecting text
("Reduce Motion: Off"/"Reduce Motion: On"), and the `#settings-toggle-button`
above it already states the panel's purpose. Same "plain semantic markup
already covers it" call this hub's colorblind-safety audits make for
comparable cases — not adding a heading purely for the sake of having one.
Checked against the same candidate list as every other game in this pass:
- Both toggle buttons (`#achievements-toggle-button`, `#settings-toggle-button`)
  already carry descriptive visible text, a sufficient accessible name on its
  own — no `aria-label` needed.
- The achievements panel itself has no heading of its own, but is adequately
  labeled by the toggle button's own visible text immediately above it.
- No focus-trap exists anywhere in this hub, and none was warranted here:
  clicking the toggle button never moves focus itself, so it naturally stays
  on that same button when the panel opens or closes.
- Every interactive element inside both panels is a real `<button>`
  (confirmed via a site-wide grep for `.onclick =` assignments and
  `createElement("div")` calls with a wired click handler — none found; this
  game's settings panel has no checkbox at all, so the label/`for` question
  doesn't apply here).

No code changed; ran as the baseline check this pass calls for regardless
of verdict.

## J16: galaxy-dot hover tooltip (2026-09-21)

Hovering the endgame galaxy canvas now names the nearest drawn dot ("Background world #N of M ... decorative dot; the galaxy is abstracted") within a 5px radius, and shows a default explanation elsewhere. Dot placement moved into `endgame_galaxy_dot_position(i)` (same golden-angle spiral, so drawing is unchanged); `endgame_galaxy_hover_text()` is a pure function; the `mousemove` listener is wired once via `_wire_endgame_galaxy_hover`. The tooltip is deliberately honest that dots are decorative rather than inventing per-world data. Suite 270 passing (new `tests/test_galaxy_hover.py`); checked live under Pyodide with no console errors (the render and hover text were exercised through `pyodide.runPython`; a real mouse hover wasn't simulated).

## J27: trade almanac (2026-09-21)

A collapsed "Trade almanac" `<details>` at the top of the Market prices panel lists, per good, its baseline sell price, the range the market can push it through (base x `MIN_PRICE_MULTIPLIER` to base x `MAX_PRICE_MULTIPLIER`), the colony that makes it and the colony that needs it. Rows come from `almanac_rows()` (goods from reachable systems only, so locked Kepler/Rift goods aren't spoiled) and are rendered by `render_almanac()`, called from `render_market()`. The page reuses the `.info-toggle` class for its disclosure behaviour, but the shared circular "i" summary styling is overridden for this label (`.info-toggle.almanac`). Suite 274 passing (new `tests/test_almanac.py`); checked live at desktop and 375px, no horizontal overflow, no console errors.

## J29: opt-in seasonal demand (2026-09-21)

A "Seasonal demand" toggle (default off) in the Market prices panel. While on, `season_ticks` advances each `tick()`; every `SEASON_LENGTH_TICKS` (30) the pair of goods "in demand" rotates through the goods from reachable systems (`seasonal_reachable_goods()`, two per season, wrapping), and a good in demand sells for `SEASONAL_DEMAND_BONUS` (+25%) more. The bonus is applied in `current_sell_price()` (the one place prices are computed, so ship profits and the market display agree), and nothing is ever marked down, matching the game's no-punishment stance. The status line always names the current pair, the ticks left, and the next pair, so it's fully predictable; in-demand goods are also flagged in the market rows. It is opt-in so the base economy and every existing test/balance stay unchanged. New saved field `seasonal_demand: {enabled, ticks}`, validated on load (bad or missing values fall back to off/0). Suite 282 passing (`tests/test_seasonal_demand.py`, 8 tests, plus the expected-keys test); checked live (toggle, status text, in-demand price).

## J23: diplomatic relations (2026-09-21)

Units delivered on trips that cross star systems (home / Kepler / Rift, judged with `_system_label_for_colony()` in `Ship.advance_transit()`) accumulate in `cross_system_units`. `DIPLOMACY_THRESHOLDS = (25, 75, 150)` give relations levels 1-3, and each level is `DIPLOMACY_BONUS_PER_LEVEL` (+5%) on the proceeds of every sale (`profit = round(qty * price * diplomacy_multiplier())`). The bonus is applied to proceeds rather than the per-unit price so it isn't lost to integer rounding of cheap goods, and it leaves the displayed market price untouched. A status line in the Market panel (`#diplomacy-status`, hidden until Galaxy Expansion makes a second system reachable) shows the level, the bonus and the units to the next level. New saved field `cross_system_units`, validated on load (bad/missing values become 0). Suite 288 passing (`tests/test_diplomacy.py`, 6 tests, plus the expected-keys test); checked live (status line appears and counts down).

## J11: opt-in route hazards and insurance (2026-09-21)

Two toggles (both default off) in the Market prices panel. With **Route hazards** on, each loaded arrival has `ROUTE_HAZARD_CHANCE` (8%, rolled from `hazard_rng`, a module-level `random.Random` tests replace with a fixed value) of being disrupted: the cargo is lost and nothing is sold or delivered. `Ship.advance_transit()` returns `(good, 0, payout)` for a disruption (`qty == 0` marks it), and `tick()` credits only the payout, skips the market impact and shows a toast. **Route insurance** (enabled only while hazards are on) charges `INSURANCE_PREMIUM_PER_TICK` (1 credit) for each ship in transit each tick, never taking credits below zero, and refunds `INSURANCE_COVERAGE` (75%) of what the lost trip would have earned. With a 5-tick trip and a typical load this is roughly break-even in expectation, so insurance is a variance-versus-cost choice rather than a free win. Counters (`disruptions_suffered`, `insurance_payouts`, `premiums_paid`) show in the status line. Saved as `route_hazards: {hazards, insurance, disruptions, payouts, premiums}`, validated on load (bad or missing values become off/0). Both are opt-in, so the base economy is unchanged. Suite 297 passing (`tests/test_route_hazards.py`, 9 tests); checked live (toggles, status text, no console errors).

## J5: ship archetypes (2026-09-21)

Ships 5 and 6 are bought with a type chosen from a picker next to their purchase button (`#ship-5/6-archetype-select`); the original four ships are always Balanced. `SHIP_ARCHETYPES` defines the three types: Balanced (no change), Cargo-heavy (x1.5 cargo, +1 travel tick) and Fast (x0.75 cargo, -1 travel tick), each a genuine trade-off so none is strictly better. `Ship.load()` multiplies cargo by the archetype (never below 1 unit), `_begin_transit()` adds the tick delta (never below 1 tick), and non-Balanced ships show their type in their label. `purchase_ship(ship_id, archetype)` falls back to Balanced for an unknown value. Saved per ship as `archetype`, validated on load (bad or missing values become Balanced), so old saves load unchanged. Suite 305 passing (`tests/test_ship_archetypes.py`, 8 tests, plus the ship-keys save test); checked live (picker shows, purchase applies the choice, label updates, no console errors).

## J15: research specialization fork (2026-09-21)

Four new research nodes form a fork gated behind Automation Expansion II. **Automation path:** `auto_efficiency` (120 points: automated ships earn +10% on every sale) then `auto_efficiency_2` (260: +1 automation slot). **Market path:** `market_insight` (120: `recover_market()` recovers 50% faster) then `market_insight_2` (260: `apply_market_sale()` drops the price 30% less per unit). Each node lists `excludes` (the other path's nodes), and `research_node_blocked_by()` makes `can_unlock_research()` refuse a node once the opposite path's first tier is taken, so the choice is permanent; the research panel says "closed: you chose X" and the locked button's tooltip explains it. The "Fully Studied" achievement can't require every node any more (the paths are mutually exclusive), so `_all_research_unlocked()` now means every shared node plus one completed path, and the achievement text says so.

**Real bug found and fixed while verifying this live:** reading `element.innerText` back from an element inside a collapsed `<details>` returns an empty string in a real browser, so the existing `status_el.innerText += " (requires X)"` pattern (from the A14 tooltip audit) silently wiped a research node's label and description whenever the panel was collapsed; the fake-DOM tests can't see this. `render_research()` now builds the text in a local variable and assigns it once, and the same fragile pattern in `render_market()`'s in-demand suffix was removed too. Suite 313 passing (`tests/test_research_specialization.py`, 8 tests, plus the updated all-research achievement test); the closed-branch and requires text were checked live via `textContent`.

## J7: colony investment (2026-09-21)

Every colony panel has an "Invest (60)" button (`#colony-<id>-invest-button`, hidden once the colony is developed) that spends `COLONY_INVEST_COST` (60 credits) to add `COLONY_INVEST_UNITS` (10) units of development progress, the same `cumulative_delivered` progress that deliveries build toward `DEVELOPMENT_THRESHOLD` (100), so investing accelerates Level 2 development and its specialization bonus. The progress logic moved into `ColonyState.add_development()` (which `deliver()` now uses, behaviour unchanged). Investing costs more per unit than a delivery earns and does not raise need satisfaction, so it speeds a colony up without replacing supplying it; it stops once the colony is developed and is refused for colonies in locked systems. No new saved state (the progress already lives in each colony's saved `cumulative_delivered`). One cosmetic caveat: the development line still reads "N/100 <good> delivered" even when some of N was invested. Suite 320 passing (`tests/test_colony_investment.py`, 7 tests); checked live (60 credits spent, 10/100 shown, no console errors).

## J9: market speculation / stockpiles (2026-09-21)

Each good's market row has a small warehouse: `Buy 5` (`STOCKPILE_LOT`) buys at the current sell price into a stockpile capped at `STOCKPILE_CAPACITY` (15), and `Sell all` sells the stockpile at the current price less a `STOCKPILE_SELL_FEE` (10%). Buying nudges the price up and selling nudges it down by the same per-unit impact a ship's sale has (`apply_market_sale()`), so the player's own trades move the market. The limits are what keep it from being a money loop: small capacity, a fee, and price impact; a test confirms a crash-then-recovery cycle profits while buying and selling back at a flat price loses money. Only goods from reachable systems can be stockpiled, and stockpile sales deliberately do not count as trade sales (no `total_sales_count`, `goods_sold_ever` or route stats), so they can't be farmed for achievements. Saved as `stockpile: {good: units}` (only non-zero entries), validated per good on load (bad or missing values become 0). Suite 329 passing (`tests/test_stockpile.py`, 9 tests); checked live (buy 5 for 40, sell for 36 after fee and price impact, no console errors).

## J17: player-run trade posts (2026-09-21)

Once automation is maxed (`automation_is_maxed()`: no free automation slot), a "Establish trade post" button appears in the Market panel. A post costs `TRADE_POST_COST` (400 credits), goes in the next reachable star system that lacks one (`TRADE_POST_SYSTEMS` order: Home, Kepler Cluster, Rift Colonies, gated by Galaxy Expansion and Outer Reaches), and pays `TRADE_POST_INCOME_PER_TICK` (2) credits every `tick()` with no ship assigned; the income is a flat credit, not a sale, so it never touches sale stats or achievements. One post per system means it scales with how far the empire has expanded. Saved as `trade_posts: [system labels]`, validated on load (unknown, duplicate or non-string entries dropped; bad shapes become none). Suite 336 passing (`tests/test_trade_posts.py`, 7 tests); checked live (hidden until automation is maxed, then buildable, status line updates, no console errors).
