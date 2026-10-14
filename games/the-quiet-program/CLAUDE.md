# The Quiet Program

Seed: `planning/the-quiet-program-plan.md`. Personal project, no BCM tag, working title. Started 2026-10-13 with `scripts/new_game.py`.
Read the plan first: it holds the design every milestone follows. Then `BUILD-STATUS.md` here.

## One-line pitch
Source: the Quick ideas round (D2), owner-approved: "advise a broken but gentle program on a failing computer network (a tragic, quiet character in the spirit of the one you like)." Checked against `PLAYER-PROFILE.md`: tragic, quiet, broken-savior characters (never an all-good hero), a barely-speaking companion that shows emotion, helper and healer role, computers and robots, dark moody, short wins that build a slow arc, a hint ladder, no timers, nothing lost, no self-harm and no self-hatred spirals. Personal project, no BCM tag, working title. One-line pitch: a failing network is held together by a gentle old program called Wick, and you are the one voice it listens to while it tries to deliver the last messages.

## Stack
- Pyodide Python, plain HTML/CSS, no build step. Engine modules are plain Python with no DOM (the Signal / Lexis
  pattern): `game.py` is the entry point (`handle(json) -> json`, plus `get_state()` / `load_state()` for the
  shared save widget); `app.js` is glue only.
- No audio files. Nothing timed, nothing lost, no luck needed for 100% (the site's standing rules).

## Milestones
| # | Milestone | Content | Status |
|---|-----------|---------|--------|
| 1 | Engine | Net, link and beat rules, Wick faults, solver proof, chapter 1 (6 Evenings) with tests | Not started |
| 2 | Evening UI | SVG net, advice lines, beat playback, Wick lamp, result card, Restore, save contract. Playable slice | Not started |
| 3 | Chapters 2-3, fragments, hints | 12 more Evenings, memory fragments, net map, hint ladder, three-goals strip | Not started |
| 4 | Chapters 4-5 and endings | 12 more Evenings (30 in all), Quiet Hours, three endings. First complete game | Not started |
| 5 | Standard kit | Opening screen, tutorial, settings, About with the fiction note, What's New, confirm dialogs, light theme, accessibility pass | Not started |
| 6 | Achievements | 14 achievements, panel and toast, manifest, reachability test | Not started |
| 7 | Desktop boot and wrap-up | `pc-config.json`, `pc.css`, `pc.js`, generated `pc.html`, docs, changelog | Not started |

## Working conventions
- Commit + tag per milestone: `git commit -m "Milestone N: <name>"` then `git tag the-quiet-program-milestone-0N`.
- Update the Status column as work happens, and `BUILD-STATUS.md` after every milestone.
- Hub registration is a separate step (`games/the-quiet-program/register.json`, then `scripts/register_game.py the-quiet-program`).
