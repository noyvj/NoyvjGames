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

## Iteration Notes — Pass 1 (implemented)

Design-review pass (pre-playtest, from `climate-games-iteration-pass.md`). Anticipated issue: the renewable cost-curve mechanic (the actual lesson) risked being invisible as pure numbers — a player could succeed without ever consciously registering "investing early made things cheaper."

**Built in response (see `BCM114-DEV-LOG.md` 2026-08-11):** the live two-line emissions/renewable-cost trend graph, and a short factual context blurb on first unlocking a renewable tier. Weather-variability-on-renewable-output was considered and deliberately skipped as scope discretion.

**Open testing question:** does a first-time player, unprompted, notice that early renewable investment made later rounds easier? The in-game feedback prompt asks directly: "Did investing early feel like it paid off?"

## Iteration Notes — Pass 2 (implemented)

Second design-review pass, from `climate-games-iteration-pass-2.md`, building on Pass 1. **Selected additions: A (global comparison) + B (infrastructure age/vulnerability).**

- **Global comparison:** at session end, show the player's grid trajectory (emissions curve, clean-energy share over time) plotted against a real-world average trend line, pulled or hardcoded from public data. A secondary comparison against other players' aggregate outcomes (via the ratings backend) is a nice stretch goal, but the real-world benchmark is the priority.
- **Infrastructure age/vulnerability:** plants accumulate an age value each round; older plants become progressively more failure-prone (higher chance of costly breakdown events) unless maintained. Adds a maintenance-budget dimension separate from the build/retire decision, reinforcing "cheap now, costly later" from a different angle.
- **Visual polish for this pass:** the two-line graph should carry the global-comparison line as a third, visually distinct series (three lines max, stay legible). Aging plants should show a visible wear state (icon degrades slightly) so vulnerability is seen before it's felt as a breakdown event.

## Info Page — real-world sources (implemented)

An optional, player-triggered "The Real Story" panel — never forced mid-session, since the mechanic teaches first and this is a supplement for players who want to go deeper. Toggled via a button near the top of the page; shows a short framing paragraph (written fresh, not copied from any source), a one-line note tying the mechanic to real data, and a sources list with clickable links.

**Framing:** Electricity generation is one of the largest single sources of global emissions, and the fastest way to cut it is building out cleaner capacity — not rationing power. Renewables have gotten dramatically cheaper the more of them get built, a real economic trend called a learning curve. That's the same tension Grid asks you to manage: lean into that cheaper long-run path, or lean on familiar fossil capacity.

**Mechanic tie-in:** Grid's cost curve and its global-comparison line are grounded in published wind/solar learning-rate data (roughly 15%/24% cost decline per capacity doubling), not an invented number.

**Sources:**
1. [IEA — Rapid rollout of clean technologies makes energy cheaper, not more costly](https://www.iea.org/news/rapid-rollout-of-clean-technologies-makes-energy-cheaper-not-more-costly) — real-world backing for Grid's central claim that leaning renewable is the cheaper long-run path, not a sacrifice.
2. [Oxford Institute for Energy Studies — A critical assessment of learning curves for solar and wind power technologies](https://www.oxfordenergy.org/publications/a-critical-assessment-of-learning-curves-for-solar-and-wind-power-technologies/) — a balanced, critical look at the same cost-decline concept Grid's core mechanic is built on.
3. [US DOE / Lawrence Berkeley National Lab — Learning a Better Way To Forecast Wind and Solar Energy Costs](https://www.energy.gov/cmei/solar/articles/learning-better-way-forecast-wind-and-solar-energy-costs) — the actual learning-rate figures (wind ~15%, solar ~24% per capacity doubling) behind Grid's cost curve.
4. [IEA — Breakthrough Agenda Report 2025: Power](https://www.iea.org/reports/breakthrough-agenda-report-2025/power) — current real-world electricity cost figures, grounding the global-comparison line.

All four links verified live before merging. Source 2 (Oxford) returns 403 to automated fetchers (bot-protection) but loads fine in a real browser — confirmed the pattern is consistent with several other major institutional domains checked the same way.

## Tech notes

- Python/Pyodide, per root conventions.
- Keep the core state (demand, budget, plant counts, emissions, event log) as a plain serializable object — this makes both testing and later save/resume trivial if you want it.

## Working conventions

- Commit + tag per milestone: `git commit -m "Milestone N: <name>"` then `git tag grid-milestone-0N`.
- Update the milestone table Status as work happens.
