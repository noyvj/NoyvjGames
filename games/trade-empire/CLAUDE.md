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
| 3 | Colony need system v1 | Colonies have need-sets; output scales with needs met; minor flavor text per colony | Pending |
| 4 | Market economics | Prices fluctuate with supply; overproducing a good crashes its price | Pending |
| 5 | Manual scaling friction | More routes/colonies added — manual management gets genuinely busy, foreshadowing automation | Pending |
| 6 | Automation v1 | First automation unlock — a route can run itself, limited slots/cost | Pending |
| 7 | 2D map v1 | Colonies as nodes, routes as lines — first visual leap, still no moving ships | Pending |
| 8 | Research tree v1 | Framework + early nodes; gates automation tiers and new ship types | Pending |
| 9 | Evolving needs v2 | Needs meaningfully change/expand as colonies develop further | Pending |
| 10 | Colony specialization | Worlds develop distinct strengths/weaknesses based on environment/history | Pending |
| 11 | Ships on the map | Automated routes render as moving dots along the map's lines | Pending |
| 12 | Fleet-level automation | Prioritization rules across many routes at once, not just per-route toggles | Pending |
| 13 | Galaxy scaling | Research-gated expansion to more systems/regions | Pending |
| 14 | Endgame | Fully automated economy visible at scale (hundreds of worlds, many ships); soft win-state, sandbox continues | Pending |

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
