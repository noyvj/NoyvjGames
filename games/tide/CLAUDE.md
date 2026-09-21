# Tide — Ocean Acidification & Sea-Level Rise Game

**Read `../climate-quartet-plan.md` first for shared conventions (testing, feedback hook, hope-angle requirement, hub integration).** This file is Tide-specific only. **Build third** — the grid redraw is the most visually involved piece of the four, so get Grid and Canopy's patterns solid first.

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
