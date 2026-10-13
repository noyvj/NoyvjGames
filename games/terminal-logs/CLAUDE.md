# Terminal Logs

Seed: `planning/terminal-logs-plan.md`. Personal project, no BCM tag, working title. Started 2026-10-13 with `scripts/new_game.py`.
Read the plan first: it holds the design every milestone follows. Then `BUILD-STATUS.md` here.

## One-line pitch
Source: the Quick ideas round (D6), owner-approved: "a choose-your-own-adventure told only through a computer terminal's logs and your commands." Checked against `PLAYER-PROFILE.md`: computers and science fiction, Lifeline-style branching story, a notebook that fills in, collecting and solving, quiet tragic-but-gentle characters (never an all-good hero), hint ladder, free rewinds, no timers, no visual novel, no on-screen death, coding and logic interest. Personal project, no BCM tag, working title. One-line pitch: you log in to the dead computer of a survey ship, read what the crew and the ship left behind, and choose which commands to run until you know what happened to the Anselm.

## Stack
- Pyodide Python, plain HTML/CSS, no build step. Engine modules are plain Python with no DOM (the Signal / Lexis
  pattern): `game.py` is the entry point (`handle(json) -> json`, plus `get_state()` / `load_state()` for the
  shared save widget); `app.js` is glue only.
- No audio files. Nothing timed, nothing lost, no luck needed for 100% (the site's standing rules).

## Milestones
| # | Milestone | Content | Status |
|---|-----------|---------|--------|
| 1 | Engine | File system, command rules, graph validator, first two directories (about 30 files) with tests | Not started |
| 2 | Terminal UI | Terminal frame, command palette, file list, rewind, ship map, save contract. Playable slice | Not started |
| 3 | The ship fills in | Remaining directories, scripts, forks, Archive Index, hint ladder, three-goals strip | Not started |
| 4 | Endings | The five endings, par paths, final polish of the logs. First complete game | Not started |
| 5 | Standard kit | Opening screen, tutorial, settings, About with live-read sources and fiction notice, What's New, keyboard help, light theme, accessibility pass | Not started |
| 6 | Achievements | 14 achievements, panel and toast, manifest, reachability test | Not started |
| 7 | Desktop boot and wrap-up | `pc-config.json`, `pc.css`, `pc.js`, generated `pc.html`, docs, changelog | Not started |

## Working conventions
- Commit + tag per milestone: `git commit -m "Milestone N: <name>"` then `git tag terminal-logs-milestone-0N`.
- Update the Status column as work happens, and `BUILD-STATUS.md` after every milestone.
- Hub registration is a separate step (`games/terminal-logs/register.json`, then `scripts/register_game.py terminal-logs`).
