# Anomaly Catalogue

Seed: `planning/anomaly-catalogue-plan.md`. Personal project, no BCM tag, working title. Started 2026-10-13 with `scripts/new_game.py`.
Read the plan first: it holds the design every milestone follows. Then `BUILD-STATUS.md` here.

## One-line pitch
Source: the Quick ideas round (C1), owner-approved: "a fixed set of odd rooms or screens where you spot what changed and file it in a field catalogue (the kind of anomaly games you like to watch)." Checked against `PLAYER-PROFILE.md`: horror and anomaly games, collecting one of each, a notebook being filled in, investigation that gets easier with learning, dark moody look, calm, no timers, nothing lost, no jump scares or on-screen death. Personal project, no BCM tag, working title. Different from Evidence Hunt (deduce a spirit from readings): this is visual comparison and filing.

## Stack
- Pyodide Python, plain HTML/CSS, no build step. Engine modules are plain Python with no DOM (the Signal / Lexis
  pattern): `game.py` is the entry point (`handle(json) -> json`, plus `get_state()` / `load_state()` for the
  shared save widget); `app.js` is glue only.
- No audio files. Nothing timed, nothing lost, no luck needed for 100% (the site's standing rules).

## Milestones
| # | Milestone | Content | Status |
|---|-----------|---------|--------|
| 1 | Scene engine and checks | Scene data model, diff comparer, anomaly kinds, geometry lints, floor 1 (4 rooms) with proofs | Not started |
| 2 | Room UI | SVG scene view, Compare toggle, Look closer, filing dialog, save contract. Playable slice | Not started |
| 3 | Floors 2-4 | 12 more rooms, more kinds, Field Catalogue binder | Not started |
| 4 | Floors 5-6, hints, goals | 8 more rooms (24), cross-references, hint ladder, three-goals strip. First complete game | Not started |
| 5 | Standard kit | Opening screen, tutorial, About with Sources, What's New, keyboard help, confirm dialogs, light theme, accessibility | Not started |
| 6 | Achievements | 14 achievements, panel and toast, manifest, reachability test | Not started |
| 7 | Desktop boot and wrap-up | `pc-config.json`, `pc.css`, `pc.js`, generated `pc.html`, docs, changelog | Not started |

## Working conventions
- Commit + tag per milestone: `git commit -m "Milestone N: <name>"` then `git tag anomaly-catalogue-milestone-0N`.
- Update the Status column as work happens, and `BUILD-STATUS.md` after every milestone.
- Hub registration is a separate step (`games/anomaly-catalogue/register.json`, then `scripts/register_game.py anomaly-catalogue`).
