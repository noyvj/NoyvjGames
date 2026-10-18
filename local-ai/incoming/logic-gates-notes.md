# Logic Gates: LA-8 notes (s3b, drafted 2026-10-19)

Steps are in `local-ai/incoming/logic-gates.txt` (lint: 0 problems). 5 open items labelled `[local AI: after split]`.

## A list
None.

## B list (chains)
- R4-LGPC-8 (3 steps): timing diagram for sequence levels. Step 1 is the engine: action `timing {on}` (a module global `timing_on`, nothing saved), view key `timing` = `{steps, rows:[{name, kind, bits}]}` built by running the level's script through a fresh `Sim` on the player's own circuit. Step 2 is the markup (toggle button, `#timing-panel`, `pc-config.json` window and menu entry) with a small browser test. Step 3 is the script (`renderTiming`, a table of 0/1 digits, so never colour alone). Interpretation stated in the steps: "each wire" is each switch and each lamp (not every internal wire), and the diagram is shown only on script ("seq") levels; elsewhere it says there is nothing to chart. The browser test only checks the no-script path, because getting a sequence level open in the browser needs many solved levels; the table content is covered by the Python test on Latch Up.
- No `index.html` size cap test exists in this game.

## C list (not for the local AI)
| Item | Label | Reason |
|------|-------|--------|
| R4-LGPC-1 drag a wire pin to pin | `[Claude: design]` | Needs a live preview line and snapping over the SVG board, which the engine rebuilds on every move; drag on the board is a task type that failed in earlier audits (the existing `pick` tap path is the engine side). |
| R4-LGPC-2 wheel zoom, pan and minimap | `[Claude: design]` | Zoom and pan of the rebuilt SVG board plus a minimap; same failure type, and the board width logic (`svg_width`) is involved. |
| R4-LGPC-4 chip right-click menu with Open inside | `[Claude: design]` | Needs an engine view of a built chip's own circuit (rendering a reference circuit in a second board), a context menu, and Duplicate/Delete semantics for chips already wired; too many undefined decisions for exact steps. |
| R4-LGMO-3 pinch zoom, two-finger pan, double-tap fit | `[Claude: design]` | Multi-touch gestures on the SVG board; same failure type as R4-LGPC-2. |

| Item | Decision | Steps |
|------|----------|-------|
| R4-LGPC-1 | C | 0 |
| R4-LGPC-2 | C | 0 |
| R4-LGPC-4 | C | 0 |
| R4-LGPC-8 | B | 3 |
| R4-LGMO-3 | C | 0 |

Totals: A 0, B 1 item (3 steps), C 4.
