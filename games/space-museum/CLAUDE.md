# Space Museum

Seed: `planning/space-museum-plan.md`. Personal project, no BCM tag, working title. Started 2026-10-13 with `scripts/new_game.py`.
Read the plan first: it holds the design every milestone follows. Then `BUILD-STATUS.md` here.

## One-line pitch
Source: the Quick ideas round (C4), owner-approved: "curate a museum of objects you have collected across the site, arranged in rooms." Checked against `PLAYER-PROFILE.md`: collects everything, a shelf or sticker book for collections, completion percentage bars, pictures and scenes over numbers, Unpacking-style calm placing (small, heavily changed), short wins that build a bigger picture, space and science fiction, dark moody, no timers, nothing lost. Personal project, no BCM tag, working title. One-line pitch: a quiet museum in a decommissioned orbital ring where every achievement you earn anywhere on the site becomes an object you can place, label and arrange in themed rooms.

## Stack
- Pyodide Python, plain HTML/CSS, no build step. Engine modules are plain Python with no DOM (the Signal / Lexis
  pattern): `game.py` is the entry point (`handle(json) -> json`, plus `get_state()` / `load_state()` for the
  shared save widget); `app.js` is glue only.
- No audio files. Nothing timed, nothing lost, no luck needed for 100% (the site's standing rules).

## Milestones
| # | Milestone | Content | Status |
|---|-----------|---------|--------|
| 1 | Engine | Catalogue builder, tags, brief checks, layout rules, solver proof that every brief is satisfiable from finds alone, 4 rooms | Not started |
| 2 | Room UI | SVG rooms, drag and keyboard placing, object cards, lamp, tray, save contract. Playable slice | Not started |
| 3 | All 12 rooms and finds | Remaining rooms, 36 arrangements, museum finds, labels, Floor Plan, three-goals strip, hint ladder | Not started |
| 4 | Site objects | Reader for other games' saves, donations shelf, new-arrivals tray, missing-object repair. First complete game | Not started |
| 5 | Standard kit | Opening screen, tutorial, settings, About, What's New, keyboard help, light theme, accessibility pass | Not started |
| 6 | Achievements | 14 achievements, panel and toast, manifest, reachability test | Not started |
| 7 | Desktop boot and wrap-up | `pc-config.json`, `pc.css`, `pc.js`, generated `pc.html`, docs, changelog | Not started |

## Working conventions
- Commit + tag per milestone: `git commit -m "Milestone N: <name>"` then `git tag space-museum-milestone-0N`.
- Update the Status column as work happens, and `BUILD-STATUS.md` after every milestone.
- Hub registration is a separate step (`games/space-museum/register.json`, then `scripts/register_game.py space-museum`).
