# Housing Board

Seed: `planning/housing-board-plan.md`. Personal project, no BCM tag, working title. Started 2026-10-13 with `scripts/new_game.py`.
Read the plan first: it holds the design every milestone follows. Then `BUILD-STATUS.md` here.

## One-line pitch
Source: the Quick ideas round (B8), owner-approved: "allocate a limited set of homes between competing needs and see how each side judges the result." Checked against `PLAYER-PROFILE.md`: housing named as a caring topic, helper role, real-world games show several points of view, planning with no randomness, "fun that happens to be accurate", three goals, no timers, nothing lost. Personal project, no BCM tag, working title. Different from Water Works (a spatial flow network): this is an assignment puzzle with a panel of judges.

## Stack
- Pyodide Python, plain HTML/CSS, no build step. Engine modules are plain Python with no DOM (the Signal / Lexis
  pattern): `game.py` is the entry point (`handle(json) -> json`, plus `get_state()` / `load_state()` for the
  shared save widget); `app.js` is glue only.
- No audio files. Nothing timed, nothing lost, no luck needed for 100% (the site's standing rules).

## Milestones
| # | Milestone | Content | Status |
|---|-----------|---------|--------|
| 1 | Rules and judges | Homes, households, five voices, verdict engine, assignment brute-forcer, chapter 1 (6 rounds) with proofs | Not started |
| 2 | Board UI | Home cards, household portraits, drag assign, voices panel with reasons, reset, save contract. Playable slice | Not started |
| 3 | Chapters 2-3 | 12 more rounds, waiting lists and access, Case Book | Not started |
| 4 | Chapters 4-5, hints, goals | 12 more rounds (30), finance voice, whole estate, town map, hint ladder, three-goals strip, live facts. First complete game | Not started |
| 5 | Standard kit | Opening screen, tutorial, About with Sources, What's New, keyboard help, confirm dialogs, light theme, accessibility | Not started |
| 6 | Achievements | 14 achievements, panel and toast, manifest, reachability test | Not started |
| 7 | Desktop boot and wrap-up | `pc-config.json`, `pc.css`, `pc.js`, generated `pc.html`, docs, changelog | Not started |

## Working conventions
- Commit + tag per milestone: `git commit -m "Milestone N: <name>"` then `git tag housing-board-milestone-0N`.
- Update the Status column as work happens, and `BUILD-STATUS.md` after every milestone.
- Hub registration is a separate step (`games/housing-board/register.json`, then `scripts/register_game.py housing-board`).
