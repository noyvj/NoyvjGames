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

## Milestones
| # | Milestone | Status |
|---|---|---|
| 1 | Sim core: seeded weather and ship generators, tick `step()`, oil/brightness/clockwork/structure/energy, day module, `handle`/save contract, text harness | DONE (tagged) |
| 2 | Night UI: SVG scene, beam, ship silhouettes, evening plan, morning report, speed/pause | DONE (tagged) |
| 3 | Day loop + upgrades | not started |
| 4 | Complete Quiet mode | not started |
| 5 | Cast, letters, gifts | not started |
| 6 | The Unease | not started |
| 7 | Standard kit | not started |
| 8 | Achievements + polish | not started |
| 9 | Own-folder wrap-up | not started |
