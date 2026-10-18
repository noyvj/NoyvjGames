# Heist Committee (working title)

Plan: `planning/heist-committee-plan.md`. TODO items M-1b-1 to M-1b-9. Personal project, no BCM tag. Fun first, funny, no lesson. Cozy caper tone (plan question He1 recommendation), invented crew names, Daily Job later (He2 recommendation).

## One-line pitch
Pick a target, hire five oddball specialists who do not get along, drag their actions into a timeline, then watch the job play out beat by beat while complications and personality clashes chain into each other.

## Stack
Python via Pyodide, plain HTML/CSS, no build step. `engine.py` is the heist resolver (pure function of content, crew, plan, gear and seed). Content is data in `content/*.json`, loaded by `content.py` (which also validates it). `app.js` is glue only.

## Core constraints
1. The heist is a pure function of (content, target, crew, plan, gear, seed). Same inputs, same event log, byte for byte. Every die is `roll(seed, label...)`, so editing one cell never reshuffles another.
2. No hue-only encoding: roles by shape + letter + word, outcomes by icon + word, odds as words (Solid / Risky / Long shot / No chance).
3. No timers anywhere. Planning time is unlimited; playback is a Next button (auto-advance is optional).
4. Chains are capped at 6 links a beat and every complication fires at most once a heist.
5. Fiction only: invented targets and people, nothing violent, no real brands.
6. Undo and re-plan freely before Start Heist; playback is fixed afterwards.

## Milestones
| # | Milestone | Status |
|---|-----------|--------|
| 1 | Engine core | Done |
| 2 | Plan UI | Done |
| 3 | Playback + payout | Done |
| 4 | Launch content | Done |
| 5 | Career and meta | Done |
| 6 | Standard kit | Done |
| 7 | Achievements + story | Done |
| 8 | Balance and bots | Done |
| 9 | Own-folder wrap-up | Done |
| 10 | Daily Job (optional, TODO M-1b-10) | Done, without a leaderboard (see "Daily Job") |

## For the local AI (exact names; every one was checked against the code on 2026-10-18)
- **Files**: engine `game.py` (entry point, the career, `_dispatch`, `_view`), `engine.py` (`simulate`, `preview`, `Sim`: the heist resolver), `content.py` + `content/*.json` (all rules as data: targets, crew, traits, actions, complications, gear), `plancheck.py`, `planops.py`, `writeup.py`, `story.py`, `daily.py`, `bots.py`, `achievements.py`, `info.py` (`harness.py` is a text tool, not loaded); page `index.html`, `app.js` (HC namespace, board, case file, hiring), `plan.js` (timeline, tray, inspector), `play.js` (playback, payout), `daily.js`, `mobile-tray.js`, `timeline-zoom.js`, `settings.js`, `pc.js`, `pc-config.json`, generated `pc.html`. The engine module list is `ENGINE_MODULES` (and `CONTENT_FILES` for the json) at the top of app.js.
- **Entry points** (the only Python the page calls): `handle(json_string) -> json_string`, `get_state_json()`, `load_state(proxy)`. In JS use `HC.send({action: ...})` (it adds `today`, saves and calls `HC.render()`; the reply is `{view, ok}`, an `info` action gives `{view, info}`, a refused call sets `view.note`, an error gives `{error, view}`). Never read a Python variable from JS by name. The answer is NOT the bare view: read `reply.view`.
- **Actions** (`game._dispatch`; unknown name is `{"error": "unknown action ...", "view"}`): `open` | `info` | `new_career {seed, seed_text}` | `seed_career {seed, seed_text}` | `take_job {target}` (ids `pigeon_museum the_affineur lucky_barge glasshouse_dome hilltop_observatory`) | `scout {level}` | `to_recruit` | `hire {crew}` | `background {crew}` | `gear {gear}` (ids `earplugs cat_treats lucky_coin umbrella dust_masks tea_flask sticky_gloves`) | `confirm_crew` | `place {lane, beat, cell}` (cell is an action id such as `lockpick`, or `standby:<kind>`) | `clear {lane, beat}` | `move_lane {lane, dir}` | `move_cell {lane, beat, to_lane, to_beat}` | `clear_plan` | `undo` | `redo` | `abandon` | `back_to_board` | `start_heist` | `step` | `skip` | `finish` | `retry` | `daily_open {date}` (`YYYY-MM-DD`). Plan, hiring and playback actions are ignored outside their phase. `game.py`'s docstring leaves out `info`, `seed_career` and `new_career {seed_text}`.
  A new rule = JSON in `content/*.json` first (no code for a new complication); a new action = a branch in `_dispatch`, a test, a line in the docstring.
- **Top-level keys of the view** (`game._view`): always `schema phase cash jobs_done reputation note achievements minutes career_seed_text career_untouched`; on the board also `board next_unlock relationships daily_board`; with a job `target beats requirements scout seed fees gear_cost` (+ `daily` for a daily job); from recruit `offer crew_ids gear background_fee`; from plan `crew tray plan`; in playback and payout `playback`; in payout `payout`. `phase` is one of `board scout recruit plan playback payout`. `view.plan`: `lanes messages pairs cover can_undo can_redo cells_used`. `view.playback`: `cursor n done events results heat beat_name attempt`.
- **get_state() keys**: `schema career_seed career_seed_text achievements_earned cash jobs_started meta job daily_days daily_job` (only non-defaults; `achievements_earned` is write-only). A heist is never saved, only the plan and the seed. New save fields: only when non-default and cleaned in `load_state` (`_clean_job`, `_clean_ids`), never raising.
- **Page**: `HC.render()` draws the view for the current phase through `HC.renderers[phase]`; hook after it by pushing a function onto `HC.onRender` (it gets the view). Phase sections `#phase-board #phase-scout #phase-recruit #phase-plan #phase-playback #phase-payout` (only the current one is visible); top bar `#hud-cash #hud-rep #hud-status #hud-job`. Buttons carry `data-testid`: `heist-take-<targetId>`, `heist-to-recruit`, `heist-hire-<crewId>`, `heist-gear-<gearId>`, `heist-confirm-crew`, `heist-tray-<actionId>`, `heist-cell-<lane>-<beat>`, `heist-start`, `heist-next-beat`, `heist-skip`, `heist-finish`, `heist-banner`, `heist-writeup`, `confirm-dialog-confirm`; plan ids `#timeline #inspector #tray #undo-button #redo-button #clear-plan-button #start-heist-button #check-list`; window panels `#minutes-panel #achievements-panel #changelog-panel #settings-panel #info-page-panel`; `#engine-status` is empty when the engine is ready.
- **New panel / window**: markup + toggle button in `index.html`, `panelToggle(buttonId, panelId)` in app.js `wireGlobal`, drawing in a function pushed on `HC.onRender`; for the Desktop boot add `[panelId, toggleButtonId, title]` to `pc-config.json` `windows` (and an icon or menu id), then run `/usr/bin/python3 scripts/generate-pc-pages.py` (rewrites every game's `pc.html`; only this game's changes). `tests/test_pc_boot.py` (`test_windows_cover_every_toggle_and_the_menu_holds_the_rest`, generated page up to date) fails otherwise. A new Python module goes into `ENGINE_MODULES` in app.js (`tests/test_assets_and_shell.py` checks it and the imports; `sw.js` is NOT edited by the AI).
- **New browser test**: copy `tests/test_example_browser.py` (uses `tests/browser_helpers.py`: `open_game(p, base)`; script errors are in `page.page_errors`). The older browser tests (`test_browser_smoke.py`, `test_daily_browser.py`) keep their own set-up and a full job to payout; leave them.
- **Tests that pin things a task may change**: `test_content.py` and `test_launch_content.py` (the JSON content validates; counts), `test_engine.py` (same inputs give the same log byte for byte), `test_game_handle.py` (actions, save round trips), `test_balance.py` (slow bot balance runs), `test_standard_kit.py` (changelog, shared includes, shortcut help points at real buttons), `test_career.py`, `test_career_seed.py`, `test_daily.py` (300 dates proven fair), `test_playback.py`, `test_achievements.py`, `test_assets_and_shell.py`, `test_pc_boot.py`, `test_accessibility.py`.
- **Do not**: invent a view key or an action (copy from above); look up an id in JS that `index.html` or a JS builder does not create; use a clock or `random` in the engine (every die is `engine.roll(seed, label...)`; the date comes in the request as `today`); encode anything by colour alone or add a timer; change a content id (saved jobs and careers refer to them).

## How the pieces fit
- `content/*.json` is all the rules as data (5 targets, 20 crew, 20 traits, 12 actions, 56 complications, 7 gear). `content.py` loads it and `validate()` checks it (every complication has a counter and can fire, every emitted tag is read, windows are in range). A new complication is a JSON entry, no code.
- `engine.py` resolves a heist: `simulate(...)` is pure, `preview(...)` gives the odds shown in the plan, `Sim` is the beat-by-beat resolver. `plancheck.py` writes the live checklist, `planops.py` edits the plan, `writeup.py` writes the payout text, `story.py` the banter and minutes, `achievements.py` the 14 achievements, `info.py` the How it works panel.
- `game.py` is the single entry point (`handle(json)`, `get_state`/`load_state`). The career (cash, reputation, relationships, flags, the current job) is saved; a heist is never saved, only the plan and seed, so mid-playback resume replays it exactly.
- `bots.py` and `harness.py` are tools: greedy and dice planners for the balance tests, and a text-only log printer (`python3 harness.py [target] [seed]`).
- `app.js` (board, case file, hiring, shared kit), `plan.js` (timeline, tray, inspector), `play.js` (playback, payout) are glue.
- Tests that drive the page use `index.html#play` to skip the shared opening screen.

## Decisions taken
- Cozy caper tone, invented names, Daily Job later (user answered He1-He3 yes, 2026-10-09). The player profile (private planning) shaped: no hard-lose state, retry pays only the improvement (no grinding), no timers, optional auto-advance only.
- Retrying a job keeps the seed: the same trouble arrives on the same beats, so an improved plan is really improved.
- Quirks are hidden until they fire in a heist or are paid for (background check); odds in the plan exclude hidden quirks.
- Reputation only rises when a job goes better than before, and unlocks jobs, crew and gear (derived, not stored).

## Daily Job
`daily.py` (pure, imports only `bots` and `engine`) makes one job per UTC date from the date text alone (`engine.roll` hashing, no clock, no random source, no server): the target, the night's seed, today's eight candidates (all five roles, the whole roster, career unlocks ignored) and a three-piece van. **Fairness bar:** before a date is accepted, `bots.greedy_plan` (told the three scouted kinds) must take at least 3 different five-crew combinations of the offer through that exact night with an escape and no alarm; a candidate that fails is replaced by the next one derived from the same date (about 1 in 150 dates needs a second try). `par` is the lowest payout among those witnesses; tiers are busted / escaped (alarm) / clean / par.
- The daily is a standalone night: crew, van and scouting are free, every quirk is on the file, no cash, reputation, friendships, `meta` or achievements change. `Career.job` is a property that returns the open daily job (`career.daily_job`) first, so every existing helper works on it; a daily can only be opened from the board (a career job is never put aside), and `new_career` keeps the date history.
- The view passes "today" in every request (`HC.send` adds it; tests pass dates explicitly); the engine stores it only as a runtime value (`game._today`). No date means no daily on the board. A save naming a date that is not open yet is dropped.
- Save keys, written only when non-default: `daily_days` ({date: {tier, net, tries}}, best tier and best payout, validated entry by entry) and `daily_job` (an unfinished daily night, rebuilt from its date on load: target, seed and offer come from `daily.spec`, never from the save). Old saves load unchanged.
- UI: a panel at the top of the contract board (`#daily-panel`, `daily.js`): Today's job, a month-calendar archive (any date from 2026-10-01 up to today is playable, skipped days cost nothing), a plain-language tally and a small grid of the last 120 days. No streak counter anywhere. Marks are symbols as well as shading.
- **Leaderboard: NOT built.** Hooks only: `daily.leaderboard_entry(date, record)` (pure; `view.daily.leaderboard`) and `HC.dailyLeaderboardHook` in `daily.js`, called with that entry on a daily payout when something defines it. A future backend board takes `{board: "heist-daily-job", date, score, tier}`.
- `sw.js` / `offline-manifest.json` (hub files, not edited here) must precache `games/heist-committee/daily.py`, `daily.js`; the page also loads `bots.py` now.
- Tests: `tests/test_daily.py` (determinism, 300 consecutive dates fairness-proven by replay, an exhaustive cross-check, save round trips and tampering), `tests/test_daily_browser.py` (calendar to payout on both pages at both widths).

## Desktop boot
`pc-config.json` + `pc.css` + `pc.js`; `pc.html` is generated (`scripts/generate-pc-pages.py`, never edit by hand). The whole job lives in the stage (board, case file, hiring, plan, playback, payout). Plan: timeline on top, inspector and tray under it, checklist and scouting column on the right with Undo/Redo/Clear/Start Heist adopted to the top of that column. Cash, reputation and stage are readout chips. Minutes, Achievements, What's New, Settings and How it works are windows. Escape puts a held action down first (a capture listener in plan.js), then opens the shell Menu. Known limit: at 1024 wide the stage scrolls inside itself.

## Not in this folder (blocked on the session that owns the hub files, TODO M-1b-11)
Hub registration: title card and thumbnail, `sw.js` precache (including `pc.*`), manifests, `game-*.json`, achievements page, admin, share cards, the root CLAUDE.md row, dev logs.

## Working conventions
Commit and tag each milestone (`heist-committee-milestone-0N`). Hub registration is NOT part of this folder's milestones (TODO M-1b-11, blocked on the session that owns the hub files).

## Career seed (Z-1c) and shared daily record (Z-5b), 2026-10-12
- **Career seed.** A career carries the shared seed text (`HEISTCOMMITT-K7F2Q`, prefix of `heist-committee`). The page derives the engine's `career_seed` from it (`NoyvjSeed.rng(text).randint(1, 2147483647)`); `new_career {seed, seed_text}` stores both, `seed_career` gives a career nothing has happened in yet (no job, no cash change, default meta, no text) its seed once (the page sends it on first render, so every new player has a copyable seed), and the view shows `career_seed_text` and `career_untouched`. The save writes `career_seed_text` only when present and validated (`_clean_seed_text`); older careers keep their number and show a note that they have no seed to copy. UI: a "Career seed" copy line and a start-from-seed field on the board (a confirm unless the career is untouched; Daily Job results stay). Tests: `tests/test_career_seed.py`, browser tests in `tests/test_daily_browser.py`.
- **Shared daily record (Z-5b).** Finishing TODAY's Daily Job (payout phase, `view.daily.date` equal to the UTC date) calls `NoyvjSeed.daily.markCompleted("heist-committee", {text})`, once per day; an archive date never does. It only feeds the hub's Today strip (which shows its kind streak line when the player opts in); the game itself still shows no streak. Fails soft without `shared/seed.js`.
