# Thaw — Permafrost Feedback Loop Game

**Built following the shared conventions in `planning/archive/climate-quartet-2-plan.md`** (moved there 2026-09-22 once all four second-set games shipped; was `climate-quartet-2-plan.md` at the games root while build order still mattered). This file is Thaw-specific only. Built second in this set.

## Concept

The player manages a northern region while global temperature rises on a fixed background trajectory they don't fully control. As it rises, permafrost gradually melts, releasing stored methane — which accelerates the same warming trajectory further. The player's regional choices (land management, local emissions) can nudge the timeline, but the core experience is watching a slow problem tip into a runaway feedback loop if nothing meaningfully intervenes.

## Function tag: Futures on the current path

This game exists to simulate what happens if things continue as they are. Unlike Grid or Herd, the player isn't the primary driver of the central meter — the background trajectory moves largely on its own, and the player's job is to understand and respond to a system bigger than their direct control. This is deliberately different from the other games' "your choices are the whole story" framing.

## Climate issue & hope angle

**Issue:** permafrost thaw and the methane-release feedback loop.
**Hope angle:** this is the game in the whole hub most at risk of reading as pure doom, because feedback loops are inherently runaway-danger mechanics — treat the hope angle here as a hard design requirement, not a nice-to-have. Give the player a real, visible lever (regional emissions reduction, permafrost-preserving land management) that measurably slows the loop's acceleration, even if it can't fully stop the background trajectory. The message should land as "intervention changes the slope, and the slope matters enormously" — not "nothing you do matters."

## Core loop

- Turn-based rounds. Background global temperature rises on a fixed schedule each round, independent of the player.
- As temperature crosses thresholds, permafrost in the player's region begins melting, releasing a methane pulse that adds to the background warming rate (this is the feedback — warming causes melt causes more warming).
- Player allocates regional resources between: local output/growth (immediate benefit, adds marginally to global emissions), permafrost-preserving measures (slows local melt rate), and monitoring/early-response infrastructure (reduces damage from melt events when they happen).
- Feedback loop is visible as an accelerating rate, not just a rising number — the meter's *slope* should visibly steepen once the loop kicks in, so players feel the moment it tips.
- No hard fail-state, but a region that lets the loop run unchecked should end a session in a visibly worse, harder-to-manage state than one that intervened early — same "delay compounds cost" pattern as Grid, but framed around a feedback mechanism instead of a linear meter.

## Standing rules a change must not break
- **Hope angle (a hard requirement).** Intervention must visibly change the slope: preserving and monitoring measurably slow the feedback loop's acceleration, and the end-of-session comparison against the undampened `counterfactual_temperature` must stay (`tests/test_hope_angle_payoff.py`, `tests/test_visible_acceleration.py`). No hard fail-state: an unchecked loop ends in a worse, harder state, never a game over. Turn-based; nothing is timed.
- **Saves.** `get_state()` (`thaw_savestate.py`) and `load_state()` (`thaw_loading.py`, validation in `thaw_saveparts.py`) must load an old save that lacks any new key; corrupt saves recover (`tests/test_corrupt_save_recovery.py`). New keys are written only when non-default (the existing code writes `hard_mode`, `carbon_bank`, `long_game` ... only when set). `summary`, `achievements_earned` and `unranked` are write-only (never read back). Personal best and the climate archive (`thaw_records.py`) live in localStorage, never in a save; per-device display settings too.
- **Speed.** Auto-playing Region D must stay closed-form (`funds // cost`, not a loop of `invest()` calls): `tests/test_worst_case_perf.py` fails on an exponential slowdown.
- No audio files; every new effect respects reduced motion and has an off switch. The page reads live numbers through Python functions, never `pyodide.globals.get("<state variable>")`.
- The module list lives in `THAW_PY_MODULES` in `boot.js`; `_PART_NAMES` in `game.py` repeats it in the same order; `tests/test_file_sizes.py` checks both against the files on disk and the import order. A variable that a function REPLACES lives in `thaw_runstate.py` (and `LIVE_NAMES`), read as `runstate.x`.
- No file the AI may edit may pass about 14,000 estimated tokens (`tests/test_file_sizes.py`); `index.html` is capped at 15,000. `pc.html` is generated, never edited by hand.

## Milestones

| # | Milestone | Content | Status |
|---|-----------|---------|--------|
| 1 | Background trajectory + core loop | Fixed-schedule temperature rise, regional resource allocation across rounds. Tests: temperature progression, allocation logic | Done |
| 2 | Permafrost melt + methane feedback | Melt triggered by temperature thresholds, methane pulse feeds back into warming rate. Tests: melt-threshold logic, feedback-rate calculation | Done |
| 3 | Intervention measures | Preserving/monitoring investments that measurably slow the feedback loop's acceleration. Tests: slope-reduction formula per measure | Done |
| 4 | Visible acceleration | Surfacing the loop's steepening slope to the player clearly (not just a bigger number, a visibly faster-rising one). Tests: slope-calculation and threshold-crossing detection | Done |
| 5 | Hope-angle payoff | End-of-session comparison showing early intervention produced a meaningfully flatter trajectory than inaction. Tests: comparison calculation across sample playthroughs | Done |
| 6 | In-game feedback prompt | Piped to Neon backend per root conventions | Done |
| 7 | Visual/UI pass + hub integration | | Done — all 7 milestones complete |
| 8 | PC version: a Desktop boot (`pc.html`, generated from `index.html`) with a full-window dashboard layout, windows for the long sections, a Desktop tutorial and the layout switch on the opening screen | Done (2026-10-07; see `planning/PC-VERSION-PLAN.md`) |

## File map (read this first; every file is small enough to read whole)

`game.py` was one 6,700-line file. It is now an entry point plus 23 `thaw_*.py` modules, and the stylesheet and the page's inline scripts are split too (SP-1d in `planning/TODO.md`; the recipe is in `planning/SHARED-COMPONENTS.md`). Nothing changed in behaviour or in a save. Ask for the one file that holds what you are changing.

**Python (`thaw_*.py`, listed in dependency order: a module imports only from the ones before it).** The list lives in ONE place that matters, `THAW_PY_MODULES` in `boot.js` (the page writes those files into Pyodide's file system before it runs `game.py`); `_PART_NAMES` in `game.py` repeats it in the same order, and `tests/test_file_sizes.py` checks both against the files on disk.

| File | Holds (ask for it when you change...) |
|------|------|
| `game.py` | Entry point. Imports the parts, re-exports every name (`game.<name>` still works for tests and the page), forwards live state, and `setup()` wires the buttons. Ask for it only to add a button listener. |
| `thaw_runstate.py` | The variables that get REPLACED while playing (`hard_mode`, `carbon_bank`, `run_over`, panel-open flags, forecast counters ...) and `LIVE_NAMES`. |
| `thaw_rules.py` | Fixed numbers and tables: costs, thresholds, policy stances, tiers, titles, storage keys, planner and forecast limits. |
| `thaw_model.py` | `RegionState` (one region: funds, temperature, melt feedback, restoration, rescue), `region`, `region_b`, `region_c`, `region_d`, the warming-rate helpers and the run-mode helpers. The feedback-loop maths lives here. |
| `thaw_bridge.py` | Tiny helpers: localStorage read/write, HTML escape, number cleaning, curve decimation. |
| `thaw_sciencelog.py` | The scientist's log (events, pinning, filter, search, text export) and the automated Region D play. |
| `thaw_presets.py` | Strategy presets, the custom preset slot, the spend-confirmation threshold, hard mode, best-region message. |
| `thaw_graphs.py` | Mini temperature graphs (SVG, crosshair data, screen-reader summary), trend and melt labels, Region B/C/D card rendering. |
| `thaw_mechanics.py` | Tipping cascades, carbon bank, supply crates, shared research, framing, long game, the thaw forecast mini-game. |
| `thaw_records.py` | Personal best and the climate archive (localStorage only, never in a save). |
| `thaw_achievements.py` | Achievements (catalog loading, checks, progress, panel, toast) and the map skins they unlock. |
| `thaw_panels.py` | Info page render, What's New changelog, community comparison, climate scientist chart, compare history. |
| `thaw_readouts.py` | Routing convoys, balance bonus, ice-age tier, sparklines, round announcement, rate inspector, highlights and share result, temperature unit, session note. |
| `thaw_runs.py` | Hold the Line (run end, titles), AI stewards, Field Notes, compare overlay, run result list. |
| `thaw_views.py` | The sortable region board and the single-region focus view. |
| `thaw_saveparts.py` | Save validation (`sanitize_save`, load notice) and the per-region save dict and loader. |
| `thaw_timeline.py` | Forecast planner, one-rewind undo, round replay. |
| `thaw_flavour.py` | Headlines, glossary, rolling temperature digits, mascots. |
| `thaw_pace.py` | Pace line and ghost sentence (best-run record). |
| `thaw_settingscode.py` | Copyable settings code (export, decode, import, re-apply). |
| `thaw_savestate.py` | `get_state()`, `steward_summary()`, the developer history readout. |
| `thaw_renderer.py` | `render()`: redraws the whole page, calling every panel's render function. |
| `thaw_loading.py` | `load_state()`: restores a save, then redraws. |
| `thaw_handlers.py` | Every `on_*` click handler and the `_make_*_handler` factories. A new handler goes here. |

**State rule.** A module variable that some function REPLACES with `global x` / `x = ...` lives only in `thaw_runstate.py`; every other module reads and writes it as `runstate.x` (each module starts with `import thaw_runstate as runstate`). Never `from thaw_runstate import x` (that copies the value once and goes stale). Lists, dicts and sets that are only changed in place (`science_log`, `field_notes`, the region objects) stay in the module that owns them. A new rebound variable goes in `thaw_runstate.py` AND in its `LIVE_NAMES`. Tests use `game.hard_mode`, `game.carbon_bank = 5` and so on: `game.py` forwards reads and writes of the names in `LIVE_NAMES` to `thaw_runstate`, and a write to any other name is copied into every module that holds that name.

**Page files.** `index.html` is markup only (about 57 KB, the one file allowed above 12,000 tokens, capped at 15,000 by `tests/test_file_sizes.py`). Scripts: `tutorial-steps.js` (the walkthrough steps), `boot.js` (loads Pyodide, writes the Python modules, runs `game.py`, starts the tutorial and mobile HUD), `feedback.js` (the yes/no feedback prompt), `community-compare.js` (`window.thawCompare`), `graph-crosshair.js` (hover/arrow-key readout on the mini graphs), `shortcuts.js` (panels for the `?` help), then the older `settings.js`, `mobile-invest.js`, `focus-mode.js`, `landscape-grid.js`, `info-page-swipe.js`, `archive-swipe.js`, `haptic-feedback.js`, `pc.js`. Styles load in this order (the order is the cascade; Desktop's `pc.css` goes after the first `style.css` link): `style-1-base.css` (text scale, page shell, meters, base panels), `style-2-visuals.css` (permafrost scene, section cards, gauges, console design pass), `style-3-panels.css` (changelog, settings panel, round-2 and round-3 panels), `style-4-features.css` (achievement cards, skins, crates, board, focus, planner, replay, glossary, crosshair, mascots, phone focus mode), `style.css` (the last part: Real Story cards, phone planner, landscape board). Put a new rule in the part for its area. `pc.html` is generated (`scripts/generate-pc-pages.py`), never edited by hand. `tests/pagefiles.py` has `game_css()` and `page_text()` for tests that need the whole stylesheet or page text.

## For the local AI: exact names (verified against the code, 2026-10-18)
Thaw has no `handle()` and no view dict: it is DOM-driven. The regions are objects (`RegionState` in `thaw_model.py`); a click handler in `thaw_handlers.py` changes one, then calls `render()`. The page code reaches Python only through `get_state`, `load_state` and a few functions looked up with `pyodide.globals.get(name)`.
- **Regions:** `region` (the main one), `region_b`, `region_c` (`SECONDARY_REGIONS = {"b": region_b, "c": region_c}`), and `region_d` (the auto-played worst-case region). `CATEGORIES = ["output", "preserve", "monitor"]` (`thaw_rules.py`). `RegionState` attributes: `round_number funds capacity (dict by category) temperature counterfactual_temperature temperature_history melt_started_round strategy_label`.
- **Engine methods (`RegionState`, argument names exact):** `invest(category)` (returns False if it cannot pay), `advance_round()`, `choose_policy_stance(key)` (`growth` ... see `POLICY_STANCES` in `thaw_rules.py`), `can_choose_policy_stance()`, `rescue()`, `can_rescue()`, read-only `is_melting()`, `is_critical()`, `acceleration_factor()`, `temperature_saved()`, `current_rise_rate()`, `feedback_dampening_fraction()`. Module functions: `set_hold_the_line(enabled)`, `set_hard_mode(enabled)`, `set_long_game(enabled)`, `apply_preset(r, preset_name)` (`growth` `preservation` `balanced`, `PRESET_WEIGHTS`), `lock_forecast(raw)`, `open_crate()`, `set_skin(skin_id)`, `set_temp_unit(unit)`, `undo_last_round()`, `check_run_end()`.
- **Click handlers (`thaw_handlers.py`):** `on_advance_round` (runs `region.advance_round()`, the secondary regions, tipping cascades, carbon bank, checks the run end, then `render()`), factories `_make_invest_handler(category)`, `_make_secondary_invest_handler(prefix, category)`, `_make_policy_stance_handler(key)`, `_make_rescue_handler(prefix)`, `_make_preset_handler(prefix, preset_name)`, plus `on_toggle_<panel>`, `on_undo`, `on_copy_highlights`, `on_open_crate`. Every listener is attached in `setup()` in `game.py` by element id.
- **`get_state()` keys always written:** `region region_b region_c region_d info_page_open worst_case_region_revealed preset_used_ever worst_case_intro_seen science_log summary achievements_earned`. Written only when set: `forecast hard_mode custom_preset carbon_bank framing long_game hold_the_line run routing balance_bonuses undo_used crates unranked`. Each region dict comes from `_region_state_dict(region)` in `thaw_savestate.py`; read it before adding a field.
- **Redraw.** `render()` in `thaw_renderer.py` redraws the whole page from the live regions and calls every panel's render/update function (`render_secondary_region`, `render_board`, `update_changelog_display`, ...). Call it after any state change. Elements you add to a redrawn region must be added inside the function `render()` calls, not once.
- **Ids.** Main region: `round-display funds-display temperature-display temperature-trend advance-round-button` and `output-invest-button preserve-invest-button monitor-invest-button` (they read "Loading..." and are disabled until `render()` has run once); Region B and C use the prefixes `b-` and `c-` (`b-output-invest-button`). Announcer: `sr-announcer`. Panels `<x>-panel` (hidden) opened by `<x>-toggle-button`: `howto achievements changelog community-compare climate-scientist settings info-page archive worst-case`.
- **New panel.** (1) `index.html`: `<button id="x-toggle-button">` and `<div id="x-panel" hidden>`; (2) `x_open = False` in `thaw_runstate.py` AND `LIVE_NAMES`; (3) `on_toggle_x` in `thaw_handlers.py` and `update_x_display()` (sets `panel.hidden = not runstate.x_open`; model: `on_toggle_changelog` and `update_changelog_display` in `thaw_panels.py`), with the updater called from `render()`; (4) the `addEventListener` line in `setup()` in `game.py`; (5) `pc-config.json`: `["x-panel", "x-toggle-button", "Title"]` in `windows` and the button id in a `toolbar.menu` group (check: `shared/tests/test_pc_games.py`), then the human runs `scripts/generate-pc-pages.py`. A new Python module goes at its dependency position in BOTH `THAW_PY_MODULES` (`boot.js`) and `_PART_NAMES` (`game.py`); the AI does NOT edit `sw.js` / `offline-manifest.json` (report it).
- **Tests that pin things you may change:** `tests/test_file_sizes.py` (module lists, import order, 14k tokens, index.html 15,000, stylesheet order), `tests/test_changelog.py` (`changelog.json`), `tests/test_achievement_cards.py` and the achievements tests (`achievements.json`), `tests/test_core_loop.py`, `tests/test_visible_acceleration.py`, `tests/test_hope_angle_payoff.py` (core numbers), `tests/test_save_system.py` and `tests/test_corrupt_save_recovery.py` (saves), `tests/test_worst_case_perf.py`, `tests/test_wiring_oct8.py`, `tests/test_info_page.py`, `shared/tests/test_pc_games.py` (every id `game.py` looks up must exist in both pages).
- **Browser tests.** `tests/browser_helpers.py` + `tests/test_example_browser.py`: copy `tests/test_example_browser.py` for a new browser test (`from browser_helpers import open_game`; the `base` fixture comes from `conftest.py`). After `open_game`, wait until `#output-invest-button` no longer reads "Loading...".
- **Do not:** invent a state key, region attribute or element id (grep `thaw_model.py`, `thaw_savestate.py`, `index.html` first); read a Python variable from JS by name (add a function); rebind a module variable outside `thaw_runstate.py`; add a save key that is always written (non-default only, validated on load); change the feedback-loop maths without reading `tests/test_core_loop.py` and `tests/test_visible_acceleration.py`; edit `pc.html`, `sw.js`, `shared/` or another game.

## Long history
The long history, per-item build notes and audit logs are in `NOTES.md` (same folder). Read only the section you are told to: `grep -n "^## " NOTES.md` lists them.
