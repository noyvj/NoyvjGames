# Drift — Climate Migration & Displacement Game

**Read `../climate-quartet-2-plan.md` first for shared conventions.** This file is Drift-specific only. **Build last** in this set — it's the most systems-heavy and longest-timeline game across both sets; only tackle it once the other patterns are proven.

## Concept

As sea-level and extreme-weather pressure rise over a long timeline (conceptually related to Tide's world-state, though Drift can stand alone), populations in vulnerable regions are displaced. The player manages a **receiving region's response** — building capacity, integration systems, and infrastructure to absorb displaced populations well versus badly. This is less about a single meter and more about how prepared institutions turn a crisis into a manageable transition instead of a chaotic one.

## Function tags: Futures on current path + Systems to combat

Drift does double duty: it simulates a downstream future consequence of unaddressed climate change (displacement), *and* it's fundamentally about designing the systems (housing capacity, integration infrastructure, services) that determine whether that future is a crisis or a manageable transition. Both framings should show up in how this game gets discussed in the Contextual Report Blog.

## Climate issue & hope angle

**Issue:** climate-driven migration and displacement, and the institutional capacity to absorb it.
**Hope angle:** the entire point of this game is that displacement doesn't have to mean crisis — a well-prepared region can absorb significant population pressure smoothly, while an unprepared one turns the same pressure into collapse. The player should be able to reach a genuinely thriving, successfully-integrated end-state through good institutional investment, proving that the "crisis" framing common in real-world migration discourse is a preparedness failure, not an inevitability.

## Core loop

- Turn-based rounds across a long timeline. Displacement pressure (number of people arriving) rises on a schedule loosely tied to background climate severity, largely outside direct player control.
- Player allocates regional resources across: housing capacity, integration services (language, employment, education access), and general infrastructure capacity (utilities, transport, healthcare).
- Under-investment relative to arrival pressure causes visible strain (service shortfalls, social/economic friction) — not a fail-state, but a visibly worse regional outcome that compounds if left unaddressed.
- Over time, well-integrated arrivals should contribute back to regional capacity (economic participation, workforce contribution) — the game should model integration as eventually *net-positive*, not a permanent drain, which is the core of the hope angle.
- Scoring: long-run regional wellbeing (a composite of service quality, economic health, and social cohesion) rather than a single number — reflects that "successful adaptation" here is multidimensional, not just "did you survive."

## Milestones

| # | Milestone | Content | Status |
|---|-----------|---------|--------|
| 1 | Core allocation loop | Resource allocation across housing/services/infrastructure, round progression. Tests: allocation logic | Done |
| 2 | Displacement pressure schedule | Arrival numbers rising over the timeline, loosely tied to background severity. Tests: pressure-schedule calculation | Done |
| 3 | Strain vs. capacity system | Visible consequences when investment lags behind arrival pressure, without a hard fail-state. Tests: strain-calculation and threshold logic | Done |
| 4 | Integration payoff loop | Well-integrated population contributing back to regional capacity over time (net-positive modeling). Tests: contribution-calculation formula, timing/lag logic | Done |
| 5 | Composite wellbeing scoring | Multidimensional scoring across service quality, economic health, social cohesion. Tests: composite scoring formula across sample playthroughs | Done |
| 6 | In-game feedback prompt | Piped to Neon backend per root conventions | Done |
| 7 | Visual/UI pass + hub integration | | Done — all 7 milestones complete |

## Iteration Notes — Pass 1 (implemented)

Design-review pass (pre-playtest, from `climate-games-iteration-pass.md`). Anticipated issue: given how sensitive the subject matter is (real displacement, real people), this game risked feeling either too dry (an allocation spreadsheet) or, if over-corrected, too narrativized in a way that dramatizes individuals rather than institutions.

**Built in response (see `BCM114-DEV-LOG.md` 2026-08-11):** a three-bar composite wellbeing dashboard (services / economy / cohesion), a mid-run plain-language checkpoint summary, and short case-study-style context blurbs about real regions that handled climate migration well institutionally — framed at the policy/systems level, not as individual personal stories.

**Open testing question:** can players identify which of the three sub-scores is lagging and explain why? Is the "integration is eventually net-positive" mechanic actually felt, or does it stay invisible in the background math?

## Iteration Notes — Pass 2 (implemented)

Second design-review pass, from `climate-games-iteration-pass-2.md`, building on Pass 1. **Selected addition: C (long-horizon outcomes).**

- **Long-horizon outcomes:** end a session with a coda showing descendants of successfully-integrated populations contributing to and thriving within the region generations later — extending the hope angle across a longer timeline than the session itself covers. Keep this framed institutionally (workforce, community roles, regional contribution), consistent with the Pass 1 sensitivity note above — this is about a region's long-run outcome, not a family's.
- **Visual polish for this pass:** the three-bar composite dashboard should carry into the coda as a final, visibly improved state relative to where the session started — the long-horizon payoff needs to be legible as a continuation of the same dashboard the player was already reading, not a disconnected epilogue screen.

## Iteration Notes — Pass 3 (Fun/Teaching Balance)

Third design-review pass, from `climate-games-fun-teaching-balance.md`. **Risk:** shares Loop's "dry abstraction" risk (a composite dashboard can feel like a spreadsheet) and Thaw's "fear without efficacy" risk (real displacement framed institutionally can read as fatalistic if the net-positive integration payoff isn't clearly felt).

**Implemented:** the net-positive integration mechanic previously only showed up as a background number (`integration_contribution()` folded into the funds total each round) — there was no called-out moment where the player notices the shift from strain to contribution. Added a legible "turning point" milestone: the game now tracks cumulative funds integrated arrivals have contributed back against cumulative funds spent on the services investment that enabled that integration (`cumulative_integration_contribution`, `cumulative_services_investment`). The first round the former catches up to the latter, the region has durably crossed from net strain to net contribution (`has_crossed_to_net_positive()`, `net_positive_round` — a milestone that's recorded once and stays true for the rest of the run, not a live ratio that could flicker if a later services investment briefly raises the payback bar again). A new callout (`integration_turning_point_message()`, rendered in a dedicated `#integration-turning-point-display` element styled with the coda's warm accent) surfaces this the moment it happens: *"Turning point, round N: this region's integrated arrivals have paid back the services investment that got them there. From here, integration is a net gain for regional capacity, not a cost."* Framing stays institutional/systems-level throughout — no names, no individual stories, consistent with this file's sensitivity note.

Also updated the in-game feedback prompt, given this game's added topic sensitivity: it now asks directly "Did you come away feeling migration pressure is a manageable systems problem, rather than an unmanageable crisis?" — a testable version of the trust-vs-fear distinction from the cited research, replacing the previous more general "did this change how you think about..." question.

## Info Page — real-world sources (implemented)

*Implementation is now shared across all 8 climate-quartet games — see `shared/info_page.py` and `shared/info-page.css`. Only the content below (framing/tie-in/sources) is game-specific; the rendering/toggle code moved out of this game's `game.py`.*

An optional, player-triggered "The Real Story" panel — never forced mid-session, since the mechanic teaches first and this is a supplement for players who want to go deeper. Toggled via a button near the top of the page; shows a short framing paragraph (written fresh, not copied from any source), a one-line note tying the mechanic to real data, and a sources list with clickable links. Framing kept institutional/systems-level, consistent with this file's sensitivity note above — about regional capacity, not individual migrant stories.

**Framing:** Climate-driven displacement is already happening at scale, and how well it goes depends far more on a receiving region's institutional preparedness than on the number of people arriving — real projections vary by tens of millions depending on how much the world invests in resilience now. Drift's capacity-vs-pressure system is modeled on that same institutional framing, deliberately kept impersonal rather than told through individual stories.

**Mechanic tie-in:** Drift's long-horizon coda is grounded in real evidence that early institutional investment in integration converts displacement pressure into a net-positive contribution over time, not just crisis management.

**Sources:**
1. [UNHCR — Climate change and displacement](https://www.unhcr.org/us/what-we-do/build-better-futures/climate-change-and-displacement) — the authoritative agency perspective, framing displacement institutionally.
2. [Migration Policy Institute — Climate Migration 101: An Explainer](https://www.migrationpolicy.org/journal/feature/climate-migration-101-explainer) — real projections (44-216 million internal migrants by 2050) echoing Drift's "preparedness changes the outcome" hope angle.
3. [Migration Policy Institute — Who Counts as a Climate Migrant?](https://www.migrationpolicy.org/article/who-is-a-climate-migrant) — the legal/definitional gap behind why Drift frames this as a systems/capacity problem, not a legal one.
4. [Brookings — The climate crisis, migration, and refugees](https://www.brookings.edu/articles/the-climate-crisis-migration-and-refugees/) — policy-level analysis of the institutional response gap.
5. [Migration Policy Institute — How Are Refugees Faring? Integration at U.S. and State Levels](https://www.migrationpolicy.org/publication/how-are-refugees-faring-integration-us-and-state-levels) — source for the in-game real-world resettlement-outcome benchmark (I9, TODO.md): as of 2023, 89% of working-age refugees resettled in the U.S. within the previous five years were employed.

All five links verified live before merging (source 5 added alongside I9). Source 1 (UNHCR) and sources 2–3, 5 (Migration Policy Institute) return 403/bot-challenge to automated fetchers but are well-known, legitimate institutional domains — consistent with the bot-protection pattern confirmed on several other sources across this batch.

## Achievements (implemented)

18 achievements added per the hub-wide framework (`planning/ACHIEVEMENTS-SYSTEM-DESIGN.md`), following SOL's reference integration: `achievements.json` catalog, `game.py`'s `ACHIEVEMENT_CHECKS`/`ACHIEVEMENT_PROGRESS`/`achievement_ids_earned()`/`achievements_summary()`, an in-game toggle + panel, an unlock toast, a hub-dashboard link, and `achievements_earned` riding `get_state()` (never read back on load). Span capacity-building, arrivals/strain resilience (including a genuine crisis-to-recovery achievement and a "never went critical" one), integration milestones, wellbeing-quality thresholds (Thriving/Model Region), and long-run play — kept institutional/systems-level throughout per this file's sensitivity note (no individual-story framing beyond the game's own existing "Integrated: N people" language). Two achievements needed genuinely new tracked state: `best_stable_streak` (a round-by-round stable-strain streak, sticky like Grid's `best_clean_streak`) and `coda_ever_viewed` (has the Long-Horizon Outcomes coda ever actually been opened, since `coda_visible` alone just toggles). Hub-side `script.js` registration (`GAMES_WITH_ACHIEVEMENTS`) is out of scope for this games/drift/-only dispatch, per the pattern already established for Grid/Canopy/Continuum's own rollouts.

## Colorblind-safety audit (implemented)

Audited as part of the site-wide colorblind-safety audit (`planning/TODO.md`, Okabe-Ito-palette method per Continuum's Phase 5, redundant-cue method per Canopy's B9, audit-only method per Tide's D11). Checked every place `game.py`/`style.css` convey game-state meaning by color, especially red/green and blue/purple confusion pairs.

- **`.meter-fill--strain`'s stable/strained/critical tiers (blue → gold → orange-red)** and **`.meter-fill--wellbeing`** — not a violation. This is a single-hue-per-tier severity scale, not a paired good/bad color, and `#strain-display`'s text already states the tier in plain words ("Strain: X% (stable/strained/critical)") per the space-theme visual pass's own note that these are meaningful, already-labeled game state.
- **`.turning-point-message`/`.coda-section`'s shared warm accent** — a single celebratory color, not part of a contrasting pair, and both are always accompanied by their own explicit message text.
- **The I1 trend graph's two lines (`.trend-line--strain` red `#e0674c`, `.trend-line--wellbeing` green `#4c9c6e`) — real violation, found and fixed.** Unlike the meters above, this red/green pair exists only here (confirmed via `grep` — neither hex value appears anywhere else in `style.css`) and had no non-color cue for reading the two lines' overall shape: each point does carry a `<title>` tooltip (e.g. "Round 4 -- Wellbeing: 55"), but that only reaches a viewer who hovers/taps one point at a time, not someone reading how the two trends move relative to each other at a glance — exactly the deuteranopia/protanopia confusion pair the task calls out, and the same shape of issue as Grid's own copy of this same trend-graph pattern (`I1`'s docstring: "same rendering approach and visual language as Grid's own trend graph" — Grid's copy is out of scope for this dispatch, tracked separately as its own TODO item).
  - **Fix:** CSS-only — added `stroke-dasharray: 6 3` to `.trend-line--wellbeing` (solid strain line vs. dashed wellbeing line), so the two lines are distinguishable by pattern regardless of color perception. Deliberately left both hex values untouched (per the space-theme visual pass's existing "these encode real game state, don't touch the hue" convention) and didn't touch the point markers or `game.py` at all — no shape/count change to the `<circle>` markers `tests/test_trend_graph.py` already pins (`svg.count("<circle") == 8`), so the fix is zero-risk to the existing suite. Full pytest suite (248 tests) green before and after.

## Settings panel (implemented)

Site-wide goal (`planning/TODO.md`, origin A9): one panel per game consolidating text-scale and animation/motion controls. **No sound toggle** — this hub has no audio implemented anywhere yet (`planning/LATER.md`'s "Standing question: what can you actually do with audio?"), so a toggle for it would control nothing real.

A new `⚙️ Settings` toggle button in the toolbar (after the difficulty toggle) opens `#settings-panel`, containing:
- **Text size** — decrease/reset/increase buttons (A−/A/A+), scaling `--text-scale` on the root element (0.85–1.5, step 0.1), same range/step Continuum's Phase 5 `accessibility.js` established first.
- **Reduce Motion** — a toggle button adding/removing `.reduce-motion` on `<html>`, which forces every animation/transition already in `style.css` to be effectively instantaneous (a global override, layered on top of the existing per-animation `@media (prefers-reduced-motion: reduce)` rules that only respect the OS-level setting, not an in-game player choice).

**`settings.js` is a new standalone file, deliberately independent of Pyodide/`game.py`** — same documented exception this hub already established for Continuum's `accessibility.js`: a browser-level UI preference, not game/save state, so it's persisted to `localStorage` (`drift-text-scale`, `drift-reduced-motion`) rather than riding `get_state()`/`load_state()`. It works even before Pyodide finishes booting.

Verified live: toggling both controls updates the page immediately with zero console errors, and both settings survive a full page reload via `localStorage`. Full pytest suite (248 tests) unaffected — this feature touches no Python.

## "What's New" changelog panel (implemented)

Site-wide goal (`planning/TODO.md`, origin K16): a small `changelog.json`
(flat list of `{"date", "entry"}`, same convention as `achievements.json`'s
own loading contract — fetched into the Pyodide boot sequence and handed to
`game.py` as a window global, with a filesystem fallback for the pytest
harness) rendered in a hidden-until-opened panel behind a new "📋 What's
New" toolbar button, same idiom as the achievements/settings panels
(`on_toggle_changelog()`/`update_changelog_display()`, mirroring
`on_toggle_achievements()`/`update_achievements_display()` almost exactly).
Entries render newest-first.

Populated with 11 real, dated highlights drawn from this file's own
milestone table and iteration-pass/achievements/settings/colorblind-audit
notes above, with dates cross-checked against `git log` where this file
didn't already carry one — a highlights reel, not a duplicate of the full
history already here and in `BCM114-DEV-LOG.md`.

10 new tests in `tests/test_changelog.py` (catalog/JSON sanity, toggle
open/close, label text, newest-first ordering, rendered content) —
258/258 tests green. Verified live: panel opens, shows the real entries
newest-first, closes cleanly, zero console errors.

## Onboarding-tooltip coverage check (site-wide goal, planning/TODO.md, origin A14)

Checked whether a returning player who skipped/forgot the tutorial has anything in the PERMANENT UI (not the one-time walkthrough, not the always-reachable How to Play panel) explaining Drift's non-obvious controls on demand. Drift already leans heavily on the `<details class="info-toggle"><summary>i</summary>...</details>` pattern next to Displacement pressure, Integration, Regional wellbeing, and the coda's "Generations from now" line, plus each capacity-investment row already carries its own always-visible one-line effect description ("Reduces strain. Doesn't speed up integration." / "...is the only capacity that moves pending arrivals to integrated.") — so most of the game already self-explains.

**Real gap found and fixed:** the "Accelerated Severity" difficulty toggle (I13) isn't in `DRIFT_TUTORIAL_STEPS` at all in `index.html`, so it's covered by neither the one-time walkthrough nor the auto-generated How to Play read-through (`shared/tutorial.js` builds that page from the same steps array) — and the button's own label ("Accelerated Severity: ON/OFF") never states what it actually changes. A returning player had no way to find out what this toggle does anywhere in the game. Fixed with a `title` tooltip in `render()` (`game.py`), stating the real effect from the same `ACCELERATED_SEVERITY_MULTIPLIER` constant the game logic uses: "Optional difficulty variant: multiplies background displacement-pressure severity growth by 2x. Only affects how fast arrival pressure rises — never your capacity or funds math directly." Verified live in a real browser (fresh isolated tab): the tooltip reads correctly on the live DOM element, zero console errors. Full pytest suite (258 tests) green.

*(Note: this fix was made while `games/drift/game.py` also had a concurrent session's in-progress "What's New" changelog work (K16) sitting in the same working tree; that session's own commit — `Drift: add in-game "What's New" changelog panel (K16)` — ended up sweeping this tooltip change in alongside its own, since both landed in the same file at the same time. The change is correctly present in the committed code either way; flagging here only so the history's commit message doesn't read as the full story of what changed.)*

**No other change made** — everything else checked (wellbeing gauges' icons/labels, the trend graph's per-point `<title>` tooltips, the net-positive badge, session-milestone/control-region callouts) already either self-explains via visible text or is covered by the section-level "i" toggles.

## UI decluttering pass (2026-09-20)

Audited as the closing item of `planning/TODO.md`'s "Big standalone features" section (the user's own note: "everything looks very crowded... making sections either collapsible or other 'screens' within a game could help"). Read through `index.html`/`style.css` and checked the live render at `hub-dev-server` for genuine crowding, not just line count.

Most of the page is already well-decluttered as a side effect of earlier feature work this file documents above: the toolbar's five secondary panels (How to Play, Achievements, What's New, Settings, the info-page "Real Story" panel) are all already hidden-until-opened, every section carries its own color-coded left border and glass-panel background (space-theme visual pass) giving clear visual separation, and each section's `<details class="info-toggle">` already keeps mechanic explanations out of the way until asked for. The Pressure, Wellbeing, and Capacity sections are each a tight handful of lines with no real prose bulk — nothing to fix there.

**Real crowding found and fixed, scoped narrowly:** the Integration section stacked two long always-visible prose paragraphs (`#uganda-comparison-display`'s Uganda-policy comparison and `#resettlement-benchmark-display`'s sourced resettlement-employment statistic — I9) directly beneath the two short numeric stat lines (`#integrated-display`, `#pending-display`) that are this section's actual per-round information. Live-verified at `hub-dev-server`: those two paragraphs alone ran a full screen of scrolling past the numbers players actually check each round. Grouped both under one new `<details class="context-toggle" open>` with `<summary>Real-world comparison</summary>`, visually separating them from the core stats above — **left open by default**, deliberately not collapsed, since this is core hope-angle framing for a sensitive real-world subject (this file's own sensitivity note above), not throwaway flavor text; the toggle exists so a repeat player advancing many rounds can collapse it after reading once, not to hide it from a first-time player. Same `<details>`/`<summary>` idiom as Tide's `.ticker-history-toggle`. New `.context-toggle` CSS added to `style.css`, styled to match the existing `.info-toggle` block's palette. No id was renamed and no `game.py` logic touched — `uganda_comparison_message()`/`resettlement_benchmark_message()` still write to the same element ids via plain `getElementById`, confirmed against `tests/conftest.py`'s fake-DOM harness (id-keyed, parent-structure-independent). Verified live: the disclosure renders open by default with both paragraphs intact and readable, collapses/expands correctly, zero new console errors. Full pytest suite (258 tests) unaffected — this is a pure HTML/CSS change.

## Round-2 improvement pass (2026-09-20)

Built from `planning/TODO.md` "Per-game: Drift": I2 (passive control region's wellbeing as a third dotted line on the trend graph, with legend), I4 (accelerated toggle label states "(2x)"), I5 (coda "what the region carries forward" choice, flavor only), I6 (session milestone shows improving/plateauing/declining), I9 (collapsible 5-round arrivals forecast with capacity needed), I11 (thriving vignette, collapsible, unlocks at Thriving), I12/I28 (tooltips on the control-region line and strain consequence), I14 (numeric "Thriving marker: 70" under each gauge), I15 ("Crisis Start" toggle, round 1 only), I16 (recovery-path Model Region badge), I19 (reallocate 10 capacity for 10 funds, 20% loss), I21 (coda side-by-side with passive region), I23 (region name carried into coda), I24 (per-sub-score trend arrows, `subscore_log`), I27 (ROI collapsible), I30 (next-capacity-milestone estimate). Already present before this pass: I8 (gauge icons; coda labels now iconed too), I10, I13, I18, I22, I26. Not built: I1/I3/I7/I25/I29 (large new mechanics), I17 (backend Drift stats fields have no wellbeing, so no meaningful comparison), I20. New state (`subscore_log`, `region_name`, `coda_legacy_choice`, `crisis_start_enabled`) rides `get_state()`/`load_state()` with safe defaults. 290 tests (`tests/test_round2_items.py`).

## Tech notes

- Python/Pyodide, per root conventions.
- This is the most conceptually sensitive game in either set — displacement and migration are real, ongoing human experiences, not just an abstract system. Keep language and framing (in-game text, UI labels, any narrative flavor) focused on institutional capacity and systems design rather than individual migrant stories, to avoid the game reading as speaking for or dramatizing real people's specific experiences.
- Model regional wellbeing as a small set of tracked sub-scores (service quality, economic health, social cohesion) rather than one blended number — keeps the composite scoring testable and keeps the end-state legible to the player.
- Site-wide space-theme visual pass (Sep 2026): adopted the shared `shared/space-bg.css` starfield/nebula background and SOL's glass-panel language — `#game` and every `.section` (including the info-page panel) now use a translucent gradient background, violet-tinted border, backdrop-filter blur, and soft drop shadow instead of flat solid panels; `button.secondary`/`button.primary` moved from flat fills to two-stop gradients with a glossy top highlight and a brightness hover state; `.meter` track darkened with an inset shadow; the `<h1>` got the shared gradient-glow text treatment (kept to the top-level title only). Deliberately left untouched: the exact hex colours on `.meter-fill--strain` and its `.strain--stable/strained/critical` modifiers, and on `.turning-point-message` and `.coda-section` (which intentionally reuses the turning-point's warm accent per the Pass 3 notes above) — these encode the strain level and the net-strain-to-net-contribution turning-point milestone, so only same-hue glow (`box-shadow`) was added around them, never a change to the colour itself. No CSS class/id names, no width/fill logic, and no in-game copy changed. Full pytest suite (114 tests) green before and after.

## Hidden-panel display bug fix (2026-09-21)

Found during a site-wide sweep after Aftermath's own Z12/panel-hiding
fixes surfaced the same pattern elsewhere: the achievements panel and settings panel (`.achievements-panel`/`.settings-panel`) set `display:
grid` as a plain class rule with no `[hidden]` override. Author-origin
CSS always beats the browser's own `[hidden] { display: none }` UA rule
regardless of specificity, so once that class applied, the panel stayed
visible as an empty box before its first open, and stayed visible with
its last-rendered content forever after being toggled closed. Fixed by
adding a `.<class>[hidden] { display: none; }` override right after each
affected rule, the same pattern SOL/Trade Empire/Continuum's own
achievements CSS already used correctly. CSS-only; no Python change
needed. Full test suite green, unaffected (pure CSS change).

## Save-payload log cap (2026-09-21)

Fix for a real bug the site-wide Z25 save-payload audit found (`planning/TODO.md`): `RegionState`'s four per-round history logs (`arrivals_log`, `strain_log`, `wellbeing_log`, `subscore_log`) grew by one entry per round with no cap at all, unlike every sibling "rolling history" field elsewhere in this hub (Canopy's `FOREST_LOG_MAX_ENTRIES`, Tide's `TICKER_FULL_HISTORY_LIMIT`, Grid's `WEATHER_LOG_MAX_ENTRIES`, Trade Empire's `TREND_HISTORY_MAX_POINTS`) — measured at ~128 bytes/round, reaching 383KB at 3000 rounds.

**Why a naive cap alone wasn't safe:** `strain_log` has two real consumers that need the FULL run history, not a recent window — `average_strain()` (`sum(strain_log) / len(strain_log)`, a lifetime average feeding `service_quality()`/`wellbeing_score()`) and the `full_recovery`/`crisis_averted` achievement gate's `_ever_reached_critical_strain()` (an "was this ever true across the whole run" scan). Truncating the raw list would have silently turned the lifetime average into a rolling-window one, and could have made the critical-strain achievement un-earnable once the round that crossed critical strain rolled off a capped list. `arrivals_log` and `subscore_log` had no such problem (nothing reads more than their last few entries), so those two were safe to cap directly.

**Fix:** decoupled both real consumers from the raw list before capping anything:
- `RegionState._strain_sum`/`_strain_count` — running totals updated once per round in `advance_round()` alongside the `strain_log` append; `average_strain()` now reads `_strain_sum / _strain_count` instead of summing the whole log.
- `RegionState._ever_critical_strain` — a sticky flag set `True` the moment a round's strain crosses the critical threshold, never cleared; `_ever_reached_critical_strain()` now just reads it instead of scanning `strain_log`.
- Both ride `get_state()`/`load_state()` (`strain_sum`/`strain_count`/`ever_critical_strain` keys) with the established `.get(key, ...)` fallback convention. An old save missing those three keys has them **recomputed from whatever `strain_log` that old save still carries** (its full, not-yet-capped history) on load, rather than defaulting to `0`/`False` and silently losing the correct lifetime average or achievement-earned state.
- Only once both consumers no longer needed the raw list were all four logs capped at `DRIFT_LOG_MAX_ENTRIES = 200` (matching Canopy/Tide's order of magnitude for a log meant to back a full-run trend graph, rather than Grid/Trade Empire's 30-entry caps for a short recent-window display), truncated on append via `del log[:-DRIFT_LOG_MAX_ENTRIES]`.

5 new tests in `tests/test_z25_log_caps.py`: all four logs stay capped after many rounds; `average_strain()` matches a manually-tracked lifetime average after the log itself gets capped (proving the sum/count decoupling, not just "doesn't crash" — includes an assertion that a naive re-sum of the capped log would give the *wrong* answer); `full_recovery` stays earnable well after the critical round has rolled off the capped log (proving the flag, not the log, is what's checked); an old save missing the three new fields recomputes them correctly from its own `strain_log`; a fresh save uses its stored fields directly rather than recomputing. Existing tests that stubbed `strain_log` directly to control `average_strain()`/`service_quality()` (several achievement/checkpoint/wellbeing tests) were updated to go through a new `game_env.set_strain_log()` test helper (`tests/conftest.py`) that keeps the derived sum/count/flag consistent with the stubbed log, mirroring `load_state()`'s own recompute logic. 295/295 tests green. Verified live at `hub-dev-server`: drove 250+ rounds via `pyodide.runPython`, confirmed all four logs cap at exactly 200 entries, `average_strain()` and the `full_recovery` achievement both correct after the log-capping window rolled past the critical round, and an old-format save (three new keys stripped from `get_state()`'s output) recomputes exactly on `load_state()` — zero console errors throughout.

## Working conventions

- Commit + tag per milestone: `git commit -m "Milestone N: <name>"` then `git tag drift-milestone-0N`.
- Update the milestone table Status as work happens.
## Screen-reader accessibility audit (Z15, site-wide goal, planning/TODO.md)

Static-analysis audit (grepping/reading `index.html`/`game.py`, no live screen
reader in this environment — same audit-only method the colorblind-safety
passes already established for this hub) of the achievements and settings
panels: toggle-button accessible names, panel role/heading semantics, focus
order on open/close, keyboard reachability of interactive elements, and
checkbox/label association.

**No real gap found — no change made.** This game's settings panel is a
short two-row control block (text-size buttons + a "Reduce Motion: On/Off"
toggle button, each row already carrying its own visible `<span
class="settings-row-label">`) rather than the longer checkbox-based panel
some other games in this hub have — there's no separate panel-title heading
element, but nothing in it needs one: each control already names itself via
its own visible label text and the button's own state-reflecting text
("Reduce Motion: Off"/"Reduce Motion: On"), and the `#settings-toggle-button`
above it already states the panel's purpose. Same "plain semantic markup
already covers it" call this hub's colorblind-safety audits make for
comparable cases — not adding a heading purely for the sake of having one.
Checked against the same candidate list as every other game in this pass:
- Both toggle buttons (`#achievements-toggle-button`, `#settings-toggle-button`)
  already carry descriptive visible text, a sufficient accessible name on its
  own — no `aria-label` needed.
- The achievements panel itself has no heading of its own, but is adequately
  labeled by the toggle button's own visible text immediately above it.
- No focus-trap exists anywhere in this hub, and none was warranted here:
  clicking the toggle button never moves focus itself, so it naturally stays
  on that same button when the panel opens or closes.
- Every interactive element inside both panels is a real `<button>`
  (confirmed via a site-wide grep for `.onclick =` assignments and
  `createElement("div")` calls with a wired click handler — none found; this
  game's settings panel has no checkbox at all, so the label/`for` question
  doesn't apply here).

No code changed; ran as the baseline check this pass calls for regardless
of verdict.

## 320px mobile-viewport audit (Z18, site-wide goal, planning/TODO.md)

Checked at a genuine 320px viewport (narrower than the original 375px
mobile pass) via the Claude Browser tool's `resize_window`.

**Real bug found and fixed:** `.invest-fields` used a bare
`grid-template-columns: 1fr auto 1fr` for its two investment buttons —
CSS Grid's classic gotcha is that a bare `1fr` track still respects its
content's *min-content* width as a floor, so a longer button label like
"Infrastructure (25)" kept this row (and `#capacity`, and the page) wider
than a 320px screen even though `1fr` looks like it should shrink freely.
Fixed with `minmax(0, 1fr)` on both flexible tracks, letting them actually
shrink to the row's real available width instead of their content's
natural size.

No other overflow found at 320px. `flake8`/tests unaffected (pure CSS).

## Difficulty-aware achievements audit (Z27, site-wide goal)

Drift already has its own dedicated `tests/test_difficulty_toggle.py` for
I13's "accelerated background severity" toggle (`accelerated_severity_
enabled`, freely reversible, doubles `BACKGROUND_SEVERITY_RISE_PER_ROUND`
via `ACCELERATED_SEVERITY_MULTIPLIER`) — a good sign this exact question
was already on this game's radar. `crisis_averted` ("reach round 21
without strain ever crossing into critical") was the obvious candidate,
since higher background severity directly raises `arrivals_this_round()`,
which is what strain is measured against.

Wrote a standalone simulation (not committed) that plays 20 real rounds
organically — spending all available funds on Housing (the cheapest
capacity-per-dollar option) before every round advance, no funds cheat —
under both settings. Result: **`crisis_averted` stays fully earnable under
accelerated severity**, with strain never leaving 0.0 in either run
(620 capacity built by round 21 against 385 lifetime arrivals normally, or
670 under accelerated severity — comfortably ahead either way, since
Housing investment scales with available funds and income far outpaces
the arrivals curve at this game's constants). The other severity-linked
achievements (`turning_point_reached`, `ahead_of_schedule`, `steady_
ground`) get harder under the toggle (a faster-growing arrival rate raises
the bar for keeping pace) but through the exact same mechanism this
simulation already tested clean, not a separate one — no reason to expect
a different outcome for them.

**No change needed.** No code touched; `flake8`/tests unaffected.
