# Slingshot (working title)

Seed: `planning/slingshot-plan.md` (Quick ideas round A6, TODO QI-6). Personal project, no BCM tag. Milestones 1 to 3 built 2026-10-12 by a background agent: the physics core with chapter 1 and its proofs, the playable planner, chapters 2 and 3 (22 missions), the Mars moons, gravity assists, the mission picker and the Moon Atlas. NOT yet linked from the hub or registered anywhere (no `sw.js` precache, no `game-manifest.json`, no `offline-manifest.json`, no site-settings key): hub registration is the separate step QI-6-R. The suite has 256 tests (about 4 s). Milestones 4 to 7 (chapters 4 and 5, hint ladder, goals strip, live data, opening screen, tutorial, achievements, Desktop boot) are not built.

## One-line pitch
Plan a probe's burns on a quiet chart, watch the flight play out exactly as planned, and use planets' gravity to reach the Moon, Mars and its moons on a fuel budget.

## Stack
- Pyodide Python, plain HTML/CSS, no build step. `game.py` is the single engine entry point (`handle(json) -> json`, `get_state()` / `load_state()` for the shared save widget); `app.js` is glue only (it draws SVG and turns input into requests). Python 3.9 locally (Pyodide 3.12): no 3.10+ syntax in engine code. No Node is available in this repo's tooling: check JS in the browser.
- Runs from any static server. No audio, no image files (every planet, path and chart is drawn as SVG by the page).

## Core constraints (do not violate without asking)
1. The engine is pure and deterministic: no clock, no randomness (a test scans every engine module). A flight is a pure function of the mission and the plan: fixed time step, no adaptive step, same plan same path to the last digit.
2. Nothing is timed, nothing can fail, nothing is lost. A miss is a report ("passed 1.2 million km wide") and the plan stays on screen; every flight starts with the full budget again. The playback animation is cosmetic and a Settings switch (reduce motion) makes it jump to the end.
3. No luck and no guessing: every mission is PROVED solvable by a stored reference plan that reaches the goal with at least 10 percent of the budget to spare (see below).
4. Never colour alone: a burn is a diamond with its number, the goal body has a dashed ring and the word "goal", the probe has a ring and its name, the path still to come is dashed, a locked mission is dashed and says "locked", a done one has a tick, the result title has its own symbol, the fuel meter has its numbers beside it. Everything visual has a text version (readout line under the slider, "Chart as text", "Atlas as text", the close-up caption).
5. Effects toggleable (the glow on the path); reduced motion honoured; light and dark theme; high contrast; text size.
6. Real data, dated and named: sizes, pull, orbit radii and periods are NASA/JPL numbers frozen in `data/snapshot.json` (read 2026-10-12) and shown on About, the Sources page and each atlas card. The model is simplified and says so on About.
7. The view never carries a mission's reference plan or alternative (a test checks).

## The model (`orbit.py`, `bodies.py`)
- Units: km, seconds, km/s. A SCENE has one central body (the Sun, Earth or Mars) and children on circular orbits (radius from the source, rate from Kepler's third law with both GMs; the planets' start angles come from the JPL mean longitudes on the mission's start date, a moon's start angle is set by the mission). 2D, coplanar, all circles.
- The probe feels only the central body's gravity, integrated with velocity-Verlet at a fixed step per scene: Earth/Moon 0.1 hour, Mars moons 1 minute, Sun scenes a quarter of a day. Stated tolerances (tests/test_orbit.py): a circular orbit keeps its radius to 5e-4 over an orbit, the energy of a free probe drifts under 5e-5 over a year.
- Patched conics: when the probe comes inside a child's sphere of influence (SOI = a (GM_child / GM_parent)^0.4; also checked along the straight piece of a fast step) the pass is solved exactly as a conic around the child (`pass_through`): the exit is the mirror of the entry about the closest approach, which bends the path and changes the speed round the central body (a gravity assist). The pass takes its real time (rounded to whole steps) and the probe resumes at the child's place then; `tests/test_orbit.py` checks the closed form against a brute-force integration to 0.3 percent. The plan may carry one "closest-approach burn" per body, along the velocity at periapsis (negative slows down): bound afterwards means captured (low and high point, period, sense reported), otherwise the pass is a powered flyby.
- A body with no usable SOI (Phobos, Deimos) is reached by RENDEZVOUS: within a stated distance at a stated relative speed (a game rule: the real escape speed of such a moon is a few metres per second).
- Burns: `{t, at, head, dv}`: step, `time` | `peri` | `apo` (the first periapsis/apoapsis at or after step t), direction in degrees from the probe's velocity (0 ahead, 180 back, 90 left, one decimal), strength in km/s (three decimals). At most 8 burns. Fuel = the burns that really happen plus closest-approach burns that were used.
- Goals (`goal` dict): `flyby {body, within, min?}` (closest approach to the centre), `capture {body, q:[lo,hi], big_q, sense?, by?}` (lowest and highest point of the orbit after the pass burn; `by` = latest step; `sense: retro` = clockwise on the chart), `rendezvous {body, radius, speed}`, `reach {radius, after?, dir?, by?}` (distance from the central body, optionally only after passing a body). Outcomes: success, over_budget, miss, crash.

## How fairness is PROVED (`tools/solve.py`, `refplans.py`, `tests/test_missions.py`)
- `tools/solve.py` finds every reference plan with the real engine (departure scan, aim burn, closest-approach burn in closed form, snapped to a 0.1 degree / 1 m/s grid) and writes `refplans.py` (GENERATED; the answers are kept in `tools/solved/*.json`, regenerate with `python3 tools/solve.py <id> --save` then `--assemble`). `budget = ceil(1.25 * cost / 0.05) * 0.05`.
- Cross-checked in the page: all 22 reference plans flown inside Pyodide (Python 3.12, WebAssembly) give the same outcome, fuel, end step and final position (to 1e-3 km) as CPython 3.9.
- Tests fly every plan: the reference plan reaches the goal with at least 10 percent of the budget to spare; the checker gives identical flights twice; a second plan with a different first burn also works (every Moon and Mars-moon mission has one; a planet transfer has a single window inside the flight); one grid step on any aim number leaves at least half of the neighbouring plans successful (a region, not a needle); the Sunward missions cannot be flown directly in the budget (the Hohmann cost to the goal radius exceeds it); no-burn plans never succeed.
- `tools/fetch_snapshot.py` reads the five JPL pages and the NASA fact sheet into `data/snapshot.json` and the generated `bodies_data.py`; a test compares them and checks each period against its source.

## Content (milestones 1 to 3: 22 missions)
Chapter 1 Near Neighbours (7, Earth scene from a high circular orbit, the Moon): First Light, Close Pass, Parking Orbit, Low Orbit, The Other Way Round (clockwise capture), Short Climb (lower start), Home Again (free return). Chapter 2 The Inner Run (8): Red Planet Flyby, Mars Orbit, Low Mars Orbit, The Next Window (a later start date), Express to Mars (by day 190), then Phobos, Deimos, Phobos From Above (Mars scene). Chapter 3 Slingshots (7, Venus): Venus Flyby, Venus Orbit, Express to Venus, Low Venus Pass, Sunward, Deeper Sunward, Mercury's Orbit (the last three need the Venus assist plus a backward burn). Chapter n+1 opens when 5 missions of chapter n are done (any five); inside a chapter any order. Derived from the reached set, so it only ever goes up; a save is judged in chapter order on load.

## Engine and page notes
- `game.handle` returns the whole view. Actions: `open`, `pick {mission}`, `next`, `burn_add {t, head, dv, at}`, `burn_set {i, ...}`, `burn_del {i}`, `pass_set {body, dv}`, `plan_clear`, `undo`, `redo`, `fly`, `scrub {n}`, `reset`. The view always carries the flight the current plan makes (`flight`: verdict, details, burn lines, path arrays, body positions per sample, close-up arcs, words), so Fly is the commit and not the first look.
- Save (`get_state`, only non-default keys besides `schema`): `cur`, `reached {id: {fuel, flights}}`, `work {id: plan}`, `tally {flights, edits, scrubs}`. Undo history is not saved. `load` checks every field alone, drops missions in closed chapters, cleans every saved plan (numbers clamped, unknown bodies dropped) and gives a fresh game for a bad or newer `schema`.
- Page: the chart is an SVG drawn by `app.js` (centre = the central body, y flipped so anticlockwise looks anticlockwise), a time slider over the engine's samples (also keys: arrows, Page Up/Down, Home/End, B adds a burn at that time, F flies, Ctrl/Cmd+Z), a burn editor (when, at the nearest/farthest point, direction with Ahead/Back/Left/Right buttons, strength), closest-approach burn rows, the results card, a close-up of each pass (zoomable), the mission picker, the Moon Atlas (a schematic column per destination with one mark per mission) and destination cards built from the dated numbers. Time units per scene: hours, minutes or days (`step_value` in the view).
- Stats strip: Missions (x/22), Fuel saved (sum of budget minus best fuel), Flights, Chapters open, Burns set.
- Engine modules (loaded in this order by `app.js`): bodies_data, bodies, orbit, plan, missions_base, missions_c1..c3, refplans, missions, atlas, info, then game. A test checks the list and the import order.

## Milestones
| # | Milestone | Content | Status |
|---|-----------|---------|--------|
| 1 | Physics core | Planet data module, integrator, burns, patched-conic capture, reference-plan checker, chapter 1 (7 missions) with proofs | Done |
| 2 | Planner UI | Chart, burn editor, Fly, scrubber, predicted path, results card, save contract. Playable slice | Done |
| 3 | Chapters 2-3 | 15 more missions, Mars moons, gravity assists, mission picker, Moon Atlas | Done |
| 4 | Chapters 4-5, hints, goals | 14 more missions (36 total), giants and far shore, hint ladder, three-goals strip, live data. First complete game | Not started |
| 5 | Standard kit | Opening screen, tutorial, About with Sources, What's New, keyboard help, confirm dialogs, light theme, accessibility | Not started |
| 6 | Achievements | 14 achievements, panel and toast, manifest, reachability test | Not started |
| 7 | Desktop boot and wrap-up | `pc-config.json`, `pc.css`, `pc.js`, generated `pc.html`, docs, changelog | Not started |
| R | Register in the hub | Same steps as the earlier new games (TODO QI-6-R) | Not started |
