# Canopy — Deforestation & Carbon Sinks Game

**Built following the shared conventions in `planning/archive/climate-quartet-plan.md`** (testing, feedback hook, hope-angle requirement, hub integration — moved there 2026-09-22 once all four quartet games shipped; was `climate-quartet-plan.md` at the games root while build order still mattered). This file is Canopy-specific only. This was the first of the four built, establishing the pattern the others followed.

## Concept

A single forest region divided into a grid of plots. Each plot can be cleared (for quick resource income), left alone (slow passive value growth), or replanted (recovery after clearing, slower than never-cleared). Combines active management (clicking individual plots) with passive/idle accumulation (value compounds over time on preserved/replanted plots).

## Climate issue & hope angle

**Issue:** land-use change and loss of carbon sinks.
**Hope angle:** replanting must visibly work — a cleared plot that gets replanted should recover, just more slowly than if it had never been cleared. The game needs an end-state or late-game moment where a mostly-preserved/restored forest is clearly thriving (a visible "if you'd done this from day one" or "recovery is real, just slower" signal), not just a number going up.

## Core loop

- One forest region, rendered as a grid of individual plots (not one abstract meter — the spatial layout matters for the "some plots recovering, some still bare" visual).
- Player can click a plot to: clear (immediate resource payout, plot becomes bare), preserve (do nothing, passive value accrues), replant (costs a little, starts a slower recovery timer).
- Passive value compounds the longer a plot stays intact — a multiplier that grows over time, not a flat rate, so patience is rewarded increasingly.
- Cleared plots degrade in *future* yield potential (soil quality drops) — clearing repeatedly on the same plot gets worse, not better, over time.
- No fail-state. It's a comparison game — the player accumulates two visible numbers over a session: total short-term resource income vs total standing forest value — and can watch how the balance shifts depending on their play style.

## Standing rules a change must not break
- **Hope angle and no fail-state.** A replanted plot must visibly recover (slower than a never-cleared one) and a mostly-preserved forest must visibly thrive; clearing is allowed and pays, repeated clears degrade soil, but the player never loses and nothing punishes exploring. The comparison "short-term income vs standing forest value" must stay legible (`tests/test_comparison_scoring.py`). Passive growth runs on a fixed one-second `tick()`; Survey mode freezes time, and no new feature may add a countdown the player must beat.
- **Saves.** `get_state()` (`canopy_savestate.py`) and `load_state()` (`canopy_loading.py`) must load an old save that lacks any new key: read each field with a default, validate it, merge into the live objects (the plot list is zipped onto plots rebuilt at the saved grid size first). New keys only when non-default. `achievements_earned` and `standing_value` are write-only (ignored on load). Meta-progress (personal best, legacy bonus, levels done, Seed Vault, bests, achievements) lives in localStorage, never in the save. Per-device settings and display preferences go in localStorage too.
- The page reads live numbers through Python functions (for example `community_field_value`), never `pyodide.globals.get("<state variable>")`. No audio files; every new effect respects reduced motion and has an off switch.
- Two lists must always match: `_PART_NAMES` in `game.py` and `CANOPY_PY_MODULES` in `boot.js` (and the files on disk): `tests/test_module_list.py`. A function that calls `render()` (even indirectly) lives in `canopy_renderer.py` or a `canopy_handlers_*` module; modules before it only draw or compute. A variable that a function REPLACES lives in `canopy_runstate.py` (and `LIVE_NAMES`), read as `runstate.x`.
- No file the AI may edit may pass about 14,000 estimated tokens (`tests/test_file_sizes.py`); `index.html` is capped at 15,000. `pc.html` is generated, never edited by hand.

## Milestones

| # | Milestone | Content | Status |
|---|-----------|---------|--------|
| 1 | Grid + plot states | Grid of plots, each with a state (bare/preserved/replanting/recovered), basic click interactions. Tests: state transitions per plot action | Done |
| 2 | Passive value accumulation | Compounding value formula for preserved/recovered plots. Tests: value-growth-over-time calculation | Done |
| 3 | Clearing payout + soil degradation | Resource payout on clear, degrading future yield on repeated clearing of the same plot. Tests: payout calculation, degradation stacking | Done |
| 4 | Replant recovery timer | Replanted plots recover on a slower timeline than never-cleared ones, reaching near-parity eventually. Tests: recovery timer logic, near-parity threshold | Done |
| 5 | Comparison scoring + hope-angle payoff | Surfacing the short-term-income vs standing-forest-value comparison clearly at session end. Tests: comparison calculation across sample play logs | Done |
| 6 | In-game feedback prompt | Piped to Neon backend per root conventions | Done |
| 7 | Visual pass + hub integration | Grid rendering, plot state icons/colors, session summary screen | Done — all 7 milestones complete |
| 8 | Desktop boot (PC version plan): `pc.html` generated from `index.html`, plot grid as the stage, side column for plot actions and requests, readout chips, windows for every panel | Done (2026-10-06) — see "Desktop boot" below |

## File map (read this before editing; the game is split into small files, 2026-10-18)

The old 499 KB `game.py`, the 95 KB `index.html` and the 92 KB `style.css` were cut into files a small model can read whole. Nothing the AI may edit passes about 14,000 estimated tokens (bytes / 4); `tests/test_file_sizes.py` fails if a file does (the generated `pc.html` and `.json` data are exempt; `index.html` has a documented cap of 15,000: it is about 59 KB of real markup with no seam to cut). Behaviour did not change: every name the old `game.py` had is still `game.<name>`, saves are identical, the page looks identical.

**Python.** `game.py` is the entry point: it imports the modules in dependency order (a module only imports from earlier ones) and re-exports every name (`game.get_state`, `game.render`, `game.Plot` ...). **The module list lives in two places that must match**: `_PART_NAMES` in `game.py` and `CANOPY_PY_MODULES` at the top of `boot.js`. A new module also goes into `sw.js` and `offline-manifest.json`. `tests/test_module_list.py` checks both lists, the files on disk and the import order. A function that (even indirectly) calls `render()` lives in `canopy_renderer.py` (the cycle with `render`) or in the `canopy_handlers_*` modules after it; everything before only draws or computes.

| File | Size | What it holds, and when to ask for it |
|------|------|---------------------------------------|
| `canopy_runstate.py` | 12 KB | The live state: every module variable that gets REPLACED while playing (income, selected plot, panel-open flags, region and level state ...) plus `LIVE_NAMES`. Ask for it to add a new rebound variable. |
| `canopy_rules.py` | 17 KB | Fixed numbers and content tables for the core rules: grid sizes, difficulty, plot states, seasons, the Forest Lab numbers, maturity, stakeholder and specialist constants, tree species, neighbour synergy. No browser calls. Ask for it to change a rate, threshold or table of the core rules. |
| `canopy_worldvars.py` | 15 KB | Constants and in-place collections for the later features (regions, golden seedling, tend, weather, challenges, contracts, display options, rival logging), plus the variables those features keep. Rebound variables are in canopy_runstate. Ask for it to change a constant or table of a later feature. |
| `canopy_helpers.py` | 14 KB | Small shared helpers: tile ids and coordinate labels, localStorage reads and writes, SVG text and sparklines, the forest log entry, the screen-reader announcer queue, timed callbacks, number formatting and display preferences. Ask for it to change shared formatting, storage or announcer helpers. |
| `canopy_valuation.py` | 4 KB | Standing forest value, biodiversity, active plot counts, clear counts and the playstyle badge: the numbers many panels read. |
| `canopy_records.py` | 9 KB | Personal best and the legacy bonus (both kept in localStorage, never in the save). |
| `canopy_weather.py` | 5 KB | Seasons, rain and drought episodes, the perfect-season streak and the end of a season. |
| `canopy_effects.py` | 9 KB | The small multipliers that feed a plot's growth, recovery and payout: carbon slump, legacy bonus, weather, perfect streak, clear-cut dip, Seed Vault perks and Expedition perks (with their trees). Ask for it to change what feeds a plot's growth or payout. |
| `canopy_clearcut.py` | 5 KB | Clear-cut soil dips (GB-21): healing, preview, the harvester badge and the panel. |
| `canopy_plot.py` | 13 KB | The Plot class (one forest plot: state, value, growth, degradation) and the plot grids built from it. Ask for it to change how one plot grows, degrades or pays. |
| `canopy_forestlog.py` | 4 KB | The forest log and wildlife log lines, and the specialist and adopt panels. |
| `canopy_gridview.py` | 6 KB | Plot tile colours, tooltips, tile marks and the stats panel render (render_grid itself is in canopy_renderer). |
| `canopy_carbon.py` | 4 KB | The carbon credit market (GB-29): price, trend, selling and the chart. |
| `canopy_lifetime.py` | 16 KB | Lifetime stats, the Forest Rank (XP, frames, palettes) and My Forests comparison. |
| `canopy_community.py` | 4 KB | The community plot (shared growth pool) and its note. |
| `canopy_layout.py` | 11 KB | Custom plot layouts (B-29): presets, saved layouts, bests and the editor. |
| `canopy_stakeholders.py` | 21 KB | Stakeholder requests (trigger, message, counter-offer plan), stakeholder faces and friendship, request history and the stakeholder panel render. |
| `canopy_plotsheet.py` | 4 KB | Plot notes and the phone bottom sheet. |
| `canopy_regions.py` | 12 KB | The Highland Grove and the Wetland Forest: unlocking, tides and floods, tooltips, stats and panels. |
| `canopy_summary.py` | 15 KB | The session summary pieces: breakdown text, counterfactual, history sparkline, share text, replay and the forest card. |
| `canopy_labui.py` | 5 KB | The Forest Lab panel (B-5): sliders, saved variants and renders. |
| `canopy_achievements.py` | 19 KB | Achievements (catalog, checks, progress, toast, grove wall). Ask for it to add or change an achievement or the toast. |
| `canopy_infopanels.py` | 11 KB | The What's New changelog, the example playthrough and The Real Story info page. |
| `canopy_ghost.py` | 7 KB | The best-session ghost (Z-3e): recording, banking and comparison. |
| `canopy_charts.py` | 12 KB | The report card and timeline charts, the forest log panels and the ghost toggle. |
| `canopy_realworld.py` | 7 KB | The sourced real-world note, the grid-size select render and the badge source copy. |
| `canopy_forecast.py` | 7 KB | The season indicator, the screen-reader announcer, selection announcements and the season forecast. |
| `canopy_tend.py` | 9 KB | Golden seedlings, Tend, the Heart Tree, forest and plot names, and Undo clear. |
| `canopy_challenge.py` | 13 KB | Scenarios (clear-cut start, remnant) and challenges (Pacifist, Scorched, Sprint ...): records, goals, status and badges. |
| `canopy_almanac.py` | 10 KB | Rare wildlife, milestone tiers and forest titles, chain bloom, and the Forest Almanac. |
| `canopy_contracts.py` | 13 KB | Ranger contracts: board, progress, rewards and the panel, plus their save fields. |
| `canopy_levels.py` | 29 KB | Levels mode: the level specs, poacher, storm and spirit runs, level status, and the Seed Vault points that levels earn. |
| `canopy_vault.py` | 9 KB | The Seed Vault (GB-10/GB-26) and crew helpers, and the loaders for levels and vault saves. |
| `canopy_expedition.py` | 15 KB | The Expedition (GB-3): seeded map, perks tree, scoring, bests and renders. |
| `canopy_gbstate.py` | 6 KB | Per-tick hooks for the GB features, the reset of their state and the loader for it. |
| `canopy_survey.py` | 8 KB | Tree species choice, forest switching and Survey mode (plan clears and replants, then commit). |
| `canopy_hazards.py` | 17 KB | Blight, wildfire and the rival logging company: state, per-tick rules and renders. |
| `canopy_session.py` | 3 KB | Reset Session confirm text and the reset button render (reset_session itself is in canopy_renderer). |
| `canopy_comfort.py` | 8 KB | Comfort features: the slow-computer guard, the coach hints and the while-away chip. |
| `canopy_sessionview.py` | 8 KB | Saved playstyle runs and their comparison, the session summary panel and the stats line. |
| `canopy_savestate.py` | 16 KB | get_state(): everything that goes into a save, and the plot and region dictionaries. Ask for it to change what a save holds. |
| `canopy_renderer.py` | 45 KB | render() and the functions that call each other with it (reset_session, render_grid, the region, level, vault and expedition renders and their button handlers). They form one cycle, so they live together. Ask for it to change render() or the grid, region, level, vault and expedition renders. |
| `canopy_handlers_core.py` | 13 KB | Click handlers for plots and regions (clear, replant, tend, names, undo, hotkeys, survey queue). |
| `canopy_handlers_panels.py` | 14 KB | Click handlers for the panels (reset, difficulty, stakeholder requests, notes, sheet, carbon, layout, lab, specialist, adopt, pace, scenario, challenge). |
| `canopy_handlers_modes.py` | 11 KB | Click handlers for levels, vault, expedition, survey commit, wildfire and rival. |
| `canopy_loading.py` | 16 KB | load_state(): restores a save into the live game, then redraws. Ask for it to change how a save is restored. |
| `canopy_tick.py` | 6 KB | tick(): one second of game time, and the tick loop starter. |
| `canopy_setup.py` | 14 KB | setup(): wires every button and starts the game. Ask for it to wire a new button. |
| `game.py` | 3 KB | Entry point: `_PART_NAMES`, the re-export loop and `_GameModule`. `setup()` runs when `canopy_setup` is imported. |

**State rule.** A module variable that some function REPLACES (`total_income += ...`, `selected_index = 3`) lives only in `canopy_runstate.py`; every other module reads and writes it as `runstate.<name>` (each starts with `import canopy_runstate as runstate`). Never `from canopy_runstate import total_income` (a test checks). Lists, dicts and sets only changed in place stay in the module that owns them. A new rebound variable goes into `canopy_runstate.py` AND its `LIVE_NAMES`; `game.<name>` reads and writes of those names are forwarded. Tests that patch a name work: the new value is copied into every module that holds it. The page reads live numbers through functions (`community_field_value`), never `pyodide.globals.get("<state name>")`.

**Page.** `index.html` is markup only (`pc.html` is generated from it by `python3 scripts/generate-pc-pages.py`, never edit it). Scripts: `boot.js` (Pyodide boot, the module list, the plot tooltip/keyboard wiring), `tutorial-steps.js`, `save-profiles.js`, `todays-run.js`, `copy-wiring.js`, `shortcuts.js`, `feedback.js`, `settings.js`. Stylesheets, in this cascade order: `style-1-base.css` (text scale, tiles, stats, legend), `style-2-visuals.css` (visual and console pass), `style-3-features.css` (toasts, summary, regions, first feature batches), `style.css` (last: the `[hidden]` rule, phone layout, later features, light theme). Tests read the pieces through `tests/pagefiles.py` (`game_css()`, `page_text(page)`, `game_source()`); `tests/conftest.py` forgets the `canopy_*` modules between tests. `tests/test_b_oct9*.py` is one old test file cut in three.

## For the local AI: exact names (verified against the code, 2026-10-18)
Canopy has no `handle()` and no view dict: it is DOM-driven. The forest is `runstate.plots` (a list of `Plot`; `game.plots` in tests), `runstate.selected_index` is the chosen tile, and the buttons call `Plot` methods and then `render()`. The page code reaches Python only through `get_state`, `load_state` and a few functions looked up with `pyodide.globals.get(name)`.
- **`Plot` (`canopy_plot.py`):** attributes `index region state value ticks_intact clear_count replant_ticks_remaining biodiversity specialization species blocked`; `state` is one of `PRESERVED BARE REPLANTING RECOVERED` (`"preserved" "bare" "replanting" "recovered"`, `canopy_rules.py`). Methods: `clear()`, `clear_cut()`, `replant(partner=False, species=None)`, `blight()`, `accrue_tick()`, `maturity_fraction()`, `finish_recovery()`, `advance_recovery()`, `has_wildlife()`, `can_specialize()`, `is_veteran()`.
- **Player actions (module functions):** `select_plot(index)` (`canopy_renderer.py`), `on_clear()`, `on_clear_cut()`, `on_replant()`, `on_tend()`, `tend_plot(index=None)`, `undo_last_clear()`, `set_forest_name(value)`, `set_plot_nickname(value)`, `start_new_forest()`, `queue_survey_action(kind, plot=None)`, `commit_survey()`, `reset_session(grid_size=None, difficulty=None, challenge=None, pace=None, scenario=None, ...)` (`canopy_renderer.py`), highland and wetland versions `on_highland_clear|replant`, `on_wetland_clear|replant|mangrove`. Handlers for the panels (`on_difficulty_change`, `on_grid_size_change`, `on_sell_carbon_half`, `grant_stakeholder_request`, ...) are in `canopy_handlers_panels.py`; levels, vault, expedition and survey handlers in `canopy_handlers_modes.py`. Every listener is attached in `setup()` in `canopy_setup.py` (run when that module is imported).
- **Time.** `tick(event=None)` in `canopy_tick.py` is one second of game time (`runstate.forest_tick`, `_session_ticks`); it returns at once in Survey mode. The loop is started by `_start_tick_loop()`.
- **`get_state()` keys always written:** `plots selected_index total_income standing_value community_relations pending_stakeholder_request _ticks_since_last_request _stakeholder_request_count info_page_open total_replants total_recoveries plots_with_wildlife_ever stakeholder_grants_count stakeholder_declines_count community_relations_min_ever current_grid_size current_difficulty forest_log forest_tick adopted_plot_index highland_unlocked highland_selected_index highland_income highland_plots achievements_earned`, plus what `_wetland_state_fields()` and `_gb_state_fields()` add. Read `canopy_savestate.get_state()` before adding or reading one.
- **Redraw.** `render()` in `canopy_renderer.py` redraws everything (`render_grid()` rebuilds every `#plot-<index>` tile from scratch, then `render_panel()`, `render_stats()`, and each feature's `render_<x>()` / `update_<x>_display()`). Call it after any state change. Anything you add to a tile must be added inside `render_grid()` (or reapplied after it), because the tiles are rebuilt on every call.
- **Ids.** Grid: `plot-grid`, tiles `plot-0 plot-1 ...` (buttons with class `plot-<state>`), `highland-plot-grid`, `wetland-plot-grid`. Actions: `clear-button replant-button` (disabled "Loading..." until `setup()` runs), `income-display` ("Harvested income: N"), `stats`. Panels `<x>-panel` (hidden) opened by `<x>-toggle-button`: `howto achievements changelog example almanac contracts vault expedition session-summary settings info-page survey` (plus panels without a window: `legend stakeholder action adopted-plot coach-hints forest-rank`).
- **New panel.** (1) `index.html`: `<button id="x-toggle-button">` and `<div id="x-panel" hidden>`; (2) `x_open = False` in `canopy_runstate.py` AND `LIVE_NAMES`; (3) `on_toggle_x` and `update_x_display()` (sets `panel.hidden = not runstate.x_open`) in the module that owns the feature (see `on_toggle_changelog` / `update_changelog_display` in `canopy_infopanels.py`), with the updater called from `render()`; (4) the `addEventListener` line in `canopy_setup.py`; (5) `pc-config.json`: `["x-panel", "x-toggle-button", "Title"]` in `windows` and the button id in a `toolbar.menu` group (check: `shared/tests/test_pc_games.py`), then the human runs `scripts/generate-pc-pages.py`. A new Python module goes at its dependency position in BOTH `_PART_NAMES` (`game.py`) and `CANOPY_PY_MODULES` (`boot.js`); the AI does NOT edit `sw.js` / `offline-manifest.json` (report it).
- **Tests that pin things you may change:** `tests/test_module_list.py`, `tests/test_file_sizes.py` (14k tokens; index.html 15,000), `tests/test_changelog.py` (`changelog.json`), `tests/test_achievements.py` (`achievements.json`), `tests/test_save_system.py` (save round trip), `tests/test_payout_and_degradation.py`, `tests/test_recovery_timer.py`, `tests/test_value_accrual.py`, `tests/test_plot_states.py` (the core numbers), `tests/test_comparison_scoring.py`, `tests/test_proxy_cleanup.py`, `tests/test_wiring_oct8.py`, `tests/test_light_theme.py`, `tests/test_time_controls.py`, `shared/tests/test_pc_games.py` (every id `game.py` looks up must exist in both pages).
- **Browser tests.** `tests/browser_helpers.py` + `tests/test_example_browser.py`: copy `tests/test_example_browser.py` for a new browser test (`from browser_helpers import open_game`; the `base` fixture comes from `conftest.py`). After `open_game`, wait until `#clear-button` no longer reads "Loading...". A fresh plot holds no value until the first game tick (one second), so wait for `#standing-value-display` to change before expecting a payout. `tests/test_todays_run_browser.py` is an older example.
- **Do not:** invent a state key, Plot attribute or element id (grep `canopy_plot.py`, `canopy_savestate.py`, `index.html` first); read a Python variable from JS by name (add a function); rebind a module variable outside `canopy_runstate.py`; add a save key that is always written (non-default only, validated on load); change payout, degradation or recovery numbers without reading the four core-number tests above; edit `pc.html`, `sw.js`, `shared/` or another game.

## Long history
The long history, per-item build notes and audit logs are in `NOTES.md` (same folder). Read only the section you are told to: `grep -n "^## " NOTES.md` lists them.
