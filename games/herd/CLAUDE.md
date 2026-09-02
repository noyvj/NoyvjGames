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
| 2 | Coupled methane meter | Meter rises automatically tied to herd size/output. Tests: coupling-ratio calculation | Done |
| 3 | Decoupling measures | Feed/cap/capture investments that reduce the coupling ratio without requiring shrinkage. Tests: ratio-reduction formula per measure type | Done |
| 4 | Soft consequence system | Market/regulatory/yield pressure scaling with sustained high emissions, no hard fail-state. Tests: pressure-trigger thresholds | Done |
| 5 | Scoring + hope-angle payoff | Profitability-vs-emissions scoring that rewards decoupling as the best strategy, provably better than either pure-growth or pure-restraint. Tests: scoring formula across sample playthroughs | Done |
| 6 | In-game feedback prompt | Piped to Neon backend per root conventions | Done |
| 7 | Visual/UI pass + hub integration | | Done — all 7 milestones complete |

## Iteration Notes — Pass 1 (implemented)

Design-review pass (pre-playtest, from `climate-games-iteration-pass.md`). Anticipated issue: the core coupling ratio (growth scales emissions) is the whole lesson, but as pure math it risked being invisible — the tension needed to be felt, not just calculated.

**Built in response (see `BCM114-DEV-LOG.md` 2026-08-11):** a prominent coupling-ratio dial gauge as the single most prominent UI element, and an ambient haze overlay whose intensity tracks the methane meter. Methane's short-term-warming-vs-CO2 context blurb shipped as part of the cross-cutting context-blurb pass.

**Open testing question:** do players discover the decoupling strategy organically, or do they need a nudge? Do the soft consequences (market/yield pressure) feel like a meaningful signal without being punishing?

## Iteration Notes — Pass 2 (implemented — fallback path)

Second design-review pass, from `climate-games-iteration-pass-2.md`, building on Pass 1. **Selected addition: A (market dynamics) — conditional, with B (alternative protein pivot) as the fallback.**

- **Primary: market dynamics.** Fluctuating demand for meat/dairy output across rounds, affecting the profitability side of the growth-vs-emissions tension. Build this first and check its complexity/performance cost once implemented — if the fluctuation logic starts adding meaningful overhead or muddying the core coupling-ratio lesson, **fall back to alternative protein pivot instead** rather than pushing through.
- **Fallback: alternative protein pivot.** A distinct decoupling path where the player can shift part of production toward plant-based output — structurally different from the existing efficiency-measure decoupling (feed/caps/capture), since it changes *what* is produced rather than how efficiently the same thing is produced. Simpler to implement, so it's the safe fallback if market dynamics prove too heavy.
- **Visual polish for this pass:** whichever path is built, the core coupling-ratio gauge from Pass 1 remains the centerpiece — any new mechanic should feed visibly into that gauge rather than adding a competing, disconnected UI element.

**Built: the fallback (alternative protein pivot), not the primary.** Market dynamics is fundamentally an income-side mechanic (fluctuating price) — it has no natural way to move the coupling-ratio gauge, which this pass's own visual-polish note requires stay the centerpiece. Rather than force a fake connection between market price and coupling ratio, invoked the pre-approved conditional and built the pivot instead: it's structurally another decoupling lever (`plant_based_fraction()` blends directly into `coupling_ratio()` alongside feed/caps/capture), so it moves the same gauge the way the design intends. A plant-based-pivoted herd earns slightly less raw income per unit (a genuine cost, not a strict downgrade — the methane cut it buys also reduces pressure-driven income loss elsewhere).

## Info Page — real-world sources (implemented)

*Implementation is now shared across all 8 climate-quartet games — see `shared/info_page.py` and `shared/info-page.css`. Only the content below (framing/tie-in/sources) is game-specific; the rendering/toggle code moved out of this game's `game.py`.*

An optional, player-triggered "The Real Story" panel — never forced mid-session, since the mechanic teaches first and this is a supplement for players who want to go deeper. Toggled via a button near the top of the page; shows a short framing paragraph (written fresh, not copied from any source), a one-line note tying the mechanic to real data, and a sources list with clickable links.

**Framing:** Livestock digestion is a major, distinct source of methane — a gas that traps far more heat than CO2 in the short term, but also breaks down faster, which makes reducing it one of the fastest-acting climate levers available. Herd's coupling gauge and its plant-based pivot are built around that real reduction pathway.

**Mechanic tie-in:** Herd's plant-based pivot mechanic is grounded in a real documented case — a roughly 42% methane-intensity reduction achieved through better farm practices — showing decoupling herd size from methane is achievable, not hypothetical.

**Sources:**
1. [FAO — Livestock and enteric methane](https://www.fao.org/in-action/enteric-methane/en) — the definitive real-world figures behind Herd's core mechanic.
2. [Clean Air Task Force — Accelerating climate solutions in agriculture](https://www.catf.us/2024/10/accelerating-climate-solutions-agriculture-why-reducing-methane-livestock-urgent-opportunity/) — documents a real ~42% methane-intensity reduction, directly supporting Herd's decoupling hope angle.
3. [US EPA — Agriculture and Aquaculture: Food for Thought](https://www.epa.gov/snep/agriculture-and-aquaculture-food-thought) — explains why methane's short-lived-but-potent warming profile makes it a distinct lever from CO2.

All three links verified live before merging.

## Iteration Notes — Pass 3 (fun/teaching-balance audit — confirmed, no code changes)

Third design-review pass, from `climate-games-fun-teaching-balance.md`. **Risk:** if the emissions/decoupling system were tracked as a separate "sustainability score" bolted onto an otherwise-normal farm sim, this is close to a textbook chocolate-covered-broccoli setup — the player could optimize pure profitability while ignoring the score entirely. **Fix (framed as a confirmation/audit task, called "the single most important check for this game specifically"):** confirm the coupling-ratio mechanic feeds directly into the *same* profitability number the player is trying to maximize, not a parallel or optional metric.

**Traced the code, not just the docstrings.** `FarmState.score()` (game.py) is `self.funds - self.methane * METHANE_PENALTY_WEIGHT` — a single number, the only one shown as "Score" in the UI (`index.html`'s `score-display`), with no separate sustainability meter anywhere. `self.methane` accumulates every round via `advance_round()` from `methane_this_round()`, which is `self.herd_size * self.coupling_ratio()` — so `coupling_ratio()` (the mechanic Pass 1's gauge and Pass 2's plant-based pivot both feed) is load-bearing on `score()` through **two independent paths**, not one:
1. **Direct penalty term** — `score()`'s own subtraction, `methane * METHANE_PENALTY_WEIGHT`.
2. **Income-pressure path** — `advance_round()` multiplies raw income by `(1 - pressure_fraction())`, and `pressure_fraction()` is `min(MAX_PRESSURE, self.methane / PRESSURE_SCALE)` — so a higher coupling ratio drags down `funds` itself before the penalty term is even applied.

**Verified the effect isn't a token gesture.** Ran sample playthroughs (6 herd growth, 15 passive rounds, matching `test_scoring.py`'s existing scenario): decoupled growth (5x capture investment) scores 345.5 vs. pure growth's 262.2 at round 15, and the gap widens with more rounds (412.1 vs. 52.2 by round 50) — not a marginal edge, a strategy-defining one. A greedy pure-growth simulation that reinvests everything into herd size with zero decoupling collapses to a deeply negative score within ~20 rounds (income capped by `MAX_PRESSURE`, methane penalty uncapped), confirming ignoring the coupling ratio is never the optimal play, at any horizon.

**Conclusion: already satisfied, no code changes needed.** `coupling_ratio()` was never tracked as cosmetic — it was built in Milestone 5 (`METHANE_PENALTY_WEIGHT`, see Tech notes below) to feed the score directly, and Pass 1/2 additions (gauge, plant-based pivot) both route through the same function rather than adding a side metric. Added `tests/test_iteration_pass_3.py` to turn this audit into a permanent regression suite: isolates each of the two paths above (penalty term, income-pressure) independently of herd-growth cost, plus a same-herd-size playthrough comparison, so a future change that quietly severs coupling ratio from score would fail loudly instead of just being missed in review.

## Tech notes

- Python/Pyodide, per root conventions.
- Keep the coupling-ratio calculation as an isolated, clearly named function — it's the single mechanic the whole lesson depends on, so it needs to be easy to test in isolation and easy to explain in the Contextual Report Blog.

## Working conventions

- Commit + tag per milestone: `git commit -m "Milestone N: <name>"` then `git tag herd-milestone-0N`.
- Update the milestone table Status as work happens.
