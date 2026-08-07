# Herd — Industrial Agriculture & Methane Game

**Read `../climate-quartet-2-plan.md` first for shared conventions.** This file is Herd-specific only. **Build this one first** in the second set — it's the simplest, closest in shape to Grid/Canopy from the original four.

## Concept

A farm/ranch management game. Growing your herd or output directly scales a methane-emissions meter that's mechanically distinct from the CO2-driven meters elsewhere in the hub (Grid, Tide). The player discovers through play — not through a tooltip — that "grow the farm" and "keep emissions low" pull against each other by default, and has to actively invest in decoupling them (feed changes, herd-size limits, methane capture infrastructure) rather than just growing less.

## Function tag: Causes

This game exists to make an invisible cause of climate change (methane from industrial agriculture) into something the player is directly and unavoidably producing. The emissions meter should rise as an automatic *consequence* of the player's core success metric (herd size / output), not as a separate thing they choose to ignore — that coupling is the entire lesson.

## Climate issue & hope angle

**Issue:** methane emissions from industrial-scale livestock agriculture.
**Hope angle:** decoupling is possible and profitable, not just a tax on growth. A player who invests in feed changes, herd-size discipline, or capture infrastructure should be able to reach a *larger, more profitable* farm with a lower emissions footprint than a player who just grows unchecked — proving decoupling isn't sacrifice, it's better management.

## Core loop

- Turn-based rounds. Player invests in herd growth, output infrastructure, or emissions-reduction measures each round.
- Methane meter rises automatically and proportionally to herd size/output — this coupling is default and visible from turn one.
- Reduction measures (feed additives, herd caps, capture systems) cost resources but reduce the coupling ratio (same herd size, lower emissions) rather than requiring the player to shrink the farm.
- No hard fail-state. High sustained methane triggers soft consequences (market/regulatory pressure, reduced yields from degraded land) that make an unchecked-growth strategy visibly worse over time, without ending the game.
- Scoring: long-run profitability weighted against sustained emissions level — rewards decoupling, not just growth or just restraint.

## Milestones

| # | Milestone | Content | Status |
|---|-----------|---------|--------|
| 1 | Core farm loop | Herd growth, output, resource allocation across rounds. Tests: growth calculation, resource allocation logic | Done |
| 2 | Coupled methane meter | Meter rises automatically tied to herd size/output. Tests: coupling-ratio calculation | Pending |
| 3 | Decoupling measures | Feed/cap/capture investments that reduce the coupling ratio without requiring shrinkage. Tests: ratio-reduction formula per measure type | Pending |
| 4 | Soft consequence system | Market/regulatory/yield pressure scaling with sustained high emissions, no hard fail-state. Tests: pressure-trigger thresholds | Pending |
| 5 | Scoring + hope-angle payoff | Profitability-vs-emissions scoring that rewards decoupling as the best strategy, provably better than either pure-growth or pure-restraint. Tests: scoring formula across sample playthroughs | Pending |
| 6 | In-game feedback prompt | Piped to Neon backend per root conventions | Pending |
| 7 | Visual/UI pass + hub integration | | Pending |

## Tech notes

- Python/Pyodide, per root conventions.
- Keep the coupling-ratio calculation as an isolated, clearly named function — it's the single mechanic the whole lesson depends on, so it needs to be easy to test in isolation and easy to explain in the Contextual Report Blog.

## Working conventions

- Commit + tag per milestone: `git commit -m "Milestone N: <name>"` then `git tag herd-milestone-0N`.
- Update the milestone table Status as work happens.
