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

## Desktop boot
`pc-config.json` + `pc.css` + `pc.js`; `pc.html` is generated (`scripts/generate-pc-pages.py`, never edit by hand). The whole job lives in the stage (board, case file, hiring, plan, playback, payout). Plan: timeline on top, inspector and tray under it, checklist and scouting column on the right with Undo/Redo/Clear/Start Heist adopted to the top of that column. Cash, reputation and stage are readout chips. Minutes, Achievements, What's New, Settings and How it works are windows. Escape puts a held action down first (a capture listener in plan.js), then opens the shell Menu. Known limit: at 1024 wide the stage scrolls inside itself.

## Not in this folder (blocked on the session that owns the hub files, TODO M-1b-11)
Hub registration: title card and thumbnail, `sw.js` precache (including `pc.*`), manifests, `game-*.json`, achievements page, admin, share cards, the root CLAUDE.md row, dev logs.

## Working conventions
Commit and tag each milestone (`heist-committee-milestone-0N`). Hub registration is NOT part of this folder's milestones (TODO M-1b-11, blocked on the session that owns the hub files).
