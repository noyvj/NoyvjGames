# Notes for drift: the long history

This is the long history moved out of CLAUDE.md on 2026-10-18 (every section below is verbatim, in its original order). Read one section at a time: grep its `## ` headings and read only the one you are told to, never the whole file.

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

## Reset-to-default settings button (Z-extra/A26, site-wide goal)

A "Reset to Default" button (`#settings-reset-button`) sits at the bottom of the settings panel, below the existing text-size and reduce-motion controls -- SOL's own A26 answer flagged this as a site-wide pattern rather than a SOL-only feature, folded into `planning/TODO.md`'s Z-extra checklist. Implemented entirely in `settings.js` (no Python touched): one click calls `applyScale(DEFAULT_SCALE)` and `applyMotion(false)`, updates `--text-scale`/`data-text-scale` and the `.reduce-motion` class on `<html>` immediately, refreshes the Reduce Motion button's own label/active state via `updateMotionLabel()`, and writes both defaults back to `localStorage` so the reset survives a reload. No confirmation dialog -- this is a low-stakes, instantly-reversible display preference, not a destructive action, so `shared/confirm-dialog.js` is deliberately not wired up here.

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

## Tech notes (the Sep 2026 space-theme visual pass bullet, moved out of CLAUDE.md's Tech notes)

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
`localStorage["whats-new-seen:drift"]` (the date string of the newest
entry already shown) and lists just the new ones, not the whole log. A
first-ever visit silently marks the current changelog as seen rather
than dumping the full history on a brand-new player. Reuses the same
`window.CHANGELOG_JSON` global this game's own changelog panel already
fetches -- no second network request. One `<script
src="../../shared/whats-new-banner.js" data-game-id="drift">` include,
added right after `shared/last-played.js`'s own include. See root
`CLAUDE.md`'s Working notes for the full write-up -- shared
infrastructure, documented once there rather than duplicated across all
12 games' own files.

## Keyboard-shortcut convention: ?/Esc (Z4, site-wide goal)

Wired via the new shared `shared/keyboard-shortcuts.js` -- one script
include plus one `KeyboardShortcuts.init({panels: [...]})` call at the
end of `index.html`, listing this game's real toggle-button + hidden-
panel pairs: How to Play, Achievements, What's New, Settings, the Info
Page, and the Long-Horizon Outcomes coda (`coda-button`/`coda-section`).
`?` opens a small floating shortcuts-help overlay; `Esc` closes it and
clicks the toggle button of whichever listed panel is currently open,
reusing each panel's own open/close logic. The Accelerated Severity /
Crisis Start difficulty toggles aren't in the list -- they're on/off
flags with no corresponding panel.

## I20: one-time callout for the arrival-dot density change (2026-09-22)

`planning/TODO.md`'s I20: "a one-time callout the first time the
arrival-dot stream's density visibly changes due to a difficulty
toggle." The real design question was what "due to" should mean, since
severity (and so the dot stream) already climbs on its own every round
regardless of the Accelerated Severity toggle -- a naive "did the dot
count change since I flipped the toggle" would misattribute ordinary
background growth to the toggle.

Resolved by making attribution structural rather than inferred: the
toggle handler (`on_toggle_accelerated_severity()`) captures a baseline
-- the dot count at the exact moment the toggle is first switched on --
into `RegionState.severity_toggle_dot_baseline`, and *only* the first
time it's ever switched on (turning it off and back on later never
recaptures it). Until that baseline exists, `severity_toggle_dot_
baseline` stays `None` and the callout can never fire, so a player who
never touches the toggle never sees it, no matter how much the stream
changes on its own. `maybe_flag_severity_density_change()` (called from
`render()` right after the existing I16 dot-stream update) sets the
one-time `severity_density_callout_shown` flag the first render where
the live dot count no longer matches that baseline -- both fields are
permanent once set, same "recorded once, stays true" shape `thriving_
round`/`net_positive_round` already use elsewhere in this file.

Rendered as `#severity-density-callout` (`index.html`, right under the
arrival-dot stream), reusing the `.turning-point-message` warm-accent
box style with its own `👁️` icon rather than the turning-point's `🌅`.
Both new fields ride `get_state()`/`load_state()` with safe `None`/
`False` defaults for old saves.

Tests: 295 -> 303 (`tests/test_difficulty_toggle.py`: baseline captured
only on the on-transition, never re-captured on a later toggle, never
set at all without ever toggling, callout stays hidden until the
density genuinely moves, fires exactly once and stays shown afterward,
never fires without a baseline even after 20 rounds of natural growth,
and a full save/load round-trip including an old-save-missing-keys
case). `flake8` clean. Verified live under Pyodide (`hub-dev-server`):
toggling on captured baseline 2, advancing 6 rounds moved the dot count
to 5 and the callout appeared with the exact expected text, styled
correctly, zero console errors.

## Policy toolkit (I3, 2026-09-26)

Three named, real-world-grounded institutional levers beside the abstract housing/services/infrastructure split (`POLICIES`, `POLICY_BASE_COST` 60 times the next level, `POLICY_MAX_LEVEL` 3): **Streamlined Credentialing** (+15% per level on the funds integrated people contribute back, via `integration_contribution()`), **Language-Access Funding** (+15% per level on integration throughput, via `integration_this_round()`), and **Community Sponsorship** (+6 effective capacity per level against strain, via `strain_fraction()`, which can never go below zero). Small, permanent and specific; capacity investments are untouched. `RegionState.policy_level`, `policy_effect()`, `policy_cost()`, `invest_policy()`; three buttons show level, next cost or 'Maxed'. Save: `policy_level` only when any level is above zero, validated per policy (int 0..3, unknown keys ignored). 303 -> 316 tests (`tests/test_policies.py`); verified live.

## Cross-region learning (I29, 2026-09-26)

Reaching Thriving once teaches something that carries over: every region that BEGINS afterwards gets `LEARNING_INTEGRATION_BONUS` (+10%) integration throughput, permanently. The unlock flag lives per browser in localStorage (`drift_cross_region_learning_v1`, like the personal best, deliberately not in a save code) and is read at startup by `_load_cross_region_learning()` (tolerates missing, blocked or throwing storage). It is applied only to regions that start after the unlock (`RegionState.learning_active`, fixed at creation), so the region that earned it doesn't double-dip; a loaded region keeps whatever it began with (`learning_active` saved only when true). The bonus adds to the Language-Access policy rather than multiplying it. A status line under the personal best explains the three states (locked, just unlocked for future regions, active here). 316 -> 329 tests (`tests/test_cross_region_learning.py`); verified live (the flag persisted and the earning region stayed unboosted).

## Second wave (I25, 2026-09-26)

After round `SECOND_WAVE_MIN_ROUND` (10) with at least `SECOND_WAVE_TRIGGER_INTEGRATION` (70%) of arrivals integrated, a second, larger wave arrives once per region: `second_wave_status` runs None, 'warned' (announced the round before), 'active' (`SECOND_WAVE_ROUNDS` 5 rounds at `SECOND_WAVE_ARRIVALS_MULTIPLIER` 2.0 times the arrivals via `arrivals_this_round()`), then 'done' with a verdict: 'held' if strain never reached the critical band while it was active, else 'strained'. It is a test of what you built, not a punishment (no fail state, arrivals go back to normal). A status line shows the warning, the countdown with the worst strain so far, and the verdict. Save: `second_wave` written only once started; on load the status must be one of warned/active/done, rounds left is an int 0..5, peak strain a finite number 0..1, and a 'done' result is held or strained (anything else loads as strained). 329 -> 342 tests (`tests/test_second_wave.py`); verified live (warning, five-round countdown, 'held' verdict).

## Neighbouring district (I1 + I7, 2026-09-26)
A second `RegionState` (`neighbor`, module-level, None until opened) built by `_new_neighbor_region()`: `NEIGHBOR_START_HOUSING` 30, no services, `NEIGHBOR_START_FUNDS` 100, `NEIGHBOR_START_ARRIVALS` 20, `NEIGHBOR_START_SEVERITY` 3.0; its second wave and cross-region learning are switched off so it stays a simple second dial. Opens from round `NEIGHBOR_MIN_ROUND` (3). `on_advance_round()` advances both; the neighbour invests only from its own funds (`invest_neighbor`). I7: `support_neighbor()` moves `NEIGHBOR_SUPPORT_AMOUNT` (40) main funds to the neighbour, allowed only while `main_region_well_prepared()` (main strain below 'strained' and funds >= amount + `NEIGHBOR_SUPPORT_RESERVE` 60). The reason to help: a neighbour in critical strain gives the main region `spillover_arrivals` (+4/round, derived by `_sync_spillover()` each render/advance, never saved). Save key `neighbor` written only once opened; `_load_neighbor()` validates every field (finite non-negative numbers, integrated <= arrivals, strain_sum <= count). Tests: `tests/test_neighbor_region.py` (12).

## Community capacity index (I17, 2026-09-26)
`get_state()` gains a write-only `wellbeing_score` (never read back; ignored on load, pinned in `tests/test_save_system.py` and `tests/test_community_index_field.py`), whitelisted in `app/stats.py`. A `shared/community-index.js` line above the neighbouring-district panel shows mean and median across players (hidden until enough saves exist).

## Story mode: A Region Prepares (W1-drift, 2026-09-26)
Third user of the shared `shared/story-chapters.js` (site-wide W1). `story.json` holds 19 short authored chapters (an opening "begin" plus one per achievement in `achievements.json`, ordered from first investment to a model region; a test pins that every achievement has a chapter). Tone matches the vignettes and coda: institutional, hopeful and dignified, newcomers written as people with skills and plans rather than numbers, hardship (strain, recovery) acknowledged without being trivialised, no invented statistics. `_story_reach_all()` calls `window.NoyvjStory.reach(id)` for the opening and every earned achievement from `_check_new_achievements_for_toast()` and `_seed_achievement_toast_baseline()` (so a loaded save brings its chapters back); idempotent, silent without the script, adds nothing to the save. `story-toggle.js`'s existing `data-story-selectors` gained `#story-chapters`, so the Story pill hides the panel along with the thriving vignette. Progress is per-browser localStorage. Tests: `tests/test_story_chapters.py` (9; 356 -> 365). No number, unlock or save key changes.

## In the real world (W2-drift, 2026-09-27)

A collapsible "In the real world" `<details id="real-world-note">` (inside the Real-world comparison section, below the existing Uganda and I9 benchmark lines) shows one sourced real example, chosen deterministically by `real_world_topic()` (no RNG) and rendered by `render_real_world()`. It changes no number and adds no save state. Kept institutional and neutral (programmes, laws, documented figures; no individual stories, no advocacy). Priority: a warned/active second wave -> `surge`; any strain above stable -> `services_strain`; else the funded policies (`language_access`, `credentialing`, `sponsorship`) rotate by `region.round_number`; else all six rotate by round. Every fact below was read with a live fetch on 2026-09-27 (nothing recalled from memory); the source line reads "Source: <name> (read 2026-09-27)" and links with `target=_blank rel="noopener noreferrer"`. Tests: `tests/test_real_world.py`.

| Topic | Mechanic | Source and URL |
|-------|----------|----------------|
| `settlement` | housing / settlement | Wikipedia, Refugees in Uganda (2006 Refugee Act, 30 by 30 m plots, ~1.95 million refugees by October 2025, implementation gaps noted) - https://en.wikipedia.org/wiki/Refugees_in_Uganda |
| `language_access` | Language-Access Funding | Wikipedia, Integration course (Germany: 2005, 600 h language + 100 h orientation, 94,020 starters 2012, 142,439 in 2014, 53% pass-rate evaluation) - https://en.wikipedia.org/wiki/Integration_course |
| `credentialing` | Streamlined Credentialing | BAMF, Recognition of foreign professional qualifications (no residence permit needed, normally within three months if documents complete) - https://www.bamf.de/EN/Themen/Integration/ZugewanderteTeilnehmende/AnerkennungBerufsabschluesse/anerkennungberufsabschluesse-node.html |
| `sponsorship` | Community Sponsorship | Wikipedia, Private Sponsorship of Refugees Program (Canada: 1978, one year of support, nearly 300,000 resettled since 1979 as of January 2020) - https://en.wikipedia.org/wiki/Private_Sponsorship_of_Refugees_Program |
| `surge` | second wave | Wikipedia, Temporary Protection Directive (invoked 3 March 2022; residence permit, work, social welfare, schooling; up to three years) - https://en.wikipedia.org/wiki/Temporary_Protection_Directive |
| `services_strain` | strain above stable | Wikipedia, Syrian refugees in Jordan (630,776 registered as of November 2015; pressure on water, sanitation, housing, energy) - https://en.wikipedia.org/wiki/Syrian_refugees_in_Jordan |

## Desktop boot (PC version, 2026-10-07)

`games/drift/pc.html` is the Desktop boot: the same game over the same `game.py` and saves (same `game_id`), laid out for wide windows. **Never edit it by hand**: it is generated from `index.html` plus `pc-config.json` by `scripts/generate-pc-pages.py`. Per-game files: `pc-config.json` (what moves where), `pc.css` (layout, all under the pc layout), `pc.js` (`window.DRIFT_PC_TUTORIAL_STEPS`, which `index.html` uses when present, plus two small fixes described below). `index.html` gained only the `layout-pref.js` tag and the `DRIFT_PC_TUTORIAL_STEPS ||` fallback. `game.py` is untouched; `MobileHud` still runs but is hidden by `pc.css`.

- **Layout.** No page scroll. Top bar: back link, title, three icon buttons (Achievements, How to Play, Settings), the Menu (Esc) and the Story pill. Under it chips (round, funds, total capacity, strain, pending integration, wellbeing score) built by the shell from the original lines, which keep updating by id (round, funds and capacity sit in the shell's hidden zone). Stage: the region skyline as a banner over three columns that each scroll on their own, displacement pressure with the status block (personal best, learning, second wave, the net-positive and recovery badges, next milestone, region name) under it, integration, and regional wellbeing with the trend graph; then the hotkey hint bar. Right column (scrolls on its own): Advance Round pinned at the top, the Long-Horizon Outcomes button (hidden until available), capacity investments with the policy toolkit, the neighbouring district and the reallocate and ROI tools.
- **Windows.** How to Play, Achievements, What's New, Settings, The Real Story and Long-Horizon Outcomes (the coda section as a window, opened by its own button) plus composites About Drift (tagline, context blurb, community index) and Feedback from the Menu. The Menu also holds the Accelerated Severity and Crisis Start toggles and the tutorial.
- **Tutorial.** `pc.js` sets 9 steps (chips, pressure, integration, wellbeing, investments, Advance Round, icons and Menu); every selector exists on `pc.html`.
- **Notifications and hotkeys.** `notify` is null (Drift has no log list; its toasts are the achievement toast and the Story panel). The only real hotkeys are `?` and Esc, so the hint bar lists those.
- **Layout notes.** `pc.css` clears the ad-bar body padding, clips the ambient blobs, moves the floating theme toggle to the top-right, keeps skyline buildings at a fixed width and centred, and at 1280px wide or less narrows the side column; at 780px tall or less the skyline banner shrinks. `shared/story-chapters.js` inserts its Story panel after the h1, which can land before or after the shell moves the h1 into the top bar; `pc.js` moves it into the top bar either way.
- **Known limits.** At 1024x700 the three stage columns and the side column scroll inside themselves; the `?` overlay is the shared one, not a shell window; the Long-Horizon Outcomes button stays in the side column behind the window while it is open; scripted play only (about 30 rounds, dark and light), no full human playthrough.

## Round-3 batch (2026-10-07): ledger, undo, collection, keys, display options

Built from `planning/TODO.md` "GI + I. Drift": I-8, I-17, I-15, GI-18, GI-30, GI-15, GI-22, I-13, I-20, I-24. No rule or number in a run changed (the ledger and collection only record, undo only restores, Play 5 rounds is five ordinary Advance Rounds). New JS file: `ui.js` (game keys; loaded by both pages, listed for the service worker). 373 -> 438 tests (`tests/test_round3_oct7.py`).

- **Round Ledger and recap (I-8, I-17).** `RegionState.ledger` gets one row per resolved round (`LEDGER_FIELDS`: round, income, spent, spend split housing/services/infrastructure/policy/realloc, arrivals, newly integrated, integrated, pending, shortfall beyond capacity, end-of-round strain, the three sub-scores, wellbeing, funds, auto flag), capped at `LEDGER_MAX_ENTRIES` (120). `ledger_rows(sort, filter)` powers the panel's two selects (`LEDGER_SORTS`, `LEDGER_FILTERS`), `ledger_csv()` the Copy as CSV button (clipboard, else a read-only text box). `round_recap_message()` fills the collapsible "Last round recap" under Round tools. Spending is tracked in `spend_by_type` (lifetime) and `round_spend` (this round), recorded in one place, `RegionState._record_spend()`. Save keys `ledger` (rows as plain lists in field order), `spend_by_type`, `round_spend`, each written only once non-empty and validated on load (bad rows skipped, non-lists load empty).
- **Reset this round (I-15).** `reset_round()` restores funds, capacity, policy levels, services-spend total, spend splits and the neighbouring district (its funds, capacity and the support sent) to the snapshot taken when the round began (`round_start_snapshot`: after each Advance, load, Play 5 rounds, or Crisis Start toggle). `region.round_buys` counts decisions since then (transient, never saved) and enables the button. Opening the neighbour is not a decision.
- **Rewind Token (GI-18).** One per region. `rewind_snapshot` is a deep copy of the region and neighbour taken just before every Advance Round (including each round of Play 5 rounds); using the token restores it (so purchases made before pressing Advance come back with it) and records `rewind_used_round`. It takes two clicks (first arms, "Confirm: undo the last Advance Round"; any other action disarms). The used marker rides the save (`rewind_used_round`, int >= 1 else unused); the snapshot itself is never saved, so a loaded save has nothing to rewind.
- **Play 5 rounds (GI-30).** `play_rounds()` advances up to five rounds with no purchases, flagged `auto` in the ledger, and stops after the round in which strain moves up a level, the second wave is announced/arrives/ends, or the neighbouring district goes critical and starts sending people. A note under the button says how many rounds ran and why it stopped.
- **Region Collection (GI-15, GI-22).** Ten civic milestones (`CIVIC_MILESTONES`, each with a locked hint, a one-line description once found, and a test of region state plus the round just completed; "by round N" means that round or earlier) and five personality titles (`REGION_TITLES`: Builder, Educator, Engineer, Reformer, Balancer, fitted by the lifetime spending split once at least 100 funds are spent, collected from round 8). Both are cosmetic, found at the end of an Advance Round or a Play 5 rounds step, shown with a toast and a "New in your collection" note, and kept per browser (`drift_collection_v1` in localStorage, like the personal best) so they accumulate across regions; the collection also rides every save (`collection`) and merges into the browser's on load. A test plays a scripted region that reaches every milestone, so no hint is a lie. Panel: `#collection-panel`; the status block shows the count and the current personality.
- **Game keys (I-13).** `ui.js`: 1/2/3 buy Housing/Services/Infrastructure, Enter Advance Round (bare page only), U Reset this round, P Play 5 rounds, L Ledger, C Collection. They are in the shared `?` overlay (`extra`) and the Desktop hint bar; on the Desktop page the turn keys stay off while a window is open.
- **Display options (I-20, I-24).** `settings.js` adds High Contrast and Easy-Read Font toggles (`html.high-contrast`, `html.easy-read-font`, localStorage `drift-high-contrast` / `drift-easy-read-font`, both included in Reset to Default; CSS at the end of `style.css`, dark and light). The tab title reads "Drift - R37 - Stable - Region Name" and updates every render.
- **Desktop.** New windows Round Ledger and Region Collection (Menu > Records and the L / C keys), `#round-tools` in the side column under the capacity investments, hint bar lists the keys, tutorial gained a Round tools step.

- **Oct 8 wiring (Z-20, Z-27, Y-7, Y-8, Y-29):** `share_result()` in `game.py` returns the Copy result figures as JSON (wellbeing, projected wellbeing, people integrated, rounds); the shared `NoyvjCopyResult` button sits in the long-horizon outcomes section (`#result-copy`, the game's end-of-run view; reads Python through `window.pyodide.globals.get("share_result")`). `shared/achievement-share.js` adds Share to earned achievement cards. The Open Graph block and JSON-LD sit in `<head>` before the shared includes; a `#credits-link` anchor sits above the ad bar (in the Desktop Help menu via `pc-config.json`). Tests: `tests/test_wiring_oct8.py`.

## Round-3 batch 2 (2026-10-08): Perfect Fit, Crisis Calendar, Council, Autopilot, stars, summary

Built from `planning/TODO.md` "GI + I. Drift": GI-13, GI-2, GI-11, GI-1, GI-5, GI-21, I-18. Everything is fixed and visible (no cards, no randomness). A run that never opens the new panel plays exactly as before: the baseline numbers are unchanged (the old 451 tests passed untouched; 451 -> 509 with `tests/test_round3_oct8b.py`). New panel `#civic-tools` (Crisis Calendar, Mayor's Council, Budget Autopilot as three `<details>`), in the Desktop side column; a Perfect Fit line beside the forecast; a run-stars line in the status block; a Copy run summary button in Round tools. No new JS file, no new asset.

- **Perfect Fit streak (GI-13).** `RegionState.is_perfect_fit()`: capacity plus coverage covers everyone who has arrived with at most `PERFECT_FIT_MARGIN` (12) to spare, and something is built. Judged each Advance Round on the same standing the strain uses; each consecutive round adds `PERFECT_FIT_FUNDS_PER_STREAK` (3) funds of income, streak counted up to 5 (so +15 at most), which lifts economic health. `perfect_fit_message()` also says whether you hold one right now. Save key `perfect_fit` {streak, best}, written once a streak existed.
- **Crisis Calendar and Surge Tests (GI-2, GI-11).** Opt-in toggle (`calendar_enabled`, off by default, like Accelerated Severity, so records stay as they were). Fixed table: from round 8 every 4 rounds through round 100 the kind cycles bumper harvest (+40 income), arrivals surge (x1.4 arrivals that round), budget cut (income x0.7), flood (-12 infrastructure); rounds 25, 50 and 75 are named Surge Tests ("The Long Queue", "The Winter Crossing", "The Great Intake", x1.8 arrivals, scaled to the severity curve). `calendar_event_for_round()` is the single source of the schedule. The preview shows "This round" and "Next round" from the round before; paying `brace_cost` (25, 20, 25, 40) in the preview or event round softens it (x1.2 / x0.9 / -4 infrastructure / x1.5). A boss round that capacity covers shows the "Held the line" card, one that does not says plainly that nothing is lost for good. `_run_auto_rounds()` (shared by Play 5 rounds and the Autopilot) refuses to start a round whose braceable event is unbraced and stops when one is next round. The unmanaged control region meets the same events, unbraced. Brace costs are not counted in the spend split (so they do not skew titles) but do count as a decision for Reset this round, which refunds them (`braced_rounds` is in the round-start snapshot). Save key `calendar` {enabled, braced, log} (bad entries dropped).
- **Mayor's Council (GI-1).** After every `COUNCIL_INTERVAL` (10) completed rounds one pick opens, never forced. Three branches (Learning, Housing, Transit) of three tiers; a pick deepens one branch by its next tier, so it is a pick-one-of-three tree with all nine programs listed up front (`COUNCIL_PROGRAMS`: effect plus a trade-off each, among throughput, contribution, coverage and income). Effects flow through `program_effect()`; coverage joins sponsorship in `coverage_bonus()` (strain and the ledger shortfall use it). Capacity costs are untouched. Save key `council` (a list of ids; a load keeps a pick only if it is the next tier of its branch, so a hand-edited save cannot skip tiers).
- **Budget Autopilot (GI-5).** Standing rules (`region.autopilot`: keep services at a share of capacity, spend the surplus on one type or hold it, a reserve, 5/10/25 rounds), `autopilot_run()` buys by the rules then advances each round as an ordinary automatic round (ledger flag `auto`, rewindable one round at a time, never gates an achievement), stops early like Play 5 rounds (strain up a level, second wave, spillover, calendar), and writes a visible rule log (`autopilot_log`, last 12 shown, not saved). Stands in for fast-forward (GI-5 and GI-30 are the same need in a turn-based game). Save key `autopilot` only when not the default.
- **Stars (GI-21).** `star_goals()`: wellbeing 50/70/90, net-positive by round 16/10/7, funds efficiency (integration paid back per fund invested) 2/4/8. Shown live in the status block; banked once into a per-browser run history (`drift_run_stars_v1`, last 12) when round 50 finishes (`stars_banked` rides the save; a token stops a rewind from banking twice). The Collection panel lists the best five star combinations. Thresholds were set from scripted runs (a passive run earns 0, a careful one 2 to 3).
- **Copy run summary (I-18).** `run_summary_text()`: region name, rounds played, band (Struggling/Managing/Thriving/Model Region), wellbeing, strain, a 30-character block curve of `wellbeing_log`, setup tags (the toggles and chosen council programs stand in for a tier until named tiers exist) and stars. Clipboard, else a read-only text box.
- **Skipped on purpose:** GI-8 (District Planner, needs the level-select shared piece and is a separate mode), GI-9/GI-27/GI-28 (Legacy, need the skill tree), GI-4 (needs level select).

## Screen-reader announcements (B-7, 2026-10-11)

Drift now speaks through the shared announcer (`shared/announcer.js`, `<script>` placed before `last-played.js` in `index.html`; `pc.html` regenerated). `game.py` keeps `_shared_announce(text)` (shared announcer when the page has it, otherwise the game's own `#sr-announcer` live region, never both, Tide's pattern) and `announce(text)`, which also strips emoji so their names are not read aloud.

- **What is announced** (player actions and round results only, never from `render()`): an investment (new capacity, total capacity, funds, strain) or why it was refused; a policy funded (level of 3) or maxed/too dear; Move capacity (`reallocate`) or why not; Brace or why not; every Advance Round via `round_announcement_text(marks_before)` (the same recap line the Round recap panel shows from `latest_recap()`, a Crisis Calendar result, a second wave only when its status changed, the net-positive turning point and the thriving milestone only the round they happen, then "Round N begins" with arrivals, funds, strain and wellbeing); Play 5 rounds and the Budget Autopilot (their note, then the last round's announcement); Reset this round and Rewind (including the confirm prompt); neighbouring district open/invest/support; an achievement unlock.
- **No double reading.** `#round-tools-note` and `#calendar-note` lost their `role="status" aria-live` because the announcer now says what they show. `#council-status` and `#ledger-copy-status` keep theirs (the council pick note is not announced separately).
- **Keyboard.** Drift has no tile map: the controls are the Invest/Fund buttons in each `.invest-row`, native and reached with Tab. No arrow-key cursor was added. Capacity and policy rows are now `role="group" aria-labelledby="<name id>"`, and `style.css` gives them and Advance Round a thick yellow `:focus-visible` ring.
- Tests: `tests/test_shared_announcer.py` (19).

## Round-4 batch (2026-10-11)

Built from `planning/TODO.md` "GI + I. Drift" (all code-drawn, no images; FY-40/FY-41 said yes to code-drawn skins, pop-ups and glyphs). No rule or number in a run changed unless an item below says so. Tests are in `tests/test_round4_*.py`.

- **Building pop (GI-14).** `_pop_building()` runs after each successful capacity investment (not for policies, the Autopilot or Play 5 rounds): `building_to_pop()` picks the skyline building (a just-revealed one first, otherwise the pops take turns), `_pulse()` adds `building-pop-a` or `building-pop-b` (two identical keyframe sets so a quick second purchase restarts the animation) for `BUILDING_POP_MS`. CSS uses the individual `translate` property so it composes with the inline `scaleY`, and a `::after` dust puff; Reduce Motion, the OS setting and Animation speed Off stop it. Critical strain keeps its flicker alongside the pop.
- **Strain heartbeat (GI-19).** `strain_heartbeat_seconds(level)` (6.0 / 2.6 / 1.2 s for stable / strained / critical); `render()` puts `strain-heartbeat` on `#strain-bar` and `strain-heartbeat-text` on `#strain-display` with that duration. Brightness and a text glow only (no opacity drop, never more than two soft beats per 1.2 s).
- **Animation speed and density (I-21, I-19).** `settings.js` adds two button groups to the Settings panel (`#anim-speed-group`: Slow/Normal/Fast/Off, `#density-group`: Comfortable/Compact), per-browser in localStorage (`drift-anim-speed`, `drift-density`, unknown values fall back), set on `<html>` as `data-anim-speed`, `--drift-anim-scale` (2 / 1 / 0.5) and `data-density`; Reset to Default restores both. `scaled_seconds(s)` in `game.py` writes durations as `calc(Ns * var(--drift-anim-scale, 1))`, so the dot stream, pop and heartbeat all follow the setting instantly with no re-render. Off sets `animation: none` on those three and is independent of Reduce Motion.
- **Readouts (I-22, I-23, I-26).** `#hud-round-display` ("R7 💰 418"), `#hud-strain-display` ("0% stable") and `#hud-wellbeing-display` ("72 Thriving", band from `wellbeing_band()`) are hidden spans that `shared/mobile-hud.js` mirrors into the phone's sticky bar (three chips, labels Strain and Wellbeing; sized to fit exactly 360px, so keep the strings short). `pending_age_bands()` splits the pending people into the latest round, the two rounds before it and the rest from `arrivals_log`, as if the longest-waiting are integrated first (an honest presentation of a count, not a per-person model); `#pending-pipeline` draws three width-proportional segments (three lightness steps, the oldest striped) and `#pending-pipeline-text` carries the numbers. `sparkline_svg()` draws the last 20 rounds of a sub-score on the fixed 0-100 scale into `#service-quality-spark` and its two siblings. Nothing here is saved. Tests: `tests/test_round4_readouts.py`.
- **Trend graph layers, events, range and crosshair (I-12, I-16).** `trend_graph_svg()` keeps its old three positional arguments and default drawing, and gains `first_round`, `layers`, `events`, `roi_history` and `view_rounds`; the viewBox now starts 10 units above the lines for a strip of event markers. `trend_events(region)` derives the events from state already kept (wellbeing log band changes, `net_positive_round`, the strain peak, ledger rows with a move, and the new `second_wave_start_round`). Each kind has its own outline (diamond, triangle, square, cross, pennant) so it reads without colour; each also appears in its round's tooltip. A new per-round `roi_log` (integration paid back per fund invested; capped, right-aligned against the other logs when an older save has fewer entries, scaled to at least 0-8 or its own peak) feeds the ROI layer. Saves: `roi_log` only once non-empty (validated: finite numbers, junk dropped, negatives to 0, at most 200), and `second_wave.start_round` only once known (int >= 1). The chosen range and layers (`trend_range`, `trend_layers`) are display choices only: never saved. Every round has an invisible `.trend-hit` column with `data-tip` (exact values); `ui.js` moves a dashed crosshair and shows `#trend-tooltip` on hover or touch, and left/right/Home/End move it when the graph (focusable, with `#trend-sr` as its live region) has the keyboard. `FakeElement` in `tests/fakes.py` gained `setAttribute`/`getAttribute`. Tests: `tests/test_round4_trend.py`.
- **Region skins (GI-25).** `SKINS` (Dusk always open; Seaside / Alpine / Desert / Neon Future unlock with `full_capacity_portfolio` / `turning_point_reached` / `crisis_averted` / `thriving_region`). Unlocks are per browser (`drift_skins_v1`, validated), found after an action by `_note_new_skins()` (Settings note and a spoken line) or quietly for a loaded save in `_seed_achievement_toast_baseline()`; the choice is `drift-skin` in localStorage and never rides a save. `render_skins()` sets `data-skin` on `#region-visual` (new id on the skyline banner) and the five Settings buttons (`#skin-<id>-button`, locked ones disabled with the achievement named in the title). The palettes are pure CSS at the end of `style.css` (gradients, building colours, window glow, and clip-path mountains or dunes on `::before`); the strain dimming and building growth work on top of every skin. Reset to Default clicks Dusk. Tests: `tests/test_round4_skins.py`.
- **Achievement glyphs (I-31).** `ACHIEVEMENT_GLYPHS` holds one code-drawn 36x36 SVG body per achievement id (a test pins that every id has one, all distinct, only path/rect/circle/polygon); `achievement_glyph_svg(id, earned, fresh)` wraps it with a ground line and the earned/locked class, and `update_achievements_display()` puts it in an absolutely positioned `.achievement-glyph-slot` on each card (shared share/stats scripts still append their lines below). A badge earned this session goes into `fresh_glyph_ids` (transient) and its glyph draws in once (stroke-dashoffset) the next time the panel renders; the set is cleared after each render, a loaded save never flourishes, and Reduce Motion, the OS setting and Animation speed Off all remove it. Tests: `tests/test_round4_glyphs.py`.
- **Budget templates (I-14).** Three plans in `budget_templates` (`drift_budget_templates_v1`, per browser, validated by `_clean_templates()`: names trimmed to 20, counts 1..20 per capacity type, always exactly three slots; never part of a save). "Save this round's buys" stores `round_purchase_counts()` (funds spent this round divided by each cost); `apply_template()` buys services, then housing, then infrastructure through the normal `region.invest()` (so Reset this round refunds it and the funds/ledger/achievements are ordinary) and returns what was bought and what was short; one building pop for the whole plan. UI: a `<details>` under Budget Autopilot in `#civic-tools` (also in the Desktop side column), ids `template-<1..3>-name/save/apply/summary` and `template-note` (cleared on Advance Round). Tests: `tests/test_round4_templates.py`.
- **Partly-readable save note (I-30).** `load_report(data)` (table `LOAD_SECTIONS`: label, keys, required, check) lists which sections of a save load as written ("restored") and which start fresh ("reset": a section every current save has but this one lacks, i.e. an older save, or one present but failing its check, i.e. damaged or hand-edited; optional sections that were simply never written are not errors). `load_state()` builds the report first, then applies the save with hardened core fields (`_finite_number()` for round, funds, capacity, severity, arrivals, integration and the three running totals; the arrivals, strain and wellbeing logs load only if every entry is a finite number, else they stay as they were), and shows `#load-note` in `#load-note-box` (status block, with a Dismiss button) and announces it once. A clean save shows nothing. The note is transient (never saved). Tests: `tests/test_round4_loadnote.py`.
- **Town-news ticker (GI-20).** `NEWS_HEADLINES` (stable / strained / critical pools of warm, institution-only lines; a test bans words that could point at the people arriving) plus three milestone lines; `news_headline(region)` is a pure function of state (net-positive or Thriving line the round after it happens, the second-wave line while it is warned or active, else the pool for the strain level, one line per round in turn), rendered into `#news-ticker` at the top of the status block. Off by default: `settings.js` keeps `drift-news-ticker` in localStorage and puts `news-ticker-on` on `<html>`, and CSS shows the line only then (Reset to Default turns it off). Nothing is saved. Tests: `tests/test_round4_news.py`.

## Round-4 batch 2 (2026-10-11): tiers, planner assist, confirmations, save nudge, glossary, report, confetti

Built from `planning/TODO.md` "GI + I. Drift": I-9, I-25, I-3, I-28, I-27, I-29, I-4, GI-29 (all code-drawn, nothing random, no number in a run changes unless the player flips an option the game already had). New code sits in one block in `game.py` ("Oct 11 batch 3", just above `get_state()`), wired from `setup_batch3()` and drawn by `render_batch3()` at the end of `render()`. Tests: `tests/test_batch3_*.py` (tiers, assist, confirm and nudge, glossary/report/confetti, pages); `tests/fakes.py` gained `FakeStorage`; the new ids are in `tests/conftest.py`'s `ELEMENT_IDS`. `pc-config.json` adds the Region Report window and a Records menu entry; `pc.html` was regenerated through a scratch script calling `build("drift", cfg)`.

- **Named tiers and per-tier bests (I-9, I-25).** `TIERS` names four sets of the three existing options: Gentle (all off, the base game, the easiest Drift gets), Standard (Crisis Calendar), Rigorous (plus Accelerated Severity), Demanding (plus Crisis Start, only choosable before round 1). `current_tier_id()` derives the tier from the options (any other mix is "custom"), `apply_tier()` sets them (refusing, with a reason, a tier that needs a different Crisis Start after round 1; the Accelerated Severity dot-density baseline is shared through `_set_accelerated_severity()`), `tier_summary_line()` says what each changes from the game's constants. Nothing reads the tier for achievements (Z27: every achievement stays earnable at every tier; a test pins that). Bests: `drift_tier_bests_v1` (localStorage, per browser, never in a save): per tier the best wellbeing score with its band, the fastest net-positive round and the date of the last improvement; updated in `render()` only once a round has been played, only for a named tier and never for an assisted run; `_clean_tier_bests()` drops anything unreadable. UI: a collapsed `#tier-details` in the status block (buttons, summary line, the table). The older single "Personal best wellbeing" line stays.
- **Planner assist (I-3).** `assist_mode` (off / suggest / explain) and `assisted_run` are module globals (not on the region, so a Rewind cannot undo the tag). `plan_suggestion()` is a pure function: it sizes capacity to cover everyone arrived plus this round's arrivals (Services first while they are under 35% of capacity, else Housing, the best capacity per fund; Infrastructure and Community Sponsorship are never suggested because they add less per fund), adds Services while the waiting backlog would take over 3 rounds to clear, then at most one integration policy (Language-Access or Credentialing) if 40 funds stay in reserve, and a Brace for a braceable calendar event; or "hold your funds". Suggest shows the line, Explain adds one reason per item citing the forecast and ROI numbers. Nothing is bought for the player. Turning it on tags the run assisted for good: it no longer updates the personal best or any tier best, the Region Report and run summary say so, achievements still count. Saved as `assist` {mode, assisted} only once assisted (loaded as unassisted if unreadable). Scripted check: following the advice for 12 rounds never leaves strain above stable.
- **Confirm large moves (I-28).** Settings select (`drift_confirm_threshold_v1`: Never, or over 25%, 50% or 75%). `_guard_large_move()` asks through the shared `ConfirmDialog` (no "don't ask again") before a policy purchase whose cost is above that share of funds, or a reallocation that moves above that share of the source type's capacity or costs above that share of funds, and shows the cost (and the 20% transition loss). Capacity purchases are never asked; an unaffordable move falls through to its normal refusal; no dialog on the page (tests) means it just goes through. Reset to Default also clears it (`on_settings_reset_click`).
- **Manual-save nudge (I-27).** After more than `SAVE_NUDGE_ROUNDS` (10) rounds advanced since the last save a note appears under the status lines ("N rounds since this region was last saved (saved 12 min ago)") with Dismiss (counts another 10). A save is noticed through the `savedat:drift` stamp that `shared/save-widget.js` writes after every successful save, checked in `render()` and at the start of every Advance Round / Play 5 / Autopilot (so a save restarts the count from the right round); a loaded save counts as saved at its own round. Never blocks anything, no pressure words.
- **Glossary (I-29).** Four chips under the region name (Capacity, Strain, Integration, Control region); click toggles a pinned one-line definition in `#glossary-pop`, hover and focus show it, leaving hides it unless pinned. Capacity and Integration offer "Read more in The Real Story" (clicks the real info-page toggle so the Desktop window opens too). `GLOSSARY` holds the text, written from the game's own rules.
- **Region Report (I-4).** `region_report_data()` feeds `region_report_html()` (the `#report-panel` card, also a Desktop window) and `region_report_text()` (Copy report as text, clipboard or a read-only box): name, tier and options, band and score, key rounds (first purchase, only trusted while the ledger still starts at round 1; net-positive; Thriving; second wave; strain peak), each sub-score first logged value to now with a block curve, a spending-and-return table (from `spend_by_type`, derived from capacity for an older save; Services show funds returned per fund spent), council programs and the coda choice. Print fills `#report-print-sheet` (a direct body child) and calls `window.print()`; the `@media print` rules hide everything else and force black on white.
- **Band-change confetti (GI-29).** `_celebrate_band_rise()` compares the wellbeing band before and after an Advance Round, Play 5 rounds or Autopilot run; a rise plays 14 CSS pieces over the gauges (`#band-confetti`, one `_pulse` of 2.6 s), shows "Wellbeing rose into the X band." and adds that line to the round announcement. Silent. Hidden by Reduce Motion, the OS setting, Animation speed Off and lite mode; a loaded save never celebrates.
- **Light theme.** The shared light sheet only lightens ids ending in `-display`, so `#save-nudge`, `#band-change-note` and the older `#load-note` get their own light and high-contrast rules at the end of `style.css`.
- **Skipped this batch:** GI-3, GI-6, GI-7, GI-10, GI-12, GI-23, GI-24, GI-26 (large new mechanics or design choices not covered by the item text), GI-4/GI-8/GI-9/GI-27/GI-28 (need level select, skill tree), GI-16 (a luck gamble), I-1, I-2, I-5, I-6, I-7, I-10, I-11 (larger builds left for another batch).


## Design specs (LA-13)

Written 2026-10-22 (LA-13 design pass, batch 2). Steps: `local-ai/incoming/drift-design.txt`. Standing rules hold for
every item: nothing timed, nothing lost, no luck needed for 100%, no audio files, saves load unchanged, the framing
stays institutional. `index.html` is at about 14,650 of its 15,000-token cap (`tests/test_file_sizes.py`): the three
items together add under 900 bytes of markup, so copy the markup exactly as given and never add comments to it.
Merge the chains in the order GI-4, GI-6, GI-10.

Why the numbers below: simulated against the real `RegionState`. Any sensible plan reaches the Model Region band
(about 98) by round 25 and every plan converges near 99 by round 30, so long-run wellbeing cannot tell regions or plans
apart. What does differ is the opening: the round the region first reaches Thriving (70) and the first net-positive
round. Both items that compare regions (the Atlas clear and the Rivals card) therefore judge the opening.

### GI-4: Region Atlas (four starting regions, each opened by clearing the one before)
- **Rule.** Before round 1 (and before anything is bought) the player may start as one of four Atlas regions instead of
  the ordinary home region. A region is CLEARED when it reaches Thriving (wellbeing 70) by round 15
  (`ATLAS_CLEAR_ROUND`); clearing the home region opens Coastal Port, clearing Coastal Port opens Mountain Valley, then
  Border Junction, then Post-Industrial Town (the Crisis Start numbers with an old mill town's infrastructure). An Atlas
  start replaces Crisis Start (choosing one turns the other off). Runs are otherwise identical: same costs, arrivals
  curve, calendar and tiers. Atlas runs do not update the tier bests (their start differs).
- **Numbers** (checked: thriving round for six fixed plans; "-" = never by round 20):

| Region | Funds | Income/round | Starting capacity | Arrived | Pressure | Default Autopilot | No services | Hoard 300 |
|---|---|---|---|---|---|---|---|---|
| Home (unchanged) | 300 | 50 | none | 0 | 0 | 13 | - | 5 |
| Coastal Port | 300 | 65 | 12 infrastructure | 0 | 2.0 | 9 | - | 5 |
| Mountain Valley | 360 | 40 | 20 housing | 0 | 0 | 13 | - | 6 |
| Border Junction | 250 | 50 | none | 30 | 3.0 | 7 | - | - |
| Post-Industrial Town | 150 | 45 | 18 infrastructure | 60 | 2.0 | 7 | - | - |

  Every region clears with the default Autopilot rules and with three other sensible plans (rounds 7 to 14); none
  clears without integration services; hoarding funds clears the calm regions fastest but never the pressured ones.
  So each region asks for a different opening, and nothing needs luck.
- **Unlocks and progress** use the shared level select (W-1, already built): a NEW data file `atlas-levels.json` and
  the shared script tag; progress lives in the level select's own per-browser store (`levels:drift`), so nothing new is
  saved per browser by the game. Play on a card calls `window.NoyvjLevelStart(id)`, which a NEW small file `atlas.js`
  forwards to the Python `on_atlas_start(id)`; Python calls `window.NoyvjLevels.complete(id, round)` when a region is
  cleared (`better: "lower"`, so the best is the earliest Thriving round). The level select itself enforces the order
  (`requires`); Python does not re-check it.
- **Saves.** One new key, `atlas_region`, written only for an Atlas run; `load_state` accepts only a known id and
  otherwise sets the home region. The region's income per round is derived from it (`base_income`, never saved).
- **Engine code.** `drift_rules.py`, at the end:

```python
# GI-4: the Region Atlas. Four starting regions; each opens when the one before it is cleared (the ordinary home
# region opens the first). Cleared = the region reached Thriving by ATLAS_CLEAR_ROUND. Checked against the real
# engine: the default Budget Autopilot clears every region (rounds 7 to 13), a region without integration services
# never does, and hoarding funds clears the calm regions fast but not the pressured ones.
ATLAS_CLEAR_ROUND = 15
ATLAS_REGIONS = [
    {"id": "coastal_port", "name": "Coastal Port", "funds": 300.0, "income": 65.0,
     "capacity": {"infrastructure": 12.0}, "arrivals": 0.0, "severity": 2.0,
     "blurb": "A busy harbour: more trade income and docks already built, but more people arrive from the start."},
    {"id": "mountain_valley", "name": "Mountain Valley", "funds": 360.0, "income": 40.0,
     "capacity": {"housing": 20.0}, "arrivals": 0.0, "severity": 0.0,
     "blurb": "A small, steady economy with savings and spare housing, but less income each round."},
    {"id": "border_junction", "name": "Border Junction", "funds": 250.0, "income": 50.0,
     "capacity": {}, "arrivals": 30.0, "severity": 3.0,
     "blurb": "A crossing point: people are already arriving and pressure is high from round 1."},
    {"id": "post_industrial", "name": "Post-Industrial Town", "funds": CRISIS_START_FUNDS, "income": 45.0,
     "capacity": {"infrastructure": 18.0}, "arrivals": CRISIS_START_ARRIVALS, "severity": CRISIS_START_SEVERITY,
     "blurb": "The Crisis Start numbers in an old mill town: little money and a backlog, but sturdy old infrastructure."},
]
ATLAS_BY_ID = {a["id"]: a for a in ATLAS_REGIONS}
```

  `RegionState.__init__` (`drift_model_region.py`): directly after `self.crisis_start_enabled = False` add

```python
        # GI-4: the Region Atlas start (None = the home region) and the income per round that start earns.
        self.atlas_region = None
        self.base_income = BASE_REGIONAL_INCOME_PER_ROUND
```

  `advance_round`: change `income = BASE_REGIONAL_INCOME_PER_ROUND * (1 - strain)` to
  `income = self.base_income * (1 - strain)  # GI-4` (the one allowed change of an existing line).
  `set_crisis_start`: directly after `self.crisis_start_enabled = bool(enabled)` add
  `self.atlas_region = None  # GI-4: Crisis Start replaces an Atlas start` and
  `self.base_income = BASE_REGIONAL_INCOME_PER_ROUND`. Directly after the method `set_crisis_start` add:

```python
    # GI-4: the Region Atlas, chosen before round 1 and before anything is bought.
    def can_choose_atlas(self):
        return self.round_number == 1 and not self.strain_log and not any(self.spend_by_type.values())

    def apply_atlas(self, atlas_id):
        """Start this region as an Atlas region (None = the home region); turns Crisis Start off. Returns False and
        changes nothing when it is too late or the id is unknown."""
        if not self.can_choose_atlas() or (atlas_id is not None and atlas_id not in ATLAS_BY_ID):
            return False
        profile = ATLAS_BY_ID.get(atlas_id)
        self.crisis_start_enabled = False
        self.atlas_region = atlas_id
        self.base_income = profile["income"] if profile else BASE_REGIONAL_INCOME_PER_ROUND
        self.funds = profile["funds"] if profile else STARTING_FUNDS
        self.total_arrivals = profile["arrivals"] if profile else 0.0
        self.background_severity = profile["severity"] if profile else 0.0
        self.capacity = {t: (profile["capacity"].get(t, 0.0) if profile else 0.0) for t in CAPACITY_TYPES}
        return True
```

  (add `ATLAS_BY_ID` to the `from drift_rules import (...)` block). `drift_savestate.py` `get_state()`: directly after
  `"crisis_start_enabled": region.crisis_start_enabled,` add
  `**({"atlas_region": region.atlas_region} if region.atlas_region else {}),  # GI-4`. `load_state`: directly after the
  line `region.crisis_start_enabled = bool(data.get("crisis_start_enabled", region.crisis_start_enabled))` add

```python
    saved_atlas = data.get("atlas_region")  # GI-4: absent for the home region and in older saves
    region.atlas_region = saved_atlas if saved_atlas in ATLAS_BY_ID else None
    region.base_income = ATLAS_BY_ID[region.atlas_region]["income"] if region.atlas_region else BASE_REGIONAL_INCOME_PER_ROUND
```

  (import `ATLAS_BY_ID, BASE_REGIONAL_INCOME_PER_ROUND` from `drift_rules`).
- **Engine tests, NEW file `tests/test_region_atlas.py`** (the `game_env` fixture; `m = game_env.module`):

```python
"""LA-13 / GI-4: the Region Atlas, four starting regions chosen before round 1."""


def _play(region, rounds, m):
    """The default Budget Autopilot plan: services to half of capacity, the rest on housing, 40 funds kept back."""
    for _ in range(rounds):
        for _ in range(25):
            total = region.total_capacity()
            share = region.capacity["services"] / total if total else 0.0
            kind = "services" if share < 0.5 else "housing"
            if region.funds - 40 < m.INVEST_COST[kind] or not region.invest(kind):
                break
        region.advance_round()


def test_each_atlas_region_starts_with_its_own_numbers(game_env):
    m = game_env.module
    r = m.RegionState()
    assert r.apply_atlas("border_junction") is True
    assert (r.funds, r.total_arrivals, r.background_severity, r.base_income) == (250.0, 30.0, 3.0, 50.0)
    assert r.apply_atlas("post_industrial") is True
    assert r.funds == m.CRISIS_START_FUNDS and r.capacity["infrastructure"] == 18.0 and r.base_income == 45.0
    assert r.apply_atlas(None) is True
    assert (r.funds, r.total_capacity(), r.atlas_region, r.base_income) == (300.0, 0.0, None, 50.0)


def test_an_atlas_start_is_only_before_round_one_and_anything_bought(game_env):
    m = game_env.module
    r = m.RegionState()
    r.invest("housing")
    assert r.apply_atlas("coastal_port") is False and r.atlas_region is None
    later = m.RegionState()
    later.advance_round()
    assert later.apply_atlas("coastal_port") is False
    assert m.RegionState().apply_atlas("atlantis") is False


def test_atlas_and_crisis_start_replace_each_other(game_env):
    m = game_env.module
    r = m.RegionState()
    r.set_crisis_start(True)
    r.apply_atlas("border_junction")
    assert r.crisis_start_enabled is False and r.atlas_region == "border_junction"
    r.set_crisis_start(True)
    assert r.atlas_region is None and r.base_income == 50.0


def test_the_income_follows_the_region(game_env):
    m = game_env.module
    coastal, home = m.RegionState(), m.RegionState()
    coastal.apply_atlas("coastal_port")
    coastal.background_severity = home.background_severity = 0.0
    coastal.capacity["infrastructure"] = 0.0
    coastal.advance_round()
    home.advance_round()
    assert coastal.funds - home.funds == 15.0


def test_every_region_clears_with_the_default_autopilot_plan(game_env):
    m = game_env.module
    for atlas_id in [None] + [a["id"] for a in m.ATLAS_REGIONS]:
        r = m.RegionState()
        r.apply_atlas(atlas_id)
        _play(r, m.ATLAS_CLEAR_ROUND, m)
        assert r.thriving_round is not None and r.thriving_round <= m.ATLAS_CLEAR_ROUND, atlas_id


def test_the_atlas_region_is_saved_only_when_chosen(game_env):
    m = game_env.module
    assert "atlas_region" not in m.get_state()
    game_env.region.apply_atlas("mountain_valley")
    state = m.get_state()
    assert state["atlas_region"] == "mountain_valley"
    m.load_state(state)
    assert game_env.region.atlas_region == "mountain_valley" and game_env.region.base_income == 40.0
    m.load_state({**state, "atlas_region": "nowhere"})
    assert game_env.region.atlas_region is None and game_env.region.base_income == 50.0
```

- **Choosing and clearing** (second engine step). `drift_tiers.py` (add `ATLAS_BY_ID, ATLAS_CLEAR_ROUND` to its rules
  import), at the end:

```python
# ---- GI-4: the Region Atlas (the shared level select shows the cards and keeps which ones are cleared) ----
def choose_atlas(level_id):
    """Play on an Atlas card ("home" = the ordinary start). Returns (ok, message); nothing changes when it fails."""
    atlas_id = None if level_id == "home" else level_id
    if atlas_id is not None and atlas_id not in ATLAS_BY_ID:
        return False, "That region is not in the Atlas."
    if not region.apply_atlas(atlas_id):
        return False, (
            "An Atlas region is chosen when a new region starts: before round 1 and before anything is bought. "
            "Use New Game on the opening screen to start one."
        )
    runstate.round_start_snapshot = _take_round_start_snapshot()
    return True, atlas_status_text()


def atlas_status_text():
    profile = ATLAS_BY_ID.get(region.atlas_region)
    if profile is None:
        return f"Home region. Reach Thriving by round {ATLAS_CLEAR_ROUND} to open the first Region Atlas start."
    return (
        f"{profile['name']}: {profile['blurb']} Started with {profile['funds']:.0f} funds; "
        f"{profile['income']:.0f} income a round. Reach Thriving by round {ATLAS_CLEAR_ROUND} to clear it."
    )


def render_atlas_status():
    status = document.getElementById("atlas-status")
    status.innerText = atlas_status_text()
```

  `_maybe_update_tier_best`: change `if runstate.assisted_run or region.round_number <= 1:` to
  `if runstate.assisted_run or region.round_number <= 1 or region.atlas_region:  # GI-4: an Atlas start has its own numbers`.
  `drift_collection.py` (add `ATLAS_BY_ID, ATLAS_CLEAR_ROUND` to its rules import), directly above
  `def _collect_after_round`:

```python
# ---- GI-4: clearing a Region Atlas start ----
def atlas_cleared_now(completed_round):
    """The Atlas level id this round clears ("home" for the ordinary start), or None. A region is cleared on the round
    it first reaches Thriving, if that is by ATLAS_CLEAR_ROUND; assisted runs never clear one (like the tier bests)."""
    if runstate.assisted_run or region.thriving_round != completed_round or completed_round > ATLAS_CLEAR_ROUND:
        return None
    return region.atlas_region or "home"


def _note_atlas_clear(completed_round):
    level_id = atlas_cleared_now(completed_round)
    if level_id is None:
        return None
    try:
        from js import window  # noqa: PLC0415 -- Pyodide-only, deliberately lazy
        levels = getattr(window, "NoyvjLevels", None)
        if levels is not None:
            levels.complete(level_id, completed_round)
    except Exception:  # noqa: BLE001 -- the level select is an extra; the run goes on without it
        pass
    name = ATLAS_BY_ID[level_id]["name"] if level_id in ATLAS_BY_ID else "Home region"
    return f"Region Atlas: {name} cleared (Thriving by round {completed_round})."
```

  and in `_collect_after_round`, directly before its `return found`:
  `cleared = _note_atlas_clear(completed_round)  # GI-4` / `if cleared:` / `found.append(cleared)` /
  `runstate.collection_note = (runstate.collection_note + " " if runstate.collection_note else "") + cleared`.
  `drift_handlers.py` (import `choose_atlas` from `drift_tiers`), at the end:

```python
def on_atlas_start(level_id):
    """GI-4: Play on a Region Atlas card (atlas.js forwards window.NoyvjLevelStart here)."""
    ok, message = choose_atlas(str(level_id))
    runstate.round_tools_message = message
    render()
    announce(message)
    return ok
```

  `game.py`: add `on_atlas_start` to its `from drift_handlers import (...)` block so the page can reach it through
  `pyodide.globals.get("on_atlas_start")`. `drift_renderer.py` `render()`: directly after the crisis-button lines
  (after `crisis_button.classList.remove("active")`) add `render_atlas_status()  # GI-4` (import it from `drift_tiers`).
  `tests/conftest.py` `ELEMENT_IDS`: add `"atlas-status", "atlas-open-button",`. Tests (append to
  `tests/test_region_atlas.py`):

```python
def test_choose_atlas_from_the_level_select(game_env):
    m = game_env.module
    ok, message = m.choose_atlas("coastal_port")
    assert ok is True and message.startswith("Coastal Port:")
    m.on_atlas_start("home")
    assert game_env.region.atlas_region is None
    assert game_env.elements["atlas-status"].innerText.startswith("Home region.")
    game_env.advance_round()
    ok, message = m.choose_atlas("mountain_valley")
    assert ok is False and "New Game" in message and game_env.region.atlas_region is None


def test_a_clear_is_the_first_thriving_round_by_round_fifteen(game_env):
    m = game_env.module
    game_env.region.thriving_round = 9
    assert m.atlas_cleared_now(9) == "home" and m.atlas_cleared_now(10) is None
    game_env.region.atlas_region = "border_junction"
    assert m.atlas_cleared_now(9) == "border_junction"
    game_env.region.thriving_round = 16
    assert m.atlas_cleared_now(16) is None
```

- **Page** (last step). NEW file `atlas-levels.json`:

```json
{
  "title": "Region Atlas",
  "levels": [
    { "id": "home", "title": "Home region", "kind": "level", "better": "lower", "unit": "rounds to Thriving",
      "blurb": "The ordinary start: 300 funds, 50 income a round. Reach Thriving by round 15 to open the Atlas." },
    { "id": "coastal_port", "title": "Coastal Port", "kind": "level", "better": "lower", "unit": "rounds to Thriving",
      "blurb": "300 funds, 65 income a round, 12 infrastructure built; more people arrive from the start.", "requires": ["home"] },
    { "id": "mountain_valley", "title": "Mountain Valley", "kind": "level", "better": "lower", "unit": "rounds to Thriving",
      "blurb": "360 funds and 20 spare housing, but only 40 income a round.", "requires": ["coastal_port"] },
    { "id": "border_junction", "title": "Border Junction", "kind": "level", "better": "lower", "unit": "rounds to Thriving",
      "blurb": "250 funds; 30 people already arrived and high pressure from round 1.", "requires": ["mountain_valley"] },
    { "id": "post_industrial", "title": "Post-Industrial Town", "kind": "mode", "better": "lower", "unit": "rounds to Thriving",
      "blurb": "The Crisis Start numbers (150 funds, 60 people arrived) with 18 old infrastructure and 45 income a round.",
      "requires": ["border_junction"] }
  ]
}
```

  NEW file `atlas.js`:

```js
// GI-4: Play on a Region Atlas card (shared level select) starts that region: Python on_atlas_start in drift_handlers.py.
window.NoyvjLevelStart = function (levelId) {
  var start = window.pyodide && window.pyodide.globals.get("on_atlas_start");
  if (start) { start(String(levelId)); }
  if (window.NoyvjLevels && window.NoyvjLevels.close) { window.NoyvjLevels.close(); }
};
```

  `index.html`: directly after the `#crisis-start-toggle-button` line add
  `<button id="atlas-open-button" class="secondary" type="button">🗺️ Region Atlas</button>`; directly after the
  `#realloc-note` element add `<p id="atlas-status" class="panel-note"></p>` (if `#realloc-note` is not a single line,
  put it after the crisis button line instead); directly after the `last-played.js` script tag add the two tags
  `<script src="atlas.js"></script>` and the level-select tag from this paragraph's end. The level-select tag is the
  same one Canopy uses with Drift's values: src `../../` + `shared/level-select.js`, `data-game-id="drift"`,
  `data-levels="atlas-levels.json"`, `data-open="#atlas-open-button"`. Browser test NEW `tests/test_region_atlas_browser.py`
  (copy `tests/test_example_browser.py`): `page.evaluate("window.NoyvjLevelStart('coastal_port')")`; wait until
  `#atlas-status` text starts with "Coastal Port:"; `#funds-display` text contains "300"; click `#atlas-open-button`;
  `#level-select` is visible and its text contains "Mountain Valley"; `page.page_errors == []`.

### GI-6: Rival Regions (three computer-run regions on the same pressure curve)
- **Rule.** Three rival regions face exactly your pressure curve (same arrivals formula, and your Accelerated Severity
  and Crisis Calendar settings; calendar events unbraced, like the passive region) and each follows one fixed plan:
  - **Frugal region:** keeps 300 funds in reserve; integration services up to 40% of capacity, then housing.
  - **Builder region:** spends everything each round; services up to 50% of capacity, then infrastructure.
  - **Reactive region:** buys only in a round when some arrived people are not covered; services up to 30%, then housing.
  They start from the ordinary home start (never your Atlas start, never Crisis Start), with no cross-region learning.
  Like the passive region they are a pure function of the round count and the two settings, so NOTHING is saved: each
  simulation is cached in memory and only extended as rounds pass (200 rounds take under 10 ms).
- **On the trend graph:** a new layer chip "Rival regions" (off by default) draws the three wellbeing lines, each with
  its own dash pattern (shape, not colour alone) and in the crosshair tooltip ("Frugal 74").
- **The round-60 card.** After round 60 has been played, `#rivals-card` shows the standings at round 60, ranked by the
  round each region first reached Thriving (sooner is better; not by round 60 = last), then by the first net-positive
  round; on a tie your region is listed first. Wellbeing at round 60 is NOT used: every plan sits near 99 by then
  (simulated), so it would not separate anyone. At default settings the rivals reach Thriving at rounds 6 (Frugal),
  13 (Builder) and 6 (Reactive) and turn net positive at 9, 10 and 7; the default Autopilot plan reaches Thriving at 13.
  So the card is a real target ("beat the Reactive region's round 6") that skill, not luck, decides.
- **Saves.** None. Old saves show the rivals at once.
- **Engine code**, `drift_messages.py`, directly after `_simulate_control_region` (add `INVEST_COST` to its rules
  import if missing):

```python
# GI-6: three computer-run rival regions on the same pressure curve as yours (your Accelerated Severity and Crisis
# Calendar settings, events unbraced), each with one fixed plan. Like the passive region they are a pure function of
# the round count, so nothing is saved; each simulation is cached and only extended as rounds pass.
RIVALS = [
    {"id": "frugal", "name": "Frugal region", "reserve": 300.0, "services_share": 0.4, "surplus": "housing",
     "reactive": False, "plan": "keeps 300 funds in reserve; services to 40% of capacity, then housing"},
    {"id": "builder", "name": "Builder region", "reserve": 0.0, "services_share": 0.5, "surplus": "infrastructure",
     "reactive": False, "plan": "spends everything each round; services to 50% of capacity, then infrastructure"},
    {"id": "reactive", "name": "Reactive region", "reserve": 0.0, "services_share": 0.3, "surplus": "housing",
     "reactive": True, "plan": "builds only when some arrivals are not covered; services to 30%, then housing"},
]
RIVAL_BY_ID = {r["id"]: r for r in RIVALS}
RIVALS_CARD_ROUND = 60
_rival_cache = {}


def _rival_buys(rival_region, rival):
    """One round of a rival's fixed plan (at most 25 purchases, like the Autopilot)."""
    for _ in range(25):
        if rival["reactive"] and rival_region.round_number > 1 and rival_region.strain_fraction() <= 0.0:
            return
        total = rival_region.total_capacity()
        share = rival_region.capacity["services"] / total if total > 0 else 0.0
        kind = "services" if share < rival["services_share"] else rival["surplus"]
        if rival_region.funds - rival["reserve"] < INVEST_COST[kind] or not rival_region.invest(kind):
            return


def simulate_rival(rival_id, round_number, accelerated_severity_enabled, calendar_enabled=False):
    """The rival region as it stands at the start of `round_number` (cached; a cached run is only ever extended)."""
    rival = RIVAL_BY_ID[rival_id]
    key = (rival_id, bool(accelerated_severity_enabled), bool(calendar_enabled))
    sim = _rival_cache.get(key)
    if sim is None or sim.round_number > round_number:
        sim = RegionState()
        sim.learning_active = False
        sim.accelerated_severity_enabled = bool(accelerated_severity_enabled)
        sim.calendar_enabled = bool(calendar_enabled)
        _rival_cache[key] = sim
    while sim.round_number < round_number:
        _rival_buys(sim, rival)
        sim.advance_round()
    return sim


def rivals_standings(region_state):
    """GI-6: the round-60 standings once round 60 has been played, else None. Ranked by the round each region first
    reached Thriving (by round 60; sooner is better, never is last), then by the first net-positive round."""
    if region_state.round_number <= RIVALS_CARD_ROUND:
        return None

    def by_60(value):
        return value if value is not None and value <= RIVALS_CARD_ROUND else None

    rows = [{"name": "Your region", "you": True, "thriving": by_60(region_state.thriving_round),
             "net_positive": by_60(region_state.net_positive_round)}]
    for rival in RIVALS:
        sim = simulate_rival(rival["id"], RIVALS_CARD_ROUND + 1, region_state.accelerated_severity_enabled,
                             region_state.calendar_enabled)
        rows.append({"name": rival["name"], "you": False, "thriving": by_60(sim.thriving_round),
                     "net_positive": by_60(sim.net_positive_round)})
    never = RIVALS_CARD_ROUND + 1
    rows.sort(key=lambda row: (row["thriving"] or never, row["net_positive"] or never, not row["you"]))
    return rows


def rivals_card_lines(rows):
    lines = []
    for place, row in enumerate(rows, 1):
        thriving = f"Thriving from round {row['thriving']}" if row["thriving"] else "not Thriving by round 60"
        net = f"net positive from round {row['net_positive']}" if row["net_positive"] else "not net positive by round 60"
        lines.append(f"{place}. {row['name']}: {thriving}, {net}.")
    return lines
```

- **Engine tests, NEW file `tests/test_rival_regions.py`:**

```python
"""LA-13 / GI-6: three rival regions with fixed plans, a pure function of the round count."""


def test_the_rivals_open_as_simulated(game_env):
    m = game_env.module
    got = {r["id"]: m.simulate_rival(r["id"], 61, False, False) for r in m.RIVALS}
    assert {k: v.thriving_round for k, v in got.items()} == {"frugal": 6, "builder": 13, "reactive": 6}
    assert {k: v.net_positive_round for k, v in got.items()} == {"frugal": 9, "builder": 10, "reactive": 7}


def test_a_cached_rival_matches_a_fresh_one(game_env):
    m = game_env.module
    m.simulate_rival("builder", 20, False, False)
    extended = list(m.simulate_rival("builder", 40, False, False).wellbeing_log)
    m._rival_cache.clear()
    assert list(m.simulate_rival("builder", 40, False, False).wellbeing_log) == extended
    assert len(m.simulate_rival("builder", 10, False, False).wellbeing_log) == 9


def test_the_card_waits_for_round_sixty_and_ranks_by_the_opening(game_env):
    m = game_env.module
    region = game_env.region
    assert m.rivals_standings(region) is None
    region.round_number = 61
    region.thriving_round, region.net_positive_round = 6, 5
    rows = m.rivals_standings(region)
    assert [row["name"] for row in rows][:2] == ["Your region", "Reactive region"]
    assert rows[-1]["name"] == "Builder region"
    region.thriving_round = None
    assert m.rivals_standings(region)[-1]["name"] == "Your region"
    assert m.rivals_card_lines(m.rivals_standings(region))[-1] == "4. Your region: not Thriving by round 60, net positive from round 5."
```

- **Graph layer** (second step). `drift_trendgraph.py`: `TREND_LAYER_ORDER` gains `"rivals"` at the end (after
  `"events"`), `TREND_LAYER_LABEL` gains `"rivals": "Rival regions"`, `TREND_LAYER_DEFAULT` gains `"rivals": False`.
  `trend_legend_text`: before its final return add `if layers.get("rivals"):` /
  `parts.append("Rival regions: long dashes Frugal, dash-dot Builder, short dashes Reactive.")`. `trend_graph_svg`:
  add the keyword `rival_histories=None` at the end of its parameters (a list of `(rival id, name, wellbeing list)`);
  directly after the control-line block (before the `# I-12: the ROI layer` comment) add:

```python
    # GI-6: the rival regions' wellbeing, one dash pattern each (CSS), aligned to the left like the passive region.
    rival_series = []
    if layers.get("rivals") and rival_histories:
        for rival_id, name, history in rival_histories:
            series = list(history[start:start + n]) if len(history) >= n_all else list(history[:n])
            if len(series) >= 2:
                ys = _normalize_series(series, TREND_GRAPH_HEIGHT, 0, 100)
                drawn.append(
                    f'<polyline points="{" ".join(f"{x:.1f},{y:.1f}" for x, y in zip(xs, ys))}" '
                    f'class="trend-line trend-line--rival trend-line--rival-{rival_id}" />'
                )
                rival_series.append((name.split()[0], series))
```

  and in the hit-column loop, directly after the `passive region` line, add
  `for short, series in rival_series:` / `if i < len(series):` / `parts.append(f"{short} {series[i]:.0f}")`.
  `drift_newsview.py` `render_trend_graph`: build `rivals = [(r["id"], r["name"], simulate_rival(r["id"], region.round_number, region.accelerated_severity_enabled, region.calendar_enabled).wellbeing_log) for r in RIVALS] if trend_layers.get("rivals") and region.round_number > 2 else None`
  before the `trend_svg = ...` call and pass `rival_histories=rivals` to it (import `RIVALS, simulate_rival` from
  `drift_messages`). CSS (`style-2-console.css`, directly after the `.trend-line--control` rule):
  `.trend-line--rival { stroke: var(--text-muted, #9aa3b5); stroke-width: 1.2; fill: none; opacity: 0.85; }`,
  `.trend-line--rival-frugal { stroke-dasharray: 8 3; }`, `.trend-line--rival-builder { stroke-dasharray: 6 2 1 2; }`,
  `.trend-line--rival-reactive { stroke-dasharray: 2 2; }`. Markup: directly after the `#trend-layer-events-button`
  line add `<button id="trend-layer-rivals-button" class="secondary chip" type="button" aria-pressed="false">Rival regions</button>`
  (game.py already wires every `TREND_LAYER_ORDER` key); `tests/conftest.py` `ELEMENT_IDS`: `"trend-layer-rivals-button",`
  after `"trend-layer-events-button",`. Test (append to `tests/test_rival_regions.py`):

```python
def test_the_rivals_layer_draws_three_dashed_lines(game_env):
    m = game_env.module
    for _ in range(6):
        game_env.advance_round()
    svg = m.trend_graph_svg(game_env.region.strain_log, game_env.region.wellbeing_log, layers={"rivals": True},
                            rival_histories=[(r["id"], r["name"], m.simulate_rival(r["id"], game_env.region.round_number, False).wellbeing_log) for r in m.RIVALS])
    assert svg.count("trend-line--rival ") == 3 and "Frugal " in svg
    assert "trend-line--rival" not in m.trend_graph_svg(game_env.region.strain_log, game_env.region.wellbeing_log)
    game_env.elements["trend-layer-rivals-button"].dispatch("click", None)
    assert "trend-line--rival-reactive" in game_env.elements["trend-graph"].innerHTML
```

- **The card** (third step). Markup directly after the `#trend-legend` element:
  `<div id="rivals-card" class="rivals-card" role="status" hidden></div>`. `drift_newsview.py`, after
  `render_trend_graph`:

```python
def render_rivals_card():
    """GI-6: the round-60 standings against the three rival regions (hidden before round 60 has been played)."""
    card = document.getElementById("rivals-card")
    rows = rivals_standings(region)
    card.hidden = rows is None
    if rows is None:
        return
    card.innerHTML = "<strong>Round 60 against the rival regions</strong><ol>" + "".join(
        f"<li>{line.split('. ', 1)[1]}</li>" for line in rivals_card_lines(rows)
    ) + "</ol><p>Ranked by the round each region first reached Thriving, then the first net-positive round.</p>"
```

  and call `render_rivals_card()` as the last line of `render_trend_graph()` (import `rivals_standings,
  rivals_card_lines`). CSS (`style-2-console.css`, end): `.rivals-card { margin-top: 0.5rem; }`,
  `.rivals-card ol { margin: 0.3rem 0 0.3rem 1.2rem; }`. `tests/conftest.py` `ELEMENT_IDS`: `"rivals-card",`. Tests:
  fake DOM `test_the_card_shows_after_round_sixty` (call `game_env.advance_round()` 59 times, asserting after each that
  `elements["rivals-card"].hidden is True`; one more call plays round 60: then `hidden is False` and its `innerHTML`
  contains "Reactive region");
  browser NEW `tests/test_rival_regions_browser.py`: advance 3 rounds with `#advance-round-button` (wait for
  `#round-display` to change each time), click `#trend-layer-rivals-button`, wait until
  `#trend-graph .trend-line--rival` count is 3, `#trend-legend` text contains "Rival regions", `page.page_errors == []`.

### GI-10: What-if Timeline Scrubber (change one decision, replay to now)
- **Rule.** From round 3 on, a "What-if" panel lets the player pick any played round, pick one of that round's
  decisions and change it in one way (one fewer of it; or, for a capacity purchase, one of another capacity type
  instead), then replay the whole run from round 1 to now with that single change. The what-if wellbeing curve is drawn
  on the trend graph as its own dashed line and a sentence compares the endings ("What-if: wellbeing now 84 instead of
  92; Thriving from round 9 instead of 13; 2 later decisions could not be afforded and were skipped"). Nothing in the
  real run changes; the what-if is in memory only and clears as soon as another round is played.
- **How the replay works (deterministic, no luck).** Every decision is logged as `[round, verb, argument, count]`
  (verbs `invest`, `policy`, `realloc`, `brace`, `council`; consecutive identical decisions in one round merge into one
  entry with a count, so an Autopilot round is one or two entries). The replay starts a fresh region with the run's own
  start (Crisis Start or Atlas region, Accelerated Severity, Crisis Calendar, cross-region learning), makes each
  round's logged decisions and advances, exactly as the run did. Autopilot, templates and Play-5 buy through
  `invest`, so they are logged for free; Reset Round drops the round's entries; the Rewind Token restores the log with
  the rest of the region (it is part of `region.__dict__`).
- **Honesty check.** Before offering a what-if the game replays the UNCHANGED log and compares it with the real run
  (every wellbeing value and the funds). If they differ, the panel says why it cannot replay this run and offers
  nothing. Runs that cannot match: a region started before this feature (no log), a run that used the neighbouring
  district (its spillover and support are not replayed), a run that switched Accelerated Severity or the Crisis
  Calendar after round 1, and a log that reached its 2,000-entry cap. Simulated: an Autopilot run with policies,
  reallocations, braces and council picks replays exactly.
- **Saves.** One new key, `decision_log`, written only when not empty; `load_state` keeps it only if every entry is
  `[positive int, known verb, str or None, positive int]`, at most 2,000 entries, rounds never decreasing; anything else
  loads as an empty log (that run simply cannot be replayed). About 1-3 KB for a typical 60-round run.
- **Engine code, logging** (`drift_rules.py`, end):

```python
# GI-10: the decision log behind the What-if replay.
DECISION_VERBS = ("invest", "policy", "realloc", "brace", "council")
DECISION_LOG_MAX = 2000
SCRUBBER_MIN_ROUND = 3
```

  `RegionState.__init__`: directly after the GI-4 `self.base_income` line (or after `self.crisis_start_enabled = False`)
  add `self.decision_log = []  # GI-10: [round, verb, argument, count] per decision, for the What-if replay`.
  Directly above `def _record_spend` add:

```python
    def _log_decision(self, verb, arg=None):
        """GI-10: one decision for the What-if replay; repeats of the same decision in a round add to its count."""
        log = self.decision_log
        if log and log[-1][0] == self.round_number and log[-1][1] == verb and log[-1][2] == arg:
            log[-1][3] += 1
        elif len(log) < DECISION_LOG_MAX:
            log.append([self.round_number, verb, arg, 1])
```

  Then, directly before the final `return True` of each method: `invest` adds `self._log_decision("invest", capacity_type)`,
  `invest_policy` adds `self._log_decision("policy", policy)`, `reallocate` adds
  `self._log_decision("realloc", f"{from_type}>{to_type}")`, `brace` adds `self._log_decision("brace")`.
  `drift_calendar.py` `council_pick`: directly before its `return True` add
  `region._log_decision("council", program["id"])  # GI-10`. `drift_undo.py` `reset_round`: directly before its
  `return True` add `region.decision_log = [e for e in region.decision_log if e[0] != region.round_number]  # GI-10`.
  Tests, NEW file `tests/test_whatif_replay.py`:

```python
"""LA-13 / GI-10: the decision log and the What-if replay."""


def _buy(game_env, kind, times=1):
    for _ in range(times):
        game_env.invest(kind)


def test_decisions_are_logged_and_merged_per_round(game_env):
    region = game_env.region
    _buy(game_env, "services", 3)
    _buy(game_env, "housing")
    game_env.advance_round()
    _buy(game_env, "services")
    assert region.decision_log == [[1, "invest", "services", 3], [1, "invest", "housing", 1], [2, "invest", "services", 1]]


def test_reset_round_drops_only_this_rounds_decisions(game_env):
    m = game_env.module
    _buy(game_env, "services")
    game_env.advance_round()
    _buy(game_env, "housing", 2)
    assert m.reset_round() is True
    assert game_env.region.decision_log == [[1, "invest", "services", 1]]
```

- **Saves** (second step). `get_state()`: directly after the `policy_level` line add
  `**({"decision_log": copy.deepcopy(region.decision_log)} if region.decision_log else {}),  # GI-10`. `load_state`:
  directly after the GI-4 atlas lines (or after the `crisis_start_enabled` line) add
  `region.decision_log = clean_decision_log(data.get("decision_log"))  # GI-10`, with this function in
  `drift_savestate.py` directly above `def load_state` (import `DECISION_LOG_MAX, DECISION_VERBS` from rules):

```python
def clean_decision_log(raw):
    """GI-10: the saved decision log, or [] when anything in it is not well formed (that run just cannot be replayed)."""
    if not isinstance(raw, list) or len(raw) > DECISION_LOG_MAX:
        return []
    out, last_round = [], 1
    for entry in raw:
        if not (isinstance(entry, list) and len(entry) == 4):
            return []
        rnd, verb, arg, count = entry
        if not (_small_int(rnd, 1) and rnd >= last_round and verb in DECISION_VERBS and _small_int(count, 1)):
            return []
        if arg is not None and not isinstance(arg, str):
            return []
        out.append([rnd, verb, arg, count])
        last_round = rnd
    return out
```

  Tests (append): `test_the_log_is_saved_only_when_there_is_one` (`"decision_log" not in m.get_state()`; buy one
  services; round trip through `m.load_state(m.get_state())` keeps `[[1, "invest", "services", 1]]`) and
  `test_a_bad_log_loads_as_empty` (`m.clean_decision_log([[1, "bribe", None, 1]]) == []`,
  `m.clean_decision_log([[2, "invest", "housing", 1], [1, "invest", "housing", 1]]) == []`,
  `m.clean_decision_log("x") == []`).
- **Replay** (third step), `drift_undo.py` at the end:

```python
# ---- GI-10: the What-if replay ----
def _apply_decision(sim, verb, arg):
    if verb == "invest":
        return sim.invest(arg)
    if verb == "policy":
        return sim.invest_policy(arg)
    if verb == "realloc":
        from_type, _, to_type = (arg or "").partition(">")
        return sim.reallocate(from_type, to_type)
    if verb == "brace":
        return sim.brace()
    if verb == "council":
        sim.council_picks.append(arg)
        sim._log_decision("council", arg)
        return True
    return False


def replay_region(source, log=None):
    """A fresh region with source's start that makes the logged decisions round by round up to source's current
    round (including the decisions already made this round). Returns (region, skipped): skipped counts decisions the
    replay could not afford."""
    sim = RegionState()
    sim.learning_active = source.learning_active
    sim.accelerated_severity_enabled = source.accelerated_severity_enabled
    sim.calendar_enabled = source.calendar_enabled
    if source.crisis_start_enabled:
        sim.set_crisis_start(True)
    if getattr(source, "atlas_region", None):
        sim.apply_atlas(source.atlas_region)
    entries = source.decision_log if log is None else log
    skipped = pos = 0
    while True:
        while pos < len(entries) and entries[pos][0] <= sim.round_number:
            _round, verb, arg, count = entries[pos]
            for _ in range(count):
                if not _apply_decision(sim, verb, arg):
                    skipped += 1
            pos += 1
        if sim.round_number >= source.round_number:
            return sim, skipped
        sim.advance_round()


def replay_matches(source):
    """True when replaying the unchanged log gives exactly the real run (so a what-if is honest)."""
    if not source.decision_log and source.round_number > 1:
        return False
    sim, skipped = replay_region(source)
    same = len(sim.wellbeing_log) == len(source.wellbeing_log) and all(
        abs(a - b) < 1e-6 for a, b in zip(sim.wellbeing_log, source.wellbeing_log)
    )
    return skipped == 0 and same and abs(sim.funds - source.funds) < 1e-6


def whatif_log(log, index, swap):
    """A copy of the log with ONE decision changed: entry `index` loses one of its count; `swap` (a capacity type, for
    an invest entry) adds one of that instead, or None for "one fewer"."""
    out = [list(e) for e in log]
    entry = out[index]
    entry[3] -= 1
    new = [[entry[0], "invest", swap, 1]] if swap else []
    out[index:index + 1] = ([entry] if entry[3] > 0 else []) + new
    return out
```

  Tests (append to `tests/test_whatif_replay.py`):

```python
def _autopilot_run(game_env, rounds):
    game_env.region.calendar_enabled = True
    game_env.region.invest_policy("language_access")
    for _ in range(rounds):
        if game_env.region.brace_target() is not None:
            game_env.region.brace()
        for _ in range(25):
            total = game_env.region.total_capacity()
            kind = "services" if total == 0 or game_env.region.capacity["services"] / total < 0.5 else "housing"
            if game_env.region.funds < 60 or not game_env.region.invest(kind):
                break
        game_env.advance_round()
    game_env.region.reallocate("housing", "infrastructure")


def test_an_unchanged_replay_matches_the_real_run(game_env):
    m = game_env.module
    _autopilot_run(game_env, 30)
    assert m.replay_matches(game_env.region) is True


def test_a_run_without_a_log_or_with_the_neighbour_cannot_be_replayed(game_env):
    m = game_env.module
    game_env.advance_round()
    game_env.region.decision_log = []
    assert m.replay_matches(game_env.region) is False


def test_one_changed_decision_changes_the_ending(game_env):
    m = game_env.module
    _autopilot_run(game_env, 20)
    region = game_env.region
    index = next(i for i, e in enumerate(region.decision_log) if e[1] == "invest" and e[2] == "services")
    changed = m.whatif_log(region.decision_log, index, "housing")
    assert sum(e[3] for e in changed) == sum(e[3] for e in region.decision_log)
    policy = next(i for i, e in enumerate(region.decision_log) if e[1] == "policy")
    sim, _skipped = m.replay_region(region, m.whatif_log(region.decision_log, policy, None))
    assert sim.round_number == region.round_number
    assert sim.wellbeing_log != region.wellbeing_log and sim.policy_level["language_access"] == 0
```

  The neighbour
  case is pinned in the browser-free fake-DOM test of step 4 (open the neighbour, support it, then
  `replay_matches` is False).
- **Panel engine** (fourth step), `drift_undo.py` after the replay code; `drift_runstate.py` gains
  `whatif = None` and `scrubber_open = False` (both in `LIVE_NAMES`):

```python
def scrubber_note():
    """Why the What-if replay is not offered, or "" when it is."""
    if region.round_number < SCRUBBER_MIN_ROUND:
        return f"Play to round {SCRUBBER_MIN_ROUND} to try a what-if."
    if not replay_matches(region):
        return ("This run cannot be replayed exactly: it began before decisions were recorded, used the neighbouring "
                "district, or switched Accelerated Severity or the Crisis Calendar after round 1.")
    return ""


def scrubber_choices(round_number):
    """[(log index, text)] for the decisions made in one round."""
    labels = {"invest": lambda a: CAPACITY_LABEL.get(a, a), "policy": lambda a: f"policy: {a}",
              "realloc": lambda a: "move capacity " + (a or "").replace(">", " to "), "brace": lambda a: "brace",
              "council": lambda a: f"council: {a}"}
    return [(i, f"{labels[e[1]](e[2])} x{e[3]}") for i, e in enumerate(region.decision_log) if e[0] == round_number]


def scrubber_swaps(index):
    """[(value, text)] for the ways one decision may be changed ("" = one fewer)."""
    entry = region.decision_log[index]
    swaps = [("", "One fewer")]
    if entry[1] == "invest":
        swaps += [(t, f"One {CAPACITY_LABEL[t]} instead") for t in CAPACITY_TYPES if t != entry[2]]
    return swaps


def run_whatif(index, swap):
    """Replays the run with one change. Returns the sentence; keeps the curve in runstate.whatif for the graph."""
    note = scrubber_note()
    if note:
        runstate.whatif = None
        return note
    sim, skipped = replay_region(region, whatif_log(region.decision_log, index, swap or None))
    def thr(value):
        return f"round {value}" if value is not None else "not yet"
    text = (f"What-if: wellbeing now {sim.wellbeing_score():.0f} instead of {region.wellbeing_score():.0f}; "
            f"Thriving from {thr(sim.thriving_round)} instead of {thr(region.thriving_round)}")
    if skipped:
        text += f"; {skipped} later decision{'s' if skipped != 1 else ''} could not be afforded and {'were' if skipped != 1 else 'was'} skipped"
    runstate.whatif = {"wellbeing": list(sim.wellbeing_log), "text": text + "."}
    return runstate.whatif["text"]
```

  (import `CAPACITY_LABEL, CAPACITY_TYPES, SCRUBBER_MIN_ROUND` from rules). `drift_collection.py`
  `_collect_after_round`: as its first line `runstate.whatif = None  # GI-10: a what-if belongs to the round it was made in`.
  Trend graph: `trend_graph_svg` gains the keyword `whatif_history=None` at the end of its parameters; directly after
  the GI-6 rivals block (or the control block) add: if `whatif_history` has 2+ values, slice it like the control series
  and draw `<polyline ... class="trend-line trend-line--whatif" />`, and in the hit loop add `what-if {v:.0f}`.
  `render_trend_graph` passes `whatif_history=runstate.whatif["wellbeing"] if runstate.whatif else None`.
  Tests: `test_the_note_explains_a_run_that_cannot_be_replayed` (round 1: note starts "Play to round 3"; after
  `m.open_neighbor()` and `m.support_neighbor()` with 4 rounds played the note starts "This run cannot be replayed");
  `test_run_whatif_keeps_a_curve_and_a_sentence` (buy services each round for 5 rounds; `run_whatif(0, "housing")`
  starts with "What-if: wellbeing now"; `m.whatif["wellbeing"]` has 5 values; `game_env.advance_round()` clears it to
  None); `test_the_whatif_line_is_drawn` (with `runstate.whatif` set, `trend_graph_svg(..., whatif_history=[...])`
  contains `trend-line--whatif`).
- **Page** (fifth step). Markup: directly after the `#ledger-toggle-button` line
  `<button id="scrubber-toggle-button" class="secondary" type="button">⏪ What-if</button>`; directly after the
  `#ledger-panel` closing tag:

```html
<div id="scrubber-panel" class="section" hidden><h2>What-if replay</h2><p id="scrubber-note" class="panel-note">Pick a round, change one decision, replay to now.</p><select id="scrubber-round-select" aria-label="Round"></select> <select id="scrubber-decision-select" aria-label="Decision"></select> <select id="scrubber-swap-select" aria-label="Change"></select> <button id="scrubber-run-button" type="button">Replay</button> <button id="scrubber-clear-button" class="secondary" type="button">Clear</button><p id="scrubber-result" role="status"></p></div>
```

  `drift_undo.py` `render_scrubber()`: toggle text "Hide What-if" / "⏪ What-if"; panel hidden unless
  `runstate.scrubber_open`; `#scrubber-note` = `scrubber_note()` or the default line; when replayable, fill
  `#scrubber-round-select` with one `<option value="R">Round R</option>` per distinct logged round (keep its current
  value if still present), `#scrubber-decision-select` from `scrubber_choices(int(round value))` (option value = log
  index), `#scrubber-swap-select` from `scrubber_swaps(int(decision value))`; `#scrubber-result` = `runstate.whatif["text"]`
  or "". Handlers in `drift_handlers.py`: `on_toggle_scrubber` (flip `runstate.scrubber_open`, `render_scrubber()`),
  `on_scrubber_round_change` and `on_scrubber_decision_change` (just `render_scrubber()`), `on_scrubber_run`
  (`run_whatif(int(decision value), swap value)`, then `render_trend_graph()`, `render_scrubber()`, `announce(text)`),
  `on_scrubber_clear` (`runstate.whatif = None`, redraw both). `game.py`: the two buttons in the `(button_id, handler)`
  list; the round and decision selects get "change" listeners. `render()` calls `render_scrubber()` next to
  `render_ledger()`. `shortcuts.js` `panels`: add `{ toggle: "scrubber-toggle-button", panel: "scrubber-panel" }`.
  `tests/conftest.py` `ELEMENT_IDS`: all nine scrubber ids. CSS (`style-2-console.css`, after the rival rules):
  `.trend-line--whatif { stroke: var(--accent, #7fb8ff); stroke-width: 2; stroke-dasharray: 4 2; fill: none; }`.
  Browser test NEW `tests/test_whatif_browser.py`: click `#services-invest-button` then `#advance-round-button`, three
  times (wait for `#round-display` to change); click `#scrubber-toggle-button`; `#scrubber-panel` visible and
  `#scrubber-round-select option` count is 3; click `#scrubber-run-button`; wait until `#scrubber-result` text starts
  with "What-if:"; `#trend-graph .trend-line--whatif` count is 1; `page.page_errors == []`.
