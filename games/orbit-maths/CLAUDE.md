# Orbit Maths

Seed: `planning/orbit-maths-plan.md`. Personal project, no BCM tag, working title. Started 2026-10-13 with `scripts/new_game.py`.
Read the plan first: it holds the design every milestone follows. Then `BUILD-STATUS.md` here.

## One-line pitch
Source: the Quick ideas round (G5), owner-approved: "short maths puzzles in a rocket-launch frame (ratios, speeds, fuel)." Checked against `PLAYER-PROFILE.md`: maths, physics and space are named interests, short wins building into a bigger picture, working it out themselves, "more game than teaching", easy-to-medium base difficulty, hint ladder, no timers (a launch has no countdown to beat), nothing lost. Personal project, no BCM tag, working title. One-line pitch: a small launch team has one rocket to get right, and every number on the checklist is a short puzzle you can solve with a pencil and a calm head.

## Stack
- Pyodide Python, plain HTML/CSS, no build step. Engine modules are plain Python with no DOM (the Signal / Lexis
  pattern): `game.py` is the entry point (`handle(json) -> json`, plus `get_state()` / `load_state()` for the
  shared save widget); `app.js` is glue only.
- No audio files. Nothing timed, nothing lost, no luck needed for 100% (the site's standing rules).

## Milestones
| # | Milestone | Content | Status |
|---|-----------|---------|--------|
| 1 | Engine | Sheet format, exact checker, units checker, sufficiency lint, stage 1 (8 sheets) with proofs | Not started |
| 2 | Sheet UI | Sheet layout, number pad and dial, calculator panel, method reveal, pad view, save contract. Playable slice | Not started |
| 3 | Stages 2-4, notebook, hints | 24 more sheets, Notebook, hint ladder, three-goals strip | Not started |
| 4 | Stage 5 and the launch | 8 more sheets (40 in all), Practice Pad, launch reveal. First complete game | Not started |
| 5 | Standard kit | Opening screen, tutorial, settings, About with live-read sources, What's New, keyboard help, light theme, accessibility pass | Not started |
| 6 | Achievements | 14 achievements, panel and toast, manifest, reachability test; Real figures sheets | Not started |
| 7 | Desktop boot and wrap-up | `pc-config.json`, `pc.css`, `pc.js`, generated `pc.html`, docs, changelog | Not started |

## Working conventions
- Commit + tag per milestone: `git commit -m "Milestone N: <name>"` then `git tag orbit-maths-milestone-0N`.
- Update the Status column as work happens, and `BUILD-STATUS.md` after every milestone.
- Hub registration is a separate step (`games/orbit-maths/register.json`, then `scripts/register_game.py orbit-maths`).
