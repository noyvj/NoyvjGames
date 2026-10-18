# Trade Empire (working title) — Interstellar Trade Empire

*Slug: `trade-empire`. Title still open, same as SOL was before it shipped.*

## One-line pitch
Start with one ship and one trade route between two colonies; end up watching a self-operating economic machine move goods across a galaxy of interdependent worlds.

## Concept
A large-scale logistics and economic management game. The player founds a private interstellar trading corporation in an already-settled human space economy — no survival, no conquest, just growth, optimization, and the satisfaction of increasingly complex systems running well. Colonies are never self-sufficient by design: every world specializes (agriculture, mining, manufacturing, research, energy) and depends on imports for the rest. The player's job is spotting inefficiencies and solving logistics problems — first by hand, eventually by building automation systems that scale far past what any player could manage manually.

**Lore tie to SOL (flavor only, not mechanical):** this is the trade layer that emerges after SOL's worlds are terraformed and reach a sustainable state — the specific routes that appear once planets are stable enough to need exchange rather than just development. No shared code or systems between the two games; purely narrative connective tissue.

## Stack
- Python via Pyodide, same approach as SOL and the climate games. No build step.
- The 2D map (introduced mid-project, milestone 7) will need canvas draw calls — expect slightly thicker JS-glue boilerplate than SOL for that milestone specifically, still driven by Python logic underneath.

## Core constraints
- No idle/wait-timer mechanics — consistent with the house rule across all games on the site. (The Milestone 1 transit countdown is a short, active-session tick sequence like SOL's planet travel, not an idle-timer gate.)
- No external threats (piracy, combat, disasters) — tension comes purely from economics: unmet colony needs and market saturation, nothing else.
- Colonies are workforce/output pools with light flavor text, not simulated individuals — avoid drifting into city-builder territory.
- Manual control should stay genuinely viable and comfortable for several milestones before automation becomes necessary — automation is a payoff, not an early crutch.
- Visuals arrive in stages: text-only → simple node/line map → moving ships on the map. Don't jump ahead of that order. Milestone 1 is text-only by design.

## Core tension mechanics
1. **Evolving needs** — every colony has a need-set. Meeting needs increases how much surplus it can contribute to trade. Needs then evolve/expand as the colony develops further — there is no final "solved" state per colony, just an ongoing relationship between development and demand. (Not built yet — Milestone 1's two colonies have fixed, always-on needs; this arrives at Milestone 3/9.)
2. **Market saturation** — overproducing and dumping a single good crashes its price. Diversification and route-planning matter more than just maximizing one output. (Not built yet — Milestone 1 uses a flat per-good sell price; this arrives at Milestone 4.)

## Working conventions
- Commit + tag per milestone: `git commit -m "Milestone N: <name>"` then `git tag trade-empire-milestone-0N`.
- Update the Status column as work happens.

- 2026-09-21: J11 -- route readout shows avg profit per trip (new `good_trip_count`, saved; absent in old saves so the average is omitted). Mobile-dock `html body` padding fix (V-AB-2); achievements hub link now anchors to the dashboard (V-AB-5).

## Milestones
Same granularity as SOL's milestones — one clearly separable, demonstrable stage each. Not mapped to specific calendar weeks; build and tag whenever done, respecting the site's "something visible every 2 weeks" rule.

| # | Milestone | Content | Status |
|---|-----------|---------|--------|
| 1 | Core loop | Founding-contract intro, one ship, one manual route between two fixed colonies (Aurum Station ↔ Verdant Reach), profit ticks in on arrival | Done |
| 2 | Second route | Basic route-management UI, manual assignment across 2+ routes | Done |
| 3 | Colony need system v1 | Colonies have need-sets; output scales with needs met; minor flavor text per colony | Done |
| 4 | Market economics | Prices fluctuate with supply; overproducing a good crashes its price | Done |
| 5 | Manual scaling friction | More routes/colonies added — manual management gets genuinely busy, foreshadowing automation | Done |
| 6 | Automation v1 | First automation unlock — a route can run itself, limited slots/cost | Done |
| 7 | 2D map v1 | Colonies as nodes, routes as lines — first visual leap, still no moving ships | Done |
| 8 | Research tree v1 | Framework + early nodes; gates automation tiers and new ship types | Done |
| 9 | Evolving needs v2 | Needs meaningfully change/expand as colonies develop further | Done |
| 10 | Colony specialization | Worlds develop distinct strengths/weaknesses based on environment/history | Done |
| 11 | Ships on the map | Automated routes render as moving dots along the map's lines | Done |
| 12 | Fleet-level automation | Prioritization rules across many routes at once, not just per-route toggles | Done |
| 13 | Galaxy scaling | Research-gated expansion to more systems/regions | Done |
| 14 | Endgame | Fully automated economy visible at scale (hundreds of worlds, many ships); soft win-state, sandbox continues | Done — all 14 milestones complete |
| 15 | Desktop boot (PC version) | `pc.html` generated from `index.html`: full-window layout with the colony map as the stage and the fleet beside it, windows for colonies/market/research and the long sections, a Desktop tutorial, layout switch on the opening screen | Done (2026-10-07); see "Desktop boot" below |

## File map (read this before editing; the game is split into small files, 2026-10-18)

The old 402 KB `game.py`, the 118 KB `index.html` and `style.css` were cut into files a small model can read whole. Nothing the AI may edit passes about 14,000 estimated tokens (bytes / 4); `tests/test_file_sizes.py` fails if a file does (the generated `pc.html` and `.json` data are exempt; `index.html` has a documented cap of 27,500: it is about 110 KB of real markup with no seam to cut). Behaviour did not change: every name the old `game.py` had is still `game.<name>`, saves are identical, the page looks identical.

**Python.** `game.py` is the entry point: it imports the modules in dependency order (a module only imports from earlier ones) and re-exports every name (`game.get_state`, `game.render`, `game.ColonyState` ...). **The module list lives in two places that must match**: `_PART_NAMES` in `game.py` and `TRADE_PY_MODULES` at the top of `boot.js` (the page writes each file into Pyodide before running `game.py`). A new module also goes into `sw.js` and `offline-manifest.json`. `tests/test_module_list.py` checks both lists, the files on disk and the import order. A new feature block is a new `trade_<feature>.py` placed in dependency order in both lists (the old `@@NEW-FEATURES-END@@` marker in other notes below now sits in `trade_savestate.py`; ignore it for placement). A function that (even indirectly) calls `render()` lives in the modules after `trade_renderer.py`; everything before it only draws or computes.

| File | Size | What it holds, and when to ask for it |
|------|------|---------------------------------------|
| `trade_runstate.py` | 8 KB | The live state: every module variable that gets REPLACED while playing (profit, run seed, panel-open flags, guild state, chain and crisis state ...) plus `LIVE_NAMES`. Ask for it to add a new rebound variable. |
| `trade_rules.py` | 17 KB | Fixed numbers and content tables: goods, colonies and their flavour, needs, specialisations, temperaments, plus the plain constants other modules share. No browser calls, no state. Ask for it to change a price, rate, threshold or table. |
| `trade_records.py` | 2 KB | Personal-best records (kept in localStorage, never in the save) and the small helpers that read saved numbers safely. Ask for it to change what is remembered across charters. |
| `trade_charter.py` | 13 KB | The charter perk tree (O-1): perk and branch tables, the lifetime ledger, crest tiers, and the getters that turn a perk into a number (costs, decay, founding conditions). Ask for it to change a perk, its cost or the crest tiers. |
| `trade_uikit.py` | 2 KB | Small page helpers: HTML escaping, the reduced-motion and effects switches, and the notice toast. |
| `trade_colony.py` | 8 KB | ColonyState (one colony: need, development, temperament, demands), the colony table, which systems are open and who needs or makes a good. Ask for it to change how a colony's need, development or temperament works. |
| `trade_research.py` | 8 KB | The research tree (nodes, costs, unlock rules), automation costs and slots, Fleet Priority, and the fleet-wide boosts research gives. Ask for it to change a research node, an automation cost or Fleet Priority. |
| `trade_mapdraw.py` | 7 KB | The trade map's fixed parts: node positions, colours, route edges, ship positions, dock pulses and temperament glyphs (render_map itself is in trade_mapview). |
| `trade_effects.py` | 2 KB | The small multipliers that feed a sale price or output: market weather, the Meridian Cartel's contest, the Cartel squeeze, the legacy sale bonus. |
| `trade_market.py` | 12 KB | Prices and demand: market multipliers, trends, seasons, diplomacy, route hazards and insurance, the run seed and its random streams, selling, the stockpile, price recovery. Ask for it to change prices, demand, seasons, hazards, the stockpile or the run seed. |
| `trade_hub.py` | 6 KB | The Distribution Hub (J-21, J-22): choosing a hub colony, stockpile capacity, trip times, the fleet priority target and the hub panel. |
| `trade_blueprints.py` | 9 KB | The Blueprint Lab: hull designs, their stat points and effects, saving and deleting designs, and the panel and ship-option renders. |
| `trade_captains.py` | 4 KB | Captain perks (the four captains, their numbers and multipliers) and the captain table. |
| `trade_ships.py` | 17 KB | Ship archetypes, the Ship class, the ship table, sale log and profit totals, automation, trade posts, colony investment and concessions, buying and renaming ships. Ask for it to change how a ship loads, travels, sells, or what a purchase does. |
| `trade_crew.py` | 4 KB | Assigning and releasing captains, captain status text and the automated ships' run_automation(). |
| `trade_founding.py` | 4 KB | Founding a new corporation: legacy levels and starting credits, founding conditions from the seed, the immediate effect of a bought charter perk, the endgame test. |
| `trade_guild.py` | 5 KB | The Trade Guild contract (offer, accept, delivery, deadline) and its panel, plus the endgame background-galaxy numbers. |
| `trade_weather.py` | 7 KB | Market weather (booms, slumps, rumours, the ticker): the event stream, headlines, status text and panel. |
| `trade_blackout.py` | 6 KB | Blackout mode: the dark price feed and star chart, buying intel, status and panel. |
| `trade_crises.py` | 8 KB | Trade Crises (J-10): the three scripted scenarios, goals, medals, progress text and panel. |
| `trade_expedition.py` | 9 KB | The Fleet Lab: expeditions (odds, rolls, curios, outcomes) and the lab panel. |
| `trade_meridian.py` | 7 KB | The Meridian Cartel contest: contest cycle, undercut, intel, ledger line and panel. |
| `trade_exchange.py` | 6 KB | The Market Desk's exchange: standing buy and sell orders, fills, the order book and panel. |
| `trade_cartel.py` | 8 KB | Cartel moves (squeeze and dump) and their backlash, the Market Desk panel that shows exchange, Meridian and Cartel together. |
| `trade_ghost.py` | 8 KB | The ghost of the best charter (Z-3e5): recording, banking, comparison and the note under the ledger. |
| `trade_chain_rules.py` | 22 KB | Chain Builder rules and content: goods, recipes, chapters and the hand-made puzzle table. |
| `trade_chain_logic.py` | 28 KB | Chain Builder logic: paths, distances, evaluation, the solver, medals, the draft board, hints and the map drawing. |
| `trade_panels_fleet.py` | 14 KB | Page renders for ships, colonies, needs strips, sparklines and the almanac. |
| `trade_panels_systems.py` | 21 KB | Page renders for run seed, trade posts, route hazards, diplomacy, seasonal demand, market, research, fleet priority and the endgame (with its galaxy canvas). |
| `trade_mapview.py` | 5 KB | render_map(): draws the whole trade map on its canvas. |
| `trade_achievements.py` | 21 KB | Achievements (catalog, checks, progress, toast), the changelog panel and the ribbon flourish. Ask for it to add or change an achievement, the toast or the changelog panel. |
| `trade_summary.py` | 10 KB | The summary panel: trends, throughput, colony overview, route profitability, share result. |
| `trade_charter_ui.py` | 11 KB | The charter panel, the crest, the ribbon, the captains panel. |
| `trade_chain_ui.py` | 12 KB | Chain Builder page: signature, panel render, level select. |
| `trade_modes.py` | 6 KB | The Modes screen (GN-17): the ladder of game modes and its render. |
| `trade_savestate.py` | 11 KB | get_state(): everything that goes into a save. |
| `trade_loadparts.py` | 20 KB | The per-feature loaders that read a save back (guild, career, charter, blackout, expedition, Meridian, Cartel, hub, blueprints, exchange, weather, captains, records, ghost). |
| `trade_sandbox.py` | 4 KB | The practice sandbox's helpers (top-up, state swap, reset tables) that do not redraw the page. |
| `trade_renderer.py` | 4 KB | render(): redraws the whole page from the live game, calling every panel's own render function. |
| `trade_loading.py` | 16 KB | load_state(), _apply_state() and the practice sandbox's enter and leave, which reuse it: restores a save into the live game, then redraws. |
| `trade_handlers_core.py` | 11 KB | Click handlers for the core game (load, depart, invest, buy, rename, automate, research, fleet priority, renewal) and the confirm dialog. |
| `trade_handlers_features.py` | 7 KB | Click handlers for the feature panels (guild, charter perks, captains, blackout, weather, expedition, exchange, blueprints, hub, Meridian, Cartel). |
| `trade_handlers_modes.py` | 5 KB | Click handlers and starters for the modes: Trade Crises, the Chain Builder, the Modes screen. |
| `trade_tick.py` | 9 KB | tick(): one second of game time, the sale spark burst and the tick loop starter. |
| `trade_setup.py` | 14 KB | setup(): wires every button and starts the game. Ask for it to wire a new button. |
| `game.py` | 6 KB | Entry point: `_PART_NAMES`, the re-export loop, `_GameModule`, and the two start-up lines that used to end the old file (`_fresh_state = ...`, `setup()`). |

**State rule.** A module variable that some function REPLACES (`total_profit += ...`, `guild_state = ...`, `chain_active = ...`) lives only in `trade_runstate.py`; every other module reads and writes it as `runstate.<name>` (each starts with `import trade_runstate as runstate`). Never `from trade_runstate import total_profit` (that copy goes stale; a test checks). Lists, dicts and sets only changed in place (`ships`, `colony_states`, `records` ...) stay in the module that owns them. A new rebound variable goes into `trade_runstate.py` AND its `LIVE_NAMES`; `game.<name>` reads and writes of those names are forwarded to it. Tests that patch a name (`game_env.module.some_function = fake`) work: the new value is copied into every module that holds that name.

**Page.** One line per file:

| File | What it holds |
|------|---------------|
| `index.html` | The page markup only (about 110 KB, the one file above the usual limit). Scripts are separate files loaded in the old order. `pc.html` is generated from it, never edit `pc.html`. |
| `boot.js` | Pyodide boot: `TRADE_PY_MODULES` (the module list), writes the shared helpers and every module into Pyodide, runs `game.py`, starts the tutorial, mobile HUD and dock. |
| `tutorial-steps.js` | The walkthrough text (`TRADE_EMPIRE_TUTORIAL_STEPS`). |
| `summary-copy.js` | Mounts the copy-result button in the Summary panel. |
| `crisis-key.js` | The R key that restarts a Trade Crisis. |
| `shortcuts.js` | Keyboard-shortcut help panels list. |
| `style-1-base.css` | Styles part 1: text scale, page shell, map, ships, colonies, market, research, base panels. |
| `style-2-visuals.css` | Styles part 2: the visual pass (section cards, gauges, colony and ship art, good icons) and the console look. |
| `style.css` | Last stylesheet: toasts, summary, sparklines, the later feature panels, settings, light-theme polish and the site-wide `[hidden]` rule (a shared test looks for it here). |

The stylesheets must stay in the order `style-1-base.css`, `style-2-visuals.css`, `style.css` (the order is the cascade). After changing `index.html`, `pc-config.json`, `pc.js` or `pc.css`, regenerate `pc.html` with `python3 scripts/generate-pc-pages.py`. Tests read the pieces through `tests/pagefiles.py` (`game_css()`, `page_text(page)`, `game_source()`); `tests/conftest.py` forgets the `trade_*` modules between tests.

## For the local AI (exact names, all grepped against the code on 2026-10-18)

Trade Empire has no `handle()` action list and no view dict: Python objects (`ships`, `colony_states`, `runstate.*`) are redrawn into the DOM, and the page reads that. Never invent a name; grep it first.
- **Entry points.** Every button is wired once in `setup()` in `trade_setup.py`: `document.getElementById(id).addEventListener("click", create_proxy(handler))`, with handlers in `trade_handlers_core.py` (`_make_load_handler`, `_make_depart_handler(ship_id, colony_id)`, `_make_invest_handler`, `_make_concession_handler`, `_make_purchase_ship_handler`, `_make_rename_handler`, `_make_automate_handler`, `_make_research_handler`, `_fleet_priority_toggle_handler`, `on_found_new_corporation`, stockpile buy/sell), `trade_handlers_features.py` (guild, charter perks, captains, blackout, weather, expedition, exchange, blueprints, hub, Meridian, Cartel) and `trade_handlers_modes.py` (crises, Chain Builder, Modes screen). Each handler ends with `render()`. Automating and researching go through the shared confirm dialog (`_confirm_dialog_ask`).
- **Engine verbs** (what tests and handlers call): `ships[id].load()`, `ships[id].depart(colony_id)`, `automate_ship(ship_id)`, `purchase_ship(ship_id, archetype)`, `rename_ship(ship_id, name)`, `invest_in_colony(colony_id)`, `grant_concession(colony_id)`, `unlock_research(node_id)`, `buy_stockpile(good)`, `sell_stockpile(good)`, `found_new_corporation()`, `tick()` (`trade_tick.py`, one game second: sales, decay, research points; run by a timer that `shared/time-controls.js` can pause or speed up). Ships are ids `"1"`-`"6"` (`"5"` and `"6"` are bought); colonies are the keys of `ALL_COLONIES` in `trade_rules.py` (`aurum verdant ferrum cryo helion`, `kepler_*`, `rift_*`, `deep_*`); research nodes are the keys of `RESEARCH_NODES`.
- **Python the page may call** (`window.pyodide.globals.get(name)`): `get_state`, `load_state`, `share_result`. To give JS a new value add a function; never read a Python variable by name from JS (replaced variables live in `trade_runstate.py` and a copy goes stale).
- **get_state()** (`trade_savestate.py`) always writes: `ships` (per ship id: `location origin destination cargo_good cargo_qty transit_ticks_remaining transit_total_ticks automated purchased archetype name idle_ticks route_key route_legs total_earned units_moved ticks_owned units_by_good captain captain_deliveries`), `total_profit sale_log market_multiplier colony_states research_points unlocked_research fleet_priority_enabled endgame_reached ticks_since_endgame total_sales_count max_profit_ever goods_sold_ever ever_repositioned market_crash_ever good_profit_total good_trip_count good_profit_recent price_history need_history seasonal_demand cross_system_units trade_posts stockpile route_hazards achievements_earned`. Only when not default: `price_memory captains legacy ledger charter guild blackout weather records ghost expedition blueprints hub meridian cartel exchange run_seed`. The loaders are `load_state()` in `trade_loading.py` and `trade_loadparts.py` (one loader per feature, each validates).
- **Redraw.** `render()` (`trade_renderer.py`) redraws the whole page from the live game and calls each panel's `render_*()` (`render_map` in `trade_mapview.py`, `render_ship` in `trade_panels_fleet.py`, `render_guild`, `render_crises` ...). JS that decorates the page must reapply after each redraw (a `MutationObserver`), never once. The map is a canvas: do not add elements over it from JS.
- **Main ids.** `ship-<id>-status`, `ship-<id>-load-button`, `ship-<id>-depart-<colony_id>-button`, `ship-<id>-automate-button`, `colony-<colony_id>-invest-button`, `research-<node_id>-unlock-button`, `fleet-priority-button`; panels `achievements-panel changelog-panel summary-panel charter-panel captains-panel lab-panel desk-panel chain-panel settings-panel`, each opened by its `*-toggle-button`.
- **A new panel/button.** (1) markup in `index.html` (hidden by default with the `hidden` attribute, a visible button that opens it, a way to close it; `pc.html` is generated from it); (2) add every id a `trade_*.py` module looks up to `ELEMENT_IDS` in `tests/conftest.py` (the fake DOM raises `KeyError` for an unknown id) and keep it in the markup (`test_markup_matches_fake_dom.py` checks both pages); (3) the listener in `setup()` and the handler in a `trade_handlers_*.py` file, plus a `render_<name>()` called from `render()`; (4) `pc-config.json`: a window is `[panel-id, button-id, "Title"]` in `windows` and the button id goes in `toolbar.menu`, otherwise the id goes in `zones` or a `composites` entry; (5) the human then runs `scripts/generate-pc-pages.py` (never edit `pc.html`); `shared/tests/test_pc_games.py` checks the config. A new Python module goes into `_PART_NAMES` (`game.py`) and `TRADE_PY_MODULES` (`boot.js`) in the same position, after everything it imports; not `sw.js`.
- **Tests that pin things.** `test_module_list.py`, `test_file_sizes.py` (14,000-token cap; `index.html` 27,500), `test_markup_matches_fake_dom.py`, `test_save_system.py` + `test_sandbox.py` (get_state byte-identical after the sandbox), `test_core_loop.py`, `test_modes.py` (the Modes ladder, menu order, and that these notes contain "## Modes as levels"), `test_time_controls.py`, `test_achievements.py` (`achievements.json`), `test_changelog.py` (`changelog.json`), `test_seeded_runs.py`, `test_wiring_oct8.py`. The fake DOM is `tests/conftest.py` (`game_env` fixture: `.module`, `.load()`, `.depart(colony)`, `.tick(n)`, `.total_profit`).
- **Browser tests.** Copy `tests/test_example_browser.py` (`from browser_helpers import open_game`; `base` is a fixture from `conftest.py`): it boots the page, clicks `#ship-1-load-button`, asserts `#ship-1-status` and `page.errors == []`.
- **Do not.** Invent a view key, id or action. Use `from trade_runstate import x` (use `runstate.x`; a rebound variable also goes in `LIVE_NAMES`). Add a `get_state()` key unless its value is not the default, and validate it in its loader; per-device records and settings go in `localStorage`, not the save. Let a rolling-history list in the save grow without a cap (`sale_log` stops at `SALE_LOG_MAX_ENTRIES`). Add idle or wait-timer mechanics, external threats, or audio files. Edit `pc.html`, `sw.js` or `offline-manifest.json`.

## Long history

The long history (per-item build notes, audit logs, site-wide-goal write-ups) was moved out of this file on 2026-10-18 into `NOTES.md` in this folder. Do not read it whole: grep its `## ` headings and read only the section you are told to.
