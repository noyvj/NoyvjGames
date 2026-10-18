# Robot Script: LA-8 notes (s3b, drafted 2026-10-19)

Steps are in `local-ai/incoming/robot-script.txt` (lint: 0 problems). 4 open items labelled `[local AI: after split]`.

## A list (relabel `[local AI: yes]`)
- R4-RSPC-2 step debugger: most of it already exists in the page (Step button, the highlighted current line through `markNode`, breakpoints from R4-RSPC-3). What is missing is F10 and a state line, so it is one small step: a `#debug-line` showing "Robot at column, row, facing, holding" from the run frame (`[x, y, d, carry, ...]`, all in the view already), and an F10 key that calls `onStep`. The "side panel" is this one line under the run line (no window, so no `pc-config.json` change).

## B list (chains)
- R4-RSPC-5 (3 steps): text view. Uses the existing `dsl.to_text` and `dsl.parse`: step 1 engine (`set_text {text}` action with `ed.load`, `program.text` view key, undoable, no save change); step 2 a `<details id="text-view">` with a textarea (one line per list, e.g. `main: F F rep 3 { F L }`) and an Apply button; step 3 Apply-and-run button and Ctrl+Enter. Interpretation: "numbered lines" are the game's own one-line-per-routine text form (main, A, B), not one numbered line per instruction, because the engine's text parser reads that form and nothing else.

## C list (not for the local AI)
| Item | Label | Reason |
|------|-------|--------|
| R4-RSPC-1 drag blocks from a palette, reorder, drop inside repeat | `[Claude: design]` | Drag and drop onto nested list gaps is a task type that failed in earlier audits (native drag-and-drop is also hard to test); the list is rebuilt after every edit. |
| R4-RSMO-1 bottom keypad with long-press reorder | `[Claude: design]` | Looks already built: `tests/test_ai_keypad.py` pins the phone keypad CSS and the grip in `app.js` (comment R4-RSMO-1, `robotScriptSwipeDelete`, the timer-free long-press). Claude should verify it on a phone width and tick the item rather than queue steps. |

| Item | Decision | Steps |
|------|----------|-------|
| R4-RSPC-1 | C | 0 |
| R4-RSPC-2 | A | 1 |
| R4-RSPC-5 | B | 3 |
| R4-RSMO-1 | C | 0 |

Totals: A 1, B 1 item (3 steps), C 2. No `index.html` size cap test exists in this game.
