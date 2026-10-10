# Mirror Lab (slug `mirror-lab`, TODO QI-10) - Groundwork Plan

Source: the Quick ideas round (A10), owner-approved: "place mirrors and prisms so a laser reaches every sensor." Checked against `PLAYER-PROFILE.md`: spatial puzzles, physics as an interest, space and computers, dark moody look (a beam on dark is easy to read), one puzzle at a time, "more game than teaching", no timers, nothing lost. Personal project, no BCM tag, working title.

Pitch: a dark optics bench where you place mirrors, splitters and prisms so a single beam lights every sensor on the board.

## 1. Concept
- You are the optics technician at a deep-sky relay (invented: Arden Relay) whose light guides were smashed. Each bench has an emitter, a set of sensors and a tray of pieces. Drop pieces onto allowed cells and watch the beam redraw instantly; light every sensor to bring that circuit back.
- 2-minute session: one or two easy benches. 20-minute session: a chapter with prisms.
- Look: black bench, thin glowing beams, faceted low-poly mirror blocks. Beam types are told apart by dash style and a letter (S short, L long), never colour alone.

## 2. Core rules (a pure ray tracer on a grid)
- Cells: empty (placeable or fixed), wall, emitter (fixed direction), sensor, fixed mirror. Pieces: mirror "/" and "\" (flip with a tap), splitter (passes straight and turns left), prism (splits into an S beam turning one way and an L beam turning the other), absorber (stops a beam), filter (passes only S or only L).
- A beam moves one cell at a time along the grid, turns on mirrors, forks at splitters and prisms, stops at walls and absorbers. A beam entering a loop it has already been through is cut by cycle detection.
- Sensors are lit when a beam of their needed kind (any, S only, L only) enters them. The bench is cleared when all sensors are lit; surplus pieces are allowed to stay unused. Some benches add "must not light" decoy sensors; lighting one is shown but is not a loss, you just cannot clear until it is dark.
- Pieces are limited per bench (the tray). The tray count is shown; Pick up returns a piece freely.

## 3. Content size
40 benches in 5 chapters of 8: Flat Mirrors, Splitters, Prisms (S and L), Filters and Decoys, The Long Run (large benches mixing everything). Chapter n+1 opens at 5 of 8; any order inside. Boards 5x5 up to 9x9.

## 4. How correctness is PROVED
- Dev tool `tools/solve.py` enumerates all placements from the tray onto the allowed cells (pruned by reachability along the beam) for every bench. Tests assert at least one valid solution, the stored solution is valid, and for the starred "single answer" benches the count of distinct solutions (modulo unused pieces) is exactly one.
- Ray-trace tests: law of reflection on a table of cases, prism S/L split geometry, loop cut, beam count never exceeds a bound; determinism with no clock or random.
- Tray minimality: removing any one piece from the stored solution breaks it (so the tray is not padded), checked per bench.

## 5. Collection and 100%
- The Optics Bench Log: a shelf of every piece type with a page that fills on first use (mirror, splitter, prism, filter, absorber) plus 40 circuit cards (one per bench) that light a relay map of the station as repaired. A "Fewest pieces" tag per bench is a bonus. 100% = all 40 benches cleared. States only go up.

## 6. Goals and hint ladder
- Three always-visible goals, any order, with bars. Stats strip: Benches cleared, Sensors lit, Pieces placed, Fewest-piece tags. The tally counts placements and pick-ups.
- Ladder (first rung asks "Would you like a suggestion?"): Nudge (which sensor to aim for first), Hint (one piece placed as a ghost), Answer (the whole stored layout as ghosts with a "Place them" button). Free, on request.

## 7. Achievements (14)
First Beam; Ten Benches; Twenty Benches; All Forty; Mirror Maker (chapter 1); Splitting Hairs (chapter 2); Rainbow (chapter 3); Clear Filter (chapter 4); The Long Run (chapter 5); Fewest Pieces (5 tags); Fewest Pieces Again (20 tags); Double Bounce (a beam turning 6 times); Light Both (a prism lighting S and L sensors); Quiet Decoys (clear a decoy bench).

## 8. Real-world facts
Three or four short facts (law of reflection, dispersion, refractive index, the Moon laser-ranging reflectors) read live from the Wikipedia REST summary service for each topic, with the read date; a bundled copy is the fallback. The simplified prism (two beams, S and L) is stated plainly on About. More game than teaching.

## 9. Reuse
Board, renderer and `tools/` solver patterns from Hull Repair; tray/inventory pattern from Logic Gates' chips; `level-select.js`, `hint-ladder.js`, `goals-panel.js`, `opening-screen.js`, `info_page.py`, `announcer.js`, `pc-shell.js`.

## 10. Milestones
| # | Milestone | Content |
|---|-----------|---------|
| 1 | Ray tracer and solver | Tracer, pieces, placement solver, chapter 1 (8 benches) with proofs |
| 2 | Bench UI | SVG bench, tray, drag or tap-place, live beam redraw, keyboard placement, save contract. Playable slice |
| 3 | Chapters 2-3 | 16 more benches, splitters, prisms and S/L sensors, Bench Log |
| 4 | Chapters 4-5, hints, goals | 16 more benches (40), filters, decoys, hint ladder, three-goals strip. First complete game |
| 5 | Standard kit | Opening screen, tutorial, About with Sources, What's New, keyboard help, confirm dialogs, light theme, accessibility |
| 6 | Achievements | 14 achievements, panel and toast, manifest, reachability test |
| 7 | Desktop boot and wrap-up | `pc-config.json`, `pc.css`, `pc.js`, generated `pc.html`, docs, changelog |

## 11. Open questions for the owner
1. Are decoy "must stay dark" sensors welcome, or should every sensor simply need lighting? Default: decoys only in chapter 4 and after.
