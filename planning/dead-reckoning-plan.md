# Dead Reckoning — Groundwork Plan (Round 3 M5)

Status: PLAN ONLY. No `games/dead-reckoning/` folder exists yet. Once approved, this becomes the seed for `games/dead-reckoning/CLAUDE.md` (per `game-template.md`).
User answer (Round 3, M item 5): "yes". Taste rule (standing): fun first. It teaches nothing on purpose, but the real navigation background is honest and adds texture (section 3). No BCM tag (personal project). Working title only.

**Shared baseline:** `overclock-plan.md` section 4 (save, settings, achievements, changelog, tutorial, confirm dialog, mobile dock/HUD, colorblind rules, test harness, feedback) and section 5 (hub integration) apply with slug `dead-reckoning`. Section 12 lists only what differs.

## 1. One-line pitch
You are a ship's navigator with only speed, heading and time. Plot a course across a chart with currents, wind and hazards, sail it, and see how far your estimate drifted from the truth.

## 2. Concept
The game is a precision puzzle with an honest sense of mastery. You never see where the ship really is while it sails. You see the chart, the destination, the charted hazards, and what the chart tells you about the water (arrows with rough numbers). You plan a route as legs (heading, speed, hours), the sim computes what the sea actually does to you, and the reveal draws your **estimated track** (what you believed) over the **true track** (what happened), with the error growing along the way. The satisfaction is getting better at reading the sea: compensating for a current you have only rough numbers for, choosing where to take a fix, deciding whether to go around a shoal or trust your numbers.

Two ways to play (chosen per chart):
- **Full plan:** commit the whole course up front, then sail it. The hardest, cleanest puzzle: you are scored on the finished result.
- **Watch by watch:** sail one leg, receive whatever information the chart gives you (a landmark bearing, a depth sounding, or nothing in fog), then plan the next leg. Corrects drift, like a real watch officer.

## 3. Real navigation background (grounded, modest)
These are the real ideas the game borrows. They are stated modestly; no figures beyond definitions. Any of these shown to the player on screen names its source, per the site's sourced-real-world-examples convention (as in Canopy and Drift), and is otherwise omitted. Sources are to be chosen and verified at build time (a hydrographic office, a maritime museum or a standard navigation text); do not invent citations.
- **Dead reckoning** means estimating your present position from a known earlier position, your course, your speed and the time elapsed. It needs no outside reference, and its errors accumulate the longer you go without a fix.
- **Fixes** correct dead reckoning: sighting a known landmark, taking a bearing, a depth sounding matched to the chart, a celestial observation, or (today) satellite positioning. In this game a fix is a landmark bearing or a sounding, never a magic "reveal".
- **Speed and distance:** a knot is one nautical mile per hour, and the international nautical mile is defined as 1852 metres. Historically speed was estimated with a knotted line and a sandglass (the chip log), which is where "knots" comes from.
- **Current:** navigators describe a current by its **set** (the direction it flows toward) and **drift** (its speed). An unnoticed current moves the ship sideways and forward relative to where the compass and log say it is.
- **Leeway:** wind pushes a sailing vessel sideways, so the actual track is a little to leeward of the heading steered.
- **Compass error:** a compass does not point at true north everywhere (magnetic variation), and a ship's own iron can shift it (deviation). Later charts include a small compass error.
- **Tides and tidal streams** alter currents over hours in coastal water, which is why tide tables matter near shore.
- **Longitude at sea** was long hard because it depends on knowing the time accurately; the marine chronometer was the practical solution. (Modest flavor; the game does not simulate celestial navigation at launch.)
- **Traditional tools** were dividers, parallel rulers and a plotting chart. The game's on-screen helpers (a ruler that reports bearing and distance between two chart points, a compass rose, a protractor arc) are modelled on these.
The game is an abstraction, not a simulator: it will not claim real-world accuracy of its numbers, and the info panel says so plainly.

## 4. Stack
- Default: Python via Pyodide, plain HTML/CSS, no build step, run via `python -m http.server`.
- Simulation in pure Python: deterministic vector math on a fixed step. The core is small (under about 400 lines), so Pyodide's load cost is acceptable; the game is not a "quick daily", so it does not need Signal's lazy-engine trick.
- Chart rendering: inline **SVG** (grid, coastline paths, hazard shapes, current arrows, tracks). No canvas, no libraries. SVG gives free scaling to 375px, crisp lines, text scaling and simple testing of generated markup.
- **Honest limits:** no audio (the game is quiet by design); no real-time precision anywhere (the sailing playback is an animation of a precomputed track, paced by CSS/`requestAnimationFrame` cosmetically, with a "Skip to result" button; the sim itself is instantaneous).
- Input is numeric first (type or step a heading and speed, choose hours) with an optional drag dial. Numeric entry is the accessible path and the primary one.

## 5. Core constraints (do not violate without asking)
1. The sail is a **pure function of (chart, plan, seed)**. Same inputs give an identical true track. All randomness (gusts on generated charts) is seeded.
2. **The true position is never shown before the reveal.** Not by accident, not in the debug view of a shipped build.
3. **No colour-only encoding.** Hazards by shape and label, currents by arrow with a numeric range, land/water by pattern; colour is decoration.
4. Scores are always explained (error in nautical miles, route safety, time), never a bare number.
5. Nothing violent or fatal is depicted; a grounded ship is "aground: the tide will lift you in a few hours" with a score penalty and a retry, not a disaster.
6. No timers gate play; no real-time clock.

## 6. Game design

### 6.1 The chart
- Units: nautical miles on a square grid (starting 20 x 20 nm, larger later). Origin and destination marked. Scale bar and compass rose always visible.
- Layers: coastline/land polygons, **hazards** (reefs, shoals, rocks as labelled shapes with a "charted" flag; some are **uncharted** and appear only after you hit or graze them, on the harder charts), **current fields** (a set of zones, each with an arrow showing the charted set and a range like "1 to 2 kn"; the true value lies in the range), **wind** (a compass arrow with strength band), **landmarks** (lighthouses, headlands, buoys usable for fixes).
- The chart tells the truth only roughly. That is the point.

### 6.2 The plan
A plan is a list of **legs**: `{heading_deg, speed_kn, hours}`. Constraints: hours are in 0.5 steps; the ship has a speed range; a total-time limit per chart (the "deadline", also expressed in hours, not real time). The planner shows the **estimated track** as you edit (dead reckoning proper: heading, speed and time only), the total distance, and an "ETA".
- Helpers (unlimited): ruler (bearing and distance between two chart points), a "steer to point" button that fills in heading and hours to a chosen point *ignoring* current (a naive estimate the player should learn to improve on), and an "apply current triangle" helper at higher levels that suggests a steer-into-current heading using the *charted* midpoint (so it is a starting guess, not the answer).
- In Watch-by-watch mode, a plan is one leg at a time with fixes in between.

### 6.3 The sim
```
sail(chart, plan, seed) -> {true_track: [(t, x, y)], estimated_track: [...], events: [...], result: {...}}
step (dt = 0.25 h):
  v_water = speed * unit(heading + compass_error)          # through the water
  v_leeway = wind_strength_factor * unit(wind_dir_perp)    # sideways push, small
  v_current = current_at(x, y, t) (set, drift) + seeded gust noise (generated charts only)
  pos += (v_water + v_leeway + v_current) * dt
  check hazards along the segment (segment-vs-shape intersection); grounding ends the sail early
  estimated pos += v_water_nominal * dt                   # what the player believed
```
- Deterministic floats rounded to 0.01 nm for stable tests. Segment-vs-circle/polygon hazard tests keep hazards from being skipped over by a large step.
- Fixes in Watch-by-watch mode: after a leg, if a landmark is in range and visibility allows, the player gets a bearing to it (with a small stated error) and can **correct** their estimated position; the game shows the corrected error, not the true position.
- Tides (later charts): current strength is a sine of time with a period given on the chart's tide table; the player must plan legs to catch the fair stream.
- Fog (later charts): fixes are unavailable and hazards are drawn only after a grounding or near-miss event ("something hissed past to starboard").

### 6.4 The reveal and scoring
After sailing, the estimated track and the true track are overlaid; an **error ribbon** connects them at each hour with the error in nm labelled at the end. Score components:
- **Arrival:** distance from the destination (or within the arrival radius = 0 penalty).
- **Safety:** grounded, grazed, or clear.
- **Time:** within the deadline, or lateness in hours.
- **Estimate quality (for stars):** how small the final error was compared with the naive no-current estimate (a line such as "You beat the naive estimate by N%", with N computed from the sim).
- Result stars 1-3; a "par" plan comes from the chart's authored solution, verified by a solver in tests.

### 6.5 Progression (charts)
- **Campaign:** authored charts in five chapters, each a small set of levels; every fifth level introduces a mode or a mechanic (matches the site's standing Level Select decision, TODO-NEXT W-1):
  1. **Open water**: one current zone; heading, speed, time only.
  2. **Wind and leeway**.
  3. **Fixes and landmarks** (Watch-by-watch).
  4. **Fog and uncharted hazards**.
  5. **Tides** (time-varying streams).
  6. **Two ships**: you steer two ships with separate speeds and deadlines, each with its own estimate and its own errors; a rendezvous or a convoy objective (later chart set).
  7. **Compass error**.
- **Generated charts (Practice):** seeded chart generator producing solvable charts of a chosen difficulty (fields, hazards, wind); each has a shareable seed string.
- **Later: Daily Chart** (date-seeded, same for all, archive, opt-in leaderboard on lowest final error via `app/leaderboards.py` and `shared/leaderboard.js`), reusing Signal's daily-seed pattern if it ships first.

## 7. Multiple ships (later charts)
A chart may hold 2-3 ships with their own start, destination, speed range and schedule; the plan has one leg list per ship; the sim steps all ships together and reports collisions (two ships closer than a stated radius) as "close pass" events and grounding as before. Ship count is a difficulty knob, not a separate game. Start with two.

## 8. Data model
```json
{
  "schema": 1,
  "meta": {
    "charts": {"open-01": {"best_error_nm": 0.0, "stars": 0, "attempts": 0, "solved_naive": false}},
    "unlocked_chapters": 1, "practice_seeds_played": 0,
    "best": {"smallest_final_error_nm": null, "longest_route_nm": 0},
    "achievements_earned": {}
  },
  "run": null,
  "settings": {"text_scale": 1, "reduce_motion": false, "units": "nm", "story_text": true, "planner_input": "numeric"}
}
```
`run` is `null` between attempts, otherwise `{"chart_id", "seed", "mode", "legs": [...], "phase": "plan|sail|reveal", "leg_index", "fixes": [...]}`. Chart definitions are content, not state: `content/charts/*.json` (polygons, hazards with charted flags, current zones with true values and charted ranges, wind, landmarks, deadline, par plan, arrival radius). A Python loader validates them (see testing). `achievements_earned` written and never read back.

## 9. Content needs
- Claude drafts: about 40 authored charts across the chapters (a launch minimum of 12 for a complete game), the practice generator, flavor lines for the captain's log (story toggle).
- Story text (a small ship's-log voice, notes on places) is switchable with the shared story toggle. Charts play identically with it off.
- Real-world flavor in the info panel and chapter intros follows the sourced-facts convention (section 3); leave any fact out rather than show an unsourced one.

## 10. UI sketch (words)
- **Chart view (centre):** SVG chart; the estimated track as a dashed line with leg markers (numbered), the destination as a ringed flag, hazards as labelled shapes with hatch patterns, current zones as light outlined regions with arrow + "1-2 kn", wind as a rose arrow.
- **Planner (right/below):** leg list with heading, speed, hours (numeric steppers + optional dial); totals and ETA; Undo/Clear; "Naive steer-to" helper; a **Sail** button (confirm dialog if the plan is empty or overshoots the deadline).
- **Sail:** the true track animates from the start; a scrub bar and Skip; the log ticks off events ("Hour 2: set to the east felt").
- **Reveal:** overlay of estimated vs true, error ribbon, score card, "Retry", "Next chart", "Show the par plan" (after the first attempt).
- **Mobile dock:** Sail and Undo in the dock; HUD shows total hours and legs. Chart pinch-zoom is a stretch goal; the default fits 375px without pan.
- Keyboard: arrows to step the selected leg's heading/speed, Enter to add a leg, `S` to sail, `?` help.

## 11. Testing approach
- pytest (pure Python): sim determinism, hazard intersection (long steps do not skip a rock), current/wind vector math against hand-computed cases, estimated-vs-true divergence with zero current equals zero, tide sine periodicity, fix correction arithmetic, arrival radius edges, save round-trip.
- **Chart validator** (runs over every authored chart as a test): the par plan actually reaches the destination without grounding; the naive steer-to plan fails on charts intended to defeat it; charted current ranges contain the true value; hazards do not overlap the start or destination; coordinates are inside bounds; ids unique.
- **Generator fuzz:** 5,000 seeded practice charts per difficulty are solvable by a reference solver (a simple search over leg headings), and generation stays under a time ceiling.
- Golden-image style test for the SVG markup of two small charts (string compare of generated markup, not pixels).
- Live checks via the shared `hub-dev-server`: numeric input and dial at 375px, keyboard-only planning, high contrast, reduce motion (playback replaced by an instant reveal).

## 12. Baseline checklist pointer (what differs)
Use `overclock-plan.md` sections 4 and 5, slug `dead-reckoning`. Specifics:
| Item | Note |
|---|---|
| Save | Attempt state is small; `run` may be mid-plan (legs) but never mid-sail |
| Confirm dialog | Sail with an empty or over-deadline plan; Reset progress |
| Mobile dock / HUD | Sail/Undo in the dock; hours and legs in the HUD |
| Colorblind | Hazards by shape, hatch and label; currents by arrow + number; tracks by dash style (estimated dashed, true solid) |
| Light theme | Natural fit: paper-chart palette; dark theme is a night-chart palette; verify line contrast in both |
| Story | Shared toggle hides the captain's log and place notes only |
| Real-world examples | Section 3 facts, each with a named, verified source or omitted |
| Info panel | "How dead reckoning works (in this game)" via `shared/info-page.css`, with the abstraction disclaimer and the sourced facts |
| Leaderboard | Later, optional, opt-in (Daily Chart, lowest final error) |
| Achievements | See below; follow `ACHIEVEMENTS-SYSTEM-DESIGN.md` |

## 13. Achievements (14)
1. First Landfall — reach a destination.
2. Dead On — end within 0.5 nm of your estimate.
3. Trust the Numbers — three-star a chart without using the naive helper.
4. Around the Rocks — clear a chart with 3 hazards on the direct line.
5. Set and Drift — beat the naive estimate by half on a current chart.
6. First Fix — use a landmark fix.
7. Fog of War-ish — finish a fog chart without grounding.
8. Riding the Tide — arrive with the fair stream on a tide chart.
9. Two at Once — complete a two-ship chart.
10. Aground — run aground once (kindly worded, "everyone does").
11. Long Way Round — plot a route over 60 nm (use a config constant; adjust to chart sizes).
12. Chapter Closer — finish a chapter.
13. Practice Makes — play 10 practice seeds.
14. All Stars — three stars on every campaign chart.

## 14. Milestones
Commit + tag each: `git tag dead-reckoning-milestone-0N`. Milestones 1-4 ship a complete, playable game.

| # | Milestone | Content | Status |
|---|-----------|---------|--------|
| 1 | Sim core | `sim.py`: vectors, current zones, leeway, hazard intersection, tracks, scoring, text harness. Tests: determinism, hazards, vectors | Not started |
| 2 | Chart SVG | Chart renderer (grid, land, hazards, current arrows, scale, rose), one hard-coded chart, static estimated track from a hard-coded plan | Not started |
| 3 | Plan and sail | Leg editor (numeric), live estimated track, Sail, animated true track, reveal overlay with error ribbon and score. **Playable slice** | Not started |
| 4 | Campaign chapter 1-2 | 12 authored charts (open water, wind), stars, retry, par plan reveal, chart validator tests. **First complete, playable game** | Not started |
| 5 | Fixes and watch-by-watch | Landmarks, bearing fixes, leg-at-a-time mode, chapter 3 | Not started |
| 6 | Fog, tides, compass error | Chapters 4, 5, 7; tide tables; uncharted hazards | Not started |
| 7 | Two ships | Multi-ship plan and sim, collision events, chapter 6 | Not started |
| 8 | Practice generator | Seeded chart generator, solvability fuzz, shareable seeds | Not started |
| 9 | Standard kit | Save widget, settings, confirm dialogs, tutorial, mobile dock/HUD, changelog, info panel with sourced facts, feedback, light theme, colorblind audit | Not started |
| 10 | Achievements + hub | 14 achievements, panel/toast, title card, favicon, `sw.js`, manifests, root CLAUDE.md row, dev logs, tag | Not started |
| 11 | Daily Chart (optional) | Date-seeded chart, archive, opt-in leaderboard board | Not started |

## 15. Risks
- **Arithmetic feeling like homework.** Mitigation: helpers and a numeric-first-but-forgiving UI, the naive helper as a first step, and short charts; the fun is the reveal moment, so make it prominent.
- **Charted current ranges feeling unfair.** Mitigation: the true value is always inside the stated range, tests enforce it, and the reveal explains what happened.
- **Solvability of generated charts.** Mitigation: the reference solver fuzz and a rejection loop; fall back to authored charts if a seed fails.
- **Mobile heading entry.** Mitigation: numeric steppers and quick-turn buttons (+/-5, +/-15), dial optional.
- **Overpromising realism.** Mitigation: the abstraction disclaimer in the info panel and only modest, sourced facts.

## 16. Open questions for the user
1. Full plan up front as the main mode, with Watch-by-watch introduced at chapter 3 (recommended), or the other way round?
2. Is a two-ship chart worth its complexity for launch, or should it wait for a later pass? (Recommend a later pass, Milestone 7.)
3. OK to leave celestial navigation out entirely at launch (modest flavor only)?
