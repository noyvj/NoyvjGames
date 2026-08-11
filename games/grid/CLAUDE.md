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

| # | Milestone | Content | Status |
|---|-----------|---------|--------|
| 1 | Core state loop | Demand growth, budget allocation, plant build/retire, round progression. No emissions or events yet. Tests: state transitions for budget spend, plant count changes, demand growth formula | Done |
| 2 | Emissions meter + cost curve | Emissions accumulate based on grid composition; renewable costs decrease with cumulative investment. Tests: emissions calculation, cost-curve decay formula | Done |
| 3 | Disruption events | Brownouts/damage triggered probabilistically by emissions level, scaling in frequency/severity. Tests: event-trigger thresholds, damage application | Done |
| 4 | Scoring + hope-angle payoff | End-of-run scoring that rewards sustained clean transition, not just final snapshot. Tests: scoring calculation across sample playthrough logs | Done |
| 5 | In-game feedback prompt | End-of-run 1–2 question prompt, piped to Neon backend per root conventions | Done |
| 6 | UI/visual pass + hub integration | Tier icons, meter displays, event notifications. Polish only after 1–5 are solid | Done — all 6 milestones complete |

## Iteration Notes

Design-review pass (pre-playtest, from `climate-games-iteration-pass.md`) — anticipated issues named honestly as anticipated, not observed. Once real playtesting happens, replace/supplement with an actual observation and log what changed in response.

**Anticipated issue:** the renewable cost-curve mechanic (the actual lesson) may be invisible as pure numbers — a player can succeed without ever consciously registering "investing early made things cheaper."

**Additions:**
- A simple two-line graph (emissions trend + average energy cost trend) updating live across rounds, so the compounding effect is seen, not just felt in the numbers.
- A short context blurb on first unlocking a renewable tier, grounding it in the real cost-curve trend it's modeling (one sentence, factual, no lecture).
- Optional depth-add if time allows: weather variability affecting renewable output reliability, adding a small realism layer without expanding scope much. (Skipped for now — scope discretion, revisit if time allows.)

**Testing focus:** does a first-time player, unprompted, notice that early renewable investment made later rounds easier? Use the in-game feedback prompt to ask directly: "Did investing early feel like it paid off?"

**Cross-cutting:** every game gets one short, factual, non-lecturing context blurb naming the real-world issue — a light anchor, not narration replacing the mechanic.

## Tech notes

- Python/Pyodide, per root conventions.
- Keep the core state (demand, budget, plant counts, emissions, event log) as a plain serializable object — this makes both testing and later save/resume trivial if you want it.

## Working conventions

- Commit + tag per milestone: `git commit -m "Milestone N: <name>"` then `git tag grid-milestone-0N`.
- Update the milestone table Status as work happens.
