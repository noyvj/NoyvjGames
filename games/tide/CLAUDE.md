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

## Working conventions

- Commit + tag per milestone: `git commit -m "Milestone N: <name>"` then `git tag tide-milestone-0N`.
- Update the milestone table Status as work happens.
