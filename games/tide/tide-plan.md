# Tide — Ocean Acidification & Sea-Level Rise Game

**Read `../climate-quartet-plan.md` first for shared conventions (testing, feedback hook, hope-angle requirement, hub integration).** This file is Tide-specific only. **Build third** — the grid redraw is the most visually involved piece of the four, so get Grid and Canopy's patterns solid first.

## Concept

You run a coastal settlement, balancing fishing/industry output against ocean health (an acidity meter) and a slowly rising sea-level line. The core teaching challenge here is **delayed consequence** — the damage from today's choices shows up late, which is exactly why acidification is hard for people to intuitively grasp in real life. The game should make that lag itself the lesson, not smooth it over for playability's sake.

## Climate issue & hope angle

**Issue:** ocean acidification and sea-level rise, and specifically the *delay* between cause and effect.
**Hope angle:** investment in adaptation infrastructure (seawalls, wetland restoration) should visibly slow the rate of sea-level encroachment and buy real time — not stop it outright (that would undercut the delayed-consequence lesson), but demonstrably change the trajectory. A player who invests early should see a flatter curve later, proving that acting now — even without immediate payoff — matters.

## Core loop

- Turn-based, seasonal cycles (simplest to implement and matches a settlement-management feel).
- Player allocates resources between: industry/fishing output (immediate income), acidity-reducing measures, and adaptation infrastructure (seawalls, wetland buffers).
- Acidity meter rises with industry output, falls (slowly) with dedicated reduction spending.
- Sea level rises on a slow background timeline, independent of player action *except* that adaptation infrastructure reduces its effective impact rate (not the rise itself — sea level keeps rising in the world, but well-adapted settlements are less damaged by it).
- **Grid redraw for sea-level rise:** implement this as a simplified tile-based coastline (a grid, not detailed art) where rows/tiles flip from "land" to "flooded" as the sea-level value crosses thresholds. This keeps the visual payoff (players can *see* the coastline shrink) without requiring real art assets — it's state-driven tile rendering, same pattern as Canopy's plot grid, just reading from a different variable.
- Fish stock (tied to acidity) acts as a slow-building consequence: high acidity eventually crashes the fishing yield, which is the player's own economy quietly punishing over-extraction — mirrors Canopy's "your own resource base collapses" lesson but on a longer delay.

## Milestones

1. **Core settlement loop** — resource allocation between output/reduction/adaptation, seasonal round progression. Tests: allocation logic, seasonal tick.
2. **Acidity meter + delayed fish-stock consequence** — acidity rises/falls per allocation; fish yield degrades on a lag tied to accumulated acidity, not instant response. Tests: acidity calculation, lagged consequence formula.
3. **Sea-level timeline + adaptation dampening** — background sea-level rise; adaptation infrastructure reduces effective damage rate. Tests: sea-level progression, damage-rate-reduction calculation.
4. **Tile-grid coastline rendering** — simplified grid where tiles flip state as sea-level crosses thresholds. **Decide Python/Pyodide vs. JS/Canvas here** if pure-Pyodide rendering proves too slow or fiddly — this is the one game where a JS fallback is pre-approved. Tests (state layer only, not rendering): tile-state-flip thresholds.
5. **Hope-angle payoff** — clear before/after comparison showing early adaptation investment flattening the damage curve. Tests: comparison calculation across sample play logs.
6. **In-game feedback prompt** — piped to Neon backend per root conventions.
7. **Visual/UI pass + hub integration.**

## Tech notes

- Default Python/Pyodide; JS/Canvas is an explicitly pre-approved fallback for the tile-grid rendering step only (milestone 4) if needed — keep all state logic in Python either way, since that's what gets tested.
- Keep state and rendering cleanly separated from the start, given the likely rendering-approach decision at milestone 4.

## Working conventions

- Commit + tag per milestone: `git commit -m "Milestone N: <name>"` then `git tag tide-milestone-0N`.
- Update the milestone table Status as work happens.
- Once ready, move this file into `games/tide/CLAUDE.md` and build there — same pattern as SOL and Trade Empire.
