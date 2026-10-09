# Lighthouse (working title)

Seed: `planning/lighthouse-plan.md`. Built 2026-10-08 to 2026-10-09. Not tied to a BCM assessment. Hub registration (title card, thumbnail, tags, `sw.js` precache, manifests, root games table, sitemap, share cards, `scripts/perf-budget.json`, smoke tests) is a separate later milestone (TODO M-2b-10) done by the main session, not in `games/lighthouse/`. The favicon lives in `games/lighthouse/icons/favicon-lighthouse.svg` (the hub convention puts favicons in `icons/`; move or copy it at registration).

## One-line pitch
You keep one light on one rock. Storms come, ships pass, oil is finite, and a small cast of passing sailors leave letters, gifts and things you cannot quite explain, while everything about the place keeps suggesting something is about to go wrong, and it never does.

## Core constraints (do not violate without asking)
1. Horror is never delivered. No jump scares, no gore, no death of the keeper, no harm to sailors from anything supernatural. Every odd detail resolves warmly; `tests/test_dread_ledger.py` and the banned-word lints enforce it.
2. The keeper cannot lose. Bad nights cost oil, repairs, reputation and comfort. A ship may be delayed or damaged ("everyone aboard is safe"), never lost. Owner answer (Li1): no ships missing for dramatic effect for now; maybe later.
3. Nothing waits on the real clock: no offline progress, no timers, the sim runs only while the page is open and is fully pausable.
4. The story layer (letters, sailors, mysteries, odd details) is removable: a Quiet run has none of it, and with it on but no letter read the sim is identical (tested).
5. Never colour-only: weather, oil and repair state each have an icon or a pattern, a number and a word.
6. No audio. Every "sound" is text or a visual cue.
7. Names of places and ships are invented. No real people, wrecks or disasters. The only real facts are the four on the About page, each with a named source and the date it was read.
8. Eerie details (the odd and moment beats and small oddities) have their own always-visible switch; kind beats, letters and resolutions stay when it is off.

## Stack
Python via Pyodide, engine modules with no DOM (the Signal and Lexis pattern: `handle(json) -> json`, `get_state()` / `load_state()` for the save widget), plain HTML/CSS with an inline SVG scene, no build step. Art is drawn by code as SVG. The page loads the modules listed in `app.js` `ENGINE_MODULES`; `harness.py` (text harness and test policies) is not loaded.

## How it plays
Each **evening** you read the barometer (a two-step band, right about nine nights in ten) and the harbour board, set a lamp level (Dim, Standard, Bright, Storm: reach 3, 5, 7, 9; oil 0.6, 1.0, 1.6, 2.6 per tick) for dusk, deep night and dawn, an optional oil ration, and the keeper's rounds (wind the clockwork, keep watch, patch between rounds). The **night** runs in ticks of ten minutes (one tick per 4 s at 1x; 2x and 4x; pause is free; Space, `[`, `]`, 1 to 4, W, T). A ship passes safely when the beam, after weather and glass and clockwork, reaches it for half its time near the rock; otherwise it turns back or runs on the shoals. The **morning** report shows the ships, lamp-hours, oil, damage, letters. The **day** has five tasks (mend, sleep, tidy, walk the tideline, tend the greenhouse, help a ship), a workshop of nine upgrades paid in salvage, and the supply boat's twelve crates to order. Forty nights make a year (four seasons, a festival night on night 20 with no ships); then a year-end screen and endless play. Three standing goals are always on screen.

## Modules (engine, no DOM)
`rng.py` stateless seeded randomness (nothing random is ever saved); `data.py` every rule number; `clock.py` calendar; `weather.py` and `ships.py` the seeded night; `cast.py` labels ships with sailors (renames only, never changes the sim); `state.py` the validated save (`Keep`, writes only non-defaults, never raises on load); `sim.py` the night; `day.py` the day; `goals.py` three standing goals; `lore.py` the cast, letters and gifts as data; `story.py` post, gifts, replies, beats, oddities, notebook; `mysteries.py` the dread ledger as data (6 mysteries, 35 beats, 8 small oddities); `unease.py` the year's pure schedule, odd-streak rules and the hidden meter; `info.py` the About panel; `achievements.py` (21, manifest in `achievements.json`); `view.py` builds the whole view; `game.py` the entry point and the save contract.

## Save contract
`get_state()` returns `{schema, meta, run, achievements_earned}`. `meta` is lifetime (counters, sets of letters read, gifts, sailors met, mysteries, oddities, achievements); `run` is the current year (seed, night, phase, tick, stocks, plan, progress through tonight's ships, story progress). Weather, ships and the mystery schedule are regenerated from the seed, never stored. `load_state` replaces the run with a validated one, calls `window.lighthouseRefresh()`, and never raises. Display choices (text size, reduce motion, effects, contrast, pause when hidden, Eerie details, Quiet for the next year, content-note seen) are per-device localStorage, not in the save.

## Milestones
| # | Milestone | Status |
|---|---|---|
| 1 | Sim core: seeded weather and ship generators, tick `step()`, oil/brightness/clockwork/structure/energy, day module, `handle`/save contract, text harness | DONE (tagged `lighthouse-milestone-01`) |
| 2 | Night UI: SVG scene, beam, ship silhouettes, evening plan, morning report, speed/pause | DONE (tagged) |
| 3 | Day loop + upgrades: day tasks, workshop (9 upgrades), boat order, seasons, barometer, three standing goals | DONE (tagged) |
| 4 | Complete Quiet mode: one year to completion, endless continue, save widget, settings, confirm dialogs | DONE (tagged) |
| 5 | Cast, letters, gifts: 10 sailors, 23 letters, 18 gifts in all, room scene, reply choices, story toggle | DONE (tagged) |
| 6 | The Unease: 6 mysteries, 8 small oddities, hidden unease meter, dread-ledger tests, Eerie details switch, content note | DONE (tagged) |
| 7 | Standard kit: tutorial, phone HUD strip and dock, About the Light (sourced), colourblind audit | DONE (tagged) |
| 8 | Achievements + polish: 21 achievements, copy lint, timing test, balance bots | DONE (tagged) |
| 9 | Own-folder wrap-up: favicon, Desktop boot, this file, tag | DONE (tagged `lighthouse-milestone-09`) |
| 10 | Hub registration (card, tags, `sw.js`, manifests, root CLAUDE.md row, share cards, perf budget, smoke tests, `scripts/generate-pc-pages.py --check`) | BLOCKED ON NOY2 (shared files), not started |

## Desktop boot
`pc-config.json` (windows for Letters, Achievements, What's New, Settings, About; icons for Letters, Achievements, Settings; Menu for Eerie details, Tutorial, About, credits, What's New; readout chips for Night, Clock, Oil, Energy, The Light, Salvage), `pc.css` (the rock and the keeper's log as the stage, the plan, night controls, report and day tasks plus the station in the right column), `pc.js` (the Desktop tutorial, picked up through `window.lighthouseTutorialSteps`), and a generated `pc.html` (built for this game only with `scripts/generate-pc-pages.py`'s `build("lighthouse", cfg)`; never edited by hand). `python3 -m pytest -q shared/tests -k lighthouse` passes. Checked live at 1440x900 and 1024x700.

## Writing rules for new story content
Add a mystery as data in `mysteries.py` in the shape build, moment, kind beat, one warm resolve, with a window for each beat that leaves room, then run `tests/test_dread_ledger.py`: it proves a thousand seeded years place every beat inside the rules. People are flawed and specific; humour is dry and a little dark, never absurd; no banned words (the lint list is in `tests/test_story_data.py`); no dashes; resolutions are self-contained so they read well with Eerie details off.

## Tests
`python3 -m pytest -q games/lighthouse` (about 190 tests, 30 s) and `python3 -m flake8 --extend-ignore=E501 games/lighthouse`. There is no fake-DOM harness because the view is glue; the page was driven live in the browser pane (Pyodide needs network for the CDN, so no automated browser test is possible offline).

## Known limits and ideas
- Panel text and the SVG scene are verified by source-level tests plus live checks; a Playwright run needs network for Pyodide.
- Sailors write in year one; after that only the post-year mysteries stay solved and the rest of the world keeps running (endless mode has no new letters).
- Ideas not built: more mysteries and sailors (data only), missing ships for drama (owner: later), a leaderboard (none planned on purpose), story chapters through `shared/story-chapters.js` (the plan listed it; the notebook of odd things does that job).
