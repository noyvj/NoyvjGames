# Continuum — A Sustainable City Across the Ages

**Working title — kept as-is (no better name landed, see naming note at the bottom).** This is the single flagship Digital Artefact for BCM114 Round 2, built around SDG 11 (Sustainable Cities and Communities). Unlike Round 1's speculative-media framing (Theme 9), **this round's framing is fictional media with a real story running through it** — not a warning about a possible future, a narrative about a specific city and its people across time. Unlike the Round 1 climate quartet (many small games, teaching-forward), **this is one deep game, and it should read as a game first** — the SDG 11 elements should live in what makes a good city good to live in, not in explicit lessons. Read this whole file before starting any milestone.

**Explicitly standalone:** no narrative or systemic connection to SOL or any other hub game. Shares only the hub's general conventions (testing, tech stack, hosting), not lore or world-state. (A generational "descendants" narrative thread was considered and deferred — see Deferred Items.)

**Design philosophy this round (important shift from the climate quartet):** less overt teaching, more game. No end-of-session survey prompts, no separate "did this feel effective" questions bolted onto the UI. Real-world grounding lives behind a collapsed, optional info panel — never on the main screen. The sustainability/livability balance should be something the player discovers through play, the way a good city-builder makes you feel the cost of bad zoning without a tooltip explaining it.

## Concept

The player grows a single settlement from a small tribal community into a space-age civilization and then a region reaching off-world, across eight eras, developing infrastructure, technology, and culture along the way — all while a visible sustainability/livability score tracks whether that growth is actually good to live inside, not just big. A real story follows the city and (loosely) its people across the eras, told through the log and transition-beat systems below.

## Eras (confirmed)

1. **Tribal** — small settlement, subsistence, earliest social organization
2. **Agrarian** — settled agriculture, early surplus and trade
3. **Classical** — early urbanization, civic institutions, early infrastructure
4. **Medieval** — denser urban centers, guilds/specialization, early public works
5. **Industrial** — mechanization, rapid growth, the era where sustainability tension becomes most visible historically
6. **Current/Digital** — modern city systems, information infrastructure, present-day sustainability challenges
7. **Space Age** — future era, off-world or post-scarcity infrastructure questions
8. **Relay Age** (R2-K26, added 2026-09-27) — a regional expansion that grows into off-world: the settlement becomes a network of a core and outlying holdings joined by supply links

**Build order (dev milestones) runs Tribal → Space Age**, matching play order — simplest era first, foundational systems proven before later eras build on top of them.

## Standing constraints (a short summary of "Core systems" and "Tech notes"; the full text is in NOTES.md)

- The sustainability/livability score is THE teaching mechanism and must gate real things (growth ceiling, migration, unrest, decay), never sit beside the score as a decorative meter. A balanced city must provably beat an unsustainable one of the same era. Nothing scolds the player in words.
- Real-world grounding lives only behind the collapsed, optional info panel (`info_content.py`, sources in `continuum-real-world-sources.md`), never on the main screen. No survey prompts: feedback is diegetic, through the log and the transition beats.
- One continuous save spans the whole arc and old saves must load unchanged. `get_state()`/`load_state()` is the shared save widget's contract (see "For the local AI"); the revisit (Look Back) system must never lose forward progress.
- State and rendering stay separate: Python holds the game, `visual.py`'s `visual_state()` is the one seam to the Three.js layer (`render3d*.js`), which has a WebGL-unavailable 2D fallback. Colour is never the only signal; text scale and reduced motion are settings in `settings.js`.
- Nothing is idle-timed: the season clock runs only while the page is visible, each step is clamped, and the player can pause. No end-of-session surveys and no audio files.

## Milestones (condensed; the full table with each milestone's tests and the per-era notes is in `NOTES.md`, section "Milestones")

| # | Milestone | Status |
|---|-----------|--------|
| 1 | Core city simulation loop for the Tribal era only (population, basic resources, simple production) | Done |
| 2 | Sustainability/livability score system, integrated from the start as a growth-gating mechanic (not a side score) ... | Done |
| 3 | Research tree engine: build the generic, extensible tier/layer structure before populating many nodes | Done |
| 4 | Save system schema — design the continuous-save-with-revisit structure now | Done |
| 5 | Collapsed info-panel UI shell (empty/placeholder content is fine at this stage — the point is proving the UI ... | Done |
| 6 | Ongoing log system — lightweight, milestone-triggered flavor text, skippable, including diegetic feedback moments ... | Done |
| 7 | Era-transition beat system — generic framework reusable across all six transitions | Done |
| 8 | First full era transition: Tribal → Agrarian, exercising the full save/revisit and transition-beat systems end to ... | Done |
| 9 | Classical era content (Administrators, Canals, research tiers 5-6) | Done |
| 10 | Medieval era content (Guildmasters, Public Works, tiers 7-8) | Done |
| 11 | Industrial era content (Factory Workers, Sanitation Works, `pollution`, tiers 9-10) | Done |
| 12 | Digital era content (Urban Planners, Transit Hubs, `sprawl`, tiers 11-12) | Done |
| 13 | Space Age era content (Habitat Architects, Habitat Rings, tiers 13-14); Phase 3 complete | Done |
| 14 | Hub-nav integration (title card, review widget) | Done |
| 15 | Achievements system (19) + Look Back era-revisit UI (K7) | Done |
| 16 | K8 info-link audit, K15 accessibility-persistence verification | Done |
| 17 | K14 research tree search/filter | Done |
| 18 | K19 distinct building meshes, K6 camera presets | Done |
| 19 | Settings panel (text scale + reduce motion, `settings.js`) | Done |
| 20 | K9 mobile-dock (Advance Season button) | Done |
| 21 | Onboarding-tooltip coverage check | Done |
| 22 | K16 "What's New" changelog panel | Done |
| 23 | K5 summary, K12 scenarios, K13 snapshot, K17 seasonal light, K18 hard mode | Done |
| 24 | UI decluttering pass (research panel disclosures) | Done |
| 25 | Civic-backlog waves (K2/K3/K4/K6/K7/K8/K10/K11/K12/K13/K14/K15/K17/K19/K21/K23/K25/K27/K29) | Done |
| 26 | City Views (K1/K24/K28), settlement archive + shareable card (K18/K20), consulting mode (K22) | Done |
| 27 | Eighth era: the Relay Age (R2-K26) | Done |
| 28 | W2-continuum: sourced "In the real world" note for all eight eras | Done |
| 29 | O-5..O-8 replayability: Found a New Settlement, archive jumping-off buttons, founder's legacy, Refuge Start | Done |
| 30 | PC version phase 1: a Desktop boot (`pc.html`, generated from `index.html`) with a full-window frame, the Hamlet ... | In progress (first slice done, 2026-10-06; see `planning/PC-VERSION-PLAN.md`) |
| 31 | Round 3 K-section, first group: K-27 sparklines and K-16 "why did that change" waterfall on the City Views ... | Done |

Phases 1-6 are done: all eight eras (Tribal through the Relay Age) have sim content, a research tier, a sustainability mechanic, a transition and info-panel content; the save/security audit is done; the Three.js scenes cover every era. Milestones 19-24 were never git-tagged.

## File map (read this before editing; the game is split into small files, 2026-10-18)

The old 264 KB `game.py`, 73 KB `sim.py`, 54 KB `research.py`, 56 KB `render3d.js`, 86 KB `index.html` and 86 KB `style.css` were cut into files a small model can read whole. Nothing the AI may edit passes about 14,000 estimated tokens (bytes / 4); `tests/test_file_sizes.py` fails if a file does (the generated `pc.html`, `CLAUDE.md` and the `.json` data are exempt; `index.html` has a documented cap of 17,500: it is about 67 KB of real markup with no seam to cut). Behaviour did not change: every name the old `game.py`, `sim.py` and `research.py` had is still `game.<name>`, `sim.<name>`, `research.<name>`; saves are identical; the page looks identical. The other engine modules (`sustainability.py`, `save.py`, `views.py` ...) were already small and are unchanged.

**Python.** `game.py` is the entry point: it imports the `continuum_*` modules in dependency order (a module only imports from earlier ones) and re-exports every name (`game.get_state`, `game.render` ...). **The module list lives in two places that must match**: `_PART_NAMES` in `game.py` and `ENGINE_MODULES` at the top of `boot.js` (the page writes each file into Pyodide before running `game.py`; it also lists the engine modules and the sim/research parts). A new module also goes into `sw.js` and `offline-manifest.json`. `tests/test_module_list.py` checks both lists, the files on disk and the import order. Put a new feature in the module for its area, or a new `continuum_<feature>.py` placed in dependency order in both lists.

**Late-bound `render`.** Panels and click handlers call `render()`, which calls every `update_*` function, so the cycle is cut in one place: each module before `continuum_renderer.py` that calls `render()` holds a `render = None` line, and `continuum_renderer.py` fills them all in at the end of its file (`_RENDER_USERS`; a test checks it). Do not add other forward references: put new code after everything it calls.

| File | Size | What it holds, and when to ask for it |
|------|------|---------------------------------------|
| `continuum_runstate.py` | 8 KB | The live state: every module variable that gets REPLACED while playing (`campaign`, `state`, `tree`, `chronicle`, `sim_speed`, the panel-open flags and status strings ...) plus `LIVE_NAMES`. Ask for it to add a new rebound variable. |
| `continuum_base.py` | 14 KB | Small things many panels share: the season's effects and report text, the visual-state hook, the season calendar and clock constants, the Desktop-layout check, and the dynasty/rewind/citizen helpers that the archive and the save code also need. Ask for it to change the season report text, the effects, or a shared helper. |
| `continuum_founders.py` | 6 KB | The Founder's Log (notes, play time), the settlement name input, and the Minutes panel. |
| `continuum_achievements.py` | 15 KB | Achievements: the checks, progress readouts, the earned list, the panel and the unlock toast. |
| `continuum_clock.py` | 3 KB | The season clock: season length, speed buttons and the clock readout. The tick itself is in continuum_advance. |
| `continuum_archive.py` | 35 KB | The settlement archive, comparison table, export and shareable card, Found a New Settlement, the post-mortem and the Civilization Summary panel (they call each other, so they live together). |
| `continuum_dynasty.py` | 16 KB | Dynasty (banked legacy points, banners), era doctrines and the K-17 rewind token. |
| `continuum_beyond.py` | 6 KB | The Beyond (K-13, the endless mode after the Relay Age): the ladder kept in localStorage, banking a result after each season, and the panel. |
| `continuum_techdebt.py` | 4 KB | Technical debt (K-4): Quick builds, the refactor button and the panel. |
| `continuum_heritage.py` | 6 KB | Heritage sites: listing, demolish confirm and the panel. |
| `continuum_infopanels.py` | 8 KB | The What's New changelog panel, the real-world info page and its report button. |
| `continuum_savestate.py` | 5 KB | get_state() / load_state() for the shared save widget, and entering and leaving the practice sandbox. |
| `continuum_timelapse.py` | 6 KB | The time-lapse run replay (K-9): frames, scrubber, play and the panel. |
| `continuum_citizens.py` | 12 KB | Notable citizens (K-15/K-28) and the neighbour settlements panel (trade, share, bid). |
| `continuum_panels.py` | 14 KB | The log, sustainability and research panels, and the Work/Build/Study click-handler factories. |
| `continuum_challenge.py` | 14 KB | Daily challenge and scenario editor with share codes (K-10/K-11): ledger, controls, runs and the panel. |
| `continuum_geography.py` | 4 KB | The geography panel: seed, new map, off switch. |
| `continuum_progress.py` | 14 KB | The Work and Build panels, the era-progress panel, Advance Era, and the Look Back (revisit) panel. |
| `continuum_extras.py` | 2 KB | The standing-advantage rows of the City Views dashboard, and the hook that banks a collapsed settlement's Dynasty legacy. |
| `continuum_peers.py` | 4 KB | The peer-settlement comparison graph (R-33): publish plan, show, hide and metric. |
| `continuum_views.py` | 13 KB | The City Views panel (dashboard, map, flow) and the civic insights/challenges render. |
| `continuum_orders.py` | 12 KB | Standing orders: running them each season and the orders panel. |
| `continuum_scenario.py` | 8 KB | Starting scenarios (K12), hard mode (K18), consulting cases (K22) and their display updates. |
| `continuum_hamlet.py` | 28 KB | The optional Hamlet view (U2) and the Desktop HUD chips: capability checks, chips, town panel and render_hamlet. |
| `continuum_advance.py` | 7 KB | The tick loop and on_advance_season(): the one place a season actually happens. Ask for it to change what happens in a season. |
| `continuum_advisors.py` | 6 KB | The advisor council (K-8): advice rows, follow handlers and the panel. |
| `continuum_renderer.py` | 6 KB | render(): redraws the whole page from the settlement. It calls every update_* function, and the handler modules before it call it back through a late-bound `render` placeholder. Ask for it to change what a full redraw updates. |
| `continuum_setup.py` | 12 KB | setup(): wires every button, then starts the game. The two research-filter handlers sit here too. Ask for it to wire a new button. |
| `game.py` | 5 KB | Entry point: `_PART_NAMES`, the re-export loop, `_GameModule`, the `sys.path` set-up. |
| `sim.py` | | Facade over `continuum_sim_tables.py` (eras, roles, buildings, scenarios, 18 KB: add a role, building or scenario here), `continuum_sim_numbers.py` (production, pollution, sprawl, relay, land and growth constants, `NEUTRAL_EFFECTS`, 19 KB: tune a rate here) and `continuum_sim_city.py` (the `CityState` class, 33 KB: change how a season is simulated). The long design docstring stays in `sim.py`. |
| `research.py` | | Facade over `continuum_research_tree.py` (tiers, `ResearchNode`, `ResearchTree`, 11 KB) and the node data in `continuum_research_nodes_early.py` (Tribal to Classical), `_mid.py` (Medieval to Digital) and `_late.py` (Space, Relay, late-tier nodes), 12-14 KB each. It composes `NODE_LIST` from the three lists and holds `NODES`, `EFFECT_LABELS`, `describe_effects`, `unlock_estimate` and `build_tree`. |

**State rule.** A module variable that some function REPLACES (`campaign`, `state`, `sim_speed`, `views_tab`, `hamlet_on` ...) lives only in `continuum_runstate.py`; every other module reads and writes it as `runstate.<name>` (each starts with `import continuum_runstate as runstate`). Never `from continuum_runstate import state` (that copy goes stale when the practice sandbox swaps the settlement; a test checks). Lists, dicts and sets only changed in place (`research_branch_filter`, `_compare_picks` ...) stay in the module that owns them. A new rebound variable goes into `continuum_runstate.py` AND its `LIVE_NAMES`; `game.<name>` reads and writes of those names are forwarded to it, and the sandbox swaps them with `vars(runstate)`. JS that needs one of them asks a function (`current_sim_speed()`), never `pyodide.globals.get("sim_speed")` (a stale copy). Tests that patch a name (`monkeypatch.setattr(game_env.module, "_pc_layout", ...)`) work: the new value is copied into every module that holds that name.

**Page.** One line per file:

| File | What it holds |
|------|---------------|
| `index.html` | The page markup only (about 67 KB, the one file above the usual limit). Scripts are separate files loaded in the old order. `pc.html` is generated from it, never edit `pc.html`. |
| `boot.js` | Pyodide boot: `ENGINE_MODULES` (the module list), writes the shared helpers and every module into Pyodide, runs `game.py`, starts the tutorial, mobile HUD, dock, the season clock and the 3D layer. |
| `tutorial-steps.js` | The walkthrough text (`CONTINUUM_TUTORIAL_STEPS`). |
| `render3d-scenes.js` | Three.js building blocks, lighting and one scene builder per era (`ERA_BUILDERS`); exports `window.ContinuumScenes`. Ask for it to change how an era looks. |
| `render3d.js` | The renderer, camera and presets, drag controls, snapshot, screensaver, 2D/3D toggle and `ContinuumVisual` / `ContinuumScene`. Loaded after `render3d-scenes.js`. |
| `copy-result-wiring.js` | Mounts the Copy result buttons in the Summary and Challenge panels. |
| `community-compare.js` | The "compare with the community" button. |
| `shortcuts.js` | Keyboard shortcuts and the `?` cheat sheet. |
| `daily-leaderboard.js` | The daily-challenge leaderboard mount. |
| `answer-report.js` | `window.submitAnswerReport` (the info panel's report button). |
| `register-sw.js` | Registers the service worker. |
| `style-1-base.css` | Styles part 1: text scale, page shell, meters, research tree, log, panels and the first visual pass. |
| `style-2-console.css` | Styles part 2: the console look, the phone layout, the Hamlet view, the first K-section panels. |
| `style.css` | Last stylesheet: the site-wide `[hidden] { display: none !important; }` rule (a shared test looks for it here), the screensaver, key remapping, the later K-section panels and the light theme for them. |

The stylesheets must stay in the order `style-1-base.css`, `style-2-console.css`, `style.css` (the order is the cascade). After changing `index.html`, `pc-config.json`, `pc.js` or `pc.css`, regenerate `pc.html` with `python3 scripts/generate-pc-pages.py`. Tests read the pieces through `tests/pagefiles.py` (`game_css()`, `page_text(page)`, `game_source()`, `render3d_source()`, `engine_module_list()`); `tests/conftest.py` forgets the `continuum_*` game modules between tests (the sim and research parts stay cached with their facades).

## For the local AI (exact names, all grepped against the code on 2026-10-18)

Continuum has no `handle()` action list and no view dict: the engine modules (`sim.py`, `research.py`, `save.py` ...) hold plain Python objects, `continuum_*.py` redraw them into the DOM, and the page reads the DOM. Never invent a name; grep it first.
- **Entry points.** Every button is wired once in `setup()` in `continuum_setup.py` (`document.getElementById(id).addEventListener("click", create_proxy(handler))`); handlers are the `on_*` / `_make_*_handler` functions in the module for that panel (`continuum_panels.py` Work/Build/Study factories, `continuum_progress.py`, `continuum_advance.py`, `continuum_archive.py` ...). Work and build rows are created by `render_work()` / `render_buildings()` (`continuum_progress.py`) with ids `<role>-add-button`, `<role>-remove-button` and `<building>-build-button`; roles/buildings are in `ERA_ROLES` / `ERA_BUILDINGS` (`continuum_sim_tables.py`, e.g. `foragers gatherers crafters keepers`, `shelter granary hearth toolworks`). Time: `#speed-pause-button`, `#speed-1x-button`, `#speed-2x-button`, `#speed-4x-button`, `#advance-era-button`.
- **Engine verbs** (what tests call): `CityState.assign_worker(role)`, `unassign_worker(role)`, `build(building)`, `can_build(building)`, `advance_season(effects)` (`continuum_sim_city.py`); `ResearchTree.research(node_id, resources)`, `can_afford`, `is_available`, `effects()` (`continuum_research_tree.py`); `Campaign.advance_to_era(era)`, `enter_revisit(era)`, `exit_revisit()`, `to_dict()`, `load_dict(data)` (`save.py`); `on_advance_season()` and `tick_clock(dt)` in `continuum_advance.py` are the only places a season happens; `set_speed(speed)` takes 0, 1, 2 or 4. The live objects are `runstate.state`, `runstate.tree`, `runstate.campaign` (`continuum_runstate.py`), never copies.
- **Python the page may call** (`window.pyodide.globals.get(name)`): `get_state`, `load_state`, `share_result`, `challenge_share_result`, `tick_clock`, `set_speed`, `current_sim_speed`, `get_visual_state`, `on_hamlet_capability_change`, `peer_ghost_id`, `peer_message`, `peer_publish_plan`, `peer_query_json`, `peer_show`. To give JS a new value add a function; never read a Python variable by name from JS.
- **get_state()** (`continuum_savestate.py`) is `Campaign.to_dict()` (`save.py`): `save_version game era_order current_era furthest_era revisiting current_state parked_state era_snapshots ui log has_revisited`, plus the write-only `achievements_earned`. `load_state(data)` returns False for a save that is not ours; `restore_city` / `load_dict` clamp and validate every field (`_sanitize_numeric_field`), so a new city field is added with a default and a bounds check. Per-device settings and local records use localStorage keys (`continuum-*`), not the save.
- **Redraw.** `render()` (`continuum_renderer.py`) redraws the whole page and calls every `update_*` / `render_*` function; every handler ends with `render()`. Modules before the renderer hold `render = None` that the renderer fills in (`_RENDER_USERS`): do not add more of these. The 3D scene reads `get_visual_state()` (`visual.py`); JS that decorates the page must reapply after a redraw.
- **Main ids.** Displays `era-display season-display population-display food-display materials-display knowledge-display score-display livability-display idle-display season-clock-display`; panels `achievements-panel changelog-panel summary-panel views-panel info-page-panel settings-panel`, each opened by its `*-toggle-button`.
- **A new panel/button.** (1) markup in `index.html` (hidden by default with the `hidden` attribute, a visible button that opens it, a way to close it; `pc.html` is generated from it); (2) add every id a `continuum_*.py` module looks up to `ELEMENT_IDS` in `tests/conftest.py` (the fake DOM raises `KeyError` for an unknown id); (3) the listener in `setup()` and a `render_<name>()` / `update_<name>()` called from `render()`; (4) `pc-config.json`: a window is `[panel-id, button-id, "Title"]` in `windows` and the button id goes in `toolbar.menu`, otherwise in `zones` or a `composites` entry; (5) the human then runs `scripts/generate-pc-pages.py` (never edit `pc.html`); `tests/test_pc_boot.py` and `shared/tests/test_pc_games.py` check ids, config and that `pc.html` is current. A new Python module goes into `_PART_NAMES` (`game.py`) and `ENGINE_MODULES` (`boot.js`) in the same position, after everything it imports (`tests/test_module_list.py`); not `sw.js`.
- **Tests that pin things.** `test_module_list.py`, `test_file_sizes.py` (14,000-token cap; `index.html` 17,500), `test_save_system.py` + `test_full_playthrough.py` (every era transition with a real JSON save and reload) + `test_sandbox.py` (get_state byte-identical after the sandbox), `test_core_loop.py`, `test_research.py`, `test_visual_state.py`, `test_pc_boot.py`, `test_changelog.py` (`changelog.json`), `test_achievements.py` (`achievements.json`), `test_info_page.py`. Each era has its own `test_<era>_era.py`. The fake DOM is `tests/conftest.py` (`game_env` fixture: `.module`, `.state`, `.assign(role)`, `.build(building)`, `.advance_season(n)`).
- **Browser tests.** Copy `tests/test_example_browser.py` (`from browser_helpers import open_game`; `base` is a fixture from `conftest.py`): it boots the page, clicks `#speed-1x-button`, asserts `#season-clock-display` and `page.errors == []`. See also `test_peers_browser.py`.
- **Do not.** Invent a view key, id or action. Use `from continuum_runstate import state` (use `runstate.state`; a rebound variable also goes in `LIVE_NAMES`). Add a save field that is not validated on load or that changes what an old save means. Add timers that run while the page is hidden, audio files or survey prompts. Edit `pc.html`, `sw.js` or `offline-manifest.json`.

## Long history

The long history (per-item build notes, audit logs, site-wide-goal write-ups) was moved out of this file on 2026-10-18 into `NOTES.md` in this folder. Do not read it whole: grep its `## ` headings and read only the section you are told to.
