# Grid — Energy Transition Game

**Read `../climate-quartet-plan.md` first for shared conventions (testing, feedback hook, hope-angle requirement, hub integration).** This file is Grid-specific only.

## Concept

You manage a regional power grid across a series of rounds. Demand grows every round. You choose which plant types to build or retire. Fossil plants are cheap and reliable early; renewables cost more upfront but get cheaper over time as you invest in them (mirrors real-world cost curves — this is the mechanic that carries the lesson, not a stat you show the player directly).

## Climate issue & hope angle

**Issue:** energy-sector emissions, the single largest lever in real-world climate mitigation.
**Hope angle:** the game must show that early investment in renewables pays off — cheaper energy, fewer disruptions, a visibly better late-game position than a fossil-heavy strategy. A player who leans renewable early should end up in a *better* position than one who doesn't, not just a "cleaner but harder" one. This is the antidote to "sustainability = sacrifice."

## Core loop

- Turn-based, discrete rounds (not real-time ticking).
- Each round: demand rises by some amount. Player allocates budget to build/retire/upgrade plants.
- Plant tiers (start simple, expand if time allows): Coal, Gas, Nuclear, Solar, Wind, Hydro.
- Renewable costs decrease the more the player has already invested in them (learning-curve effect) — this needs to be visible/legible to the player, not hidden math.
- Emissions accumulate as a rising background meter tied to the fossil-heavy share of the grid.
- **No hard fail-state/game over.** Instead, rising emissions trigger progressively more frequent/severe disruption events (brownouts, damaged plants, cost spikes) — the game gets *harder to manage*, not suddenly lost. This is what teaches "delay compounds cost" without punishing exploration.
- Scoring/win condition: sustained grid stability over N rounds, weighted by how clean the grid became over time (not just final-state cleanliness).

## Milestones

| # | Milestone | Content | Status |
|---|-----------|---------|--------|
| 1 | Core state loop | Demand growth, budget allocation, plant build/retire, round progression. No emissions or events yet. Tests: state transitions for budget spend, plant count changes, demand growth formula | Done |
| 2 | Emissions meter + cost curve | Emissions accumulate based on grid composition; renewable costs decrease with cumulative investment. Tests: emissions calculation, cost-curve decay formula | Done |
| 3 | Disruption events | Brownouts/damage triggered probabilistically by emissions level, scaling in frequency/severity. Tests: event-trigger thresholds, damage application | Done |
| 4 | Scoring + hope-angle payoff | End-of-run scoring that rewards sustained clean transition, not just final snapshot. Tests: scoring calculation across sample playthrough logs | Done |
| 5 | In-game feedback prompt | End-of-run 1–2 question prompt, piped to Neon backend per root conventions | Done |
| 6 | UI/visual pass + hub integration | Tier icons, meter displays, event notifications. Polish only after 1–5 are solid | Done — all 6 milestones complete |

## Iteration Notes — Pass 1 (implemented)

Design-review pass (pre-playtest, from `climate-games-iteration-pass.md`). Anticipated issue: the renewable cost-curve mechanic (the actual lesson) risked being invisible as pure numbers — a player could succeed without ever consciously registering "investing early made things cheaper."

**Built in response (see `BCM114-DEV-LOG.md` 2026-08-11):** the live two-line emissions/renewable-cost trend graph, and a short factual context blurb on first unlocking a renewable tier. Weather-variability-on-renewable-output was considered and deliberately skipped as scope discretion.

**Open testing question:** does a first-time player, unprompted, notice that early renewable investment made later rounds easier? The in-game feedback prompt asks directly: "Did investing early feel like it paid off?"

## Iteration Notes — Pass 2 (implemented)

Second design-review pass, from `climate-games-iteration-pass-2.md`, building on Pass 1. **Selected additions: A (global comparison) + B (infrastructure age/vulnerability).**

- **Global comparison:** at session end, show the player's grid trajectory (emissions curve, clean-energy share over time) plotted against a real-world average trend line, pulled or hardcoded from public data. A secondary comparison against other players' aggregate outcomes (via the ratings backend) is a nice stretch goal, but the real-world benchmark is the priority.
- **Infrastructure age/vulnerability:** plants accumulate an age value each round; older plants become progressively more failure-prone (higher chance of costly breakdown events) unless maintained. Adds a maintenance-budget dimension separate from the build/retire decision, reinforcing "cheap now, costly later" from a different angle.
- **Visual polish for this pass:** the two-line graph should carry the global-comparison line as a third, visually distinct series (three lines max, stay legible). Aging plants should show a visible wear state (icon degrades slightly) so vulnerability is seen before it's felt as a breakdown event.

## Info Page — real-world sources (implemented)

*Implementation is now shared across all 8 climate-quartet games — see `shared/info_page.py` and `shared/info-page.css`. Only the content below (framing/tie-in/sources) is game-specific; the rendering/toggle code moved out of this game's `game.py`.*

An optional, player-triggered "The Real Story" panel — never forced mid-session, since the mechanic teaches first and this is a supplement for players who want to go deeper. Toggled via a button near the top of the page; shows a short framing paragraph (written fresh, not copied from any source), a one-line note tying the mechanic to real data, and a sources list with clickable links.

**Framing:** Electricity generation is one of the largest single sources of global emissions, and the fastest way to cut it is building out cleaner capacity — not rationing power. Renewables have gotten dramatically cheaper the more of them get built, a real economic trend called a learning curve. That's the same tension Grid asks you to manage: lean into that cheaper long-run path, or lean on familiar fossil capacity.

**Mechanic tie-in:** Grid's cost curve and its global-comparison line are grounded in published wind/solar learning-rate data (roughly 15%/24% cost decline per capacity doubling), not an invented number.

**Sources:**
1. [IEA — Rapid rollout of clean technologies makes energy cheaper, not more costly](https://www.iea.org/news/rapid-rollout-of-clean-technologies-makes-energy-cheaper-not-more-costly) — real-world backing for Grid's central claim that leaning renewable is the cheaper long-run path, not a sacrifice.
2. [Oxford Institute for Energy Studies — A critical assessment of learning curves for solar and wind power technologies](https://www.oxfordenergy.org/publications/a-critical-assessment-of-learning-curves-for-solar-and-wind-power-technologies/) — a balanced, critical look at the same cost-decline concept Grid's core mechanic is built on.
3. [US DOE / Lawrence Berkeley National Lab — Learning a Better Way To Forecast Wind and Solar Energy Costs](https://www.energy.gov/cmei/solar/articles/learning-better-way-forecast-wind-and-solar-energy-costs) — the actual learning-rate figures (wind ~15%, solar ~24% per capacity doubling) behind Grid's cost curve.
4. [IEA — Breakthrough Agenda Report 2025: Power](https://www.iea.org/reports/breakthrough-agenda-report-2025/power) — current real-world electricity cost figures, grounding the global-comparison line.

All four links verified live before merging. Source 2 (Oxford) returns 403 to automated fetchers (bot-protection) but loads fine in a real browser — confirmed the pattern is consistent with several other major institutional domains checked the same way.

## Iteration Notes — Pass 3 (Fun/Teaching Balance)

Third design-review pass, from `climate-games-fun-teaching-balance.md`. **Risk:** the tiered plant system could drift toward a pure optimization spreadsheet where a player wins by number-crunching without ever registering *why* the renewable path pays off — the emissions meter reading as a side-score rather than the actual mechanism gating disruption risk.

**Found already satisfied:** the fix's core ask — disruption probability/severity scaling directly off the same emissions meter, with no separate difficulty setting, on a soft escalating curve rather than a sudden spike — was already built in Milestone 3 (`disruption_probability()` / `disruption_severity()` are both a direct linear function of `state.emissions`, capped rather than cliffed, and covered by `tests/test_disruption_events.py`). The Pass 2 aging/vulnerability system is a deliberately separate axis (plant neglect, not emissions) and was left untouched here — it's a different lesson, not a rival difficulty curve standing in for the emissions one.

**Actual gap — legibility:** nothing on-screen ever stated in words that rising emissions were the thing driving disruption risk. A player could watch the emissions bar fill and brownouts get worse without the causal link ever being spelled out, which is exactly the "invisible math" failure mode the risk describes. **Built in response:** a live `disruption-risk-display` line under the emissions meter (`game.py`'s new `disruption_risk_message()`, wired into `render()`) that states the current next-round disruption probability in plain language, and calls out when severity has crossed into damage-risk territory — e.g. "Rising emissions mean a 50% chance of a disruption next round." Scoped to this one addition; no changes to the underlying probability/severity math, which didn't need any.

## Audit fix — retire refund exploit

Code-quality audit pass. **Bug found:** `retire_plant()` refunded a flat `PLANT_BASE_COST * REFUND_FRACTION` regardless of a renewable's current (learning-curve-discounted) cost. Once a renewable's cumulative-built discount passed 50% off base cost — solar around 14 units in, well within a normal playthrough — its build cost dropped below the flat refund, turning build-then-immediately-retire into a risk-free, repeatable money exploit (and each cycle nudged the discount further, making later cycles more profitable). **Fixed** by refunding off `plant_cost()` (the plant's current cost) instead of the flat base cost; for fossil/nuclear plant_cost() already equals base cost, so their refund behavior is unchanged. Covered by a new regression test in `tests/test_emissions_and_cost_curve.py`.

## Second audit pass — save/load merge fix + comment cleanup

A more aggressive follow-up pass (fix anything safe, however minor, rather than just flagging it). **Bug found:** `load_state()` replaced `plant_counts`, `cumulative_built` and `plant_age` wholesale (`state.plant_counts = copy.deepcopy(data["plant_counts"])`, etc.) instead of merging key-by-key. A save missing one of those keys — e.g. an older save format from before a plant type existed, or a hand-edited/truncated payload — would drop that key from live state entirely, and every consumer (`render()`, `total_capacity()`, `plant_cost()`, ...) does `state.plant_counts[plant_type]` unconditionally for every type in `PLANT_TYPES`, so the very next access crashed with a `KeyError`, after the save widget had already reported a successful load. Exactly the same bug shape found and fixed this session in Continuum's `restore_city()` and SOL's `deserialize_state()`. **Fixed** with a new `_merge_plant_dict()` helper that writes only the keys present in the saved dict into the live one, leaving any key the save doesn't know about at its current live value. Covered by a new regression test in `tests/test_save_widget.py` that deletes a key from a snapshot before loading it and confirms `render()` no longer crashes.

Also checked and found clean on this pass: no second cost/refund asymmetry (maintenance and aging-breakdown repair costs are debits off a flat base cost, not refunds, so there's no exploit direction the way the flat-refund bug had); no `create_proxy()` leak (all proxies are created once in `setup()`, never per-repaint, since `render()` only updates existing DOM elements rather than recreating any); no dead constants or functions (every module-level constant is read at least once). Two stale comments were corrected: the module docstring still described the Milestone-1-only state ("Emissions, cost curves, and disruption events land in later milestones") despite all of those having since landed in this same file, and a comment above `PLANT_BASE_COST` said renewable cost decay was "Milestone 2's job" as an unfinished forward reference rather than pointing at the `plant_cost()` method that has implemented it since.

## Visual pass — space theme (site-wide design system adoption)

Site-wide visual overhaul pass (hub + SOL already shipped; this game brought in line). Adopted the shared `shared/space-bg.css` starfield/nebula background (added the `<div class="space-bg">` markup + stylesheet link right after `<body>`) and reskinned `#game`/`.section` as glass panels (translucent gradient background, `backdrop-filter: blur`, violet-tinted `rgba(140,160,255,…)` borders, soft drop shadow) matching SOL's reference implementation. `<h1>` got the gradient-glow text treatment; `.tagline`/sub-headings were left plain for hierarchy. `button.secondary`/`button.primary` moved from flat solid backgrounds to two-stop gradients with a glossy inset highlight and a `filter: brightness(1.1)` hover state, keeping every existing `:disabled`/`:active`/`.selected` behavior intact (just re-skinned colors). `.meter`/`.meter-fill--emissions`/`.meter-fill--score` kept their exact existing colors (red/green) and only gained a matching-hue `box-shadow` glow — width/fill logic in `game.py` untouched. Flat gray borders (`.plant-row`, `.context-blurb`) switched to the violet-tinted rgba used elsewhere.

**Deliberately left alone:** `PLANT_ICON` emoji and the `wear-1`/`wear-2`/`wear-3` desaturation filters (aging-vulnerability cue) — these are the actual state-encoding visuals (plant identity + wear) and weren't touched beyond leaving their existing filter/opacity values exactly as they were. The trend-graph SVG stroke colors (`trend-line--emissions`/`--cost`/`--global`) are also untouched — they're a legend, not decoration. No "no motion" test constraint exists in this game's `tests/` (that's a Drift-specific wellbeing-pass decision, confirmed by grepping all 8 climate-quartet games' tests before starting) and the root `climate-quartet-plan.md` visual-polish requirement explicitly calls for eased transitions, so the existing `transition: filter`/`width` rules were kept and a hover-brightness transition was added to buttons — no new hover-lift/transform motion was introduced. `ad-bar.css`/`shared/info-page.css` are shared files out of this game's scope and weren't touched (matches SOL, which also left them flat). Full pytest suite (132 tests) stayed green throughout; live-verified in-browser (starfield/glass panels render, Solar build + Advance Round both work exactly as before, funds/capacity/round state update correctly, no new console errors beyond a pre-existing ServiceWorker-registration warning unrelated to this CSS/HTML-only change).

## Colorblind-safety audit (C18 / site-wide goal)

Site-wide colorblind-safety audit (Okabe-Ito-palette method, per Continuum's Phase 5, Canopy's B9, Tide's D11). Checked every place `game.py`/`style.css` conveys game-state meaning by color: the two single-value meters (`.meter-fill--emissions` red, `.meter-fill--score` green) are each their own bar with their own adjacent text label and never appear side by side as a pair a player has to tell apart — same "single-hue bar, not a paired good/bad color" shape Tide's D11 audit already found clean, so left alone. The plant-mix bar chart (`mix-bar--coal/gas/nuclear/solar/wind/hydro`) uses six different hues but each bar has its own name label, so it's a legend, not a two-state pair. `.disruption-toast--warning` (amber) vs. `--danger` (red-orange) is a severity gradient with its own message text each time, not a red/green good/bad pair.

**Real issue found:** the C15 trend graph (`trend_graph_svg()`) draws three lines on one SVG — emissions (red, `#e0674c`), average renewable cost (was green, `#4c9c6e`), and a dashed grey global-average benchmark. Emissions vs. cost were both solid, same-weight lines told apart *only* by red vs. green — the exact deuteranopia/protanopia confusion pair — and the only text identifying which line is which (each point's `<title>` tooltip, e.g. "Your emissions" / "Avg renewable cost") is hidden until hover, not visible at a glance the way Tide's D19 tooltip was layered on top of an *already*-redundant texture pair. This is a genuine hue-only encoding, unlike Tide's D11 finding.

**Fixed** (`games/grid/style.css`'s `.trend-line--cost`/`.trend-point--cost`): re-picked cost's color from green to Okabe-Ito blue (`#4fa8dd`, already used elsewhere in this file for the hydro mix-bar), so the pair reads as red/orange vs. blue instead of red vs. green. Also gave `.trend-line--cost` its own `stroke-dasharray: 2 2` (a fine dash, distinct from the global line's existing `4 3` dash and emissions' solid line), so all three lines are now told apart by pattern as well as color — the same "recolor plus a second, non-color cue" combination Continuum's own fix used, rather than relying on the palette swap alone. `trend-point--cost`'s marker fill was updated to match. No `game.py` change needed — `trend_graph_svg()` only emits CSS classes, never inline colors. Full pytest suite (255 tests) stayed green (CSS-only change, no Python logic touched).

## Settings panel (site-wide goal, planning/TODO.md, origin A9)

A consolidated settings panel — text-scale (A−/A/A+ buttons, same clamp/step
shape as Continuum's Phase 5 `accessibility.js`) and a reduced-motion
checkbox — toggled from a new "⚙️ Settings" button in the second toolbar row
(alongside the Steeper Demand / Weather Variability difficulty toggles),
rendered into a `.section`-styled panel matching the existing
`#howto-panel`/`#achievements-panel` hidden-until-opened idiom.

Built as `settings.js`, deliberately independent of Pyodide entirely (same
discipline as Continuum's `accessibility.js`) — it has no Python dependency
and works even if `game.py` never boots, wired up in `<head>` before
`game.py`'s own `<script>` runs. `style.css` gained a `:root
{ --text-scale: 1 }` custom property read by `html { font-size: calc(16px *
var(--text-scale, 1)) }` (every font-size in this file is already in rem,
confirmed by grep, so scaling the root font-size scales the whole game
uniformly with zero other changes needed) and a blanket
`html[data-reduced-motion="true"] *` override collapsing every
animation/transition to effectively instant — additive to, not replacing,
this game's own existing `prefers-reduced-motion` media-query-gated rules
(`grid-current-flow`, `grid-meter-shimmer`, `grid-smoke-rise`,
`grid-flame-flicker`, `grid-radiate-pulse`, `grid-panel-shine`,
`grid-turbine-spin`, `grid-wave-flow`, `grid-battery-pulse`).

**Deliberately no sound toggle** — this hub has no audio system built
anywhere yet (see `planning/LATER.md`'s "what can you actually do with
audio" standing question), so a sound control here would control nothing
real.

Both settings are a browser-level UI preference, not game state — persisted
to `localStorage` (`grid-text-scale`, `grid-reduced-motion`), deliberately
never touching `get_state()`/`load_state()`, since a save code is meant to
be portable across devices/browsers and a local browser's accessibility
preference shouldn't silently override another device's.

Verified live: 255/255 pytest suite unaffected (pure HTML/CSS/JS, no Python
touched); in a real browser, applying a 1.3 text-scale correctly computed
`<html>`'s font-size to 20.8px, and enabling reduced-motion collapsed the
`.grid-visual`/pylon elements' live `animation-duration` to ~1e-6s, both
persisting to their localStorage keys. The only console error present was
a pre-existing, unrelated AdSense placeholder-client CSP frame-ancestors
warning, reproducible on the unmodified page. Verification required
cache-busting the stylesheet `<link>` directly (a fresh `?v=` query on its
`href`) to sidestep this sandbox's own known static-asset HTTP-caching
quirk — not a defect in the shipped code, the same environment hazard
Continuum's, SOL's, and Canopy's own build notes already document.

## Shared confirmation-dialog integration (C14, site-wide goal)

Retiring a plant type's very last unit now routes through
`shared/confirm-dialog.js`'s `ConfirmDialog.ask()` instead of retiring
immediately (`_make_retire_handler()`'s new `handler()` wrapper in
`game.py`, gated on `state.plant_counts[plant_type] == 1`). Retiring down
from 2+ units, or an already-empty type, stays exactly as instant as
before -- only the true "you're about to lose this capacity entirely"
moment is gated. Covered by 5 new tests in
`tests/test_confirm_dialog.py` (fake `js.window.ConfirmDialog`, since the
real fake-DOM harness's `js` module never provides `window` by default).

**Found and fixed a real bug in the shared file itself while
live-verifying this**: `shared/confirm-dialog.js` built and appended its
overlay DOM at top-level IIFE-execution time, which crashed with
`document.body` still null (every game includes it from an un-deferred
`<script>` tag in `<head>`, before `<body>` is parsed) -- silently
breaking `window.ConfirmDialog` on every page that includes the script,
Grid included. Fixed at the shared-file level (deferred DOM setup to
first real `ask()` call, same lazy pattern `tutorial.js` already uses);
see that file's own header comment and its commit for the full story.
Only found because live-browser verification checks `typeof
window.ConfirmDialog` and the actual click flow, not just the pytest
fake-DOM suite (which never exercises the real script at all).

Live-verified end to end in a real browser after the shared-file fix:
built Coal to 1, clicked Retire -> dialog appeared with the correct
message; Cancel left the plant in place; a second Retire -> checked
"don't ask me again" -> Retire it -> plant count went to 0 and the skip
flag persisted to `localStorage`; building Coal back to 1 and retiring a
third time skipped the dialog entirely as expected. Zero console errors
during the verified flow. Full 260/260 pytest suite unaffected.

## Tech notes

- Python/Pyodide, per root conventions.
- Keep the core state (demand, budget, plant counts, emissions, event log) as a plain serializable object — this makes both testing and later save/resume trivial if you want it.

## Onboarding-tooltip coverage check (site-wide goal, planning/TODO.md, origin A14)

Audited whether a returning player who's forgotten the tutorial can still
make sense of the permanent UI's non-obvious parts, on top of the
persistent, reachable-any-time `#howto-toggle-button`/`#howto-panel`.

Most of the permanent UI already covers itself: the "Power Plants" and
"Maintenance & Aging" section-level `.info-toggle` (i) icons permanently
explain the renewable learning-curve discount and the aging/breakdown-risk
mechanic (matching Canopy's own section-level pattern), and per-round
status figures are all plainly labelled.

**Real gap found:** the Retire button's most non-obvious behavior --
refunding 50% of a plant's *current* (possibly learning-curve-discounted)
cost, not what was originally paid -- was explained *only* by a one-time
`retire-callout` banner, shown once on first-ever retire and then
permanently suppressed (`state.seen_retire_callout`, persisted in save
state). A returning player who dismissed it in an earlier session, or
anyone who first retires a unit long after that banner is gone, had no
permanent way to learn this. The button itself just read "Retire", and no
section-level info-toggle covers refund behavior specifically (the
"Power Plants" toggle only covers *build* cost, not retire refunds).

**Fixed:** added a `title` attribute to all 7 retire buttons (`index.html`)
stating the 50%-of-current-cost refund rule in plain language, matching
Tide's D19 per-tile-tooltip / Canopy's per-plot-tooltip reference pattern
-- a light, permanent, always-available supplement rather than a dialog
or new panel. No `game.py` change needed since the button's `disabled`
state and text logic were already correct; this was purely a missing
static attribute. Maintain's non-obvious "reduces age, doesn't reset to
zero" behavior was left alone since the "Maintenance & Aging" section
info-toggle already states this permanently.

Verified: full 260/260 pytest suite green (HTML-only change, no Python
touched); live-verified in a real browser that all 7 retire buttons
(`coal`/`gas`/`nuclear`/`solar`/`wind`/`hydro`/`battery`) carry the correct
`title` text on the live DOM, that Retire remains correctly
enabled/disabled by plant count exactly as before, and zero new console
errors.

## "What's New" changelog panel (site-wide goal, planning/TODO.md, origin K16)

A new `changelog.json` manifest (flat list of `{date, entry}` objects,
hand-authored newest-first, dates sourced from real commit history via
`git log --follow -- games/grid/CLAUDE.md` rather than guessed) plus a
"📋 What's New" toggle+panel, following the exact same hidden-until-opened
`.section` idiom and dynamic-DOM-build pattern `#achievements-panel`
already established here. Fetched into the Pyodide boot sequence alongside
`achievements.json` (`window.CHANGELOG_JSON`), with the same disk-read
fallback for the pytest harness's fake `js` module that `ACHIEVEMENTS`
already uses. `render()` keeps an open panel live on every action, same
as every sibling panel.

Tests: 260 → 270 (new `tests/test_changelog.py`: catalog sanity, toggle
open/close, panel content matches `CHANGELOG` newest-first, render-time
liveness). Verified live under Pyodide: this sandbox's known static-asset
HTTP-caching quirk (documented in several other games' own build notes)
hit the boot script's *own* `fetch("game.py")` call directly — its default
cache mode kept resolving to a stale cached response for that exact URL
regardless of the outer page URL being cache-busted — so verification
forced a fresh (`cache: 'no-store'`) fetch of both `changelog.json` and
`game.py` and re-ran them through the already-loaded `pyodide` instance.
With the fresh code loaded: the panel opened, listed all 11 real entries
with correct dates/text in newest-first order, and closed correctly on a
second click, with zero console errors.

## UI decluttering pass (2026-09-20, planning/TODO.md closing task)

Audit-first pass, same standard as the site-wide colorblind-safety audit: only change something if it's genuinely crowded, otherwise leave it. Read through `index.html` and `style.css` end to end. Found this game already carries a lot of prior decluttering work: every panel-scale feature (Tutorial, How to Play, Achievements, What's New, Run Summary, Settings) is hidden-until-opened behind toolbar toggles; the funds breakdown is already tucked behind a `.funds-breakdown-toggle` `<details>`; every non-obvious mechanic has its own inline `.info-toggle` "i" disclosure; and `.section` cards each carry a distinct colored left border (`#status` cyan, `#plants` orange, `#plant-mix` green) so the page already reads as labeled zones, not one flat wall.

**Real gap found:** `#plant-mix`'s six `.mix-row` composition bars (Coal/Gas/Nuclear/Solar/Wind/Hydro, each a label + bar + percentage) were the one remaining always-visible block that's genuinely supplementary — it's a generation-capacity-share breakdown a player might check occasionally, not something needed at a glance to decide this round's build/retire/maintain actions (unlike `#status`'s funds/emissions/disruption-risk, which are decision-critical every round), and it added six full rows of always-on UI for information a player doesn't need turn-to-turn.

**Fixed:** wrapped the six `.mix-row` divs in a new block-level `<details class="mix-breakdown-toggle">` (`index.html`), collapsed by default, with a plain "Show breakdown" `<summary>` — the "Plant Mix" heading and its existing info-toggle stay visible outside the disclosure so the feature is still discoverable. Styled in `style.css` by copying Tide's own `.ticker-history-toggle` idiom (0.78rem, opacity 0.65 summary, block spacing) so the two games touched in this pass share one collapse-affordance look. No `game.py` change — `render()` only ever does `document.getElementById(...)` on the same six `-mix-bar`/`-mix-pct` ids, which are untouched by the wrapping div.

Verified: full 270/270 pytest suite green (HTML/CSS-only change, no Python touched, tests only reference elements by id via `getElementById`/`document.elements[...]`, none assert on DOM nesting). Everything else audited and left alone: `#status`'s status-line stack, the trend graph, and the seven `.plant-row` build/retire/maintain rows are all either decision-critical every round or already grouped under a labeled, bordered `.section` card — collapsing any of those further would hide information a player actually needs mid-round, which is exactly the over-collapsing failure mode this pass is meant to avoid.

## Working conventions

- Commit + tag per milestone: `git commit -m "Milestone N: <name>"` then `git tag grid-milestone-0N`.
- Update the milestone table Status as work happens.

## Round-2 improvement pass (2026-09-20, planning/TODO.md C-items)

Built: C4 (wear-% tooltip with the numeric aging rules), C26 (three wear-tier glyphs ○◔◑● beside the wear %), C5 (operator letter grade A-F from cumulative emissions vs. the benchmark line, in Run Summary), C11 (resilience/diversification score = normalized Shannon entropy of generation shares), C25 (20-round unchanged-fleet projection in Run Summary), C12 (diamond marker at the best-clean-share round on the trend graph), C14 (bar visuals in the funds breakdown), C13 (starting scenarios — Standard / Coal-heavy legacy / Greenfield — cycled by a toolbar button, locked after the first build or round; `scenario` persisted, defaults safely for old saves), C10 (toast now carries a "Why:" line naming the plant), C18 (retire-last dialog shows wear + age), C20 (demand growth arrow; only up/flat states exist since growth is otherwise constant), C22 (steeper label shows x2), C24 (emissions-meter pulse on the 50%-renewable crossing), C28 (always-visible clean-streak line), C8 (renewable/fossil/low-carbon icon on plant-mix labels), C6 (mix-bar transition lengthened; width was already animated), C15 (Run Summary percentile of emissions via `GET /stats/games/grid/percentile`, JS hook `window.gridCompare` in index.html; falls back to "isn't available yet" until the endpoint is deployed).
Already satisfied, no change: C2 (badge already shows the exact %), C30 (persistent renewable-unlock blurb).
Not built: C1, C3, C7, C9, C17, C19, C23, C27, C29 (large mechanics, left for later passes). Tests 270 -> 287 (`tests/test_round2_items.py`).
