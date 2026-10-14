# Saboteur Puzzle

Seed: `planning/saboteur-puzzle-plan.md`. Personal project, no BCM tag, working title. Started 2026-10-13 with `scripts/new_game.py`.
Read the plan first: it holds the design every milestone follows. Then `BUILD-STATUS.md` here.

## One-line pitch
Source: the Quick ideas round (E3), owner-approved: "a solo logic puzzle where you work out who among the crew is sabotaging the ship from their statements." Checked against `PLAYER-PROFILE.md`: Among Us is the best gaming memory, logic and deduction puzzles, Phasmophobia-style learn-more-get-easier, clever over fast, quiet dry humour, no all-good hero, no timers, nothing lost, a hint ladder, easy to 100%. Personal project, no BCM tag, working title. One-line pitch: six crew, one lie that matters; read their statements, mark who could be telling the truth, and name the saboteur.

## Stack
- Pyodide Python, plain HTML/CSS, no build step. Engine modules are plain Python with no DOM (the Signal / Lexis
  pattern): `game.py` is the entry point (`handle(json) -> json`, plus `get_state()` / `load_state()` for the
  shared save widget); `app.js` is glue only.
- No audio files. Nothing timed, nothing lost, no luck needed for 100% (the site's standing rules).

## Milestones
| # | Milestone | Content | Status |
|---|-----------|---------|--------|
| 1 | Engine | Statement forms, role rules, constraint solver, chapter 1 (8 cases) with uniqueness proofs | Not started |
| 2 | Case UI | Deck plan, statement sheet, notebook grid, naming and result card, save contract. Playable slice | Not started |
| 3 | Chapters 2-4, crew files, hints | 24 more cases, crew files, Pallas log, contradiction check, hint ladder, three-goals strip | Not started |
| 4 | Chapter 5 and Endless | 8 more cases (40 in all), seeded generator with solver gate, seed codes. First complete game | Not started |
| 5 | Standard kit | Opening screen, tutorial, settings, About, What's New, keyboard help, confirm dialogs, light theme, accessibility pass | Not started |
| 6 | Achievements | 14 achievements, panel and toast, manifest, reachability test | Not started |
| 7 | Desktop boot and wrap-up | `pc-config.json`, `pc.css`, `pc.js`, generated `pc.html`, docs, changelog | Not started |

## Working conventions
- Commit + tag per milestone: `git commit -m "Milestone N: <name>"` then `git tag saboteur-puzzle-milestone-0N`.
- Update the Status column as work happens, and `BUILD-STATUS.md` after every milestone.
- Hub registration is a separate step (`games/saboteur-puzzle/register.json`, then `scripts/register_game.py saboteur-puzzle`).
