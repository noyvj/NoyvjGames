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

## Standing rules a change must not break
- **Hope angle and no game over.** An early renewable investment must leave the player in a better position than a fossil-heavy run; rising emissions make disruptions more frequent and severe but never end the run. Turn-based: nothing is timed (rounds advance only when the player presses Advance Round or turns on auto-advance).
- **Costs.** Renewable cost falls with `cumulative_built`; `retire_plant()` refunds off `plant_cost()` (the current, discounted cost), never a flat base cost (a past build-then-retire money exploit, `tests/test_core_loop.py`). Weather Variability never touches `disruption_probability()`.
- **Saves.** `get_state()` is in `grid_savegame.py`, `load_state()` in `grid_loading.py`; old saves must load unchanged. `load_state()` reads every field with a default (`.get(...)`), validates it, and MERGES the per-plant dicts key by key (`_merge_plant_dict`: `plant_counts`, `cumulative_built`, `plant_age`), because every consumer indexes them for each of `PLANT_TYPES`. New keys are written only when non-default. `summary` and `achievements_earned` are write-only (never read back). The practice sandbox (`sandbox_enter()` / `sandbox_leave()` in `grid_handlers_play.py`) never edits the real game: `get_state()` returns the stashed real snapshot while it is on.
- Randomness only through the run's seeded streams (`state.stream(label, round_number)`, `shared/seed.py`), so a seed replays a run. Per-device display settings live in localStorage (`prefs`, `validate_prefs`), not in saves. No audio files; every new effect respects reduced motion and has an off switch.
- Two lists must always match: `_PART_NAMES` in `game.py` and `GRID_PY_MODULES` in `boot.js` (and the files on disk): `tests/test_module_list.py`. A variable that a function REPLACES lives in `grid_runstate.py` (and `LIVE_NAMES`), read as `runstate.x`.
- No file the AI may edit may pass about 14,000 estimated tokens (`tests/test_file_sizes.py`); `index.html` is capped at 15,500. `pc.html` is generated, never edited by hand.

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

## File map (read this before editing; the game is split into small files, 2026-10-17)

The old 347 KB `game.py`, the big `index.html` and `style.css` were cut into files a small model can read whole. Nothing the AI may edit passes about 14,000 estimated tokens (bytes / 4); `tests/test_file_sizes.py` fails if a file does (the generated `pc.html` and `.json` data are exempt; `index.html` has a documented cap of 15,500). Behaviour did not change: every name the old `game.py` had is still `game.<name>`, saves are identical, the page looks identical.

**Python.** `game.py` is the entry point: it imports the modules, re-exports every name (`game.get_state`, `game.render`, `game.GridState` ...), wires the buttons in `setup()` and runs the two start-up steps that used to run at import. Modules are in dependency order (a module only imports from earlier ones). **The module list lives in two places that must match**: `_PART_NAMES` in `game.py` and `GRID_PY_MODULES` at the top of `boot.js` (the page writes each file into Pyodide before running `game.py`). A new module also goes into `sw.js` and `offline-manifest.json`. `tests/test_module_list.py` checks both lists, the files on disk and the import order. `GridState` is cut into three classes in `grid_state_round.py`, `grid_state_extras.py` and `grid_state.py` (mixins; `grid_state.GridState` inherits the other two).

| File | Size | What it holds, and when to ask for it |
|------|------|---------------------------------------|
| `grid_rules.py` | 24 KB | Grid's numbers and tables: costs, capacities, emissions factors, wear tiers, scenarios, grants, the career tree, default settings. Data only. Ask for this file to change a price, a rate, a threshold or a table. |
| `grid_runstate.py` | 4 KB | The live state: every module variable that gets REPLACED while playing (`state`, `career`, `prefs`, the panel-open flags and message strings ...) plus `LIVE_NAMES`. Ask for it to add a new rebound variable. |
| `grid_state_round.py` | 20 KB | GridState, part 2 of 3 (a mixin): the round itself. advance_round and what it runs: arbitrage, the regional grid, the emergency, scheduled maintenance, revenue-capacity and weather maths. |
| `grid_state_extras.py` | 12 KB | GridState, part 3 of 3 (a mixin): surprise grants, the peek forecast, scoring and projection, demand response and policy levers. |
| `grid_state.py` | 28 KB | GridState, part 1 of 3: the grid being played (setup, costs, capacity, build, retire, maintain, wear). Mixes in GridStateRound and GridStateExtras so the whole class still reads as game.GridState. |
| `grid_sandbox_state.py` | 6 KB | The practice sandbox's grid (SandboxGridState) and its balance sliders (Z-18, C-27). Entering and leaving the sandbox needs render() and get_state(), so those functions live in grid_handlers_play. |
| `grid_whatif.py` | 6 KB | The career what-if strategies (replaying a run under canned strategies) and the Career panel's what-if rows. |
| `grid_career_data.py` | 12 KB | The Grid Operator career record (C1): defaults, validation of saved careers, ghost traces and browser storage. |
| `grid_career_actions.py` | 4 KB | Career actions: career points for a run, adding to lifetime totals, unlocking perks, choosing a loadout. |
| `grid_prefs.py` | 7 KB | Display preferences (C-12, C-19, GC-8, GC-9 ...) and the settings built on them: skipped confirmations, number format, units and funds deltas. |
| `grid_achievements.py` | 11 KB | Achievements: the checks, progress readouts, milestone text and the earned list. |
| `grid_shadow.py` | 5 KB | The shadow grid (C21): replaying your build and retire actions on a different starting scenario to compare. |
| `grid_savegame.py` | 22 KB | Saving: get_state(), the field-by-field loaders, the load report and steward_summary(). |
| `grid_trend.py` | 21 KB | The emissions and cost trend graph (SVG, table and description), the Info Page content and the comparison messages. |
| `grid_panels.py` | 5 KB | The What's New changelog panel, the weather log panel and the Info Page toggle. |
| `grid_views.py` | 9 KB | Small views: demand-growth arrow, wear tooltip, render_trend, plant-mix and gauge tables, chart theme. |
| `grid_messages.py` | 2 KB | Sentences for random events and disruptions (event_message, disruption_reason, severity classes). |
| `grid_announce.py` | 9 KB | Screen-reader announcements (B-7), the round recap text and the achievement unlock toast. |
| `grid_difficulty.py` | 3 KB | Difficulty presets (C-10): relaxed, standard, operator and custom, derived from the existing toggles. |
| `grid_summary.py` | 7 KB | The Run Summary panel, the copy-result fields and the summary toggle. |
| `grid_skyline.py` | 4 KB | The city skyline strip (GC-8): the SVG buildings, the smog haze and its caption. |
| `grid_achievement_cards.py` | 6 KB | Achievement cards in the skyline look (C-31): the building icons, the panel and the stats request. |
| `grid_runs.py` | 7 KB | Finishing and recording runs: starting a new run, finish_run, daily run, ghost traces and the run record. |
| `grid_sandbox.py` | 4 KB | Practice sandbox helpers: the stash of real-game values, the balance slider text and the page notification. |
| `grid_fleet.py` | 5 KB | The sortable fleet overview (C-14). |
| `grid_runsetup.py` | 6 KB | Run setup: starting loadout, run seed, Ironman, undo, grants, peek and the setup panel render. |
| `grid_coach.py` | 5 KB | The opt-in coach (C-21): picks one observation about your grid. |
| `grid_arbitrage.py` | 2 KB | The storage-arbitrage mode and the emergency messages, and their render. |
| `grid_schematic.py` | 7 KB | The single-line schematic (C-11): rows, flow widths, caption and SVG. |
| `grid_realgrid.py` | 6 KB | Real-grid comparison (C29) and the regional grid panel (C3). |
| `grid_slots.py` | 6 KB | Local run slots (C-13): saving, switching, starting and clearing slots in this browser. |
| `grid_gridley.py` | 10 KB | Gridley, the one-line commentator (GC-19), the supply-against-demand needle gauge (GC-28) and operator ranks (C-17). |
| `grid_callouts.py` | 9 KB | One-time callouts and per-plant helpers: the 50%-renewable callout, retire/maintain callouts, disruption toast, arrow-key commands for the plant rows and the mix hover text. |
| `grid_advance.py` | 6 KB | Advancing a round: the round animation (C-23), auto-advance, the round recap panel and their render. |
| `grid_careerpanel.py` | 12 KB | The Career panel: lines, perk progress, history charts, heatmap, import/export and the upgrade tree's view. |
| `grid_renderer.py` | 18 KB | render(): the one function that redraws the whole page from the grid, plus the Career panel update and tree view it calls back into (they call each other, so they stay together). |
| `grid_loading.py` | 5 KB | load_state(): putting a saved game back, then redrawing. |
| `grid_handlers_panels.py` | 14 KB | Click and change handlers for panels and settings: preferences, fleet sort, confirmations, rank theme, run slots, career finish, run setup, Today's run, import and export. |
| `grid_handlers_play.py` | 13 KB | Click handlers for playing: build, retire, maintain, plant keys, advance and auto-advance, arbitrage, scenarios, policies, shadow and real-grid pickers, difficulty, and the sandbox (enter, leave, sliders). |
| `game.py` | 14 KB | Entry point: `_PART_NAMES`, the re-export loop, `_GameModule`, the start-up steps and `setup()` (every `addEventListener`). Ask for it to wire a new button. |

**State rule.** A module variable that some function REPLACES (`state = ...`, `career = ...`, `prefs = ...`) lives only in `grid_runstate.py`; every other module reads and writes it as `runstate.<name>` (each starts with `import grid_runstate as runstate`). Never `from grid_runstate import state` (that copy goes stale; a test checks). Lists, dicts and sets only changed in place stay in the module that owns them. A new rebound variable goes into `grid_runstate.py` AND its `LIVE_NAMES`; `game.<name>` reads and writes of those names are forwarded to it, and the practice sandbox swaps them with `vars(runstate)`. `state` and `career` start as `None` there (their first value needs later modules); `game.py` fills them at start-up. Tests that patch a name (`game_env.module.some_function = fake`) work: the new value is copied into every module that holds that name.

**Page.** One line per file:

| File | What it holds |
|------|---------------|
| `index.html` | The page markup only (about 60 KB, the one file above the usual limit: one big block of markup with no seam). Scripts are separate files loaded in the old order. `pc.html` is generated from it, never edit `pc.html`. |
| `boot.js` | Pyodide boot: `GRID_PY_MODULES` (the module list), writes the shared helpers and every module into Pyodide, runs `game.py`, starts the tutorial, mobile HUD and dock. |
| `tutorial-steps.js` | The walkthrough text (`GRID_TUTORIAL_STEPS`). |
| `community-compare.js` | The `gridCompare` hook the Run Summary panel calls. |
| `todays-run.js` | The Today's run button wiring. |
| `copy-and-credits.js` | Copy-result button in the summary panel and the Credits links. |
| `summary-print-and-schematic-save.js` | The Print button in the summary panel and the Save schematic image button. |
| `shortcuts.js` | Keyboard-shortcut help panels list. |
| `feedback.js` | The feedback prompt. |
| `style-1-base.css` | Styles part 1: layout, status panel, trend graph, plant rows, callouts, info toggles. |
| `style-2-panels.css` | Styles part 2: achievements, run summary, changelog, toasts, hero picture, section cards, plant mix, gauges. |
| `style-3-plants.css` | Styles part 3: plant icons, action buttons, nameplates, the console look. |
| `style-4-rounds.css` | Styles part 4: reduced motion, arbitrage, career panel, shadow grid, difficulty row, round recap, run setup, grants, plant nicknames, screen-reader helpers. |
| `style-5-extras.css` | Styles part 5: fleet, coach, skyline, Gridley, needle gauge, ranks, chart themes, achievement cards, round animation, sandbox. |
| `style.css` | Last stylesheet: only the site-wide `[hidden] { display: none !important; }` rule (a shared test looks for it here). |

The stylesheets must stay in the order `style-1-base.css` ... `style-5-extras.css`, then `style.css` (the order is the cascade). After changing `index.html`, `pc-config.json`, `pc.js` or `pc.css`, regenerate `pc.html` with `python3 scripts/generate-pc-pages.py`. Tests read the pieces through `tests/pagefiles.py` (`game_css()`, `page_text(page)`); `tests/conftest.py` forgets the `grid_*` modules between tests.

## For the local AI: exact names (verified against the code, 2026-10-18)
Grid has no `handle()` and no view dict: it is DOM-driven. `runstate.state` is the `GridState` being played (`game.state` in tests); the buttons call it and then `render()` redraws the whole page. The page code reaches Python only through `get_state`, `load_state` and a few `pyodide.globals.get(name)` functions.
- **Plant types:** `PLANT_TYPES = coal gas nuclear solar wind hydro battery` (`RENEWABLE_TYPES` solar wind hydro; `FOSSIL_TYPES` coal gas), all in `grid_rules.py`. `GridState` per-plant dicts (`plant_counts`, `cumulative_built`, `plant_age`, `maintenance_schedule`, `plant_names`, `name_serial`) are keyed by exactly these names.
- **Engine methods (argument names exact), `GridState`:** `build_plant(plant_type)`, `retire_plant(plant_type)`, `maintain_plant(plant_type)`, `advance_round(rng=None, age_rng=None, weather_rng=None)`, `undo_last_build()`, `set_maintenance_schedule(plant_type, interval)`, `set_arbitrage_mode(mode)`, `connect_regional_grid()`, `apply_scenario(scenario_id)`, `set_start_option(option)`, `set_ironman(flag)`, `set_seed(text)`, `accept_grant()`, `decline_grant()`, `buy_peek()`, `invest_demand_response()`, `enact_policy(policy_type)`, `decline_policy()`. Read-only: `plant_cost(t)`, `total_capacity()`, `fossil_share()`, `emissions_this_round()`, `disruption_probability()`, `score()`, `resilience_score()`, `benchmark_grade()`, `wear_percent(t)`, `peek_forecast()`. Module functions: `finish_run()` (`grid_runs.py`), `sandbox_enter()` / `sandbox_leave()` (`grid_handlers_play.py`), `set_pref(key, value)` (`grid_prefs.py`).
- **Click handlers** are in `grid_handlers_play.py` (`_make_build_handler(plant_type)`, `_make_retire_handler`, `_make_maintain_handler`, `on_advance_round`, `on_auto_advance`, `on_toggle_steeper_demand`, `on_cycle_scenario`, `on_enact_carbon_pricing` ...) and `grid_handlers_panels.py` (`on_toggle_career`, `on_toggle_ironman`, run slots, import/export); each one changes `runstate.state`, then calls `render()`. Every listener is attached in `setup()` in `game.py` by element id.
- **`get_state()` keys always written:** `round_number demand funds plant_counts cumulative_built emissions event_log last_event clean_fraction_log emissions_history avg_renewable_cost_history renewable_unlocked plant_age maintenance_schedule scenario career seed start_option ironman plant_names name_serial grant_offer grant_effects summary achievements_earned` and about 40 more bookkeeping keys; `shadow`, `real_grid` and `regional_grid` only when in use. Read `grid_savegame.get_state()` before adding or reading one.
- **Redraw.** `render()` in `grid_renderer.py` redraws everything (it calls each panel's `update_<x>_display()` / `render_<x>()`); call it after any state change. Hook your own per-redraw code inside `render()` or one of the functions it calls, because the board is rebuilt on every call.
- **Ids.** Per plant (`<t>` in `PLANT_TYPES`): `<t>-row <t>-mix-row <t>-build-button <t>-retire-button <t>-maintain-button <t>-maintenance-schedule-select`. Round: `advance-round-button auto-advance-button round-display demand-display funds-display capacity-display emissions-display fossil-share-display event-display score-display trend-display streak-display undo-build-button`. Toasts: `achievement-toast disruption-toast`. Panels `<x>-panel` (hidden) are opened by `<x>-toggle-button`: `howto achievements changelog summary weather-log career settings info-page` (`slots-panel schematic-panel coach-panel` have no window).
- **New panel.** (1) `index.html`: `<button id="x-toggle-button">` and `<div id="x-panel" hidden>`; (2) `x_open = False` in `grid_runstate.py` AND `LIVE_NAMES`; (3) `on_toggle_x` and `update_x_display()` (sets `panel.hidden = not runstate.x_open`) in the module that owns the feature, with `update_x_display()` called from `render()`; (4) the `addEventListener` line in `setup()` in `game.py`; (5) `pc-config.json`: `["x-panel", "x-toggle-button", "Title"]` in `windows` and the button id in a `toolbar.menu` group (check: `shared/tests/test_pc_games.py`), then the human runs `scripts/generate-pc-pages.py`. A new Python module goes at its dependency position in BOTH `_PART_NAMES` (`game.py`) and `GRID_PY_MODULES` (`boot.js`); the AI does NOT edit `sw.js` / `offline-manifest.json` (report it).
- **Tests that pin things you may change:** `tests/test_module_list.py`, `tests/test_file_sizes.py` (14k tokens; index.html 15,500), `tests/test_changelog.py` (`changelog.json`), `tests/test_achievements.py` (`achievements.json`), `tests/test_core_loop.py` and `tests/test_emissions_and_cost_curve.py` (costs, refunds, emissions), `tests/test_disruption_events.py`, `tests/test_scoring.py` (hope-angle score), `tests/test_save_widget.py` (save round trip), `tests/test_wiring_oct8.py`, `tests/test_info_page.py`, `shared/tests/test_pc_games.py` (every id `game.py` looks up must exist in both pages).
- **Browser tests.** `tests/browser_helpers.py` + `tests/test_example_browser.py`: copy `tests/test_example_browser.py` for a new browser test (`from browser_helpers import open_game`; the `base` fixture comes from `conftest.py`). After `open_game`, wait until `#coal-build-button` no longer reads "Loading..." (`setup()` has run). `tests/test_todays_run_browser.py` is an older, longer example.
- **Do not:** invent a state key, method or element id (grep `grid_state*.py`, `grid_savegame.py`, `index.html` first); read a Python variable from JS by name (add a function and call it through `pyodide.globals.get`); rebind a module variable outside `grid_runstate.py`; add a save key that is always written (non-default only, validated on load); change the cost, refund or disruption formulas without reading `tests/test_core_loop.py`; edit `pc.html`, `sw.js`, `shared/` or another game.

## Long history
The long history, per-item build notes and audit logs are in `NOTES.md` (same folder). Read only the section you are told to: `grep -n "^## " NOTES.md` lists them.
