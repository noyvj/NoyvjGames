# Derelict Garden

Seed: `planning/derelict-garden-plan.md`. Personal project, no BCM tag, working title. Started 2026-10-13 with `scripts/new_game.py`.
Read the plan first: it holds the design every milestone follows. Then `BUILD-STATUS.md` here.

## One-line pitch
Source: the Quick ideas round (B5), owner-approved: "tend a garden on an abandoned ship, restoring one section at a time, with a steady-progress-that-cannot-be-lost feel." Checked against `PLAYER-PROFILE.md`: steady progress that can never be lost and a routine they know by heart (named as relaxed), collecting one of each species, space and robots, a companion robot that barely speaks, Unpacking-like calm without perfectionism, no timers, no energy, no grinding. Personal project, no BCM tag, working title.

## Stack
- Pyodide Python, plain HTML/CSS, no build step. Engine modules are plain Python with no DOM (the Signal / Lexis
  pattern): `game.py` is the entry point (`handle(json) -> json`, plus `get_state()` / `load_state()` for the
  shared save widget); `app.js` is glue only.
- No audio files. Nothing timed, nothing lost, no luck needed for 100% (the site's standing rules).

## Milestones
| # | Milestone | Content | Status |
|---|-----------|---------|--------|
| 1 | Engine and solver | Need model, fixtures, growth steps, placement solver, sections 1-3 with proofs and the monotone-progress test | Not started |
| 2 | Garden UI | SVG deck, drag or tap-place fixtures, growth animation (toggleable), save contract. Playable slice | Not started |
| 3 | Sections 4-8 | 5 more sections, shade and neighbour needs, Greenhouse Book and plant cards | Not started |
| 4 | Sections 9-12, hints, goals | 4 more sections (12), ship rarities, hint ladder, three-goals strip, live GBIF facts. First complete game | Not started |
| 5 | Standard kit | Opening screen, tutorial, About with Sources, What's New, keyboard help, confirm dialogs, light theme, accessibility | Not started |
| 6 | Achievements | 14 achievements, panel and toast, manifest, reachability test | Not started |
| 7 | Desktop boot and wrap-up | `pc-config.json`, `pc.css`, `pc.js`, generated `pc.html`, docs, changelog | Not started |

## Working conventions
- Commit + tag per milestone: `git commit -m "Milestone N: <name>"` then `git tag derelict-garden-milestone-0N`.
- Update the Status column as work happens, and `BUILD-STATUS.md` after every milestone.
- Hub registration is a separate step (`games/derelict-garden/register.json`, then `scripts/register_game.py derelict-garden`).
