# Grid — Energy Transition Game

**Built following the shared conventions in `planning/archive/climate-quartet-plan.md`** (testing, feedback hook, hope-angle requirement, hub integration — moved there 2026-09-22 once all four quartet games shipped; was `climate-quartet-plan.md` at the games root while build order still mattered). This file is Grid-specific only.

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
| 7 | Desktop boot (PC version): `pc.html` generated from `index.html`, full-window layout, Desktop tutorial, layout switch on the opening screen | Done (2026-10-06); see "Desktop boot" below |

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

**Deliberately left alone:** `PLANT_ICON` emoji and the `wear-1`/`wear-2`/`wear-3` desaturation filters (aging-vulnerability cue) — these are the actual state-encoding visuals (plant identity + wear) and weren't touched beyond leaving their existing filter/opacity values exactly as they were. The trend-graph SVG stroke colors (`trend-line--emissions`/`--cost`/`--global`) are also untouched — they're a legend, not decoration. No "no motion" test constraint exists in this game's `tests/` (that's a Drift-specific wellbeing-pass decision, confirmed by grepping all 8 climate-quartet games' tests before starting) and `climate-quartet-plan.md` (now `planning/archive/climate-quartet-plan.md`)'s own visual-polish requirement explicitly calls for eased transitions, so the existing `transition: filter`/`width` rules were kept and a hover-brightness transition was added to buttons — no new hover-lift/transform motion was introduced. `ad-bar.css`/`shared/info-page.css` are shared files out of this game's scope and weren't touched (matches SOL, which also left them flat). Full pytest suite (132 tests) stayed green throughout; live-verified in-browser (starfield/glass panels render, Solar build + Advance Round both work exactly as before, funds/capacity/round state update correctly, no new console errors beyond a pre-existing ServiceWorker-registration warning unrelated to this CSS/HTML-only change).

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


## Reset-to-default settings button (Z-extra/A26, site-wide goal)

A "Reset to Default" button (`#settings-reset-button`) sits at the bottom of the settings panel, below the existing text-size and reduce-motion controls -- SOL's own A26 answer flagged this as a site-wide pattern rather than a SOL-only feature, folded into `planning/TODO.md`'s Z-extra checklist. Implemented entirely in `settings.js` (no Python touched, matching this file's own "deliberately independent of Pyodide" rule for the rest of the settings panel): one click calls `applyScale(DEFAULT_SCALE)` and `applyMotion(false)`, updates `--text-scale`/`data-text-scale`/`data-reduced-motion` on the live DOM immediately, resets the reduce-motion checkbox's own `checked` state to match, and writes both defaults back to `localStorage` so the reset survives a reload rather than only looking reset until the next render. No confirmation dialog -- this is a low-stakes, instantly-reversible display preference, not a destructive action, so `shared/confirm-dialog.js` is deliberately not wired up here.

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

- Commit + tag per milestone: `git commit -m "Milestone N: <name>"` then `git tag grid-milestone-0N`.
- Update the milestone table Status as work happens.

## Round-2 improvement pass (2026-09-20, planning/TODO.md C-items)

Built: C4 (wear-% tooltip with the numeric aging rules), C26 (three wear-tier glyphs ○◔◑● beside the wear %), C5 (operator letter grade A-F from cumulative emissions vs. the benchmark line, in Run Summary), C11 (resilience/diversification score = normalized Shannon entropy of generation shares), C25 (20-round unchanged-fleet projection in Run Summary), C12 (diamond marker at the best-clean-share round on the trend graph), C14 (bar visuals in the funds breakdown), C13 (starting scenarios — Standard / Coal-heavy legacy / Greenfield — cycled by a toolbar button, locked after the first build or round; `scenario` persisted, defaults safely for old saves), C10 (toast now carries a "Why:" line naming the plant), C18 (retire-last dialog shows wear + age), C20 (demand growth arrow; only up/flat states exist since growth is otherwise constant), C22 (steeper label shows x2), C24 (emissions-meter pulse on the 50%-renewable crossing), C28 (always-visible clean-streak line), C8 (renewable/fossil/low-carbon icon on plant-mix labels), C6 (mix-bar transition lengthened; width was already animated), C15 (Run Summary percentile of emissions via `GET /stats/games/grid/percentile`, JS hook `window.gridCompare` in index.html; falls back to "isn't available yet" until the endpoint is deployed).
Already satisfied, no change: C2 (badge already shows the exact %), C30 (persistent renewable-unlock blurb).
Not built: C1, C3, C7, C9, C17, C19, C23, C27, C29 (large mechanics, left for later passes). Tests 270 -> 287 (`tests/test_round2_items.py`).

## Round-3 pass (2026-09-21) — three of the remaining large mechanics

Built C7, C17, and C19 (all `tests/test_round3_items.py`, 287 -> 304). C23 (maintenance scheduling) got its `GridState` methods (`set_maintenance_schedule()`/`_run_scheduled_maintenance()`, wired into `advance_round()`) but no UI yet — left as backend-only, tracked as a real follow-up rather than rushed, since it's genuinely a fourth separate feature and this pass already covers three.

**C23's UI, finished 2026-09-21.** A `<select id="{plant}-maintenance-schedule-select">` (Manual only / Every 3 / 5 / 8 rounds) sits in each plant row's own action strip, right after Maintain — a per-plant-type setting rather than a fourth action button, so it gets its own full-width line under Build/Retire/Maintain via `flex-basis: 100%` rather than competing with them for space. Disabled whenever that type has zero plants, same gating `maintain-button` already uses, and its displayed value is resynced from `state.maintenance_schedule` every render so a loaded save or a grid reset never leaves it showing a stale cadence. `_run_scheduled_maintenance()`'s own backend logic (built in the round-3 pass above) had no test coverage at all before this pass — `tests/test_maintenance_schedule.py` covers the select's disabled/enabled gating, value sync, invalid-interval rejection, the interval actually firing on schedule (round 3 of an every-3-rounds schedule, confirmed via `maintenance_actions_count`), manual-only never auto-firing, a best-effort skip when funds can't cover it that round, and a stale schedule on a since-retired-to-zero plant type staying inert rather than erroring. 304 -> 311 tests. Verified live: built a coal plant, switched its schedule to "Every 3 rounds," advanced three rounds, and confirmed `state.maintenance_actions_count` read `1` — matching the test suite's own assertion — with zero console errors.

- **C7 — demand response.** A fourth lever alongside build/retire/maintain, but acting on demand growth itself rather than the fleet: `invest_demand_response()` permanently trims `demand_growth_this_round()` at an escalating cost (`DEMAND_RESPONSE_COST_GROWTH` per level), floored at `DEMAND_RESPONSE_MIN_GROWTH` so growth can never go negative or stall entirely. `demand_growth_this_round()` is the single source of truth `advance_round()`/`projection()`/the demand-arrow tooltip all read, so investing correctly flattens the 20-round projection line too, not just the next round.
- **C17 — weather-event log.** A separate log from the emissions-driven disruption log, narrating specifically how Weather Variability affected renewable output round to round (`"Round N: weather variability put renewable output X% above/below nameplate capacity"`). `effective_capacity_for_revenue()` stashes the round's nameplate/actual renewable figures so `advance_round()` can narrate them without a second, non-deterministic `weather_rng` call — the log only ever describes what actually happened, never re-rolls anything. Same hidden-until-opened `.section` toggle idiom as the changelog/achievements panels; capped at `WEATHER_LOG_MAX_ENTRIES`.
- **C19 — policy lever.** An occasional opt-in choice, offered every `POLICY_LEVER_INTERVAL` rounds when none is active: carbon pricing (fossil builds cost more) or a renewable subsidy (renewable builds cost less), both temporary (`POLICY_LEVER_DURATION` rounds) build-time-only price signals. `plant_cost()` (the current build price) includes the active policy's multiplier; retiring refunds off `_learning_curve_cost()` instead (the price *before* any policy adjustment) — a policy discount is meant to encourage building during the window, not to be exploitable via build-then-immediately-retire for a policy-inflated refund. Verified with a dedicated regression test on top of the existing retire-refund-exploit protection this file's own second audit pass already documented.

All three plug into `demand-response-button`/`-level-display`, `policy-lever-banner`/`active-policy-display` + its three action buttons, and `weather-log-toggle-button`/`-panel` in `index.html`, registered in `tests/conftest.py`'s `ELEMENT_IDS`. Full 304/304 pytest suite green; not verified live in a running browser this pass (pure additive UI wiring following an established pattern, `flake8` clean).

- 2026-09-21: mobile-dock `body` padding-bottom now `html body` so it beats ad-bar.css (V-AB-2).

## Round-4 pass (2026-09-21) — C9, C27, C1

Built C9, C27, C1 (`tests/test_round4_items.py`, `tests/test_career.py`; 311 -> 343 tests). Not built: C3 (two interconnected grids — a second full GridState plus transfer UI, out of budget), C29 (needs honestly sourced per-region generation data; none sourced, so skipped rather than invented).

- **C9 storage arbitrage.** A per-round Idle/Charge/Discharge mode button (in the Battery row, disabled until a battery exists) plus an info toggle. Charge banks generation above demand (which earns nothing) at 85% round-trip efficiency; Discharge sells stored energy into a shortfall at 1.5x price. Storage cap = 2x battery capacity, rate = battery capacity per round. Never touches emissions/disruption math. Mode is sticky and spelled out in text.
- **C27 emergency response.** A fourth, opt-in entry in the scenario cycle (last, so it's never the default): 3 coal + 1 gas, 300 funds, demand 180. Get capacity to demand for 2 consecutive rounds within 6 rounds. No game over: missing the window just closes the banner as "missed" and play continues. Status banner `#emergency-status-display`.
- **C1 operator career.** Career panel (toolbar toggle). "Finish run" (through ConfirmDialog) banks points (1 + operator grade A4..F0 + 1 for resilience 60+ + 1 for stabilizing the emergency; runs under 5 rounds don't count) and starts a fresh GridState. Points buy four modest perks (seed capital, crew training, storage partnerships, demand analytics) that apply from the next run; none touches emissions, disruption or the learning curve. Earned achievements are banked so they persist across runs. Persisted in localStorage `grid_career_v1` and mirrored into `get_state()["career"]`; `validate_career()` defaults/clamps everything, unlocks can't exceed earned points, and `load_state()` never adopts a career with fewer finished runs than the live one.
- **Save fix.** `get_state()` previously omitted the round-3 fields (demand response level, weather log, policy lever state, maintenance schedules), so they silently reset on load; now saved with validation (`_load_round3_fields`).
- Live-verified in the browser pane: emergency scenario, arbitrage button, finishing a run via the real dialog, localStorage write; zero console errors.
## Screen-reader accessibility audit (Z15, site-wide goal, planning/TODO.md)

Static-analysis audit (grepping/reading `index.html`/`game.py`, no live screen
reader in this environment — same audit-only method the colorblind-safety
passes already established for this hub) of the achievements and settings
panels: toggle-button accessible names, panel role/heading semantics, focus
order on open/close, keyboard reachability of interactive elements, and
checkbox/label association.

**Found and fixed one real gap:** the settings panel's own title
(`Display Settings`) was marked up as a plain `<p class="settings-panel-heading">`
rather than a heading element, so a screen-reader user navigating by heading
(the "jump between headings" navigation mode most screen readers offer) would
never see it — it read as an anonymous paragraph. Changed to
`<h2 class="settings-panel-heading">` (CSS is a pure class selector, so the
visual appearance is unaffected — it now matches the `<h2>` several other
games in this hub already use for the identical heading). No `game.py`
change needed; no test referenced the tag.

Everything else audited clean, matching this hub's site-wide pattern:
- Both toggle buttons (`#achievements-toggle-button`, `#settings-toggle-button`)
  already carry descriptive visible text ("🏆 Achievements (N/M)" / "⚙️ Settings"),
  which is a sufficient accessible name on its own — no `aria-label` needed.
- The achievements panel itself has no heading of its own, but is adequately
  labeled by the toggle button's own visible text immediately above it — the
  same "plain semantic markup is enough" call this hub's colorblind-safety
  audits already made for comparable cases; not over-engineered with ARIA
  that plain HTML already covers.
- No focus-trap exists anywhere in this hub, and none was warranted here:
  clicking the toggle button never moves focus itself, so it naturally stays
  on that same button when the panel opens or closes (no case of focus being
  silently dropped to `document.body`).
- Every interactive element inside both panels is a real `<button>`/`<input>`
  (confirmed via a site-wide grep for `.onclick =` assignments and
  `createElement("div")` calls with a wired click handler — none found; the
  achievements panel's own cards are static informational `<div>`s with no
  click behavior, so they don't need to be buttons).
- The reduced-motion checkbox is properly associated with its label
  (`<label class="settings-checkbox-label" for="reduced-motion-checkbox">`
  wrapping the input).

Verified: full pytest suite green (pure HTML tag-name change, no Python
touched), `flake8` unaffected (no `.py` file in the diff).

## R2-C16: "Stored Power" achievement (2026-09-21)

Added the `first_storage` achievement (label "Stored Power", earned by building the first battery; predicate `state.cumulative_built["battery"] >= 1`, so it survives retiring the battery) instead of a bespoke first-battery callout, per the user's note that callouts should become achievements. The existing unlock toast announces it. The other existing callouts (renewable milestone, Retire refund, Maintain cost) are not plant-type callouts and were left as they are. Grid now has 17 achievements; suite 344 passing (added one test in `tests/test_achievements.py`).

## 320px mobile-viewport audit (Z18, site-wide goal, planning/TODO.md)

Checked at a genuine 320px viewport (narrower than the original 375px
mobile pass) via the Claude Browser tool's `resize_window`.

**Real bug found and fixed:** `#advance-round-button.mobile-docked`
(`style.css`) set `position: fixed; left: 1rem; right: 1rem;` to dock the
button above the ad bar with a 1rem margin on each side, but never
overrode `button.primary`'s base `width: 100%` — once fixed-positioned,
that `100%` resolves against the *viewport* (its containing block, since
nothing here re-establishes one), not the narrower gap `left`/`right` were
trying to carve out. At 320px the button held its full 320px width and ran
past the right edge instead of shrinking to fit — the exact same bug shape
Continuum's own docked Advance Season button had (see that game's Z18
section). Fixed with `width: auto`, letting `left`/`right` (and the
existing `max-width: 480px`) size the box correctly; confirmed live at
288px wide (320 − 2×16px), flush inside both margins.

No other overflow found (the top `#mobile-hud-bar` strip's own
`overflow-x: auto` is the same deliberate "let it scroll instead of clip"
idiom Canopy's Z18 section documents, not a bug). `flake8`/tests
unaffected (pure CSS) — suite stayed at 344/344; a caching quirk in this
dev environment (documented earlier in this file, under "Settings panel")
required busting the `style.css` `<link>` directly, not just the page URL,
to see the fix take effect while verifying.

## Difficulty-aware achievements audit (Z27, site-wide goal)

Grid has the most difficulty-shaped surface area in the hub: two freely
reversible opt-in toggles (C16 steeper demand growth, C4 weather
variability on renewable output) plus C13's four starting scenarios
(standard/coal-heavy legacy/greenfield/emergency), locked in once any
round has been played.

Checked both toggles first, since they're the more obviously "hard mode"
pair. **Weather variability never touches `disruption_probability()`/
`disruption_severity()` at all** — `effective_capacity_for_revenue()`
only varies *revenue* around a fixed nameplate figure; the two
achievements most likely to be at risk from a harder disruption profile
(`clean_streak_15`, `no_damage_20`) read `disruption_probability()`
exclusively, so this toggle can't touch them either way. **Steeper demand
growth** only doubles `demand_growth_this_round()` — it makes the demand
target rise faster, but `disruption_probability()` is driven purely by
`self.emissions` (cumulative fossil-plant output), which the player
controls directly by choosing what to build to meet that faster-growing
demand. A harder demand curve makes the balancing act harder, not
structurally different — the same "more skill required, not less
possible" shape SOL's/Canopy's own toggles land on.

**C13's scenarios were the one candidate worth actually running the
numbers on.** `coal_legacy`/`emergency` both start with real standing
fossil capacity (4 coal + 1 gas, or 3 coal + 1 gas), and `self.emissions`
is a cumulative, never-decreasing counter — a naive worry was that
starting emissions baked in during round 1 could permanently inflate
`disruption_probability()` for the rest of the game, threatening
`clean_streak_15`/`no_damage_20`. Checked the actual mechanics: emissions
only accrue via `advance_round()` calling `emissions_this_round()`, which
reads the CURRENT standing fleet — so a player who retires every inherited
fossil plant before ever clicking "Advance Round" for the first time never
adds a single unit of emissions from the scenario's starting fleet at all.
Both achievements stay fully reachable from a coal-heavy or emergency
start; the scenario just demands that one specific piece of savvy play
(retire first, advance second) that a standard/greenfield start doesn't.

**No change needed.** Nothing in Grid's difficulty surface makes an
achievement's condition unsatisfiable — every path stays a "play better"
problem, never a "the toggle removed this outcome" one. No code touched;
`flake8`/tests unaffected.

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
`localStorage["whats-new-seen:grid"]` (the date string of the newest
entry already shown) and lists just the new ones, not the whole log. A
first-ever visit silently marks the current changelog as seen rather
than dumping the full history on a brand-new player. Reuses the same
`window.CHANGELOG_JSON` global this game's own changelog panel already
fetches -- no second network request. One `<script
src="../../shared/whats-new-banner.js" data-game-id="grid">` include,
added right after `shared/last-played.js`'s own include. See root
`CLAUDE.md`'s Working notes for the full write-up -- shared
infrastructure, documented once there rather than duplicated across all
12 games' own files.

## Keyboard-shortcut convention: ?/Esc (Z4, site-wide goal)

Wired via the new shared `shared/keyboard-shortcuts.js` -- one script
include plus one `KeyboardShortcuts.init({panels: [...]})` call at the
end of `index.html`, listing this game's real toggle-button + hidden-
panel pairs: How to Play, Settings, Achievements, What's New, Summary,
Weather Log, the Info Page, and Career. `?` opens a small floating
shortcuts-help overlay; `Esc` closes it and clicks the toggle button of
whichever listed panel is currently open, reusing each panel's own
open/close logic. The Steeper Demand / Weather Variability / Scenario
difficulty toggle buttons aren't in the list -- they're on/off flags with
no corresponding panel, not something Esc can meaningfully "close."

## Comparison/benchmark chart migrated to shared component (Z17, site-wide goal)

The C15/Pass-2 "global comparison" line -- this game's own hand-rolled
combined-min-max trend-graph normalization plus per-point hoverable
markers -- is now built by composing the new shared
`shared/comparison_chart.py`'s `normalize_together()`/`marker_fragment()`/
`xs_for()` building blocks, and `global_comparison_message()` now
delegates its ahead/behind/tie branching to that module's
`comparison_message()` (with this game's exact original wording kept via
its `ahead_text`/`behind_text`/`tie_text` overrides). Grid is the
reference integration this shared component was generalized FROM -- see
that module's own header comment for the full story, and Continuum's K13
"vs. history" chart / Herd's new F15 chart for the other two integrations
built on it. The avg-renewable-cost line and the best-round diamond
marker stay local to this file's own `trend_graph_svg()`, since neither
is part of the "you vs. a reference" comparison shape the shared
component covers.

Pure refactor -- byte-for-byte the same rendered SVG/message text as
before. Full 344-test pytest suite green (the 6 unrelated failures seen
mid-session in `test_achievements.py`, from a concurrently-running
sibling agent's in-flight `card.dataset` work, are not from this change --
confirmed by re-reading the diff, which touches none of that code); `flake8`
clean. Live-verified via the shared `hub-dev-server`: built coal capacity
and advanced several rounds, confirmed the trend graph renders real,
differentiated emissions/global/cost lines with correct hoverable
`<title>` tooltips, and the global-comparison message correctly read
"Your grid has emitted 720 vs. an estimated 329 ... you're behind the
curve." Zero console errors.

## Shadow grid (C21, 2026-09-26)

The lighter 'grid twin': a second, NON-interactive grid that mirrors your build and retire choices onto a different starting scenario (Standard, Coal-heavy legacy, Greenfield or Emergency), so the two outcomes can be compared side by side. It is derived, not simulated live: your successful builds and retires are logged with their round (`shadow_actions`, capped at `SHADOW_MAX_ACTIONS` 400) while the shadow is on, and `replay_shadow()` replays them round by round on a fresh grid with its own fixed random stream (`SHADOW_SEED`), so it is reproducible, cannot affect your grid, and needs only the scenario name plus the action log to save. A mirrored move the twin cannot afford is skipped and counted in the verdict line. A table shows score, funds, clean share of capacity and emissions avoided for you and the twin. It sits in the trend section beside the C15 global comparison. Save: `shadow` written only when on; on load the scenario must be a known one and every action is validated (round int >= 1, kind build or retire, known plant type). 344 -> 360 tests (`tests/test_shadow_grid.py`); verified live.

## Regional grid (C3, 2026-09-26)

The lighter multi-grid mode -- a one-way 'Connect a regional grid' switch, same shape as Tide's D3 sister settlement: it shares this grid's own spare capacity rather than adding a second grid's worth of plants to manage. It has no plants of its own; its own demand (`REGIONAL_DEMAND_FRACTION`, 0.35 of this grid's) grows automatically alongside this grid's, needing no separate growth model. Each round, `_advance_regional_grid()` first serves the regional demand from whatever main-grid surplus capacity this round's storage-arbitrage charging didn't already claim (reads `_run_arbitrage()`'s own record of what it took, so the same idle capacity is never counted for both), earning a little revenue for the surplus it uses; whatever regional demand still isn't covered falls back to buying power in for it, at shared funds' expense. Never touches this grid's own emissions/disruption math. A readout under the connect button shows cumulative units shared and the net funds effect so far. Save: `regional_grid` written only when connected (running totals, validated finite and non-negative on load); a save without the key loads unconnected. 360 -> 370 tests (`tests/test_regional_grid.py`); flake8 clean. Verified live via a standalone local server (the shared `hub-dev-server` port was already held by another concurrent session): built 3 nuclear plants (300 capacity vs. 100 demand), connected, advanced one round, and the readout correctly showed "35 units of spare capacity shared so far, net +35 funds effect" -- exactly the expected 100 x 0.35 regional demand, fully covered by surplus. No console errors beyond the pre-existing, unrelated ServiceWorker-registration quirk this hub's other build notes already document.

## Real grid comparison (C29, 2026-09-26)
`REAL_GRIDS` holds three regions' published generation mixes, read from live pages on 2026-09-26 rather than recalled: the U.S. from the EIA's 'Electricity in the U.S.' (2025, its rounded 'about' figures), Germany from Wikipedia's Energy in Germany net-generation table (2025; lignite + hard coal shown as coal, biomass as other) and France from Wikipedia's Electricity sector in France (2020, the newest full-year table on that page). Australia was checked and left out because the page only gives renewables as one lump. `real_grid_rows()` compares each generation type's share of standing CAPACITY (what this game tracks) with the region's share of GENERATION, plus other and a clean total (nuclear + solar + wind + hydro, matching the game's non-fossil idea); the panel states that difference and names the source. `real_grid` is saved only when on and validated against `REAL_GRIDS` on load. Rendered with the shadow grid's table styling. The TODO's 'community-sourced' wording was read as 'sourced from published real data', since there is no per-region community data to draw on. Tests: `tests/test_real_grid.py` (10; 360 -> 370). Verified live.

## Story mode: Kestrel Valley (W1-grid, 2026-09-26)
The first user of the new shared `shared/story-chapters.js` (site-wide W1: story for low-story games). `story.json` holds 18 short authored chapters, one opening plus one per achievement in `achievements.json` (a test pins that every achievement has a chapter). `_story_reach_all()` calls `window.NoyvjStory.reach(id)` for the opening and every earned achievement from `_check_new_achievements_for_toast()` and `_seed_achievement_toast_baseline()` (so a loaded save brings its chapters back); it is idempotent, silent without the script, and adds nothing to the save. The panel shows only reached chapters, in story order, with a latest-line banner, and `story-toggle.js` (newly added to Grid) lists `#story-chapters` so the Story pill turns it off. Progress is per-browser localStorage. No number, unlock or save key changes. Tests: `tests/test_story_chapters.py` (6; 380 -> 386). Verified live.

## Desktop boot (PC version, 2026-10-06)

`games/grid/pc.html` is the Desktop boot: the same game over the same `game.py` and saves (same `game_id`), laid out for a wide window with a mouse. **Never edit it by hand**: it is generated from `index.html` plus `pc-config.json` by `scripts/generate-pc-pages.py` (run it after changing either; `--check` and the shared tests fail if it is stale). No rule, state or save change, and `game.py` is untouched. Classic (`index.html`) only gained the `shared/layout-pref.js` tag and the `window.GRID_PC_TUTORIAL_STEPS ||` fallback on the tutorial init.

- **Where things went.** Top bar: back link, title, three icon buttons (Achievements, Run Summary, Settings), the Menu button and the Story pill. Readout chips under it (round, Demand, Funds, Capacity, Emissions, Fossil share), built by the shell from the same `#round-display`, `#demand-display` ... text lines, which keep updating inside a hidden holder together with the rest of `#status`. Stage: the transmission-line strip, then the Power Plants board as one compact row per plant type (name, count, wear, Build / Retire / Maintain, Auto-maintain), then Plant Mix. Side column (scrolls on its own, Advance Round pinned at the top): milestone callout, emergency status, policy lever banner and active policy, demand response, the disruption-risk line with the emissions meter, last round's disruption and aging events, clean streak, score and meter, the trend text, the trend graph with its messages, and the funds breakdown (relabelled "Funds breakdown" by CSS). Windows (Menu or the icons): How to Play, Achievements, What's New, Run Summary, Weather Log, Grid Operator Career, Settings, In the real world, plus three composites opened from the Menu: Compare and connect (shadow grid, real grid comparison, regional grid), About Grid (tagline and context blurbs), Feedback (the end-of-run prompt). The difficulty toggles and the starting scenario button sit in the Menu's Game group.
- **Desktop tutorial.** `pc.js` sets `window.GRID_PC_TUTORIAL_STEPS` (11 steps pointing at the chips, the board, the side column and the Menu); every selector exists on `pc.html` (the shared tests check it).
- **Hotkeys.** Grid only has `?` (shortcut help) and Esc (closes the open panel), so the hint bar lists just those plus Esc for the Menu. No notification stack (`notify` is null): Grid has no log list, its toasts are the existing achievement and disruption toasts.
- **Layout notes.** `pc.css` clears the ad-bar body padding (it made the body scrollable by 22px, and the tutorial's scroll-into-view then pushed the whole layout up), clips the ambient blobs, moves the floating theme toggle to the top-right corner, and at 1280px wide or less shrinks the plant rows (Auto-maintain shortened to "Auto:", narrower side column); at 780px tall or less the decorative transmission-line strip is hidden. Verified live at 1440x900 and 1024x700 in dark and light themes: no page scroll, the whole plant board fits without scrolling at both sizes.
- **Known limits.** At 1024x700 the side column scrolls a few pixels (its own scroll, not the page). Below about 960px wide the plant rows wrap their buttons onto a second line and the stage scrolls; phones and narrow windows are meant to use Classic. The Story panel floats over the side column while open. The shared keyboard-shortcuts help overlay (`?`) is not a window of the Desktop shell (it is the shared overlay and works as in Classic).

## Round-5 pass (2026-10-07) — career depth, auto-advance, recap, presets

Built from `planning/TODO.md` "GC + C. Grid": C-1, C-2, C-7, C-8, C-10, C-16, GC-17, GC-26 (`tests/test_round5_items.py`; 386 -> 418 tests together with the updated save-key and confirm-dialog fakes).

- **C-1 run history.** `GridState` now also records `funds_history` and `demand_history` each round. `finish_run()` files a record (`run_record()`: scenario, grade, points, rounds, score, resilience, final funds/emissions, best streak, disruption counts, built totals, and clean-share/funds/demand series thinned to at most `CAREER_SERIES_POINTS` = 30 points) into `career["history"]` (last `CAREER_HISTORY_MAX` = 12 runs, oldest first). Everything is validated on load (`_validate_run_record`), so old careers and hand-edited saves default safely. The Career panel's "Run history" section lists runs newest first and draws three stacked small charts (clean share, funds, demand), one line per run for the six most recent runs, each plotted start to end of its own run; every line has its own colour AND dash pattern, and the legend repeats them.
- **C-2 perk gaps.** Each perk has an `effect` string ("+75 funds at the start of every run"); locked perk buttons say "N more point(s) needed" or "ready to unlock", and a "Next perk" line names the cheapest locked one. Perks stay single-level, so no next-level preview was needed.
- **C-7 lifetime statistics.** `career["lifetime"]` holds uncapped totals (rounds, plants built, brownouts, damage events, aging breakdowns, per-scenario grade points), kept apart from the capped history. Panel section "Lifetime statistics": rounds played, average grade per scenario, most-built plant, disruptions by cause, plus a clean-share heatmap (one row per saved run, one hue whose strength is the clean share, exact figure in each cell's tooltip). Aging breakdowns are counted by the new `aging_breakdown_count`.
- **GC-26 records.** `career["best_streak"]` and `career["best_rounds_to_90"]` join best score/grade. `first_90_clean_round` is set the first round the standing grid is at least 90% non-fossil. Beating a previous record on Finish run shows a "New record!" line (brief pulse, static under reduced motion) until the next round; a first run only sets records, it never flashes.
- **C-16 backup, restore, reset.** "Export career" puts the career JSON in a text box (and on the clipboard when the browser allows), "Import career" validates pasted JSON (non-career data is refused, perks can never exceed earned points), "Reset career" copies a backup first, then asks. Import and Reset use `ConfirmDialog` with `allowSkip: false` (`_confirm_dialog_ask(..., allow_skip=False)`), so "don't ask again" can never skip them. Note: a loaded save still adopts the career it carries if that has at least as many finished runs (existing C1 rule), so loading an old save after a reset restores the old career.
- **GC-17 auto-advance.** `auto_advance()` plays up to 5 rounds and stops after the first disruption, aging breakdown or policy-lever offer (the toast and achievement checks run afterwards); disabled while a policy offer is open. A status line says how many rounds ran and why it stopped. No building happens in between.
- **C-8 round recap.** `last_round_recap` (saved, validated on load) breaks the last round into base revenue, arbitrage, regional grid, scheduled maintenance, weather delta, disruption loss, aging repair and demand growth; shown as an expandable `<details id="round-recap">` in the status column.
- **C-10 difficulty presets.** Relaxed (greenfield start, no toggles), Standard (default) and Operator (steeper demand plus weather variability) set the three existing controls together. The preset is derived from steeper/weather/scenario, never stored, so any other mix reads "Custom"; the header line "Difficulty: X" sits under the title. The scenario part only applies before the first build or round (a note says so).
- **Desktop.** Auto-advance and the recap are in the side column, the header label beside the title, the preset in a new "Difficulty" window (Menu > Game); the new career sections live in the existing Career window. `pc.html` regenerated.
- **Saves.** `get_state()` gained `funds_history`, `demand_history`, `aging_breakdown_count`, `first_90_clean_round` and `last_round_recap`; each loads with a safe default from older saves. The career block in saves now also carries history, lifetime and records.
- Wiring pass 2026-10-08: the Run Summary panel carries the shared Copy result button (`copy_result_fields()` in game.py feeds `shared/copy-result.js`; the panel is rebuilt every render, so the inline script at the end of index.html re-mounts the button with a MutationObserver), earned achievement cards get a Share button (`shared/achievement-share.js`), the head carries the Open Graph/Twitter block and JSON-LD from `share/meta/grid.html` and `share/jsonld/grid.json`, and the How to Play and Info panels end with a Credits link. Pins: `tests/test_wiring_oct8.py`.

## Round-6 pass (2026-10-08) — seeded runs, the upgrade tree, what-if, play polish

Built from `planning/TODO.md` "GC + C. Grid": **GC-2b, GC-1, GC-11, C-3, GC-15, GC-21, GC-4, GC-25, C-4, C-26** (new tests: `tests/test_seeded_runs.py`, `test_upgrade_tree.py`, `test_whatif_and_play.py`, `test_hover_and_load_report.py`; 430 -> 505 tests with the rewritten career tests). Not built (reasons in the session report): GC-3, GC-5, GC-6, GC-7, GC-8, GC-9, GC-10, GC-12, GC-14, GC-16, GC-18, GC-19, GC-20, GC-22, GC-24, GC-27, GC-28, GC-29 and C-5 to C-30 except C-4 and C-26.

- **Seeded runs (the foundation).** Grid used `random.random()`, so no run could be replayed. `game.py` now reuses the shared Z-1 helper read-only (`shared/seed.py`, fetched into Pyodide next to `skill_tree.py` in `index.html`). A run has `state.seed` (`GRID-K7F2Q`) and every draw comes from a STATELESS stream `state.stream(label, round)` = `seed.Rng(f"{seed}#{label}#{round}")`: `disruption`, `aging` and `weather` (what `advance_round()` uses when no callable is passed; tests, the shadow grid and auto-advance still pass their own), plus `grant`, `eulogy` and nickname draws. Same seed and same choices give the same run; a peek and a what-if replay are exact because the stream does not depend on how many draws came before. A typed seed (`set_seed`, "Run setup" details in the Difficulty row, Desktop: Menu > Difficulty and run setup) is accepted only before the first build or round. The test fixture seeds Python's `random` and pins `QUIET_SEED = "GRID-BCDFG"` (no grant offer in 40 rounds) so older exact-round tests never meet a grant.
- **GC-2b the upgrade tree.** `CAREER_TREE` (`shared/skill_tree.py` rules, drawn by `shared/skill-tree.js` into `#career-tree`; the old `career-unlock-*` buttons are gone). The four original perks are the first nodes of the Operations branch with unchanged ids, costs and effects, so old careers load as they were; `career["unlocked"]` is the owned list, validated by `skill_tree.sanitize_owned(..., overspend="trim")` (unknown ids, repeats, nodes missing a prerequisite and overspend are dropped). 14 nodes, 52 points in all, no refunds, no randomness. A run that has not started (`state.unstarted()`) picks up newly bought nodes at once; a run in progress keeps its rules until the next run (as before).
- **GC-2b starting loadout.** Three Starting-loadout nodes make a choice at run setup (`#start-option-select`, remembered in `career["loadout"]` for the next runs): Old Coal Contract (2 aged coal plants for free), Storage Startup (1 battery), Diplomatic Immunity (the first disruption of the run is waived; a waived round counts as disruption-free). Applied inside `apply_scenario()` so it stacks on any scenario; locked once anything is built or advanced. No random mutators.
- **GC-1 projects (the deterministic replacement for the declined card draw).** Projects branch: Wind site leases and Solar site leases (-15% build cost), Storage subsidy (-20% batteries), R&D grant (needs both leases; renewable decay 0.95 -> 0.94 per unit built, floor unchanged) and Policy liaison (renewable subsidy 30% off instead of 25% and 2 extra rounds). Discounts live in `plant_cost()` (a build-time price signal like the policy lever), never in `_learning_curve_cost()`, so the retire refund can never be inflated; a test builds and retires 60 times per type with everything stacked and always loses money.
- **GC-11 peek forecast (Meteorology branch).** Weather station unlocks `Peek forecast` (20 funds, once per round): it reads the next round's disruption roll (hit, none or waived) and, with Weather Variability on, each renewable type's output factor from the same `weather` stream `advance_round()` will use (a test checks it against what the round then does, over several seeds). Long-range outlook adds the round after next's weather. `peeked_round` is saved; the result is recomputed on demand.
- **C-3 what-if analyzer.** `finish_run()` files three extra rows in the run record (`whatif`: grade, funds, clean score) by replaying the same seed, scenario, toggles, perks and loadout on a fresh `GridState` under three simple bots: All-renewable early (builds the cheapest renewable per unit of capacity, retires fossil once the rest covers demand), Never retire, grow with fossil (cheapest coal or gas), Storage first (a battery first, charge/discharge by surplus, then renewables). They are demonstrations, not optimal play; capped at 100 rounds. Shown in the Career panel's "What if?" section with a one-line verdict. Records also keep `seed` and `ironman`.
- **GC-15 Perfect Round combo.** A round with no disruption (a waived one counts), no aging breakdown and demand fully met extends `perfect_streak`; each streak step adds 5% (max 6 steps) to the next round's base revenue, shown as "Perfect Round streak" with a flame glyph and the percentage in words, and in the round recap. `best_perfect_streak` is kept.
- **GC-21 undo and Ironman.** `undo_last_build()` refunds the exact cost and restores the unit age, learning-curve count, renewable flag and the shadow-grid log, but only while the build is still the last thing done this round (a retire, maintenance, demand response, peek, accepted grant or round advance closes the window). The opt-in Ironman toggle (Run setup) disables it, can only change before the run starts, shows "| Ironman" in the difficulty header and is filed in the run history.
- **GC-4 nicknames and eulogy.** Each standing unit has a nickname from a per-type pool, drawn from the run seed (reproducible) and kept in step with the count (`plant_name_list()`: extras from damage or breakdowns drop from the newest end). Retiring the last coal plant shows a eulogy line in the plant board (and a CSS smoke puff, replayed from a 30 ms timer, off under reduced motion). No effect on the maths.
- **GC-25 surprise grants.** From round 3 each round has a 15% chance (seeded `grant` stream, not while a policy offer is open) of a two-button offer: Clean-energy grant (+120 funds, fossil builds cost 25% more for 3 rounds), Industrial sponsor (+90 funds, demand +6), Safety inspection (pay 70 and cut every fleet's wear by 3, or contest it free and double the aging breakdown chance for 2 rounds). An unanswered offer lapses as declined when the round advances; auto-advance stops at an offer and will not start while one is open.
- **C-4 and C-26.** Hover or focus a plant-mix bar: the row highlights and `#mix-hover-readout` states its share of capacity, of revenue (output is capped by demand, every unit earns the same) and of emissions. `load_state()` now records which saved fields were missing (`compute_load_report()`), and the What's New panel opens with "Last save loaded: repaired N missing fields ..." (or "nothing had to be repaired").
- **Desktop.** New side-column items: Undo last build, grant banner and message, Peek forecast, Perfect Round streak; the run setup lives in the Difficulty window (renamed "Difficulty and run setup"); `pc.html` regenerated. `pc.css` keeps nicknames on their own line and the eulogy visible inside the board.
- **New save keys.** `get_state()` gained `seed`, `start_option`, `immunity_available`, `immunity_used`, `peeked_round`, `perfect_streak`, `best_perfect_streak`, `ironman`, `plant_names`, `name_serial`, `last_eulogy`, `grant_offer`, `grant_effects`, `last_grant_message` (each validated with a safe default on load); `last_round_recap` gained `perfect_bonus`, `perfect`, `immunity`; the career block gained `loadout`, and each history record gained `seed`, `ironman`, `whatif`. localStorage: `grid_career_v1` is unchanged in name. Old saves and careers load unchanged.

## Practice sandbox (Z-18, 2026-10-11)

An opt-in "Practice sandbox" (toolbar button `#sandbox-toggle-button`, Desktop: Menu > Game) on the shared `shared/sandbox-mode.js` and `shared/sandbox-mode.css` (button, "Sandbox: nothing here is saved" banner, dashed window frame, announcements; no game logic). The shared script calls `sandbox_enter()`, `sandbox_leave()` and `sandbox_is_active()` in `game.py`.

- **Rules.** `SandboxGridState(GridState)`: funds never drop below `SANDBOX_FUNDS` (1,000,000; the display reads "Funds: unlimited (sandbox)"), `disruption_probability()`, `aging_breakdown_probability()` and `breakdown_risk_probability()` are 0, no grants or fines, the emergency scenario can be stabilized but never missed (its clock does not run). All 14 upgrade-tree nodes are on (`SANDBOX_ALL_PERKS`: loadouts, peek forecast, cheaper builds and upkeep). The scenario button works at any time and starts the practice grid over. The policy lever keeps its normal schedule.
- **The real game is never edited.** `sandbox_enter()` takes `get_state()` as a snapshot and sets the real `GridState` object, the career object and the other module state a save reads (`info_page_open`, shadow twin, real-grid compare, run-setup messages, callout flags) aside in `_sandbox_real`, then points `state` at a fresh sandbox grid. `sandbox_leave()` puts the very same objects back, so `get_state()` is byte-identical.
- **Saves.** While the sandbox is on, `get_state()` returns a copy of the real snapshot, so Save, the autosave and anything else reading it get the real game. `load_state()` leaves the sandbox first and then calls `NoyvjSandbox.sync()`.
- **No side effects.** `achievement_ids_earned()` returns the real list as it was (no new achievements, toasts or story chapters), `finish_run()`, `unlock_career_perk()`, career import and reset are refused, `save_career_to_storage()` writes nothing, the comparison request is skipped and Copy result is labelled "Grid (practice sandbox)". Nothing is stored: reloading the page leaves the sandbox.
- Tests: `tests/test_sandbox.py` (24) and `shared/tests/test_sandbox_mode_browser.py`. Verified live at 1440x900 and 360x740 on `index.html` and `pc.html` (enter, play, a save equals the real game, leave).

## Screen-reader announcements (B-7, 2026-10-11)

Grid now speaks through the shared announcer (`shared/announcer.js`, `<script>` placed before `last-played.js` in `index.html`; `pc.html` regenerated). `game.py` keeps `_shared_announce(text)` (shared announcer when the page has it, otherwise the game's own `#sr-announcer` live region, never both, exactly Tide's pattern) and `announce(text)`.

- **What is announced** (player actions and round results only, never from `render()`): a build (plant, nickname, count, funds) or why it was refused; a retire (refund, funds) or "none standing"; a maintain (new wear %, funds) or why not; every Advance Round via `round_announcement_text()` (the recap line from `round_recap_text()`, "Now round N", any disruption via `event_message()`, any aging breakdown, a Perfect Round, demand against capacity, renewable and fossil shares, funds, a policy lever or grant now on offer, and the one-time 50% renewable milestone); Auto-advance (its summary line, then the last round's announcement, or why it would not start); demand response (new level and growth, or why not); policy lever enact/decline; grant accept/decline (`last_grant_message`); Undo last build; and an achievement unlock (no trophy emoji).
- **No double reading.** `#auto-advance-status` and `#grant-message-display` lost their `role="status"` because the announcer now says what they show.
- **Keyboard.** Grid has no tile map: its controls are the Build/Retire/Maintain buttons and Auto-maintain selects in each plant row, all native and reached with Tab (Enter/Space activate). So no arrow-key cursor was added (that is for tile grids like Canopy). Each `.plant-row` is now `role="group" aria-labelledby="<plant>-name"` so a button reads with its plant, and `style.css` gives plant-row controls, Advance Round, Auto-advance, Demand Response and Undo a thick yellow `:focus-visible` ring.
- Tests: `tests/test_shared_announcer.py` (21).

## Round-7 pass (2026-10-11) — display choices, coach, skyline and more

Built from `planning/TODO.md` "GC + C. Grid" (tests: `tests/test_round7_*.py`). One shared idea: a small **display-preference store**, `prefs` in `game.py` (`PREF_DEFAULTS`, `validate_prefs`, `set_pref`, localStorage key `grid_prefs_v1`). Like the text-size and reduced-motion settings it is a browser preference and is never part of `get_state()`, so loading a save cannot change how the page looks and old saves load unchanged.

- **C-12 trend-line checkboxes.** `#trend-controls` (a fieldset of checkboxes, each with a swatch that repeats the line's colour AND dash pattern) switches Emissions, Renewable cost, Global benchmark, and three new lines, Funds, Demand and Clean share, on or off. Defaults are the original three lines, so the graph and its message are unchanged until the player ticks something. `trend_graph_svg()` keeps its old call shape (new keyword arguments `visible`, `funds_history`, `demand_history`, `ghost`); a series of the wrong length (the funds of an old save) is skipped, not a crash. The best-round diamond sits on the first visible line (emissions, clean share, cost, funds, demand, benchmark) and at mid-height if every line is off.
- **GC-9 ghost run.** `ghost_record()` picks the career's best finished run (highest score, the latest on a tie) with a usable series; `ghost_value()` reads its thinned clean-share and funds series at any round (a run longer than 30 rounds was thinned evenly, so the read is spread; None once the ghost's run has ended). With "Ghost run" ticked the graph draws faint fine-dashed ghost lines under Clean share and Funds (when those are on) and `#trend-ghost-note` states in words how many points or funds ahead or behind the ghost the run is at the latest round. Nothing is stored beyond the career history that already exists.
- **C-19 table view.** "Show charts as tables" swaps the trend graph for a plain table (last 15 rounds, a column per visible line, ghost columns, "(best round)" in words) plus a one-line description (`trend_description()`), turns the plant-mix bars into `#mix-table` and adds `#gauge-table` (emissions meter, clean-grid score, disruption risk, fossil share, supply against demand). The Career panel's run-history list is already a text table, so it was left as is.
- Desktop: `#trend-controls`, `#trend-ghost-note` and `#gauge-table` sit in the side column next to the graph; `pc.html` regenerated.
- **C-14 fleet overview.** `<details id="fleet-overview">` inside the Plant Mix section (so it is on the Desktop stage with no config change): a table, one row per plant type (units, wear with its tier glyph, breakdown risk, next auto-maintain, revenue per round). `fleet_rows()` only reads existing numbers (`wear_percent`, `breakdown_risk_probability`, `maintenance_schedule`, the same revenue share the plant-mix hover uses; the battery earns "-" because storage is not generation). `rounds_until_scheduled_maintenance()` mirrors `_run_scheduled_maintenance()` (a test plays rounds and checks they agree). Column headings are real buttons (`#fleet-sort-<key>`): a new column sorts high to low (names A to Z), pressing it again reverses, the arrow and the button title say which way. The sort lives in `fleet_sort_key` / `fleet_sort_reverse`, a this-session view choice, never saved.
- **C-20 sticky key-stats bar.** The `MobileHud.init` list in `index.html` is now Round, Funds, Demand, Capacity, Emissions (the shared bar already scrolls sideways when full). `tests/test_round7_hud.py` pins the list on both pages and that every source id exists. The Desktop page has no phone bar of its own (the readout chips already show all of them).
- **C-21 coach.** Settings checkbox `#pref-coach` (off by default) shows `<details id="coach-panel">` with `#coach-text`, from `coach_observation()`: first match wins, most urgent first (no generation; capacity short of demand, with how many of the cheapest type close the gap; a fleet whose breakdown chance is 15% or more, with the maintenance price; a disruption chance of 20% or more and its main source; demand that will outgrow capacity next round; idle funds against a renewable that keeps getting cheaper; weather variability with renewables and no battery; an open policy lever; otherwise "Nothing urgent"). It only reads numbers the page already shows, never edits state (a test compares `get_state()` before and after) and never blocks. Settings > Reset to Default now also resets every display preference (`reset_prefs()`, the page's own `settings.js` still resets text size and motion). Desktop: `#coach-panel` is in the side column above the round recap.
- **C-22 / FY-24 confirmations.** The owner's answer (FY-24) is that retiring asks only for the LAST unit of a type, which is how it already worked (a test pins it), so the "skip under 20% wear" part of C-22 was not built: it would have meant skipping the last-unit warning, which has to stay. What was built is the missing control: Settings > Confirmations (`#confirm-reset-status`, `#confirm-reset-button`) lists which of Grid's skippable questions (`SKIPPABLE_CONFIRMATIONS`: finish run and the seven last-unit retires) carry a "don't ask again" flag (read from the `confirm-dialog:skip:<id>` keys that `shared/confirm-dialog.js` writes) and "Ask me again" removes exactly those keys (Grid's own, never another game's). The career import and reset questions use `allowSkip: false`, so they are never listed.
- **C-6 numbers and units.** Settings selects `#pref-number-format` (full / compact) and `#pref-unit` (plain units / labelled MW). `format_amount()` gives whole numbers or 1.2k / 3M / 3.5B from 1,000 up; `format_demand()` leaves demand and capacity exactly as before in full mode (the raw number, so existing displays and tests are unchanged) and compacts them otherwise; `unit_suffix()` appends " MW" to the Demand and Capacity lines only (a label, no rule change). `#funds-delta-display` (Desktop: side column) says what the last round did to funds in words with an arrow (up, down, unchanged; the colour only backs the words), from `last_round_recap["net"]`; it is empty before round one and in the sandbox.
- **GC-8 skyline strip.** `<div id="skyline-strip">` (Settings checkbox `#pref-skyline`, on by default) draws `SKYLINE_BUILDINGS` (16 fixed building shapes) from `skyline_status()`: buildings lit left to right = round(16 x capacity/demand) (0 with no generation, all 16 once demand is covered), haze = the emissions meter fraction (overlay opacity up to `SKYLINE_MAX_HAZE`), brownout = the last round's event was a brownout or damage. Lit buildings carry windows, dark ones are bare outlines (shape, not only colour); a brownout dims the windows (`sky-window--dim`, kept under reduced motion) and adds a three-step flicker animation that is switched off by `prefers-reduced-motion` and the Settings reduce-motion flag. `#skyline-caption` repeats it in words and the SVG has the same text as `aria-label`. Pure display, nothing saved. Desktop: in the stage under the transmission-line strip (40px high, beside its caption; under 780px tall only the caption stays).
- **GC-19 Gridley.** `#gridley-line` (Settings checkbox `#pref-gridley`, on by default) shows "Gridley: <line>" from `GRIDLEY_LINES` (8 categories x 3 lines: welcome, brownout, damage, aging, perfect, short, clean, quiet), chosen by `gridley_category()` from the last round (event, aging breakdown, Perfect Round, capacity against demand, renewable share) and then by the run seed and round through a stateless stream (`state.stream("gridley", rounds_played)`), so a replayed run hears the same lines. The voice is dry and plain: no numbers, no emoji, never advice (a test pins this). It is deliberately not announced to screen readers (the round announcement already says what happened). Pure display, never saved. Desktop: the side column above the funds delta.
- **C-18 achievement readouts.** `ACHIEVEMENT_PROGRESS` now covers 14 of the 17 achievements (the three one-step builds, First Watt, Renewable Pioneer and Stored Power, stay plain on purpose): Zero Fossil (clean share out of 100), Learning Curve Paid Off (percent of the way to the price floor, read from the learning-curve price so a policy discount never shows), Fossil Phase-Out (three fossil builds first, then units retired out of units built), Reach Round 21 undamaged (rounds, and no readout once a plant was damaged), Ahead of the Curve (rounds up to 11, none afterwards because the rest is a comparison, not a count). A readout may return None. `next_milestone()` picks the locked achievement with the largest fraction done (it needs some progress) and the Achievements panel opens with "Next milestone: <name> (x of y)".
- **C-24 print view.** `#summary-panel` carries the shared `print-summary` class and `index.html` links `shared/print-summary.css` with `media="print"` (a new file this page fetches; already used by Aftermath and Herd), so printing shows only the Run Summary in plain dark-on-white. `summary_panel_html()` gained a scenario / difficulty / seed line first and a career line last (points earned, finished runs, and what finishing this run would bank); the grade and resilience lines were already there. A small inline script puts a "Print or save as PDF" button (`window.print()`) into the panel whenever the panel is rebuilt; the print stylesheet hides it on paper. Tests: `tests/test_round7_print.py`.
- **GC-28 needle gauge.** `#needle-gauge` (side column, above the disruption-risk line) is a persistent half-dial SVG for capacity against demand (0 to 1.5 times demand). `gauge_reading()` gives the ratio, the needle angle (-90 to +90), the zone (short under 1.0, matched 1.0 to 1.15, spare above) and whether the last round was a brownout or damage (then the ratio is cut by severity x `MAX_REVENUE_LOSS_FRACTION`, so the needle drops into the short zone and the caption says a disruption cut delivery). The needle is a CSS transition with an overshoot curve on a persistent element, so it animates between rounds; matched adds a one-off glow and a tick, a cut round a one-off shake. The Settings checkbox `#pref-gauge-effects` (pref `gauge_effects`) adds `needle-gauge--still`, which turns all of that off; reduce motion and `prefers-reduced-motion` do too. The three zones differ by dash style and word labels (SHORT, MATCHED, SPARE), the caption repeats the reading in words and is the SVG title. No sound (the click in the TODO text became the tick and glow; audio stays with the AU section).
- **C-17 operator ranks.** Experience = lifetime rounds in finished runs + 15 per grade point earned (`operator_experience()`, from `career["lifetime"]`, so old careers already have it); six ranks at 0, 40, 120, 260, 450 and 700 (`OPERATOR_RANKS`, Junior Dispatcher to Chief Engineer). The title shows under the game title (`#rank-display`, Desktop top bar); the Career panel says the rank, the experience and the gap to the next rank (`#career-rank-display`), and `#rank-theme-select` picks an accent colour (`RANK_THEMES`: default plus one more per rank above the first), applied as `data-rank-theme` to the title and the Career panel. A locked colour is refused with the rank that unlocks it; a stored choice the rank no longer covers falls back to default. Nothing in the rules reads the rank and nothing new is saved in the game or the career (the colour is the `rank_theme` display preference).
