# Derelict Garden (slug `derelict-garden`, TODO QI-17) - Groundwork Plan

Source: the Quick ideas round (B5), owner-approved: "tend a garden on an abandoned ship, restoring one section at a time, with a steady-progress-that-cannot-be-lost feel." Checked against `PLAYER-PROFILE.md`: steady progress that can never be lost and a routine they know by heart (named as relaxed), collecting one of each species, space and robots, a companion robot that barely speaks, Unpacking-like calm without perfectionism, no timers, no energy, no grinding. Personal project, no BCM tag, working title.

Pitch: wake a drowned garden deck on an abandoned ship one bed at a time, placing lamps, pipes and soil so plants sprout and stay sprouted.

## 1. Concept
- You are the new groundskeeper of the ship Verdigris, abandoned but warm. A small maintenance robot, Moss, follows you and mostly just tilts its lamp. The garden deck has twelve sections; each section is a short placement puzzle: beds, plants that want things (light, water, soil, shade, a neighbour) and a few fixtures to place (lamp, pipe, soil bag, vent, shade).
- 2-minute session: place a few fixtures, watch beds sprout. 20-minute session: restore a whole section and read its plant notes.
- Look: dark ship deck with soft warm lamps, faceted low-poly plants that visibly grow in three steps (sprout, leaf, bloom). Needs shown by icon plus word, never colour alone. Quiet tone; Moss's lamp is the only voice.

## 2. Core rules (pure functions, nothing can wither)
- A section is a grid (4x4 up to 7x7) with bed cells, blocked cells and a fixed set of fixtures to place. A plant has up to three needs from: Light (reached by a lamp within 2 cells in line), Water (a pipe next to it), Soil (a soil bag next to it), Air (a vent in the row or column), Shade, Near X / Away from Y.
- Placing a fixture is free and reversible. A bed grows one step for each need met, shown immediately and permanently: the step reached is stored and never lost, even if the player later moves the fixture (the plant simply stays at its best step; moving things never kills). A section is Restored when every bed reaches full bloom at the same time in one layout.
- No clock, no watering schedule, no energy, no spoilage. Leaving the game changes nothing.

## 3. Content size
12 sections (the ship's decks), 4 beds each in a tutorial section up to 12 beds, 60 plants in total: 40 real species (herbs, vegetables, flowers) and 20 ship-grown rarities, each with a card. Sections open from the start (any order), shown on a ship cutaway; the order a player picks forms a bigger picture. Section sizes grow from 4x4 to 7x7.

## 4. How correctness is PROVED
- Dev tool `tools/place.py` is a constraint solver (backtracking over fixture positions) that finds every layout that fully blooms. Tests assert each section has at least one and at most 12 full-bloom layouts, the stored layout is one of them, and every plant's need is satisfiable by the stored layout.
- Monotone progress: a property test replays random-looking move lists from fixed seeds-in-data and asserts a bed's stored growth step never decreases.
- No-clock, no-random, no-energy lint over the code. Determinism: pure functions.

## 5. Collection and 100%
- The Greenhouse Book: 60 plant cards, each filled when the plant first reaches full bloom (a pressed-flower picture, its needs, a one-line fact and a sourced note for real species). The ship cutaway shows each restored section lit and green. 100% = all 12 sections Restored and 60 cards. States only go up; a half-restored section keeps all its progress.

## 6. Goals and hint ladder
- Three always-visible goals, any order, with bars. Stats strip: Sections restored, Beds in bloom, Plants found, Fixtures placed. The tally counts placements and moves; every placement visibly counts.
- Ladder (first rung asks "Would you like a suggestion?"): Nudge (which bed has the most demanding plant), Hint (one fixture shown as a ghost), Answer (the whole stored layout as ghosts, with a "Place them" button). Free, on request.

## 7. Achievements (14)
First Sprout; Ten Sprouts; First Section; Six Sections; Twelve Sections; Full Bloom (30 beds); Greenhouse Book (30 cards); Whole Book (60 cards); Herb Shelf (all herbs); Salad Bar (all leaf vegetables); Rarities (all 20 ship rarities); Tidy Beds (a section restored in under par placements); Moved Things (rearrange a section twice and keep progress); Moss Approves (1,000 fixtures placed).

## 8. Real-world facts
The 40 real species cards show a short fact and a growing note read live from GBIF (api.gbif.org species API) and, for space-grown plants, from NASA's Veggie experiment pages (nasa.gov), each with a read date and a bundled snapshot as fallback. The ship, rarities and Moss are fiction and marked so. More game than teaching.

## 9. Reuse
Grid and placement solver from Hull Repair; the collectable shelf and ship map from Station Medic and Stranded; `ambient-bg.css`, shared `level-select.js`, `hint-ladder.js`, `goals-panel.js`, `opening-screen.js`, `info_page.py`, `announcer.js`, `pc-shell.js`.

## 10. Milestones
| # | Milestone | Content |
|---|-----------|---------|
| 1 | Engine and solver | Need model, fixtures, growth steps, placement solver, sections 1-3 with proofs and the monotone-progress test |
| 2 | Garden UI | SVG deck, drag or tap-place fixtures, growth animation (toggleable), save contract. Playable slice |
| 3 | Sections 4-8 | 5 more sections, shade and neighbour needs, Greenhouse Book and plant cards |
| 4 | Sections 9-12, hints, goals | 4 more sections (12), ship rarities, hint ladder, three-goals strip, live GBIF facts. First complete game |
| 5 | Standard kit | Opening screen, tutorial, About with Sources, What's New, keyboard help, confirm dialogs, light theme, accessibility |
| 6 | Achievements | 14 achievements, panel and toast, manifest, reachability test |
| 7 | Desktop boot and wrap-up | `pc-config.json`, `pc.css`, `pc.js`, generated `pc.html`, docs, changelog |

## 11. Open questions for the owner
1. Should plants ever show a passive visual change over real time (a slow sway), or stay still unless you act? Default: gentle sway only, toggleable, never progress.
2. Is a free "decorate" mode (move rocks and benches for looks only) wanted after a section is restored? Default: no, to avoid perfectionism.
