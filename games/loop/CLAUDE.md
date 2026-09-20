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

## Working conventions

- Commit + tag per milestone: `git commit -m "Milestone N: <name>"` then `git tag loop-milestone-0N`.
- Update the milestone table Status as work happens.
