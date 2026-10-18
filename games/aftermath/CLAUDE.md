# Aftermath — Climate Adaptation & Resilience Game

**Built following the shared conventions in `planning/archive/climate-quartet-plan.md`** (testing, feedback hook, hope-angle requirement, hub integration — moved there 2026-09-22 once all four quartet games shipped; was `climate-quartet-plan.md` at the games root while build order still mattered). This file is Aftermath-specific only. Built last of the four — the meta-progression skill tree was the most complex system, tackled once the other three patterns were proven.

## Concept

Unlike the other three (all mitigation-focused), Aftermath treats climate change as a given, not a variable the player controls. Extreme weather events (floods, heatwaves, storms) hit on a schedule within each run. Between events, the player spends resources on resilience infrastructure vs. immediate growth. Runs are short and repeatable; a **skill tree/tech tree persists between runs**, representing accumulated societal adaptation knowledge — each run, the player starts a little more capable than the last, even though the climate events themselves don't get easier.

## Climate issue & hope angle

**Issue:** adaptation and disaster resilience as a distinct climate response — not mitigation, not a failure state, but its own necessary category.
**Hope angle:** the persistent skill tree *is* the hope mechanic — every run, even a rough one, contributes permanent capability for the next. The game should make clear that resilience is cumulative and never wasted, even when a single run goes badly. This is the most direct "long-term societal progress is real" message of the four.

## Core loop

- **Repeated short runs** (not full permadeath roguelite — that's more scope than needed). Each run: a settlement facing a scheduled sequence of extreme weather events, with resource-allocation decisions between events (build resilience infrastructure vs. pursue growth).
- Events are the same *type* of climate reality each run (floods, heatwaves, storms recur), but the settlement's baseline capability shifts run-to-run based on the skill tree.
- **Skill tree lives outside the run loop** — unlocked using a currency earned during runs (e.g. "resilience knowledge points"), persists across sessions, and pre-equips future runs with permanent bonuses (faster infrastructure builds, reduced event damage, better resource yields).
- A run "ends" when its scheduled event sequence completes — not a win/loss framing, more a "how well did the settlement weather this run" score that also feeds skill-tree currency.

## Tech notes

- Python/Pyodide, per root conventions.
- **Persistence decision (revised from the original plan):** the plan originally called for Neon-backend persistence, written under the assumption this might run in a sandboxed Claude Artifact where browser storage is unavailable. It doesn't — this is a normal static site with no accounts/auth system anywhere in the project (SOL/Canopy/Grid/Tide are all anonymous, shared-per-browser). Persisting to Neon would mean inventing an anonymous-device-identity scheme just to key rows to a browser with no other identity, plus new backend surface on the shared ratings service. Confirmed with the user: **use `localStorage`** instead — same per-browser persistence, no new backend surface. Trade-off: doesn't sync across devices, and clearing browser data resets it.
- Keep run-state and skill-tree-state as separate objects from the start — they're tested and persisted differently.

## Working conventions

- Commit + tag per milestone: `git commit -m "Milestone N: <name>"` then `git tag aftermath-milestone-0N`.
- Update the milestone table Status as work happens.

- 2026-09-21: E20 -- Growth button/readout now show the real current payoff ("+16 -> +24 resources/event") instead of a static number (`growth_button_label`). Mobile-dock `html body` padding fix (V-AB-2).

## Milestones

| # | Milestone | Content | Status |
|---|-----------|---------|--------|
| 1 | Single-run core loop | Scheduled event sequence, resource allocation between events, event damage resolution. Tests: event scheduling, allocation logic, damage resolution | Done |
| 2 | Run scoring + skill-tree currency generation | End-of-run score, currency earned based on performance. Tests: scoring formula, currency calculation | Done |
| 3 | Skill tree structure | Persistent tree of unlockable resilience bonuses, spend currency between runs. Tests: unlock logic, currency spend/balance tracking | Done |
| 4 | Bonus application to new runs | Unlocked skill-tree bonuses actually modify the next run's starting conditions/event resolution. Tests: bonus application across a sample run | Done |
| 5 | Hope-angle payoff | A clear "look how far you've come" comparison across runs (e.g. run 1 vs. run 5 outcome, same event sequence, visibly better handled) | Done |
| 6 | In-game feedback prompt | Piped to Neon backend per root conventions | Done |
| 7 | Visual/UI pass + hub integration | | Done — all 7 milestones complete |
| 8 | PC version: a Desktop boot (`pc.html`, generated from `index.html`) with a full-window dashboard layout, windows for the long sections, a Desktop tutorial and the layout switch on the opening screen | Done (2026-10-07; see `planning/PC-VERSION-PLAN.md`) |

## File map (read this first; every file is small enough to read whole)

`game.py` was one 8,300-line file (368 KB). It is now an entry point plus 20 `aftermath_*.py` modules, and the stylesheet and the page's inline scripts are split too (SP-1g in `planning/TODO.md`; the recipe is in `planning/SHARED-COMPONENTS.md`). Nothing changed in behaviour or in a save. Ask for the one file that holds what you are changing.

**Python (`aftermath_*.py`, listed in dependency order: a module imports only from the ones before it).** The list lives in ONE place that matters, `AFTERMATH_PY_MODULES` in `boot.js` (the page writes those files into Pyodide's file system before it runs `game.py`); `_PART_NAMES` in `game.py` repeats it in the same order, and `tests/test_file_sizes.py` checks both against the files on disk.

| File | Holds (ask for it when you change...) |
|------|------|
| `game.py` | Entry point. Imports the parts, re-exports every name (`game.<name>` still works for tests and the page), forwards live state, and `setup()` wires the buttons. Ask for it only to add a button listener. |
| `aftermath_runstate.py` | The variables that get REPLACED while playing (`run`, `skill_tree`, `meta`, `run_history`, panel-open flags, filters, status texts) and `LIVE_NAMES`. |
| `aftermath_rules.py` | Fixed numbers and tables: costs, `EVENT_SCHEDULE`, `SCENARIOS`, event labels/icons/damage/categories, severity helpers, `SKILLS`, storage keys. |
| `aftermath_persist.py` | localStorage helpers and save health, loaders/savers for every saved record (legacy, societal memory, curriculum, run history, `meta` and its sanitizers, Second Founding data), `skill_tree_strength`. |
| `aftermath_skilltree.py` | `SkillTreeState` (unlock, reset, move, pins) and the first load of the saved records into the live game. |
| `aftermath_bonuses.py` | What skills and the Second Founding add to a run, societal memory, mutual aid from neighbouring towns (R-31), settlement looks and the run-timer helpers. |
| `aftermath_achievements.py` | Achievements (catalog, checks, progress, panel, toast), event badges, end-of-run message helpers. |
| `aftermath_pastruns.py` | Legacy history and scar tiers, the mentor, Past Runs (notes, sort, filter, archive, compare), improvement streaks, expected-damage helpers, ETA, pinned skills. |
| `aftermath_panels.py` | Info page, What's New changelog, export/import progress code, skill-tree reset, skill unlock toast, callouts, epilogue text, real-world note. |
| `aftermath_codex.py` | Invest step size, the Disaster Codex and the Lifetime Stats panel. |
| `aftermath_runview.py` | Announcements, damage popup, run summary and copy text, tab title, skill help text, damage waterfall, epitaph, schedule strip, countdown note and run timer. |
| `aftermath_tools.py` | Skill search and filter chips, named allocation presets, save health badge, purchase route planner, plain-text schedule. |
| `aftermath_challenges.py` | The ghost of your best run, shareable run codes, challenge runs, today's run, the schedule builder. |
| `aftermath_skillmap.py` | Skill states and routes, the skill map (layout, model, SVG, render), skill ranks earned by use, `render_skill_move`. |
| `aftermath_chronicle.py` | The Second Founding panel and the Settlement Chronicle. |
| `aftermath_flourish.py` | Mood strip, settlement look, achievements tree strip, docked resources line, damage hit effects. |
| `aftermath_model_run.py` | `RunState` (one run: resources, events, damage, payout, score) and the creation of the first live `run`. |
| `aftermath_renderer.py` | `render()`: redraws the whole page, calling every panel's render function. |
| `aftermath_actions.py` | Actions that replace the running game and redraw: new run, challenge and daily starts, custom run, Second Founding, community resilience. |
| `aftermath_savestate.py` | `steward_summary()`, `get_state()`, `load_state()`: the save format. |
| `aftermath_handlers.py` | Every `on_*` click/change handler, plus `_make_*` handler factories. A new handler goes here. |

**State rule.** A module variable that some function REPLACES with `global x` / `x = ...` lives only in `aftermath_runstate.py`; every other module reads and writes it as `runstate.x` (each module that needs one starts with `import aftermath_runstate as runstate`). Never `from aftermath_runstate import x` (that copies the value once and goes stale). Lists, dicts and sets that are only changed in place (`societal_memory`, `run_log_history`, `_storage_state`) stay in the module that owns them. A new rebound variable goes in `aftermath_runstate.py` AND in its `LIVE_NAMES`. Tests use `game.run`, `game.run = ...` and so on: `game.py` forwards reads and writes of the names in `LIVE_NAMES` to `aftermath_runstate`, and a write to any other name is copied into every module that holds that name (so `monkeypatch.setattr(m, "_now", ...)` works). In the browser, `__main__` is the game module, so Pyodide code reads a live name as `__import__("__main__").run`, not as a bare `run`.

**Late-bound names.** `aftermath_tools`, `aftermath_challenges` and `aftermath_skillmap` call `render()` but come before `aftermath_renderer`: each holds `render = None` and the renderer fills it in at the end of its own file. `tests/test_file_sizes.py` checks that wiring. Do not add more of these; put a new function in a module after everything it calls.

**Page files.** `index.html` is markup only (about 57 KB, the one file allowed above 14,000 tokens, capped at 15,000 by `tests/test_file_sizes.py`). Scripts: `tutorial-steps.js` (the walkthrough steps), `boot.js` (loads Pyodide, writes the Python modules, runs `game.py`, starts the tutorial and mobile HUD), `seasonal-event.js` (N-2 Halloween badge), `copy-wiring.js` (Copy result and Credits links), `todays-run.js`, `run-code-boxes.js`, `community-resilience.js` (R-31 fetch), `shortcuts.js` (keys and panels for the `?` help), `feedback.js`, then the older `settings.js`, `ui.js`, `pc.js`. Styles load in this order (the order is the cascade; Desktop's `pc.css` goes after the first `style.css` link): `style-1-base.css`, `style-2-console.css`, `style-3-panels.css`, `style-4-tools.css`, `style.css` (the last part; starts with the blanket `[hidden]` rule that `shared/tests/test_hidden_attribute_rule.py` expects there). Put a new rule in the part for its area. `pc.html` is generated (`scripts/generate-pc-pages.py`), never edited by hand. `tests/pagefiles.py` has `game_css()`, `page_text()` and `game_source()` for tests that need the whole stylesheet, page or Python text.

## For the local AI (exact names, all grepped against the code on 2026-10-18)

Aftermath has no `handle()` action list and no view dict: the Python reads the live `runstate.run` and writes the DOM directly. Never invent a name; grep it first.
- **Entry points.** Every button is wired once in `setup()` in `game.py` (`document.getElementById(id).addEventListener("click", create_proxy(handler))`); handlers are the `on_*` / `_make_*_handler` functions in `aftermath_handlers.py`. Run-changing actions are in `aftermath_actions.py`: `start_new_run`, `start_challenge(code)`, `start_todays_run(seed_text)`, `leave_challenge`, `set_community_resilience(mean)`. The ids: `resilience-invest-button`, `growth-invest-button`, `resolve-event-button`, `new-run-button`, `undo-allocation-button`, `skill-<skill_id>-unlock-button` and `skill-<skill_id>-pin-button` (skill ids are the keys of `SKILLS` in `aftermath_rules.py`).
- **Engine verbs** (`RunState`, `aftermath_model_run.py`, what tests call): `invest_resilience()`, `invest_growth()`, `invest_steps(kind, step)` (kind `"resilience"|"growth"`, step 1, 5 or `"max"`), `invest_preset(resilience, growth)`, `undo_last_allocation()`, `resolve_next_event()`, `is_complete()`, `run_score()`, `knowledge_points_earned()`, `mitigation_for(event_type)`. Events are `flood heatwave storm supply_chain infrastructure_failure civil_unrest heat_mortality`; `SkillTreeState` (`aftermath_skilltree.py`) does unlock/reset/move.
- **Python the page may call** (`window.pyodide.globals.get(name)`): `get_state`, `load_state`, `copy_result_fields`, `set_community_resilience`, `start_todays_run`, `start_challenge`, `set_event_badges`, `run_code_fields`, `run_code_mode_names`. To give JS a new value add a function; never read a Python variable by name from JS (in the page `__main__` is the game module, a replaced variable goes stale).
- **get_state()** (`aftermath_savestate.py`) is ONLY the current run: `run_number event_index resources resilience_capacity growth_capacity damage_taken event_log extended summary achievements_earned skill_tree_strength`, plus `scenario challenge_code challenge_daily custom_events custom_name timer_seconds resources_log event_badges` only when not default. The skill tree, run history, legacy, settings and `meta` are NOT in it: they live in localStorage keys `aftermath_*_v1` (`aftermath_persist.py`, `aftermath_rules.py`). `load_state(data)` reads the required run keys with `data["..."]` ON PURPOSE (a malformed save must raise; `tests/test_save_system.py` pins it) and uses `.get` only for newer keys.
- **Redraw.** `render()` (`aftermath_renderer.py`) redraws the whole page from `runstate.run` and calls every panel's `render_*()`; every handler ends with `render()`. JS must reapply anything it adds to the page after a redraw (`aftermath_challenges.py` calls the page hook `window.aftermathRunCodeUpdate` during every render, see `run-code-boxes.js`; or use a `MutationObserver`).
- **Main ids.** Displays `progress-display next-event-display last-event-display resources-display resilience-display growth-display run-summary-display knowledge-points-display legacy-display mitigation-bar`; panels `achievements-panel past-runs-panel codex-panel stats-panel chronicle-panel changelog-panel info-page-panel run-summary-panel`, each opened by its `*-toggle-button` (skill-map ids are in `aftermath_skillmap.py`).
- **A new panel/button.** (1) markup in `index.html` (hidden by default with the `hidden` attribute, a visible button that opens it, and a way to close it); (2) add every id `game.py` or an `aftermath_*.py` module looks up to `ELEMENT_IDS` in `tests/conftest.py` (the fake DOM raises `KeyError` for an unknown id); (3) the listener in `setup()` and a handler in `aftermath_handlers.py`; a `render_<name>()` called from `render()`; (4) `pc-config.json`: a window is `[panel-id, button-id, "Title"]` in `windows` and the button id goes in `toolbar.menu`, otherwise add the id to `zones.side` or a `composites` entry; (5) the human then runs `scripts/generate-pc-pages.py` (never edit `pc.html`); `shared/tests/test_pc_games.py` checks the config, the ids and that `pc.html` is current. A new Python module goes into `AFTERMATH_PY_MODULES` (`boot.js`) and `_PART_NAMES` (`game.py`) in the same position, after everything it imports; not `sw.js`.
- **Tests that pin things.** `test_file_sizes.py` (token cap per file, module lists, late-bound `render`), `test_save_system.py` (save contract, malformed-save raise, double-award guard), `test_scoring.py`, `test_core_loop.py`, `test_skill_tree.py`, `test_skill_map_ranks.py` (`SKILL_RANK_RULES` thresholds must appear in the notes), `test_bonus_application.py`, `test_changelog.py` (`changelog.json`), `test_achievements.py` (`achievements.json`), `test_info_page.py`, `test_wiring_oct8.py`, `test_second_founding.py`, `test_round3_oct7.py` (Desktop windows). The fake DOM is `tests/conftest.py` (`game_env` fixture: `.module`, `.run`, `.invest_resilience()`, `.resolve_event()`, `.start_new_run()`).
- **Browser tests.** Copy `tests/test_example_browser.py` (`from browser_helpers import open_game`; `base` is a fixture from `conftest.py`): it boots the page, clicks `#resilience-invest-button`, asserts `#resilience-display` and `page.errors == []`. Others: `test_todays_run_browser.py`.
- **Do not.** Invent a view key, id or action. Use `from aftermath_runstate import x` (use `runstate.x`; a rebound variable also goes in `LIVE_NAMES`). Add a `get_state()` key unless its value is not the default; per-device settings go in `localStorage`, not the save. Add another late-bound `render = None`. Remove the `highest_awarded_run` guard in `resolve_next_event()` (reloading an old save must not pay out a run twice). Edit `pc.html`, `sw.js` or `offline-manifest.json`. Add timers, countdowns or audio files (the optional run timer is the only clock and is off by default); every effect must be off under reduced motion.

## Long history

The long history (per-item build notes, audit logs, site-wide-goal write-ups) was moved out of this file on 2026-10-18 into `NOTES.md` in this folder. Do not read it whole: grep its `## ` headings and read only the section you are told to.
