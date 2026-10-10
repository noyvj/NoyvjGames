# Material Match (slug `material-match`, TODO QI-41) - Groundwork Plan

Source: the Quick ideas round (G8), owner-approved: "pick materials for a tool or building from their real properties, with the numbers read from a named source." Checked against `PLAYER-PROFILE.md`: chemistry, physics and engineering interests, collecting every item (one of each material), a notebook that fills in, housing and healthcare named as caring topics, real-world games show several points of view, "fun that happens to be accurate", sources easy to find, hint ladder, no timers, nothing lost. Personal project, no BCM tag, working title. One-line pitch: a station workshop needs a hammer head, a window and a hull plate; the right material is on the shelf, and its numbers will tell you which.

## 1. Concept
You run the supply shelf at **Rook Workshop**, an orbital makerspace. A **Brief** arrives ("a hammer head: hard, tough, not too heavy", "a window pane: clear, stiff, tolerates heat"). The shelf holds 30 materials (steel, aluminium, titanium, copper, glass, concrete, oak, bamboo, carbon fibre, nylon, rubber, brick, granite...). Each material is a card with real numbers: density, strength, stiffness, hardness, melting point, thermal and electrical conductivity, and a relative cost word. You sort, filter, compare and **assign** a material to the part. The brief checks its stated limits and says which part of the brief each pick meets or misses.
- 2-minute session: one pick-one brief, filter by a property, choose, a plaque with the part appears.
- 20-minute session: a chapter of eight briefs that mix pick-one with pick-two (a frame and a skin), and a trade-off note comparing two good answers.
- Look: dark, calm low-poly workshop; materials drawn as faceted swatches with a name and a shape code (never colour alone); properties set as bars and numbers with units. Quiet; optional generated clicks only.
- **Nothing fails.** A wrong pick is a note ("this melts below your limit") with the failing property shown, free retry, no penalty.

## 2. Rules (a pure function of the briefs and the materials table)
- A brief has 1 to 3 **parts**; each part has constraints on properties (at least, at most, between) and sometimes an ordering rule ("lightest that meets the limits"). A pick satisfies a part if all its constraints hold; the brief is **cleared** when each part has a satisfying pick and, where the brief says "best", the pick is the best by that rule.
- Pick-two briefs add pair rules ("not both conductors", "the two must differ in stiffness by at least a factor of five").
- Many briefs also carry a **point-of-view note**: for example, "the builder wants cheap, the engineer wants stiff, the neighbour wants low carbon". These notes list how the answer changes when a different priority leads, shown after clearing, with sources. The game never ranks the priorities.
- Determinism: pure function of data; no clock, no randomness.

## 3. Content size
- 40 briefs in five chapters of eight: Tools, Buildings, Station Parts, Clothes and Cloth, Everyday Things. 30 materials, 8 properties each (240 numbers).
- A **Materials Book** of 30 cards (one per material, with a fun fact and a source line) collected by using each material correctly once; 40 plaques of "Part made" in the workshop.

## 4. How fairness is PROVED (tests)
- A solver (`tools/solver.py`) enumerates all picks for every brief and requires: at least one satisfying pick exists, and for "best" briefs, **exactly one** pick (or pair) is best, with a **margin**: the winner beats the runner-up by at least 10% on the ranking property, so small changes in a source value cannot flip the answer.
- A **data guard** checks every stored number against the source sheet (file with dated rows), flags a value that moves more than 10% on refresh, and rebuilds briefs' limits from margins; briefs never depend on a single borderline value.
- Data lint: all units consistent, no missing property for any material used in a brief, every number carries its source id and date.
- Determinism: same pick, same verdict. A completion simulator picks the stored answer for every brief and confirms the Materials Book fills to 30 of 30.

## 5. Bigger picture, goals, hints
- The **Workshop Floor** is the picture: a dark workshop with 40 empty slots on the walls that fill with the parts you have made, a completion percentage bar, and the **Materials Book** shelf of 30.
- Three goals always visible (any order): the next three unearned achievements with counts and bars. Stats strip: Briefs cleared, Parts made, Materials known, Notes read.
- Hint ladder (opt-in; first rung asks "Would you like a suggestion?"): Nudge (which property matters most), Hint (greys out materials that fail the first limit), Answer (the winning pick, with a Use it button; the brief still clears).
- Every chapter and brief open from the start; the order is a suggestion.

## 6. Achievements (14; computed from facts)
1 First Part; 2 Ten Parts; 3 Chapter Built (a whole chapter); 4 Full Workshop (all 40); 5 Right First Time (10 briefs on the first pick); 6 Thirty First Tries; 7 Materials Half (15); 8 Materials Full (30); 9 Pair (first pick-two brief); 10 Best of Two (clear 5 pick-two briefs); 11 Other Side (read 10 point-of-view notes); 12 All Sides (read all notes); 13 Filtered (use filters on 10 briefs); 14 Second Opinion (all three hint rungs on one brief).

## 7. Real-world facts
The materials table is **real data read from named sources and dated on screen**: a stored `materials.json` built by a dev tool from named reference tables (for example a public engineering materials reference such as Engineering ToolBox and the reference values on Wikipedia, each row stamped with its source and read date), plus a live check on the About page that re-reads those pages and shows today's value beside the stored one. Where sources disagree the card shows the range. Point-of-view notes cite named sources. More game than teaching, and a note on every card says these are typical values, not design data.

## 8. Stack, save and reuse
- Pyodide Python, plain HTML/CSS with code-drawn SVG, no build step. Modules: `materials.py` (loader and validation), `briefs_*.py`, `check.py`, `solver.py` (tests and dev), `book.py`, `povs.py`, `progress.py`, `hints.py`, `render.py` (cards, bars, sorting UI), `achievements.py`, `info.py`, `game.py`, `app.js`. `tools/build_materials.py` regenerates the data file.
- Reuses Station Medic's sheet-and-cabinet interface pattern, Lexis's `sources.json` live-read pattern, `shared/hint-ladder.js`, `goals-panel.js`, `save-widget.js`, `level-select.js`.
- Save: best pick per brief, book, notes read, hint rungs, flags. Saved picks are re-checked against the current data on load.

## 9. Milestones
| # | Milestone | Content |
|---|-----------|---------|
| 1 | Engine | Materials table with sources, brief format, checker, margin solver, chapter 1 (8 briefs) with proofs |
| 2 | Shelf UI | Material cards, sort and filter, assign, verdict note, workshop floor, save contract. Playable slice |
| 3 | Chapters 2-4, book, hints | 24 more briefs, Materials Book, point-of-view notes, hint ladder, three-goals strip |
| 4 | Chapter 5 | 8 more briefs (40 in all), pick-two briefs. First complete game |
| 5 | Standard kit | Opening screen, tutorial, settings, About with live-read sources and value check, What's New, keyboard help, light theme, accessibility pass |
| 6 | Achievements | 14 achievements, panel and toast, manifest, reachability test |
| 7 | Desktop boot and wrap-up | `pc-config.json`, `pc.css`, `pc.js`, generated `pc.html`, docs, changelog |

## 10. Open questions for the owner (defaults used meanwhile)
1. Which named source should be the main one for the numbers? Default: a public engineering reference (Engineering ToolBox) cross-checked against the Wikipedia reference values.
2. Should the cost word (cheap to dear) be included, given it varies by place and year? Default: yes as a relative word with a date, never a price.
