# Loop — Circular Economy & Overconsumption Game

**Built following the shared conventions in `planning/archive/climate-quartet-2-plan.md`** (moved there 2026-09-22 once all four second-set games shipped; was `climate-quartet-2-plan.md` at the games root while build order still mattered). This file is Loop-specific only. Built third in this set — more structurally different from the others (redesigning a system rather than managing a rising meter), so built after the simpler patterns were solid.

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

## Visual pass — space theme (site-wide design system rollout)

Adopted the shared space-themed visual language already shipped to the hub
and SOL: `shared/space-bg.css`'s starfield+nebula background
(`<div class="space-bg">` markup right after `<body>`), a glass-panel
treatment (translucent gradient + `backdrop-filter: blur()` + soft violet
border + drop shadow) on `#game` and every `.section`/`.context-blurb`/
`.vignette`, gradient buttons with a glossy top highlight and a
`brightness(1.1)` hover state, glowing gradient meter fills, and a
gradient-glow `<h1>` title matching the hub/SOL treatment. Purely a
CSS/HTML property-value change — no selector was renamed and no `game.py`
DOM code touched.

**Deliberately left alone:** the extraction meter's red/orange (`#e0674c`),
the circularity meter and closed-loop chain's green (`#4c9c6e`), the
default straight-line flow-particle's brown (`#9c7a3c`), the trade-network
import-flow's blue (`#4c8ed8`), and the single-item vignette's purple
accent (`#6f6ab0`) are exactly the hues a player relies on to read the
chain-flow visualization, the trade-network link, and the vignette at a
glance — every one of those hex values is untouched; only gradients built
from the same color (plus a matching `box-shadow` glow) were added around
them. The animated chain-flow/return-flow/import-flow particles
(`@keyframes flow-particle-move`, `return-flow-move`, `import-flow-move`)
are pre-existing from Iteration Pass 1/2 (see notes above) and were left
running exactly as before — checked `tests/` for any "no motion" assertion
(none exists for this game; that constraint is specific to champ-de-mots)
and confirmed no CLAUDE.md design decision here forbids animation, so this
game's own restyle additions used only static gradients/shadows, same as
before. Full pytest suite (108 tests) stayed green throughout; verified
live via a local server on a fresh port — starfield/glass panels render,
investing in Recycling Loops and Advance Cycle still update funds,
investment counts, the chain-flow message/vignette, and cycle/damage/score
figures correctly, and the only console errors present are the
pre-existing site-wide ServiceWorker registration quirk also reproducible
on the unmodified hub page.

## Post-milestone backlog pass + achievements (H1-H20, H16 parked)

Worked through `planning/TODO.md`'s "Per-game: Loop" checklist (H1-H20; H16
stayed parked in `LATER.md`) plus the hub-wide achievements framework
rollout (`ACHIEVEMENTS-SYSTEM-DESIGN.md`), all in one pass.

**H1 bug fix:** `exportable_surplus()` used to read
`max(0.0, internal_circular_supply() - PRODUCTION_TARGET)` — only excess
*internal* circularity supply was ever sold outward for export revenue.
Excess *imported* supply (from either trade partner) simply evaporated —
no revenue, no carry-over — even though the player paid real funds for
that import capacity. Fixed to look at total `circular_supply()`
(internal + imported) beyond the production target instead, so any
supply the chain doesn't need this cycle is sold outward regardless of
source. Covered by `tests/test_iteration_pass_2.py`.

**Other H-items, briefly:** a goods-category picker (electronics/
clothing/furniture) at game start, locked in until reset (H2/H20); a
second, differently-priced trade partner, the Regional Distributor
(H8); an in-game "Start New Chain" reset control that wipes the current
chain but keeps the two lifetime counters (`chains_completed_count`,
`goods_categories_tried`) that exist specifically to measure across
resets (H7); a closed-loop streak tracker, sticky best-ever value (H19);
a "time to close the loop" cycle projection reusing the existing trend
calculation (H6); loop-ring node highlighting tied to real investment
(H5); cost-per-unit-of-supply + running-contribution readouts per
measure (H4/H15); a live score breakdown (H17); a few alternate
real-world sector comparisons (H9); a documented hard-ceiling note on
the cost multiplier (H10); a lighter first-cycle message (H11);
alternate vignette phrasings per fraction bucket (H14); a first-time-
closed-loop celebratory banner (H3); and reactive visual pulses on the
funds display (export revenue) and trade-network display (H12/H18).

**Achievements:** 20 achievements (`achievements.json`) covering every
circularity/trade/streak/score/reset/goods-category system above, an
in-game panel + toggle button, an unlock toast, and a link to the
hub-wide achievements dashboard — same pattern as SOL's reference
integration. `achievements_earned` rides `get_state()`/`load_state()`
per the design doc; every achievement's earned status is a pure
function of live state, recomputed on every check, never a hand-set
flag.

**index.html/style.css:** every new element `game.py`'s `render()`/
`setup()` reference (the achievements toggle/panel/toast, the
loop-closed banner, the goods-category picker, the reset button, the
Regional Distributor row, the per-measure stats lines, the loop-ring
node ids, and the score-breakdown/loop-projection/sector-comparison/
streak status lines) was added to the markup and styled to match the
existing space-themed console look — confirmed live in-browser (no
console errors, achievements panel/toast/banner/pulses all fire
correctly) rather than assumed from the pytest fake-DOM harness passing
alone, since the fake harness defines its own element registry and
can't catch an index.html/game.py id mismatch on its own.

**Test-harness fixture:** `tests/conftest.py`'s `game_env` fixture now
creates and passes a `FakeTimers` instance (`tests/fakes.py`) so tests
can assert on pre/post-`setTimeout`-flush state for the achievement
toast, loop-closed banner, and funds/trade-network pulse auto-clear
timers — same shape as Grid's `tests/fakes.py`. `setup()` also now
explicitly sets the achievement-toast/loop-closed-banner `hidden = True`
(the fake-DOM harness's `FakeElement` starts `hidden=False`, unlike a
real `hidden` HTML attribute), matching the pattern already used for
Grid's own toast/banner reset. New `tests/test_achievements.py` (41
tests) covers the achievement catalog/checkers, every individual
achievement earned through real game systems, progress readouts, the
panel/toggle/toast, and the H3/H12/H18 reactive-effect timers. Full
suite: 151 tests, all green.

## Colorblind-safety audit (audited, no change needed)

Audited as part of the site-wide colorblind-safety audit (`planning/TODO.md`, Okabe-Ito-palette method per Continuum's Phase 5, redundant-cue method per Canopy's B9, audit-only method per Tide/Aftermath/Herd/Thaw's own precedent). Checked every place `game.py`/`style.css` convey game-state meaning by color, especially red/orange-vs-green/brown and blue-vs-purple pairs (the two confusion risks the task calls out).

- **`.meter-fill--extraction` (red/orange) vs. `.meter-fill--circular` (green)** — not a violation. These are two permanently separate, permanently labeled meters (an "Extraction" bar and a "Circularity" bar, per the CLAUDE.md's own visual-pass note), not one element switching between the two colors — a viewer reads which meter is which from its own label, never needing to tell the two hues apart from each other.
- **`.return-flow-particle`/`.return-flow-label` (green, internal reuse loop) vs. `.import-flow-particle`/`.import-flow-label` (blue, trade-network import)** — not a violation, and not the relevant confusion pair anyway (blue/purple is the risk pair, not blue/green). Each already carries its own icon (↩ vs ⇢) and full descriptive text ("recovered electronics flowing back into Manufacturing" vs. "reuse capacity crossing in from the trade network"), per `index.html`.
- **`.flow-particle`'s default brown/tan (`#9c7a3c`, linear chain) vs. `.chain-flow--closed .flow-particle`'s green (`#4c9c6e`, closed loop) — the one real candidate, checked closely, concluded already redundantly coded.** Brown-vs-green is exactly the kind of reds/browns-vs-greens pair the task flags as a risk. But this single particle's color isn't the only channel: `chain_flow_message()` renders an always-visible, fully explicit sentence every render pass ("Straight line: 100% of production needs new extraction." / "Loop closed: 100% of production comes from repair, reuse & recycling..." / the live percentage otherwise), and `.chain-arrow`'s opacity independently jumps from 0.5 (dim, linear) to 1.0 (fully lit, closed) — a non-color cue on the same element. A player who can't perceive the particle's hue at all still gets the exact same information from the text and the arrow brightness.

No CSS or `game.py` change made. Full pytest suite (unchanged) stays green since nothing was touched.

## Settings panel (site-wide goal, planning/TODO.md, origin A9)

A consolidated settings panel — text-scale (A-/A/A+ buttons, same clamp/step
shape as Continuum's Phase 5 `accessibility.js`, following Aftermath/Herd/
Thaw's own `settings.js` builds) and a reduced-motion checkbox — toggled
from a new "⚙️ Settings" button in the top toolbar alongside Tutorial/How to
Play/Achievements, rendered into a `.section`-styled panel matching the
existing `#howto-panel`/`#achievements-panel` hidden-until-opened idiom.

Built as `settings.js`, deliberately independent of Pyodide entirely — it
has no Python dependency and works even if `game.py` never boots, and it's
wired up in `<head>` before `game.py`'s own `<script>` runs. `style.css`
gained a `:root { --text-scale: 1 }` custom property read by `html
{ font-size: calc(16px * var(--text-scale, 1)) }` (every font-size in this
file is already in rem, confirmed by grep) and a blanket
`html[data-reduced-motion="true"] *` override collapsing every
animation/transition to effectively instant, additive to the existing
`prefers-reduced-motion` media-query-gated rules already in this file
(including the chain-flow/return-flow/import-flow particle keyframes this
game's own visual-pass note deliberately kept running). Deliberately does
not touch any of this game's meaningful game-state colors (extraction/
circularity meters, flow-particle hues) — only animation/transition timing
collapses.

**Deliberately no sound toggle** — this hub has no audio system built
anywhere yet (`planning/LATER.md`'s standing "what can you actually do with
audio" question), so a sound control here would control nothing real.

Both settings are a browser-level UI preference, not game state — persisted
to `localStorage` (`loop-text-scale`, `loop-reduced-motion`), never
touching `get_state()`/`load_state()`.

Verified live via a local server on a fresh port (sidesteps an unrelated
browser heuristic-caching quirk in the dev-server setup, unrelated to this
game's own code): text-scale increases the whole page's font size correctly
(confirmed via computed `font-size` on `<html>`), the reduced-motion
checkbox sets `data-reduced-motion` correctly, and both settings persist
correctly across a full page reload. Zero new console errors — the
pre-existing ServiceWorker-registration quirk and a report-only
AdSense-iframe CSP notice are both already present on the unmodified page.
Full pytest suite (151 tests, unchanged — `settings.js` is plain frontend JS
with no Python surface) stayed green throughout.


## Reset-to-default settings button (Z-extra/A26, site-wide goal)

A "Reset to Default" button (`#settings-reset-button`) sits at the bottom of the settings panel, below the existing text-size and reduce-motion controls -- SOL's own A26 answer flagged this as a site-wide pattern rather than a SOL-only feature, folded into `planning/TODO.md`'s Z-extra checklist. Implemented entirely in `settings.js` (no Python touched, matching this file's own "deliberately independent of Pyodide" rule for the rest of the settings panel): one click calls `applyScale(DEFAULT_SCALE)` and `applyMotion(false)`, updates `--text-scale`/`data-text-scale`/`data-reduced-motion` on the live DOM immediately, resets the reduce-motion checkbox's own `checked` state to match, and writes both defaults back to `localStorage` so the reset survives a reload rather than only looking reset until the next render. No confirmation dialog -- this is a low-stakes, instantly-reversible display preference, not a destructive action, so `shared/confirm-dialog.js` is deliberately not wired up here.

## Onboarding-tooltip coverage check (site-wide goal, planning/TODO.md, origin A14)

Checked whether a returning player who skipped/forgot the tutorial has anything in the PERMANENT UI (not the one-time walkthrough, not the always-reachable How to Play panel) explaining this game's non-obvious controls on demand. Loop already leans heavily on the `<details class="info-toggle"><summary>i</summary>...</details>` pattern — permanent, always-visible disclosure widgets sitting right next to the Environmental damage meter, the Loop closure meter, the score breakdown, the Circularity investments row, and the Trade network row — so most of the game already self-explains.

**Real gap found and fixed:** the Trade network section's own "i" toggle explains what Trade Link does, but never mentions Regional Partner exists at all, and the two buttons ("Trade Link (25)" / "Regional Partner (40)") carry no readout of what a unit of each actually buys — unlike the Circularity Investments row just above, where each of Repair/Reuse/Recycle already prints its own "X funds/unit · supplying Y/cycle" stats line. A player who forgot H8 (the second, differently-priced trade partner) had nothing in the permanent UI to explain why there are two buttons or what distinguishes them beyond price. Fixed with a `title` attribute on each button (`render()` in `game.py`), set from the same `TRADE_LINK_COST`/`IMPORT_SUPPLY_PER_UNIT`/`REGIONAL_TRADE_COST`/`REGIONAL_IMPORT_SUPPLY_PER_UNIT` constants the game logic already uses, so the numbers can't drift out of sync: Trade Link "25 funds for 4 imported units/cycle (6.25 funds/unit)", Regional Partner "40 funds for 6 imported units/cycle (6.67 funds/unit) — a separate trade partner from Trade Link, so both can be invested in at once." Verified live: full 151-test pytest suite green, and in a real browser both tooltips read correctly via `title` (confirmed the exact strings on the live DOM elements) with zero console errors.

**No other change made** — everything else checked (goods-category picker, Repair/Reuse/Recycle buttons with their own inline stats, the loop-ring visualization, Advance Cycle) already either self-explains via visible text/labels or is covered by the section-level "i" toggles.

## "What's New" changelog panel (K16, planning/TODO.md, site-wide goal)

A small in-game highlights panel — a curated `changelog.json` (flat list of
`{"date", "entry"}` objects, fetched into the Pyodide boot sequence exactly
like `achievements.json` already is) rendered into a hidden-until-opened
"📋 What's New" panel — same toggle+panel idiom as the achievements panel,
with a plain date+text-card layout (no earned/unearned styling, since a
changelog entry has no checkable condition). `CHANGELOG` is sorted
newest-first at load time and degrades to an empty list on a
malformed/missing file, matching `ACHIEVEMENTS`'s own defensive pattern.

Populated with 9 real highlight entries pulled from this file's own
milestone table and iteration notes above, dates cross-checked against
`git log --follow -- games/loop/CLAUDE.md`. Covered by
`tests/test_changelog.py` (catalog sanity, newest-first ordering, toggle
open/close, panel content, no state mutation as a side effect — same
suite shape as Herd/Aftermath/Thaw's own `test_changelog.py`). Full
pytest suite (151 → 160 tests) stayed green throughout; verified live via
a local server on a fresh port — the panel opens, shows all 9 real
entries in the correct order, and there are zero new console errors (the
pre-existing ServiceWorker-registration quirk on this dev setup is
unrelated and was present before this change).

## UI decluttering pass (2026-09-20, planning/TODO.md closing task)

Audited as the last open item in `planning/TODO.md`'s "Big standalone features" section (the user's own crowding note: "everything looks very crowded... making sections either collapsible or other 'screens' within a game could help"). Read `index.html`/`style.css` section by section rather than assuming either "obviously fine" or "obviously broken" going in, and cross-checked the verdict against Thaw's own audit from the same pass (see `games/thaw/CLAUDE.md`) to calibrate what "genuinely crowded" means in practice, since both games share the same climate-quartet-2 status-block layout pattern.

**Real crowding found and fixed:** `#status`'s tail end. After the Environmental damage and Loop closure meter groups, `score-display`/`score-breakdown-display` ran directly into five more lines — `streak-display`, `trend-display`, `loop-projection-display`, `real-world-comparison-display`, `sector-comparison-display` — with zero header or visual break between any of them, reading as one undifferentiated run of `.comparison-message` text. Unlike the meters/investment rows above (checked every cycle before deciding an allocation), none of these five are per-click actionable — they're supplementary readouts a player checks with interest, not something they act on each turn.

**Fixed:** wrapped those five lines in a new `.stats-detail-toggle` `<details>` block (`<summary>📊 Streak, trend &amp; real-world comparison</summary>`), collapsed by default, styled in `style.css` to match Tide's own `.ticker-history-toggle` block-level disclosure precedent — deliberately distinct from the inline "i" `.info-toggle` bubble already used elsewhere in this game, since this collapses a whole group of lines rather than one explanatory paragraph. Same zero-JS native `<details>` mechanism; no `game.py`/Python change; no element id renamed, so `render()` still writes into `streak-display` etc. exactly as before regardless of the panel's open/closed state. `score-display`/`score-breakdown-display` stayed outside the collapse since score is the headline end-of-session stat, not supplementary.

**Everything else audited and left alone:** the goods-category picker, chain-flow/vignette block, `#circularity`, and `#trade-network` sections are each either compact (3-4 rows) or already use the `.info-toggle` disclosure pattern for their own supplementary explanation text — none showed the same flat run-on stacking `#status`'s tail had.

Verified: full pytest suite (160 tests, unchanged — a pure HTML/CSS markup wrapper, `game.py` untouched) stayed green. Live-browser verification wasn't reachable this session (the shared dev-server port was in use by another concurrent session's work, and editing `.claude/launch.json` to add a second port was out of scope for a `games/loop/`-only change); confirmed instead by manual review that no test or `game.py` code path reads DOM structure or parent tags — this hub's fake-DOM test harness keys purely on element ids (confirmed via `tests/conftest.py`), so wrapping existing ids in a `<details>` container is safe by construction.

## Tech notes

- Python/Pyodide, per root conventions.
- Model the production chain as a graph/flow structure (nodes for extraction/manufacturing/use/disposal, with circularity investments adding new edges back into earlier stages) — this makes both the logic and the eventual visualization more natural than a flat meter-based approach.

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

## H13/H20 completion-audit fixes (2026-09-21)

**H13 — no more overlapping toast/banner.** The audit found closing the
loop for the first time earns the "loop_closed" achievement in the exact
same action that fires the H3 celebratory banner — two one-shot
notifications from one event, both visible at once. The user's answer:
keep the achievement-toast substitution (don't build a separate
milestone-toast system), just "don't want both popping up at the same
time." `_check_new_achievements_for_toast()` gained an optional
`delay_ms` parameter; `_run_action()` now passes
`LOOP_CLOSED_BANNER_DURATION_MS` on exactly the loop-closing transition,
so the achievement toast waits until the banner's own visible window has
passed instead of stacking with it. Every other achievement-earning
action still shows its toast immediately (delay 0), unchanged.

**H20 — genuinely distinct goods-flavor content.** The three goods
categories (electronics/clothing/furniture) previously differed only in
the swapped noun/icon/label — every vignette sentence's actual repair/
reuse/recycle mechanism was identical prose. The user's answer:
"distinct." `CATEGORY_LOOP_DETAIL` gives each category its own concrete,
category-appropriate loop mechanics across all four fraction buckets
(closed/majority/minority/none) — a battery swap and circuit-board
metal reclamation for electronics, a mended seam and shredded fabric for
clothing, a fixed joint and remilled timber for furniture — instead of
one generic "repaired... recycled" phrase with a different noun plugged
in. `vignette_message()` looks up `CATEGORY_LOOP_DETAIL[chain.goods_
category][bucket]` and falls back to the original generic wording for
any category not covered there (defensive, in case a future category is
added to `GOODS_CATEGORIES` without flavor content yet). H14's per-cycle
variant-cycling behavior (at least 2 phrasings per bucket) is preserved
for every category, not just the original default.

Tests: 191 -> 201 (`tests/test_achievements.py`'s two new H13 tests:
the toast is held back exactly as long as the banner shows, then appears
correctly, with a regression check that ordinary achievements still show
immediately; new `tests/test_distinct_flavor_content.py`: every category
produces genuinely different text at every fraction bucket, each
category's "closed" wording actually mentions its own mechanic,
every category/bucket combination keeps at least 2 variants, an unknown
category falls back safely, and variant-cycling still works within a
category). Four pre-existing tests that pinned the old generic wording
literally (`"recycled"`, `"Nothing about it comes back"`) were updated
to match the new, equally-valid, more specific default-category text —
the underlying behavior they guard (a closed loop reads as fully
circular, a straight line reads as fully linear) is unchanged. 201/201
green, flake8 clean. Verified live: switching to Furniture and closing
the loop showed the correct furniture-specific "wood... reclaimed"
vignette text, zero console errors.

## Working conventions

- Commit + tag per milestone: `git commit -m "Milestone N: <name>"` then `git tag loop-milestone-0N`.
- Update the milestone table Status as work happens.

## Round-2 backlog wave (2026-09-20, planning/TODO.md "Per-game: Loop")

Built (all UI additions sit inside collapsibles or existing rows; state
additions default safely for old saves): H1 third partner "Overseas
Consortium" (90 funds / 15 units, 6.0 funds/unit); H2 streak progress
text bar toward the next 5-cycle mark; H4 cosmetic-only relabel panel
(does not touch `goods_categories_tried`); H6 particle burst on crossing
each 25% circular step; H8 extraction-cost trend arrow (rising/steady --
damage never decays so "cheaper" cannot occur); H10 projection tooltip;
H12 score-source pie (conic-gradient plus percent legend); H14
`goods_collector` achievement (now 23 achievements); H15 loop efficiency
audit (`audit_lines()`); H16 first-closed cycle number in the banner
(`first_loop_closed_cycle`, saved); H18 top-investment ring node glow;
H20 random per-session vignette-variant offset (browser only, 0 in
tests); H22 ceiling-multiplier tooltip; H24 cycles-since-extraction line
(shown at >=75% circular); H25a/H29a a text supply map (`network_map_text()`
inside the Trade network section); H26 pulse intensity tiers; H27
deterministic weekly featured category (no backend); H28 one-time Regional
Partner hint (`regional_hint_seen`, saved); H30 reset confirmation naming
surviving counters. Tests: 160 -> 186 (`tests/test_backlog_round2.py`).
Verified live in an iframe (the shared browser pane was contended).

Left for a later pass: H3, H7, H9, H13, H17, H21, H23 (new mechanics),
H25b/H29b (rich desktop SVG maps), H19 (largely covered by the existing
sector comparison), H5 (needs Z1 -- stats endpoint not deployed), H11
(needs backend).

## H5: live cross-player circular-economy-index comparison (Z1 now deployed)

Z1, the hub-wide cross-game aggregate-stats backend (`app/stats.py` +
`app/main.py`), is now built and deployed, so came back to unpark H5 from
the list above -- a "circular economy index" community comparison,
aggregate stats on average circular-fraction reached across all players.
Followed Grid's own C15 (`games/grid/game.py`/`index.html`) as the
established reference architecture for this exact feature (also checked
Canopy's B19 `community-forest-button`, a button-triggered/multi-field
variant of the same idea) rather than inventing a new shape: a Python-side
optional-hook call, guarded by `getattr(window, "loopCompare", None)` so
it's a safe no-op under the pytest fake-DOM harness (which never fakes
`window`, only `document`/`setTimeout`), paired with a JS-side `fetch()`
in `index.html` that does the real network call and writes the result
into the DOM -- `game.py` never touches `#community-comparison-display`
directly, same division of labor as Grid's `#summary-compare`.

**Metric chosen:** `chain.lifetime_circular_fraction()` -- the same 0..1
lifetime circular share already surfacing everywhere else in this game
(the "Lifetime circular share" meter readout, the two static ballpark
`real_world_comparison_message()`/`sector_comparison_message()` lines,
the score bonus) -- rather than a raw count like `total_extracted`, since
it's the one number this game's whole design already treats as *the*
circular-economy index a player is optimizing for. It wasn't yet a plain
top-level `get_state()` field in a form `app/stats.py`'s `STATS_FIELDS`
whitelist could read directly (only the two raw counts it's derived
from, `total_extracted`/`total_produced`, were), so `get_state()` now
also exposes `lifetime_circular_fraction` as a derived, read-only key --
recomputed fresh every call, never restored by `load_state()` (an extra
key `load_state()` simply doesn't read), so it can't drift out of sync
with the two counts it comes from. Added it to `STATS_FIELDS["loop"]` in
`app/stats.py` (a small, careful addition -- `loop` was already
registered there for its other five raw counters; this just adds the one
new key). No dedicated per-field backend test added since
`app/tests/test_aggregate_stats.py`'s existing pattern doesn't cover
individual games/fields either (it exercises the whitelist mechanism
generically against `grid`/`herd`/`thaw`/`tide`) -- full backend suite
(76 tests) confirmed green with the addition regardless.

**Wiring:** `_request_community_comparison()` (new, next to
`sector_comparison_message()`) calls `window.loopCompare(chain.lifetime_
circular_fraction())` from the tail of `render()`, right after the two
static comparison lines it sits beside in the UI. `index.html` defines
`window.loopCompare` as an IIFE (same shape as Grid's `window.gridCompare`
-- cache-by-rounded-value with a 60s TTL and an in-flight guard, so
Loop's own frequent `render()` calls -- every click, not gated behind an
open/closed summary-panel flag the way Grid's is, since this game has no
such panel -- don't spam the endpoint): it fetches `GET
/stats/games/loop/percentile?field=lifetime_circular_fraction&value=<x>`
and, on a real non-suppressed percentile, writes "Compared with N other
saved chains: your lifetime circular share beats X% of them." into
`#community-comparison-display`; any error, non-2xx response, or
`suppressed: true` leaves that element's static HTML fallback ("Compare
with other players isn't available yet.") untouched -- `game.py` never
writes into that id at all, so the fallback is exactly what a player sees
until/unless the fetch actually succeeds. Placed inside the existing
"📊 Streak, trend & real-world comparison" `<details>` block (the UI
decluttering pass's collapsible), right after `sector-comparison-display`,
since it's the same kind of supplementary, non-per-click-actionable
readout the other lines in that block already are.

**Tests:** new `tests/test_community_comparison.py` (5 tests) --
mirrors `games/grid/tests/test_round2_items.py`'s own C15 coverage shape:
`render()` calls the hook with the live, freshly-recomputed
`lifetime_circular_fraction()` value (checked across two different
lifetime states in the same test, not just once); a safe no-op when
`window` isn't faked at all (the normal pytest case) and when `window`
exists but has no `loopCompare` attribute; and a static check that
`index.html` actually ships the element, its fallback text, and the
hook/endpoint/field name wiring. Also had to update
`tests/test_save_system.py::test_get_state_includes_every_expected_key`'s
exact-key-set assertion to include the new `lifetime_circular_fraction`
key (a deliberate, expected change, not a regression). Full suite: 186 ->
191 tests, all green. `flake8 games/loop app --extend-ignore=E501` clean.

**Verified live** against the shared `hub-dev-server` and the *real*
production backend (`https://noyvjgames.fastapicloud.dev`, same
`API_BASE` Grid's own `index.html` already points at) in a dedicated
Claude Browser tab (the shared/default tab in this pane was being
actively driven by another concurrent session mid-session and kept
navigating out from under this check -- opened a fresh tab instead of
fighting over the shared one): confirmed `window.loopCompare` is defined
and gets called with the live fraction value on every `render()`
(intercepted the real hook and triggered a Repair Networks investment
click, confirmed the call), and that `#community-comparison-display`
never shows raw JSON or an error string -- only ever its plain-English
fallback or (once real data exists) the plain-English percentile
sentence. Production's `/stats/games/loop/percentile` currently 404s for
`field=lifetime_circular_fraction` specifically (expected: this session
added the field to `app/stats.py` locally, and it hasn't been
deployed/pushed yet -- same "built, not yet deployed" situation Milestone
6's accounts backend documents), which does surface as a "Failed to load
resource: 404" browser console line -- an artifact of the browser's own
network-panel logging for any non-2xx `fetch()` response, not a JS
exception this code raises or leaves uncaught, and not something a player
ever sees on the page itself. Separately confirmed against production
that even an already-deployed, already-whitelisted field (Grid's
`emissions`) currently returns `suppressed: true` with a clean 200 (this
site simply doesn't have 3+ real saves yet for most fields) -- so once
this field is deployed, the realistic day-one state is the same graceful
"not enough players yet" text, zero console noise, that every other
game's own C15/B19-style comparison currently shows in production too.

- 2026-09-21: H10 -- the hard 2.5x extraction-cost ceiling is now visible in an info-toggle (`#damage-ceiling-note`) beside the damage meter, not only a hover title.
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

## 320px mobile-viewport audit (Z18, site-wide goal, planning/TODO.md)

Checked at a genuine 320px viewport (narrower than the original 375px
mobile pass) via the Claude Browser tool's `resize_window`.

**Real bug found and fixed:** the four-stage chain-flow visualization
(`.chain-stage` + three `.chain-arrow`s) fits comfortably at 375px+, but
at 320px the combined width of "Manufacture" (the longest stage label)
plus each stage's own padding/gap and the arrows' minimum width added up
to more than the viewport has room for. `.chain-stage` had no
`min-width: 0`, so flexbox's default content-based min-width kept the row
from shrinking below its content, pushing `#chain-flow-section` (and the
page) wider than 320px. Fixed with `min-width: 0` on `.chain-stage`,
`overflow-wrap`/`word-break` on `.chain-label` as a safety net, and a
`@media (max-width: 359px)` block trimming padding/font-size/arrow-width
just enough at this one breakpoint to fit without needing the wrap/break
fallback in practice.

No other overflow found at 320px. `flake8`/tests unaffected (pure CSS).

## Difficulty-aware achievements audit (Z27, site-wide goal)

Grepped `game.py` for a difficulty/hard-mode toggle and found two
candidates that turned out to be forward-looking scaffolding, not shipped
features: **H13** ("an opt-in harder variant... multiplies both internal
and imported circular supply down") and **H23** ("an opt-in 'zero-waste'
variant... tracking whether lifetime extraction ever exceeds this cap")
both exist ONLY as a constant (`CHALLENGE_MODE_SUPPLY_MULTIPLIER`,
`ZERO_WASTE_EXTRACTION_CAP`) and an explanatory comment referencing a
`ChainState.set_challenge_mode()` method that doesn't exist anywhere in
the file — no toggle checkbox, no state field, no code path a player can
actually reach. Cross-checked against `planning/TODO.md`: both H13 and
H23 are still unchecked (`- [ ]`) open backlog items, not completed
features — the "H13" references elsewhere in this file and in `game.py`
(the toast/banner-overlap audit fix, V-E-5) are about the achievement-
unlock toast timing for the EXISTING milestone achievements
(`quarter_loop`/`half_loop`/etc.), an unrelated use of the same H-number,
not this difficulty variant.

**Loop currently has no reachable difficulty/hard-mode toggle to audit —
not applicable.** Building H13/H23 for real is out of scope for this
audit pass (Z27 is about auditing existing toggles, not building new
ones); they remain open items in `planning/TODO.md` for whenever they're
actually built, at which point this same Z27 question is worth re-asking.
No code touched.

## Achievement-progress bar in toolbar (Z-extra/A10, site-wide goal)

Already satisfied — see the existing toggle-button label. `#achievements-
toggle-button`'s `innerText` already reads `"🏆 Achievements (N/M)"` via
`update_achievements_display()`, which runs on every render pass (not
only on toggle), so the live count is visible in the toolbar before the
panel is ever opened. No code change needed here.

## "What's new since you played" banner (Z24, site-wide goal)

A new shared `shared/whats-new-banner.js` -- deliberately distinct from
this game's own in-game "📋 What's New" changelog PANEL above (K16,
opt-in, player-triggered, always shows the full history from scratch).
The banner instead appears automatically on page load, but ONLY for a
RETURNING player who has missed real entries since their last visit: it
diffs this game's `changelog.json` against
`localStorage["whats-new-seen:loop"]` (the date string of the newest
entry already shown) and lists just the new ones, not the whole log. A
first-ever visit silently marks the current changelog as seen rather
than dumping the full history on a brand-new player. Reuses the same
`window.CHANGELOG_JSON` global this game's own changelog panel already
fetches -- no second network request. One `<script
src="../../shared/whats-new-banner.js" data-game-id="loop">` include,
added right after `shared/last-played.js`'s own include. See root
`CLAUDE.md`'s Working notes for the full write-up -- shared
infrastructure, documented once there rather than duplicated across all
12 games' own files.

## Keyboard-shortcut convention: ?/Esc (Z4, site-wide goal)

Wired via the new shared `shared/keyboard-shortcuts.js` -- one script
include plus one `KeyboardShortcuts.init({panels: [...]})` call at the
end of `index.html`, listing this game's real toggle-button + hidden-
panel pairs: How to Play, Achievements, What's New, Settings, and the
Info Page. `?` opens a small floating shortcuts-help overlay; `Esc`
closes it and clicks the toggle button of whichever listed panel is
currently open, reusing each panel's own open/close logic. The various
`<details>` disclosures (relabel-goods, the efficiency audit, the supply
map) aren't in the list -- they're native browser disclosures with their
own `<summary>` click affordance, not the toggle-button pattern the
shared helper targets.

## Circular design challenge and Zero-waste challenge (H13/H23, 2026-09-26)

Two opt-in modes, picked in the start-of-chain picker before the first cycle (`ChainState.can_choose_mode()`: nothing produced yet, then locked for that chain; "Start New Chain" resets them). They were previously only constants plus a comment; this builds the real toggles the Z27 audit note above said were missing.

- **Circular design challenge (H13):** `challenge_mode` multiplies both internal and imported circular supply by `CHALLENGE_MODE_SUPPLY_MULTIPLIER` (0.65) via `supply_multiplier()`, so closing the loop needs roughly 1.5x the investment. It only changes supply, so it slows every circularity achievement rather than making any impossible, and it can be avoided by simply not picking it.
- **Zero-waste challenge (H23):** `zero_waste` tracks lifetime extraction against `ZERO_WASTE_EXTRACTION_CAP` (150). It is soft by hub convention: going over is reported ("missed, play carries on") and never blocks anything.
- The two combine. A status line under the picker (kept visible after the picker hides) shows what is in force and the running extraction count.
- Save: `challenge_mode` and `zero_waste` are written only when on and read back strictly as booleans (anything else loads as off). 201 -> 215 tests (`tests/test_start_modes.py`); verified live, zero console errors.

## Waste stream focus (H9, 2026-09-26)

A free, switchable emphasis on ONE circularity measure: that measure's supply counts `WASTE_STREAM_SPECIALIZATION_BONUS` (25%) higher, the other two stay at base. The only trade-off is structural (one focus at a time), so there is no cost and no confirm. `ChainState.waste_focus` (None or a measure), `measure_multiplier()`, and `set_waste_focus()` (rejects unknown/non-string values); a Focus button on each measure toggles it (clicking the focused one clears it) and the stats line shows the boosted contribution and a '+25%' note. It stacks with the Circular design challenge multiplier. Save: `waste_focus` written only when set, validated on load. 215 -> 228 tests (`tests/test_waste_focus.py`); verified live (recycling 10/cycle became 12/cycle when focused, switching moved the boost).

## Circular economy scorecard (H19, 2026-09-26)

Extends the two single-line real-world comparisons with a scorecard inside the Stats details: one row per benchmark (the overall real-world average plus each of `SECTOR_COMPARISONS`), each with a verdict line (`▲ 93 points above` / `▼ … below` / `◆ level with`, so the state is text and shape, never colour alone) and two thin bars, yours then the benchmark's. `scorecard_rows(lifetime_fraction)` is the pure data (label, benchmark, signed gap in points, verdict, symbol, clamped bar widths) and `render_scorecard()` rebuilds the rows each render. Same 'ballpark figures, not a precise dataset' hedge as the lines above it; read-only (never touches state or saves). 228 -> 236 tests (`tests/test_scorecard.py`); verified live (all five rows, 'above' for a fully circular chain).

## Supply chain redesign (H3, 2026-09-26)

A late-game layer: once the loop has closed at least once (`first_loop_closed_cycle` is set), each circularity measure can be redesigned up to `REDESIGN_MAX_LEVEL` (3) times. Each level costs funds (`REDESIGN_BASE_COST` 120 times the next level number) and makes that measure's supply count `REDESIGN_SUPPLY_BONUS` (5%) higher permanently: deliberately small, per the item's 'small efficiency bonus'. It stacks ADDITIVELY with the H9 focus in `measure_multiplier()` (1 + focus + 0.05 times level) rather than compounding. `ChainState.redesign_level`, `redesign_unlocked()`, `redesign_cost()`, `redesign()`; a Redesign button per measure shows its cost, a locked hint before the first close, or 'max'. Spend counts toward lifetime investment. Save: `redesign_level` written only when any level is above zero, validated per measure (int 0..3). Start New Chain clears it. 236 -> 249 tests (`tests/test_redesign.py`).

## Consumer behavior: culture campaign (H17, 2026-09-26)

A demand-side lever, distinct from the three supply-side measures. Each level of the Repair & Reuse Culture campaign (`CULTURE_BASE_COST` 40 times the next level, up to `CULTURE_MAX_LEVEL` 5) trims `CULTURE_DEMAND_REDUCTION` (4%) off the material one cycle's production needs (`ChainState.material_need()`, equal to `PRODUCTION_TARGET` with no campaign), so it shrinks the gap supply has to fill instead of adding supply. `new_extraction_needed()` and `exportable_surplus()` now use `material_need()`; revenue still uses the full production target (people still buy things, they just need fewer new materials each). The circular-share metric is unchanged in form: less new extraction means a higher circular share. Save: `culture_level` only when above zero, validated (int 0..5). Start New Chain clears it. 249 -> 263 tests (`tests/test_culture.py`); verified live along with the H3 redesign buttons (two levels cut extraction from 50 to 46 units; the redesign button unlocked and bought a level after the loop closed).
