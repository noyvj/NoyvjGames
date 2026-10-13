# Fog Rescue

Seed: `planning/fog-rescue-plan.md`. Personal project, no BCM tag, working title. Started 2026-10-13 with `scripts/new_game.py`.
Read the plan first: it holds the design every milestone follows. Then `BUILD-STATUS.md` here.

## One-line pitch
Source: the Quick ideas round (B3), owner-approved: "guide lost animals or travellers out of a dark foggy forest by lighting the right lanterns in the right order." Checked against `PLAYER-PROFILE.md`: a helper role, dark moody setting with fog, one puzzle at a time, short wins into a bigger picture, nothing lost, no on-screen harm, no timers. Related to the foggy-forest dream game idea as a possible small piece, built as a separate game and not tied to it. Personal project, no BCM tag, working title.

## Stack
- Pyodide Python, plain HTML/CSS, no build step. Engine modules are plain Python with no DOM (the Signal / Lexis
  pattern): `game.py` is the entry point (`handle(json) -> json`, plus `get_state()` / `load_state()` for the
  shared save widget); `app.js` is glue only.
- No audio files. Nothing timed, nothing lost, no luck needed for 100% (the site's standing rules).

## Milestones
| # | Milestone | Content | Status |
|---|-----------|---------|--------|
| 1 | Engine and solver | Graph, lantern and creature rules, BFS solver, dead-state check, chapter 1 (8 woods) with proofs | Not started |
| 2 | Wood UI | SVG wood and fog, tap-to-light, glow animation (toggleable), step back and restore, save contract. Playable slice | Not started |
| 3 | Chapters 2-3 | 16 more woods, Owl, reach and blocked paths, Lost and Found board | Not started |
| 4 | Chapters 4-5, hints, goals | 16 more woods (40), Fox and Lamb, Cast book, hint ladder, three-goals strip. First complete game | Not started |
| 5 | Standard kit | Opening screen, tutorial, About with Sources, What's New, keyboard help, confirm dialogs, light theme, accessibility | Not started |
| 6 | Achievements | 14 achievements, panel and toast, manifest, reachability test | Not started |
| 7 | Desktop boot and wrap-up | `pc-config.json`, `pc.css`, `pc.js`, generated `pc.html`, docs, changelog | Not started |

## Working conventions
- Commit + tag per milestone: `git commit -m "Milestone N: <name>"` then `git tag fog-rescue-milestone-0N`.
- Update the Status column as work happens, and `BUILD-STATUS.md` after every milestone.
- Hub registration is a separate step (`games/fog-rescue/register.json`, then `scripts/register_game.py fog-rescue`).
