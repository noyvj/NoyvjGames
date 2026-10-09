# Lighthouse (working title)

Seed: `planning/lighthouse-plan.md`. Started 2026-10-08. Not tied to a BCM assessment. Hub registration (card, thumbnail, hub lists, offline cache) is a separate later milestone done by the main session, not in `games/lighthouse/`.

## One-line pitch
You keep one light on one rock. Storms come, ships pass, oil is finite, and a small cast of passing sailors leave letters, gifts and things you cannot quite explain, while everything about the place keeps suggesting something is about to go wrong, and it never does.

## Core constraints (do not violate without asking)
1. Horror is never delivered. No jump scares, no gore, no death of the keeper, no harm to sailors from anything supernatural. Every odd detail resolves warmly (a data test enforces it from Milestone 6).
2. The keeper cannot lose. Bad nights cost oil, repairs, reputation and comfort. A ship may be delayed or damaged ("everyone aboard is safe"), never lost.
3. Nothing waits on the real clock: no offline progress, no timers, the sim runs only while the page is open and is fully pausable.
4. The story layer (letters, sailors, mysteries, odd details) is removable and the sim, saves and non-story achievements work identically with it off.
5. Never colour-only: weather, oil and repair state each have an icon, a number and a pattern or label.
6. No audio. Every "sound" is text or a visual cue.
7. Names of places and ships are invented. No real people, wrecks or disasters.

## Stack
Python via Pyodide, engine modules with no DOM (the Signal and Lexis pattern: `handle(json) -> json`, `get_state()` / `load_state()` for the save widget), plain HTML/CSS with an inline SVG scene, no build step. Art is drawn by code as SVG.

## Modules (engine, no DOM)
`rng.py` stateless seeded randomness; `data.py` every rule number; `clock.py` calendar; `weather.py` and `ships.py` the seeded night; `cast.py` labels ships with sailors; `state.py` the validated save; `sim.py` the night; `day.py` the day; `goals.py` three standing goals; `lore.py` the cast, letters and gifts as data; `story.py` post, gifts, replies; `mysteries.py` the dread ledger as data; `unease.py` the year's schedule and the hidden meter; `achievements.py`; `view.py` builds the whole view; `game.py` `handle(json)`, `get_state()`, `load_state()`. `harness.py` plays nights as text and holds the test policies (not loaded by the page).

## Milestones
| # | Milestone | Status |
|---|---|---|
| 1 | Sim core: seeded weather and ship generators, tick `step()`, oil/brightness/clockwork/structure/energy, day module, `handle`/save contract, text harness | DONE (tagged) |
| 2 | Night UI: SVG scene, beam, ship silhouettes, evening plan, morning report, speed/pause | DONE (tagged) |
| 3 | Day loop + upgrades: day tasks, workshop (9 upgrades), boat order, seasons, barometer, three standing goals | DONE (tagged) |
| 4 | Complete Quiet mode: one year to completion, endless continue, save widget, settings, confirm dialogs | DONE (tagged) |
| 5 | Cast, letters, gifts: 10 sailors, 23 letters, 11 gifts, room scene, reply choices, story toggle | DONE (tagged) |
| 6 | The Unease: 6 mysteries, 8 small oddities, hidden unease meter, dread-ledger tests, Eerie details switch, content note | DONE (tagged) |
| 7 | Standard kit: tutorial, phone HUD strip and dock, About the Light (sourced), colourblind audit | DONE (tagged) |
| 8 | Achievements + polish | not started |
| 9 | Own-folder wrap-up | not started |
