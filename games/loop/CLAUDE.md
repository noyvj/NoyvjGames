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

## Iteration Notes — Pass 1 (implemented)

Design-review pass (pre-playtest, from `climate-games-iteration-pass.md`). Anticipated issue: the supply-chain-as-graph structure risked feeling like a spreadsheet rather than a game if the flow wasn't visually intuitive, and "closing the loop" risked not reading clearly without a visual legend.

**Built in response (see `BCM114-DEV-LOG.md` 2026-08-11):** animated chain-flow particles (color-coded circular vs. linear paths), goods-flavor naming per category, and an end-of-session comparison against an illustrative real-world supply-chain circularity rate.

**Open testing question:** do players understand what "closing the loop" visually means without a legend or explanation? Is the environmental cost meter's link to extraction volume clear?

## Iteration Notes — Pass 2 (implemented)

Second design-review pass, from `climate-games-iteration-pass-2.md`, building on Pass 1. **Selected additions: B (trade network) + C (single-item vignette).**

- **Trade network:** allow the player's system to share or trade circularity capacity with a neighboring system (e.g. sending recovered materials outward, receiving reuse capacity inward), adding a light systemic/social layer to what's otherwise a self-contained chain. Keep this simple — a basic import/export of circularity capacity, not a full second economy to manage.
- **Single-item vignette:** alongside the abstract flow-chain view, add a short, concrete side-view following one representative product (a phone, a shirt) as it moves through either a closed loop or a straight line, making the abstraction tangible for a player who might not naturally read a flow diagram.
- **Visual polish for this pass:** the single-item vignette is itself a visual addition — treat it as a small, optional inset or a between-round cutaway, not a separate full mode, so it stays lightweight to build. The trade-network link should be visually distinct from the internal loop (a different color/line style for capacity crossing in from outside).

## Iteration Notes — Pass 3 (Fun/Teaching Balance)

Fun/teaching-balance review pass, from `climate-games-fun-teaching-balance.md`. **Risk:** the supply-chain-as-graph structure risks a different flavor of boredom than idle waiting — dry abstraction, where "closing the loop" is legible as a number improving but not *felt* as a meaningful change.

**Fix (per the design doc, framed as already satisfied by Pass 2):** the single-item vignette added in Pass 2 is the direct answer — the abstract flow-chain graph is where the strategy lives, and the vignette is where the player *feels* what that strategy means. Checked this concretely rather than taking it on faith:

- `vignette_message()` is driven by `chain.circular_fraction_this_cycle()` — the same live figure the abstract chain view uses — not a separate or static value, so the vignette text can't drift out of sync with what the player actually did.
- `render()` calls `vignette_message(fraction)` and writes it to `vignette-display` on every render pass, and every state-changing handler (`_make_circularity_handler`, `on_invest_trade_link`, `on_advance_cycle`) calls `render()` synchronously right after mutating `chain` state — no delay, no batching, no wait for cycle-advance. Clicking a circularity or trade-link button updates the vignette in the same tick as the click.
- Imported trade-link supply counts toward the fraction too (`circular_supply()` = internal + imported), so the vignette reacts to both investment paths the player has, not just the internal one.

**Conclusion: satisfied, no code change made.** Added `tests/test_iteration_pass_3.py` (5 tests) as a permanent regression check locking in that the vignette updates immediately on investment (no `advance_cycle()` needed) and always matches the chain's current fraction — so this stays true if the render/handler wiring is ever touched later.

## Info Page — real-world sources (implemented)

*Implementation is now shared across all 8 climate-quartet games — see `shared/info_page.py` and `shared/info-page.css`. Only the content below (framing/tie-in/sources) is game-specific; the rendering/toggle code moved out of this game's `game.py`.*

An optional, player-triggered "The Real Story" panel — never forced mid-session, since the mechanic teaches first and this is a supplement for players who want to go deeper. Toggled via a button near the top of the page; shows a short framing paragraph (written fresh, not copied from any source), a one-line note tying the mechanic to real data, and a sources list with clickable links.

**Framing:** Most of the modern economy still runs in a straight line — extract, make, use, discard — even though a genuinely circular alternative (eliminate waste, circulate materials, regenerate nature) is well-documented and already improving outcomes where it's tried. Loop's chain-visualization mechanic is a direct simplification of that real framework.

**Mechanic tie-in:** Loop's three circularity investments (repair, reuse, recycling) map onto the three real circular-economy design principles this whole field is built around.

**Sources:**
1. [Ellen MacArthur Foundation — The Circular Economy: Definition & Model Explained](https://www.ellenmacarthurfoundation.org/topics/circular-economy-introduction/overview) — the standard-setting definition Loop's core mechanic directly translates.
2. [Ellen MacArthur Foundation — Circular Economy Principles](https://www.ellenmacarthurfoundation.org/circular-economy-principles) — the three design principles that structure Loop's three circularity investments.
3. [Mongabay — The circular economy: Sustainable solutions to solve planetary overshoot?](https://news.mongabay.com/2023/07/the-circular-economy-sustainable-solutions-to-solve-planetary-overshoot/) — accessible journalism with a concrete example for the framing paragraph.
4. [PMC/NCBI — Waste metrics in the framework of circular economy](https://pmc.ncbi.nlm.nih.gov/articles/PMC10693739/) — a more academic treatment connecting overconsumption to circular economy metrics.

All four links verified live before merging.

## Audit fix — save-load robustness for circularity investment

Second-pass code-quality audit found `load_state()` doing a wholesale
`dict(data["circularity_investment"])` replace instead of merging
key-by-key against the current `CIRCULARITY_INVESTMENTS` schema — the
same shape of bug found and fixed in a few other games' save systems this
session. `render()` unconditionally reads
`chain.circularity_investment[measure]` for every measure currently in
`CIRCULARITY_INVESTMENTS`, so loading a snapshot missing one of those keys
(an older/hand-edited save, or one from a build with a different
measure set) would leave that key absent entirely and crash the very
next render with a `KeyError`. A stale key no longer in
`CIRCULARITY_INVESTMENTS` would also linger in the live dict forever.

**Fix:** `load_state()` now rebuilds `circularity_investment` as
`{measure: saved.get(measure, 0) for measure in CIRCULARITY_INVESTMENTS}`
— missing keys default to 0, unknown/retired keys are dropped. Covered by
two new tests in `tests/test_save_system.py`. No other issue (memory
leak, dead code, stale comment) turned up on this pass — `setup()` is the
only place `create_proxy()` is called, once at load, so there's no
per-render proxy leak here.

## Tech notes

- Python/Pyodide, per root conventions.
- Model the production chain as a graph/flow structure (nodes for extraction/manufacturing/use/disposal, with circularity investments adding new edges back into earlier stages) — this makes both the logic and the eventual visualization more natural than a flat meter-based approach.

## Working conventions

- Commit + tag per milestone: `git commit -m "Milestone N: <name>"` then `git tag loop-milestone-0N`.
- Update the milestone table Status as work happens.
