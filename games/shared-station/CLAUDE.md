# Shared Station

Seed: `planning/shared-station-plan.md`. Personal project, no BCM tag, working title. Started 2026-10-13 with `scripts/new_game.py`.
Read the plan first: it holds the design every milestone follows. Then `BUILD-STATUS.md` here.

## One-line pitch
Source: the Quick ideas round (E2), owner-approved: "friends' finished puzzles light up rooms in a shared space station you can visit." Checked against `PLAYER-PROFILE.md`: space stations over forests, collecting and completionist, a bigger picture that grows, optional friend ties, friends leaving gifts or short notes with no chat, no mandatory leaderboard, "hide my score" style privacy, nothing lost, no timers. Personal project, no BCM tag, working title. One-line pitch: a dark orbital station whose rooms light up as you finish things in the other games, with a visitor mode that lets a friend walk through yours from a link.

## Stack
- Pyodide Python, plain HTML/CSS, no build step. Engine modules are plain Python with no DOM (the Signal / Lexis
  pattern): `game.py` is the entry point (`handle(json) -> json`, plus `get_state()` / `load_state()` for the
  shared save widget); `app.js` is glue only.
- No audio files. Nothing timed, nothing lost, no luck needed for 100% (the site's standing rules).

## Milestones
| # | Milestone | Content | Status |
|---|-----------|---------|--------|
| 1 | Engine | Deed table, reader, lit-set rules, validation against the repo, ring layout with tests | Not started |
| 2 | Station UI | SVG station, camera moves between rooms, plaques, save contract. Playable slice | Not started |
| 3 | All 60 rooms | Full deed table and plaques, Next lights, percentage bar, hint ladder, three-goals strip. First complete game | Not started |
| 4 | Visitor mode | Station Card codec, sample crews, waves and guest shelf | Not started |
| 5 | Standard kit | Opening screen, tutorial, settings, About with the privacy note, What's New, keyboard help, light theme, accessibility pass | Not started |
| 6 | Achievements | 14 achievements, panel and toast, manifest, reachability test | Not started |
| 7 | Desktop boot and wrap-up | `pc-config.json`, `pc.css`, `pc.js`, generated `pc.html`, docs, changelog | Not started |

## Working conventions
- Commit + tag per milestone: `git commit -m "Milestone N: <name>"` then `git tag shared-station-milestone-0N`.
- Update the Status column as work happens, and `BUILD-STATUS.md` after every milestone.
- Hub registration is a separate step (`games/shared-station/register.json`, then `scripts/register_game.py shared-station`).
