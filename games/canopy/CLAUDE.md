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

## Iteration Notes — Pass 2 (implemented)

Second design-review pass, from `climate-games-iteration-pass-2.md`, building on Pass 1. **Selected additions: A (biodiversity sub-meter) + B (stakeholder tension).**

- **Biodiversity sub-meter:** preserved and recovered plots accumulate a biodiversity value over time, separate from the passive economic value already tracked — represented simply (e.g. small wildlife icons appearing on well-established plots) rather than another number to read. Deepens the hope payoff: a thriving late-game forest isn't just economically valuable, it visibly has life in it.
- **Stakeholder tension:** periodically, the player faces a plot-specific decision where local community needs (a request to clear a specific plot for housing, farming, or resources) conflict with preservation. Not a trap or a "wrong answer" mechanic — meant to introduce real ethical weighing (whose need matters, short-term vs. long-term) rather than making preservation an obviously correct default choice every time.
- **Visual polish for this pass:** biodiversity should be legible at a glance (small animated wildlife sprites/icons on mature plots, subtle motion) without cluttering the plot grid. Stakeholder-tension moments should get a distinct visual treatment (a different UI panel or framing) so they read as a different kind of decision than routine plot management.

## Iteration Notes — Pass 3 (Fun/Teaching Balance)

Third design-review pass, from `climate-games-fun-teaching-balance.md`. **Risk:** the idle/passive accumulation side of the mechanic risks tipping toward boredom — if preserving a plot mostly means waiting, without active skill or decision-making, flow drops even though the "lesson" (restraint compounds) is technically still present.

**Assessment:** the *choice of which plot to clear and when* was already reasonably skill-based going into this pass — soil degradation punishes repeatedly clearing the same plot, compounding growth rewards patience but stakeholder tension specifically targets whichever plot is currently most established, so a player who understands the system has real reasons to selectively harvest rather than just wait uniformly. The actual gap was pacing: the two Pass 2 systems meant to break up idle stretches (stakeholder-tension requests, the biodiversity wildlife-icon payoff) weren't paced against each other. Stakeholder requests fired every 20 ticks, but the first biodiversity payoff (wildlife icon) didn't land until 50 ticks in — well after two stakeholder cycles had already passed — so the early game's only felt beat was the same grant/decline decision repeating, with nothing new arriving to reinforce that preservation itself was paying off.

**Built in response:** tightened both intervals so they land close together early rather than one at 20 ticks and the other at 50. `STAKEHOLDER_EVENT_INTERVAL_TICKS` dropped from 20 to 15. `BIODIVERSITY_WILDLIFE_THRESHOLD` dropped from 1.0 to 0.2 (accrual rate unchanged), so the first wildlife icon now appears around tick 11 instead of tick 50 — inside the first idle stretch instead of after it. No new mechanics added; this is timing/frequency tuning of what Pass 1/Pass 2 already built.

## Info Page — real-world sources (implemented)

An optional, player-triggered "The Real Story" panel — never forced mid-session, since the mechanic teaches first and this is a supplement for players who want to go deeper. Toggled via a button near the top of the page; shows a short framing paragraph (written fresh, not copied from any source), a one-line note tying the mechanic to real data, and a sources list with clickable links.

**Framing:** Standing forests are one of the world's largest active carbon sinks, and clearing them for quick income is one of the largest reversible sources of emissions — reversible because forests left alone, or given light assistance, can recover. Canopy's core tension, clear it now or let it compound, is a simplified stand-in for that real land-use tradeoff.

**Mechanic tie-in:** Canopy's replant-and-recover path loosely echoes real "assisted natural regeneration" — a genuinely cost-effective restoration approach, rather than costly full replanting from scratch.

**Sources:**
1. [World Resources Institute — Forests in the IPCC Special Report on Land Use: 7 Things to Know](https://www.wri.org/insights/forests-ipcc-special-report-land-use-7-things-know) — explains why deforestation and forest carbon sinks are two sides of the same coin, mapping directly to Canopy's clear/preserve tension.
2. [World Resources Institute — How Effective Is Land At Removing Carbon Pollution? The IPCC Weighs In](https://www.wri.org/insights/how-effective-land-removing-carbon-pollution-ipcc-weighs) — real reforestation carbon-removal potential, grounding the "replanting works, just slower" hope angle in actual IPCC figures.
3. [UNFCCC — Land Use, Land-Use Change and Forestry (LULUCF)](https://unfccc.int/topics/land-use/workstreams/land-use--land-use-change-and-forestry-lulucf) — the formal policy framework for tracking forest carbon sinks internationally.
4. [Climate Change Resources — Deforestation & Reforestation](https://climatechangeresources.org/learn-more/science/reforestation-deforestation/) — accessible overview with links to real reforestation organizations, for players who want to go from facts to action.

All four links verified live before merging.

## Audit Notes — Code-quality pass (implemented)

Site-wide bug/cleanup audit. Found one real bug: a pending stakeholder
request names its target plot by index, but nothing stopped the player
from selecting that same plot and clicking Clear directly instead of
using Grant/Decline. That left the request stale — Grant would hand out
its relations bonus for free (the plot was already BARE, so `clear()`
paid out nothing), Decline would penalize relations against a plot that
wasn't standing anymore, and since `maybe_trigger_stakeholder_request()`
refuses to raise a new request while one is already pending, the whole
stakeholder-tension system could get stuck indefinitely if the player
never happened to click Grant/Decline on the now-meaningless request.

**Fixed:** `grant_stakeholder_request()`/`decline_stakeholder_request()`
now check the target plot is still in an accruing state before applying
their relations delta, and `tick()` drops a request whose target is no
longer standing so a fresh one can still fire later. Everything else
audited clean — no other bugs, no convention violations (relative paths,
save-widget contract, test structure all check out).

## Audit Notes — Code-quality pass 2 (implemented)

Second, more aggressive audit pass covering minor/cosmetic issues as well
as bugs, per a hub-wide follow-up. Re-checked the stakeholder-request
guard from pass 1's fix for remaining edge cases (tick ordering around
recovery/accrual, save/load field handling) — found nothing further
there; `load_state()` already restores `plots` field-by-field onto the
existing `Plot` instances rather than replacing the list wholesale, so no
stale-reference risk exists for save/load.

**Found and fixed a real bug:** `render_grid()` rebuilds every plot tile
element from scratch on every `render()` call (at minimum once per tick,
i.e. once a second for the life of a session) and wired a fresh
`create_proxy(...)` click handler onto each one, but never `.destroy()`d
the previous render's proxies. Each `create_proxy()` call allocates a
persistent Python↔JS bridge object that Pyodide does not garbage-collect
on its own, so the old proxies leaked indefinitely even though the DOM
nodes they were attached to were long gone — a slow memory leak over a
long play session. Fixed by tracking each plot's current click proxy in
`_plot_click_proxies` and destroying the previous one before creating its
replacement each render. Covered by `tests/test_proxy_cleanup.py`.

**Also removed:** a dead `WILDLIFE_ICON` constant — the wildlife icon is
actually rendered via CSS (`.plot-has-wildlife::after`'s `content` in
style.css), so the Python constant was leftover and unused.

No other issues found worth changing; economy/scoring numbers were left
untouched per this pass's scope.

## Tech notes

- Python/Pyodide, per root conventions.
- Keep the plot grid as a simple 2D array of plot-state objects — straightforward to test and to render.

## Working conventions

- Commit + tag per milestone: `git commit -m "Milestone N: <name>"` then `git tag canopy-milestone-0N`.
- Update the milestone table Status as work happens.
