# Picture Grid (slug `picture-grid`, TODO QI-12) - Groundwork Plan

Source: the Quick ideas round (A12), owner-approved: "nonograms where each solved picture goes into a gallery you can browse." Checked against `PLAYER-PROFILE.md`: Flow Free style logic puzzles, collecting, a sticker book or shelf for collections, short wins forming a bigger picture, calming perfectionism-friendly play, no timers, nothing lost. Personal project, no BCM tag, working title.

Pitch: fill in a grid from the number clues on its rows and columns, and every solved picture hangs in a dark gallery of space, robot and machine scenes.

## 1. Concept
- You are the new hand at a closed gallery of small pictures on a quiet station (invented: the Long Gallery). Each frame is blank until you solve it. Row and column numbers say how many filled cells run together; deduce the picture, and it appears in full light and takes its place on the wall.
- 2-minute session: one 5x5 or 8x8 frame. 20-minute session: a 15x15 or two 10x10 frames.
- Look: dark wall, faceted low-poly frames, cells as large squares; filled cells use a pattern and a glyph in addition to colour. A solved picture gets a two- or three-tone final tint. Quiet tone; each picture has a one-line caption (optional).

## 2. Core rules (pure functions)
- A frame is a grid from 5x5 to 15x15. Each row and column has a clue list of block lengths. The player marks cells filled, empty (a dot) or unknown. A frame is solved when every row and column matches its clue.
- Optional assists in settings: Check mistakes (marks wrong cells; off by default, never forced), Auto-dot finished lines, Row focus highlight. Drag to fill many cells; tap with a mode switch; keyboard cursor.
- Nothing can fail. Clear a line or the frame freely.

## 3. Content size
60 pictures in six galleries of 10: Instruments (5x5), Small Machines (8x8), Robots (10x10), Station Rooms (10x10 and 12x12), Deep Sky (12x12 and 15x15), The Long Wall (15x15 finale, each with a mix of sizes). Pictures are hand-authored bitmaps (no generated images). Gallery n+1 opens at 6 of 10; any order inside.

## 4. How correctness is PROVED
- Dev tool `tools/solve.py` has two solvers: (a) a line-logic solver (the usual overlap and edge rules, iterated to a fixpoint) and (b) an exhaustive counter. Tests assert every picture has exactly ONE solution (counter) and that the line-logic solver alone finishes it, so a human never has to guess. Pictures that need guessing are rejected by the tool and redrawn.
- The stored bitmap equals the solved grid; clue generation is a pure function of the bitmap.
- Hint rungs use the line solver's next forced deduction, so hints are always logically justified. Determinism: no clock, no random.

## 5. Collection and 100%
- The Gallery: a wall of 60 frames, each dark until solved and then shown as a small picture with its caption and a "solved in" count of moves (for the player's eyes only). Tapping a picture opens it large; a Slideshow button steps through the ones you own. 100% = all 60 hung. States only go up.

## 6. Goals and hint ladder
- Three always-visible goals, any order, with bars. Stats strip: Pictures hung, Cells filled, Galleries done, Hints. The tally counts fills, dots and clears.
- Ladder (first rung asks "Would you like a suggestion?"): Nudge (names a row or column that has something forced), Hint (shows the forced cells in it as ghosts), Answer (fills that whole line, with a button). Free, on request.

## 7. Achievements (14)
First Frame; Ten Hung; Thirty Hung; Sixty Hung; Small Hands (all of Instruments); Machine Shop; Robot Row; Station Rooms; Deep Sky Done; The Long Wall; Big One (a 15x15); Clean Lines (10 pictures with no hint); Slow Light (open the Slideshow); Ten Thousand (fill 10,000 cells).

## 8. Real-world facts
None, fiction. The About page notes the history of nonograms (Non Ishida and Tetsuya Nishio, Japan, 1987-88) as text with sources named and read date shown on Sources, if the live read from the Wikipedia REST service is available (bundled copy fallback).

## 9. Reuse
Grid renderer, drag input and solver-in-`tools/` pattern from Hull Repair; gallery panel in the style of Evidence Hunt's notebook; shared `level-select.js`, `hint-ladder.js`, `goals-panel.js`, `opening-screen.js`, `confirm-dialog.js`, `info_page.py`, `announcer.js`, `pc-shell.js`.

## 10. Milestones
| # | Milestone | Content |
|---|-----------|---------|
| 1 | Engine and solvers | Clue generator, line-logic solver, exhaustive counter, gallery 1 (10 pictures) with proofs |
| 2 | Frame UI | SVG grid, drag fill and dot, keyboard cursor, assists, save contract. Playable slice |
| 3 | Galleries 2-3 | 20 more pictures, the Gallery wall and large view, gating |
| 4 | Galleries 4-6, hints, goals | 30 more pictures (60), hint ladder, three-goals strip, slideshow. First complete game |
| 5 | Standard kit | Opening screen, tutorial, About with Sources, What's New, keyboard help, confirm dialogs, light theme, accessibility |
| 6 | Achievements | 14 achievements, panel and toast, manifest, reachability test |
| 7 | Desktop boot and wrap-up | `pc-config.json`, `pc.css`, `pc.js`, generated `pc.html`, docs, changelog |

## 11. Open questions for the owner
1. Mono pictures with a final tint, or true multi-colour nonograms for the last gallery? Default: mono with tint (clearer, easier to read on dark).
2. Should Check mistakes be on by default for the first gallery? Default: off, offered once in the tutorial.
