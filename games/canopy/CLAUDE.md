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

## Iteration Notes

Design-review pass (pre-playtest, from `climate-games-iteration-pass.md`) — anticipated issues named honestly as anticipated, not observed. Once real playtesting happens, replace/supplement with an actual observation and log what changed in response.

**Anticipated issue:** the plot-grid mechanic risks feeling passive/idle without clear stakes, and soil degradation from repeated clearing may not read clearly without a tooltip.

**Additions:**
- Color gradient per plot state (bare → light green recovering → deep green mature) so state is legible at a glance without reading numbers.
- Light visual cue on recovery milestones (a small sparkle/glow flash) to make the hope angle felt, not just tracked. (Audio cue skipped — no audio system in the stack; visual-only version implemented.)
- Short grounding context blurb referencing a real reforestation approach the mechanic loosely echoes.

**Testing focus:** do players notice degradation stacking on repeatedly-cleared plots without being told? Is plot state readable at a glance across the session?

**Cross-cutting:** every game gets one short, factual, non-lecturing context blurb naming the real-world issue — a light anchor, not narration replacing the mechanic.

## Tech notes

- Python/Pyodide, per root conventions.
- Keep the plot grid as a simple 2D array of plot-state objects — straightforward to test and to render.

## Working conventions

- Commit + tag per milestone: `git commit -m "Milestone N: <name>"` then `git tag canopy-milestone-0N`.
- Update the milestone table Status as work happens.
