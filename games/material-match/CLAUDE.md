# Material Match

Seed: `planning/material-match-plan.md`. Personal project, no BCM tag, working title. Started 2026-10-13 with `scripts/new_game.py`.
Read the plan first: it holds the design every milestone follows. Then `BUILD-STATUS.md` here.

## One-line pitch
Source: the Quick ideas round (G8), owner-approved: "pick materials for a tool or building from their real properties, with the numbers read from a named source." Checked against `PLAYER-PROFILE.md`: chemistry, physics and engineering interests, collecting every item (one of each material), a notebook that fills in, housing and healthcare named as caring topics, real-world games show several points of view, "fun that happens to be accurate", sources easy to find, hint ladder, no timers, nothing lost. Personal project, no BCM tag, working title. One-line pitch: a station workshop needs a hammer head, a window and a hull plate; the right material is on the shelf, and its numbers will tell you which.

## Stack
- Pyodide Python, plain HTML/CSS, no build step. Engine modules are plain Python with no DOM (the Signal / Lexis
  pattern): `game.py` is the entry point (`handle(json) -> json`, plus `get_state()` / `load_state()` for the
  shared save widget); `app.js` is glue only.
- No audio files. Nothing timed, nothing lost, no luck needed for 100% (the site's standing rules).

## Milestones
| # | Milestone | Content | Status |
|---|-----------|---------|--------|
| 1 | Engine | Materials table with sources, brief format, checker, margin solver, chapter 1 (8 briefs) with proofs | Not started |
| 2 | Shelf UI | Material cards, sort and filter, assign, verdict note, workshop floor, save contract. Playable slice | Not started |
| 3 | Chapters 2-4, book, hints | 24 more briefs, Materials Book, point-of-view notes, hint ladder, three-goals strip | Not started |
| 4 | Chapter 5 | 8 more briefs (40 in all), pick-two briefs. First complete game | Not started |
| 5 | Standard kit | Opening screen, tutorial, settings, About with live-read sources and value check, What's New, keyboard help, light theme, accessibility pass | Not started |
| 6 | Achievements | 14 achievements, panel and toast, manifest, reachability test | Not started |
| 7 | Desktop boot and wrap-up | `pc-config.json`, `pc.css`, `pc.js`, generated `pc.html`, docs, changelog | Not started |

## Working conventions
- Commit + tag per milestone: `git commit -m "Milestone N: <name>"` then `git tag material-match-milestone-0N`.
- Update the Status column as work happens, and `BUILD-STATUS.md` after every milestone.
- Hub registration is a separate step (`games/material-match/register.json`, then `scripts/register_game.py material-match`).
