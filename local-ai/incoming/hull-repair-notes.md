# Hull Repair: LA-8 notes (s3b, drafted 2026-10-19)

`local-ai/incoming/hull-repair.txt` holds no steps (header comment only, lint: 0 problems). 4 open items labelled `[local AI: after split]`; all four are C.

## A list
None.

## B list
None.

## C list (not for the local AI)
| Item | Label | Reason |
|------|-------|--------|
| R4-HRPC-1 zoomable, pannable station cutaway with hover and click | `[Claude: design]` | Wheel zoom, drag pan and hover on `render.station_svg` (a single SVG string the page replaces) is the zoom/pan task type that failed in earlier audits, and the click-to-open and hover status need ids on every room that the SVG does not carry yet. |
| R4-HRMO-3 two-finger pan, pinch zoom, double-tap fit for 9 by 9 boards | `[Claude: design]` | Multi-touch on the board SVG, which the engine rebuilds after each move (`board-holder` also owns the finger-drawing pointer events, so a second finger must not start a line). |
| R4-HRMO-4 vertical scroll of decks with room thumbnails | `[Claude: design]` | Thumbnails of boards need a new small renderer in `render.py` (the rooms view carries only names, status and size) and a layout decision for phones. |
| R4-HRMO-6 drag backward to trim a line, a soft tick per cell | `[Claude: design]` | Looks already built, so Claude should verify and tick: `play.py`'s docstring says "dragging back over your own line trims it", `tests/test_ai_hrpc4.py` checks the engine moves forward and back, and `app.js` `onPointerMove` calls `HR_Haptics.tick()` for every cell moved. |

| Item | Decision | Steps |
|------|----------|-------|
| R4-HRPC-1 | C | 0 |
| R4-HRMO-3 | C | 0 |
| R4-HRMO-4 | C | 0 |
| R4-HRMO-6 | C | 0 |

Totals: A 0, B 0, C 4.
