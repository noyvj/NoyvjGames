# Picture Grid (working title)

Seed: `planning/picture-grid-plan.md` (Quick ideas round A12, TODO QI-12). Personal project, no BCM tag. Milestones 1 to 3 built 2026-10-12 by a background agent. NOT yet linked from the hub or registered anywhere (no `sw.js` precache, no `game-manifest.json`, no `offline-manifest.json`, no site-settings key): hub registration is the separate step QI-12-R.

## One-line pitch
Nonograms in a quiet gallery: fill each grid from the number clues on its rows and columns, and every solved picture is hung on a wall of space, robot and machine scenes that you can browse.

## Stack
- Pyodide Python, plain HTML/CSS, no build step. `game.py` is the single engine entry point (`handle(json) -> json`, `get_state()` / `load_state()` for the shared save widget); `app.js` is glue only (it draws SVG and turns input into requests). Python 3.9 locally (Pyodide 3.12): no 3.10+ syntax in engine code. No Node is available in this repo's tooling: check JS in the browser.
- Runs from any static server. No audio, no image files (every picture is a bitmap written out as data, drawn as SVG).

## Core constraints (do not violate without asking)
1. The engine is pure and deterministic: no clock, no randomness (a test scans every engine module). Clues are a pure function of the stored bitmap.
2. Nothing is timed, nothing can fail, nothing is lost. Marks are free to clear, undo and redo. A hung picture stays hung.
3. No luck and no guessing: every picture is PROVED to have exactly one solution AND to be solvable by line logic alone (see below). A picture that fails is redrawn, never shipped.
4. Never colour alone: a filled cell is a block with a facet and a hatch, a dot is a round mark, a wrong cell (Check mistakes) is a dashed outline with a slash, a finished clue greys and gets a tick, the selected tool has a thicker border, the keyboard cursor is a heavy ring. Everything visual has a text version (cursor line, "Clues as text", "Describe this picture in words").
5. Effects toggleable (the glow when a picture is hung); reduced motion honoured; light and dark theme; high contrast; text size.
6. All pictures are small pixel bitmaps authored by hand as data. No generated or downloaded images.

## How correctness is PROVED (`nonogram.py`, `tools/check_pictures.py`, `tests/test_pictures.py`)
- `solve_lines(rows, cols)`: the line-logic solver. One row or column at a time, it keeps every cell that is filled (or empty) in every arrangement of that line that fits the clue and the cells known, and repeats to a fixpoint. No branching, no guessing. `line_deductions(clue, cells)` is the per-line step (milestone 4's hint ladder will use it, so hints are always logically justified).
- `count_solutions(rows, cols, limit)`: the exhaustive counter (line logic, then branch on an unknown cell, so every picture that fits is visited). `count_by_rows`: a second counter that shares no code with the solver (every row arrangement, pruned only by column prefixes); the tests cross-check the two.
- Every picture: exactly one solution (both counters), finished by line logic alone and equal to its bitmap, clues match the bitmap row by row and column by column, deterministic. `python3 tools/check_pictures.py [gallery-id] [--draw]` prints the proof table; `suggest_fixes(rows)` lists one- and two-cell edits of a draft that pass (symmetric drawings are usually ambiguous and need one asymmetric pixel).

## Content
`pictures_g1.py` Instruments (10 pictures, 5x5), `pictures_g2.py` Small Machines (10, 8x8), `pictures_g3.py` Robots (10, 10x10): frozen data (id, title, one-line caption, tint, bitmap). `pictures.py` wraps them (`GALLERIES`, `ALL`, `BY_ID`, `ORDER`), derives the clues and holds the gating. Tints (`brass teal rose violet moss sky`) are three-tone ramps in `style.css` (dark and light); a hung picture is drawn with the ramp's tones banded by row thirds.
Adding a gallery: write `pictures_gN.py`, add it to `pictures._MODULES` and to `ENGINE_MODULES` in `app.js` (a test checks the list), run `tools/check_pictures.py`, then the tests.

## Gating
Gallery 0 is open from the start; gallery n+1 opens when `OPEN_AT` (6) pictures of gallery n are hung (any six); inside a gallery every frame is open in any order. Derived from the hung set, so it only ever goes up. A save is judged in gallery order on load, so a hand-edited save cannot skip ahead.

## Engine and page notes
- `game.handle` returns the whole view. Actions: `open`, `pick {picture}`, `next` (next open frame not yet hung), `paint {cells: [[r, c], ...], value 1|2|0}` (fill / dot / unknown; one call = one undo step and one "stroke"), `undo`, `redo`, `assist {name, on}` (`check`, `autodot`, `focus`: all off by default), `retry` (solve a hung picture again from a blank frame; it stays hung; fewer strokes improves its best), `reset`.
- A frame is finished when every row and column's FILLED cells make exactly its clue (dots and unknowns both count as empty); the engine then hangs it, keeps the best stroke count and shows the picture clean (filled cells only, tinted). A hung frame is read-only until Solve it again. The view never contains an unhung picture's title, caption or bitmap (a test checks).
- The tally counts the player's own marks only (fills, dots, clears); auto-dots are free and not counted. "Cells filled" is the headline stat; "Strokes here" counts this frame's strokes.
- Save (`get_state`, only non-default keys besides `schema`): `cur`, `solved {id: best strokes}`, `work {id: rows of ".#x"}` (an unhung frame with any mark, or a hung picture being solved again), `moves {id: strokes}` (only for saved frames), `tally`, `assist`. Undo history is not saved. `load` checks every field alone, drops pictures in closed galleries and frames of the wrong shape or alphabet, and hangs a saved frame that is already complete. A `schema` key (1) is always written; a save with a missing schema is read as layout 1, one with a bad or newer schema is ignored (a fresh game), and every other key is optional so old saves stay compatible.
- Page: the SVG board is drawn by `app.js` (`drawBoard`): clues left and above with a tick when the engine says a line is satisfied, marks, grid lines (heavier every fifth), a heavy keyboard ring. Input: pointer drag along a line (the first move locks the row or column; a stroke started on an empty cell fills or dots only empty cells, one started on a mark clears marks of that kind), right button / Shift / Alt dots, Fill/Dot buttons for touch, keyboard (arrows, Space/Enter marks, F/X choose tool, Backspace clears, Shift+arrow marks the cell moved onto, Ctrl/Cmd+Z undo, Ctrl/Cmd+Shift+Z or Y redo). Cells fit the width down to 24 px; Settings "Large cells" makes them 44 px and the board scrolls sideways (a quick tap still marks on a scrolling board).
- Gallery wall (`#gallery-panel`): each gallery with hung/total, locked galleries say how many more to hang; a hung frame is a small tinted picture with name, size and strokes (opens the large view: big picture, caption, a words description, previous/next hung, Solve it again); an unhung frame is a dark frame you can open to play.
- Standard kit is NOT built yet (no opening screen, tutorial, About, What's New, keyboard-help overlay, achievements, Desktop boot, `last-played`, `whats-new-banner`). The page includes only the shared files the plan's milestone 2 needs: theme, lite mode, error boundary, perf mark, debug overlay, report-problem, profile, site-settings, a11y/touch-target CSS, hub-auth, save widget, confirm dialog.

## Milestones
| # | Milestone | Content | Status |
|---|-----------|---------|--------|
| 1 | Engine and solvers | Clue generator, line-logic solver, exhaustive counter, gallery 1 (10 pictures) with proofs | Done |
| 2 | Frame UI | SVG grid, drag fill and dot, keyboard cursor, assists, save contract. Playable slice | Done |
| 3 | Galleries 2-3 | 20 more pictures, the Gallery wall and large view, gating | Done |
| 4 | Galleries 4-6, hints, goals | 30 more pictures (60), hint ladder, three-goals strip, slideshow. First complete game | Not started |
| 5 | Standard kit | Opening screen, tutorial, About with Sources, What's New, keyboard help, confirm dialogs, light theme, accessibility | Not started |
| 6 | Achievements | 14 achievements, panel and toast, manifest, reachability test | Not started |
| 7 | Desktop boot and wrap-up | `pc-config.json`, `pc.css`, `pc.js`, generated `pc.html`, docs, changelog | Not started |
| R | Register in the hub | Same steps as the earlier new games (TODO QI-12-R) | Not started |
