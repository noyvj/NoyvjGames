# Binary Bakery

Seed: `planning/binary-bakery-plan.md`. Personal project, no BCM tag, working title. Started 2026-10-13 with `scripts/new_game.py`.
Read the plan first: it holds the design every milestone follows. Then `BUILD-STATUS.md` here.

## One-line pitch
Source: the Quick ideas round (G4), owner-approved: "a calm game where you build numbers from binary switches to fill orders." Checked against `PLAYER-PROFILE.md`: calm "routine you know by heart" feel, collecting every item (one of each bake), coding and maths interest, Unpacking-style calm, short wins building one bigger picture, three goals, easy to 100%, no timers, orders that never expire. Personal project, no BCM tag, working title. One-line pitch: a night bakery run by switches, where every order is a number and every number is a row of trays turned on or off.

## Stack
- Pyodide Python, plain HTML/CSS, no build step. Engine modules are plain Python with no DOM (the Signal / Lexis
  pattern): `game.py` is the entry point (`handle(json) -> json`, plus `get_state()` / `load_state()` for the
  shared save widget); `app.js` is glue only.
- No audio files. Nothing timed, nothing lost, no luck needed for 100% (the site's standing rules).

## Milestones
| # | Milestone | Content | Status |
|---|-----------|---------|--------|
| 1 | Engine | Bit rows, order kinds, exhaustive solver, chapters 1-2 (14 slips) with proofs | Not started |
| 2 | Counter UI | SVG counter, trays and switches, order spike, bell, save contract. Playable slice | Not started |
| 3 | Chapters 3-5, Bake Book, hints | 21 more slips, Bake Book, shop front, hint ladder, three-goals strip | Not started |
| 4 | Chapter 6 and Practice Counter | 7 more slips (42 in all), letter cakes and hex icing, seeded practice. First complete game | Not started |
| 5 | Standard kit | Opening screen, tutorial, settings, About with live-read sources, What's New, keyboard help, light theme, accessibility pass | Not started |
| 6 | Achievements | 14 achievements, panel and toast, manifest, reachability test | Not started |
| 7 | Desktop boot and wrap-up | `pc-config.json`, `pc.css`, `pc.js`, generated `pc.html`, docs, changelog | Not started |

## Working conventions
- Commit + tag per milestone: `git commit -m "Milestone N: <name>"` then `git tag binary-bakery-milestone-0N`.
- Update the Status column as work happens, and `BUILD-STATUS.md` after every milestone.
- Hub registration is a separate step (`games/binary-bakery/register.json`, then `scripts/register_game.py binary-bakery`).
