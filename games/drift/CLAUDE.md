# Drift — Climate Migration & Displacement Game

**Built following the shared conventions in `planning/archive/climate-quartet-2-plan.md`** (moved there 2026-09-22 once all four second-set games shipped; was `climate-quartet-2-plan.md` at the games root while build order still mattered). This file is Drift-specific only. Built last in this set — the most systems-heavy and longest-timeline game across both sets, tackled once the other patterns were proven.

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
| 8 | PC version: a Desktop boot (`pc.html`, generated from `index.html`) with a full-window dashboard layout, windows for the long sections, a Desktop tutorial and the layout switch on the opening screen | Done (2026-10-07; see `planning/PC-VERSION-PLAN.md`) |

## Tech notes

- Python/Pyodide, per root conventions.
- This is the most conceptually sensitive game in either set — displacement and migration are real, ongoing human experiences, not just an abstract system. Keep language and framing (in-game text, UI labels, any narrative flavor) focused on institutional capacity and systems design rather than individual migrant stories, to avoid the game reading as speaking for or dramatizing real people's specific experiences.
- Model regional wellbeing as a small set of tracked sub-scores (service quality, economic health, social cohesion) rather than one blended number — keeps the composite scoring testable and keeps the end-state legible to the player.

## Working conventions

- Commit + tag per milestone: `git commit -m "Milestone N: <name>"` then `git tag drift-milestone-0N`.
- Update the milestone table Status as work happens.

## Standing constraints (short; the history is in `NOTES.md`)

- **Institutions, not individuals.** Text, labels and flavour talk about capacity, services and systems. Never individual migrant stories or named people.
- **Turn-based, nothing timed.** Every round is an active decision; there is no clock, timer or countdown. Animations (arrival dots, building pop, strain heartbeat, confetti, glossary sheet) are decorative and must stop under Reduce Motion and animation speed "Off" (`settings.js`, `style.css`).
- **No hue-only meaning.** Strain and wellbeing are also stated in words; the two trend lines differ by solid vs dashed.
- **Per-device settings are not saves.** Text size, Reduce Motion, density, skin, confirm threshold, tier bests, collection live in `localStorage` (`settings.js` is independent of Pyodide); `get_state()` holds only the current region.
- **A class that sets `display` must not defeat the `hidden` attribute.** `style.css` starts with the blanket `[hidden] { display: none !important; }`; panels start hidden and open from a toolbar button.

## File map (read this first; every file is small enough to read whole)

`game.py` was one 6,600-line file (300 KB). It is now an entry point plus 23 `drift_*.py` modules; the stylesheet and the page's inline scripts are split too (SP-1b in `planning/TODO.md`). Nothing changed in behaviour or in a save. Ask for the one file that holds what you are changing.

**Python (`drift_*.py`, listed in dependency order: a module imports only from the ones before it).** The list lives in ONE place that matters, `DRIFT_PY_MODULES` in `boot.js` (the page writes those files into Pyodide's file system before it runs `game.py`); `_PART_NAMES` in `game.py` repeats it in the same order, and `tests/test_file_sizes.py` checks both against the files on disk.

| File | Holds (ask for it when you change...) |
|------|------|
| `game.py` | Entry point. Imports the parts, re-exports every name (`game.<name>` still works for tests and the page), forwards live state, and `setup()` wires the buttons. Ask for it only to add a button listener. |
| `drift_runstate.py` | The variables that get REPLACED while playing (panel-open flags, notes, undo snapshots, `neighbor`, `assist_mode`, `glossary_open`, ...) and `LIVE_NAMES`. |
| `drift_rules.py` | Fixed numbers and tables: costs, `CAPACITY_TYPES`, `POLICIES`, strain thresholds, `CALENDAR_KINDS`, `COUNCIL_PROGRAMS`, autopilot choices, achievement thresholds, trend arrows and sparklines, number checkers (`_finite_number`). No state. |
| `drift_model_region.py` | `RegionState` (the engine: invest, policies, reallocate, `advance_round`, strain, integration, wellbeing, second wave, ledger rows) and the one live `region`. |
| `drift_regional.py` | The optional neighbouring district (open, invest, support, spillover) and the second-wave, policies and neighbour panels. |
| `drift_trendgraph.py` | The trend graph (layers, ranges, event markers, SVG), `wellbeing_band`, `wellbeing_curve`. |
| `drift_visuals.py` | Region picture (building counts and heights, building pop, strain heartbeat), pending pipeline, `_pulse`, `_set_pressed`. |
| `drift_messages.py` | Arrival dot stream sizes and every plain-language message: wellbeing, Uganda comparison, resettlement benchmark, checkpoint, forecast, ROI, coda, thriving, turning point. |
| `drift_achievements.py` | Achievements (catalog from `achievements.json`, checks, progress, glyphs, panel), the screen-reader `announce()`. |
| `drift_pages.py` | What's New changelog panel, the info page, personal best and learning readouts, the sourced real-world note, the localStorage read/write helpers. |
| `drift_ledger.py` | The Round Ledger (rows, sort, filter, CSV) and the round recap line. |
| `drift_calendar.py` | Perfect Fit, the Crisis Calendar with Surge Tests, the Mayor's Council tree, the spoken round summary. |
| `drift_collection.py` | Region collection (titles, civic milestones), region skins, the achievement-toast checks that unlock skins, star goals and the run history, `share_result()`. |
| `drift_undo.py` | Reset this round, the Rewind Token, Play 5 rounds. |
| `drift_tiers.py` | Difficulty tiers, per-tier bests, band helpers. |
| `drift_plans.py` | Budget Autopilot, the three budget templates, the run summary text and the civic-tools panel. |
| `drift_assist.py` | Planner assist (off, suggest, explain). |
| `drift_settings.py` | Confirm large moves, the manual-save nudge, glossary popovers (`GLOSSARY`). |
| `drift_loading.py` | The helpers `load_state()` uses to read each saved part safely, and the load note. |
| `drift_report.py` | The Region Report (data, text, HTML, copy, print), the band-rise confetti, `render_batch3()`. |
| `drift_newsview.py` | The local news line, the trend graph panel, the tab title. |
| `drift_renderer.py` | `render()`: redraws the whole page from the live `region`. |
| `drift_handlers.py` | Every `on_*` click/change handler, the `_make_*` handler factories and `setup_batch3()`. A new handler goes here. |
| `drift_savestate.py` | `get_state()`, `steward_summary()`, `load_state()`: the save format. |

**State rule.** A module variable that some function REPLACES (`global x` in the old file) lives only in `drift_runstate.py`; every other module reads and writes it as `runstate.x` (each module that needs one starts with `import drift_runstate as runstate`). Never `from drift_runstate import x` (that copies the value once and goes stale), and never `global`. Lists, dicts and sets that are only changed in place (`region`, `collection`, `run_history`, `autopilot_log`, `tier_bests`) stay in the module that owns them. A new rebound variable goes in `drift_runstate.py` AND in its `LIVE_NAMES`. Tests use `game.glossary_open`, `game.round_start_snapshot = ...`: `game.py` forwards reads and writes of the `LIVE_NAMES` to `drift_runstate`, and a write to any other name is copied into every module that holds it (so `game_env.module.announce = ...` works). There are no late-bound names: a new function goes in a module after everything it calls.

**Page files.** `index.html` is markup only (about 57 KB, the one file allowed above 14,000 tokens, capped at 15,000 by `tests/test_file_sizes.py`). Scripts, in load order: `tutorial-steps.js` (the walkthrough steps), `boot.js` (loads Pyodide, writes the Python modules, runs `game.py`, starts the tutorial and mobile HUD), `settings.js`, `ui.js` (phone view, swipe cards, term sheet, game keys; leave as is unless asked), `shortcuts.js` (panels the `?` help and Esc know), `feedback.js`, `result-copy.js` (Copy result button), and `pc.js` on the Desktop page. Styles load in this order (the order is the cascade; Desktop's `pc.css` goes after the first `style.css` link): `style-1-base.css`, `style-2-console.css`, `style-3-panels.css`, `style.css` (the last part: the blanket `[hidden]` rule, which must stay before the print rules, then the batch 3 panels and the phone view). Put a new rule in the part for its area. `pc.html` is generated (`scripts/generate-pc-pages.py`), never edited by hand. `tests/pagefiles.py` has `game_css()`, `page_text()`, `game_source()` and `notes_text()` for tests that need the whole stylesheet, page, Python or notes text.

## For the local AI (exact names, all grepped against the code on 2026-10-18)

Drift has no `handle()` action list and no view dict: the Python reads the live `region` (a `RegionState`) and writes the DOM directly. Never invent a name; grep it first.
- **Entry points.** Every button is wired once in `setup()` in `game.py` (`document.getElementById(id).addEventListener("click", create_proxy(handler))`); the batch-3 ones (tiers, assist, confirm threshold, glossary, report, save nudge) in `setup_batch3()` in `drift_handlers.py`. Handlers are the `on_*(event=None)` functions and the `_make_*_handler(arg)` factories there. The ids: `advance-round-button`, `housing-invest-button` / `services-invest-button` / `infrastructure-invest-button`, `policy-credentialing-button` / `policy-language-access-button` / `policy-sponsorship-button`, `realloc-button`, `coda-button`, `reset-round-button`, `rewind-button`, `play-rounds-button`, `calendar-brace-button`, `autopilot-run-button`, `neighbor-open-button`, `neighbor-support-button`, `neighbor-<capacity>-button`, `council-pick-<branch>` (`education`, `housing`, `transit`), `skin-<id>-button`, `tier-<id>-button`, `assist-<mode>-button`, `template-<1..3>-save|apply|name`, `trend-range-<10|25|all>-button`, `trend-layer-<layer>-button`, `region-name-input`.
- **Engine verbs** (`RegionState`, `drift_model_region.py`; `game.region` is the one live object): `invest(capacity_type)` (`"housing"`, `"services"`, `"infrastructure"`), `invest_policy(policy)`, `reallocate(from_type, to_type)`, `advance_round(auto=False)`, `brace()`, `set_crisis_start(enabled)`, `calendar_event(round_number=None)`; readouts `total_capacity()`, `arrivals_this_round()`, `strain_fraction()`, `strain_level()`, `pending_population()`, `service_quality()`, `economic_health()`, `social_cohesion()`, `wellbeing_score()`, `total_invested()`, `investment_roi()`. Module-level actions: `reset_round()`, `use_rewind_token()`, `play_rounds(count)` (`drift_undo.py`), `apply_tier(tier_id)`, `set_assist_mode(mode)`, `save_template(slot, name)`, `apply_template(slot)`, `autopilot_run()`, `council_pick(branch)`, `choose_skin(skin_id)`, `open_neighbor()`, `invest_neighbor(capacity_type)`, `support_neighbor()`.
- **Python the page may call** (`window.pyodide.globals.get(name)`): `get_state`, `load_state`, `share_result` (the Copy result button in `result-copy.js`), `render` (the boot check). `boot.js` also puts `window.ACHIEVEMENTS_JSON` and `window.CHANGELOG_JSON` where the Python reads them at import. To give JS a new value add a function; never read a Python variable by name from JS (a replaced variable goes stale).
- **get_state()** (`drift_savestate.py`) holds only the current region: `round_number funds capacity background_severity total_arrivals arrivals_log strain_log strain_sum strain_count ever_critical_strain wellbeing_log integrated_population cumulative_services_investment cumulative_integration_contribution net_positive_round current_stable_streak best_stable_streak thriving_round coda_ever_viewed last_milestone_round last_milestone_snapshot accelerated_severity_enabled severity_toggle_dot_baseline severity_density_callout_shown subscore_log region_name coda_legacy_choice crisis_start_enabled coda_visible info_page_open wellbeing_score summary achievements_earned`, plus `policy_level learning_active second_wave roi_log` and the neighbour, ledger and assist fields only when not default. `load_state(data)` reads every key with `.get` and a safe fallback and returns `False` for a non-dict; keep it that way (old saves must load). `wellbeing_score`, `summary` and `achievements_earned` are write-only.
- **Redraw.** `render()` (`drift_renderer.py`) redraws the whole page from `region` and calls every panel's `render_*()`. A handler that changes the region ends with `render()` (see `on_advance_round`); one that only opens, closes or filters a panel calls just that panel's function (`on_toggle_ledger` calls `render_ledger()`). The load path calls `render()` too.
- **Main ids.** Readouts `round-display funds-display total-capacity-display arrivals-display total-arrivals-display strain-display strain-bar integrated-display pending-display service-quality-display economic-health-display social-cohesion-display wellbeing-display wellbeing-message-display net-positive-badge`, the region picture `region-visual-building-a` (to `f`), the trend graph `trend-graph`; panels `howto-panel achievements-panel changelog-panel ledger-panel collection-panel report-panel settings-panel info-page-panel coda-section`, each opened by its `*-toggle-button` (the coda by `coda-button`).
- **A new panel/button.** (1) markup in `index.html` (hidden by default with the `hidden` attribute, a visible button that opens it, a way to close it); (2) add every id Python looks up to `ELEMENT_IDS` in `tests/conftest.py` (the fake DOM raises `KeyError` for an unknown id); (3) an open flag in `drift_runstate.py` (and `LIVE_NAMES`), an `on_toggle_<name>` handler in `drift_handlers.py` with its listener in `setup()`, and a `render_<name>()` in the feature module that `render()` calls (copy `render_ledger`); (4) `shortcuts.js` `panels` list so Esc closes it; (5) `pc-config.json`: a window is `[panel-id, button-id, "Title"]` in `windows` and the button id goes in `toolbar.menu`, otherwise add the id to `zones.side` or a `composites` entry; (6) the human then runs `scripts/generate-pc-pages.py` (never edit `pc.html`); `shared/tests/test_pc_games.py` checks the config, the ids and that `pc.html` is current. A new Python module goes into `DRIFT_PY_MODULES` (`boot.js`) and `_PART_NAMES` (`game.py`) in the same position, after everything it imports; not `sw.js`.
- **Tests that pin things.** `test_file_sizes.py` (token cap per file, module lists, import order, no `global`), `test_save_system.py` (save keys and round trip, malformed saves), `test_core_loop.py`, `test_achievements.py` (`achievements.json`), `test_changelog.py` (`changelog.json`), `test_batch3_pages.py` (every id the batch 3 code looks up is in the fake DOM), `test_round3_oct7.py` and `test_round3_oct8b.py` (Desktop windows), `test_wiring_oct8.py`, `test_ai_*.py` (phone view, term sheet, advance ring: they compare `index.html`, `style.css`, `ui.js` and `GLOSSARY`, so keep those ids and classes). The fake DOM is `tests/conftest.py` (`game_env` fixture: `.module`, `.region`, `.advance_round()`, `.invest(capacity_type)`, `.toggle_coda()`, `.set_strain_log(values)`); tests that read page text use `tests/pagefiles.py`.
- **Browser tests.** Copy `tests/test_example_browser.py` (`from browser_helpers import open_game`; `base` is a fixture from `conftest.py`): it boots the page, clicks `#housing-invest-button`, asserts `#total-capacity-display` and `#funds-display` changed and `page.page_errors == []`. The two `test_ai_*_browser.py` files start their own server (phone width).
- **Do not.** Invent a name, id or action. Use `global` or `from drift_runstate import x` (use `runstate.x`; a rebound variable also goes in `LIVE_NAMES`). Add a `get_state()` key without a safe `.get(...)` fallback in `load_state()`, or put a per-device setting in the save. Add timers, countdowns or audio; every effect must be off under Reduce Motion, and the framing stays institutional (no individual migrant stories). Edit `pc.html`, `sw.js`, `offline-manifest.json`, or `ui.js` and its `test_ai_*` tests unless the task is about the phone view.

## Long history

The long history (per-item build notes, audit logs, site-wide-goal write-ups) was moved out of this file on 2026-10-18 into `NOTES.md` in this folder. Do not read it whole: grep its `## ` headings and read only the section you are told to.
