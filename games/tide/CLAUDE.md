# Tide — Ocean Acidification & Sea-Level Rise Game

**Built following the shared conventions in `planning/archive/climate-quartet-plan.md`** (testing, feedback hook, hope-angle requirement, hub integration — moved there 2026-09-22 once all four quartet games shipped; was `climate-quartet-plan.md` at the games root while build order still mattered). This file is Tide-specific only. Built third of the four — the grid redraw was the most visually involved piece, built after Grid and Canopy's patterns were solid.

## Concept

You run a coastal settlement, balancing fishing/industry output against ocean health (an acidity meter) and a slowly rising sea-level line. The core teaching challenge here is **delayed consequence** — the damage from today's choices shows up late, which is exactly why acidification is hard for people to intuitively grasp in real life. The game should make that lag itself the lesson, not smooth it over for playability's sake.

## Climate issue & hope angle

**Issue:** ocean acidification and sea-level rise, and specifically the *delay* between cause and effect.
**Hope angle:** investment in adaptation infrastructure (seawalls, wetland restoration) should visibly slow the rate of sea-level encroachment and buy real time — not stop it outright (that would undercut the delayed-consequence lesson), but demonstrably change the trajectory. A player who invests early should see a flatter curve later, proving that acting now — even without immediate payoff — matters.

## Core loop

- Turn-based, seasonal cycles (simplest to implement and matches a settlement-management feel).
- Player allocates resources between: industry/fishing output (immediate income), acidity-reducing measures, and adaptation infrastructure (seawalls, wetland buffers).
- Acidity meter rises with industry output, falls (slowly) with dedicated reduction spending.
- Sea level rises on a slow background timeline, independent of player action *except* that adaptation infrastructure reduces its effective impact rate (not the rise itself — sea level keeps rising in the world, but well-adapted settlements are less damaged by it).
- **Grid redraw for sea-level rise:** implement this as a simplified tile-based coastline (a grid, not detailed art) where rows/tiles flip from "land" to "flooded" as the sea-level value crosses thresholds. This keeps the visual payoff (players can *see* the coastline shrink) without requiring real art assets — it's state-driven tile rendering, same pattern as Canopy's plot grid, just reading from a different variable.
- Fish stock (tied to acidity) acts as a slow-building consequence: high acidity eventually crashes the fishing yield, which is the player's own economy quietly punishing over-extraction — mirrors Canopy's "your own resource base collapses" lesson but on a longer delay.

## Milestones

| # | Milestone | Content | Status |
|---|-----------|---------|--------|
| 1 | Core settlement loop | Resource allocation between output/reduction/adaptation, seasonal round progression. Tests: allocation logic, seasonal tick | Done |
| 2 | Acidity meter + delayed fish-stock consequence | Acidity rises/falls per allocation; fish yield degrades on a lag tied to accumulated acidity, not instant response. Tests: acidity calculation, lagged consequence formula | Done |
| 3 | Sea-level timeline + adaptation dampening | Background sea-level rise; adaptation infrastructure reduces effective damage rate. Tests: sea-level progression, damage-rate-reduction calculation | Done |
| 4 | Tile-grid coastline rendering | Simplified grid where tiles flip state as sea-level crosses thresholds. Tests (state layer only, not rendering): tile-state-flip thresholds | Done — pure Pyodide, no JS/Canvas fallback needed |
| 5 | Hope-angle payoff | Clear before/after comparison showing early adaptation investment flattening the damage curve. Tests: comparison calculation across sample play logs | Done |
| 6 | In-game feedback prompt | Piped to Neon backend per root conventions | Done |
| 7 | Visual/UI pass + hub integration | | Done — all 7 milestones complete |
| 8 | PC version: a Desktop boot (`pc.html`, generated from `index.html`) with a full-window dashboard layout, windows for the long sections, a Desktop tutorial and the layout switch on the opening screen | Done (2026-10-06; see `planning/PC-VERSION-PLAN.md`) |

## Iteration Notes — Pass 1 (implemented)

Design-review pass (pre-playtest, from `climate-games-iteration-pass.md`). Anticipated issue: delayed consequence (the whole point of the game) risked reading as random or confusing rather than caused, if the fish-stock crash arrived with no visible link back to earlier acidity choices; the two meters (acidity, sea level) also risked blurring together visually.

**Built in response (see `BCM114-DEV-LOG.md` 2026-08-11):** a delayed-effect ticker log narrating consequences as they build, and a visually separate sea-level meter (distinct color/position from the acidity meter).

**Open testing question:** the feedback prompt asks directly whether players understood *why* their fish stock declined — the clearest test of whether delayed consequence taught anything or just felt arbitrary.

## Iteration Notes — Pass 2 (implemented)

Second design-review pass, from `climate-games-iteration-pass-2.md`, building on Pass 1. **Selected addition: A (adaptation tech tree).**

- **Adaptation tech tree:** seawalls and other adaptation infrastructure upgrade through tiers over the course of a session (within-run, not between sessions like Aftermath's meta-progression), with each tier requiring sustained investment and unlocking a visibly stronger dampening effect on sea-level damage. Gives adaptation spending a clearer sense of escalating payoff rather than a flat, same-effect-every-time investment.
- **Visual polish for this pass:** each tech tier should have a distinct visual signature on the coastline tiles (e.g. a visible seawall line appearing/thickening on the tile-grid as tiers unlock), so upgrading isn't just a stat change — it's something the player can see standing between their settlement and the rising water.

## Iteration Notes — Pass 3 (Fun/Teaching Balance, implemented)

Fun/teaching-balance pass, from `climate-games-fun-teaching-balance.md`. **Risk:** Tide is the game most exposed to the "fuelling fear rather than building trust" failure mode identified in the Klim:S21 study — the delayed fish-stock crash can read as arbitrary or unfair if the player can't trace it back to their own choices, risking anxiety without efficacy.

Audited the existing ticker (Pass 1) and adaptation tech tree (Pass 2) against that risk: the ticker already narrated fish-stock recovery as well as decline, but the sea-level/damage side of the game — the part adaptation spending actually acts on — had no recovery narration at all, only a silently-updating static comparison. Tier unlocks changed the on-screen tier label immediately, but with no flagged moment calling out that anything had just improved.

**Built in response:**
- A ticker message fires the moment an adaptation tier unlocks (at the point of investment, not on the next season), naming the new tier and its dampening percentage — the concrete "trust" test from the study: the player sees, immediately and in the log they're already reading, that their spending just did something.
- A one-time ticker message fires the first season the damage curve visibly flattens (comparing first-half vs. second-half average damage-per-season, the same comparison already driving the static damage-trend display), giving the adaptation payoff its own recovery narration alongside the existing fish-stock one — feedback in both directions, not just decline.

No new mechanics were added; both hook into ticker infrastructure and comparisons that already existed from Pass 1/2.

## Info Page — real-world sources (implemented)

*Implementation is now shared across all 8 climate-quartet games — see `shared/info_page.py` and `shared/info-page.css`. Only the content below (framing/tie-in/sources) is game-specific; the rendering/toggle code moved out of this game's `game.py`.*

An optional, player-triggered "The Real Story" panel — never forced mid-session, since the mechanic teaches first and this is a supplement for players who want to go deeper. Toggled via a button near the top of the page; shows a short framing paragraph (written fresh, not copied from any source), a one-line note tying the mechanic to real data, and a sources list with clickable links.

**Framing:** Ocean acidification and sea-level rise are two separate consequences of the same underlying cause — the ocean absorbing extra CO2 and extra heat — and both show up on a delay: today's emissions determine damage that doesn't fully land for years. Tide's delayed-effect ticker and background sea-level timeline are built around that real lag.

**Mechanic tie-in:** The fish-stock crash mechanic mirrors the real acidification pathway — more absorbed CO2 makes water more acidic, which is measurably harmful to shellfish and reef-building organisms first.

**Sources:**
1. [NOAA Fisheries — Understanding Ocean Acidification](https://www.fisheries.noaa.gov/insight/understanding-ocean-acidification) — the real process behind Tide's fish-stock crash.
2. [NASA Sea Level Change Portal — Global Mean Sea Level](https://sealevel.nasa.gov/understanding-sea-level/key-indicators/global-mean-sea-level/) — real satellite-measured sea-level data, informing the pacing of Tide's background timeline.
3. [NOAA Climate.gov — Climate Change: Global Sea Level](https://www.climate.gov/news-features/understanding-climate/climate-change-global-sea-level) — explains both causes of sea-level rise (thermal expansion + ice melt) in plain language.
4. [Smithsonian Ocean Portal — Ocean Acidification](https://ocean.si.edu/ocean-life/invertebrates/ocean-acidification) — the most accessible explanation of the acidification chemistry.

All four links verified live before merging. Source 4 (Smithsonian) returns 403 to automated fetchers (bot-protection) but is a legitimate, well-known institutional domain.

## Post-launch improvement pass (`planning/TODO.md` D1-D19, implemented)

D10/D20 stayed parked in `planning/LATER.md` per that doc — everything else in the range landed in one pass:

- **D1 (mobile dock):** wraps the investments panel + Advance Season button in a new `#actions-dock` div, docked to the bottom of the viewport on mobile via `shared/mobile-dock.js` — same pattern as Aftermath's `#actions-dock`.
- **D2 (fourth adaptation tier):** Storm-surge barriers, threshold 15, 95% dampening — `MAX_DAMPENING` (0.9) now describes the third tier only, not the ceiling of the whole list.
- **D3 (next-flood estimate):** `next_flood_estimate()` — seasons remaining (rounded up) until the next currently-unflooded row crosses its threshold, reading bottom-up since that's flood order.
- **D4 (then-vs-now stat block):** `then_vs_now_text()` — a numeric companion to the existing visual coastline-comparison grids.
- **D5 (expandable ticker history):** `ticker_full_history`, capped at 200 entries, behind a `<details>` disclosure alongside (not instead of) the short live ticker.
- **D6 (counterfactual replay):** `counterfactual_message()` — holds the *current* adaptation tier's dampening fixed across every season already played and compares the resulting hypothetical damage to what actually happened, making "invest early" concrete.
- **D7 (end-of-session summary):** `session_summary_text()`, an on-demand panel — same never-forced pattern as the info page/achievements panels.
- **D8 (newly-flooded-row flash):** a one-shot `.coastline-flash` class on any row flooding for the first time this render, tracked via a module-level `_previous_flooded_rows` snapshot (reset on both a fresh game and a loaded save, so neither spuriously flashes every already-flooded row).
- **D9 (harder-lag difficulty mode):** `hard_lag_mode` toggle — 6-season lag instead of the default 3, safe to flip mid-session since it only changes which index `_effective_fish_lag()` reads.
- **D11 (colorblind-safe coastline):** audited, not re-colored — see the dedicated note below.
- **D12 (worst-season callout):** `worst_season()` — the single highest-damage season played so far.
- **D13 (best-coastline-saved record):** a per-browser personal best via `localStorage`, deliberately outside `get_state()`/the save-code system, same distinction Canopy's B14/Thaw's G19 draw.
- **D14 (fish-yield-crash early warning):** `next_season_fish_yield_preview()` computes what next season's yield will be from acidity already banked in `acidity_history` (the lag means this is always knowable one season ahead); `#fish-warning-banner` fires *before* the drop lands, distinct from the ticker's after-the-fact narration.
- **D15 (acidity/fish-yield mini-graph):** `acidity_fish_history_svg()` — same inline-SVG-string technique as Canopy's own session sparkline, charting both series on one shared 0..1 scale.
- **D16 (Output fishing/industry sub-choice):** `output_mix` (fishing/mixed/industry) — "fishing" reproduces the original single-formula behavior byte-for-byte, so every pre-existing save/behavior keeps working unless the player actively picks a different mix.
- **D17 (one-time first-flood callout):** `_record_first_flood_message()` — fires once, the first season any coastline row actually floods.
- **D18 (comparison-baseline checkpoint):** `set_comparison_baseline()` re-anchors the then-vs-now comparison to right now instead of the literal Season 1 start.
- **D19 (per-tile flood-threshold tooltip):** a plain `tile.title` attribute on each coastline tile, naming its flood threshold — zero extra markup, works for both mouse hover and (on most mobile browsers) long-press.

Full pytest suite (163 tests) green after the pass.

### D11 worked note — colorblind-safety audit

Audited as part of the site-wide colorblind-safety audit (Okabe-Ito-palette method, per Continuum's Phase 5 and Canopy's B9). Tide's only discrete two-state color-coded pair is the coastline grid's `.coastline-land` (green) vs. `.coastline-flooded` (blue) — everything else (meters, ticker text, achievement cards) is already redundantly coded (icons, text, or a single-hue bar rather than a paired good/bad color).

Unlike Continuum's actual violation (a hue-only green/red pair — exactly the deuteranopia/protanopia confusion), green vs. blue is not that confusion pair, and the two states were already redundantly coded before this pass even started: `.coastline-land` carries a dot-pattern texture and `.coastline-flooded` a diagonal-stripe texture (from the earlier "Full visual pass" — see Tech notes below), independent of hue. D19's new per-tile `title` tooltip adds a third, fully non-visual cue — it states "Flooded" or "Floods once sea level reaches N" in plain text — so the distinction no longer depends on color perception at all, regardless of colorblindness type (including tritanopia, the one form where blue/green can genuinely get closer). No CSS re-color was applied; `.coastline-land`/`.coastline-flooded`'s hex values are the same ones the Sep 2026 visual pass explicitly protected as load-bearing state color.

## Achievements (implemented)

20 achievements added per the hub-wide framework (`planning/ACHIEVEMENTS-SYSTEM-DESIGN.md`), following SOL's reference integration: `achievements.json` catalog, `game.py`'s `ACHIEVEMENT_CHECKS`/`ACHIEVEMENT_PROGRESS`/`achievement_ids_earned()`/`achievements_summary()`, an in-game toggle + panel, an unlock toast, a hub-dashboard link, and `achievements_earned` riding `get_state()` (never read back on load). Span first-investment-per-category milestones, all four adaptation tiers (including D2's new Storm-surge barriers), coastline flood-progression thresholds (first flood / half the rows / the whole grid), the delayed fish-stock crash and its recovery, an acidity-drawdown-from-peak achievement, funds/damage-saved/longevity thresholds, the damage-curve-flattening moment, a well-rounded-investment achievement, and `fortified_in_time` (reaching the max adaptation tier before a single coastline tile floods) — the last needed a genuine new tracked flag (`fortified_in_time_earned`, set once inside `invest()`'s own tier-unlock branch) since it asks "was this true at a past moment," not recoverable from present-only state. Three other checks (`min_fish_yield_ever`, `max_acidity_ever`, `max_funds_ever`) needed new tracked state for the same "how far did this ever go" reason; every other check is a pure function of state that already existed. `tests/test_achievements.py` covers catalog sanity, every achievement through real game actions, panel/toast behavior, and save/load round-trip, following Canopy's test pattern.

## Tech notes

- Default Python/Pyodide; JS/Canvas is an explicitly pre-approved fallback for the tile-grid rendering step only (milestone 4) if needed — keep all state logic in Python either way, since that's what gets tested.
- Keep state and rendering cleanly separated from the start, given the likely rendering-approach decision at milestone 4.
- Site-wide space-theme visual pass (Sep 2026): adopted the shared starfield/nebula background (`shared/space-bg.css`) and the glass-panel/gradient-button design language already shipped on the hub and SOL — `<div class="space-bg">` markup added right after `<body>`, `.section` blocks (status, sea-level, coastline comparison, investments, feedback) restyled as translucent blurred glass cards with violet-tinted borders, `button.secondary`/`button.primary` moved from flat fills to two-stop gradients with a glossy inset highlight and a `brightness(1.1)` hover state, the three meter fills (acidity/fish-yield/sea-level) got a same-hue gradient + glow, and the `<h1>` got the shared gradient-glow text treatment. Deliberately left untouched: `.coastline-land`/`.coastline-flooded` (functional state colors on the coastline grid) and the `.coastline-seawall` line's own color (only added a same-hue glow around it) — tier/damage-state identity must stay readable exactly as before. No `game.py` changes; no CSS class/id renamed. This game has no "no animation" test constraint (checked `tests/` and this file for one, unlike some other quartet games), so the existing `transition: filter`/`width` rules were kept and extended, matching SOL's pattern — the shared `space-bg.css` animations are unaffected either way. `tests/` stayed at 120/120 passing throughout.

## Settings panel (site-wide goal, planning/TODO.md, origin A9)

A consolidated settings panel — text-scale (A−/A/A+ buttons, same clamp/step
shape as Continuum's Phase 5 `accessibility.js`) and a reduced-motion
checkbox — toggled from a new "⚙️ Settings" button in the second toolbar
row (alongside the Hard Lag difficulty toggle), rendered into a
`.section`-styled panel matching the existing `#howto-panel`/
`#achievements-panel` hidden-until-opened idiom.

Built as `settings.js`, deliberately independent of Pyodide entirely (same
discipline as Continuum's `accessibility.js`) — it has no Python dependency
and works even if `game.py` never boots, wired up in `<head>` before
`game.py`'s own `<script>` runs. `style.css` gained a `:root
{ --text-scale: 1 }` custom property read by `html { font-size: calc(16px *
var(--text-scale, 1)) }` (every readable font-size in this file is already
in rem, confirmed by grep — the one exception, `.fish-school`'s decorative
10px label, was deliberately left alone — so scaling the root font-size
scales the whole game uniformly with zero other changes needed) and a
blanket `html[data-reduced-motion="true"] *` override collapsing every
animation/transition to effectively instant — additive to, not replacing,
this game's own existing `prefers-reduced-motion` media-query-gated rules
(`tide-scene-sway`, `tide-scene-fish-swim`, `meter-shimmer`,
`meter-bubbles`, `meter-foam-drift`).

**Deliberately no sound toggle** — this hub has no audio system built
anywhere yet (see `planning/LATER.md`'s "what can you actually do with
audio" standing question), so a sound control here would control nothing
real.

Both settings are a browser-level UI preference, not game state — persisted
to `localStorage` (`tide-text-scale`, `tide-reduced-motion`), deliberately
never touching `get_state()`/`load_state()`, since a save code is meant to
be portable across devices/browsers and a local browser's accessibility
preference shouldn't silently override another device's.

Verified live: 163/163 pytest suite unaffected (pure HTML/CSS/JS, no Python
touched); in a real browser, applying a 1.3 text-scale correctly computed
`<html>`'s font-size to 20.8px, and enabling reduced-motion collapsed the
`.tide-scene`/wave elements' live `animation-duration` to ~1e-6s, both
persisting to their localStorage keys. The only console errors present
were the pre-existing, unrelated AdSense placeholder-client CSP
frame-ancestors warning and its associated load failure, reproducible on
the unmodified page (same as Grid's own build note). Verification required
cache-busting the stylesheet `<link>` directly (a fresh `?v=` query on its
`href`) to sidestep this sandbox's own known static-asset HTTP-caching
quirk — not a defect in the shipped code, the same environment hazard
Continuum's, SOL's, Canopy's, and Grid's own build notes already document.


## Reset-to-default settings button (Z-extra/A26, site-wide goal)

A "Reset to Default" button (`#settings-reset-button`) sits at the bottom of the settings panel, below the existing text-size and reduce-motion controls -- SOL's own A26 answer flagged this as a site-wide pattern rather than a SOL-only feature, folded into `planning/TODO.md`'s Z-extra checklist. Implemented entirely in `settings.js` (no Python touched, matching this file's own "deliberately independent of Pyodide" rule for the rest of the settings panel): one click calls `applyScale(DEFAULT_SCALE)` and `applyMotion(false)`, updates `--text-scale`/`data-text-scale`/`data-reduced-motion` on the live DOM immediately, resets the reduce-motion checkbox's own `checked` state to match, and writes both defaults back to `localStorage` so the reset survives a reload rather than only looking reset until the next render. No confirmation dialog -- this is a low-stakes, instantly-reversible display preference, not a destructive action, so `shared/confirm-dialog.js` is deliberately not wired up here.

## Onboarding-tooltip coverage check (site-wide goal, planning/TODO.md, origin A14)

Audited whether a returning player who's forgotten the tutorial can still
make sense of the permanent UI's non-obvious parts, on top of the
persistent, reachable-any-time `#howto-toggle-button`/`#howto-panel`. Most
of the permanent UI already covers itself well here: D19's per-tile
coastline tooltips (this game's own reference pattern for the site-wide
goal) and four section-level `.info-toggle` icons permanently explain the
delayed-acidity-to-fish-yield lag, the sea-level-vs-damage distinction,
and the adaptation-tier threshold mechanic.

**Real gap found:** D16's `output-mix-select` dropdown (Fishing/Mixed/
Industry) changes a real, non-trivial trade-off -- `OUTPUT_MIX` in
`game.py` shows Industry drops fishing-tied income to zero (dodging the
delayed fish-stock crash entirely) but raises acidity 40% faster, with
Mixed splitting the difference (half fishing-tied, +15% acidity) -- and
none of that was stated anywhere permanent. The tutorial mentions
"Output (fishing/industry income)" exactly once, in passing, with no
trade-off numbers; there's no info-toggle nearby; and the three
`<option>`s just read "Fishing (default)" / "Mixed" / "Industry" with no
elaboration. A returning player switching this dropdown had no way to
know what it actually changes.

**Fixed:** added a `title` attribute (identical text) to both the
`<select id="output-mix-select">` and its wrapping `<label
class="output-mix-label">`, stating the acidity-rate/fish-crash-exposure
trade-off in plain language, and enriched the three `<option>` labels
themselves to show the numbers inline ("Mixed (+15% acidity, half
fishing-tied)", "Industry (+40% acidity, no fish-crash exposure)") so the
information is visible even without hovering. No `game.py` change needed
-- `OUTPUT_MIX`'s values and `set_output_mix()`'s validation were already
correct; this was purely a missing explanation in the markup.

Verified: full 163/163 pytest suite green (HTML-only change, no Python
touched, and no test hardcodes option text); live-verified in a real
browser (post cache-bust, this sandbox's known static-asset-caching quirk
per this file's own Settings-panel note) that both the select and label
carry the correct `title` text and the three option labels read as
written, with zero console errors.

## "What's New" changelog panel (site-wide goal, planning/TODO.md, origin K16)

A new `changelog.json` manifest (flat list of `{date, entry}` objects,
hand-authored newest-first, dates cross-checked against `git log --follow
-- games/tide/CLAUDE.md`/`git log -- games/tide/game.py` rather than
guessed) plus a "📋 What's New" toggle+panel, following the exact same
hidden-until-opened `.section` idiom and dynamic-DOM-build pattern
`#achievements-panel`/`#session-summary-panel` already established here —
a plain date+text card layout (like the session-summary panel) rather than
achievements' earned/unearned styling, since a changelog entry has no
checkable condition. Fetched into the Pyodide boot sequence alongside
`achievements.json` (`window.CHANGELOG_JSON`), with the same disk-read
fallback for the pytest harness's fake `js` module that `ACHIEVEMENTS`
already uses. Unlike Grid/SOL, `CHANGELOG` sorts its entries newest-first
defensively at load time rather than trusting the JSON's own order, purely
a stylistic choice — matches Aftermath's precedent for this same feature.
`render()` keeps an open panel live on every action, same as every sibling
panel. Also added `.changelog-panel[hidden] { display: none; }` in
`style.css` up front, since this panel uses `display: grid` and would
otherwise be exposed to the exact CSS-cascade-over-`[hidden]` bug SOL's own
achievements panel hit and had to patch after the fact.

Tests: 163 → 174 (new `tests/test_changelog.py`: catalog sanity, newest-
first sort, toggle open/close, panel content matches `CHANGELOG`, render-
time liveness, and a check that opening the panel never mutates
`SettlementState`). Verified live under Pyodide via the `hub-dev-server`
launch config: this sandbox's known static-asset HTTP-caching quirk
(documented in several other games' own build notes, including this file's
own Settings-panel note) hit the boot script's `fetch("game.py")` call
directly — a fresh page load kept resolving to a stale cached `game.py`
with no `CHANGELOG` in it at all, confirmed by inspecting the fetched text
length against the file on disk — so verification forced a fresh
(`cache: 'no-store'`, cache-busted query string) fetch of both
`changelog.json` and `game.py` and re-ran them through the already-loaded
`pyodide` instance. With the fresh code loaded: the panel opened, listed
all 10 real entries with correct dates/text in newest-first order, the
toggle label flipped to "Hide What's New", and it closed correctly on a
second click — zero console errors throughout.

## UI decluttering pass (2026-09-20, planning/TODO.md closing task)

Audit-first pass, same standard as the site-wide colorblind-safety audit: only change something if it's genuinely crowded, otherwise leave it. Read through `index.html` and `style.css` end to end. This game has had the most post-launch iteration of the quartet (the full D1-D19 pass, plus achievements, settings, changelog, session-summary), and most of it already declutters as a side effect: every panel-scale feature is hidden-until-opened (Tutorial/How to Play/Achievements/What's New/Session Summary/Settings), D5 already tucked the full ticker history behind a `.ticker-history-toggle` `<details>`, D19's per-tile tooltips replaced what could have been more on-screen UI, and D1's mobile dock keeps the investments panel from competing with the status cards on small screens.

**Real gap found:** `#sea-level-section` had accreted two derived "nice to know" stat lines one at a time as separate passes landed — D3's `#next-flood-display` (seasons until the next row floods) and D12's `#worst-season-display` (the worst single season so far) — each just appended as another always-visible `<p>` under the section's core sea-level/damage/adaptation-tier readouts, with no grouping consideration at the time either landed. Neither is something a player needs at a glance to decide this season's investment (unlike sea-level, cumulative damage, and the adaptation tier/progress lines directly above them, which are), so they were the one part of this section that had drifted toward "just more stacked text" rather than a deliberately-scoped display.

**Fixed:** wrapped both in a new block-level `<details class="sea-level-stats-toggle">` (`index.html`) with a plain "More stats" `<summary>`, collapsed by default, sitting after the core sea-level/damage/adaptation-tier lines so those stay immediately visible. Styled in `style.css` by copying this game's own `.ticker-history-toggle` rule shapes (0.78rem, opacity 0.65 summary) under a new class name (it's a different section, so reusing the "ticker" class name would have been misleading) — same look Grid's own decluttering pass in this session adopted for consistency. No `game.py` change — `render_sea_level_stats()`'s equivalent code (the block writing `next-flood-display`/`worst-season-display`'s `innerText` in `render()`) only does `document.getElementById(...)`, untouched by the new wrapping div.

Verified: full 174/174 pytest suite green (HTML/CSS-only change, no Python touched; `tests/conftest.py`'s `next-flood-display`/`worst-season-display` ids are read the same way regardless of DOM nesting). Everything else audited and left alone: the coastline grid, the then-vs-now comparison, and `#investments` are either the game's core visual payoff or already docked/grouped from prior passes — collapsing any of those further would hide information or controls a player actually needs mid-season, the over-collapsing failure mode this pass is meant to avoid.

## Round-2 pass (2026-09-20, planning/TODO.md D-list)

Built: D2 (worst-season cause via new `tier_log`), D6 (warning-banner suggested action), D10 (dashed average line on the acidity/fish graph), D14 (then-vs-now damage sparkline), D16 (hard-lag tooltip), D18 (baseline marker on the graph), D19 (`sea_scenario`: conservative 4 / moderate 5 / severe 6.5 per season, locked after season 1; `SEA_LEVEL_RISE_PER_SEASON` is now the moderate default and all rise maths goes through `sea_rise_per_season()`), D20 (tier badge in the investments row), D22 (live output-mix preview), D23 (recovery banner + ticker celebration, `fish_crash_open`/`recovery_celebrated_season`), D24 (seasons-survived counter), D26 (per-tile seasons-until-flood tooltip), D28 (per-tier seawall textures `coastline-seawall--tN`), D30 (one-time hard-lag ticker note, `hard_lag_note_seen`). All new state is in `get_state()`/`load_state()` with safe defaults for old saves. Tests 175 -> 195 (`tests/test_round2_pass.py`).

Not built in that pass: D9 (`/stats/games/tide` exposes no adaptation-tier field, still open) and the larger mechanics, built in the 2026-09-21 round-3 pass below.

## Decorative sea-level wave cue (planning/TODO.md D4)

A small standalone `#sea-level-wave-cue` strip sits directly under the
sea-level meter (`index.html`, right after `#sea-level-bar`) — a separate
element from the meter fill's own `meter-foam-drift` sweep (that one lives
inside `.meter-fill--sea-level::after` and always runs at a fixed 3.2s;
left untouched here rather than repurposed, since D4 asks for the cue's
speed itself to track the percentage, and folding that into an animation
that's already documented/tested elsewhere risked entangling two separate
concerns). Same "Python computes, CSS `@keyframes` just plays it" pattern
as this hub's other percentage-driven visuals: `render()` sets only the
strip's `animationDuration` inline style each call, from a new
`sea_level_wave_cue_duration()` helper that linearly maps
`sea_level_fraction()` (0..1) onto `SEA_LEVEL_WAVE_CUE_MAX_DURATION` (6s,
calm) down to `SEA_LEVEL_WAVE_CUE_MIN_DURATION` (1.5s, fastest at a full
meter) — the `@keyframes sea-level-wave-cue-drift` rule in `style.css`
never changes. Purely cosmetic: `render()` never reads the element back,
and `#sea-level-display`/`#sea-level-bar`'s own numeric text and width are
set on the lines immediately before it, untouched.

Confirmed before building: this game has no "no animation" constraint
(this file's own Tech notes already state that explicitly), and it already
has both a `prefers-reduced-motion` media-query convention and a
settings-driven `data-reduced-motion` attribute toggle (Settings panel
section above). The new `.sea-level-wave-cue::after` rule was added to the
existing `@media (prefers-reduced-motion: reduce)` block alongside the
other meter-fill animations, and is also covered for free by the blanket
`html[data-reduced-motion="true"] *` override, same as every other
animated element in this file.

Tests: 195 → 202 (new `tests/test_wave_cue.py`: element exists, duration
sits at the slow end at zero sea level and the fast end once the meter
caps out, duration strictly decreases across sample sea-level values, the
helper function's own boundary values, that the cue never changes
`#sea-level-display`'s text or `#sea-level-bar`'s width, and that
`render()` doesn't error if the element is missing). Full suite green,
flake8 clean.

Verified live via the `hub-dev-server` launch config: hit both of this
sandbox's known caching quirks this session's other build notes already
document (`game.py` boot-fetch and the `style.css` `<link>` both needed a
cache-busted re-fetch to pick up the new code) — with fresh code loaded,
`#sea-level-wave-cue` rendered at its styled 5px/412px box with the
correct `animation` shorthand, `animationDuration` read `"6.00s"` at
`sea_level = 0`, `"4.00s"` at 40, and `"1.50s"` once the meter capped out,
while `#sea-level-display`/`#sea-level-bar` kept updating normally
alongside it. Zero console errors beyond the pre-existing, unrelated
pageview-tracking 404 (the local dev server has no `/app` backend) this
file's other build notes already note as an environment artifact, not a
defect.

## Hidden-panel display bug fix (2026-09-21)

Found during a site-wide sweep after Aftermath's own Z12/panel-hiding
fixes surfaced the same pattern elsewhere: the achievements panel (`.achievements-panel`) set `display:
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

- Commit + tag per milestone: `git commit -m "Milestone N: <name>"` then `git tag tide-milestone-0N`.
- Update the milestone table Status as work happens.

- 2026-09-21: mobile-dock `body` padding-bottom now `html body` so it beats ad-bar.css (V-AB-2).

## Round-3 pass (2026-09-21, planning/TODO.md D-list)

Built (all in `game.py`, tests in `tests/test_round3_pass.py`, 202 -> 252):
- **D7** delayed-consequence timeline (collapsed `<details>` under the acidity graph; purple acidity vs. green dashed yield shifted right by the live lag).
- **D8** tide indicator: deterministic `tide_offset()` (sine of the season, no saved state); dry rows the tide reaches get a dashed edge plus tooltip note.
- **D29** settlement name (24-char cap, sanitised) and a capped chronicle of notable moments.
- **D17** coastal heritage: two sites (lighthouse row 5, oyster reef row 6) shown as emoji tiles; protect for a one-off cost plus 6/season upkeep, else lost when their row goes.
- **D21** citizen-science monitoring: paid report every 2 seasons at most, revealing 8 real-world findings in order.
- **D13** storm seasons: opt-in toggle, surge every 5 seasons, forecast ahead, cut by current dampening; the rest costs funds.
- **D1** managed retreat: up to 2 steps, each gives up the lowest dry row (hatched, drawn flooded) for a compounding 20% extra damage cut via `dampening_fraction()`. Deliberately not a fifth `ADAPTATION_TIERS` entry so tier indices/achievements are untouched.
- **D5 + D15** population: grows toward housing (dry rows x density by tier) while fish yield >= 50%; lost rows displace the excess (orderly retreat counts as "relocated"). Display only, no funds effect.
- **D11** diversification: tourism (fades with lost coast, boosted by protected heritage) and aquaculture (mild unlagged acidity penalty), 3 levels each.
- **D27** checkpoint replay: `set_checkpoint()` stores a compact snapshot (no nested checkpoint/foresight/full ticker); `replay_from_checkpoint()` rewinds and records the abandoned run's per-season yield/damage/flooding as "foresight".

All new state is in `get_state()`/`load_state()` with validation and safe defaults for old saves (`test_get_state_includes_every_expected_key` is now a superset check). Every new element lookup tolerates a missing node. Nothing new is hue-only (emoji, dashed/hatched patterns, text). Verified live (Pyodide, fresh `game.py` re-run to bypass the known boot-fetch cache): all buttons work, zero console errors. Achievements not extended for these mechanics.

Still open: D9 (needs a tier field in the stats backend).
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
right after the existing `ad-bar.css` link, and `#session-summary-panel`
(D7's own end-of-session recap, `#session-summary-text`) gained the
`print-summary` class alongside its existing `section
session-summary-panel` classes. Purely additive — `media="print"` means
these rules never apply on-screen, and no `game.py`/on-screen markup
changed.

**Verification method used:** this sandbox has no print-to-PDF affordance,
so per this task's own guidance, verification was done by confirming the
stylesheet loads with `media="print"` and that its selectors have real
targets in the live DOM, rather than a literal print render — the same
method used for Canopy's Z21 pass (see that game's CLAUDE.md for the
detailed DOM-selector checks run against a structurally similar panel).
`python3 -m pytest games/tide/tests -q` stayed at 252/252 (pure HTML
class/link addition, no Python touched).

## 320px mobile-viewport audit (Z18, site-wide goal, planning/TODO.md)

Checked at a genuine 320px viewport (narrower than the original 375px
mobile pass) via the Claude Browser tool's `resize_window`.

**Real bug found and fixed:** `#output-mix-select` (the D16 fishing/mixed/
industry dropdown) sits inside `.output-mix-label`, a `display: flex` row.
A `<select>` has no CSS width of its own here, so as a flex item it fell
back to flexbox's default `min-width: auto` — a floor equal to its content's
intrinsic width, which for a `<select>` is sized off its *longest* `<option>`
text ("Industry (+40% acidity, no fish-crash exposure)"). That intrinsic
width was wide enough to push the select past both the `#investments` card
and the viewport's right edge at 320px — 85px past the card, 69px past the
screen itself. The same "flex child needs `min-width: 0`" shape Loop's own
Z18 fix already documented, just on a `<select>` instead of a flex row.
Fixed by adding `min-width: 0` to `.output-mix-label select`, letting it
actually shrink to the space `.output-mix-label` has (`flex-shrink` was
already the flex default); confirmed live afterward at 200px wide, fully
inside the card, with the card's own `overflow-x: auto` no longer needed
(its `scrollWidth`/`clientWidth` now match exactly).

No other overflow found — the top `#mobile-hud-bar` strip's own
`overflow-x: auto` is the same deliberate scroll-not-clip idiom Canopy's
Z18 section documents. `flake8`/tests unaffected (pure CSS) — suite stayed
at 252/252.

## Difficulty-aware achievements audit (Z27, site-wide goal)

Tide has two difficulty-shaped toggles: D9's hard-lag mode (freely
reversible mid-session, only changes which index `_effective_fish_lag()`
reads) and D19's sea-level scenario (conservative/moderate/severe,
locked once season 1 has played).

**Hard-lag mode:** checked against `the_lag_arrives`/`stocks_rebound`
(the two achievements most obviously tied to the lag mechanic) — both
just need the fish-yield multiplier to eventually cross a threshold, which
a longer lag only delays, never blocks (acidity keeps accruing into
`acidity_history` regardless of which index reads it back out), and the
toggle is freely reversible besides. No change needed here.

**Sea-level scenario, and a real finding that turned out NOT to be
toggle-specific:** `fortified_in_time` ("reach the max adaptation tier
before a single coastline tile floods") looked like the obvious
severity-sensitive candidate — a faster sea-level rise leaves less safe
time to reach the 15-investment threshold before the first row (threshold
15) floods. Wrote a standalone simulation (game-module-level, not a
committed test) trying every reasonable organic strategy — pure
adaptation-rushing off the 300 starting funds, bootstrapping N units of
Output first then rushing adaptation, and a compounding-output strategy
growing Output capacity across several safe seasons before switching to
adaptation — against all three scenarios. Result: **the achievement never
got earned via organic play in ANY of the three scenarios, including
`moderate` (the un-toggled default)**. The economics are the reason:
reaching the max tier costs 15 x 30 = 450 funds in adaptation investment
alone, starting funds are only 300, and the only income source (Output)
means diverting some of that 300 away from adaptation to ever earn more —
the existing unit test for this achievement (`test_fortified_in_time_
needs_max_tier_before_any_flood`) only proves the condition *logic* is
correct, by injecting `funds = 10000` directly rather than earning it
through play.

Since this shows up identically whether the scenario is severe, moderate,
or conservative, it is **not a difficulty-toggle-differential issue** —
the achievement is equally (un)reachable regardless of which scenario a
player picks, so there's nothing for a hard-mode-specific fix to correct.
Rebalancing the underlying economy so `fortified_in_time` is earnable
through ordinary play at all is a real but separate question from Z27's
scope (does the DIFFICULTY TOGGLE change reachability) — flagged as a
background suggestion for a dedicated look rather than folded into this
pass. No code changed for Tide as part of Z27; `flake8`/tests unaffected
(252/252, confirmed unchanged — the scratch simulation script used for
this investigation was never committed).

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
`localStorage["whats-new-seen:tide"]` (the date string of the newest
entry already shown) and lists just the new ones, not the whole log. A
first-ever visit silently marks the current changelog as seen rather
than dumping the full history on a brand-new player. Reuses the same
`window.CHANGELOG_JSON` global this game's own changelog panel already
fetches -- no second network request. One `<script
src="../../shared/whats-new-banner.js" data-game-id="tide">` include,
added right after `shared/last-played.js`'s own include. See root
`CLAUDE.md`'s Working notes for the full write-up -- shared
infrastructure, documented once there rather than duplicated across all
12 games' own files.

## Keyboard-shortcut convention: ?/Esc (Z4, site-wide goal)

Wired via the new shared `shared/keyboard-shortcuts.js` -- one script
include plus one `KeyboardShortcuts.init({panels: [...]})` call at the
end of `index.html`, listing this game's real toggle-button + hidden-
panel pairs: How to Play, Settings, Achievements, What's New, Session
Summary, and the Info Page. `?` opens a small floating shortcuts-help
overlay; `Esc` closes it and clicks the toggle button of whichever listed
panel is currently open, reusing each panel's own open/close logic. The
Hard Lag difficulty toggle isn't in the list -- it's an on/off flag with
no corresponding panel.

## Sister settlement (D3, 2026-09-26)

The lighter multi-settlement mode: an optional, one-way switch ('Add a sister settlement') that adds a second coastal settlement which SHARES your funds and your adaptation tier but has its own, lower-lying coastline (`SISTER_EXPOSURE` 1.3 times the sea rise, rows flooding `SISTER_LEVEL_OFFSET` 20 earlier via `sister_sea_level()`/`sister_rows_flooded()`). Each season, right after the main coast's rise, `_advance_sister()` charges the shared funds `SISTER_FUNDS_PER_DAMAGE` (2) per point of the sister's damage (taken after the same tier dampening, so one seawall investment protects both) and credits `SISTER_INCOME` (10) from its own fishing and trade. It is not a second game to manage: it adds a second, differently exposed thing that your one set of decisions must protect, and it cannot be switched off once added because its history is part of the run. A readout shows rows flooded, damage so far and the net funds effect. Off by default, with no effect on funds while off (tested). Save: `sister` written only when on (damage and net funds, validated finite and bounded); a save without the key loads with it off. 252 -> 265 tests (`tests/test_sister_settlement.py`); verified live.

## Community seawall pace (D9, 2026-09-26)
`get_state()` gains a write-only `tier_first_season` dict (`t1`..`t4`: the first season each adaptation tier was active, derived from `tier_log`; only tiers reached are present), whitelisted in `app/stats.py` as `tier_first_season.t1..t4`. `shared/community-index.js` shows the community median season per tier with optional `[...]` groups so tiers with too little data are simply left out. Tests: `tests/test_community_tier_field.py`.

## Y11b light-theme polish (2026-09-27)

Method: a computed-style WCAG scan run in a real browser with the light theme on (walks every visible element with text, composites the ancestors' backgrounds including gradients, compares against the computed text colour, flags below 4.5:1 for normal text and below 3:1 for large text; also flags meter/track/tile fills that sit within 1.5:1 of their parent and dark surfaces left under the light theme). Disabled buttons are excluded (WCAG exempts inactive controls) and counted separately. It was run on the fresh game and again after playing, with every panel opened one at a time, and finally with every `[hidden]` element force-shown to catch panels a normal session does not reach. Screenshots in this environment were unreliable, so the scan output is the evidence, not eyeballing.

**Found (before):** 8 text groups on the fresh game and 9 after play: dimmed captions (`.meter-label`, `.hub-back-link`, achievement progress/description/earn-rate, changelog dates, how-to step numbers at opacity .5-.7, 3.2-4.3:1), the pale info "i" bubble (1.23:1), the earned-achievement teal label (1.4:1), the selected feedback button's dark text on its dark-green fill (2.0:1) and, only when the yield warning shows, the pale `.fish-warning-banner` text (1.19:1). The coastline plot tiles were checked separately: land against the pale panel is 4.5:1, flooded 6.1:1, the seawall and tidal-outline lines 2.8-4.9:1, and tile *meaning* is carried by the seawall line, dashed outline, heritage glyphs and hatch rather than hue alone, so no tile colour was changed; only the grid's own edge (dark, invisible on light) gets a visible border.

**Fixed:** a `Y11b` block at the end of `style.css`, every rule under `html[data-theme="light"]`: captions to `opacity: 1` with a deeper slate, info bubble, earned label, feedback button text, fish warning, coastline grid border. Dark is untouched.

**After:** 0 flagged text and 0 flagged fills on the fresh game, after about 40 seasons of play, and with every hidden element shown. Exceptions: disabled buttons (2.37:1, exempt), the transparent gradient-clipped `h1` (its glyphs are the shared layer's dark gradient, measured 1.0 only because the scan can't read a clipped gradient) and the achievement toast (deliberately a dark toast in both themes). `tests/test_light_theme.py` pins that the block exists and stays light-scoped. Needs a human eye: the pill still floats bottom-left here (this game has a Settings panel, but moving the switch was only asked for SOL).

## Endgame flourish (R-19, 2026-09-27)
CSS only: `.coastline-seawall--t4` (the top tier) animates `tide-barrier-glint`, a slow inset shadow pulse that changes no tile state or colour, inside `@media (prefers-reduced-motion: no-preference)`; the existing in-game `html[data-reduced-motion="true"]` blanket rule collapses it too. Tests: `tests/test_barrier_flourish.py` (3; 271 -> 274).

## Desktop boot (PC version, 2026-10-06)

`games/tide/pc.html` is the Desktop boot: the same game over the same `game.py` and saves (same `game_id`), laid out for wide windows. **Never edit it by hand**: it is generated from `index.html` plus `pc-config.json` by `scripts/generate-pc-pages.py`. Per-game files: `pc-config.json` (what moves where), `pc.css` (layout, all under the pc layout), `pc.js` (`window.TIDE_PC_TUTORIAL_STEPS`, which `index.html` uses when present, plus a small Escape fix for the `?` list). `index.html` gained only the `layout-pref.js` tag and the `TIDE_PC_TUTORIAL_STEPS ||` fallback.

- **Layout.** No page scroll. Top bar: back link, title, three icon buttons (Achievements, Session Summary, Settings) and the Menu (Esc). Under it a strip of readout chips mirroring the original lines (season, funds, acidity, fishing yield, sea level, damage), which keep updating by id. Stage: the sea-level scenario select above the coastline (it locks after season 1, so it stays visible and is called out in the Desktop tutorial), the fish warning/recovery banners, the decorative tide scene, the coastline grid filling the remaining height, then the live ticker (capped at four lines, scrolls), the population line and the hotkey hint bar. Right column (scrolls on its own): investments and Advance Season (sticky at the top), the next adaptation tier progress line, Coastal programmes, Settlement name and history.
- **Windows from the Menu.** "Status, graphs and history" (the old `#status` section with the meters, graphs and full ticker history), "Sea level, damage and adaptation" (`#sea-level-section` plus the community line), "Coastline: then vs. now", and "Send feedback"; plus How to Play, What's New, Session Summary, Settings, Achievements and The Real Story as before. The Menu also holds the sister-settlement and harder-lag toggles and the tutorial.
- **Notifications.** None: `#ticker-log` is one paragraph, not a list, so `notify` is null; the ticker is shown live under the coastline instead.
- **Hotkeys.** Only `?` (shortcuts list) and Esc are real in Tide, so those are the only hints.
- **Known limits.** The sea-level scenario control is only a visual hint that it is locked (greyed select) after the first season; the `?` overlay is the shared one, not a shell window (pc.js stops Escape from also opening the Menu); no game-specific notification stack; scripted play only (about 30 seasons in the Desktop layout), no full human playthrough. 274 tests unchanged.


## TODO pass 2026-10-07 (planning/TODO.md "GD + D. Tide": D-1, D-7, D-14, D-15, D-17, D-18, D-24, D-27)

- **D-1 Harbor Ledger.** `season_ledger` on the state: one dict per resolved season (season, funds, acidity, fish_yield, damage, rows_dry, population, tier, invested; rounded, capped at `LEDGER_LIMIT` 120), written at the end of `advance_season()`. Saved as `season_ledger`, validated entry by entry on load (a save without it, or with damaged entries, loads an empty ledger and the summary notes that older seasons are not listed). It is dropped from checkpoints (`CHECKPOINT_DROP_KEYS`) and `replay_from_checkpoint()` truncates it to the seasons before the checkpoint. Panel `#ledger-panel` (toggle `#ledger-toggle-button`, shortcut L, Desktop window under Records): sortable column buttons (`ledger-sort-<key>`, `aria-sort` on `ledger-th-<key>`) and a sparkline per column (`ledger-chart-<key>`).
- **D-15 Advance x5.** `advance_quiet_seasons()` runs up to 5 seasons and stops BEFORE any season where `attention_reasons()` is non-empty: storm forecast this or next season, fish-yield warning showing (`fish_warning_active()`), an affordable unprotected heritage site about to flood (`HERITAGE_RISK_SEASONS` 1), or a monitoring crew available again (only for a player who has used monitoring before). If something already needs attention, it does not start and says why (`#advance-x5-note`).
- **D-14 game keys** in `ui.js` (shared by both pages): A, X, 1/2/3, R (session report), L; ignored while typing, with Ctrl/Meta/Alt, over the opening screen/tutorial/confirm dialog/`?` list, and (Desktop) the turn and invest keys are off while a window is open. Listed in the `?` overlay (`extra`) and the Desktop hint bar.
- **D-7 accessibility (partly closes the item).** `#season-announcer` (polite live region) announces each season's result, investments and x5 outcome; `#coastline-description` plus per-row `aria-label`s ("Row 5: dry, seawall tier 2, ..."); one focus stop per coastline row with Up/Down between rows and focus kept across re-renders; invest buttons get descriptive `aria-label`s; graphs are focusable with latest values in their labels; a visible `:focus-visible` ring everywhere. Not done: a full roving-tabindex grid or per-tile (column) navigation, since all columns of a row share one state.
- **D-17 ticker filters.** Chips (All/Fish/Sea/Economy/Storm/Chronicle) and a search box on the FULL history only; the short live ticker is deliberately never filtered. `ticker_category()` classifies by wording at render time, so old saves filter too. View-only state, never saved.
- **D-18 Copy as text.** `share_text()` (name, session summary, population/rows, chronicle) copied via the clipboard API; falls back to a read-only text box when the browser refuses.
- **D-24 tab title/favicon.** `document.title` = "Tide S12", plus " - storm forecast" / " - fish warning" / " - heritage at risk"; the favicon swaps to a data-URI badge (amber circle for warnings, red square for a storm, so not hue-only) and back to the original.
- **D-27 details memory.** `ui.js` remembers every `<details>` panel's open state per browser under `tide-details-open:<summary text>` (the "i" bubbles are skipped).

Tests 274 -> 322 (`tests/test_todo_pass_oct7.py`). `tests/fakes.py` gained `setAttribute/getAttribute/focus/tabIndex`. Verified live (index.html and pc.html at 1440x900, index at 360x740): keys, ledger sort/charts, x5 refusal note, filter and search, remembered details across reload, row focus with arrows, tab title and favicon, no console errors.

## TODO pass 2026-10-08 (planning/TODO.md "GD + D. Tide": D-2, D-4, D-6, D-9, D-21, D-22, D-23, D-25, rest of D-7)

- **D-21/22/23 graphs.** `acidity_fish_history_svg()`, `delayed_consequence_svg()` and the damage sparkline share small helpers (`_xy`, `_series_svg`, `_marker_svg`, `_crosshair_attr`). Each graph carries a `data-crosshair` JSON list (one readout string per x position, built in Python so it is tested); `ui.js` draws the vertical line and a readout from it on hover, tap, or Left/Right/Home/End on the focused graph (Escape clears it; `pc.js` stops that Escape from opening the Menu). Range (Last 10 / Last 20 / All, `graph-range-*`) windows the main and delayed-consequence graphs (the average line, baseline marker and timeline follow the window). Markers toggle (`graph-markers-toggle`) adds circle/square/triangle points and a long dash on fish yield (dotted on damage), thinned to `GRAPH_MARKER_LIMIT`. Both options are view-only, kept in localStorage `tide_graph_prefs_v1`.
- **D-4 scrubber.** `season_snapshots` ([season, sea_level, heritage code "u/p/l" per site, retreat rows], about 30 bytes each, capped like the ledger, validated on load, dropped from checkpoints and truncated on replay) plus the ledger rebuild any earlier season start. `#scrub-slider` under the coastline redraws the SAME grid from that snapshot (class `coastline-grid--scrubbed`, dashed outline, no flash, no tide) and `#scrub-readout` names funds, acidity, yield, damage, rows, population, tier and heritage. Any change to the live run (`_state_stamp()`) ends the look back; the live state is never written. Seasons an old save has no record of are skipped.
- **D-6 planner.** `project_plan()` deep-copies the settlement, swaps the module `state` for the copy inside try/finally, invests and advances, and returns one point per planned season (funds, acidity, yield, damage, rows dry, rows at risk = flooding within `PLANNER_RISK_SEASONS`, tier, unaffordable count). 3 to 5 seasons, 0 to 9 per category. Nothing is saved or spent until "Commit season N", which invests and advances ONE real season and slides the plan up. Window "Season Planner".
- **D-2 library.** localStorage `tide_session_library_v1`, up to 12 sessions (settings, damage avoided, rows dry, tier, acidity and fish series, validated on load, never in a save). Needs 3 played seasons. Any two (A solid, B dashed; A may be the current session) overlay in the panel, and one saved session can be drawn dashed on the main graph.
- **D-9 almanac (+ D-25).** localStorage `tide_almanac_v1`: lifetime seasons, rows kept dry (counted per season), heritage sites protected, storms weathered, and the best run (most damage avoided) per sea scenario and lag mode with its tier combination. `almanac_sync()` runs from `render()` against a cursor that is reset on load/replay, so loading a save never double counts. Because rows flood on the sea's schedule whatever you do, "best" is measured in damage avoided, not seasons dry. The session summary gains a "Best for this scenario" line. NOT fed to the hub achievements dashboard (needs a shared hook).
- **D-7 rest.** Every coastline tile is now labelled ("Row 5, column 3: dry, ...", heritage only on its column) and focusable; one Tab stop per row, arrows/Home/End walk rows and columns in `ui.js`.
- Not built: D-17 live-ticker filter (kept unfiltered by design), D-3, D-5, D-8, D-10 to D-13, D-16, D-19, D-20, D-26, D-28 to D-31 (not in this batch; several need shared components or user input).
- Tests 322 -> 370 (`tests/test_oct8_pass.py`; the old one-focus-stop test was updated for focusable columns). New ids: planner-*, library-*, almanac-*, scrub-*, graph-range-*, graph-markers-toggle (all in index.html and pc.html; panels are Desktop windows and Menu entries). No new JS file.

## Pause and fast-forward audit (W-2, 2026-10-08)
- Tide has no real-time tick (no `setInterval`; the only timers are one-shot UI timeouts). Seasons advance only when the player presses Advance Season, so there is nothing to pause or speed up and neither shared control was added.
- Wiring pass 2026-10-08: the Session Summary carries the shared Copy result button (`copy_result_fields()` in game.py feeds `shared/copy-result.js`; mounted by the inline script at the end of index.html; the storm count is only mentioned when storms were on), earned achievement cards get a Share button (`shared/achievement-share.js`), the head carries the Open Graph/Twitter block and JSON-LD from `share/meta/tide.html` and `share/jsonld/tide.json`, and the How to Play and Info panels end with a Credits link. Pins: `tests/test_wiring_oct8.py`.

### Acidity three seasons ago (FY-2 / D10, 2026-10-08)
`acidity_past_text()` in `game.py` reads `state.acidity_history[-3]` and renders "Three seasons ago: acidity X (now Y, up/down/unchanged)" into `#acidity-past-display` (a second status line under the acidity, a "Acidity then" chip on the Desktop page). It says "not yet played (n of 3 seasons banked)" before three seasons exist. Derived from existing history: no new save key. `ACIDITY_PAST_SEASONS = 3`. Tests: `tests/test_acidity_past.py`. Also fixed pre-existing flake8 warnings (an unused `global` list, two ambiguous `l` names).


## 2026-10-10 TODO pass (D-26, D-10, D-17, D-12)

- **D-26 phone view.** `index.html` has a `#mobile-views` bar (All / Coast / Meters / Log, All is the default and hides nothing); elements carry `data-mview="coast|meters|log"`, and `style.css` hides the others under `max-width: 640px` only (never on `data-layout="pc"`). `ui.js` handles the buttons, swipes (60 px, mostly horizontal, ignored on sliders, graphs, tables and the dock), the remembered choice (`tide-mobile-view`) and a tap on a coastline tile writing its note into `#coastline-tap-readout`. Tiles, chips and invest/advance buttons are 44 px tall on phones. Tests: `tests/test_mobile_view_browser.py` (real index.html in headless Chromium via `tests/browser_support.py`, game not booted).
- **D-10 ranks.** 18 new flat ids (`storm|heritage|retreat|diversify|monitor|population` x `bronze|silver|gold`) with extra `family` and `rank` fields in `achievements.json`; `achievements_earned` stays a flat id list. New counters `storms_weathered`, `storms_clean`, `early_retreats` ride a `ranks` block in the save (omitted while all zero). The in-game panel shows a rank line and a "Ranks:" summary. The hub rarity labels (Bronze/Silver/Gold by how rare) are a different thing and can sit beside a rank label.
- **D-17 live ticker filter.** `live_ticker_filter` / `live_ticker_search`, own chips (`live-filter-*`), closed `<details class="ticker-live-filter">`, default All, never saved; a visible status line says how many messages are hidden. The full-history filter is unchanged and independent.
- **D-12 dashboard.** `ui.js` `DASH_PANELS` (meters, sea, coast, compare, settlement, programmes), presets Standard/Compact/Analyst/Postcard, show/hide, pin (pinned sit on top) and up/down moves, in `localStorage["tide-dashboard-v1"]`. Hiding is `data-dash-hidden` (CSS display none); ordering moves the real elements between two comment markers. Not applied on the Desktop page. Tests: `tests/test_dashboard_browser.py`.

- **GN-8 / GN-9 (2026-10-11, your notes).** GN-8: on the Desktop page the Workshop, Restore and Crew folds sat below the hint bar and left a gap; `pc-config.json` now has composite window `pc-tools-panel` ("Workshop, restore and crew", Menu > Game; `pc.js` opens its folds) and `pc-sightings-panel` (Menu > Records) for the sightings line; `#harbor-quip` moved into the stage zone. The Classic page is unchanged. GN-9: `season_forecast()` runs the real `advance_season()` on a deep copy (the same global-state swap the Season Planner uses, restored in a `finally`), so the projection is exactly the next season with no new investments: income, upkeep, wages, the fish lag, sea rise, storms, deals. `forecast_chips()` gives funds, acidity, fishing yield, sea level and damage as now -> next with an arrow (up, down or a dot and "no change", so it never relies on colour) and the delta, plus a dry-rows chip only when a row would flood; `render_forecast()` writes `#forecast-line` (Classic: top of the status section, Desktop: the stage bar). The Settings checkbox (`forecast-checkbox`, on by default) stores `tide-season-forecast` = "off" in localStorage; Reset to Default turns it back on. Nothing is saved to the run. Tests: `tests/test_gn_oct11.py` (13, including forecast == real next season over 14 seasons, with investments, a mixed output, storms, a severe sea, hard lag, crew and the sister town, and a check that the real state is unchanged).

## D-8 named coastlines, D-3 shareable run codes, GD-5 Daily Tide (2026-10-11)

Tests: `tests/test_oct11_batch.py` (about 90). New element ids (both `index.html` and the generated `pc.html`): `coastline-select`, `coastline-blurb`, `run-code-output`, `run-code-copy`, `run-code-status`, `run-code-input`, `run-code-load-button`, `run-code-clear-button`, `run-code-message`, `daily-toggle-button`, `daily-panel`, `daily-date-input`, `daily-plan`, `daily-start-button`, `daily-message`, `daily-status`, `daily-copy`, `daily-archive`. The boot script now also writes `shared/seed.py` and `shared/run_code.py` into Pyodide (`game.py` imports `run_code as shared_run_code` and `seed as shared_seed`) and the page loads `shared/seed.js`. Desktop: Daily Tide is a window (Menu, Game group); the run-code box lives inside the existing Session Library window; the coastline picker sits in the stage bar next to the sea scenario (it carries the same `sea-scenario-label` class so the zone picks it up).

**D-8 coastlines.** `COASTLINES` (open, delta, headland, atoll, port) holds per coastline: `thresholds` (sea level at which each row floods, row 0 = top), `heritage` (two sites with their own ids, rows and costs), `output` / `tourism` / `aquaculture` income weights, `storm_interval` and `surge`. `open` is the standard game and reproduces the old numbers exactly (guarded multiplications, thresholds built from the old formula; a pinned 20-season run in the tests). The module functions `row_flood_threshold`, `tile_row_state`, `coastline_grid`, `flooded_row_count`, `heritage_sites`, `coast_meter_max`, `coast_storm_interval` take an optional coast id and otherwise read the running `state.coastline`; the class methods always pass `self.coastline`, so the planner/forecast copies (which swap the module `state`) stay correct. `state.coastline` is locked once season 1 has been played (`set_coastline`, like `set_sea_scenario`), saved only when not `open` (`coastline` key; unknown or missing values load as `open`), carried by library records (`coast`, older records read as `open`), the planner, the ghost replay and run codes. The Almanac's per-scenario best stays the standard coastline's: other coastlines still add to the lifetime totals but never set a best. Balance (adaptation policy: 3 Output, 4 Reduction, adaptation to tier 3, versus the same economy with no defences): every coastline loses all its rows in the end, as the open coast does, because the sea always wins; the defences cut damage by about half or more on all of them and hold every storm, while the undefended economy gets breached at every storm.

**D-3 run codes.** `shared/run_code.py` carries a mode word (8 symbols), a score and two numbers; Tide packs 184 bits into those (`_pack_run`): a 39-bit header (coastline, sea scenario, lag, storms, output mix, seasons played, seasons held, damage avoided, rows dry, tier) then Elias-gamma Output / Reduction / Adaptation purchases per season. A long run keeps its first seasons that fit (the header says "first N of M"; about 25 to 40 seasons). The code is built from `state.season_buys` (a per-season purchase log, saved as `buys`; runs begun before the log existed cannot be shared). Not shareable: Workshop, Tidal Chess, Acid Tide boss, and Daily Tide runs. Pasting (`decode_run_code` / `load_ghost`) accepts the copied "Tide run code, RUN-TIDE-..." line, forgives case and dashes, caps input at 400 characters and says in plain words when a code is mistyped, cut off, from another game, from a newer format or does not describe a real Tide run; nothing changes on any refusal. A good code is replayed through the game's own `advance_season` on a scratch settlement (`replay_run`, exact for acidity and fish yield unless the sender used Trade Winds exports, crew or retreat, which do not change what the code needs), stored in memory only (`_ghosts`, up to 6, ids `g1`...), listed in the library selectors, shown as the dashed overlay on the graphs and as session B. It is never playable and writes nothing. The shared Copy result button copies the code; the box says "A friend will see: ..." and that codes are not verified.

**GD-5 Daily Tide.** An opt-in panel (`daily-panel`): 12 seasons (`DAILY_SEASONS`), the coastline, sea scenario and three storm seasons (one in each of three windows) come from `shared/seed.py`'s daily seed for the UTC date (`daily_plan`). The sea scenario, coastline and storm toggle are locked in a daily; storms follow `state.daily["storms"]`. Any date from 2026-01-01 up to today (UTC) is playable, so skipping a day costs nothing, and there is no streak anywhere in Tide's own UI. Starting a daily replaces the current run (a second press confirms when a run is under way). A finished day books its result once (kept in `tide_daily_v1` in this browser and in `state.daily["result"]`, saved with the run) and offers a Copy result line ("Tide daily 2026-10-11: 12 seasons, 2 rows lost, 1 site saved" plus the seed). Daily runs stay out of the Almanac, bests and library (`keeps_records_out`). The hub Today mark (`NoyvjSeed.daily.markCompleted`) is called only when today's own daily finishes, the player has turned on "Show my daily puzzles and streak in the Today strip" at the hub (`hub_today_track_dailies`) and the page's shared seed helper agrees it is today's seed; an archive day never marks. The optional daily board (a backend change) was deliberately skipped.
