# Keep Talking

Seed: `planning/keep-talking-plan.md`. Personal project, no BCM tag, working title. Started 2026-10-13 with `scripts/new_game.py`.
Read the plan first: it holds the design every milestone follows. Then `BUILD-STATUS.md` here.

## One-line pitch
Source: the Quick ideas round (E1), owner-approved: "two players each see half of a puzzle and have to talk it out (voice or text in whatever app they already use), joined by an invite link." Checked against `PLAYER-PROFILE.md`: loved Keep Talking and Nobody Explodes for how people communicate badly, Among Us banter, co-op where two friends fix one problem, optional friend ties, helper role, no timers, no chat built in, no mandatory friend feature. Personal project, no BCM tag, working title. One-line pitch: one player holds the control panel, the other holds the manual, and neither can solve the vault door alone.

## Stack
- Pyodide Python, plain HTML/CSS, no build step. Engine modules are plain Python with no DOM (the Signal / Lexis
  pattern): `game.py` is the entry point (`handle(json) -> json`, plus `get_state()` / `load_state()` for the
  shared save widget); `app.js` is glue only.
- No audio files. Nothing timed, nothing lost, no luck needed for 100% (the site's standing rules).

## Milestones
| # | Milestone | Content | Status |
|---|-----------|---------|--------|
| 1 | Engine | Seed to job, Wires and Symbol Pad generators, information-split proofs, 12 jobs with tests | Not started |
| 2 | Solo UI | Panel and Manual screens, Pim, solo roles, answer entry, save contract. Playable slice (solo) | Not started |
| 3 | More modules | Dials, Lamps, Maze, 24 more jobs (36 in all), hint ladder, three-goals strip. First complete game | Not started |
| 4 | Invite links | Invite link parsing, role choice, two-browser play, tamper-proof link validator, Endless mode | Not started |
| 5 | Standard kit | Opening screen, tutorial, settings, About, What's New, keyboard help, light theme, accessibility pass | Not started |
| 6 | Achievements | 14 achievements, panel and toast, manifest, reachability test | Not started |
| 7 | Desktop boot and wrap-up | `pc-config.json`, `pc.css`, `pc.js`, generated `pc.html`, docs, changelog | Not started |

## Working conventions
- Commit + tag per milestone: `git commit -m "Milestone N: <name>"` then `git tag keep-talking-milestone-0N`.
- Update the Status column as work happens, and `BUILD-STATUS.md` after every milestone.
- Hub registration is a separate step (`games/keep-talking/register.json`, then `scripts/register_game.py keep-talking`).
