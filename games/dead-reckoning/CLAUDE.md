# Dead Reckoning

Seed: `planning/dead-reckoning-plan.md` (Round 3, M5). Built 2026-10-08 by a background agent. Personal project, no BCM tag, working title. Fun first: it teaches nothing on purpose; the real navigation background is honest and modest.

## One-line pitch
You are a ship's navigator with only speed, heading and time. Plot a course across a chart with currents, wind and hazards, sail it, and see how far your estimate drifted from the truth.

## Stack
- Pyodide Python, plain HTML/CSS, no build step. `game.py` is the single engine entry point (`handle(json) -> json`, plus `get_state()` / `load_state()` for the shared save widget); `app.js` is glue only. The chart is an inline SVG string built in Python (`render.py`), so its markup is unit-tested.
- Runs from any static server (`python -m http.server`).
- No audio, ever. No timers gate play. The animation of a sail is cosmetic and skippable; the sim is instantaneous.

## Core constraints (do not violate without asking)
1. The sail is a pure function of `(chart, plan, seed)`. Positions are rounded to 0.01 nm in every recorded track.
2. The true position is never shown (nor stored in a view) before the reveal. In Watch-by-watch mode the engine re-derives the truth from the committed legs and only reports public events and fixes.
3. No colour-only encoding: hazards by shape, hatch and label; currents by arrow plus a numeric range; the estimated track is dashed and the true one solid.
4. Scores are always explained (nm error, safety, time), never a bare number.
5. Nothing violent or fatal: a grounding is "aground, the tide will lift you in a few hours".
6. Real-world facts on screen name their source or are left out. The game is an abstraction and its About panel says so.

## Rules as built (milestone 1)
- Chart plane in nautical miles; x east, y north; headings are degrees clockwise from north.
- A plan is a list of legs `{heading (whole degrees), speed (0.5 kn steps inside the chart's range), hours (0.5 h steps, up to 12)}`.
- Step = 0.25 h. Velocity over the ground = steered heading (+ compass error) at the leg's speed + leeway + current + (generated charts only) seeded gusts.
- Leeway = 5 percent of the wind's component across the ship, to leeward (a stated game constant, not a claim about real ships).
- A current zone is a rectangle with a charted set, a charted drift range, and the true set and drift (the true drift lies inside the charted range; the true set within 10 degrees of the charted one). Tidal zones multiply the drift by cos(2 pi (t - phase) / period) on the chart's clock.
- Three models of the sea: `true` (what happens), `charted` (midpoint of every printed range: the honest forecast) and `nominal` (heading, speed, time only).
- Hazards are circles; land is polygons. Segment tests catch a rock that one step would jump. Touching one ends the sail early (aground). Passing within 0.4 nm of an edge is a "close pass".
- Stars: 1 landfall (end within the arrival radius, not aground); 2 also on time (total plan hours within the deadline) and no close pass of a hazard the crew knew about; 3 also within half the arrival radius of the flag. The reveal card lists each reason, the naive plan's miss and "you beat the naive plan by N percent".

## Milestones
| # | Milestone | Content | Status |
|---|-----------|---------|--------|
| 1 | Sim core | `geom.py`, `sim.py`: vectors, current zones, leeway, hazard intersection, tracks, scoring, text harness (`tools/textharness.py`) | Done |
| 2 | Chart SVG | `render.py`: grid, land, hazards, current arrows, scale, rose, wind, landmarks, tracks, ribbons, the chart in words; `index.html` shell (standard shared includes), `style.css` (night and paper-chart themes), `settings.js`, favicon; page draws the demo chart with a hard-coded plan; golden SVG tests | Done |
| 3 | Plan and sail | `game.py` (handle/get_state/load_state), `state.py`, `progress.py`, `solver.py`; leg editor (numeric steppers, quick turns, Undo/Clear), live estimated track with an "allow for the chart" switch, naive and allow-for-the-chart helpers, ruler, Sail with confirm dialog, animated true track with scrub bar and Skip, reveal card with stars explained, save contract; mobile dock and HUD. **Playable slice** | Done |
| 4 | Campaign chapters 1-2 | 12 authored charts (6 open water, 6 wind), par plans generated into `pars.py` from each chart's `waypoints` (`tools/check_charts.py --write`), chart validator tests, chapter gates (four cleared opens the next), chart picker, Next chart, Show/Load the par plan after a first attempt, captain's log. **First complete, playable game** | Done |
| 5 | Fixes and watch-by-watch | `fixes.py` (bearing and distance off a landmark in sight, bounded repeatable errors of 2 degrees and 5 percent), Watch-by-watch mode (sail one leg, take a fix, plan the next; anchor to end early; grounding ends it), mode switch, chapter 3 (5 charts), validator test that a careful watch player lands | Done |
| 6 | Fog, tides, compass error | Chapters 4 (fog, 4 charts), 5 (tides, 4) and 6 (compass error, 4) = 29 charts in all; unmarked hazards are drawn only once found (a close pass or grounding) and remembered per chart; lie at anchor (speed 0) to wait for a fair stream; tidal timetable in the chart's words; the compass error shown on the chart and in the plot; validators for fog, tide and compass charts | Done |
| 7 | Two ships | DEFERRED (plan recommendation, FOR-YOU Dr2: later pass) | Deferred |
| 8 | Practice generator | `gen.py`: seeded chart generator in five difficulties (open water; a stream; wind and land; tides and compass; fog and everything), built by rejection and SOLVED on the way (visibility-graph route, shot leg by leg under the true sea, waiting for a fair tide), share codes `DR<level>-<base36 seed>`, practice charts counted in a visible total; solvability fuzz in `tests/test_gen.py` | Done |
| 9 | Standard kit | Settings panel (text size, reduce motion, effects, high contrast, theme), What's New (`changelog.json`), About page (`info.py`: six facts, each reworded with its source named and the date read, plus the abstraction disclaimer), guided tutorial, keyboard help, Copy result, confirm dialogs, mobile dock and HUD, story toggle, light (paper chart) and dark (night chart) themes with computed contrast checks, colourblind and non-colour-cue checks | Done |
| 10 | Achievements and own-folder wrap-up | 14 achievements (`achievements.py` + `achievements.json`, panel and toast, `achievements_earned` written to the save and never read back), favicon, Desktop boot (`pc-config.json`, `pc.css`, `pc.js`, generated `pc.html`), this file's tables, tag. The whole game can be 100%-ed with the par plans (tested) | Done |
| 11 | Daily Chart (optional, TODO M-5b-11) | One chart per UTC date, archive, tally grid; no leaderboard (hooks only) | Done (see "Daily Chart") |

## Working conventions
- Commit + tag per milestone: `git commit -m "Milestone N: <name>"` then `git tag dead-reckoning-milestone-0N`.
- Hub registration (title card, `sw.js`, manifests, root CLAUDE.md row, dev logs) is a separate later milestone owned by the hub session (TODO M-5b-12). Nothing outside this folder is touched here.

## Chart schema and authoring (milestone 4)
- A chart is a dict built with `chartkit.chart(...)`: `id, name, chapter, size (nm), start, dest, arrival_radius, deadline, speeds, start_hour, land, hazards, currents, wind?, compass?, landmarks, fog?, waypoints, naive_fails, intro, log{arrived,missed,aground,late}`. Charted values (`set`, `drift_range`, wind `range`) sit beside the true ones (`true_set`, `true_drift`, wind `true`).
- To add a chart: write it in `charts_<chapter>.py`, register the chapter in `charts.py`, run `python3 tools/check_charts.py --write` (prints naive miss, par and forecast results; rewrites `pars.py`), then `pytest`. `tests/test_charts.py` is the validator: ids unique, nothing overlaps the start or the flag, charted ranges contain the truth (drift range at most 1 kn wide, true set within 10 degrees), the par plan makes 3 stars cleanly with slack on the deadline, the printed midpoints followed carefully still make landfall (ranges are never a trap), and the naive plan fails exactly where `naive_fails` says.
- Chapters open when four charts of the one before have a star or more (derived from the records, nothing stored). The shared `level-select.js` is not used; the game has its own picker (a deliberate deviation, see BUILD-STATUS).

## Watch-by-watch (milestone 5)
- `run.mode` is `plan` (commit the whole course) or `watch`; a chart lists `modes` and a `default_mode` (chapter 3 opens in `watch`). `run.sailed` is the number of committed legs; at most one pending leg is edited at a time. `run.fixes` holds `{after_leg, x, y, landmark}`: the plot jumps there after that leg.
- After a watch the engine recomputes the true position from the committed legs (never stored, never shown) and only reports: public events (a close pass, grounding), and a reading per landmark within its `visible` range (none in fog). A reading is a bearing (whole degrees) and a distance (0.1 nm) with errors of up to 2 degrees and 5 percent, repeatable (hash of chart, landmark and watch). Taking a fix moves the plot to the landmark minus the distance along the bearing: close to the truth, never exactly it.
- Soundings (the plan's second fix kind) are not built: landmarks only.

## Fog, tides, compass error (milestone 6)
- Chapter ids are `open, wind, fixes, fog, tides, compass`. The plan's chapter 6 (Two ships) is deferred, so compass error is chapter 6 here and the plan's chapter 7.
- Fog: `fog: True` hides every landmark and stops fixes; hazards with `charted: False` never appear on the chart, in the notes or on the reveal until the ship has found one (close pass or grounding), then `discovered` in that chart's record keeps it drawn ("(found)"). A close pass of an unfound hazard costs no star. The par plan never touches or brushes any hazard, marked or not.
- Tides: a current zone with `tide: {period: 12, phase}` runs `drift * cos(2 pi (t - phase) / period)` on the chart's clock (start at `start_hour`). The chart's notes give the timetable. A leg at speed 0 lies at anchor (no leeway, no current: the ship holds her place); `par_wait` is the anchored hours the authored plan waits first. `fair_ok: False` marks a crossing-stream chart where Riding the Tide is not the point.
- Compass: `compass: {range, true}` is added to every steered heading; the chart prints the range in the picture and in words; the plot includes the midpoint when "allow for the chart" is on.

## Practice generator (milestone 8)
- A practice chart is a pure function of `(difficulty 1-5, seed < 36^6)`; its id is `practice-<d>-<seed in base 36>` and its share code `DR<d>-<SEED>`. `charts.get_chart` makes one on demand, so a saved run (or a pasted code) rebuilds the same sea. `gen.make_chart` returns None only if no solvable chart came out of 14 attempts; the caller then tries the next seed.
- Acceptance (the same rules as the campaign): the generator's own par plan lands cleanly (not aground, not even a close pass), on time and with the deadline set from it; the printed midpoints followed carefully also make landfall. Gusts (a small repeatable wobble) exist on generated charts only.
- Practice never touches the campaign records. Each practice chart sailed counts once toward the visible "Practice charts sailed" total (`meta.practice_seeds_played`, which Practice Makes uses); finishing one also feeds the smallest-final-error and longest-route bests. Found unmarked hazards are kept in the run (`run.found`), and the par plan can be shown after a first attempt.
- Fuzz: `DR_FUZZ=<n> python3 -m pytest games/dead-reckoning/tests/test_gen.py` sets the charts per difficulty (default 30; measured 0 failures in 300 per difficulty; the plan's 5,000 would take the better part of an hour on this machine).

## Standard kit (milestone 9)
- Display settings live in `settings.js` (per device, never in the save). The page follows the system's reduced-motion and theme choices until the player picks.
- The About page facts (`info.py`) were each read live on 2026-10-09 from the page named (Wikipedia: Dead reckoning, Nautical mile, Chip log, Leeway, Magnetic declination, Marine chronometer) and reworded. The figures kept are the 1,852 metre nautical mile and the 1929 conference; the game says plainly it is an abstraction. No celestial navigation is simulated (FOR-YOU Dr3).
- Accessibility checks are in `tests/test_accessibility.py`: AA contrast for every text pair and 3:1 for lines in both themes, dash and hatch cues, labels, live regions, the chart's text twin, and the standard shared includes.
- Site feedback and rating live on the hub; the game page has no feedback form of its own.

## Achievements (milestone 10)
- 14, computed from the saved record (flags in `meta.flags`, per-chart stars, the practice total), never stored separately. The plan's "Two at Once" (a two-ship chart) waits for the deferred Two ships milestone, so **Patient Navigator** (lie at anchor for the tide, then make landfall) takes its place. `tests/test_achievements.py` plays every par plan, takes a fix, runs aground once and sails ten practice charts, and checks all 14 end up earned: easy to 100%.
- "Trust the Numbers" needs three stars with no helper (naive, allow-for-the-chart or the par plan) used in that run.

## Daily Chart
- `daily.py` makes one chart per UTC date from the date text alone (FNV hashes pick a level 1-5 and a start seed; no clock, no random source, no server). The chart IS a practice-generator chart (`gen.make_chart`, already solver-proven: its par route lands cleanly, on time, the printed midpoints make landfall), re-labelled `daily-YYYY-MM-DD` ("Daily Chart N"). **The daily bar on top:** the par plan must score three stars with no helper (`daily._accept`); a seed that fails is skipped for the next seed from the same date (the shipped generator has needed zero skips in 300 dates). `charts.get_chart` rebuilds a daily from its id, so a saved run (or an archive date) always gets the same sea.
- A daily is scoped like a practice chart (`game._scoped`): unmarked hazards found live in the run, the campaign records and the practice total never change, but it also does NOT count toward "Practice charts sailed". Its own record per date lives in `meta.daily_days` ({date: {stars, best_error_nm, tries}}, best of each; written only when non-empty; validated entry by entry; merged per date by `daily.better`). The usual achievement flags (landfall, dead on, ...) still come from `progress.record_outcome` as for practice.
- The view passes "today" in every request (`DeadReckoningDaily.today()` in `daily.js`, the only clock read, added by `app.js` to each request); the engine keeps it only as a runtime value (`game.today`). Without a date there is no daily panel. A saved daily run for a date that is not open yet is dropped. `start_daily {date}` accepts any real date from 2026-10-01 to today; `reset` ("forget all progress") also clears the daily record.
- UI: a "Daily chart" toolbar button and panel (`#daily-panel`; a window with a calendar icon in the Desktop boot): Today's chart, a month-calendar archive (stars as symbols), a plain sentence tally ("Played N of M open days") and a small grid of the last 120 days. No streak counter anywhere. A line under the chart title says it is a daily and that nothing else changes.
- **Leaderboard: NOT built.** Hooks only: `daily.leaderboard_entry(date, record)` (view `daily.entry` on the reveal) and `DeadReckoningDaily.leaderboardHook` in `daily.js`. A future board takes `{board: "dead-reckoning-daily-chart", date, stars, error_nm}`.
- `sw.js` / `offline-manifest.json` (hub files, not edited here) must precache `games/dead-reckoning/daily.py` and `daily.js`.
- Tests: `tests/test_daily.py` (determinism, 300 consecutive dates solved by their par plan with three stars, midpoint landfall on 60, flow, saves, tampering, merge), `tests/test_daily_browser.py` (calendar to result on both pages; the Desktop page at desktop width only, that layout is not for phones).

## Desktop boot
- `pc.html` is generated: `python3 games/dead-reckoning/tools/build_pc.py` (this game only; the shared all-games generator is not run from here). The chart is the stage; the plan or the passage is the side column; Charts, Achievements, Captain's log, What's New, Settings and About are windows; three icons (Charts, Achievements, Settings) and the Menu hold the toolbar. `pc.js` is the Desktop tutorial. Same engine, same save.

## Not built / deferred
- Milestone 7 Two ships. Depth soundings (landmark fixes only). A drag dial for headings (numeric steppers and quick turns only). Celestial navigation (never planned, FOR-YOU Dr3).
- Hub registration (M-5b-12) is deliberately not done: title card, `sw.js`, `offline-manifest.json`, `game-*.json`, share cards, root CLAUDE.md row, dev logs, the generated meta and JSON-LD blocks in `index.html`, `scripts/perf-budget.json`, `shared/site-settings.js` and the hub smoke tests.
