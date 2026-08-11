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

| # | Milestone | Content | Status |
|---|-----------|---------|--------|
| 1 | Core settlement loop | Resource allocation between output/reduction/adaptation, seasonal round progression. Tests: allocation logic, seasonal tick | Done |
| 2 | Acidity meter + delayed fish-stock consequence | Acidity rises/falls per allocation; fish yield degrades on a lag tied to accumulated acidity, not instant response. Tests: acidity calculation, lagged consequence formula | Done |
| 3 | Sea-level timeline + adaptation dampening | Background sea-level rise; adaptation infrastructure reduces effective damage rate. Tests: sea-level progression, damage-rate-reduction calculation | Done |
| 4 | Tile-grid coastline rendering | Simplified grid where tiles flip state as sea-level crosses thresholds. Tests (state layer only, not rendering): tile-state-flip thresholds | Done — pure Pyodide, no JS/Canvas fallback needed |
| 5 | Hope-angle payoff | Clear before/after comparison showing early adaptation investment flattening the damage curve. Tests: comparison calculation across sample play logs | Done |
| 6 | In-game feedback prompt | Piped to Neon backend per root conventions | Done |
| 7 | Visual/UI pass + hub integration | | Done — all 7 milestones complete |

## Iteration Notes

Design-review pass (pre-playtest, from `climate-games-iteration-pass.md`) — anticipated issues named honestly as anticipated, not observed. Once real playtesting happens, replace/supplement with an actual observation and log what changed in response.

**Anticipated issue:** delayed consequence (the whole point of the game) risks reading as random or confusing rather than caused, if the fish-stock crash arrives with no visible link back to earlier acidity choices. Two meters (acidity, sea level) may also blur together visually.

**Additions:**
- A short running log/ticker ("Fish stocks quietly declining — rising acidity") that narrates delayed effects as they build, without fully spelling out the mechanic — enough to make cause traceable in hindsight, not enough to remove the lag as a felt experience.
- Clear visual separation between the acidity meter and sea-level indicator (different colors/positions, not adjacent bars that read as one system).
- A short end-of-session before/after comparison of the coastline, for the hope-angle payoff.

**Testing focus:** ask directly in the feedback prompt whether players understood *why* their fish stock declined — this is the clearest test of whether delayed consequence taught anything or just felt arbitrary.

**Cross-cutting:** every game gets one short, factual, non-lecturing context blurb naming the real-world issue — a light anchor, not narration replacing the mechanic.

## Tech notes

- Default Python/Pyodide; JS/Canvas is an explicitly pre-approved fallback for the tile-grid rendering step only (milestone 4) if needed — keep all state logic in Python either way, since that's what gets tested.
- Keep state and rendering cleanly separated from the start, given the likely rendering-approach decision at milestone 4.

## Working conventions

- Commit + tag per milestone: `git commit -m "Milestone N: <name>"` then `git tag tide-milestone-0N`.
- Update the milestone table Status as work happens.
