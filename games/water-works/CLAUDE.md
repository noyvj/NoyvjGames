# Water Works

Seed: `planning/water-works-plan.md`. Personal project, no BCM tag, working title. Started 2026-10-13 with `scripts/new_game.py`.
Read the plan first: it holds the design every milestone follows. Then `BUILD-STATUS.md` here.

## One-line pitch
Source: the Quick ideas round (B4), owner-approved: "route clean water to villages with trade-offs between town, farm and wild land, shown from several people's points of view." Checked against `PLAYER-PROFILE.md`: water named as a caring topic, real-world games show several points of view, helper role, planning three steps ahead with no randomness, "fun that happens to be accurate", three goals, no timers, nothing lost. Personal project, no BCM tag, working title.

## Stack
- Pyodide Python, plain HTML/CSS, no build step. Engine modules are plain Python with no DOM (the Signal / Lexis
  pattern): `game.py` is the entry point (`handle(json) -> json`, plus `get_state()` / `load_state()` for the
  shared save widget); `app.js` is glue only.
- No audio files. Nothing timed, nothing lost, no luck needed for 100% (the site's standing rules).

## Milestones
| # | Milestone | Content | Status |
|---|-----------|---------|--------|
| 1 | Flow model and judges | Graph, flow rule, voices and verdicts, plan enumerator, chapter 1 (7 valleys) with proofs | Not started |
| 2 | Map UI | SVG map, buying links and parts, share dials, Voices panel with reasons, save contract. Playable slice | Not started |
| 3 | Chapters 2-3 | 15 more valleys, farm and wild voices, Valley Atlas | Not started |
| 4 | Chapters 4-5, hints, goals | 14 more valleys (36), downstream and dry years, Voices Book, hint ladder, three-goals strip, live facts. First complete game | Not started |
| 5 | Standard kit | Opening screen, tutorial, About with Sources, What's New, keyboard help, confirm dialogs, light theme, accessibility | Not started |
| 6 | Achievements | 14 achievements, panel and toast, manifest, reachability test | Not started |
| 7 | Desktop boot and wrap-up | `pc-config.json`, `pc.css`, `pc.js`, generated `pc.html`, docs, changelog | Not started |

## Working conventions
- Commit + tag per milestone: `git commit -m "Milestone N: <name>"` then `git tag water-works-milestone-0N`.
- Update the Status column as work happens, and `BUILD-STATUS.md` after every milestone.
- Hub registration is a separate step (`games/water-works/register.json`, then `scripts/register_game.py water-works`).
