# AI Mistakes

Seed: `planning/ai-mistakes-plan.md`. Personal project, no BCM tag, working title. Started 2026-10-13 with `scripts/new_game.py`.
Read the plan first: it holds the design every milestone follows. Then `BUILD-STATUS.md` here.

## One-line pitch
Source: the Quick ideas round (G7), owner-approved: "spot where a simple AI would go wrong in a series of small cases and say why." Checked against `PLAYER-PROFILE.md`: AI and coding named as new interests, finds broken-build cleverness satisfying, investigation and deduction feel, real-world issues shown with several points of view, "more game than teaching", hint ladder, no timers, nothing lost, dry dark humour, no harm on screen. Personal project, no BCM tag, working title. One-line pitch: a very small, very honest machine called Pip makes guesses; you check each one, decide whether it is a mistake, and say why, then change what it learned and watch it fix itself.

## Stack
- Pyodide Python, plain HTML/CSS, no build step. Engine modules are plain Python with no DOM (the Signal / Lexis
  pattern): `game.py` is the entry point (`handle(json) -> json`, plus `get_state()` / `load_state()` for the
  shared save widget); `app.js` is glue only.
- No audio files. Nothing timed, nothing lost, no luck needed for 100% (the site's standing rules).

## Milestones
| # | Milestone | Content | Status |
|---|-----------|---------|--------|
| 1 | Engine | Tiny models, case format, counterfactual and rubric proofs, chapter 1 (6 cases) with tests | Not started |
| 2 | Bench UI | Pip, training grid, verdict and kind pickers, Fix step, result card, save contract. Playable slice | Not started |
| 3 | Chapters 2-4, field guide, hints | 18 more cases, Field Guide, hint ladder, three-goals strip | Not started |
| 4 | Chapters 5-6 | 12 more cases (36 in all), all 12 failure kinds. First complete game | Not started |
| 5 | Standard kit | Opening screen, tutorial, settings, About with live-read sources, What's New, keyboard help, light theme, accessibility pass | Not started |
| 6 | Achievements | 14 achievements, panel and toast, manifest, reachability test | Not started |
| 7 | Desktop boot and wrap-up | `pc-config.json`, `pc.css`, `pc.js`, generated `pc.html`, docs, changelog | Not started |

## Working conventions
- Commit + tag per milestone: `git commit -m "Milestone N: <name>"` then `git tag ai-mistakes-milestone-0N`.
- Update the Status column as work happens, and `BUILD-STATUS.md` after every milestone.
- Hub registration is a separate step (`games/ai-mistakes/register.json`, then `scripts/register_game.py ai-mistakes`).
