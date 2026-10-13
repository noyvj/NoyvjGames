# Glitch Hunter

Seed: `planning/glitch-hunter-plan.md`. Personal project, no BCM tag, working title. Started 2026-10-13 with `scripts/new_game.py`.
Read the plan first: it holds the design every milestone follows. Then `BUILD-STATUS.md` here.

## One-line pitch
Source: the Quick ideas round (C3), owner-approved: "small levels with deliberate, harmless exploits; the goal is to break the rules and the log records every glitch you found." Checked against `PLAYER-PROFILE.md`: loves watching glitch and build-breaking videos, feels clever finding the one broken build, collecting and solving, a collection that fills in, three goals at once, easy to 100%, no tutorial needed, no timers, nothing lost, dry dark humour. Personal project, no BCM tag, working title. One-line pitch: you are a night-shift tester in an old test lab; every tiny room states its rules, and your job is to break them on purpose and log how.

## Stack
- Pyodide Python, plain HTML/CSS, no build step. Engine modules are plain Python with no DOM (the Signal / Lexis
  pattern): `game.py` is the entry point (`handle(json) -> json`, plus `get_state()` / `load_state()` for the
  shared save widget); `app.js` is glue only.
- No audio files. Nothing timed, nothing lost, no luck needed for 100% (the site's standing rules).

## Milestones
| # | Milestone | Content | Status |
|---|-----------|---------|--------|
| 1 | Engine | Room rules, quirk flags, breadth-first glitch solver, chapter 1 (6 rooms) with proofs and tests | Not started |
| 2 | Room UI | SVG room, move and keyboard input, rule card, glitch stamp and replay clip, Reset, save contract. Playable slice | Not started |
| 3 | Chapters 2-4 and the log | 18 more rooms, Glitch Log, Defect Wall, hint ladder, three-goals strip | Not started |
| 4 | Chapters 5-6 and the finale | 12 more rooms (36 in all), decoys, Free Poke, The Original Build. First complete game | Not started |
| 5 | Standard kit | Opening screen, tutorial, settings, About with live-read sources, What's New, confirm dialogs, light theme, accessibility pass | Not started |
| 6 | Achievements | 14 achievements, panel and toast, manifest, reachability test | Not started |
| 7 | Desktop boot and wrap-up | `pc-config.json`, `pc.css`, `pc.js`, generated `pc.html`, docs, changelog | Not started |

## Working conventions
- Commit + tag per milestone: `git commit -m "Milestone N: <name>"` then `git tag glitch-hunter-milestone-0N`.
- Update the Status column as work happens, and `BUILD-STATUS.md` after every milestone.
- Hub registration is a separate step (`games/glitch-hunter/register.json`, then `scripts/register_game.py glitch-hunter`).
