# Notes for herd: the long history

This is the long history moved out of CLAUDE.md on 2026-10-18 (every section below is verbatim, in its original order). The local AI should read only the section it is told to, never the whole file.

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

- **Achievements**: 19 achievements (`achievements.json`) spanning herd growth, all three decoupling paths, the plant-based pivot, beating the pure-growth baseline, and round-count/score milestones. In-game panel (🏆 toggle) with live progress readouts, a separate unlock toast (distinct from the F5/F11/F17 milestone-nudge toast below so an achievement is never confused with a gameplay nudge), `achievements_earned` riding `get_state()`, and a link out to the hub-wide dashboard.
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

## F10: trend arrow on the community comparison (2026-09-26)
`planning/TODO.md`'s F10: "let the community stat show a small trend arrow if the backend can support it cheaply" -- the honest answer is that the shared stats endpoint (Z1) only ever returns a live snapshot, never a history, so a real trend can't come from the backend at all. The cheap version instead has this browser remember its own last reading (`localStorage["herd-community-lower-pct"]`) and compare the new one against it -- entirely client-side, no backend change, no new request. `window.herdCompare()` (`index.html`) now appends a shape-coded arrow (▲/▼/▶, same convention as Thaw's own round-to-round trend arrows -- never color-only) plus a `title` tooltip ("Better/Worse/Same as your last check.") whenever a previous reading exists; the very first check in a browser shows no arrow, since there's nothing yet to compare against. Lives entirely in the same inline `<script>` F7 already put this logic in (untestable from the Python fake-DOM harness for the same reason F7 itself is, per that section's own note) -- verified live instead: mocked `window.fetch` to feed the hook two different percentiles in sequence and confirmed the arrow direction, the stored value, and the tooltip text all matched. Pure JS/HTML change; full 220/220 pytest suite unaffected, as expected.

## Decoupling leaderboard (F21, 2026-09-26)
After each round `_report_decoupling_gap()` sends `score() - counterfactual_score()` (only when positive) and the round to `window.NoyvjLeaderboard` (shared/leaderboard.js, mounted above the feedback prompt); it submits only for a signed-in, opted-in player and remembers the personal best. Backend board `herd/decoupling_gap`. Tests: `tests/test_leaderboard_report.py` (3).

## Story mode (W1, 2026-09-26)

A light narrative thread, "The Marlow Farm", built on the shared `shared/story-chapters.js` (Grid was the reference integration; that file is not edited per game). `story.json` holds an opening chapter `begin` plus exactly one chapter per achievement id in `achievements.json`, in story order from early to late game, about the family farm across generations. `_story_reach_all(earned_ids)` in `game.py` calls `window.NoyvjStory.reach()` for `begin` and every earned id, from the achievement check (`_check_new_achievements_for_toast`) and from the load/baseline path, so a loaded save brings its chapters back. It is idempotent and silent when the script is missing. Progress lives in `localStorage["story-chapters:herd"]`, never in the save. `#story-chapters` is appended to the existing `story-toggle.js` selectors, so the Story on/off pill hides it. Tests: `tests/test_story_chapters.py` (7).

## Reactive tagline (R-23, 2026-09-27)
`tagline_message()` picks one sentence for the line under the title in priority order: certified (`TAGLINE_CERTIFIED`), decoupled by half or more (`TAGLINE_HALF`, at `HALF_DECOUPLED_CALLOUT_THRESHOLD`), methane pressure at or past `PRESSURE_CALLOUT_THRESHOLD` (`TAGLINE_PRESSURE`), else the original line. Rendered from `render()` into `#tagline-display`; display only, no state or save change (tested). Tests: `tests/test_tagline.py` (5; 230 -> 235).

## Desktop boot (PC version, 2026-10-07)

`games/herd/pc.html` is the Desktop boot: the same game over the same `game.py` and saves (same `game_id`), laid out for a wide window with a mouse. **Never edit it by hand**: it is generated from `index.html` plus `pc-config.json` by `scripts/generate-pc-pages.py` (run it after changing either; `--check` and the shared tests fail if it is stale). No rule, state or save change, and `game.py` is untouched. Classic (`index.html`) only gained the `shared/layout-pref.js` tag and the `window.HERD_PC_TUTORIAL_STEPS ||` fallback on the tutorial init. The shared `MobileHud` still runs in the page but is hidden by `pc.css` (phones and narrow windows are meant to use Classic).

- **Where things went.** Top bar: back link, title, three icon buttons (Achievements, Report Card, Settings), the Menu button and the Story pill. Readout chips under it (round, Funds, Herd, Methane, Coupling, Pressure, Score), built by the shell from the same `#round-display`, `#funds-display` ... text lines, which keep updating inside the "Status and score" window (a composite holding `#status`). Stage: the pasture (grows to fill spare height) above the coupling gauge section, laid out as two columns (dial and its readouts on the left, the real-world comparison chart and the methane trend graph on the right). Side column (scrolls on its own, Advance Round pinned at the top): Grow Herd with its preview, the decoupling investments, the plant-based pivot, the collapsed "Farm operations and scenario options", and the policy, succession, poultry and satellite panels when game state shows them. Windows (Menu or the icons): How to Play, Achievements, Report Card, What's New, Settings, The Real Story, plus composites opened from the Menu: Status and score, Baseline farm comparison, Community leaderboard, About Herd (tagline, context blurb, community stat) and Feedback.
- **Desktop tutorial.** `pc.js` sets `window.HERD_PC_TUTORIAL_STEPS` (9 steps pointing at the chips, the Grow Herd card, the gauge, the decoupling and pivot cards, Advance Round and the Menu); every selector exists on `pc.html`.
- **Hotkeys.** Herd only has `?` (shortcut help) and Esc (closes the open panel), so the hint bar lists just those plus Esc for the Menu. No notification stack (`notify` is null): Herd has no log list, its toasts are the existing achievement and milestone toasts.
- **Layout notes.** `pc.css` clears the ad-bar body padding (it made the body scrollable), clips the ambient blobs, moves the floating theme toggle to the top-right corner, and at 1180px wide or less drops the chip text labels (icon plus hover title) so the chip strip stays on one row. The chart labels get a dark fill in the light theme. Verified live at 1440x900, 1920x1080 and 1024x700 in dark and light themes: no page scroll.
- **Known limits.** The methane meter bar lives only in the Status window (the Methane chip shows the number). The Pressure chip shows the whole "Market/regulatory pressure: N% income loss" sentence, since the line has no short label before a colon. At 1024x700 the side column scrolls (its own scroll, not the page). The Story panel floats over the side column while open. The shared keyboard-shortcuts help overlay (`?`) is not a window of the Desktop shell.

## Round-3 collector and progress batch (2026-10-07)

From `planning/TODO.md`'s "GF + F. Herd" section (235 -> 298 tests, `tests/test_round4_batch.py`). All of it is derived from existing state plus three new `FarmState` records (`funds_history` aligned with `methane_history`, `lever_log`, `perfect_streak`/`best_perfect_streak`) and two module-level collections. New save keys are written only when there is something to save, and each is validated and defaulted in `load_state()` (`_load_progress_fields`); `lever_log` is capped at `LEVER_LOG_MAX` (300).
- **GF-15 perfect-round streak.** A round is perfect when the methane it added fell below the previous round's (the existing `just_flattened`) AND funds ended higher than they ended the round before. Streaks pay `PERFECT_STREAK_BONUSES` (3 -> 10, 5 -> 20, 10 -> 40 funds) to the real farm only, never the counterfactual, with a milestone toast. Needs a decoupling purchase each round that still pays for itself.
- **GF-16 breed shelf.** `BREEDS`: 11 collected-for-good breeds (module-level `breeds_collected`, survives handovers), each a state check (`herd_size`, lever counts, certified, ...). The last, Methane-Eater Cow, is hidden (silhouette, "???" and a rumour) until coupling is under 0.25 with welfare 90 or more; it glows when earned (reduced-motion respecting).
- **GF-5 combo book.** `COMBOS`: 8 named lever combinations (Circular Barn, Happy Herd, Green Gourmet, Full Stack, ...) found once each (`combos_found`), paying `COMBO_REWARD_FUNDS` (20) to the real farm only. The book hides names until found but shows every rule. These are lever-SET combos checked every render, not strict build orders.
- `_sync_collection(award)` runs at the top of `render()`. `load_state` calls it with `award=False` so loading a save records what the farm qualifies for but never changes funds.
- **GF-22 rating ladder.** `RATING_TITLES` (Hobby Farmer to Decoupling Legend), highest satisfied rung wins; shown in the decoupling card and the report card with the next title's requirement.
- **GF-29 highlights reel.** Three lines on the report card from `funds_history`/`methane_history` (biggest single round, best methane cut in one round, peak herd and best streak). Older saves with no funds record are padded with `None`, which the reel skips.
- **F-13 funds per methane saved.** `FarmState.methane_saved_by(key)` tries one more unit of a lever and puts it back; each lever row shows "Saves X methane/round: about N funds per methane saved" (uses the subsidised cost; includes the satellite network offset and the pivot cap).
- **F-24 cap headroom.** With the regional cap on, a bar plus `cap_headroom_message()`: free methane and `rounds_until_cap()` at the herd's pace so far.
- **F-17 lever history.** Every purchase logs (round, lever, cost); a filterable list under Collection. The `<option>` list in both pages must match `LEVER_LABELS` (tested).
- **F-10 (partial).** `#round-announcer` is a polite live region that reads the round result after Advance Round. Still open from F-10: arrow-key control on the lever list, visible-focus audit, shortcut cheat sheet in How to Play.
- **Where it lives.** Classic: one collapsed `#collection-extras` panel (breeds, combos, history). Desktop: `#collection-extras` is in the `hidden` zone and its three blocks plus the summary are the composite window "Breeds, combos and history" in the Menu's Records group; the rating, streak, per-lever efficiency lines and cap headroom are in the side column; rating titles and highlights are in the Report Card window. Verified live at 1440x900 and 1024x700 (Desktop, dark and light) and 360x740 (Classic, no horizontal overflow), zero console errors.
- Wiring pass 2026-10-08: the Report Card carries the shared Copy result button (`copy_result_fields()` in game.py feeds `shared/copy-result.js`; the card is rebuilt every render, so the inline script at the end of index.html re-mounts the button with a MutationObserver), earned achievement cards get a Share button (`shared/achievement-share.js`), the head carries the Open Graph/Twitter block and JSON-LD from `share/meta/herd.html` and `share/jsonld/herd.json`, and the How to Play and Info panels end with a Credits link. Pins: `tests/test_wiring_oct8.py`.

## Play-quality batch (2026-10-08)

From `planning/TODO.md`'s "GF + F. Herd" section (310 -> 366 tests, `tests/test_oct8_batch.py`). The new code sits in one block in `game.py` ("Round-4 batch", before `round_announcement`) and is drawn by `render_round_extras()` at the end of `render()`.
- **F-19 bulk buying.** `FarmState.bulk_plan(key, mode)` works out (units, total) on a scratch copy, `buy_bulk()` then makes the real purchases one by one (each priced and logged like a single click). A stepper `x1 / x5 / Max` in `#actions` sets the module-level `bulk_mode` (session only, not saved). Applies to Grow Herd and Feed / Caps / Capture; the Plant-Based Pivot stays single because it goes through the confirm dialog. Max is capped at 50; x5 and Max stop at the regional cap, the funds, and (for levers) the efficiency floor. Mode x1 keeps the old labels and rules exactly.
- **F-20 round-delta chips.** After Advance Round, four chips (Funds, Methane added, Welfare, Pressure in points) with a triangle/square shape and a sign; they fade after `DELTA_FADE_MS` (6 s) unless pinned by a click (a stale timer is ignored through `delta_token`). In the Desktop side column under Advance Round. Not saved.
- **GF-18 undo.** `on_advance_round` stores `farm.undo_snapshot = get_state()` before advancing. `undo_last_round()` calls `load_state(snapshot)`, then keeps succession (generation, legacy points and perks, hall of fame) and collected breeds as they are, charges `UNDO_PENALTY_FUNDS` (25), marks `farm.undo_used` and clears the snapshot. Everything bought or toggled since the advance is undone. Once per game (a handover starts a new game). The snapshot is never saved; `undo_used` is saved only when true.
- **F-21 season calendar.** `season_calendar_cells()` lists the next 12 rounds from the same `season_for_round()` / `demand_surge_active()` the income uses; cells carry a shape (down/up triangles, square), the percentage and a seedling for a surge, plus an aria-label. Hidden unless variation is on.
- **F-22 poultry vs cattle.** `poultry_compare_html()`: a labelled table per unit per round (income, methane-equivalent, income per methane, welfare effect). Honest about welfare: flock levers do not move the welfare score.
- **F-23 breeding rings.** `genetics_rings_html()`: one SVG ring per maturing line, rounds left written in the middle.
- **GF-13 named cows.** `cow_name(index, gen)` is fixed by position and generation (24 names, then numerals), so names survive reloads. Hovering a pasture cow names the animal that revealed it. `hand_over_farm()` calls `retire_herd_to_hall()`: the 3 longest-serving animals (from `lever_log` purchase rounds; units the log no longer holds count from round 1) join `hall_of_fame` (best 5 kept), listed under Collection. Saved as `hall_of_fame` only when non-empty, validated and HTML-escaped on load. Not done: "losing herd units to a cap" (the herd never shrinks).
- **F-28 pace note.** `#pace-note` under the round counter ("This sitting: N rounds, about M min"), and every `SAVE_NUDGE_EVERY` (10) rounds in one sitting a toast suggests saving and resting (joined onto a streak toast when both happen). Counted from page load (`session_rounds`), so loading a late save never nudges.
- **Desktop.** `#undo-panel` and `#round-delta-strip` are in the side zone; `#hall-of-fame` is a member of the Collection window. New save keys: `hall_of_fame`, `undo_used`.

- FY-4 (2026-10-09): the end-of-game feedback prompt has a second question, "Did decoupling feel like a real strategy, or a tax on growth?" (`#feedback-decoupling-strategy-button`, `#feedback-decoupling-tax-button`), the Thaw two-question pattern. Submit needs both answers; the response string is `understanding=<yes|no>; decoupling=<strategy|tax> — <comment>`. Plain inline JS in `index.html` (no Python); `tests/test_feedback_lesson_question.py` checks both pages. No backend change.

## Round-5 display preferences (F-15, F-14; 2026-10-10)

Three browser-level switches in the Settings panel, all in `settings.js` (no Pyodide, never in `get_state()`): `herd-high-contrast`, `herd-dyslexia-font` and `herd-hatch-patterns` in localStorage, mirrored as `data-high-contrast`, `data-dyslexia-font` and `data-hatch-patterns` on `<html>`; "Reset to Default" clears them. `style.css` ("Round-5 display preferences") does the rest: high contrast is a blanket black/white pass (with a doubled-attribute selector so it beats the light theme and the Desktop shell windows; the pasture picture, meters and SVGs are left alone), the easy-read font is a font stack with no download (OpenDyslexic/Atkinson Hyperlegible/Lexend/Verdana if installed) plus letter and word spacing. F-14: two new small bars in the farm-extras panel (`#welfare-bar`, welfare out of 100, dots; `#supply-chain-bar`, units out of the max, vertical stripes) beside the existing methane bar (diagonal stripes, also used by the cap-headroom bar), and `trend_markers_svg()` draws a shape on every round of the methane graph (square = curve flattened, circle = otherwise, diamond = latest, capped at the last 40 rounds), shown only when the pattern setting is on. Also fixed: the Report Card toggle label was left at the HTML placeholder "Loading..." until first clicked; `render()` now always sets it. Tests: `tests/test_display_prefs.py`.

## Keyboard play: the rest of F-10 (2026-10-10)

Finishes F-10 (the live region reading each round result was done 2026-10-07). In `settings.js`: one `keydown` listener moves focus between the buy buttons (`LEVER_SELECTOR`, 13 ids that exist on both pages) with Up/Down/Home/End and inside `#bulk-stepper` with Left/Right/Home/End; disabled and hidden buttons are skipped (a disabled button cannot take focus), modifier chords are left alone, and Tab still reaches everything in page order, so the arrows are a shortcut, not the only way. How to Play gets a "Keyboard play" block (`.howto-keys`, from `CHEAT_SHEET_ITEMS`) appended by a MutationObserver, so it survives the shared tutorial redrawing the panel; the shared `?` overlay gets two Herd lines through `KeyboardShortcuts.init({extra})`; `#grow-herd-button` has `aria-describedby="lever-keys-hint"` (a screen-reader-only tip). **Visible-focus audit:** a Playwright pass focused every visible focusable element on `index.html` (44) and `pc.html` (26) and compared outline/shadow/border before and after: all show a change except the shared `#story-toggle` pill (shared file, not Herd's). Verified live on both pages (Down, Down, Up, End, Home and the stepper Left/Right land on the expected buttons). Tests: `tests/test_keyboard_play.py`.

## Friendly save recovery (F-30, 2026-10-10)

`load_state(data)` now validates before it changes anything. `check_save()` lists every field that is present but unusable (the numeric fields in `SAVE_NUMBER_FIELDS`, each decoupling count, `methane_history`); a field that is merely missing is not a problem, so older saves load exactly as before. A bad save raises `ValueError` (the shared save widget then says "Load failed") after `#save-recovery-panel` shows a plain reason per problem (escaped, at most 6 listed), with "Keep my current farm" and "Load with defaults for those fields" (`sanitize_save()` swaps in fresh-farm values for just those fields and calls `_apply_state()`). A non-dict save returns `False` with the notice. A save that passes the checks but still fails while being applied puts the farm back from a `get_state()` backup and shows the same panel. The old body of `load_state` is now `_apply_state()`, unchanged. Nothing new is saved. The panel is in the Desktop side column (above Advance Round). Tests: `tests/test_save_recovery.py`.

## Ask before a big purchase (F-18, 2026-10-10)

`#confirm-threshold-select` in Settings (Never / 25 / 50 / 75 percent) stores `herd-confirm-percent` in localStorage (settings.js, browser-level, not in saves; Reset to Default sets it back to Never). `confirm_threshold_percent()` in game.py reads it at press time (junk means off); `purchase_needs_confirm(cost)` is true when the cost is strictly more than that share of current funds, and `_guarded_purchase(label, cost, action)` then routes through the shared `ConfirmDialog` with `allowSkip=False` (id `herd-big-purchase`, no "don't ask again" box, the setting is the off switch) or runs the action at once. Every purchase button uses it: Grow Herd and the three levers (judged by the bulk plan's total, so a Max batch counts as one purchase), Grow Flock, the poultry levers, Breeding Program, Processing & Distribution and the three satellite buttons. The Plant-Based Pivot keeps its own dialog unless the setting says it is big, in which case the F-18 dialog (with the pivot trade-off text) is used every time. Tests: `tests/test_confirm_threshold.py`; verified live (Max grow at 25 percent shows "Grow Herd costs 290 funds, 97% ..." and buys on confirm).

## Achievement hover progress (F-27, 2026-10-10)

`ACHIEVEMENT_PROGRESS` now covers all 19 achievements (added first_herd, first_decoupling, all_three_measures, sustainably_certified, plant_pioneer, outperforming_baseline and clean_operator; Clean Operator returns `None` once the farm's worst pressure has passed the limit, since it can no longer be earned on that farm), `ACHIEVEMENT_PROGRESS_UNITS` names what each counts, and `achievements_summary()` carries `unit`. An unearned card with progress gets `tabindex="0"`, an `aria-label` ("Label: N to go (c of t)"), `.achievement-card-bar` (mini bar, diagonal-striped fill so it is not colour alone) and `.achievement-card-left` ("N<unit> to go (c of t)", exact, never rounded up). CSS shows the bar and text on `:hover`, `:focus` and `:focus-within` (always on where there is no hover, `@media (hover: none)`). Earned cards are unchanged. Changelog cap in `tests/test_changelog.py` raised from 40 to 80. Tests: `tests/test_achievement_progress.py`; verified live (hover shows the bar, other cards stay hidden).

## Glossary popovers (F-29, 2026-10-10)

`settings.js` holds `GLOSSARY` (8 words: coupling ratio, decoupling, baseline farm/counterfactual, welfare, capture systems, pressure, sustainable certification, methane-equivalent; one or two plain sentences each). `markGlossaryTerms()` wraps the first match of each word per paragraph in a focusable `.glossary-term` (dotted underline, `role="button"`, `aria-label` with the definition) but only inside `GLOSSARY_SCOPE` (`.info-toggle p`, `.context-blurb`, the How to Play step paragraphs), so live readouts written by `game.py` are never rewritten; the How to Play panel is rescanned by a MutationObserver when the shared tutorial redraws it. A single `#glossary-popover` (role tooltip) opens on hover, focus or click/tap, is clamped to the viewport, and Esc closes it (capture-phase, so it does not also close a panel). `buildGlossaryBlock()` appends the full glossary to How to Play. Light theme and high-contrast variants in `style.css`. Tests: `tests/test_glossary.py` (word list, definition length, scope, CSS); behaviour checked live at 1440 and 360 on both pages.

## "Why this number?" inspector (F-6, 2026-10-10)

`FarmState.income_breakdown()` splits one round's income into the pieces the game applies (herd base, plant-based blend, certification, welfare, poultry, satellite, supply chain, season, pressure, biogas) and `advance_round()` now banks exactly `breakdown["total"]`, so the inspector cannot disagree with the game (tested against real advances across 12 farm shapes). `explain_*_nodes()` build small trees (income, methane, coupling ratio, pressure) from the live state, `_tree_html()` renders them escaped as nested lists, and `#explain-panel` (a collapsed details block with four toggle buttons, `aria-pressed`, live region) redraws on every `render()`. `explain_kind` is session-only. Desktop: `#explain-panel` is in the side column after Undo. Not done: clicking the readout chips themselves (the Desktop shell builds them). Tests: `tests/test_explain_inspector.py`; verified live on both pages at 1440 and 360.

## Ranch Rules (F-1, 2026-10-11)

Four balance sliders in the Settings panel (`#ranch-rules`; Desktop: the Settings window): starting funds 150-600, season swing 0-200%, pressure penalty 50-200% and growth-cost slope 0-4, with the standard value in the middle of each (`RULE_SPECS`, `ranch_rules`, `rule(name)`). Standard rules are the constants the file was always written around, so a standard farm behaves exactly as before. `pressure_scale()` is `PRESSURE_SCALE` stretched by the strength slider and is used by `pressure_fraction()`, the baseline's pressure, the methane bar and the inspector; `season_modifier()` is scaled by the swing slider (the calendar shows the scaled percent); `grow_herd_cost()` uses the slope. Starting funds applies at once only to a farm that has not started (`farm_is_pristine()`, moving the baseline and the funds history with it); after play it waits for the next new farm or handover. **Unranked (FY-32):** `rules_unranked()` is true when the rules are non-standard or the run ever used them (`farm.custom_rules_used`, kept even if the player goes back to standard after playing); such a run is skipped by `_report_decoupling_gap()` (leaderboard) and `_request_comparison()` (the client-side `herdCompare` hook), the report card says so, the Copy result line says so, and the score-400 achievement cannot be earned (a bigger purse would make it free). Saves: `ranch_rules` (only the non-standard values) and `custom_rules_used` are written only when set, clamped and snapped on load (`clean_rule_value`), and a save without them restores the standard rules. The rules are also remembered in `localStorage[herd-ranch-rules]` so a new farm in this browser starts on them (the display preferences' Reset to Default does not touch them; Back to standard rules does). **Not done:** the save-based community stats (percentile of lifetime methane, achievement rarity) are computed by the backend from saves, so keeping custom-rule saves out of them needs a backend change (`custom_rules_used` is in the save for that). Tests: `tests/test_ranch_rules.py`.

## Policy-advisor pool (F-9, 2026-10-11)

The advisor that visits every 8 rounds now draws two options from a pool of six (`POLICY_ORDER`, `POLICY_OPTIONS`): the decoupling subsidy and the cash bonus (the original pair, always the first offer), a carbon-credit contract (funds now, more the further below baseline), a feed-price hedge (Feed Additives half price for 6 rounds, stacking with the subsidy), an organic label trial (+8% herd income for 4 rounds, a `label` factor in `income_breakdown()` and the inspector) and a welfare grant (funds now, more with welfare above 50). `FarmState.draw_policy_offer()` takes the first two unseen options in the fixed order (the second picked by how many offers were taken, so the pairs vary but never by chance) and starts the pool over once fewer than two are left. The two existing buttons (`#policy-subsidy-button`, `#policy-cash-button`) are now slot A and slot B and are relabelled per offer with the option name and its tag (Subsidy programme, Direct payment, Carbon market, Price hedge, Eco-label, Welfare payment); each option also has a one-line "Real-world idea: ..." text (a kind of scheme that exists, no figures, so nothing needs a live source) shown under the offer and as the button tooltip. History: `policy_history` ([round, taken, passed-on], capped at 40) is listed under "Advisor history" in the Collection panel (Desktop: a member of the Breeds, combos and history window) and as a report-card line. Gains go to the real farm only, like the original cash bonus. Saves: `policy_offer`, `policy_seen`, `policy_history`, `hedge_rounds_left`, `label_rounds_left` are written only when set, ids and counts validated on load; an old save with a pending offer and no stored pair gets the original pair. Tests: `tests/test_policy_pool.py`.

## Dry-run planner (F-7, 2026-10-11)

`#planner-panel` ("Plan ahead (dry run)", a collapsed details block; Desktop: the side column after the inspector). Pick a lever (Grow Herd, the three decoupling levers, Plant-Based Pivot, Breeding Program, Processing & Distribution), how many (x1, x2, x5) and when (now to 9 rounds ahead), queue up to 12 steps, and choose a 5- or 10-round look-ahead. `project_plan()` plays the queue on `clone_farm(farm)`, a deep-enough scratch copy (every list and dict copied, undo snapshot dropped), and on a second copy that buys nothing; it never touches the real farm, the save, the lever log or any achievement (tested by comparing the whole farm and `get_state()` before and after). Output: a one-line summary (score after the horizon against doing nothing and against the pure-growth baseline, which is the scratch farm's own counterfactual), a small SVG chart (solid plan, dashed doing nothing, dotted baseline, with P/N/B letters at the line ends, so not colour alone) and a table with a caption and column scopes (round, funds, methane per round, coupling, score, score against doing nothing, score against the baseline). Purchases the funds or the regional cap cannot afford are skipped and named ("Round +2: Capture Systems x1 not bought"). The plan itself is session-only (`plan_steps`, `plan_horizon`), never saved. Advisor offers and streak choices are not modelled (the scratch farm may reach a streak bonus, as the real one would). Tests: `tests/test_planner.py` (`tests/fakes.py` elements now carry a `value`).

## Ranch Ledger (F-2, 2026-10-11)

`#ledger-panel` (collapsed details; Desktop: side column). A handover (`hand_over_farm()`) files the finished farm automatically (`done: true`), and "File this farm now" files the one in play (filing the same generation at the same round replaces that line). Each line (`ledger_entry()`): generation, round, funds, methane, score, the baseline's score, herd, flock, mode (`farm_mode()`: plain, seasons, cap or seasons and cap), a custom-rules flag, and the six lever counts. Stored in `localStorage["herd-ranch-ledger-v1"]` (capped at `LEDGER_MAX` 60, every line validated one by one on read by `_clean_ledger_entry`; junk is dropped), never in a save. The filter select (All, Plain, Seasons, Cap; seasons-and-cap lines show under both Seasons and Cap) feeds a table (caption, column scopes) and a trend chart of score minus baseline (line, a square at every point, a dashed zero line, aria label naming the best). Clear ledger goes through the shared confirm dialog. Tests: `tests/test_ranch_ledger.py`.

## Pin-a-stat strip (F-16, 2026-10-11)

`#pinned-strip` is a sticky strip at the top of the page (Desktop: first item of the side column, which scrolls on its own) showing up to three pinned readouts, so they stay in view while the extras panels are open. The picker is a fieldset of eight checkboxes in the Farm operations panel (`PIN_STATS`: funds, income per round from `income_breakdown()`, welfare, methane per round, total methane, score, herd, pressure); a fourth pin is refused and the unticked boxes are disabled at three. Each chip is a text label plus a value (no colour coding). The choice is a browser preference (`localStorage["herd-pinned-stats"]`, `clean_pins()` drops unknown ids, repeats and extras), never part of a save. The strip is a plain group, not a live region, so it does not chatter at a screen reader every round. Tests: `tests/test_pinned_stats.py`.

## Round celebration (GF-14, 2026-10-11)

After Advance Round, `on_advance_round()` computes the round's income (`income_breakdown()["total"]`, taken before advancing) and `celebrate_round(income, beat)` hands it to the page's optional `window.HerdFx.roundGain()` (in `settings.js`, plain JS, no new file). `beat` is true when the income is higher than the previous round's (`last_round_income`, session-only; the first round of a sitting never beats). The hook builds a decorative `#cha-ching` block under the Advance Round button ("Earned +N funds", counting up over 0.7 s, plus a 16-piece confetti burst when it beat the last round), hidden again after 3.5 s. It is aria-hidden because the polite live region already reads the round result. On by default; the Settings checkbox `#cha-ching-checkbox` stores `"false"` in `localStorage["herd-cha-ching"]` (the display preferences' Reset to Default turns it back on). With reduced motion (Settings or the OS), lite mode (`html[data-lite="true"]`) there is no count-up and no confetti, just the final text. No hook (pytest, other pages) is a silent no-op. Tests: `tests/test_cha_ching.py`; the JS itself was checked live (count-up, confetti, reduced motion, off switch) on both pages.

## Feed-additive mixer (GF-25, FY-31, 2026-10-11)

An optional click-timing minigame in the Farm operations panel (`#mixer-panel`), unlocked by the first Feed Additives unit. A marker sweeps across a bar (`initMixer()` in `settings.js`, 1.6 s per sweep, 5 s to stop it); the player stops it with the Stop button (focus moves there, Enter or Space) as near the middle as they can. The JS passes the quality (0 to 1, from the distance to the middle) to `on_mixer_result()` through the hidden `#mixer-result-button`'s `data-quality`; `FarmState.blend()` pays `quality x min(MIXER_BONUS_MAX 40, 5% of the funds in hand)` (FY-31: a small bonus capped near 5% of a round's funds), once per round (`mixer_round`), a timed blend never below `MIXER_MIN_QUALITY` 0.2 so a miss is not wasted, 0.9 or more counts as perfect. Running out of time uses nothing up. **Auto-blend** (`#mixer-auto-button`, plain Python) pays half (`MIXER_AUTO_QUALITY`) with no timing at all, and with reduced motion, lite mode or the OS setting the sweeping bar is off and only Auto-blend is offered. The bar's zones carry the words Off, Good and Perfect and different fills (not colour alone). The play always counts: the funds, a visible tally ("N blends, P perfect, +F funds earned in total", on the panel and in the report card), saved as `mixer_stats` [blends, perfects, funds, last round] only once there is one (validated on load). Bonus funds go to the real farm only. Tests: `tests/test_mixer.py`; the bar itself was verified live on both pages (start, stop, timeout, reduced motion, Auto-blend).

## The Family Farm, a branching story (GF-10, FY-30, 2026-10-11)

A short original story in `#family-story` (a collapsed details block, "Farm story"; Desktop: side column), alongside (not replacing) the achievement-chapter Marlow Farm story. Grandpa Tobias gets a letter (page 1, round 4): sell the north field, go organic slowly, or take the barn grant. Each branch has a short vignette, a second page at round 10 with two options, and an ending (The Quiet Sale, The Slow Green, The Barn Grant; each ending text has one variant per option, so six texts for three endings) that arrives at round 16 or as soon as the farm is certified. All text lives in `FAMILY_BRANCHES` in game.py (no new file to fetch), short and figure-free (a test checks length and that no digits appear: real-world facts stay in the Real Story panel). **The sim is untouched**: the story only reads the round and certification to decide when a page is ready (tested by comparing the whole farm before and after a choice). The panel is in the Story pill's selector list on both pages, so Story off hides it; a page waiting shows in the summary line ("a choice is waiting"), never as a popup. "Tell it again" restarts the farm's story after an ending so the other endings can be found; endings found are a collection (`family_endings`, module-level, survives a handover; "Endings found: N of 3", unfound names shown as ???). Saves: `family_choices` (the farm's path, only when non-empty, validated as a real branch then one of its options) and `family_endings` (real branch ids, no repeats), written only when set. Tests: `tests/test_family_story.py`.

## Achievement card restyle (F-31, 2026-10-11)

`ACHIEVEMENT_GLYPHS` gives each of the 19 achievements its own livestock or pasture glyph (cow, ox, tractor, grain, clover, seedling, herb, tree, farmhouse, carrot, leafy green, sunflower, bee, milk, cheese, basket, hen, sheep, goat), drawn as an aria-hidden span at the left of every card (greyed on locked cards, so the shelf reads as a collection to fill). Earned cards get a barnyard border (red barn side, double top rule, faint plank stripes); a card earned this session plays a short hop-and-glow flourish the first time it is drawn (`achievement_flourish_ids`, filled by `_check_new_achievements_for_toast()` which redraws an open panel at once; a loaded save never replays old flourishes). The flourish is off under reduced motion (Settings or the OS) and lite mode; high contrast keeps the glyphs fully visible. Tests: `tests/test_achievement_cards.py`.

## Cow reactions (GF-12, 2026-10-11)

`herd_mood()` reads the farm: **hop** when welfare is 70 or more and the coupling ratio 0.7 or less, **nap** when welfare is 45 or less or pressure is 40% or more, otherwise calm. `update_pasture_visual()` puts `cow-mood-hop` or `cow-mood-nap` on the five pasture cows (a hop animation; a napping cow shows "z z" and stops grazing, so the mood is never motion alone) and writes the mood in words on the new `#cow-listen-button` ("Listen to the herd (hopping)"). Clicking a pasture cow, or pressing the Listen button (the keyboard way, since the pasture is aria-hidden), shows a dry one-liner in the polite live region `#cow-bubble`, starting with that animal's name (GF-13's `cow_name`), for 4 s. Four lines per mood in `COW_QUIPS`, rotated by a counter (no luck). Off under reduced motion, lite mode or the OS setting (animations only; the text stays). Nothing here changes the farm or the save (tested). Desktop: the Listen row sits under the pasture in the stage. Tests: `tests/test_cow_reactions.py`.

## Play style profiles (F-11, 2026-10-11)

A "Play style" select in Settings (`#profile-select`): Beginner, Standard (the game as it was, the default) or Expert, built as toggled layers over existing content, chosen by the player and never adaptive. The choice is `localStorage["herd-profile"]`, mirrored by `settings.js` as `html[data-profile]` and read by `current_profile()`; never in a save; the display preferences' Reset to Default sets it back to Standard. **Beginner** shows `#next-lever-hint` (in the buy area, a polite live region): `next_lever_hint()` suggests the affordable Feed, Caps or Capture lever that saves the most methane per fund (using `methane_saved_by`), or says to grow the herd or press Advance Round; it only reads, never buys, and it exists only because the player chose Beginner (nothing is highlighted unasked). **Expert** hides the grow preview, the bulk note, the per-lever efficiency lines, the combined-decoupling line, the real-world comparison sentence, every "i" note and the glossary underlines and popover (CSS only). Not hidden: native `title` tooltips (a CSS layer cannot remove them). Tests: `tests/test_profiles.py`; both layers verified live on both pages.

## Tactile feel (GF-19, 2026-10-11)

Plain JS and CSS, no audio, nothing in game.py or a save. Buttons squish slightly while pressed (`html:not([data-tactile="off"]) button:active`), and `driveTractor()` (settings.js, listening on `#advance-round-button`) sends a small decorative tractor (a CSS-animated emoji, aria-hidden, created on first use inside `.pasture-visual`) across the pasture in 1.8 s. On by default; the Settings checkbox `#tactile-checkbox` stores `"false"` in `localStorage["herd-tactile"]` (mirrored as `html[data-tactile]`; the display preferences' Reset to Default turns it back on). Reduced motion (Settings or OS) and lite mode disable the tractor and the squish. Tests: `tests/test_tactile.py`; the tractor and the reduced-motion path were verified live on both pages.

## Lite mode, Herd's part (F-26, 2026-10-11)

The site-wide lite mode (`shared/lite-mode.js`/`.css`, Z-31, already offered to every game and synced to the account by `shared/site-settings.js`) had no switch inside Herd, and its generic rules did not cover Herd's own costs. Settings now carries the shared switch (`#lite-mode-checkbox` with `data-lite-toggle` and a `data-lite-status` line), and `style.css` turns off, under `html[data-lite="true"]`, the page-wide haze overlay, the methane wisps, the drifting clouds, the cows' grazing and hopping and the backdrop blur. Nothing needed to play is lost: pressure, methane and coupling are all on screen as text. (Also in this pass: Settings selects are capped at the panel width, found live at 360px.) Tests: `tests/test_lite_mode.py`; verified live on both pages at 1440 and 360.

## Settings code (F-25, 2026-10-11)

`#settings-code-row` in Settings (Desktop: the Settings window): "Make and copy code" and "Restore from code" around one text box. `settings_snapshot()` gathers what this browser keeps for Herd: the UI keys in localStorage (`herd-text-scale`, `herd-reduced-motion`, `herd-high-contrast`, `herd-dyslexia-font`, `herd-hatch-patterns`, `herd-tactile`, `herd-cha-ching`, `herd-confirm-percent`, `herd-profile`), the four ranch rules, the pinned stats and the best coupling ratio. The code is `HERDSET1:` plus base64 JSON through the shared `shared/export_progress.py` (fetched by the boot script, so it is now a file the page loads; `import export_progress` at the top of game.py). Import is a REPLACE for settings (each value validated: text scale 0.85 to 1.5, booleans only "true"/"false", choices from fixed lists, rules clamped and snapped by `clean_rule_value`, pins through `clean_pins`; unknown keys are ignored) except the record, where the lower (better) ratio always wins so an old code cannot undo a record. A code with nothing usable, a wrong prefix, bad base64 or another version changes nothing and says why. Rules go through `set_rule`, so custom rules in a code make the run unranked, and the status line says so. `HerdSettings.reloadFromStorage()` (settings.js) then re-applies the data attributes and every control without a reload; `HerdSettings.copyText()` does the clipboard copy (the code also stays in the box). Never part of a save and never touches the farm (tested with a byte-identical `get_state()`). The shared lite-mode switch is not in the code (it has its own account sync); the Ranch Ledger is not either (it can be long). Tests: `tests/test_settings_code.py` (8).

## Cosmetic barns (GF-17, 2026-10-11)

`BARN_SKINS` lists six pasture styles (barn, fence and tractor tint together): the default Red Barn plus five unlocked by an achievement each (Stone: Growing Operation; Green-Roof: Sustainably Certified; Sunflower: Plant Pioneer; Moonlit: Long Haul; Golden: Decoupling Dividend). `_sync_barns()` runs inside `_sync_collection()` (so every render records unlocks; a load records silently, a normal action adds the barn to the existing "Collection" toast). Unlocks live in module-level `barns_unlocked` and the choice in `barn_skin`, both outside `farm`, so a handover and an undo keep them (like breeds). Saved as `barns_unlocked` and `barn_skin` only when not default; on load the ids must be real, the chosen barn must be unlocked, anything else falls back to the red barn. The picture is `#pasture-barn` and `.pasture-fence` inside `#pasture-visual`; `data-barn` on `#pasture-visual` drives the CSS variables (wall, roof, trim, fence, door symbol, tractor filter), so the skin is never colour alone (each has its own symbol in the panel swatch and on the door). Panel `#barn-panel` (collapsed details; Desktop: side column) has six static rows `barn-use-<id>` / `barn-note-<id>`, a summary and a polite status line. Purely visual: tested that choosing a barn changes no saved number. Tests: `tests/test_barns.py` (10).

## Golden cow (GF-21, 2026-10-11)

Deterministic and untimed: `golden_cows_due()` is `(round_number - 1) // 8 - farm.golden_claimed`, so a visit arrives at round 9, 17, 25 ... and waits (visits pile up, nothing is ever missed). `welcome_golden_cow()` pays `golden_cow_bonus()` (15% of this round's income from `income_breakdown()`, never below 15 or above 60) to the real farm only (the baseline is untouched) and adds the bonus to the last `funds_history` entry so a welcome cannot fake a perfect round. The accessible control is `#golden-cow-claim-button` (shown while a visit waits; always works); `#golden-cow-glider` is a decorative aria-hidden cow gliding across the pasture (14 s loop, paused on hover) that does the same thing when clicked, and stands still (right of centre) under reduced motion, lite mode or the OS setting. `#golden-cow-panel` (hidden until the first visit; Desktop: side column) keeps the visible tally ("Golden cows welcomed: N (+F funds in all)"). `FarmState.golden_claimed` / `golden_funds` are per farm (a handover starts again), saved as `golden_claimed` and `golden_funds` only when above zero and validated on load (non-negative numbers; funds ignored when no cow was welcomed). Tests: `tests/test_golden_cow.py` (10).

## Blind run (GF-28, 2026-10-11)

An opt-in hard mode, `farm.blind_run` / `farm.blind_revealed` (saved as `blind_run` and `blind_revealed` only when true; on load `blind_revealed` only counts when `blind_run` is true, anything not exactly `True` is false). The checkbox `#blind-run-checkbox` (Farm operations, scenario options) can switch it on only while `round_number == 1` (`can_start_blind_run()`), so it is chosen before any information exists. `blind_hidden()` (run on and not revealed) gates every place that would show the baseline: `counterfactual_comparison_message()`, the Baseline Farm card numbers ("hidden"), the gauge's best-ever diamond and the "Best ever" line, `#gauge-range-display`, the report card (a shorter version that says the comparison is hidden), the Copy result stats (no "methane avoided", "blind run" instead) and the planner's chart line, table column and summary reference. It ends only by revealing: `#blind-reveal-button` (inside the Baseline Farm card; through the shared confirm dialog, no "don't ask again"), filing the farm in the Ranch Ledger (the button then reads "File this farm now (reveals the blind run)"), or a handover (a toast gives the reveal). `blind_reveal_message()` is the stronger reveal: score against baseline score, the gap in points and percent, methane against the baseline's, methane avoided and the final coupling ratio; it stays in `#blind-reveal-text` for that farm. Nothing in the simulation depends on it (tested: identical `get_state()` with and without a blind run), so a blind farm is still ranked and the leaderboard gap report is unchanged. Known leaks, left on purpose: the Outperforming Baseline achievement and the rating ladder's rule text can still hint at the result, and the opt-in leaderboard shows the player's own gap only if they opted in. Tests: `tests/test_blind_run.py` (11).

## Starting loadouts (GF-23, 2026-10-11)

`LOADOUTS` (standard plus Big Herd, Lean Green, Poultry Start, Cash Rich; each unlocked by an achievement: Major Operation, Full Toolkit, Sustainably Certified, Score 400) bends the opening funds and levers. Every loadout is a symmetric set of deltas (`_shift_loadout(target, id, +1/-1)`): Big Herd +4 animals for -90 funds (baseline funds -90 too, it pays for the same herd), Lean Green one of each decoupling measure for -50 (baseline funds untouched, the measures are what is being tested), Poultry Start two birds and an open flock for -25 (`poultry_unlocked()` also true for that loadout), Cash Rich +150 funds and 12 methane on the books (baseline too). `choose_loadout()` applies at once while `farm_is_pristine()` (round 1, nothing bought; the loadout's own gifts do not count as play, so Ranch Rules' starting-funds slider still works on such a farm), taking back the old loadout first; on a started farm it only stores the choice for the next generation. `hand_over_farm()` applies legacy perks, then the chosen loadout. State: `farm.loadout` (per farm), module-level `loadouts_unlocked` and `loadout_choice` (survive a handover and an undo, like breeds and barns), saved as `loadout`, `loadouts_unlocked`, `loadout_choice` only when not default and validated on load (real ids, "standard" never in the unlocked list, a choice must be unlocked). A loadout makes the run unranked: `rules_unranked()` is true for it (leaderboard, other-farms comparison, the Score 400 achievement and the ledger's custom flag all follow), with its own wording through `unranked_compare_note()`, the rules badge and `rules_summary_message()`. Unlocks are recorded by `_sync_loadouts()` inside `_sync_collection()` (the Collection toast names them). Loadouts exist only inside a loaded save's session (a fresh page has nothing unlocked), so "a new game" means the next generation. Panel `#loadout-panel` (collapsed details; Desktop: side column): a select (rebuilt only when the unlocked set changes), a note, the list with unlock hints, a polite status line. Tests: `tests/test_loadouts.py` (16).

## Regulator audits (GF-3, FY-29, 2026-10-11)

At the end of every `AUDIT_EVERY` (10th) round `FarmState.advance_round()` ends with `_run_audit()` (round counter 11, 21, ...; a save from round 37 gets its first audit at the end of round 40). Two targets, both on screen from round 1 in `#audit-panel` (side column on Desktop), tighten with the audit number: coupling ratio `audit_coupling_target(n)` 0.90, 0.80, 0.70, then 0.60 for good; welfare `audit_welfare_target(n)` 55, then 60 for good. The panel names the numbers, the current values and "met" or "not met yet" in words, and from `AUDIT_WARNING_ROUNDS` (3) rounds before it carries a "Warning:" headline, an amber border and a warning sign (never colour alone). Pass: the next unowned perk of `AUDIT_PERKS` (Regulator's Goodwill, +3% income through the new `audit` factor in `income_breakdown()` and the inspector; Green Loan Terms, decoupling levers cost 1 less (never below 1, applied before subsidies); Friendly Inspector, a later fine is halved and the trust hit halved), then 40 funds per later pass. Fail: a fine of one round's income (`AUDIT_FINE_INCOME_ROUNDS` 1.0, never more than the funds, so a farm that earns nothing is never fined and `test_scoring`'s "pure restraint" still ends at exactly 300) and 3 rounds of -5% income (`trust_rounds_left`). Fines and bonuses go to the real farm only (the baseline is untouched) and update the last `funds_history` entry, so an audit cannot fake or hide a perfect round. Deterministic, no opt-out switch (mild, visible and bounded; balance values chosen under FY-29). The result goes to the polite round announcer, the milestone toast (merged into the one nudge or callout toast of that round so it is not overwritten, through `_check_milestone_callout(prefix)`) and the report card ("Regulator audits: N passed of M. Perks: ..."). New per-farm state `audits_done`, `audit_log` (last 10 as [number, round, passed]), `audit_perks`, `trust_rounds_left`, saved only once an audit happened or something is pending, validated on load (log entries need numbers >= 1 and a 0/1 flag, perks must be real and unique, trust clamped to 0-3). A handover starts a new record. The planner's scratch copy plays audits too (so a projection includes them) without touching the real record. Tests: `tests/test_audits.py` (23).

## Practice sandbox (GF-24, 2026-10-11)

Built on the shared `shared/sandbox-mode.js` / `.css` (Grid, Continuum and Trade Empire pattern): `#sandbox-toggle-button` (`data-sandbox-toggle`; in the Classic toolbar and the Desktop Menu's Game group) plus the script tag after the save widget, and `sandbox_enter()` / `sandbox_leave()` / `sandbox_is_active()` in game.py. Entering stashes the real farm object and a snapshot (`_sandbox_real`) and puts a `SandboxFarmState` in `farm` (funds never drop below `SANDBOX_FUNDS`, 1,000,000, so anything can be bought; `poultry_unlocked()` is true there). Module-level values that a save or the browser could carry are stashed too (`_SANDBOX_STASHED`: generation, legacy points and perks, breeds, combos, hall of fame, family endings, barns, loadouts, pins, ranch rules, the record, session displays); the collections are deep-copied for the sandbox and the ORIGINAL objects are put back on leaving, so `get_state()` is byte-identical before and after and `farm` is the very same object. The guards that keep it sealed: `get_state()` answers with a deep copy of the real snapshot while on (Save, autosave and the leaderboard hook can only ever see the real game); `_write_local_storage_item()` is a no-op (rules, record, ledger, pins); `achievement_ids_earned()` returns the real list (no toast, no progress lines); `_sync_collection()` returns at once (no breed, combo, barn or loadout); `_maybe_update_record_coupling_ratio()` returns at once; `rules_unranked()` is true (no leaderboard line, no other-farms comparison, the ledger would say custom); `set_rule`, undo (`can_undo()` false and no undo snapshot is taken), handover (`can_hand_over()` false), the ledger buttons and the settings-code import are refused; `load_state()` of a valid save leaves the sandbox first (a broken save leaves it on) and tells the page via `NoyvjSandbox.sync()`. The sandbox panel `#sandbox-panel` (side column on Desktop; hidden outside the sandbox) has seven sliders (herd 0-80, methane 0-300, Feed, Caps, Capture, Plant-Based Pivot, poultry flock; `SANDBOX_CONTROLS` clamps and snaps; nonsense values are ignored) and a "Start the practice farm over" button; the buy buttons, Advance Round, the planner and audits all work on the practice farm. Funds read "unlimited (sandbox)" and the score "not counted (sandbox)" in the readouts, pins and the Copy result line ("Herd (practice sandbox)"). Memory only: a reload is the real game. Tests: `tests/test_sandbox.py` (16). New files fetched by the page: `shared/sandbox-mode.js` and `shared/sandbox-mode.css`.

- **Ghost of your best farm (Z-3e and GF-4's ghost half, 2026-10-12).** Herd opts in to `shared/ghost.py` (written to the Pyodide filesystem as `ghost.py` in `index.html`; `pc.html` regenerated). GF-4's rival ranches (Big Ag Barry, Organic Olive, a community median) and the live scoreboard strip are NOT built; only the "ghost of your own best farm" part is. A farm is Herd's run: it ends by handover (`hand_over_farm`) or when the player files it in the Ranch Ledger, and `file_ghost()` runs at exactly those two points, next to `ledger_record`. Two numbers per round are fed through `ghost.Recorder` from `farm_series()` (score = funds minus `METHANE_PENALTY_WEIGHT` times methane, and methane itself, read from `funds_history`/`methane_history` index 1..n; a farm whose funds history has any unknown round, i.e. a save from before it, gives None and is simply not filed). Kept per farm mode (`plain`, `seasons`, `cap`, `seasons_and_cap`) when the farm has at least `GHOST_MIN_ROUNDS` (4) rounds, is ranked (`rules_unranked()` false: no sandbox, custom rules or non-standard loadout) and its `score - counterfactual_score` is at least the stored one (latest wins a tie, the same measure as the Ledger's "best result"). Storage: localStorage `herd-ghost-v1` ({mode: {gen, result, score: trace, methane: trace}}, written only once a ghost exists, never part of `get_state()`, so saves are unchanged; `load_ghosts()` cleans both traces with `ghost.load`, requires equal lengths and drops unknown modes). Display: `methane_trend_graph_svg(history, ghost=None)` draws the ghost's methane as a dashed 50%-opacity line (`data-testid="ghost-line"`, the scale grows to include it, nothing drawn past the ghost's last round, svg gets `role="img"` and the sentences as its label); `#ghost-note` (`role="status"`) shows the shared `ghost.summary` sentences: score first, then "Methane (lower is better):" with the methane comparison (`higher_is_better=False`). Plain sentences cover no ghost yet, no round yet, a save without funds history, sandbox/custom farms; nothing is shown during a hidden blind run. `#ghost-toggle` (shown once a ghost exists, `herd-ghost-on`, default on) hides line and note without deleting the ghost. Tests: `tests/test_shared_ghost.py`.

## Round 4 view ideas, audited (2026-10-17)

Seven local-model ideas were audited and rebuilt where they were dead. **Phone view** (all in `style.css` inside the `max-width: 600px` block, behaviour in `app.js`, a per-device calm-barn flag in `localStorage["herd-calm-barn"]`, never in a save): R4-HEMO-2 thin fixed top strip (`#mobile-top-strip`: round, funds, methane and a Stable/Rising/High word read from the pressure line, bands at 10 and 25 percent income loss; it hides the shared `#mobile-hud-bar`, which carried the same numbers); R4-HEMO-4 methane thermometer (`#methane-thermometer`, a button in the right gutter outside `#game`, because `#game`'s backdrop blur would trap a fixed child; the tube fills with the pressure line up to the game's 80 percent cap; a tap opens "Why this number?" on methane); R4-HEMO-7 Calm barn (`#calm-barn-toggle`, dims the pasture, slows the animals to 14 s, 14 s and 160 s loops, keeps only the pasture, one honest word, Advance Round and the notices, and has a visible "Leave calm barn" button; everything not marked `calm-keep` is hidden); R4-HEMO-8 herd-size slider (`herd_slider_plan()` / `render_herd_slider()` / `on_herd_slider_buy()` in `game.py`: the handle runs from the herd now to what the funds allow, the numbers come from `clone_farm` and `income_breakdown`, the button buys exactly those units through `_guarded_purchase`; nothing is saved); R4-HEMO-3 lever shelf (`#mobile-lever-shelf` wraps Grow Herd, the decoupling card and the pivot card as a sideways-scrolling row, with Advance Round moved to sit directly after it; the Decoupling tile is still tall, so it is a partial). **Desktop view** (`pc.js`, `pc.css`; no `pc-config.json` change, both pieces are built at run time): R4-HEPC-4 hold I builds `.pasture-label` boxes inside the pasture while the key is down (cleared on release or blur, ignored while typing); R4-HEPC-3 right-click menu on a lever (Buy presses the lever's own button, Pin as a goal is a per-device Goal badge in `localStorage["herd-pinned-goals"]`, Show cost over time opens the Collection window filtered to that lever, Compare opens the Baseline window). Tests: `tests/test_ai_round4_audit.py` (engine plus wiring) and `tests/test_ai_round4_browser.py` (one Pyodide boot per page).


## Design specs (LA-13)

Written 2026-10-22 (LA-13 design pass, batch 2). Steps: `local-ai/incoming/herd-design.txt`. Standing rules hold for
every item: nothing timed, nothing lost, no luck needed for 100%, no audio files, saves load unchanged. R4-PH-2
(Extension Officer, a whole new mode) is not designed in this batch.

### GF-2: the legacy perks as a visible upgrade tree, with early goals every generation chases
- **The tree.** The three existing perks keep their names, costs, levels and effects; four new perks join them, and the
  seven are shown as a tree in three branches with the shared skill-tree component (W-3), above the existing perk
  buttons (which stay, as the keyboard and screen-reader way to buy; a button of a perk whose requirement is not owned
  is disabled and its title says what it needs):

| Branch | Perk (id) | Cost | Needs | Effect |
|---|---|---|---|---|
| Savings | Family Savings (`family_savings`, 3 levels, drawn as 3 nodes) | 1 each | the level before | +75 starting funds per level (unchanged) |
| Herd | Mentor's Methods (`mentor_methods`) | 2 | | starts with 1 Feed Additives unit (unchanged) |
| Herd | Biogas Inheritance (`capture_start`) | 2 | Mentor's Methods | starts with 1 Methane Capture unit |
| Herd | Heritage Breeding Line (`heritage_line`) | 3 | Biogas Inheritance | breeding investments mature in 2 rounds instead of 3 |
| Farm | Heritage Flock (`heritage_flock`) | 2 | | poultry from round 1 (unchanged) |
| Farm | Second Opinion (`second_opinion`) | 2 | Heritage Flock | once per generation, ask the policy advisor for a different pair |
| Farm | Heritage Farmhouse (`heritage_farmhouse`) | 1 | Second Opinion | a farmhouse barn style for the pasture (looks only) |

  The TODO's "rare breed with better breeding odds" is made deterministic (no luck): the heritage line breeds true, so
  breeding simply matures a round sooner. "A second policy-advisor option" is the Second Opinion: a fresh pair from the
  advisor's fixed pool (the same no-repeat order the advisor already uses), once per generation.
- **Early goals each generation chases.** Handover points become: 1 (as now) + 1 for a flock of 3 or more (as now)
  + 1 when the farm was certified by round 15 (`CERT_EARLY_ROUND`). The succession panel lists both goals with ✓ or ○
  and the round. Simulated against the real `FarmState` (growing the herd each round when funds allow): certification
  comes at round 7 to 9 with capture or mixed levers, 13 with caps only, 17 with feed only, never with no levers; so
  round 15 rewards using the levers early and never needs luck. Full tree: 15 points, about 5 to 8 generations.
- **Saves.** Perks stay in `legacy_perks` (the loader already accepts every `LEGACY_PERKS` key, clamped to its max;
  old saves keep their perks). New farm keys, each written only when not default: `certified_round` (int, set the round
  certification is earned; an older certified save has none and simply gets no early bonus) and `second_opinion_used`
  (`True` only). Both validated in `herd_loading.py`.
- **Engine code.** `herd_succession.py`: add a `"branch"` key to the three existing `LEGACY_PERKS` entries
  (`family_savings`: `"savings"`, `heritage_flock`: `"farm"`, `mentor_methods`: `"herd"`) and add these four entries at
  the end of the dict:

```python
    "capture_start": {"label": "Biogas Inheritance", "cost": 2, "max": 1, "branch": "herd", "requires": ["mentor_methods"],
                      "blurb": "Every generation starts with one Methane Capture unit already in place."},
    "heritage_line": {"label": "Heritage Breeding Line", "cost": 3, "max": 1, "branch": "herd", "requires": ["capture_start"],
                      "blurb": "The heritage line breeds true: breeding investments mature in 2 rounds instead of 3."},
    "second_opinion": {"label": "Second Opinion", "cost": 2, "max": 1, "branch": "farm", "requires": ["heritage_flock"],
                       "blurb": "Once per generation, ask the policy advisor for a different pair of options."},
    "heritage_farmhouse": {"label": "Heritage Farmhouse", "cost": 1, "max": 1, "branch": "farm", "requires": ["second_opinion"],
                           "blurb": "A farmhouse barn style for the pasture picture. Looks only."},
```

  and, directly after `FAMILY_SAVINGS_FUNDS = 75`:

```python
CERT_EARLY_ROUND = 15  # GF-2: a farm certified by this round earns one more legacy point on handover
SUCCESSION_EARLY_CERT_POINTS = 1


def perk_requirements_met(name):
    return all(runstate.legacy_perks.get(req, 0) >= 1 for req in LEGACY_PERKS[name].get("requires", []))


def generation_goals():
    """GF-2: the two early goals every generation chases, as [(text, done)]."""
    farm = runstate.farm
    early = farm.certified_round is not None and farm.certified_round <= CERT_EARLY_ROUND
    return [
        (f"Certified by round {CERT_EARLY_ROUND} (+{SUCCESSION_EARLY_CERT_POINTS} point)"
         + (f": done in round {farm.certified_round}" if early else ""), early),
        (f"A flock of {SUCCESSION_FLOCK_MIN_SIZE} poultry (+{SUCCESSION_FLOCK_BONUS_POINTS} point)",
         farm.poultry_size >= SUCCESSION_FLOCK_MIN_SIZE),
    ]
```

  `handover_points()`: directly before its `return points` add
  `if runstate.farm.certified_round is not None and runstate.farm.certified_round <= CERT_EARLY_ROUND:` /
  `points += SUCCESSION_EARLY_CERT_POINTS  # GF-2`. `buy_legacy_perk`: directly after the line
  `if level >= spec["max"] or runstate.legacy_points < spec["cost"]:` and its `return False`, add
  `if not perk_requirements_met(name):` / `return False`. `_apply_perk_to_farm`: add the branches
  `elif name == "capture_start":` / `runstate.farm.decoupling_investment["capture"] += 1` and
  `elif name == "heritage_farmhouse" and "farmhouse" not in runstate.barns_unlocked:` /
  `runstate.barns_unlocked.append("farmhouse")`. `herd_model.py` `FarmState.__init__`: directly after
  `self.certified = False` add `self.certified_round = None  # GF-2` and `self.second_opinion_used = False  # GF-2`;
  in `advance_round` directly after `self.certified = True` add `self.certified_round = self.round_number`;
  `invest_genetics`: change `self.genetics_pending.append(GENETICS_MATURE_ROUNDS)` to
  `self.genetics_pending.append(GENETICS_MATURE_ROUNDS - (1 if runstate.legacy_perks.get("heritage_line", 0) else 0))  # GF-2`;
  directly after `choose_policy` add:

```python
    def ask_second_opinion(self):
        """GF-2: with the Second Opinion perk, once per generation, a fresh pair from the advisor's fixed pool."""
        if not self.policy_offer_pending or self.second_opinion_used or not runstate.legacy_perks.get("second_opinion", 0):
            return False
        self.policy_offer = self.draw_policy_offer()
        self.second_opinion_used = True
        return True
```

  `herd_savegame.py` `get_state()`, next to the other only-when-not-default fields:
  `if runstate.farm.certified_round is not None: state["certified_round"] = runstate.farm.certified_round` and
  `if runstate.farm.second_opinion_used: state["second_opinion_used"] = True`. `herd_loading.py`: directly after
  `runstate.farm.certified = bool(data.get("certified", False))` add
  `saved_cert_round = _safe_int(data.get("certified_round"), 0)` /
  `runstate.farm.certified_round = saved_cert_round if runstate.farm.certified and saved_cert_round >= 1 else None  # GF-2`
  and directly after the `policy_offer_pending` line
  `runstate.farm.second_opinion_used = data.get("second_opinion_used") is True  # GF-2`.
- **Engine tests, NEW file `tests/test_legacy_tree.py`** (`game_env` fixture; `m = game_env.module`):

```python
"""LA-13 / GF-2: the legacy tree, its requirements, the new perks and the early goals."""


def test_new_perks_need_their_branch_first(game_env):
    m = game_env.module
    m.legacy_points = 10
    assert m.buy_legacy_perk("capture_start") is False
    assert m.buy_legacy_perk("mentor_methods") is True and m.buy_legacy_perk("capture_start") is True
    assert m.legacy_points == 6 and game_env.farm.decoupling_investment["capture"] == 1


def test_inherited_capture_and_the_heritage_line(game_env):
    m = game_env.module
    m.legacy_perks = {"mentor_methods": 1, "capture_start": 1, "heritage_line": 1}
    game_env.farm.funds = 500
    game_env.farm.invest_genetics()
    assert game_env.farm.genetics_pending == [2]


def test_second_opinion_once_per_generation(game_env):
    m = game_env.module
    farm = game_env.farm
    farm.policy_offer_pending = True
    farm.policy_offer = farm.draw_policy_offer()
    first = list(farm.policy_offer)
    assert farm.ask_second_opinion() is False  # no perk yet
    m.legacy_perks = {"heritage_flock": 1, "second_opinion": 1}
    assert farm.ask_second_opinion() is True and farm.policy_offer != first and len(farm.policy_offer) == 2
    assert farm.ask_second_opinion() is False


def test_early_certification_is_a_goal_worth_a_point(game_env):
    m = game_env.module
    farm = game_env.farm
    farm.certified = True
    farm.certified_round = 12
    assert m.handover_points() == 2
    assert m.generation_goals()[0][1] is True
    farm.certified_round = 16
    assert m.handover_points() == 1 and m.generation_goals()[0][1] is False


def test_the_new_fields_save_only_when_set(game_env):
    m = game_env.module
    state = m.get_state()
    assert "certified_round" not in state and "second_opinion_used" not in state
    game_env.farm.certified, game_env.farm.certified_round, game_env.farm.second_opinion_used = True, 9, True
    m.load_state(m.get_state())
    assert game_env.farm.certified_round == 9 and game_env.farm.second_opinion_used is True
```

- **The tree data** (second step), `herd_succession.py` at the end (`json` imported at the top):

```python
# ---- GF-2: the legacy perks as a tree for the shared skill-tree component (Python owns the state) ----
LEGACY_BRANCHES = [
    {"id": "savings", "title": "Savings", "blurb": "Money the family puts by."},
    {"id": "herd", "title": "Herd", "blurb": "Know-how and kit passed down with the cows."},
    {"id": "farm", "title": "Farm", "blurb": "The flock, the advisor and the farmhouse."},
]


def _node_ids(name):
    spec = LEGACY_PERKS[name]
    return [f"{name}_{n}" for n in range(1, spec["max"] + 1)] if spec["max"] > 1 else [name]


def legacy_tree():
    nodes = []
    for name, spec in LEGACY_PERKS.items():
        ids = _node_ids(name)
        for n, node_id in enumerate(ids):
            requires = [ids[n - 1]] if n else list(spec.get("requires", []))
            label = spec["label"] + (f" {n + 1}" if len(ids) > 1 else "")
            nodes.append({"id": node_id, "branch": spec["branch"], "cost": spec["cost"], "label": label,
                          "description": spec["blurb"], "requires": requires})
    return {"id": "herd-legacy", "title": "Family legacy", "currency": "legacy points",
            "branches": LEGACY_BRANCHES, "nodes": nodes}


def legacy_tree_json():
    """For legacy-tree.js: the tree, the owned node ids and the points ever earned."""
    owned = []
    spent = 0
    for name, level in runstate.legacy_perks.items():
        owned += _node_ids(name)[:level]
        spent += LEGACY_PERKS[name]["cost"] * level
    return json.dumps({"tree": legacy_tree(), "owned": owned, "earned": runstate.legacy_points + spent})


def buy_legacy_node(node_id):
    """Buys the perk level a tree node stands for (only the next level of a multi-level perk). Returns the new JSON."""
    node_id = str(node_id)
    for name in LEGACY_PERKS:
        ids = _node_ids(name)
        if node_id in ids and ids.index(node_id) == runstate.legacy_perks.get(name, 0):
            buy_legacy_perk(name)
    return legacy_tree_json()
```

  `game.py`: add `legacy_tree_json, buy_legacy_node` to its imports from `herd_succession` so the page can reach them.
  Tests (append): `test_the_tree_matches_the_perks` (`json.loads(m.legacy_tree_json())`: 9 nodes, the three
  `family_savings_N` ids chained by `requires`, `capture_start` requires `["mentor_methods"]`, `owned == []`, `earned == 0`);
  `test_buying_through_the_tree` (`m.legacy_points = 3`; `buy_legacy_node("family_savings_2")` buys nothing;
  `buy_legacy_node("family_savings_1")` gives owned `["family_savings_1"]`, earned 3, `m.legacy_points == 2`).
- **Page** (third and fourth steps). Python side: `render_succession` (after its perk-button loop) sets each perk
  button's `disabled` also when `not perk_requirements_met(name)` and its `title` to
  `spec["blurb"] + (" Needs " + ", ".join(LEGACY_PERKS[r]["label"] for r in spec.get("requires", [])) + "." if not perk_requirements_met(name) else "")`;
  writes `#succession-goals` as one `<li>` per `generation_goals()` entry ("✓ " or "○ " + text); shows
  `#policy-second-opinion-button` (in the policy panel) only when the perk is owned and not used this generation;
  handler `on_second_opinion` (`herd_handlers_play.py`): `runstate.farm.ask_second_opinion()` then `render()`.
  `herd_barns.py`: a seventh `BARN_SKINS` entry
  `{"id": "farmhouse", "label": "Heritage Farmhouse", "glyph": "\U0001F3E1", "unlock": "legacy:heritage_farmhouse"}`
  and, in `barn_card_state` directly above its final `return`, `if skin["unlock"] == "legacy:heritage_farmhouse":` /
  `return "Locked", True, "Buy the Heritage Farmhouse legacy perk."`. CSS (`style-5-round7.css`, after the gold barn):
  `.pasture-visual[data-barn="farmhouse"] { --barn-wall: #f1e3c6; --barn-roof: #7a4b2a; --barn-trim: #ffffff; --fence: #b88a5a; --barn-mark: "\1F3E1"; --tractor-filter: sepia(0.4); }`.
  Markup (`index.html`, inside `#succession-panel`): directly after `#succession-display`:
  `<ul id="succession-goals" class="succession-goals"></ul><div id="legacy-tree" class="legacy-tree"></div>`; after
  the `perk-mentor-methods-button` row, four rows in the same shape for `perk-capture-start-button`,
  `perk-heritage-line-button`, `perk-second-opinion-button`, `perk-heritage-farmhouse-button`; in the policy panel
  directly after `#policy-cash-button`:
  `<button id="policy-second-opinion-button" class="secondary" hidden>Ask for a second opinion</button>`. Scripts,
  directly after the `feedback.js` (or last game) script tag: the shared skill-tree tag
  (`<script src="../../` + `shared/skill-tree.js"></script>`) then `<script src="legacy-tree.js"></script>`. NEW file
  `legacy-tree.js`:

```js
// GF-2: the legacy perks drawn as a tree with the shared skill-tree component. Python owns the state:
// legacy_tree_json() gives {tree, owned, earned}; buy_legacy_node(id) buys and returns the same JSON.
(function () {
  "use strict";
  var view = null;
  function call(name, arg) {
    var fn = window.pyodide && window.pyodide.globals.get(name);
    if (!fn) { return null; }
    return JSON.parse(arg === undefined ? fn() : fn(arg));
  }
  function draw() {
    var box = document.getElementById("legacy-tree");
    var panel = document.getElementById("succession-panel");
    if (!box || !panel || panel.hidden || !window.NoyvjSkillTree) { return; }
    var data = call("legacy_tree_json");
    if (!data) { return; }
    if (view) { view.update({ owned: data.owned, earned: data.earned }); return; }
    view = window.NoyvjSkillTree.render(box, {
      tree: data.tree, owned: data.owned, earned: data.earned,
      onBuy: function (id) {
        var after = call("buy_legacy_node", id);
        if (!after) { return; }
        view.update({ owned: after.owned, earned: after.earned });
        var render = window.pyodide.globals.get("render");
        if (render) { render(); }
      }
    });
  }
  var display = document.getElementById("succession-display");
  if (display) {
    new MutationObserver(draw).observe(display, { childList: true, characterData: true, subtree: true });
  }
})();
```

  `tests/conftest.py` `ELEMENT_IDS`: the four new perk buttons, `succession-goals`, `legacy-tree`,
  `policy-second-opinion-button`; `game.py`: the four perk buttons in the `_make_perk_handler` list and
  `("policy-second-opinion-button", on_second_opinion)`. `pc-config.json`: nothing (the panel already exists).
  Browser test NEW `tests/test_legacy_tree_browser.py`: load a save through `load_state` with `generation: 2`,
  `legacy_points: 3` (`page.evaluate` calling `window.pyodide.globals.get("load_state")` with a dict from `get_state()`
  plus those keys, the way `tests/test_save_widget.py` does), then `#succession-panel` is visible, `#legacy-tree` holds
  9 nodes (count the component's node buttons inside it), clicking `#perk-family-savings-button` lowers the points in
  `#succession-display` to 2; `page.errors == []`.

### R4-PH-2: Extension Officer, a helper mode where you advise three computer-run farms
Written 2026-10-22 (LA-13, after batch 2). Steps: `local-ai/incoming/herd-design.txt`, chain `R4-PH-2` (7 steps). A small
first version; the open choices are listed at the end as owner questions with a recommended default.

- **What it is.** A separate panel (`#extension-panel`, opened from a toolbar button `#extension-toggle-button`,
  "🤝 Extension Officer") with its own short season. You are the regional extension officer; three neighbouring farms
  run themselves and keep growing. Each round you can make **2 visits**, **at most one per farm**; a visit installs one
  unit of one lever on that farm, paid by an extension grant (the farm's own funds never change). Then you end the round
  and all three farms play it out. A season is **8 rounds**. Your score is the **methane avoided**: what the three
  farms emitted less than the same three farms given no advice (each farm has an unadvised twin, its "shadow", that
  plays the same rounds). The panel also says how much more the advised farms earned (less methane pressure), the
  hope angle in one line: decoupling paid them, it did not cost them.
- **The three farms** (`EXT_FARMS`; each is a real `FarmState` from `herd_model.py`, never `runstate.farm`):

| # | Farm | Starts with | Grows each round | Limit | Best lever at the start |
|---|------|-------------|------------------|-------|-------------------------|
| 0 | Hillside Dairy | 12 cattle | +1 cattle | Capture Systems at most 2 (the slurry pit) | Capture Systems, cuts 1.2 a round; then Herd Caps |
| 1 | Brookside Mixed | 4 cattle, 20 poultry (`loadout = "poultry_start"` so `poultry_unlocked()` is true) | +2 poultry | Capture Systems at most 1 | Ventilation Biofilters, cuts 1.0 a round, growing with the flock |
| 2 | Old Mill Network | 6 cattle, a satellite farm of 10 (`satellite_open`) | nothing | none | Retrofit Barns, cuts 0.8 a round (capture at home only 0.6) |

  The levers a visit can install (`EXT_LEVERS`, also the tie order): `capture caps feed pivot biofilter litter
  satellite_retrofit`. Each farm's card shows only the levers that would cut something there, each as a button with
  its number ("Capture Systems: cuts 1.20 a round", from the engine's own `FarmState.methane_saved_by(key)`, so the
  satellite network offset and the plant-pivot blend are included). That number is the lesson: the same lever is
  worth different amounts on different farms, and the best one changes as you install it.
- **Rules.** Unspent visits carry over to the next round (nothing lost), but each farm still takes one visit a round.
  "Take back last visit" undoes a visit made this round (it rebuilds the season from the visit list); ended rounds stay.
  After round 8 the season is over: the panel shows the result and "Start a new season" (the best result is kept).
  Nothing is timed (rounds end only on the button) and nothing is random (the farms are fixed data and a season is
  rebuilt from its visit list). While the practice sandbox is open the panel's buttons are disabled and every action
  returns False, because a save made in the sandbox writes the real game's snapshot.
- **Stars, and why no luck is needed for 100 percent.** Par is the score of an officer who always takes the visit
  with the biggest cut per round right now (`ext_best_visit()`, ties broken by farm order then `EXT_LEVERS` order):
  **93.2**. Three stars at par, two stars from 75 percent of par (69.9), one star for any help. Simulated against the
  real `FarmState` (a scratch copy, 2026-10-22): an exhaustive search over all 3^8 = 6,561 ways to pick two farms each
  round (each visit taking that farm's best lever) found nothing above 93.2, so par is the best a season can do and the
  numbers on the buttons lead straight to it. Other plans: every farm's best lever but visiting the farms in turn
  88.2 (two stars); cattle levers only (capture, then caps, then feed) 72.6 (two stars); capture then caps on the
  first two farms only 55.4 (one star); feed only 29.8 (one star); no visits 0. The greedy season, round by round:
  Hillside capture + Brookside biofilter (rounds 1-2), Brookside biofilter + Hillside caps (3-5), Hillside caps + Old
  Mill retrofit (6-8); it avoids 45.4, 43.0 and 4.8 on the three farms and they earn 200.9 more.
- **What counts, visibly.** The season's methane avoided and stars, and the best season (avoided, stars, seasons
  played) in the panel's status line and on the toolbar button ("🤝 Extension Officer (3/3)").
  It does not touch the main farm, its score, the leaderboard, achievements or legacy points (owner questions below).
- **Saves.** Two new keys, each written only when not default, both validated in `ext_load()` and both absent from
  older saves (which load into a fresh season): `extension` = `{"round": int, "visits": [[round, farm index, lever],
  ...]}` (only once a round has ended or a visit was made) and `extension_best` = `{"avoided": float, "stars": 0-3,
  "seasons": int >= 1}` (only once a season has ended). Loading replays the visits through `ext_visit()`, so a
  malformed or impossible visit is simply dropped; a bad `extension_best` is dropped whole. The season itself lives in
  the module dict `EXT` (changed in place, never rebound, so it is not a `herd_runstate` name and the sandbox never
  swaps it). The farm handover keeps it (you are the officer, not the farmer).
- **Must not break.** `get_state()` of a game that never opened the panel is unchanged (`test_save_widget.py`,
  `test_sandbox.py` byte-identical); the main farm is never read or written by the mode; `coupling_ratio()` and every
  `FarmState` method are used as they are (no engine change); `index.html` gains about 230 bytes (cap 14,800 tokens in
  `test_file_sizes.py`). The new module is placed after `herd_profile` in `_PART_NAMES` and `HERD_PY_MODULES`; after the
  chain merges, run `python scripts/sw-precache-game.py herd`, `python scripts/generate-offline-manifest.py` and
  `python scripts/generate-pc-pages.py` (the local AI never touches those).
- **Checked on a scratch copy outside the repo (2026-10-22):** every block below applied in step order, each step's
  tests passing at that step; then Herd's whole non-browser suite and the new browser test passed, and
  `shared/tests/test_pc_games.py -k herd` passed after regenerating `pc.html`.

- **Block 1, NEW file `herd_extension.py` (step 1), VERBATIM:**

```python
"""Extension Officer (R4-PH-2, LA-13): a helper mode. You advise three computer-run farms over a short season, spending a
few visits a round on the lever that cuts each farm's methane most; your score is the methane they did not emit.
The client farms are real FarmState objects (herd_model.py) and never touch runstate.farm. Nothing is random: every
client farm is built from EXT_FARMS and replayed from the saved list of visits, so a season always plays the same way.
"""

from herd_rules import DECOUPLING_MEASURES, POULTRY_MEASURES
from herd_model import FarmState

EXT_ROUNDS = 8  # rounds in one advisory season
EXT_VISITS_PER_ROUND = 2  # visits you can make each round; unspent visits carry over to the next round
EXT_GRANT = 1000.0  # the extension grant covers a lever's price, so the farm's own funds never change
EXT_LEVERS = ("capture", "caps", "feed", "pivot", "biofilter", "litter", "satellite_retrofit")  # also the tie order
EXT_FARMS = [
    {"name": "Hillside Dairy", "herd": 12, "grow_herd": 1, "grow_poultry": 0, "poultry": 0, "satellite": 0,
     "limits": {"capture": 2},
     "blurb": "A big dairy herd that adds a cow every round. Its slurry pit fits only two capture units."},
    {"name": "Brookside Mixed", "herd": 4, "grow_herd": 0, "grow_poultry": 2, "poultry": 20, "satellite": 0,
     "limits": {"capture": 1},
     "blurb": "A few cattle and a big poultry flock that grows by two birds every round."},
    {"name": "Old Mill Network", "herd": 6, "grow_herd": 0, "grow_poultry": 0, "poultry": 0, "satellite": 10,
     "limits": {},
     "blurb": "A small home farm running an old, dirty satellite farm of ten cattle."},
]
EXT_STAR_SHARE = 0.75  # two stars from this share of par, three stars at par

# The season in play. Changed in place only (never rebound), so it lives here and not in herd_runstate.
EXT = {"round": 1, "visits": [], "farms": [], "shadows": [], "best": None}
_EXT_PAR = []  # cached par (the greedy officer's score); filled on first use


def _ext_new_farm(spec):
    farm = FarmState()
    farm.herd_size = spec["herd"]
    if spec["poultry"]:
        farm.loadout = "poultry_start"  # poultry_unlocked() reads the loadout
        farm.poultry_size = spec["poultry"]
    if spec["satellite"]:
        farm.satellite_open = True
        farm.satellite_size = spec["satellite"]
    return farm


def _ext_lever_count(farm, lever):
    if lever in DECOUPLING_MEASURES:
        return farm.decoupling_investment[lever]
    if lever in POULTRY_MEASURES:
        return farm.poultry_investment[lever]
    if lever == "pivot":
        return farm.plant_pivot_investment
    return farm.satellite_retrofits


def ext_lever_saving(index, lever, farms=None):
    """Methane per round one more unit of this lever would remove on client farm `index` (0 when not allowed)."""
    farm = (farms or EXT["farms"])[index]
    limit = EXT_FARMS[index]["limits"].get(lever)
    if limit is not None and _ext_lever_count(farm, lever) >= limit:
        return 0.0
    if lever == "satellite_retrofit" and not farm.satellite_open:
        return 0.0
    return round(farm.methane_saved_by(lever), 4)


def _ext_install(farm, lever):
    funds = farm.funds
    farm.funds = funds + EXT_GRANT
    if lever in DECOUPLING_MEASURES:
        ok = farm.invest_decoupling(lever)
    elif lever in POULTRY_MEASURES:
        ok = farm.invest_poultry(lever)
    elif lever == "pivot":
        ok = farm.invest_plant_pivot()
    else:
        ok = farm.retrofit_satellite()
    farm.funds = funds
    return ok


def _ext_advance_farms(farms, shadows):
    for index, spec in enumerate(EXT_FARMS):
        for farm in (farms[index], shadows[index]):
            farm.advance_round()
            farm.herd_size += spec["grow_herd"]
            farm.poultry_size += spec["grow_poultry"]


def ext_avoided(farms=None, shadows=None):
    """Methane the client farms did not emit, compared with the same farms given no advice."""
    farms, shadows = farms or EXT["farms"], shadows or EXT["shadows"]
    return round(sum(s.methane - f.methane for f, s in zip(farms, shadows)), 1)


def ext_income_gain():
    """Extra funds the advised farms earned (less methane pressure), compared with no advice."""
    return round(sum(f.funds - s.funds for f, s in zip(EXT["farms"], EXT["shadows"])), 1)
```

- **Block 2 (step 2).** Directly above the line `from herd_rules import DECOUPLING_MEASURES, POULTRY_MEASURES` add
  `import herd_runstate as runstate`; then append at the end of `herd_extension.py`, VERBATIM:

```python
def ext_visits_left():
    used = sum(1 for visit in EXT["visits"] if visit[0] <= EXT["round"])
    return max(0, EXT_VISITS_PER_ROUND * min(EXT["round"], EXT_ROUNDS) - used)


def ext_finished():
    return EXT["round"] > EXT_ROUNDS


def ext_visited_this_round():
    """Farm indexes already visited this round (each farm takes at most one visit a round)."""
    return {visit[1] for visit in EXT["visits"] if visit[0] == EXT["round"]}


def ext_visit(index, lever):
    """One visit: client farm `index` installs one unit of `lever`. False (and no change) when not allowed."""
    if not isinstance(index, int) or not 0 <= index < len(EXT_FARMS) or lever not in EXT_LEVERS:
        return False
    if runstate.sandbox_active or ext_finished() or ext_visits_left() < 1 or index in ext_visited_this_round():
        return False
    if ext_lever_saving(index, lever) <= 0 or not _ext_install(EXT["farms"][index], lever):
        return False
    EXT["visits"].append([EXT["round"], index, lever])
    return True


def ext_advance():
    """Ends the round on all three farms. False when not allowed."""
    if runstate.sandbox_active or ext_finished():
        return False
    _ext_advance_farms(EXT["farms"], EXT["shadows"])
    EXT["round"] += 1
    return True


def ext_reset(visits=None, last_round=1):
    """A fresh season, then replays `visits` ([round, farm index, lever], in order) up to round `last_round`.
    Visits that are not allowed are dropped. Used for a new season, for taking a visit back and for loading."""
    EXT["round"] = 1
    EXT["visits"] = []
    EXT["farms"] = [_ext_new_farm(spec) for spec in EXT_FARMS]
    EXT["shadows"] = [_ext_new_farm(spec) for spec in EXT_FARMS]
    best = EXT["best"]
    for visit in visits or []:
        while EXT["round"] < visit[0] and not ext_finished():
            ext_advance()
        if EXT["round"] == visit[0]:
            ext_visit(visit[1], visit[2])
    while EXT["round"] < last_round and not ext_finished():
        ext_advance()
    EXT["best"] = best  # replaying a season never counts as finishing one again


def ext_take_back():
    """Takes back the last visit made this round (rounds already ended stay as they are)."""
    if runstate.sandbox_active or not EXT["visits"] or EXT["visits"][-1][0] != EXT["round"]:
        return False
    ext_reset(EXT["visits"][:-1], EXT["round"])
    return True


def ext_new_season():
    """Starts a fresh season once the last one is over (the best result is kept)."""
    if runstate.sandbox_active or not ext_finished():
        return False
    ext_reset()
    return True


ext_reset()
```

- **Block 3 (step 3).** In `ext_advance()`, directly after `EXT["round"] += 1`, add the two lines
  `if ext_finished():` / `_ext_record_season()` (indented inside the function); then append at the end, VERBATIM:

```python
# ---- par and stars: the greedy officer sets the three-star mark ----
def ext_best_visit(farms=None, visited=None):
    """(farm index, lever, saving) of the visit that removes the most methane per round right now, or None."""
    best = None
    visited = ext_visited_this_round() if visited is None else visited
    for index in range(len(EXT_FARMS)):
        if index in visited:
            continue
        for lever in EXT_LEVERS:
            saving = ext_lever_saving(index, lever, farms)
            if saving > 0 and (best is None or saving > best[2] + 1e-9):
                best = (index, lever, saving)
    return best


def ext_par():
    """The score of an officer who always takes ext_best_visit(): the three-star mark (no luck, same every time)."""
    if not _EXT_PAR:
        farms = [_ext_new_farm(spec) for spec in EXT_FARMS]
        shadows = [_ext_new_farm(spec) for spec in EXT_FARMS]
        for _round in range(EXT_ROUNDS):
            visited = set()
            for _visit in range(EXT_VISITS_PER_ROUND):
                best = ext_best_visit(farms, visited)
                if best is not None:
                    _ext_install(farms[best[0]], best[1])
                    visited.add(best[0])
            _ext_advance_farms(farms, shadows)
        _EXT_PAR.append(ext_avoided(farms, shadows))
    return _EXT_PAR[0]


def ext_stars(avoided):
    par = ext_par()
    if avoided >= par - 0.05:
        return 3
    if avoided >= EXT_STAR_SHARE * par:
        return 2
    return 1 if avoided > 0 else 0


def _ext_record_season():
    """Called by ext_advance() when the last round ends: keeps the best result and counts the season."""
    avoided = ext_avoided()
    best = EXT["best"] or {"avoided": 0.0, "stars": 0, "seasons": 0}
    EXT["best"] = {"avoided": max(best["avoided"], avoided), "stars": max(best["stars"], ext_stars(avoided)),
                   "seasons": best["seasons"] + 1}
```

- **Block 4 (step 4).** Directly above `from herd_model import FarmState` add
  `from herd_util import _is_finite_number, _safe_int`; append at the end, VERBATIM:

```python
# ---- saving (new keys only when not default) ----
def ext_save_fields():
    fields = {}
    if EXT["round"] > 1 or EXT["visits"]:
        fields["extension"] = {"round": EXT["round"], "visits": [list(visit) for visit in EXT["visits"]]}
    if EXT["best"]:
        fields["extension_best"] = dict(EXT["best"])
    return fields


def ext_load(data):
    """Puts a saved season back by replaying its visits; anything malformed is dropped. Old saves: a fresh season."""
    EXT["best"] = None
    best = data.get("extension_best")
    if isinstance(best, dict) and _is_finite_number(best.get("avoided")) and best.get("stars") in (0, 1, 2, 3):
        seasons = _safe_int(best.get("seasons"), 0)
        if seasons >= 1 and best["avoided"] >= 0:
            EXT["best"] = {"avoided": round(float(best["avoided"]), 1), "stars": best["stars"], "seasons": seasons}
    saved = data.get("extension")
    last_round, visits = 1, []
    if isinstance(saved, dict):
        last_round = min(EXT_ROUNDS + 1, max(1, _safe_int(saved.get("round"), 1)))
        raw = saved.get("visits")
        for visit in raw[:EXT_ROUNDS * EXT_VISITS_PER_ROUND] if isinstance(raw, list) else []:
            if (isinstance(visit, list) and len(visit) == 3 and visit[2] in EXT_LEVERS
                    and all(isinstance(v, int) and not isinstance(v, bool) for v in visit[:2])
                    and 1 <= visit[0] <= last_round):
                visits.append(list(visit))
    ext_reset(visits, last_round)
```

  `herd_savegame.py`: add `from herd_extension import ext_save_fields` directly after
  `from herd_family import FAMILY_BRANCHES`, and directly before the final `return state` of `get_state()` the line
  `state.update(ext_save_fields())  # R4-PH-2: Extension Officer keys, only when not default`. `herd_loading.py`: add
  `from herd_extension import ext_load` directly after `from herd_collection import _sync_collection`, and directly
  after the line `_load_policy_fields(data)` in `_apply_state()` the line `ext_load(data)  # R4-PH-2`.

- **Block 5 (step 5).** Imports become (exactly this order): `from js import document`, a blank line,
  `import herd_runstate as runstate`, `from herd_rules import DECOUPLING_MEASURES, LEVER_LABELS, POULTRY_MEASURES`,
  `from herd_util import _is_finite_number, _safe_int`, `from herd_model import FarmState`. Append at the end, VERBATIM:

```python
# ---- the panel (Python writes it whole; one click listener on #extension-panel reads the data-ext-* attributes) ----
EXT_INTRO = ("You are the regional extension officer. Three neighbouring farms keep growing; each round you can visit two "
             "of them and help one install a lever, paid by an extension grant. Pick the lever that cuts each farm's "
             "methane most. Your score is the methane they did not emit.")


def ext_status_text():
    avoided = ext_avoided()
    best = EXT["best"]
    record = (f" Best season: {best['avoided']:.1f} avoided, {best['stars']} of 3 stars, {best['seasons']} played."
              if best else "")
    if ext_finished():
        return (f"Season over. The three farms emitted {avoided:.1f} less methane than they would have without you, "
                f"and earned {ext_income_gain():.1f} more. {ext_stars(avoided)} of 3 stars "
                f"(three stars at {ext_par():.1f}).{record}")
    return (f"Round {EXT['round']} of {EXT_ROUNDS}. Visits left: {ext_visits_left()} (one per farm a round). "
            f"Methane avoided so far: {avoided:.1f} (three stars at {ext_par():.1f}).{record}")


def _ext_farm_html(index):
    spec, farm, shadow = EXT_FARMS[index], EXT["farms"][index], EXT["shadows"][index]
    visited = index in ext_visited_this_round()
    can_visit = not (runstate.sandbox_active or ext_finished() or visited or ext_visits_left() < 1)
    sizes = f"{farm.herd_size} cattle"
    if farm.poultry_size:
        sizes += f", {farm.poultry_size} poultry"
    if farm.satellite_open:
        sizes += f", a satellite farm of {farm.satellite_size} cattle"
    buttons = ""
    for lever in EXT_LEVERS:
        saving = ext_lever_saving(index, lever)
        if saving > 0:
            buttons += (f'<button type="button" class="secondary ext-lever" data-ext-farm="{index}" '
                        f'data-ext-lever="{lever}"{"" if can_visit else " disabled"}>'
                        f"{LEVER_LABELS[lever]}: cuts {saving:.2f} a round</button> ")
    return (f'<div class="ext-farm"><h3>{spec["name"]}</h3><p>{spec["blurb"]}</p>'
            f"<p>{sizes}. Methane this round: {farm.methane_this_round():.1f} "
            f"(without your advice: {shadow.methane_this_round():.1f}).{' Visited this round.' if visited else ''}</p>"
            f'<div class="ext-levers">{buttons}</div></div>')


def ext_panel_html():
    off = " disabled" if runstate.sandbox_active else ""
    if ext_finished():
        controls = f'<button type="button" data-ext-action="new"{off}>Start a new season</button>'
    else:
        controls = (f'<button type="button" data-ext-action="advance"{off}>End this round</button> '
                    f'<button type="button" class="secondary" data-ext-action="back"{off}>Take back last visit</button>')
    rest = "<p>The extension office is closed while the practice sandbox is open.</p>" if runstate.sandbox_active else ""
    farms = "".join(_ext_farm_html(index) for index in range(len(EXT_FARMS)))
    return (f'<h2>Extension Officer</h2><p>{EXT_INTRO}</p>{rest}<p class="ext-status" role="status">'
            f'{ext_status_text()}</p><div class="ext-farms">{farms}</div><p class="ext-controls">{controls}</p>')


def render_extension():
    best = EXT["best"]
    document.getElementById("extension-toggle-button").innerText = (
        "🤝 Extension Officer" + (f" ({best['stars']}/3)" if best else ""))
    document.getElementById("extension-panel").innerHTML = ext_panel_html()
```

  `herd_renderer.py`: `from herd_extension import render_extension` directly after
  `from herd_profile import render_profile`, and `render_extension()` directly after the `render_sandbox()` call at the
  end of `render()`. `tests/conftest.py` `ELEMENT_IDS`: before its closing `]` add the comment line
  `# R4-PH-2 Extension Officer.` and the line `"extension-toggle-button", "extension-panel",`.

- **Block 6 (step 6), handlers.** `herd_handlers_panels.py`: add
  `from herd_extension import ext_advance, ext_new_season, ext_take_back, ext_visit` directly above
  `from herd_renderer import render`, and append at the end, VERBATIM:

```python
def on_toggle_extension(event=None):
    """R4-PH-2: opens or closes the Extension Officer panel."""
    panel = document.getElementById("extension-panel")
    panel.hidden = not panel.hidden
    render()


def on_extension_click(event=None):
    """R4-PH-2: one listener on #extension-panel; the clicked button says what to do in its data-ext-* attributes."""
    target = getattr(event, "target", None)
    if target is None:
        return
    farm = target.getAttribute("data-ext-farm")
    action = target.getAttribute("data-ext-action")
    if farm is not None and str(farm).isdigit():
        ext_visit(int(farm), target.getAttribute("data-ext-lever"))
    elif action == "advance":
        ext_advance()
    elif action == "back":
        ext_take_back()
    elif action == "new":
        ext_new_season()
    else:
        return
    render()
```

  `game.py`: add `on_extension_click, on_toggle_extension,` to the end of the `from herd_handlers_panels import (...)`
  list, and directly after the line that wires `mixer-auto-button` in `setup()`:
  `document.getElementById("extension-toggle-button").addEventListener("click", create_proxy(on_toggle_extension))` and
  `document.getElementById("extension-panel").addEventListener("click", create_proxy(on_extension_click))`.
  `index.html`: directly above the `<button id="sandbox-toggle-button"` line in `.game-toolbar`:
  `<button id="extension-toggle-button" class="secondary" type="button">🤝 Extension Officer</button>`; directly after
  the `<div id="changelog-panel" ...></div>` line: `<div id="extension-panel" class="section extension-panel" hidden></div>`.

- **Block 7 (step 7), Desktop and style.** `pc-config.json`: in `windows`, directly after the `changelog-panel` entry,
  `["extension-panel", "extension-toggle-button", "Extension Officer"],`; in `toolbar.menu` the "Game" group's ids become
  `["sandbox-toggle-button", "extension-toggle-button"]`. `style-5-round7.css`, at the end, VERBATIM:

```css
/* R4-PH-2: Extension Officer panel */
.extension-panel .ext-farms { display: grid; gap: 0.6rem; grid-template-columns: repeat(auto-fit, minmax(14rem, 1fr)); }
.extension-panel .ext-farm { border: 1px solid rgba(127, 127, 127, 0.4); border-radius: 8px; padding: 0.5rem 0.7rem; }
.extension-panel .ext-farm h3 { margin: 0 0 0.3rem; font-size: 1rem; }
.extension-panel .ext-levers { display: flex; flex-wrap: wrap; gap: 0.3rem; }
```

- **Tests, NEW file `tests/test_extension_officer.py`** (`game_env` fixture; `m = game_env.module`; every
  `herd_extension` name is reachable as `m.<name>` and `m.EXT` is the same dict). Step 1 creates the file with this
  block; steps 2 to 6 each append the next block (step 6 also adds `import types` directly above `from pathlib import Path`).

  Step 1:

```python
"""LA-13 / R4-PH-2: the Extension Officer, a helper mode where you advise three computer-run farms."""
from pathlib import Path


def _fresh(m):
    return [m._ext_new_farm(spec) for spec in m.EXT_FARMS], [m._ext_new_farm(spec) for spec in m.EXT_FARMS]


def test_the_three_client_farms(game_env):
    m = game_env.module
    farms, _shadows = _fresh(m)
    assert [farm.herd_size for farm in farms] == [12, 4, 6]
    assert farms[1].poultry_size == 20 and farms[1].poultry_unlocked() is True
    assert farms[2].satellite_open is True and farms[2].satellite_size == 10
    assert game_env.farm.herd_size == 0


def test_each_farm_has_its_own_best_lever(game_env):
    m = game_env.module
    farms, _shadows = _fresh(m)
    assert m.ext_lever_saving(0, "capture", farms) == 1.2
    assert m.ext_lever_saving(1, "biofilter", farms) == 1.0
    assert m.ext_lever_saving(2, "satellite_retrofit", farms) == 0.8
    assert m.ext_lever_saving(0, "biofilter", farms) == 0.0
    assert m.ext_lever_saving(0, "satellite_retrofit", farms) == 0.0


def test_the_grant_pays_and_the_slurry_pit_takes_two(game_env):
    m = game_env.module
    farms, _shadows = _fresh(m)
    funds = farms[0].funds
    assert m._ext_install(farms[0], "capture") is True and m._ext_install(farms[0], "capture") is True
    assert farms[0].funds == funds and farms[0].decoupling_investment["capture"] == 2
    assert m.ext_lever_saving(0, "capture", farms) == 0.0


def test_advice_counts_as_methane_avoided_and_nothing_is_random(game_env):
    m = game_env.module
    farms, shadows = _fresh(m)
    m._ext_install(farms[0], "capture")
    m._ext_advance_farms(farms, shadows)
    assert farms[0].herd_size == 13 and farms[1].poultry_size == 22
    assert m.ext_avoided(farms, shadows) == 1.2
    source = (Path(__file__).resolve().parent.parent / "herd_extension.py").read_text(encoding="utf-8")
    assert "import random" not in source and "from random" not in source
```

  Step 2 (append):

```python
def test_a_fresh_season(game_env):
    m = game_env.module
    assert m.EXT["round"] == 1 and m.EXT["visits"] == [] and m.EXT["best"] is None
    assert m.ext_visits_left() == 2 and m.ext_avoided() == 0.0
    assert [farm.herd_size for farm in m.EXT["farms"]] == [12, 4, 6]


def test_one_visit_per_farm_a_round(game_env):
    m = game_env.module
    assert m.ext_visit(0, "capture") is True and m.EXT["farms"][0].decoupling_investment["capture"] == 1
    assert m.ext_visit(0, "caps") is False
    assert m.ext_visit(2, "nonsense") is False and m.ext_visit(7, "caps") is False
    assert m.ext_visit(1, "capture") is True and m.ext_visits_left() == 0
    assert m.ext_visit(2, "satellite_retrofit") is False
    assert m.EXT["visits"] == [[1, 0, "capture"], [1, 1, "capture"]]


def test_unspent_visits_carry_over_and_the_season_ends(game_env):
    m = game_env.module
    assert m.ext_advance() is True
    assert m.EXT["round"] == 2 and m.ext_visits_left() == 4
    for _ in range(7):
        m.ext_advance()
    assert m.ext_finished() and m.ext_advance() is False and m.ext_visit(0, "capture") is False
    assert m.ext_new_season() is True and m.EXT["round"] == 1


def test_taking_back_a_visit_this_round_only(game_env):
    m = game_env.module
    m.ext_visit(0, "capture")
    assert m.ext_take_back() is True and m.EXT["visits"] == []
    assert m.EXT["farms"][0].decoupling_investment["capture"] == 0
    m.ext_visit(0, "capture")
    m.ext_advance()
    assert m.ext_take_back() is False and len(m.EXT["visits"]) == 1


def test_closed_while_the_sandbox_is_open_and_the_real_farm_is_untouched(game_env):
    m = game_env.module
    before = m.get_state()
    m.ext_visit(0, "capture")
    m.ext_advance()
    after = m.get_state()
    for key in ("round_number", "funds", "herd_size", "methane", "decoupling_investment"):
        assert after[key] == before[key]
    m.sandbox_active = True
    assert m.ext_visit(1, "biofilter") is False and m.ext_advance() is False and m.ext_take_back() is False
    m.sandbox_active = False
```

  Step 3 (append):

```python
def test_the_best_visit_and_par(game_env):
    m = game_env.module
    assert m.ext_best_visit() == (0, "capture", 1.2)
    m.ext_visit(0, "capture")
    assert m.ext_best_visit() == (1, "biofilter", 1.0)
    assert m.ext_par() == 93.2
    assert m.ext_stars(93.2) == 3 and m.ext_stars(70.0) == 2 and m.ext_stars(5.0) == 1 and m.ext_stars(0.0) == 0


def test_following_the_best_visit_reaches_three_stars(game_env):
    m = game_env.module
    while not m.ext_finished():
        for _ in range(2):
            best = m.ext_best_visit()
            if best:
                m.ext_visit(best[0], best[1])
        m.ext_advance()
    assert m.ext_avoided() == 93.2 and m.ext_income_gain() > 0
    assert m.EXT["best"] == {"avoided": 93.2, "stars": 3, "seasons": 1}
    assert m.ext_new_season() is True and m.EXT["round"] == 1 and m.EXT["best"]["seasons"] == 1


def test_an_empty_season_still_counts_as_played(game_env):
    m = game_env.module
    for _ in range(8):
        m.ext_advance()
    assert m.EXT["best"] == {"avoided": 0.0, "stars": 0, "seasons": 1}
```

  Step 4 (append):

```python
def test_saves_only_when_not_default_and_loads_back(game_env):
    m = game_env.module
    state = m.get_state()
    assert "extension" not in state and "extension_best" not in state
    m.ext_visit(1, "biofilter")
    m.ext_advance()
    m.ext_visit(2, "satellite_retrofit")
    state = m.get_state()
    assert state["extension"] == {"round": 2, "visits": [[1, 1, "biofilter"], [2, 2, "satellite_retrofit"]]}
    avoided = m.ext_avoided()
    m.ext_reset()
    m.load_state(state)
    assert m.EXT["round"] == 2 and m.EXT["visits"] == state["extension"]["visits"]
    assert m.ext_avoided() == avoided and m.EXT["farms"][2].satellite_retrofits == 1


def test_an_old_save_and_a_broken_one_load(game_env):
    m = game_env.module
    m.ext_visit(0, "capture")
    state = m.get_state()
    state.pop("extension")
    m.load_state(state)
    assert m.EXT["round"] == 1 and m.EXT["visits"] == []
    state["extension"] = {"round": "x", "visits": [[1, 7, "capture"], "junk", [1, 0, "capture"], [1, 0, "capture"]]}
    state["extension_best"] = {"avoided": -3, "stars": 9, "seasons": 1}
    m.load_state(state)
    assert m.EXT["visits"] == [[1, 0, "capture"]] and m.EXT["best"] is None
    state["extension_best"] = {"avoided": 80.5, "stars": 2, "seasons": 3}
    m.load_state(state)
    assert m.EXT["best"] == {"avoided": 80.5, "stars": 2, "seasons": 3}
    assert m.get_state()["extension_best"] == {"avoided": 80.5, "stars": 2, "seasons": 3}
```

  Step 5 (append):

```python
def test_the_panel_shows_the_farms_and_their_levers(game_env):
    m = game_env.module
    m.render()
    html = game_env.elements["extension-panel"].innerHTML
    assert "Hillside Dairy" in html and "Brookside Mixed" in html and "Old Mill Network" in html
    assert 'data-ext-farm="0" data-ext-lever="capture"' in html and "Capture Systems: cuts 1.20 a round" in html
    assert "Round 1 of 8. Visits left: 2" in html and "three stars at 93.2" in html
    assert game_env.elements["extension-toggle-button"].innerText == "\U0001F91D Extension Officer"
    m.ext_visit(0, "capture")
    m.render()
    html = game_env.elements["extension-panel"].innerHTML
    assert "Visited this round." in html and 'data-ext-lever="caps" disabled' in html
```

  Step 6 (append):

```python
def _click(m, **attributes):
    target = types.SimpleNamespace(getAttribute=lambda name: attributes.get(name))
    m.on_extension_click(types.SimpleNamespace(target=target))


def test_clicks_visit_take_back_and_end_the_round(game_env):
    m = game_env.module
    _click(m, **{"data-ext-farm": "0", "data-ext-lever": "capture"})
    assert m.EXT["visits"] == [[1, 0, "capture"]]
    assert "Visited this round." in game_env.elements["extension-panel"].innerHTML
    _click(m, **{"data-ext-action": "back"})
    assert m.EXT["visits"] == []
    _click(m, **{"data-ext-action": "advance"})
    assert m.EXT["round"] == 2 and "Round 2 of 8" in game_env.elements["extension-panel"].innerHTML


def test_the_toggle_opens_and_closes_the_panel(game_env):
    panel = game_env.elements["extension-panel"]
    panel.hidden = True
    game_env.elements["extension-toggle-button"].dispatch("click")
    assert panel.hidden is False
    game_env.elements["extension-toggle-button"].dispatch("click")
    assert panel.hidden is True
```

- **Browser test, NEW file `tests/test_extension_officer_browser.py` (step 7), VERBATIM:**

```python
"""LA-13 / R4-PH-2: the Extension Officer panel in the real page (one Pyodide boot)."""
import pytest

pytest.importorskip("playwright.sync_api")
from playwright.sync_api import sync_playwright  # noqa: E402

from browser_helpers import open_game  # noqa: E402


def test_a_visit_and_the_end_of_a_round_in_the_real_page(base):
    with sync_playwright() as p:
        browser, page = open_game(p, base)
        page.click("#extension-toggle-button")
        page.wait_for_selector("#extension-panel", state="visible")
        assert "Round 1 of 8. Visits left: 2" in page.inner_text("#extension-panel")
        page.click('#extension-panel button[data-ext-farm="0"][data-ext-lever="capture"]')
        page.wait_for_function("document.getElementById('extension-panel').innerText.includes('Visits left: 1')")
        page.click('#extension-panel button[data-ext-action="advance"]')
        page.wait_for_function("document.getElementById('extension-panel').innerText.includes('Round 2 of 8')")
        assert page.errors == []
        browser.close()
```

- **Owner questions** (each with the default this first version uses):
  1. Should a good season feed the main game (for example one legacy point for a first three-star season)? Default: no,
     the mode stands apart, so the main score, the leaderboard and `test_scoring.py` are untouched.
  2. Achievements for the mode (first season, three stars)? Default: none in this version (it would change
     `achievements.json` and the hub's counts); add two later if wanted.
  3. More than one season layout (other farm sets, or a new set each season from the run seed)? Default: one fixed
     layout, so par and the three-star mark are proved by search; a rotating set would need par recomputed per set.
