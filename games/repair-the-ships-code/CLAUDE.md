# Repair the Ship's Code

Seed: `planning/repair-the-ships-code-plan.md`. Personal project, no BCM tag, working title. Started 2026-10-13 with `scripts/new_game.py`.
Read the plan first: it holds the design every milestone follows. Then `BUILD-STATUS.md` here.

## One-line pitch
Source: the Quick ideas round (G1), owner-approved: "learn Python by fixing a starship's broken functions, with tests that go green as you fix each one." Checked against `PLAYER-PROFILE.md`: coding and logic puzzle games (yes), space and computers, helper and fixer role, short wins that build a bigger picture, hint ladder, easy-to-medium base difficulty, "more game than teaching", working it out themselves, no timers, nothing lost. Personal project, no BCM tag, working title. One-line pitch: the starship **Wren** is limping home on broken functions; open a system, read its failing tests, fix the code and watch the lights come back.

## Stack
- Pyodide Python, plain HTML/CSS, no build step. Engine modules are plain Python with no DOM (the Signal / Lexis
  pattern): `game.py` is the entry point (`handle(json) -> json`, plus `get_state()` / `load_state()` for the
  shared save widget); `app.js` is glue only.
- No audio files. Nothing timed, nothing lost, no luck needed for 100% (the site's standing rules).

## Milestones
| # | Milestone | Content | Status |
|---|-----------|---------|--------|
| 1 | Engine | Sandbox runner with step budget, level format, checker, chapter 1 (6 levels) with fix, bug-diff and mutation proofs | Not started |
| 2 | Editor UI | Editor, tests list, Run and Reset, ship cutaway, phone token mode, save contract. Playable slice | Not started |
| 3 | Chapters 2-4, bestiary, hints | 18 more levels, Bug Bestiary, hint ladder, three-goals strip | Not started |
| 4 | Chapters 5-6 and Home Run | 12 more levels (36 in all), final level. First complete game | Not started |
| 5 | Standard kit | Opening screen, tutorial, settings, About with live-read sources, What's New, keyboard help, light theme, accessibility pass | Not started |
| 6 | Achievements | 14 achievements, panel and toast, manifest, reachability test | Not started |
| 7 | Desktop boot and wrap-up | `pc-config.json`, `pc.css`, `pc.js`, generated `pc.html`, docs, changelog | Not started |

## Working conventions
- Commit + tag per milestone: `git commit -m "Milestone N: <name>"` then `git tag repair-the-ships-code-milestone-0N`.
- Update the Status column as work happens, and `BUILD-STATUS.md` after every milestone.
- Hub registration is a separate step (`games/repair-the-ships-code/register.json`, then `scripts/register_game.py repair-the-ships-code`).
