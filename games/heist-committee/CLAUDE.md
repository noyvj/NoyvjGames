# Heist Committee (working title)

Plan: `planning/heist-committee-plan.md`. TODO items M-1b-1 to M-1b-9. Personal project, no BCM tag. Fun first, funny, no lesson. Cozy caper tone (plan question He1 recommendation), invented crew names, Daily Job later (He2 recommendation).

## One-line pitch
Pick a target, hire five oddball specialists who do not get along, drag their actions into a timeline, then watch the job play out beat by beat while complications and personality clashes chain into each other.

## Stack
Python via Pyodide, plain HTML/CSS, no build step. `engine.py` is the heist resolver (pure function of content, crew, plan, gear and seed). Content is data in `content/*.json`, loaded by `content.py` (which also validates it). `app.js` is glue only.

## Core constraints
1. The heist is a pure function of (content, target, crew, plan, gear, seed). Same inputs, same event log, byte for byte. Every die is `roll(seed, label...)`, so editing one cell never reshuffles another.
2. No hue-only encoding: roles by shape + letter + word, outcomes by icon + word, odds as words (Solid / Risky / Long shot / No chance).
3. No timers anywhere. Planning time is unlimited; playback is a Next button (auto-advance is optional).
4. Chains are capped at 6 links a beat and every complication fires at most once a heist.
5. Fiction only: invented targets and people, nothing violent, no real brands.
6. Undo and re-plan freely before Start Heist; playback is fixed afterwards.

## Milestones
| # | Milestone | Status |
|---|-----------|--------|
| 1 | Engine core | Done |
| 2 | Plan UI | Done |
| 3 | Playback + payout | Done |
| 4 | Launch content | Done |
| 5 | Career and meta | Done |
| 6 | Standard kit | Done |
| 7 | Achievements + story | Done |
| 8 | Balance and bots | Done |
| 9 | Own-folder wrap-up | Done |
| 10 | Daily Job (optional, TODO M-1b-10) | Done, without a leaderboard (see "Daily Job") |

## How the pieces fit
- `content/*.json` is all the rules as data (5 targets, 20 crew, 20 traits, 12 actions, 56 complications, 7 gear). `content.py` loads it and `validate()` checks it (every complication has a counter and can fire, every emitted tag is read, windows are in range). A new complication is a JSON entry, no code.
- `engine.py` resolves a heist: `simulate(...)` is pure, `preview(...)` gives the odds shown in the plan, `Sim` is the beat-by-beat resolver. `plancheck.py` writes the live checklist, `planops.py` edits the plan, `writeup.py` writes the payout text, `story.py` the banter and minutes, `achievements.py` the 14 achievements, `info.py` the How it works panel.
- `game.py` is the single entry point (`handle(json)`, `get_state`/`load_state`). The career (cash, reputation, relationships, flags, the current job) is saved; a heist is never saved, only the plan and seed, so mid-playback resume replays it exactly.
- `bots.py` and `harness.py` are tools: greedy and dice planners for the balance tests, and a text-only log printer (`python3 harness.py [target] [seed]`).
- `app.js` (board, case file, hiring, shared kit), `plan.js` (timeline, tray, inspector), `play.js` (playback, payout) are glue.
- Tests that drive the page use `index.html#play` to skip the shared opening screen.

## Decisions taken
- Cozy caper tone, invented names, Daily Job later (user answered He1-He3 yes, 2026-10-09). The player profile (private planning) shaped: no hard-lose state, retry pays only the improvement (no grinding), no timers, optional auto-advance only.
- Retrying a job keeps the seed: the same trouble arrives on the same beats, so an improved plan is really improved.
- Quirks are hidden until they fire in a heist or are paid for (background check); odds in the plan exclude hidden quirks.
- Reputation only rises when a job goes better than before, and unlocks jobs, crew and gear (derived, not stored).

## Daily Job
`daily.py` (pure, imports only `bots` and `engine`) makes one job per UTC date from the date text alone (`engine.roll` hashing, no clock, no random source, no server): the target, the night's seed, today's eight candidates (all five roles, the whole roster, career unlocks ignored) and a three-piece van. **Fairness bar:** before a date is accepted, `bots.greedy_plan` (told the three scouted kinds) must take at least 3 different five-crew combinations of the offer through that exact night with an escape and no alarm; a candidate that fails is replaced by the next one derived from the same date (about 1 in 150 dates needs a second try). `par` is the lowest payout among those witnesses; tiers are busted / escaped (alarm) / clean / par.
- The daily is a standalone night: crew, van and scouting are free, every quirk is on the file, no cash, reputation, friendships, `meta` or achievements change. `Career.job` is a property that returns the open daily job (`career.daily_job`) first, so every existing helper works on it; a daily can only be opened from the board (a career job is never put aside), and `new_career` keeps the date history.
- The view passes "today" in every request (`HC.send` adds it; tests pass dates explicitly); the engine stores it only as a runtime value (`game._today`). No date means no daily on the board. A save naming a date that is not open yet is dropped.
- Save keys, written only when non-default: `daily_days` ({date: {tier, net, tries}}, best tier and best payout, validated entry by entry) and `daily_job` (an unfinished daily night, rebuilt from its date on load: target, seed and offer come from `daily.spec`, never from the save). Old saves load unchanged.
- UI: a panel at the top of the contract board (`#daily-panel`, `daily.js`): Today's job, a month-calendar archive (any date from 2026-10-01 up to today is playable, skipped days cost nothing), a plain-language tally and a small grid of the last 120 days. No streak counter anywhere. Marks are symbols as well as shading.
- **Leaderboard: NOT built.** Hooks only: `daily.leaderboard_entry(date, record)` (pure; `view.daily.leaderboard`) and `HC.dailyLeaderboardHook` in `daily.js`, called with that entry on a daily payout when something defines it. A future backend board takes `{board: "heist-daily-job", date, score, tier}`.
- `sw.js` / `offline-manifest.json` (hub files, not edited here) must precache `games/heist-committee/daily.py`, `daily.js`; the page also loads `bots.py` now.
- Tests: `tests/test_daily.py` (determinism, 300 consecutive dates fairness-proven by replay, an exhaustive cross-check, save round trips and tampering), `tests/test_daily_browser.py` (calendar to payout on both pages at both widths).

## Desktop boot
`pc-config.json` + `pc.css` + `pc.js`; `pc.html` is generated (`scripts/generate-pc-pages.py`, never edit by hand). The whole job lives in the stage (board, case file, hiring, plan, playback, payout). Plan: timeline on top, inspector and tray under it, checklist and scouting column on the right with Undo/Redo/Clear/Start Heist adopted to the top of that column. Cash, reputation and stage are readout chips. Minutes, Achievements, What's New, Settings and How it works are windows. Escape puts a held action down first (a capture listener in plan.js), then opens the shell Menu. Known limit: at 1024 wide the stage scrolls inside itself.

## Not in this folder (blocked on the session that owns the hub files, TODO M-1b-11)
Hub registration: title card and thumbnail, `sw.js` precache (including `pc.*`), manifests, `game-*.json`, achievements page, admin, share cards, the root CLAUDE.md row, dev logs.

## Working conventions
Commit and tag each milestone (`heist-committee-milestone-0N`). Hub registration is NOT part of this folder's milestones (TODO M-1b-11, blocked on the session that owns the hub files).
