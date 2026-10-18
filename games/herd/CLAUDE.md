# Herd — Industrial Agriculture & Methane Game

**Built following the shared conventions in `planning/archive/climate-quartet-2-plan.md`** (moved there 2026-09-22 once all four second-set games shipped; was `climate-quartet-2-plan.md` at the games root while build order still mattered). This file is Herd-specific only. Built first of the second set — the simplest, closest in shape to Grid/Canopy from the original four.

## Concept

A farm/ranch management game. Growing your herd or output directly scales a methane-emissions meter that's mechanically distinct from the CO2-driven meters elsewhere in the hub (Grid, Tide). The player discovers through play — not through a tooltip — that "grow the farm" and "keep emissions low" pull against each other by default, and has to actively invest in decoupling them (feed changes, herd-size limits, methane capture infrastructure) rather than just growing less.

## Function tag: Causes

This game exists to make an invisible cause of climate change (methane from industrial agriculture) into something the player is directly and unavoidably producing. The emissions meter should rise as an automatic *consequence* of the player's core success metric (herd size / output), not as a separate thing they choose to ignore — that coupling is the entire lesson.

## Climate issue & hope angle

**Issue:** methane emissions from industrial-scale livestock agriculture.
**Hope angle:** decoupling is possible and profitable, not just a tax on growth. A player who invests in feed changes, herd-size discipline, or capture infrastructure should be able to reach a *larger, more profitable* farm with a lower emissions footprint than a player who just grows unchecked — proving decoupling isn't sacrifice, it's better management.

## Core loop

- Turn-based rounds. Player invests in herd growth, output infrastructure, or emissions-reduction measures each round.
- Methane meter rises automatically and proportionally to herd size/output — this coupling is default and visible from turn one.
- Reduction measures (feed additives, herd caps, capture systems) cost resources but reduce the coupling ratio (same herd size, lower emissions) rather than requiring the player to shrink the farm.
- No hard fail-state. High sustained methane triggers soft consequences (market/regulatory pressure, reduced yields from degraded land) that make an unchecked-growth strategy visibly worse over time, without ending the game.
- Scoring: long-run profitability weighted against sustained emissions level — rewards decoupling, not just growth or just restraint.

## Working conventions

- Commit + tag per milestone: `git commit -m "Milestone N: <name>"` then `git tag herd-milestone-0N`.
- Update the milestone table Status as work happens.

## Milestones

| # | Milestone | Content | Status |
|---|-----------|---------|--------|
| 1 | Core farm loop | Herd growth, output, resource allocation across rounds. Tests: growth calculation, resource allocation logic | Done |
| 2 | Coupled methane meter | Meter rises automatically tied to herd size/output. Tests: coupling-ratio calculation | Done |
| 3 | Decoupling measures | Feed/cap/capture investments that reduce the coupling ratio without requiring shrinkage. Tests: ratio-reduction formula per measure type | Done |
| 4 | Soft consequence system | Market/regulatory/yield pressure scaling with sustained high emissions, no hard fail-state. Tests: pressure-trigger thresholds | Done |
| 5 | Scoring + hope-angle payoff | Profitability-vs-emissions scoring that rewards decoupling as the best strategy, provably better than either pure-growth or pure-restraint. Tests: scoring formula across sample playthroughs | Done |
| 6 | In-game feedback prompt | Piped to Neon backend per root conventions | Done |
| 7 | Visual/UI pass + hub integration | | Done — all 7 milestones complete |
| 8 | Desktop boot (PC version): `pc.html` generated from `index.html`, full-window layout, Desktop tutorial, layout switch on the opening screen | Done (2026-10-07); see "Desktop boot" below |

## File map (read this before editing; the game is split into small files, 2026-10-17)

The old single `game.py` (300 KB) and the big `index.html` and `style.css` were cut into files a small model can read whole. Nothing the AI may edit passes about 14,000 estimated tokens (bytes divided by 4); `tests/test_file_sizes.py` fails if a file does (the generated `pc.html`, `.json` data and this notes file are exempt). Behaviour did not change: every name the old `game.py` had is still `game.<name>`, saves are byte-identical, the page looks identical.

**Python.** `game.py` is only the entry point: it imports the modules, re-exports every name (`game.get_state`, `game.render`, `game.FarmState` ... tests and the page use them), wires the buttons in `setup()` and runs the few start-up steps that used to run at import time. The modules below are listed in dependency order (a module only imports from the ones before it). **The module list lives in two places that must match**: `_PART_NAMES` in `game.py` and `HERD_PY_MODULES` at the top of `boot.js` (the page fetches each file and writes it into Pyodide's file system before it runs `game.py`); a new module also goes into `sw.js` and `offline-manifest.json`. `tests/test_module_list.py` checks the files on disk, both lists and the import order.

| File | Size | What it holds, and when to ask for it |
|------|------|---------------------------------------|
| `herd_rules.py` | 15 KB | Herd's numbers and tables: costs, ratios, thresholds, seasons, policy cards and the ranch-rule and audit specs. Pure data, no behaviour. Ask for this file to change a price, a rate or a threshold. |
| `herd_runstate.py` | 6 KB | The live state: every module variable that gets REPLACED while playing (`farm`, `generation`, `legacy_points`, `bulk_mode`, the panel-open flags ...), plus `LIVE_NAMES`. Ask for it to add a new rebound variable. |
| `herd_util.py` | 3 KB | Tiny shared helpers: the finite-number check, the safe int and the browser-storage read and write. |
| `herd_model.py` | 37 KB | The farm itself: FarmState (herd, methane, income, pressure, welfare, satellite farm, poultry, purchase log) plus the ranch-rule accessors it reads (rule(), pressure_scale(), season_for_round() ...). Ask for this file to change how the simulation works. |
| `herd_purchases.py` | 4 KB | The optional 'ask before a big purchase' check: the threshold setting, the confirm message and the guarded purchase helper. |
| `herd_blind.py` | 5 KB | Blind run (GF-28): the hard mode that hides the pure-growth baseline until you reveal it. |
| `herd_visuals.py` | 18 KB | Drawings and markers: the coupling gauge, the record-coupling-ratio marker, the methane trend graph, the real-world comparison chart, the season calendar, the poultry-versus-cattle card and the breeding rings. |
| `herd_messages.py` | 12 KB | The Real Story info page and the sentences that compare your farm with the pure-growth baseline, certification, the plant pivot and the consequence of growing. |
| `herd_achievements.py` | 21 KB | Achievements: the checks, the progress readouts, the panel, the unlock toast and the one-time milestone callouts. |
| `herd_pasture.py` | 8 KB | The pasture: cow moods, quips and speech bubbles, the pasture picture, named cows and the hall of fame. |
| `herd_changelog.py` | 4 KB | The in-game 'What's New' changelog panel. |
| `herd_sandbox.py` | 6 KB | Practice sandbox core (GF-24): the sandbox farm, the stash that sets the real game aside, the sliders. Entering and leaving the sandbox needs render() and get_state(), so those two functions live in herd_handlers_panels. |
| `herd_barns.py` | 7 KB | Barn skins (GF-17) and the golden cow (GF-21): what is unlocked, what is chosen and what the cards say. |
| `herd_loadouts.py` | 12 KB | Starting loadouts (GF-23) and the stewardship audits (GF-3), plus farm_is_pristine(). |
| `herd_rules_ui.py` | 6 KB | Ranch Rules (F-1): setting, resetting, remembering and describing the four custom rules. |
| `herd_ledger.py` | 16 KB | The Ranch Ledger (F-2) and the ghost of your best farm (Z-3e): filing a farm, the table, the chart and the ghost line. |
| `herd_succession.py` | 7 KB | Farm succession (F25): handing the farm over, legacy points and perks, and the round celebration. |
| `herd_extras.py` | 14 KB | Extra panels: vignettes, season, welfare, genetics and biogas lines, the policy cards, the satellite farm and the tagline. |
| `herd_collection.py` | 16 KB | Breeds and combos (GF-16, GF-5), rating titles, the highlights reel, lever efficiency, cap headroom and the lever history. |
| `herd_round.py` | 11 KB | Round play helpers: the bulk-buy stepper, the herd-size slider, the round-delta chips, undo, pace and save nudges. |
| `herd_explain.py` | 9 KB | The 'explain this number' inspector (F-6): income, methane, coupling and pressure breakdown trees. |
| `herd_planner.py` | 9 KB | The what-if planner (F-9): queue purchases, project the next rounds and draw the projection chart. |
| `herd_pins.py` | 4 KB | The pinned-stat strip (F-16). |
| `herd_mixer.py` | 3 KB | The feed-mixer timing minigame readouts (GF-25). |
| `herd_family.py` | 8 KB | The Family Farm branching story (GF-10). |
| `herd_profile.py` | 3 KB | Beginner / Standard / Expert play styles (F-11) and the next-best-lever hint. |
| `herd_savegame.py` | 20 KB | Saving: get_state(), the field-by-field loaders, the save checker and the recovery panel, steward_summary(). |
| `herd_settings_code.py` | 8 KB | Settings export and import code (F-25). |
| `herd_summary.py` | 5 KB | The end-of-run report card and the copy-result fields. |
| `herd_renderer.py` | 9 KB | render(): the one function that redraws the whole page from the farm. |
| `herd_loading.py` | 8 KB | load_state() and _apply_state(): putting a saved game back, then redrawing. |
| `herd_handlers_play.py` | 11 KB | Click handlers for playing: buying (herd, levers, poultry, genetics, supply chain, pivot), advancing and undoing a round, handing the farm over, the bulk stepper and the satellite and policy buttons. |
| `herd_handlers_panels.py` | 7 KB | Click handlers for the panels: ranch rules, ghost, ledger, mixer, family story, profile, recovery, settings import, barns, golden cow, blind run, loadouts and the sandbox (enter, leave, sliders, reset). |
| `game.py` | 14 KB | Entry point and wiring: `_PART_NAMES`, the re-export loop, `_GameModule`, the start-up steps, `current_farm()` and `setup()` (every `addEventListener`). Ask for it to wire a new button. |

**State-handling rule.** A module variable that some function REPLACES (`farm = ...`, `generation += 1`) lives only in `herd_runstate.py` and every other module reads and writes it as `runstate.<name>` (each starts with `import herd_runstate as runstate`). Never `from herd_runstate import farm`: that copies the name once and goes stale (a test checks this). Lists, dicts and sets that are only changed in place stay in the module that owns them. A new rebound variable goes into `herd_runstate.py` AND its `LIVE_NAMES` tuple; `game.<name>` reads and writes of those names are forwarded to it, and the practice sandbox swaps them with `vars(runstate)`. `farm`, `record_coupling_ratio`, `pinned_stats` and `barn_skin` start as `None` there because their first value needs code from later modules; `game.py` fills them in at start-up, in the order the old file did. `settings.js` reads the live farm through `current_farm()` (in `game.py`), because a plain `farm` global in `game.py` would go stale. Tests that patch a name (`game_env.module.some_function = fake`) work: `_GameModule.__setattr__` copies the new value into every module that holds that name.

**Page.** `index.html` is the markup (about 54 KB, the one file still above 12,000 tokens: it is one `#game` block of 48 KB of markup with no seam to cut; the generated `pc.html` is the same page plus the Desktop shell, so never edit it). Its scripts are separate files loaded in the same order as before: `tutorial-steps.js` (the walkthrough text), `boot.js` (Pyodide boot and the module list), `copy-and-credits.js`, `shortcuts.js`, `feedback.js`, `community-stat.js`, `community-compare.js` (the `herdCompare` hook), plus the older `app.js` (phone view), `settings.js` (Settings panel, tractor, mixer, glossary ...) and `pc.js`. The stylesheet is cut into ordered parts that must stay in this order (the order is the cascade): `style-1-base.css` (layout, gauge, investments, pasture picture), `style-2-panels.css` (HUD cards, achievements, report card, toasts, trend graph), `style-3-extras.css` (rounds 1-5: collector shelf, bulk stepper, deltas, undo, calendar, display preferences), `style-4-round6.css` (easy-read font, glossary, inspector, ranch rules, planner, ledger, pins, mixer, story, tactile), `style-5-round7.css` (lite mode, settings code, barns, golden cow, blind run, loadouts, audits, sandbox, phone view) and last `style.css` (only the site-wide `[hidden] { display: none !important; }` rule that `shared/tests/test_hidden_attribute_rule.py` looks for; `scripts/generate-pc-pages.py` also anchors on its link). Put new rules in the part for their area. After changing `index.html`, `pc-config.json`, `pc.js` or `pc.css`, regenerate `pc.html` with `python3 scripts/generate-pc-pages.py`.

**Tests read the pieces through `tests/pagefiles.py`:** `game_css()` (every linked stylesheet in order), `page_text(page)` (the page plus every local script it loads) and `game_source()` (`game.py` plus every `herd_*.py`), so a rule or function can move between files without breaking a test. `tests/conftest.py` puts the game folder on `sys.path` and forgets the `herd_*` modules between tests (each binds `document` and `setTimeout` from that test's fake `js`).

**index.html comments moved out (to keep the page small).** Long HTML comments that sat beside markup or script tags, in page order, with where each one was.

1. (before `#changelog-toggle-button`) K16 (planning/TODO.md "What's New" changelog, site-wide goal): a small in-game highlights panel, same hidden-until-opened idiom as achievements/report-card above.
2. (before `#sandbox-toggle-button`) Site-wide settings panel (planning/TODO.md, origin A9): consolidated text-scale + reduced-motion controls. See settings.js -- plain JS, independent of Pyodide, same as Continuum's Phase 5 accessibility.js/Aftermath's settings.js this pattern is modeled on.
3. (before `#coupling-gauge-record-display`) F8 (planning/TODO.md): a small per-browser "record decoupling ratio" marker, distinct from the session-only gauge-range-display above -- see game.py's record_coupling_ratio / render_record_coupling_ratio() for why the two need to be separate labels. Hidden until a record actually exists (a brand-new browser shows nothing).
4. (before `#real-world-comparison-chart`) Z17 (site-wide goal): a small chart alongside the sentence above, built on the shared shared/comparison_chart.py component -- see game.py's real_world_comparison_chart_svg().
5. (before `#baseline-herd-display`) UI decluttering pass (planning/TODO.md closing task): the raw herd/funds/methane/score breakdown below is collapsed by default -- it's the same information the on-demand Report Card panel (report_card_html() in game.py) already restates in full sentence form, so keeping it always-expanded here duplicated a feature that already exists as an on-demand summary. The one line players actually want every round without a click -- counterfactual-comparison-display above -- stays visible. Pure HTML move: every child id/game.py lookup is unchanged.
6. (before `#feedback-decoupling-strategy-button`) FY-4: a second question about Herd's own lesson (the Thaw two-question pattern): did decoupling growth from emissions feel like a real strategy, or a tax on growth? Both answers fold into the single `response` string, no backend change.
7. (before the shared save-widget script tags) SAVE-BUTTON-INTEGRATION.md: shared save widget, SOL is the reference integration. game.py exposes get_state()/load_state(); the widget itself is untouched per-game.
8. (before the sandbox-mode script tag) GF-24: the practice sandbox toggle and its banner (the rules live in game.py: sandbox_enter / sandbox_leave / sandbox_is_active).
9. (before the keyboard-shortcuts script tag) Z4 (site-wide goal): "?" shows a keyboard-shortcuts help overlay, Esc closes whichever panel is open. See shared/keyboard-shortcuts.js.

## For the local AI (exact names, all grepped against the code on 2026-10-18)

Herd has no `handle()` action list and no view dict: the Python redraws the DOM directly and the page reads it. Never invent a name; grep it first.
- **Entry points.** Every button is wired once in `setup()` in `game.py` (`document.getElementById(id).addEventListener("click", create_proxy(handler))`). Handlers: `herd_handlers_play.py` (`on_grow_herd`, `on_advance_round`, `on_undo_round`, `on_invest_plant_pivot`, `on_grow_poultry`, `on_invest_genetics`, `on_invest_supply_chain`, `on_hand_over_farm`, `_make_decoupling_handler(measure)`, `_make_bulk_handler`, `_make_satellite_handler`, `_make_policy_handler`) and `herd_handlers_panels.py` (rules, ledger, mixer, story, profile, barns, golden cow, blind run, loadouts, sandbox, recovery, settings import).
- **Engine verbs** (methods of `FarmState`, `herd_model.py`, what tests call): `grow_herd()`, `invest_decoupling(measure)` with measure `"feed"|"caps"|"capture"`, `invest_plant_pivot()`, `grow_poultry()`, `invest_poultry("litter"|"biofilter")`, `invest_genetics()`, `invest_supply_chain()`, `open_satellite()`, `grow_satellite()`, `retrofit_satellite()`, `choose_policy(choice)`, `buy_bulk(key, mode)`, `advance_round()`; readers `score()`, `coupling_ratio()`, `income_breakdown()`, `pressure_fraction()`, `welfare()`. The live farm is `runstate.farm` (`herd_runstate.py`), never a copy.
- **Python the page may call** (`window.pyodide.globals.get(name)`): only `get_state`, `load_state`, `current_farm`, `copy_result_fields`. To give JS a new value, add a function; never read a Python variable by name (a replaced one goes stale).
- **get_state()** (`herd_savegame.py`) always writes: `round_number funds herd_size methane decoupling_investment plant_pivot_investment counterfactual_funds counterfactual_methane methane_history max_pressure_fraction_seen seen_half_decoupled_callout seen_pressure_callout seen_methane_penalty_nudge certification_streak certified poultry_size poultry_investment genetics_active genetics_pending supply_chain_investment variation_enabled regional_cap_enabled policy_offer_pending subsidy_rounds_left summary achievements_earned`. Everything else (satellite_*, funds_history, lever_log, breeds_collected, hall_of_fame, audits_*, loadout*, blind_*, golden_*, barn*, policy_*, family_*, mixer_stats, ranch_rules, generation, legacy_*...) only when not default. `load_state` is in `herd_loading.py` (`check_save` first); every field uses `.get()` with a validated fallback.
- **Redraw.** `render()` (`herd_renderer.py`) rewrites the page from the farm, then calls one `render_<panel>()` per panel (`render_extras`, `render_planner`, `render_ledger`, `render_pins`, `render_mixer`, `render_barns`, `render_sandbox` ... listed at its end); every handler ends with `render()`. JS that decorates the page re-applies it from a `MutationObserver` (see `app.js`, `settings.js`), never once.
- **Main ids.** Displays `round-display funds-display herd-display methane-display coupling-display pressure-display score-display`; buttons `grow-herd-button advance-round-button feed-invest-button caps-invest-button capture-invest-button plant-pivot-invest-button undo-round-button bulk-1-button bulk-5-button bulk-max-button`; panels `achievements-panel report-card-panel changelog-panel info-page-panel planner-panel ledger-panel sandbox-panel explain-panel` (most open from a `*-toggle-button`). A fresh farm has 0 cows.
- **A new panel/button.** (1) markup in `index.html` inside `#game` (hidden by default with the `hidden` attribute, plus a visible button that opens it and Escape/the button to close); (2) add every id `game.py` looks up to `ELEMENT_IDS` in `tests/conftest.py` (the fake DOM raises `KeyError` for an unknown id); (3) `addEventListener` in `setup()`, and a `render_<name>()` called from `render()`; (4) `pc-config.json`: a window is `[panel-id, button-id, "Title"]` in `windows`, otherwise put the id in `zones.side` or a `composites` entry, and the button in `toolbar.menu`; (5) the human then runs `scripts/generate-pc-pages.py` (never edit `pc.html`); `shared/tests/test_pc_games.py` checks the config, ids and that `pc.html` is current. A new Python module also goes into `_PART_NAMES` (`game.py`) and `HERD_PY_MODULES` (`boot.js`) in the same position; not `sw.js`.
- **Tests that pin things.** `test_module_list.py` (module lists and import order), `test_file_sizes.py` (14,000-token cap per file), `test_save_widget.py` + `test_save_recovery.py` (get_state/load_state contract), `test_scoring.py` (decoupled growth must beat pure growth and pure restraint), `test_core_loop.py`, `test_changelog.py` (`changelog.json`), `test_achievements.py` (`achievements.json`), `test_info_page.py`, `test_wiring_oct8.py` (shared script tags on both pages), `test_sandbox.py` (get_state byte-identical after leaving the sandbox). The fake DOM is `tests/conftest.py` (`game_env` fixture: `.module`, `.farm`, `.grow_herd()`, `.advance_round()`).
- **Browser tests.** Copy `tests/test_example_browser.py` (`from browser_helpers import open_game`; `base` is a fixture from `conftest.py`): it boots the page, clicks `#grow-herd-button`, asserts `#herd-display` and `page.errors == []`.
- **Do not.** Invent a view key, id or action. Rebind a name from `herd_runstate` with `from herd_runstate import x` (use `runstate.x`). Add a `get_state()` key unless its value is not the default, and validate it in `load_state`. Put a per-device setting (all `herd-*` keys) into a save; it lives in `localStorage`. Change what `coupling_ratio()` means (the whole lesson rests on it), or edit `pc.html`, `sw.js`, `offline-manifest.json`. Add timers, countdowns or audio (nothing is timed, no sound files); keep every effect off under reduced motion/lite mode.

## Long history

The long history (per-item build notes, audit logs, site-wide-goal write-ups) was moved out of this file on 2026-10-18 into `NOTES.md` in this folder. Do not read it whole: grep its `## ` headings and read only the section you are told to.
