# Loadout Lab

Seed: `planning/loadout-lab-plan.md`. Personal project, no BCM tag, working title. Started 2026-10-13 with `scripts/new_game.py`.
Read the plan first: it holds the design every milestone follows. Then `BUILD-STATUS.md` here.

## One-line pitch
Source: the Quick ideas round (C2), owner-approved: "combine parts to reach target numbers, with a catalogue of every combination you have found, including the one overpowered build per challenge." Checked against `PLAYER-PROFILE.md`: finding the one broken build feels clever, collecting every combination, optimising that is easy to get working and deeper with real depth (not spreadsheet level), robots and science fiction, planning with no randomness, three goals, no timers, nothing lost. No roguelike or deck mechanics: parts are fixed and always available. Personal project, no BCM tag, working title.

## Stack
- Pyodide Python, plain HTML/CSS, no build step. Engine modules are plain Python with no DOM (the Signal / Lexis
  pattern): `game.py` is the entry point (`handle(json) -> json`, plus `get_state()` / `load_state()` for the
  shared save widget); `app.js` is glue only.
- No audio files. Nothing timed, nothing lost, no luck needed for 100% (the site's standing rules).

## Milestones
| # | Milestone | Content | Status |
|---|-----------|---------|--------|
| 1 | Stat engine and enumerator | Parts, synergy rules, evaluator, full-build enumerator, chapter 1 (8 challenges) with proofs | Not started |
| 2 | Workshop UI | Slots and part tiles, live stat panel with Why lines, Run, save contract. Playable slice | Not started |
| 3 | Chapters 2-3 | 16 more challenges, bounds and pair bonuses, Build Book | Not started |
| 4 | Chapters 4-5, hints, goals | 16 more challenges (40), conversions, Broken stamps, hint ladder including the Broken clue, three-goals strip. First complete game | Not started |
| 5 | Standard kit | Opening screen, tutorial, About with Sources, What's New, keyboard help, confirm dialogs, light theme, accessibility | Not started |
| 6 | Achievements | 14 achievements, panel and toast, manifest, reachability test | Not started |
| 7 | Desktop boot and wrap-up | `pc-config.json`, `pc.css`, `pc.js`, generated `pc.html`, docs, changelog | Not started |

## Working conventions
- Commit + tag per milestone: `git commit -m "Milestone N: <name>"` then `git tag loadout-lab-milestone-0N`.
- Update the Status column as work happens, and `BUILD-STATUS.md` after every milestone.
- Hub registration is a separate step (`games/loadout-lab/register.json`, then `scripts/register_game.py loadout-lab`).
