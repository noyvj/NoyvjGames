# Canopy — Deforestation & Carbon Sinks Game

**Read `../climate-quartet-plan.md` first for shared conventions (testing, feedback hook, hope-angle requirement, hub integration).** This file is Canopy-specific only. **Build this one first** — it's the simplest of the four and establishes the pattern the others follow.

## Concept

A single forest region divided into a grid of plots. Each plot can be cleared (for quick resource income), left alone (slow passive value growth), or replanted (recovery after clearing, slower than never-cleared). Combines active management (clicking individual plots) with passive/idle accumulation (value compounds over time on preserved/replanted plots).

## Climate issue & hope angle

**Issue:** land-use change and loss of carbon sinks.
**Hope angle:** replanting must visibly work — a cleared plot that gets replanted should recover, just more slowly than if it had never been cleared. The game needs an end-state or late-game moment where a mostly-preserved/restored forest is clearly thriving (a visible "if you'd done this from day one" or "recovery is real, just slower" signal), not just a number going up.

## Core loop

- One forest region, rendered as a grid of individual plots (not one abstract meter — the spatial layout matters for the "some plots recovering, some still bare" visual).
- Player can click a plot to: clear (immediate resource payout, plot becomes bare), preserve (do nothing, passive value accrues), replant (costs a little, starts a slower recovery timer).
- Passive value compounds the longer a plot stays intact — a multiplier that grows over time, not a flat rate, so patience is rewarded increasingly.
- Cleared plots degrade in *future* yield potential (soil quality drops) — clearing repeatedly on the same plot gets worse, not better, over time.
- No fail-state. It's a comparison game — the player accumulates two visible numbers over a session: total short-term resource income vs total standing forest value — and can watch how the balance shifts depending on their play style.

## Milestones

| # | Milestone | Content | Status |
|---|-----------|---------|--------|
| 1 | Grid + plot states | Grid of plots, each with a state (bare/preserved/replanting/recovered), basic click interactions. Tests: state transitions per plot action | Done |
| 2 | Passive value accumulation | Compounding value formula for preserved/recovered plots. Tests: value-growth-over-time calculation | Done |
| 3 | Clearing payout + soil degradation | Resource payout on clear, degrading future yield on repeated clearing of the same plot. Tests: payout calculation, degradation stacking | Done |
| 4 | Replant recovery timer | Replanted plots recover on a slower timeline than never-cleared ones, reaching near-parity eventually. Tests: recovery timer logic, near-parity threshold | Done |
| 5 | Comparison scoring + hope-angle payoff | Surfacing the short-term-income vs standing-forest-value comparison clearly at session end. Tests: comparison calculation across sample play logs | Done |
| 6 | In-game feedback prompt | Piped to Neon backend per root conventions | Done |
| 7 | Visual pass + hub integration | Grid rendering, plot state icons/colors, session summary screen | Done — all 7 milestones complete |

## Iteration Notes — Pass 1 (implemented)

Design-review pass (pre-playtest, from `climate-games-iteration-pass.md`). Anticipated issue: the plot-grid mechanic risked feeling passive/idle without clear stakes, and soil degradation from repeated clearing risked not reading clearly without a tooltip.

**Built in response (see `BCM114-DEV-LOG.md` 2026-08-11):** a continuous plot-maturity color gradient (bare → light green recovering → deep green mature) plus a recovery-milestone flash, and a short factual context blurb referencing a real reforestation approach. Audio cue on recovery was considered and skipped — no audio system in the stack; the visual-only version shipped instead.

**Open testing question:** do players notice degradation stacking on repeatedly-cleared plots without being told? Is plot state readable at a glance across the session?

## Iteration Notes — Pass 2 (not yet implemented)

Second design-review pass, from `climate-games-iteration-pass-2.md`, building on Pass 1. **Selected additions: A (biodiversity sub-meter) + B (stakeholder tension).**

- **Biodiversity sub-meter:** preserved and recovered plots accumulate a biodiversity value over time, separate from the passive economic value already tracked — represented simply (e.g. small wildlife icons appearing on well-established plots) rather than another number to read. Deepens the hope payoff: a thriving late-game forest isn't just economically valuable, it visibly has life in it.
- **Stakeholder tension:** periodically, the player faces a plot-specific decision where local community needs (a request to clear a specific plot for housing, farming, or resources) conflict with preservation. Not a trap or a "wrong answer" mechanic — meant to introduce real ethical weighing (whose need matters, short-term vs. long-term) rather than making preservation an obviously correct default choice every time.
- **Visual polish for this pass:** biodiversity should be legible at a glance (small animated wildlife sprites/icons on mature plots, subtle motion) without cluttering the plot grid. Stakeholder-tension moments should get a distinct visual treatment (a different UI panel or framing) so they read as a different kind of decision than routine plot management.

## Tech notes

- Python/Pyodide, per root conventions.
- Keep the plot grid as a simple 2D array of plot-state objects — straightforward to test and to render.

## Working conventions

- Commit + tag per milestone: `git commit -m "Milestone N: <name>"` then `git tag canopy-milestone-0N`.
- Update the milestone table Status as work happens.
