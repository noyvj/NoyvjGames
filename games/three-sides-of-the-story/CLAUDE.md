# Three Sides of the Story

Seed: `planning/three-sides-of-the-story-plan.md`. Personal project, no BCM tag, working title. Started 2026-10-13 with `scripts/new_game.py`.
Read the plan first: it holds the design every milestone follows. Then `BUILD-STATUS.md` here.

## One-line pitch
Source: the Quick ideas round (D4), owner-approved: "a branching story about a real issue (for example a water shortage), played once from each of three people's viewpoints." Checked against `PLAYER-PROFILE.md`: story only Lifeline-style with lots of branching, short missions that join into a story, real-world games show several points of view, caring topics (water, food, healthcare, housing), flawed people and no all-good hero, "fun that happens to be accurate", pictures over charts, free rewind, nothing lost. HARD BAN respected: this is not a visual novel (no portraits, no sprites, no dialogue-box scenes); it is a text-thread and radio-log format like Stranded and Lifeline. Personal project, no BCM tag, working title. One-line pitch: one dry week in a river town, lived three times, as the farmer, the water engineer and the clinic nurse, where each of them is partly right.

## Stack
- Pyodide Python, plain HTML/CSS, no build step. Engine modules are plain Python with no DOM (the Signal / Lexis
  pattern): `game.py` is the entry point (`handle(json) -> json`, plus `get_state()` / `load_state()` for the
  shared save widget); `app.js` is glue only.
- No audio files. Nothing timed, nothing lost, no luck needed for 100% (the site's standing rules).

## Milestones
| # | Milestone | Content | Status |
|---|-----------|---------|--------|
| 1 | Engine | Graph walker, stats, fixed events, ledger and reachability validators, Ilse's view (14 scenes) with tests | Not started |
| 2 | Thread UI | Message thread, choices, week map, rewind, reservoir gauge, save contract. Playable slice | Not started |
| 3 | Dev and Rosa | The other two views (28 scenes), fixed events told three ways, Compare panel, hint ladder, three-goals strip | Not started |
| 4 | Council | The Council meeting (8 scenes), 12 endings, notebook. First complete game | Not started |
| 5 | Standard kit | Opening screen, tutorial, settings, About with live-read sources and fiction notice, What's New, keyboard help, light theme, accessibility pass | Not started |
| 6 | Achievements | 14 achievements, panel and toast, manifest, reachability test | Not started |
| 7 | Desktop boot and wrap-up | `pc-config.json`, `pc.css`, `pc.js`, generated `pc.html`, docs, changelog | Not started |

## Working conventions
- Commit + tag per milestone: `git commit -m "Milestone N: <name>"` then `git tag three-sides-of-the-story-milestone-0N`.
- Update the Status column as work happens, and `BUILD-STATUS.md` after every milestone.
- Hub registration is a separate step (`games/three-sides-of-the-story/register.json`, then `scripts/register_game.py three-sides-of-the-story`).
