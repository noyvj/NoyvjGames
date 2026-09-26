# Herd — Industrial Agriculture & Methane Game

**Built following the shared conventions in `planning/archive/climate-quartet-2-plan.md`** (moved there 2026-09-22 once all four second-set games shipped; was `climate-quartet-2-plan.md` at the games root while build order still mattered). This file is Herd-specific only. Built first of the second set — the simplest, closest in shape to Grid/Canopy from the original four.

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


## Reset-to-default settings button (Z-extra/A26, site-wide goal)

A "Reset to Default" button (`#settings-reset-button`) sits at the bottom of the settings panel, below the existing text-size and reduce-motion controls -- SOL's own A26 answer flagged this as a site-wide pattern rather than a SOL-only feature, folded into `planning/TODO.md`'s Z-extra checklist. Implemented entirely in `settings.js` (no Python touched, matching this file's own "deliberately independent of Pyodide" rule for the rest of the settings panel): one click calls `applyScale(DEFAULT_SCALE)` and `applyMotion(false)`, updates `--text-scale`/`data-text-scale`/`data-reduced-motion` on the live DOM immediately, resets the reduce-motion checkbox's own `checked` state to match, and writes both defaults back to `localStorage` so the reset survives a reload rather than only looking reset until the next render. No confirmation dialog -- this is a low-stakes, instantly-reversible display preference, not a destructive action, so `shared/confirm-dialog.js` is deliberately not wired up here.

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

## UI decluttering pass (site-wide goal, planning/TODO.md closing task)

Audited the single-page layout for the "everything looks very crowded" concern (the user's own framing) against the established `<details>`-disclosure fix pattern (Tide's `.ticker-history-toggle`, this game's own `.info-toggle` badges). Walked every always-visible block top to bottom: the toolbar's five panels (`#howto-panel`/`#achievements-panel`/`#report-card-panel`/`#changelog-panel`/`#settings-panel`) are already hidden-until-opened; `#gauge-section` and `#status` are the core every-round readouts and already lean on `.info-toggle` for their own explanatory text; `#decoupling`/`#plant-pivot`/`#actions` are the core investment controls, checked every round; the pasture visual is `aria-hidden` art, not text stacking.

**Found one real offender:** `#baseline-farm-card` (F13's persistent pure-growth-counterfactual card) rendered a full always-visible breakdown — heading, four raw stat lines (`#baseline-herd-display`/`#baseline-funds-display`/`#baseline-methane-display`/`#baseline-score-display`), the live comparison sentence, and an info-toggle — even though F3's on-demand Report Card panel (`report_card_html()` in `game.py`) already restates those same three numbers (score/methane/funds vs. baseline) in full sentence form, on demand. The always-expanded raw numbers here were duplicating a feature this game already built to solve exactly this problem. **Fix:** kept the heading and the live `#counterfactual-comparison-display` sentence visible (the one line worth seeing every round without a click, matching F1's "live comparison" intent), and wrapped the four raw stat lines in a new `<details class="baseline-stats-toggle"><summary>Show baseline numbers</summary>...</details>`, collapsed by default. Pure HTML/CSS move — every id `game.py`'s `render()` writes to (`baseline-herd-display` etc.) is unchanged and unaffected by the collapsed state (confirmed no code toggles `#baseline-farm-card`'s or the new `<details>`'s own hidden/open attribute), and the existing `.info-toggle` explaining the comparison's rules was left in place after it. Added matching `.baseline-stats-toggle` CSS (small text-link-style summary with a `▸`/`▾` marker, same understated tone as `.info-toggle`) to `style.css`. Full pytest suite (137/137) unaffected, as expected for a pure layout change.

## Round-2 improvement pass (2026-09-20)

Built from `planning/TODO.md`'s Herd F-list (137 -> 153 tests, `tests/test_round2_features.py`):
F2 herd-size overlay on the pasture; F4 half-decoupled toast now defines "decoupled" in plain terms; F6 report-card percentage vs baseline (`beat_percentage_message()`); F11 sustainable certification (5 rounds at ratio <= 0.5 gives a permanent +10% income premium; `certification_streak`/`certified` saved, old saves default safely; baseline never gets it); F12 exact income tradeoff in the pivot confirm; F14 congratulation once the 42% real benchmark is beaten; F16 methane graph pulses when a round adds less than the last; F18 before -> after arrows in the Grow preview; F22 gauge range label pulses on a new best; F24 info toggle explaining haze; F26 icon investment summary in the report card with the pivot marked a separate lever; F30 wisps fade with coupling ratio and vanish at 90% decoupled. F28 audited: the How to Play panel already renders every tutorial step including the worked example. F8 skipped at the time: a *session*-scoped record marker would always equal the current value, since the ratio only ever falls within one session -- see the dedicated "F8 — record decoupling ratio marker" note below for the cross-session (per-browser, localStorage) version actually built later, which doesn't have that redundancy problem.
Left: F1, F3, F5, F7/F10/F21 (community, would need Z1 fields that don't fit), F9, F13, F15, F17, F19, F23/F25 (large), F27, F29.

## F8 — record decoupling ratio marker on the coupling gauge (2026-09-21)

`planning/TODO.md`'s Herd checklist carried one leftover item from the
Round-2 pass above: "F8: A small 'record decoupling ratio' marker on the
coupling gauge, like Grid's best-round marker." The Round-2 pass note
itself had explicitly *skipped* an earlier reading of this same idea --
"the ratio only ever falls, so a 'record' marker would always equal the
current value" -- and that reasoning is still correct for a *session*-
scoped record: `coupling_ratio()` never rises within one session
(decoupling/pivot investment counts only ever go up), so `#gauge-range-
display`'s existing "Session best: X | Baseline: Y" line already covers
that axis and a second copy of it would be exactly the redundant marker
the earlier pass rightly declined to build.

What makes the TODO item non-redundant is a different axis entirely: the
best ratio this **browser** has ever reached, **across every session**,
via `localStorage` -- the same per-browser "personal best" pattern this
hub already uses elsewhere (Canopy's `personal_best`, Tide's
`best_coastline_saved`, Thaw's G19). A fresh session always starts back
at `BASE_COUPLING_RATIO` (1.0), so once a player has played this game
before on this browser, "best ever" and "the current session's value"
genuinely diverge -- that divergence is exactly what makes a persistent
marker worth drawing.

**Built:**
- `_read_local_storage_item()`/`_write_local_storage_item()` (`game.py`)
  -- byte-for-byte the same lazy-`import js`/broad-except shape every
  other game's equivalent pair uses, so a real browser refusing
  localStorage access (private browsing) degrades to "no record" instead
  of crashing the module.
- `load_record_coupling_ratio()` / module-level `record_coupling_ratio`
  -- unlike Tide's `best_coastline_saved` (where 0.0 is a safe "nothing
  recorded" default because higher is better), lower is better here and
  both `BASE_COUPLING_RATIO` (1.0) and `MIN_COUPLING_RATIO` (0.1) are
  real, reachable ratios -- so the "no record yet" sentinel is `None`,
  not a number.
- `_maybe_update_record_coupling_ratio()`, called every `render()`: only
  writes a new record when `farm.coupling_ratio()` drops **below
  baseline** (not just below the previous record) -- a fresh,
  never-decoupled farm sitting exactly at `BASE_COUPLING_RATIO` is the
  starting point, not an achievement, and without this guard every brand
  -new browser would silently "record" 1.0 on its very first render,
  defeating the "marker only appears once a real record exists"
  requirement.
- `coupling_gauge_svg()` gained an optional `record_ratio` parameter and
  a new `_gauge_point(fraction)` helper (shared geometry so the live
  `.gauge-fill` arc and the record diamond agree on the exact same
  semicircle math) -- when a record exists, a small `<polygon>` diamond
  (`.gauge-record-marker`, gold `#e0c24c`, matching the shared
  `personal-best.css` medal color) is drawn on the arc at the record's
  position, carrying its own `<title>` tooltip. Same "shape, not just
  color" technique as Grid's own best-round diamond on its trend graph.
- `render_record_coupling_ratio()` / `#coupling-gauge-record-display`
  (`index.html`, styled via the shared `shared/personal-best.css`
  `.personal-best-display`/`.just-improved` classes, newly linked into
  this page) -- a small persistent label beside `#gauge-range-display`,
  hidden entirely until a record exists, briefly pulsing gold the moment
  a new one is set (`_flash_record_coupling_ratio_badge()`, same
  setTimeout+create_proxy shape as Canopy/Tide's equivalent).
- Deliberately **not** part of `get_state()`/`load_state()` -- same
  distinction Canopy's B14/Tide's D13/Thaw's G19 draw: this is a
  per-browser device record across every session/save, not one save's
  snapshot, so loading someone else's save code must never overwrite it.

Tests: 137 -> 167 in this pass overall (F8 alone: 15 new tests in
`tests/test_record_coupling_ratio.py`), covering: no record on a brand
-new browser and the marker/label staying absent until one exists; the
first qualifying investment setting a record; the marker's diamond
position and the label's stated value updating on each new (lower) best;
the record staying byte-for-byte unchanged (identical gauge SVG, no
`localStorage` write) across a re-render with no state change; advancing
rounds alone (which grows accumulated methane but never moves
`coupling_ratio()` itself) never creating a spurious record; and the
core cross-session contract, that a record written by one module load is
picked back up by the very next one against the same `localStorage` --
required adding a `FakeLocalStorage` (`tests/fakes.py`, copied from
Canopy/Tide's own fake) and a `GameEnv.reload()` helper
(`tests/conftest.py`) that re-execs a fresh `game.py` against the same
fake storage, since this test harness had never needed either before.

Verified live via `hub-dev-server`: hit this sandbox's own well
-documented static-asset-caching quirk (several other games' build notes
above already describe it) where the boot script's own `fetch("game.py")`
call keeps resolving to a stale cached response regardless of the outer
page URL being cache-busted -- worked around the same way those notes
do, by forcing a fresh `cache: "no-store"` fetch of `game.py` and
re-running it through the already-booted `pyodide` instance. With fresh
code loaded: a brand-new browser (no `localStorage` entry) showed no
marker and a hidden label; investing in Capture Systems immediately drew
the diamond at the correct arc position and un-hid the label reading
"Best ever (this browser): 0.90 methane/herd/round"; a second investment
moved the diamond and updated the label to 0.80; and a full page
navigation picked the 0.80 record straight back up from `localStorage`
on a fresh farm sitting at baseline, with the marker visible immediately
and zero console errors throughout. (This session's screenshot tool
itself hit an unrelated rendering glitch — a solid-black band over the
upper portion of some mid-scroll captures on this page, reproducible
regardless of code changes and inconsistent with the DOM/accessibility
-tree reads taken at the same moments, which were correct throughout —
noted here as a tool quirk, not a defect in the shipped code.)

## F7 — "farm cooperative" community comparison (2026-09-21)

`planning/TODO.md`'s Per-game: Herd section: "F7: A 'farm cooperative'
comparison — aggregate stats on community-wide methane-per-unit avoided
*(needs Z1 for a first pass ... ship the Z1-backed version now, expand
later)*." Z1's shared aggregate-stats backend (`app/stats.py`,
`app/main.py`) is built and deployed, and Herd is already registered in
its `STATS_FIELDS` whitelist (`round_number`, `funds`, `herd_size`,
`methane`).

Built byte-for-byte the same optional-hook architecture as Grid's own
C15 (`_request_comparison()`/`window.gridCompare`, the reference
integration for this feature in this hub): `game.py`'s
`_request_comparison()` does a lazy, guarded `from js import window`
(no-op under pytest, where `js.window` doesn't exist by default) and
calls `window.herdCompare(methane, round_number)` if that hook exists;
`index.html`'s own inline `<script>` defines the hook, does the real
`fetch()` against `GET /stats/games/herd/percentile?field=methane&value=
<x>`, and fills `#report-card-compare` with a plain-English sentence —
or leaves `game.py`'s own fallback text ("Comparison with other farms
isn't available yet.") in place on any error, an unreachable backend, or
the endpoint's own `suppressed` flag (too few saves to compare against
without risking identifying anyone).

**Metric chosen: `methane` (lifetime accumulated methane), not a raw
coupling ratio.** `coupling_ratio()` is a live per-round rate with no
save-state field of its own, so it isn't one of the numeric paths
`app/stats.py`'s whitelist can rank — the single-field `/percentile`
endpoint needs an actual `get_state()` field. `methane` is the closest
honest stand-in: it's the direct cumulative output of `coupling_ratio()
x herd_size` every round (`methane_this_round()`), so two farms at a
similar round/herd_size mostly diverge on lifetime methane by how well
they've actually decoupled — the same relationship Grid's own
`emissions` field has to its own cost-curve mechanic, just measured
cumulatively rather than as a live rate. Framed to the player as
"your lifetime methane is lower than N% of them" (lower is better, same
polarity as the rest of this game's own framing) rather than a bare
percentile number.

Surfaces inside the existing F3 report-card panel (`#report-card-compare`,
a new line appended after the existing summary lines in
`report_card_html()`), asked for once when the panel opens and re-asked
on every subsequent render while it stays open — same "ask again each
render, let the JS side cache/dedupe by rounded value" pattern C15 uses,
so repeatedly re-opening the panel at the same methane total doesn't
hammer the endpoint.

Tests: `tests/test_community_comparison.py` (7 new, Herd 167 -> 174) —
mirrors Grid's own C15 test coverage exactly (fallback text present
before any hook runs, safe no-op with no `js.window` at all, the hook
firing with the right `(methane, round_number)` pair once installed,
re-asking on a later render while the panel stays open, never asking
while the panel is closed, and the fallback constant matching the
panel's own text) — the real `fetch()` itself can't be exercised from
Python tests, same limitation Grid's own suite has for this feature.
flake8 clean.

Verified live against the shared `hub-dev-server`: opened the report
card and confirmed `#report-card-compare` correctly holds the fallback
text with zero console errors, and confirmed `window.herdCompare` is
defined and callable. The actual round-trip to the deployed production
endpoint (`https://noyvjgames.fastapicloud.dev`) could not be exercised
in this sandboxed browser pane specifically — an external `fetch()` to
that host never resolved or errored within this session's tooling (no
request even appears in the network log), a sandbox network limitation
rather than a code defect, consistent with the AdSense/CSP network
quirks other games' build notes in this repo already document for the
same environment. The `.catch()` path this leaves untested live is
already covered by the fallback-text tests above, and functionally an
unreachable/never-resolving backend and a genuinely-down one produce
the identical player-visible result: the fallback text stays put.

## Round-3 Herd mechanics (2026-09-21)

Built from `planning/TODO.md`'s Herd F-list (174 -> 191 tests, `tests/test_round3_features.py`). New UI lives in one collapsed `#farm-extras` panel (plus a hidden `#policy-panel` and `#poultry-panel`), so the main screen is not re-crowded; all new state is validated and defaulted in `load_state()`.
- **F23 poultry:** unlocked by sustainable certification (the game's prestige). Own base ratio 0.3 (methane-equivalent; real poultry emissions are mostly manure N2O/ammonia), two own levers (litter, biofilters), housing upkeep, counterfactual includes it at base ratio.
- **F5 breeding:** fourth lever that matures after 3 rounds. **F13 supply chain:** up to +30% income. **F15 welfare:** feed/caps/breeding raise it, up to +10% income.
- **F9/F3 (opt-in):** deterministic season income swings and plant-based demand surges; applied to the baseline farm too. **F19 (opt-in):** regional cap of 20 methane/round blocks growth. **F27:** policy advisor every 8 rounds (30% subsidy for 5 rounds or +40 funds). **F17:** farm-tour vignettes by coupling band.
- **F29:** researched (see `planning/FOR-YOU.md`): real farms sell biogas/RNG and credits, so built as surplus-capture biogas sales (first 2 capture units are on-farm use).
- Not done: F1 (satellite farm), F25 (succession), F10/F21 (need community stats the backend cannot support).
- Live-verified: the panel's `innerText` reads empty while the `<details>` is closed (use `textContent`); zero console errors.

## Tech notes

- Python/Pyodide, per root conventions.
- Keep the coupling-ratio calculation as an isolated, clearly named function — it's the single mechanic the whole lesson depends on, so it needs to be easy to test in isolation and easy to explain in the Contextual Report Blog.
- **Site-wide visual pass (Sep 2026):** adopted the shared `ambient-bg.css` background system, using its `--pastoral` theme (warm gold/green farmland motes and blobs) — a space starfield doesn't fit a farm game, so each game gets a theme matching its own subject rather than one look site-wide (SOL and Trade Empire are the two games where an actual starfield fits). Re-skinned this game's own chrome to match — `#game` and every `.section` block became translucent glass panels (gradient background, violet-tinted border, `backdrop-filter` blur, soft shadow), flat gray borders/dividers switched to the shared `rgba(140, 160, 255, 0.12–0.18)` tint, `button.secondary`/`button.primary` moved from flat fills to two-stop gradients with a glossy inset highlight and a `brightness(1.1)` hover (existing `:active`/`:disabled`/`.selected` states re-skinned in place, not renamed), the methane meter fill got a matching-hue glow, and the `<h1>` got the same gradient-clip-text treatment as SOL/the hub. Explicitly left untouched: the coupling-ratio gauge's own color logic (`GAUGE_LOW_COLOR`/`GAUGE_HIGH_COLOR`, `_lerp_color`, `.gauge-track`/`.gauge-fill` in `style.css`) and the haze-overlay's color, since both encode live game state, not chrome. No CSS class/id names changed, no `game.py` logic touched, no motion/transitions added beyond what already existed (`tests/` has no no-animation constraint for this game — unlike some other climate-quartet titles — so the pre-existing `filter`/`width`/`opacity` transitions were left as they were). Full pytest suite (93 tests) green before and after.

## Hidden-panel display bug fix (2026-09-21)

Found during a site-wide sweep after Aftermath's own Z12/panel-hiding
fixes surfaced the same pattern elsewhere: the achievements/changelog panels (`.achievements-panel`/`.changelog-panel`) set `display:
grid` as a plain class rule with no `[hidden]` override. Author-origin
CSS always beats the browser's own `[hidden] { display: none }` UA rule
regardless of specificity, so once that class applied, the panel stayed
visible as an empty box before its first open, and stayed visible with
its last-rendered content forever after being toggled closed. Fixed by
adding a `.<class>[hidden] { display: none; }` override right after each
affected rule, the same pattern SOL/Trade Empire/Continuum's own
achievements CSS already used correctly. CSS-only; no Python change
needed. Full test suite green, unaffected (pure CSS change).

## Working conventions

- Commit + tag per milestone: `git commit -m "Milestone N: <name>"` then `git tag herd-milestone-0N`.
- Update the milestone table Status as work happens.
## Screen-reader accessibility audit (Z15, site-wide goal, planning/TODO.md)

Static-analysis audit (grepping/reading `index.html`/`game.py`, no live screen
reader in this environment — same audit-only method the colorblind-safety
passes already established for this hub) of the achievements and settings
panels: toggle-button accessible names, panel role/heading semantics, focus
order on open/close, keyboard reachability of interactive elements, and
checkbox/label association.

**No real gap found — no change made.** Checked against the same candidate
list as every other game in this pass:
- Both toggle buttons (`#achievements-toggle-button`, `#settings-toggle-button`)
  already carry descriptive visible text, a sufficient accessible name on its
  own — no `aria-label` needed.
- The settings panel's own title is already a real `<h2 class="settings-panel-heading">`
  (this game was already ahead of four sibling games in this hub that had it
  as a plain, heading-nav-invisible `<p>` — fixed there this same pass), so
  it's already reachable via a screen reader's heading-navigation mode.
- The achievements panel itself has no heading of its own, but is adequately
  labeled by the toggle button's own visible text immediately above it — the
  same "plain semantic markup is enough" call this hub's colorblind-safety
  audits already made for comparable cases.
- No focus-trap exists anywhere in this hub, and none was warranted here:
  clicking the toggle button never moves focus itself, so it naturally stays
  on that same button when the panel opens or closes.
- Every interactive element inside both panels is a real `<button>`/`<input>`
  (confirmed via a site-wide grep for `.onclick =` assignments and
  `createElement("div")` calls with a wired click handler — none found).
- The reduced-motion checkbox is properly associated with its label
  (`<label class="settings-checkbox-label" for="reduced-motion-checkbox">`
  wrapping the input).

No code changed; ran as the baseline check this pass calls for regardless
of verdict.

## Print-friendly summary (Z21, site-wide goal)

`planning/TODO.md`'s Z21: a shared `media="print"` stylesheet
(`shared/print-summary.css`) so printing the page while a game's
end-of-session summary is open produces a clean paper page instead of the
site's dark space theme (which prints as blank/near-blank on most
printers) plus a pointless copy of the nav/ad bar/toolbar/starfield. The
shared file works off one convention: whatever element the game's own
summary lives in gets a `print-summary` class, and the stylesheet hides
everything else on the page (`body * { visibility: hidden }`, then
un-hides `.print-summary` and its descendants), strips
gradients/glow/`backdrop-filter` in favor of plain dark-on-white, hides
any buttons/inputs inside the summary itself, forces open any collapsed
`<details>`, and adds `page-break-inside: avoid` on the summary's own
direct-child blocks.

**Applied here:** `index.html` gained
`<link rel="stylesheet" href="../../shared/print-summary.css" media="print">`
right after the existing `ad-bar.css` link, and `#report-card-panel` (F3's
on-demand end-of-session Report Card — the `report_card_html()`
breakdown plus the F7 community-comparison line) gained the
`print-summary` class alongside its existing `section report-card-panel`
classes. `game.py` only ever sets this panel's `innerHTML` (never its
class list), so the new class survives every re-render. Purely additive:
`media="print"` never applies on-screen, and no `game.py`/on-screen markup
changed.

**Verification method used:** this sandbox has no print-to-PDF affordance,
so per this task's own guidance, verification was done by confirming the
stylesheet loads with `media="print"` and that its selectors have real
targets in the live DOM, rather than a literal print render — same method
as Canopy's Z21 pass (see that game's CLAUDE.md for the detailed
DOM-selector checks run against a structurally similar panel).
`python3 -m pytest games/herd/tests -q` stayed at 191/191 (pure HTML
class/link addition, no Python touched).

## 320px mobile-viewport audit (Z18, site-wide goal, planning/TODO.md)

Checked at a genuine 320px viewport (narrower than the original 375px
mobile pass) via the Claude Browser tool's `resize_window`: tutorial,
Achievements, Settings panels, plus a full-DOM `scrollWidth`/`clientWidth`
sweep. Audited, no change needed — `document.documentElement.scrollWidth`
never exceeded 320 in any state checked. Herd has no shared `mobile-dock.js`
integration (unlike Canopy/Grid/Tide/Aftermath/Trade Empire/Le Champ de
Mots), so there was no docked-button width case to check here, and its top
status bar (Funds/Herd size/Methane) is short enough to fit without the
`overflow-x: auto` HUD-strip pattern several other games in this hub use.

## Difficulty-aware achievements audit (Z27, site-wide goal)

Herd has two opt-in toggles: F9/F3's "market & weather variation"
(`variation_enabled`) and F19's regional methane cap (`regional_cap_
enabled`).

**Variation** applies a deterministic, symmetric per-round income modifier
(`SEASONS`, -10% to +10%, mean zero) plus an occasional plant-based-income
demand surge that is strictly a bonus (`DEMAND_SURGE_PLANT_INCOME_
MULTIPLIER` 1.05 vs. the base 0.85 multiplier — surge can only ever raise
plant income, never lower it). Neither touches `methane` or `pressure_
fraction()` at all — confirmed by reading `pressure_fraction()`, which is
a pure function of `self.methane` — so `clean_operator` (the one
achievement built directly around pressure) is completely unaffected.
Every score-threshold achievement (`score_400`, `decoupling_dividend`,
etc.) can only be nudged by a small, mean-zero, deterministic swing, never
pushed out of reach.

**The regional cap** blocks herd/poultry growth once projected methane
would exceed `REGIONAL_CAP` — this looked like a real candidate for
blocking `major_operation` (herd size 25) or `score_400`, since it
directly gates growth. But the cap is on METHANE, not herd size, and
decoupling investment (Feed Additives/Herd Caps/Capture Systems) reduces
the methane-per-herd-unit ratio by up to 90% (`fully_decoupled`) — so the
cap doesn't remove any achievement's reachability, it just requires
decoupling investment to happen BEFORE further herd growth rather than
after. That ordering requirement is, if anything, the core lesson the
whole game is built to teach (coupling ratio vs. growth), not a bug the
toggle introduces.

**No change needed.** No code touched; `flake8`/tests unaffected.

## Achievement-progress bar in toolbar (Z-extra/A10, site-wide goal)

Already satisfied — see the existing toggle-button label. `#achievements-
toggle-button`'s `innerText` already reads `"🏆 Achievements (N/M)"` via
`update_achievements_display()`, called from the main render loop, so the
live earned/total count is visible in the toolbar before the panel is
ever opened. No code change needed here.

## "What's new since you played" banner (Z24, site-wide goal)

A new shared `shared/whats-new-banner.js` -- deliberately distinct from
this game's own in-game "What's New" changelog PANEL above (opt-in,
player-triggered, always shows the full history from scratch). The
banner instead appears automatically on page load, but ONLY for a
RETURNING player who has missed real entries since their last visit: it
diffs this game's `changelog.json` against
`localStorage["whats-new-seen:herd"]` (the date string of the newest
entry already shown) and lists just the new ones, not the whole log. A
first-ever visit silently marks the current changelog as seen rather
than dumping the full history on a brand-new player. Reuses the same
`window.CHANGELOG_JSON` global this game's own changelog panel already
fetches -- no second network request. One `<script
src="../../shared/whats-new-banner.js" data-game-id="herd">` include,
added right after `shared/last-played.js`'s own include. See root
`CLAUDE.md`'s Working notes for the full write-up -- shared
infrastructure, documented once there rather than duplicated across all
12 games' own files.

## Keyboard-shortcut convention: ?/Esc (Z4, site-wide goal)

Wired via the new shared `shared/keyboard-shortcuts.js` -- one script
include plus one `KeyboardShortcuts.init({panels: [...]})` call at the
end of `index.html`, listing this game's real toggle-button + hidden-
panel pairs: How to Play, Achievements, Report Card, What's New,
Settings, and the Info Page. `?` opens a small floating shortcuts-help
overlay; `Esc` closes it and clicks the toggle button of whichever listed
panel is currently open, reusing each panel's own open/close logic. The
policy panel and the poultry panel aren't in the list -- both are shown
by game state (a pending offer, an unlock), not a player-clicked toggle
button.

## Comparison/benchmark chart migrated to shared component (Z17, site-wide goal)

F15's real-world comparison previously had a text sentence only
(`real_world_comparison_message()`) and no chart at all. `planning/TODO.md`'s
Z17 asked for exactly this: F7 (the "farm cooperative" live-percentile
comparison, `window.herdCompare`) was considered as the migration target
too, but F15 is the genuinely chart-shaped, "hardcoded real-world constant"
comparison Z17's own wording describes -- F7's live-percentile hook is a
different, already-shared architecture (byte-for-byte the same pattern as
Grid's own C15 hook) that this rollout deliberately didn't touch.

New `real_world_comparison_chart_svg()` builds a small two-bar chart (You
vs. "Real farms (documented)") via the new shared
`shared/comparison_chart.py`'s `bar_comparison_svg()` -- the same module
Grid's C15 global-comparison line and Continuum's K13 "vs. history" chart
also now share -- rendered into a new `#real-world-comparison-chart` div
right under the existing sentence. "You" reuses the gauge's own
decoupled-green; the reference bar uses an Okabe-Ito blue rather than red,
so this never becomes a red/green colorblind-confusion pair.

This is genuinely new player-facing behavior (a chart where there was none
before), so it's in `changelog.json` too. 3 new tests
(`tests/test_real_world_comparison_chart.py`); full suite green aside from
the same unrelated `test_achievements.py` `card.dataset` failures a
concurrently-running sibling agent's in-flight work left mid-edit (not
touched by this change). `flake8` clean. Live-verified via the shared
`hub-dev-server`: a fresh farm showed the chart at 0% vs. the 42%
reference bar; growing the herd and investing in Capture Systems three
times correctly grew the "You" bar to 30%. Zero console errors.


## Callout-to-achievement audit (Z-extra, 2026-09-26)

Of Herd's four one-time milestone toasts (`_MILESTONE_CALLOUT_MESSAGES`), only `certified` was a pure "you did a thing once" celebration with no achievement behind it, so it became the **Sustainably Certified** achievement (`ACHIEVEMENT_CHECKS["sustainably_certified"]` reads `farm.certified`) and its toast, the `newly_certified` bookkeeping and the message were removed. The other three stay on purpose: `half_decoupled` is F4's "what does decoupled mean" explainer (a separately requested teaching moment, even though the Half Decoupled achievement fires alongside it), and `pressure` / `methane_penalty` are gameplay warnings, not celebrations. 191 -> 194 tests green.

## Farm succession (F25, 2026-09-26)

An Aftermath-style meta-progression, built independently and tied to F23. Once a farm is sustainably certified it can be handed to the next generation (confirm dialog, no "don't ask again" since it wipes the farm): `hand_over_farm()` restarts the farm from scratch, raises `generation`, and awards legacy points, 1 base plus 1 if the outgoing farm raised a poultry flock of 3 or more (`handover_points()`, the F23 tie-in). Points buy permanent perks (`LEGACY_PERKS`): Family Savings (1 pt, up to 3 levels, +75 starting funds each, counterfactual funds raised equally so "saved vs baseline" stays fair), Heritage Flock (2 pt, poultry available from round 1 without certification, via `poultry_unlocked()`), Mentor's Methods (2 pt, one free Feed Additives unit every generation). A perk takes effect immediately on the current farm and on every later generation.

- `generation`, `legacy_points` and `legacy_perks` are module-level, deliberately outside `farm`, so replacing `farm` on handover never touches them (same shape as Loop's `chains_completed_count`).
- Save: the three fields are written only when non-default, and validated on load (ints only, unknown perk names dropped, levels clamped to each perk's max).
- Known trade-off (same as SOL's prestige): achievements derived from live farm state (e.g. sustainably certified) reset with the farm.
- Panel `#succession-panel` is hidden until certified, or a generation/points/perk exists. 194 -> 208 tests (`tests/test_succession.py`); verified live through the real confirm dialog, zero console errors.

## Satellite farm (F1, 2026-09-26)
`FarmState` gains `satellite_open/size/retrofits`. Available once `herd_size >= SATELLITE_MIN_MAIN_HERD` (6); `open_satellite()` costs `SATELLITE_OPEN_COST` (40). Own ratio starts at `SATELLITE_BASE_RATIO` 1.2 (dirtier than main), lowered by `retrofit_satellite()` (-0.08 each, max 8, floor 0.15); size capped at `SATELLITE_MAX_SIZE` 10. Network effect: `satellite_offset_fraction()` = main-farm `decoupled_fraction()` beyond `SATELLITE_OFFSET_FLOOR` (0.4) x `SATELLITE_OFFSET_RATE` (1.0), capped at `SATELLITE_MAX_OFFSET` (0.5); effective ratio = own ratio x (1 - offset). Satellite output feeds `methane_this_round()`, income (before supply-chain/season multipliers), the regional cap (`cap_blocks_growth(satellite=1)`) and the counterfactual (at its base ratio, so the pure-growth comparison stays honest). Save keys written only after opening, clamped/validated on load; a handover starts a fresh farm with no satellite. Tests: `tests/test_satellite_farm.py` (12).
