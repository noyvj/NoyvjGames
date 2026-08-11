# Loop — Circular Economy & Overconsumption Game

**Read `../climate-quartet-2-plan.md` first for shared conventions.** This file is Loop-specific only. **Build third** in this set — it's more structurally different from the others (redesigning a system rather than managing a rising meter), so get the simpler patterns solid first.

## Concept

Unlike most of the other games in the hub, Loop isn't primarily about watching a meter rise or fall — it's about **redesigning a supply chain**. The player manages a production/consumption system: goods are made, used, and discarded by default. The player can invest in circular systems (repair, reuse, recycling loops) that reduce how much new raw-material extraction each cycle requires. The teaching moment is structural: waste isn't inevitable, it's a design choice built into how the system is shaped.

## Function tag: Systems to combat

This game exists to let the player ideate and build a *system*, not just respond to a threat. It should feel less like "manage a crisis" and more like "redesign the machine" — the player's satisfaction should come from watching a linear extract-use-discard chain become a closed loop, not from surviving a meter.

## Climate issue & hope angle

**Issue:** overconsumption and the emissions/extraction cost of a linear (take-make-waste) production economy.
**Hope angle:** this is naturally one of the easier games to make hopeful, since it's explicitly about building something better rather than staving off a threat. Lean into that — the visual and mechanical payoff of successfully closing a loop (less new extraction needed each cycle, same or better output) should feel like a genuine systems-design win, not just an emissions reduction.

## Core loop

- Turn-based rounds. Player manages a production chain: raw material extraction → manufacturing → consumer use → disposal, by default a straight line.
- Each round, player can invest in circularity infrastructure at different points in the chain: repair networks (extend product use-phase), reuse systems (route used goods back into manufacturing), recycling loops (recover raw materials from disposed goods).
- Each circularity investment reduces how much *new* extraction the next cycle needs to hit the same production target — this is the core payoff loop and should be the most visually satisfying feedback in the game.
- Extraction has an environmental cost meter (emissions/land damage) that rises with new-material use — same underlying "extraction is costly" logic as Canopy, but expressed through a supply-chain lens instead of a forest-plot lens.
- No hard fail-state. Scoring rewards how much of the production target is met via circular flow vs. new extraction by session end — a fully "closed loop" late-game state is the clearest win condition in the whole hub.

## Milestones

| # | Milestone | Content | Status |
|---|-----------|---------|--------|
| 1 | Core linear chain | Extraction → manufacturing → use → disposal, basic production-target loop. Tests: chain-flow calculation, production-target logic | Done |
| 2 | Circularity investments | Repair/reuse/recycling infrastructure that reduces required new extraction per cycle. Tests: extraction-reduction formula per investment type | Done |
| 3 | Environmental cost meter | Cost scaling with new-extraction volume. Tests: cost-calculation formula | Done |
| 4 | Loop-closure visualization state | Tracking and surfacing what percentage of production is circular vs. new-extraction-sourced each round. Tests: percentage-calculation logic | Done |
| 5 | Scoring + hope-angle payoff | End-of-session score rewarding high circularity, with a clear "you closed the loop" state achievable through good play. Tests: scoring formula across sample playthroughs | Done |
| 6 | In-game feedback prompt | Piped to Neon backend per root conventions | Done |
| 7 | Visual/UI pass + hub integration | This game especially benefits from a clear before/after visual of the chain (straight line vs. closed loop), worth prioritizing in the polish pass | Done — all 7 milestones complete |

## Iteration Notes

Design-review pass (pre-playtest, from `climate-games-iteration-pass.md`) — anticipated issues named honestly as anticipated, not observed. Once real playtesting happens, replace/supplement with an actual observation and log what changed in response.

**Anticipated issue:** the supply-chain-as-graph structure risks feeling like a spreadsheet rather than a game if the flow isn't visually intuitive, and "closing the loop" may not read clearly without a visual legend.

**Additions:**
- Literal animated flow of goods along the chain (motion along the chain-flow arrows), color-coded circular vs. linear paths so the structural difference is seen, not inferred from numbers.
- Light flavor naming per goods category so the abstract chain feels grounded in relatable objects rather than generic "units."
- A short comparison at session end against an illustrative "average real-world supply chain" circularity rate, for context.

**Testing focus:** do players understand what "closing the loop" visually means without a legend or explanation? Is the environmental cost meter's link to extraction volume clear?

**Cross-cutting:** every game gets one short, factual, non-lecturing context blurb naming the real-world issue — a light anchor, not narration replacing the mechanic.

## Tech notes

- Python/Pyodide, per root conventions.
- Model the production chain as a graph/flow structure (nodes for extraction/manufacturing/use/disposal, with circularity investments adding new edges back into earlier stages) — this makes both the logic and the eventual visualization more natural than a flat meter-based approach.

## Working conventions

- Commit + tag per milestone: `git commit -m "Milestone N: <name>"` then `git tag loop-milestone-0N`.
- Update the milestone table Status as work happens.
