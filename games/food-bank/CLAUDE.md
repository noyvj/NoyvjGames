# Food Bank

Seed: `planning/food-bank-plan.md`. Personal project, no BCM tag, working title. Started 2026-10-13 with `scripts/new_game.py`.
Read the plan first: it holds the design every milestone follows. Then `BUILD-STATUS.md` here.

## One-line pitch
Source: the Quick ideas round (B7), owner-approved: "plan a week of meals and deliveries for a food bank with a limited budget and several families' needs." Checked against `PLAYER-PROFILE.md`: food named as a caring topic, helper role, planning with no randomness, real-world games show several points of view, "fun that happens to be accurate", three goals, no timers or pressure, nothing lost. Personal project, no BCM tag, working title.

## Stack
- Pyodide Python, plain HTML/CSS, no build step. Engine modules are plain Python with no DOM (the Signal / Lexis
  pattern): `game.py` is the entry point (`handle(json) -> json`, plus `get_state()` / `load_state()` for the
  shared save widget); `app.js` is glue only.
- No audio files. Nothing timed, nothing lost, no luck needed for 100% (the site's standing rules).

## Milestones
| # | Milestone | Content | Status |
|---|-----------|---------|--------|
| 1 | Rules and planner | Items, needs, spoilage, packing and delivery rules, plan search, season 1 (6 weeks) with proofs | Not started |
| 2 | Pantry UI | Day view, shelf and box panels, family cards, delivery planner, reset to any day, save contract. Playable slice | Not started |
| 3 | Seasons 2-4 | 18 more weeks, new needs, Pantry Wall and Neighbours book | Not started |
| 4 | Seasons 5-6, hints, goals | 12 more weeks (36), summer gap and big week, hint ladder, three-goals strip, live facts. First complete game | Not started |
| 5 | Standard kit | Opening screen, tutorial, About with Sources, What's New, keyboard help, confirm dialogs, light theme, accessibility | Not started |
| 6 | Achievements | 14 achievements, panel and toast, manifest, reachability test | Not started |
| 7 | Desktop boot and wrap-up | `pc-config.json`, `pc.css`, `pc.js`, generated `pc.html`, docs, changelog | Not started |

## Working conventions
- Commit + tag per milestone: `git commit -m "Milestone N: <name>"` then `git tag food-bank-milestone-0N`.
- Update the Status column as work happens, and `BUILD-STATUS.md` after every milestone.
- Hub registration is a separate step (`games/food-bank/register.json`, then `scripts/register_game.py food-bank`).
