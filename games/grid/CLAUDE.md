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
