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

## Achievements + improvement pass (Sep 2026)

Built the hub-wide achievements framework here as part of the site-wide rollout (`planning/ACHIEVEMENTS-SYSTEM-DESIGN.md`, SOL is the reference integration) plus `planning/TODO.md`'s Herd checklist (F1-F3, F5-F9, F11-F15, F17-F19 — F4/F10/F16/F20 stay parked in `LATER.md`), in one session:

- **Achievements**: 18 achievements (`achievements.json`) spanning herd growth, all three decoupling paths, the plant-based pivot, beating the pure-growth baseline, and round-count/score milestones. In-game panel (🏆 toggle) with live progress readouts, a separate unlock toast (distinct from the F5/F11/F17 milestone-nudge toast below so an achievement is never confused with a gameplay nudge), `achievements_earned` riding `get_state()`, and a link out to the hub-wide dashboard.
- **F1/F13 — pure-growth counterfactual**: `FarmState` tracks a parallel `counterfactual_funds`/`counterfactual_methane` path — same herd size every round, zero decoupling/plant-pivot investment ever applied — accumulated in `advance_round()` alongside the real numbers, so it survives save/load. Doubles as both the live comparison line (F1) and a persistent baseline-farm card (F13).
- **F3 — report card**: on-demand panel restating the counterfactual numbers with a fuller breakdown (funds/methane/score deltas, methane avoided, the F15 real-world line).
- **F2 — pasture visual**: the 5 fixed cow elements in the hero illustration reveal progressively at herd-size thresholds (1/3/6/10/15) rather than generating unbounded DOM nodes.
- **F5/F11/F17 — milestone-toast nudges**: a second toast type (not achievements) for three one-time callouts — 50% decoupled-below-baseline, pressure crossing 25% income loss, and methane's score-penalty crossing a fixed magnitude — each gated by a `seen_*` flag on `FarmState` that persists through save/load, same shape as Thaw's tipping-flash pattern.
- **F6 — rising growth cost**: `grow_herd_cost()` keeps the very first unit at the original flat price (so existing tests for a fresh farm are unaffected) and adds a fixed per-unit slope after that.
- **F7 — trend graph**: `methane_trend_graph_svg()`, an unlabeled inline-SVG polyline over `methane_history` (Thaw's mini-graph technique) — the point is the curve's shape, not any one round's exact value.
- **F8/F9/F14 — decoupling readouts**: a combined efficiency+plant-pivot message, a no-mutation preview of the next Grow Herd unit's cost/income/methane, and session-best/baseline range labels behind the coupling gauge.
- **F12 — worked example**: a concrete 10-herd/Capture-Systems numeric walkthrough added to the tutorial's Decoupling Investments step.
- **F15 — real-world comparison**: `real_world_comparison_message()` surfaces the same ~42% methane-intensity-reduction figure cited in the Info Page as a live in-session comparison.
- **F18 — community stat**: fetched client-side from the ratings backend in `index.html`, fails silently if the backend is unreachable (matches other games' aggregate-stat patterns).
- **F19 — investment feedback**: `_pulse()` toggles a short CSS animation class on a clicked control for a fixed duration.

All of the above are pure functions of state that already exists or state that follows the same save/load contract as everything else in `FarmState` — no separate hand-maintained "earned"/"seen" bookkeeping outside what's listed. Full suite: 125/125 (31 new achievement tests), no regressions.

## Colorblind-safety audit (site-wide goal)

Audited as part of the site-wide colorblind-safety audit (Okabe-Ito-palette method, per Continuum's Phase 5, Canopy's B9, Tide's D11, Grid's C18, Aftermath's own pass). The site-wide visual pass note above had already flagged one real candidate worth checking here: `GAUGE_LOW_COLOR`/`GAUGE_HIGH_COLOR` (`game.py`) — the coupling-ratio dial, this game's single most prominent UI element and "the mechanic the whole lesson depends on" per its own docstring — lerp green (`#4c9c6e`, fully decoupled) to red (`#e0674c`, fully coupled) as `coupling_gauge_svg()`'s `fraction` climbs. Continuous, not discrete, so the applicable method (per this audit's own instructions) would be Canopy's redundant-cue approach rather than Continuum's discrete-palette swap, if a fix were actually needed.

**Investigated and found already redundantly coded — no change made.** Unlike Canopy's original plot-tile gradient (color and *only* color, before B9's fix), this gauge was never color-alone to begin with:
1. **Spatial/length encoding, independent of hue.** `coupling_gauge_svg()` draws `.gauge-fill` as a `stroke-dasharray` partial arc (`dash = fraction * 100` of a `pathLength="100"` path) on top of an always-full-length dark `.gauge-track`. The fraction is directly readable from *how far the colored arc extends against the dark track*, exactly the way a plain progress-bar's fill width works — the same "position/width, not hue, carries the value" shape Continuum's and SOL's own audits found acceptable elsewhere.
2. **Text end-labels.** `index.html`'s `gauge-tick-label--low`/`--high` spell out "CLEAN" and "HIGH" in words at the two ends of the arc, not just in color.
3. **Always-visible numeric readout.** `render()` sets `#coupling-gauge-label` to "Emissions per herd unit: X methane/round" and `#coupling-display` to "Coupling ratio: X methane/herd/round" every frame, unconditionally (not behind a hover or a toggle) — the exact figure the gauge represents is on-screen in plain text at all times.

Three independent non-color cues (length, end-text, live numeric text) were already present before this audit started, which is a stronger redundancy bar than Tide's D11 precedent (texture + a hover tooltip) cleared. Re-picking the gradient's hues would only change which two colors are being lerped between — it wouldn't add any information a colorblind player doesn't already have from (1)-(3) above — so, per this task's own "don't invent a fix for a problem that doesn't exist" instruction, none was made. Also checked and found not a real pair: the milestone-nudge vs. achievement toasts (green vs. amber, two different one-at-a-time notification *types* with their own full text, never shown together) and the selection LED dot (`#5fbf7e` green vs. `#454b5c` neutral grey — on/off, not a red/green pair).

## Settings panel (site-wide goal, planning/TODO.md, origin A9)

A consolidated settings panel — text-scale (A-/A/A+ buttons, same clamp/step
shape as Continuum's Phase 5 `accessibility.js`, following Aftermath's own
`settings.js` build) and a reduced-motion checkbox — toggled from a new
"⚙️ Settings" button in the top toolbar alongside Tutorial/How to Play/
Achievements/Report Card, rendered into a `.section`-styled panel matching
the existing `#howto-panel`/`#achievements-panel` hidden-until-opened idiom.

Built as `settings.js`, deliberately independent of Pyodide entirely — it
has no Python dependency and works even if `game.py` never boots, and it's
wired up in `<head>` before `game.py`'s own `<script>` runs. `style.css`
gained a `:root { --text-scale: 1 }` custom property read by `html
{ font-size: calc(16px * var(--text-scale, 1)) }` (every font-size in this
file is already in rem, confirmed by grep) and a blanket
`html[data-reduced-motion="true"] *` override collapsing every
animation/transition to effectively instant, additive to the existing
`prefers-reduced-motion` media-query-gated rules already in this file (the
cow-graze/wisp-rise/meter-shimmer/invest-pulse animations and the gauge's
own transitions).

**Deliberately no sound toggle** — this hub has no audio system built
anywhere yet (`planning/LATER.md`'s standing "what can you actually do with
audio" question), so a sound control here would control nothing real.

Both settings are a browser-level UI preference, not game state — persisted
to `localStorage` (`herd-text-scale`, `herd-reduced-motion`), never touching
`get_state()`/`load_state()`.

Verified live via a local server on a fresh port (sidesteps an unrelated
browser heuristic-caching quirk in the dev-server setup, unrelated to this
game's own code): text-scale increases the whole page's font size correctly
(confirmed via computed `font-size` on `<html>`), the reduced-motion
checkbox collapses the methane meter's `transition-duration` to ~0, and
both settings persist correctly across a full page reload. Zero new console
errors — the pre-existing ServiceWorker-registration quirk and a CORS error
from the unrelated community-stat fetch (an artifact of testing against a
non-whitelisted localhost port, not this change) are both already present
on the unmodified page. Full pytest suite (125 tests, unchanged —
`settings.js` is plain frontend JS with no Python surface) stayed green
throughout.

## Shared confirmation-dialog integration (F16, site-wide goal)

Investing in the Plant-Based Pivot now routes through
`shared/confirm-dialog.js`'s `ConfirmDialog.ask()` instead of investing
immediately (`on_invest_plant_pivot()` in `game.py`). It's the pricier of
the two decoupling investments (25, vs. 15/20/20 for feed/caps/capture)
and, unlike those three, changes *what* the herd produces rather than
just how efficiently -- the shared pattern's pre-action-confirm shape
(not an undo window; the shared file only supports confirm-before, per
its own header doc), with the built-in "don't ask again" checkbox
covering the "won't this get annoying on repeat clicks" concern this
task originated from. Covered by 3 new tests in
`tests/test_confirm_dialog.py` (fake `js.window.ConfirmDialog`, same
technique as Grid's C14 integration -- the real fake-DOM harness's `js`
module never provides `window` by default).

Live-verified in a real browser (after Grid's session had already found
and fixed a real bug in `shared/confirm-dialog.js` itself -- see that
file's header comment and Grid's own CLAUDE.md note): clicked
Plant-Based Pivot -> dialog appeared with the correct message and an
"Invest" confirm label; Cancel left funds/investment count untouched; a
second click -> checked "don't ask me again" -> Invest -> investment
landed and the skip flag persisted to `localStorage`; a third click
skipped the dialog entirely and invested immediately as expected. Zero
new console errors during the verified flow. Full 128/128 pytest suite
(125 existing + 3 new) unaffected.

## "What's New" changelog panel (K16, planning/TODO.md, site-wide goal)

A small in-game highlights panel — a curated `changelog.json` (flat list of
`{"date", "entry"}` objects, fetched into the Pyodide boot sequence exactly
like `achievements.json` already is) rendered into a hidden-until-opened
"📋 What's New" panel — same toggle+panel idiom as the achievements/report-
card panels, with a plain date+text-card layout (no earned/unearned styling,
since a changelog entry has no checkable condition). `CHANGELOG` is sorted
newest-first at load time and degrades to an empty list on a
malformed/missing file, matching `ACHIEVEMENTS`'s own defensive pattern.

Populated with 10 real highlight entries pulled from this file's own
milestone table and iteration notes above, dates cross-checked against
`git log` for this game's path. Covered by `tests/test_changelog.py`
(catalog sanity, newest-first ordering, toggle open/close, panel content,
no state mutation as a side effect). Full pytest suite (128 → 137 tests)
stayed green throughout; verified live via a local server — the panel
opens, shows all 10 real entries in the correct order, and there are zero
console errors.

## Onboarding-tooltip coverage check (site-wide goal, planning/TODO.md, origin A14)

Audited, no change needed. Checked whether a returning player who's
forgotten the tutorial can still make sense of the permanent UI's
non-obvious parts, on top of the persistent, reachable-any-time
`#howto-toggle-button`/`#howto-panel`.

Found the permanent UI already covers every non-obvious mechanic, at
multiple redundant layers, matching Aftermath's own "no gap found" audit:
- Six section-level `.info-toggle` icons permanently explain the coupling
  gauge's "per-unit, not total" scope, the pressure formula's
  never-resets/80%-cap behavior, the score formula (funds minus a
  methane penalty, not just funds), the baseline-farm counterfactual's
  exact comparison rules, the three efficiency measures' additive
  stacking (with a floor), and the plant-based pivot's separate-lever/
  60%-cap/income tradeoff.
- Every investment button (`Grow Herd (N)`, each decoupling measure, the
  plant-based pivot) shows its live cost inline in its own label, per
  `render()` in `game.py` — never a bare unlabeled action.
- The coupling gauge itself (this game's single most prominent element)
  is already triple-redundantly coded per the earlier colorblind-safety
  audit above: arc length against a dark track, "CLEAN"/"HIGH" text
  labels, and an always-visible numeric readout — none of that is
  gated behind hover or a one-time callout.
- The tutorial's Decoupling Investments step already carries a concrete
  worked numeric example (F12), and the Plant-Based Pivot's
  confirm-dialog (F16) restates its own tradeoff at the moment of
  investment, on top of the permanent info-toggle covering the same
  ground.

No gaps found; nothing added. Full 137/137 pytest suite unaffected (no
code changed).

## Tech notes

- Python/Pyodide, per root conventions.
- Keep the coupling-ratio calculation as an isolated, clearly named function — it's the single mechanic the whole lesson depends on, so it needs to be easy to test in isolation and easy to explain in the Contextual Report Blog.
- **Site-wide visual pass (Sep 2026):** adopted the shared `ambient-bg.css` background system, using its `--pastoral` theme (warm gold/green farmland motes and blobs) — a space starfield doesn't fit a farm game, so each game gets a theme matching its own subject rather than one look site-wide (SOL and Trade Empire are the two games where an actual starfield fits). Re-skinned this game's own chrome to match — `#game` and every `.section` block became translucent glass panels (gradient background, violet-tinted border, `backdrop-filter` blur, soft shadow), flat gray borders/dividers switched to the shared `rgba(140, 160, 255, 0.12–0.18)` tint, `button.secondary`/`button.primary` moved from flat fills to two-stop gradients with a glossy inset highlight and a `brightness(1.1)` hover (existing `:active`/`:disabled`/`.selected` states re-skinned in place, not renamed), the methane meter fill got a matching-hue glow, and the `<h1>` got the same gradient-clip-text treatment as SOL/the hub. Explicitly left untouched: the coupling-ratio gauge's own color logic (`GAUGE_LOW_COLOR`/`GAUGE_HIGH_COLOR`, `_lerp_color`, `.gauge-track`/`.gauge-fill` in `style.css`) and the haze-overlay's color, since both encode live game state, not chrome. No CSS class/id names changed, no `game.py` logic touched, no motion/transitions added beyond what already existed (`tests/` has no no-animation constraint for this game — unlike some other climate-quartet titles — so the pre-existing `filter`/`width`/`opacity` transitions were left as they were). Full pytest suite (93 tests) green before and after.

## Working conventions

- Commit + tag per milestone: `git commit -m "Milestone N: <name>"` then `git tag herd-milestone-0N`.
- Update the milestone table Status as work happens.
