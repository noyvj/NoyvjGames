# Pattern Match

Seed: `planning/pattern-match-plan.md`. Personal project, no BCM tag, working title. Started 2026-10-13 with `scripts/new_game.py`.
Read the plan first: it holds the design every milestone follows. Then `BUILD-STATUS.md` here.

## One-line pitch
Source: the Quick ideas round (G3), owner-approved: "learn regular expressions by filtering garbled transmissions." Checked against `PLAYER-PROFILE.md`: coding and logic puzzles (yes), space and computers, short wins, a notebook or shelf that fills, hint ladder, "more game than teaching", working it out themselves, no timers, nothing lost. Personal project, no BCM tag, working title. One-line pitch: signals arrive from the dark half-eaten by noise; write a short pattern that catches the real messages and lets the static fall through.

## Stack
- Pyodide Python, plain HTML/CSS, no build step. Engine modules are plain Python with no DOM (the Signal / Lexis
  pattern): `game.py` is the entry point (`handle(json) -> json`, plus `get_state()` / `load_state()` for the
  shared save widget); `app.js` is glue only.
- No audio files. Nothing timed, nothing lost, no luck needed for 100% (the site's standing rules).

## Milestones
| # | Milestone | Content | Status |
|---|-----------|---------|--------|
| 1 | Engine | Matcher with step budget, conformance tests against `re`, tape checker, chapter 1 (6 tapes) with tempting-wrong proofs | Not started |
| 2 | Receiver UI | Pattern field, live marking, status words, signal log, save contract. Playable slice | Not started |
| 3 | Chapters 2-4, toolbox, hints | 18 more tapes, Toolbox, hint ladder, three-goals strip | Not started |
| 4 | Chapters 5-6 and Practice Static | 12 more tapes (36 in all), extract tapes, seeded practice. First complete game | Not started |
| 5 | Standard kit | Opening screen, tutorial, settings, About with live-read sources, What's New, keyboard help, light theme, accessibility pass | Not started |
| 6 | Achievements | 14 achievements, panel and toast, manifest, reachability test | Not started |
| 7 | Desktop boot and wrap-up | `pc-config.json`, `pc.css`, `pc.js`, generated `pc.html`, docs, changelog | Not started |

## Working conventions
- Commit + tag per milestone: `git commit -m "Milestone N: <name>"` then `git tag pattern-match-milestone-0N`.
- Update the Status column as work happens, and `BUILD-STATUS.md` after every milestone.
- Hub registration is a separate step (`games/pattern-match/register.json`, then `scripts/register_game.py pattern-match`).
