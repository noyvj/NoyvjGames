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
| 3 | Plan and sail | Not started | Not started |
| 4 | Campaign chapters 1-2 | Not started | Not started |
| 5 | Fixes and watch-by-watch | Not started | Not started |
| 6 | Fog, tides, compass error | Not started | Not started |
| 7 | Two ships | DEFERRED (plan recommendation, FOR-YOU Dr2: later pass) | Deferred |
| 8 | Practice generator | Not started | Not started |
| 9 | Standard kit | Not started | Not started |
| 10 | Achievements and own-folder wrap-up | Not started | Not started |

## Working conventions
- Commit + tag per milestone: `git commit -m "Milestone N: <name>"` then `git tag dead-reckoning-milestone-0N`.
- Hub registration (title card, `sw.js`, manifests, root CLAUDE.md row, dev logs) is a separate later milestone owned by the hub session (TODO M-5b-12). Nothing outside this folder is touched here.
