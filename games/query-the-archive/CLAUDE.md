# Query the Archive

Seed: `planning/query-the-archive-plan.md`. Personal project, no BCM tag, working title. Started 2026-10-13 with `scripts/new_game.py`.
Read the plan first: it holds the design every milestone follows. Then `BUILD-STATUS.md` here.

## One-line pitch
Source: the Quick ideas round (G2), owner-approved: "learn simple database queries by finding records in a space-station archive, no deletion allowed." Checked against `PLAYER-PROFILE.md`: coding and logic puzzles (yes), space stations and computers, a notebook that fills in, helper role, short wins, hint ladder, "more game than teaching", no timers, nothing lost. Personal project, no BCM tag, working title. One-line pitch: you are the new records clerk of Cinder Station; every request is a question for the Archive, and the answer is a query you write.

## Stack
- Pyodide Python, plain HTML/CSS, no build step. Engine modules are plain Python with no DOM (the Signal / Lexis
  pattern): `game.py` is the entry point (`handle(json) -> json`, plus `get_state()` / `load_state()` for the
  shared save widget); `app.js` is glue only.
- No audio files. Nothing timed, nothing lost, no luck needed for 100% (the site's standing rules).

## Milestones
| # | Milestone | Content | Status |
|---|-----------|---------|--------|
| 1 | Engine | Seeded archive and twin, read-only guard, checker, chapter 1 (6 slips) with near-miss and safety proofs | Not started |
| 2 | Clerk UI | Editor, clause chips, result table, slip stamp, save contract. Playable slice | Not started |
| 3 | Chapters 2-4, drawer, hints | 18 more slips, Clause Drawer, hint ladder, three-goals strip | Not started |
| 4 | Chapters 5-6 | 12 more slips (36 in all), grouping and joins. First complete game | Not started |
| 5 | Standard kit | Opening screen, tutorial, settings, About with live-read sources, What's New, keyboard help, light theme, accessibility pass | Not started |
| 6 | Achievements | 14 achievements, panel and toast, manifest, reachability test | Not started |
| 7 | Desktop boot and wrap-up | `pc-config.json`, `pc.css`, `pc.js`, generated `pc.html`, docs, changelog | Not started |

## Working conventions
- Commit + tag per milestone: `git commit -m "Milestone N: <name>"` then `git tag query-the-archive-milestone-0N`.
- Update the Status column as work happens, and `BUILD-STATUS.md` after every milestone.
- Hub registration is a separate step (`games/query-the-archive/register.json`, then `scripts/register_game.py query-the-archive`).
