# Grid — Energy Transition Game

**Read `../climate-quartet-plan.md` first for shared conventions (testing, feedback hook, hope-angle requirement, hub integration).** This file is Grid-specific only.

## Concept

You manage a regional power grid across a series of rounds. Demand grows every round. You choose which plant types to build or retire. Fossil plants are cheap and reliable early; renewables cost more upfront but get cheaper over time as you invest in them (mirrors real-world cost curves — this is the mechanic that carries the lesson, not a stat you show the player directly).

## Climate issue & hope angle

**Issue:** energy-sector emissions, the single largest lever in real-world climate mitigation.
**Hope angle:** the game must show that early investment in renewables pays off — cheaper energy, fewer disruptions, a visibly better late-game position than a fossil-heavy strategy. A player who leans renewable early should end up in a *better* position than one who doesn't, not just a "cleaner but harder" one. This is the antidote to "sustainability = sacrifice."

## Core loop

- Turn-based, discrete rounds (not real-time ticking).
- Each round: demand rises by some amount. Player allocates budget to build/retire/upgrade plants.
- Plant tiers (start simple, expand if time allows): Coal, Gas, Nuclear, Solar, Wind, Hydro.
- Renewable costs decrease the more the player has already invested in them (learning-curve effect) — this needs to be visible/legible to the player, not hidden math.
- Emissions accumulate as a rising background meter tied to the fossil-heavy share of the grid.
- **No hard fail-state/game over.** Instead, rising emissions trigger progressively more frequent/severe disruption events (brownouts, damaged plants, cost spikes) — the game gets *harder to manage*, not suddenly lost. This is what teaches "delay compounds cost" without punishing exploration.
- Scoring/win condition: sustained grid stability over N rounds, weighted by how clean the grid became over time (not just final-state cleanliness).

## Milestones

1. **Core state loop** — demand growth, budget allocation, plant build/retire, round progression. No emissions or events yet. Tests: state transitions for budget spend, plant count changes, demand growth formula.
2. **Emissions meter + cost curve** — emissions accumulate based on grid composition; renewable costs decrease with cumulative investment. Tests: emissions calculation, cost-curve decay formula.
3. **Disruption events** — brownouts/damage triggered probabilistically by emissions level, scaling in frequency/severity. Tests: event-trigger thresholds, damage application.
4. **Scoring + hope-angle payoff** — end-of-run scoring that rewards sustained clean transition, not just final snapshot. Tests: scoring calculation across sample playthrough logs.
5. **In-game feedback prompt** — end-of-run 1–2 question prompt, piped to Neon backend per root conventions.
6. **UI/visual pass + hub integration** — tier icons, meter displays, event notifications. Polish only after 1–5 are solid.

## Tech notes

- Python/Pyodide, per root conventions.
- Keep the core state (demand, budget, plant counts, emissions, event log) as a plain serializable object — this makes both testing and later save/resume trivial if you want it.

## Working conventions

- Commit + tag per milestone: `git commit -m "Milestone N: <name>"` then `git tag grid-milestone-0N`.
- Update the milestone table Status as work happens.
- Once ready, move this file into `games/grid/CLAUDE.md` and build there — same pattern as SOL and Trade Empire.
