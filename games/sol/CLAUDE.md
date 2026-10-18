# SOL — Solar System Incremental Clicker

Dual-purpose university digital artefact (DA) for BCM114 + BCM206 at UOW, Spring 2026 semester (starts July 27, 13 weeks). Built almost entirely via AI-assisted development.

## Game concept
Universal-Paperclips-style incremental game, solar-system themed. Player starts clicking to gather a resource on Earth, unlocks automation, then expands outward through the solar system.

**Core loop progression:** click → automation → multi-resource economy → ecology tension → research-gated expansion → trade → terraforming → endgame.

### Key systems
1. **Resources** — named per planet (e.g. Iron, Water on Earth), not abstract points. Numbers can go into scientific notation at scale.
2. **Ecology system** — one global sustainability meter.
   - Below 10% health: 25% output penalty.
   - At 0% health: production halts entirely until back to 10%.
   - Recoverable by shipping in materials from an already-stabilized planet (ties into trade system).
   - Certain buildings cost resources to build but improve ecological health / contribute to terraforming.
3. **Research system** — NOT strictly linear planet-by-planet. Research unlocks "distance tiers"; reaching a tier can open multiple bodies in parallel (e.g. Jupiter's moons together). Some buildings require resources only found on specific other planets (e.g. gas giant buildings need Mars materials) — this is what makes trade matter.
4. **Trade system** — resource exchange between active planets. First introduced as a 2-planet mechanic, later extended to more.
5. **Governor system** — when the player leaves a planet, it doesn't go idle-silent; the player sets priorities + a resource budget, and a "governor" manages it passively while away.
6. **Terraforming** — a per-planet progress bar filled by sustained economic/ecological balance (not a separate grind resource).
7. **Manual clicking** — relevance fades as automation kicks in per-planet, but re-becomes relevant again on each *new* planet (small structural loop, not literal one mechanic reused forever).
8. **Gas giants** — reuse the standard building system, reskinned; not a separate subsystem.
9. **Win condition** — 100% completion across the solar system triggers a soft "win" state; game remains playable sandbox-style afterward.
10. **Balance philosophy** — soft punishment for imbalance, always recoverable. No dead-end/unwinnable states.

## Stack
- **Python via Pyodide** (runs in-browser via WebAssembly) — not JavaScript. All game logic should be written in Python in `game.py`, using the `js` module / `pyodide.ffi.create_proxy` to interact with the DOM.
- Plain HTML/CSS shell (`index.html`, `style.css`). No frameworks.
- Must be served via a local HTTP server (`python -m http.server`) — `fetch()` of `game.py` fails on `file://` due to CORS.
- No build step, no bundler. Keep it simple — this is a solo AI-assisted project, not a production app.

## Core design constraints (do not violate without asking)
- **No idle/wait-timer mechanics.** No countdowns, no "wait 30 min for upgrade." Everything is either an active click or a continuous passive rate — never a timer gate.
- **Mobile-friendly**, responsive, playable in a browser.
- Visual style: **text/numbers first** (no icons yet), but structure code so icons/images could be layered in later without a rewrite.
- Button press gives visible feedback (darkens briefly on click, ~120ms).

## Standing rules a change must not break
- Nothing is timed or lost. No countdowns or wait gates (see "Core design constraints" above): `tick()` runs on a fixed 100 ms step and never reads the clock or the game speed; the away report counts ticks, not wall time. Manual mining must always work, even at 0% ecology (no dead ends).
- Saves must stay identical. `get_state()` and `load_state()` (in `sol_session.py`, over `serialize_state()` / `deserialize_state()` in `sol_savestate.py`) must load an old save that lacks any new key. A new key appears in the saved dict only when its value is not the default, and every loaded value is validated, falling back to the default. `deserialize_state()` MERGES into `planet_state` key by key (never `.clear()`, a past crash). `achievements_earned` is written by `get_state()` and never read back; `researched_nodes` is pruned by `_clean_researched_nodes()`.
- Per-device settings (theme, text scale, reduced motion, pause-when-hidden ...) live in localStorage, not in saves. No audio files. Every new effect respects reduced motion and has an off switch.
- Two lists must always match: `_PART_NAMES` in `game.py` and `SOL_PY_MODULES` in `boot.js` (and the files on disk): `tests/test_module_list.py`.
- A variable that a function REPLACES lives in `sol_runstate.py` (and its `LIVE_NAMES`), read everywhere as `runstate.x`; never `from sol_runstate import x`.
- No file the AI may edit may pass about 14,000 estimated tokens (`tests/test_file_sizes.py`); `index.html` is capped at 21,500. `pc.html` is generated (`python3 scripts/generate-pc-pages.py`), never edited by hand.

## Milestone plan (17 milestones, weeks 1–13; milestone 9 is a multi-part batch and will likely run over its single nominal week)

| Wk | Milestone | Content |
|----|-----------|---------|
| 1 | Core loop | Click Earth resource, dark-button feedback, basic mobile UI — **DONE** |
| 2 | First automation | Auto-generators, continuous passive rate, no timers — **DONE** |
| 3 | Ecology system | Global sustainability meter, penalty curve, ecology-improving buildings — **DONE** |
| 4 | Research system v1 | Tech-tree/distance framework, first unlock tier (Moon or Mars) — **DONE** |
| 5 | Planet transition + governor | Travel to new planet, governor priority/budget system — **DONE** |
| 6 | Second planet resource loop | New resource, reuse week 2/3 systems — **DONE** |
| 7 | Trade system v1 | Resource exchange between two planets, ties into ecology recovery — **DONE** |
| 8 | Terraforming | Per-planet progress bar — **DONE** |
| 9a | Research tier 2 framework | Second distance tier, parallel-unlocks Moon/Venus/Asteroid Belt/Pluto/Jupiter's moons/Saturn's moons; generalize governor + trade from a hardcoded 2-planet pair to N planets — **DONE** |
| 9b | Moon resource loop | New resource, reuse the standard building system — **DONE** |
| 9c | Venus resource loop | New resource, reuse the standard building system — **DONE** |
| 9d | Asteroid Belt resource loop | New resource, reuse the standard building system — **DONE** |
| 9e | Pluto resource loop | New resource, reuse the standard building system — **DONE** |
| 9f | Jupiter's moons resource loop | New resource, reuse the standard building system (one combined economy, not one per moon — matches the "parallel-unlock" framing) — **DONE** |
| 9g | Saturn's moons resource loop | New resource, reuse the standard building system (one combined economy, not one per moon) — **DONE** — Milestone 9 fully complete |
| 10 | Gas giant buildings | Reskinned building system + sky cities + Mars-material dependency — **DONE** |
| 11 | Full system endgame | 100% completion win-state, final balance pass — **DONE** |
| 12 | Desktop boot (PC version) | `pc.html` generated from `index.html`: full-window layout with the current world as the stage and its cards beside it, resource chips, windows for Research/Governor/Overview and the long panels, a Desktop tutorial, layout switch on the opening screen — **DONE** (2026-10-07); see "Desktop boot" below |

All 17 milestones complete (plus the Desktop boot, row 12 above).

**Important:** milestones can be built ahead of schedule, but should be *tagged* (`git tag milestone-0N` — sub-parts of 9 use `git tag milestone-09a` etc.) at actual completion time and *not publicized* (Instagram/devlog) until their assigned week. Don't backdate anything — the tag date must be real. This is a deliberate anti-burnout pacing strategy, not a submission deadline system.

## File map (read this before editing; the game is split into small files, 2026-10-18)

The old 375 KB `game.py`, the big `index.html` and `style.css` were cut into files a small model can read whole. Nothing the AI may edit passes about 14,000 estimated tokens (bytes / 4) except `index.html` (about 85 KB of real markup with no seam to cut; read it with grep by element id, cap 21,500 in `tests/test_file_sizes.py`); the generated `pc.html` and `.json` data are exempt. Behaviour did not change: every name the old `game.py` had is still `game.<name>`, saves are identical, the page looks identical.

**Python.** `game.py` is the entry point: it imports the modules, re-exports every name (`game.tick`, `game.get_state` ...) and wires the buttons in `setup()`. Modules are in dependency order (a module only imports from earlier ones). **The module list lives in two places that must match**: `_PART_NAMES` in `game.py` and `SOL_PY_MODULES` at the top of `boot.js` (the page writes each file, plus `challenges.py`, into Pyodide before running `game.py`). A new module also goes into `sw.js` and `offline-manifest.json`. `tests/test_module_list.py` checks both lists, the files on disk and the import order.

| File | Size | What it holds, and when to ask for it |
|------|------|---------------------------------------|
| `sol_runstate.py` | 12 KB | The live state: every module variable that gets REPLACED while playing (tick counters, lifetime stats, prestige, panel-open flags, the Scarcity Run, ghost recordings) plus `LIVE_NAMES`. Ask for it to add a new rebound variable. |
| `sol_rules.py` | 26 KB | Fixed numbers and tables: the planets, research nodes and tiers, the prestige tree, Governor personalities, specialisations, build-plan limits, rumours, storage keys. Data and tiny pure checks only. Ask for it to change a price, rate, threshold or table. |
| `sol_util.py` | 10 KB | Small shared helpers: the toast, localStorage reads and writes, time and number formatting, DOM element makers, floating sparks, view hiding. Ask for it when a helper is used by several panels. |
| `sol_story.py` | 10 KB | The achievements catalog (read from achievements.json) and the captain's story log lines. |
| `sol_runmods.py` | 12 KB | Run-wide rule modifiers: prestige mutators, Eras, timed anomalies and the megaproject yield factors. Ask for it to add a mutator, an era or an anomaly. |
| `sol_scarcity.py` | 5 KB | The Scarcity Run's fixed numbers, saved days, factors and the text helpers the Stats card shares. |
| `sol_econ.py` | 24 KB | Research effects and costs, production, terraforming, close-call tracking and the display updaters for each world (resource, generators, ecology, trade, sky cities, research, travel, Governor). Ask for it to change a cost, a formula or a world's readout. |
| `sol_rhythm.py` | 14 KB | Click-rhythm streak, speedrun split data, trophy shelf data, chain reactions and the Governor's mood. |
| `sol_observatory.py` | 22 KB | The Observatory: survey chart, rival colonies, rumours, rogue comets and the panel. |
| `sol_codex.py` | 10 KB | The hidden Codex and the three-goals list. |
| `sol_charter.py` | 12 KB | The Mission Board with Charter stamps, and Megaprojects (logic). |
| `sol_doctrines.py` | 7 KB | Governor Doctrines: rules, conditions, actions and the per-tick doctrine step. |
| `sol_sim.py` | 7 KB | One tick of one world: governor_step, incoming trade restore and _simulate_planet. Ask for it to change the core economy tick. |
| `sol_headless.py` | 17 KB | Runs on a copy (Doctrine dry run, Ecology Stress Test, Blueprint Swap) and the Doctrines panel. |
| `sol_achievements.py` | 13 KB | Achievement checks and progress tables, the summary and panel, trophy shelf and best-run text. Ask for it to add or change an achievement. |
| `sol_panels.py` | 6 KB | The What's New changelog panel and the Governor Report. |
| `sol_statsview.py` | 12 KB | The Stats and Share panel, the share card text, cross-planet summaries, stats codes and the run compare. |
| `sol_planner.py` | 10 KB | Build-order planner, prestige tree, epilogue and win display panels. |
| `sol_overview.py` | 9 KB | The multi-planet overview dashboard. |
| `sol_actions.py` | 14 KB | Player actions behind the click handlers: mining, buying, research, trade destination, travel, away reports and per-world resets. |
| `sol_capsules.py` | 14 KB | Time Capsules: frozen run snapshots to compare and branch from. |
| `sol_savestate.py` | 25 KB | serialize_state / deserialize_state, the session additions and the welcome-back snapshot and toast. Ask for it to add a saved field. |
| `sol_scarcity_run.py` | 8 KB | The Scarcity Run engine: swapping the real game out and a day's copy in, the Governor-alone headless run and the daily spec. |
| `sol_ghost.py` | 16 KB | The Ghost Run (personal-best and daily recordings, pace sentence) and the splits panel. |
| `sol_scarcity_panel.py` | 17 KB | The Scarcity Run's finish, tick hook and panel (calendar, ghost section, tally). |
| `sol_charter_panel.py` | 9 KB | The Mission Board and Megaproject panels. |
| `sol_run.py` | 10 KB | tick(), _full_render() and the per-tick achievement and story hooks. Ask for it to change what runs each tick or what a redraw covers. |
| `sol_session.py` | 3 KB | Loading a save (get_state, load_state, JSON forms) and starting or leaving a Scarcity Run: things that replace the running game and redraw. |
| `sol_handlers.py` | 29 KB | Every `on_*` click and change handler (buy, mine, travel, toggle panels, reset, prestige, scarcity ...). Ask for it to change what a button does. |
| `game.py` | 26 KB | Entry point: `_PART_NAMES`, the re-export loop, `_GameModule`, the tick loop and `setup()` (every addEventListener). Ask for it to wire a new button. |

`challenges.py` (the Scarcity Run's pure helpers) is unchanged.

**State rule.** A module variable that some function REPLACES (`total_ticks += 1`, `current_planet = ...`) lives only in `sol_runstate.py`; every other module reads and writes it as `runstate.<name>` (each starts with `import sol_runstate as runstate`). Never `from sol_runstate import total_ticks` (that copy goes stale; a test checks). Lists, dicts and sets only changed in place (`planet_state`, `researched_nodes`, `capsules` ...) stay in the module that owns them. A new rebound variable goes into `sol_runstate.py` AND its `LIVE_NAMES`; `game.<name>` reads and writes of those names are forwarded to it. The stats-code and compare helpers reach their counters with `vars(runstate)[name]`. Tests that patch a name (`game_env.module.some_function = fake`) work: the new value is copied into every module that holds that name.

**Page.** `index.html` is the markup; its scripts are separate files loaded in the old order: `tutorial-steps.js` (`SOL_TUTORIAL_STEPS`), `boot.js` (Pyodide boot and `SOL_PY_MODULES`), `copy-wiring.js` (Copy result button, Credits links), `goals-mount.js` (three-goals list), `shortcuts.js` (shortcut help panels); the service-worker line and the ad push stay inline. Stylesheets load in this order (the order is the cascade): `style-1-base.css` (shell, planet views, gauges, planet art), `style-2-panels.css` (console pass, achievements, research tree, reports, overview, build plan, prestige tree, epilogue, sparks), then `style.css` (last; starts with the site-wide `[hidden]` rule a shared test looks for, then round-3 additions, Scarcity Run and light-theme polish). After changing `index.html`, `pc-config.json`, `pc.js` or `pc.css`, regenerate `pc.html` with `python3 scripts/generate-pc-pages.py`; never edit `pc.html`. Tests read the split pieces through `tests/pagefiles.py` (`game_css()`, `page_text(page)`, `game_source()`); `tests/conftest.py` forgets the `sol_*` modules between tests.

## For the local AI: exact names (verified against the code, 2026-10-18)
SOL has no `handle()` and no view dict: it is DOM-driven. Python reads and writes elements with `from js import document`; the page code calls Python only through `get_state`, `load_state`, `copy_result_fields` and `goals_json` (looked up as `pyodide.globals.get(name)`). Everything you can name is `game.<name>` in tests.
- **Worlds.** Keys of `PLANETS` / `planet_state`: `Earth Mars Moon Venus AsteroidBelt Pluto JupiterMoons SaturnMoons` (exact spelling, no spaces). `planet_state[p]` keys: `resource_count generator_count recycler_count ecology_health trade_routes trade_destination terraform_progress governed_resource_generated governor_personality specialization player_actions`, plus `sky_city_count` on `JupiterMoons` and `SaturnMoons` only (`GAS_GIANT_BODIES`).
- **Player actions (`sol_actions.py`, all take the world name):** `_mine(planet, event=None)`, `_buy_generator(planet)`, `_buy_recycler(planet)`, `_buy_trade_route(planet)`, `_buy_sky_city(planet)` (gas giants), `_cycle_trade_destination(planet)`, `_travel_to(planet)`, `_return_to_earth()`, `_reset_world(planet)`, `research_node_action(node_id)`. The button handlers in `sol_handlers.py` are thin: `on_<world>_click`, `on_<world>_buy_generator|buy_recycler|buy_trade_route|cycle_trade_destination|buy_sky_city`, `on_travel_<world>`, `on_return_to_earth_from_<world>`, `on_reset_<world>` (world in `earth mars moon venus asteroid_belt pluto jupiter_moons saturn_moons`; travel and return exist for every world except earth), `on_priority_growth|balance|ecology`, `on_budget_increase|decrease`, `on_prestige`, `on_research_node_click`, and `on_toggle_<panel>` (`splits chains achievements changelog governor_report stats overview build_plan prestige_tree sandbox epilogue charter doctrine observatory capsules scarcity`). Save/load: `get_state()`, `load_state(data)`, `get_save_state_json()`, `load_save_state_json(s)`.
- **Saved dict (`get_state()`) top-level keys that are always there:** `planet_state research_progress completed_tiers researched_nodes unlocked_bodies visited_bodies current_planet governor_priority governor_budget_pct governor_tick_count governor_purchase_count prestige_level total_ticks total_manual_clicks lifetime_* any_generator_ever_built quick_start_hit swift_expansion_hit manual_labor_hit off_the_grid_hit prestige_points_earned prestige_nodes ng_challenge_active sandbox_mode build_plan close_call_hit back_from_brink_hit ecology_low_seen ecology_zero_seen achievements_earned`. Everything else (`story_log chain_counts run_splits pb_splits doctrine_rules mission_stamps mutators_next survey_data scarcity_days ...`) is added only when non-default (see `serialize_state()`).
- **Redraw.** `tick(*args)` (`sol_run.py`, every 100 ms) calls `update_resource_display(p)`, `update_generator_display(p)`, `update_ecology_display(p)`, `update_trade_display(p)`, `update_terraform_display(p)` per world and every panel's `update_<panel>_display()`. After anything that replaces the game (a load, a travel) call `_full_render()`. After your own change to a number call `update_resource_display(planet)` (and the panel's own updater); never touch the DOM from `tick` for a new panel without adding its updater to both `tick()` and `_full_render()`.
- **Ids.** Earth's ids are unprefixed, every other world prefixes its lowercase name (`_dom_id(planet, suffix)` in `sol_util.py`): `click-button resource-count generator-count generator-rate buy-generator-button buy-recycler-button buy-trade-route-button cycle-trade-destination-button` (Earth), `mars-click-button`, `asteroidbelt-click-button`, `jupitermoons-buy-sky-city-button` ... Travel: `travel-<moon|mars|venus|asteroid-belt|pluto|jupiter-moons|saturn-moons>-button`, back: `<world>-return-to-earth-button`. Governor: `priority-growth-button priority-balance-button priority-ecology-button governor-budget-value`. Toasts: `achievement-toast`. Panels are `<x>-panel` (hidden) opened by `<x>-toggle-button`.
- **New panel.** (1) `index.html`: `<button id="x-toggle-button">` in the toolbar and `<div id="x-panel" hidden>`; (2) `runstate.x_open = False` in `sol_runstate.py` AND in `LIVE_NAMES`; (3) `update_x_display()` (sets `panel.hidden = not runstate.x_open`) in the module that owns the feature, called from `tick()` and `_full_render()` in `sol_run.py`; (4) `on_toggle_x` in `sol_handlers.py` and its `addEventListener` line in `setup()` in `game.py`; (5) `pc-config.json`: add `["x-panel", "x-toggle-button", "Title"]` to `windows` and the button id to a `toolbar.menu` group (tests: `tests/test_round3.py`, `tests/test_scarcity.py`, `shared/tests/test_pc_games.py`); then the human runs `scripts/generate-pc-pages.py`. A new Python module goes at its dependency position in BOTH `_PART_NAMES` (`game.py`) and `SOL_PY_MODULES` (`boot.js`); the AI does NOT edit `sw.js` or `offline-manifest.json` (report it). A new page script needs a `<script src>` in `index.html` and a line in `pc-config.json` only if it is a window.
- **Tests that pin things you may change:** `tests/test_module_list.py` (module lists and import order), `tests/test_file_sizes.py` (14k-token cap, index.html 21,500), `tests/conftest.py` `INITIALLY_DISABLED_IDS` (the buttons that start disabled and `setup()` must enable: add a new world button there), `tests/test_achievements.py` (5 to 40 achievements, ids unique; `achievements.json`), `tests/test_changelog.py` (`changelog.json`, newest first), `tests/test_save_system.py` and `tests/test_core_loop.py` (save round trip), `tests/test_wiring_oct8.py` (share/credits wiring), `tests/test_light_theme.py`, `tests/test_time_controls.py` (only `_start_tick_loop` mentions `NoyvjTime`), `shared/tests/test_pc_games.py` (every id `game.py` looks up must exist in both pages).
- **Browser tests.** `tests/browser_helpers.py` + `tests/test_example_browser.py`: copy `tests/test_example_browser.py` for a new browser test (`from browser_helpers import open_game`; the `base` fixture comes from `conftest.py`). Wait for `#click-button:not([disabled])` after `open_game`.
- **Do not:** invent a state key or element id (grep `index.html` / `serialize_state()` first); read a Python variable from JS by name (add a function and call it through `pyodide.globals.get`); rebind a module variable outside `sol_runstate.py`; add a save key that is always written (non-default only, validated on load); edit `pc.html`, `sw.js`, `shared/` or another game; use `setTimeout` for game timing.

## Long history
The long history, per-item build notes and audit logs are in `NOTES.md` (same folder). Read only the section you are told to: `grep -n "^## " NOTES.md` lists them.
