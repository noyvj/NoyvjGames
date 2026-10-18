# Trade Empire: LA-8 notes (drafted 2026-10-18)

Steps are in `local-ai/incoming/trade-empire.txt` (a header line only, lint: 0 problems). 7 open items labelled `[local AI: after split]`.

## A list (relabel `[local AI: yes]`)
None.

## B list (chains)
None.

## C list (not for the local AI)
The map is one `<canvas id="map-canvas" width="620" height="450">` that `render_map()` (`trade_mapview.py`) clears and redraws completely on every render, which runs once a second from `tick()`. Anything that sits on, over or inside it (zoom, pan, drawing a route, box select, a drop target for a dragged ship, a pinch) has to be rebuilt in canvas coordinates, with its own hit testing, and none of that exists today. That is the same task type (gestures and pan/zoom over a redrawn picture) that failed in earlier audits, and the canvas cannot be checked by the fake DOM tests. All seven items are also vague about what is new game behaviour.

| Item | Label | Reason |
|------|-------|--------|
| R4-PE-5 ship minds | `[Claude: design]` | A name and a "quirk" per automated ship, and a collection of all of them: the quirks are new game rules (they must change trade numbers without luck), and they overlap with the existing Fleet Captains (four captains with perks, `trade_captains.py`). Needs a decision on how minds and captains differ before steps can be exact. |
| R4-PE-6 low-poly galaxy view | `[Claude: art]` | An optional rotating low-poly 3D view of colonies and lanes: Three.js scene, camera and art, plus the 3D loading rules the other 3D game (Continuum) has. Not a small step. |
| R4-TEPC-1 full-window star chart, zoom, pan, draw a route | `[Claude: design]` | Wheel zoom and drag pan on a canvas that is cleared every second, plus a click-and-drag to "draw a new route". Routes are not drawn by the player today (a route is a ship's departure from a colony to another), so what drawing one means is undefined. |
| R4-TEPC-4 drag ships from the captains list onto routes | `[Claude: design]` | Drag and drop from a DOM list onto canvas routes, with a profit-per-trip preview; needs canvas hit testing and a rule for what assigning a ship to a route does (ships are loaded and sent by hand or automated, not assigned). |
| R4-TEPC-5 box-select ships on the map | `[Claude: design]` | Needs selected-ship state, a shared order and a drag rectangle on the canvas; "give a shared order" is not a verb the game has. |
| R4-TEMO-1 portrait map with two-tap routes and a bottom sheet | `[Claude: design]` | Phone layout, canvas taps, a route-creation flow and a bottom sheet: gesture and sheet work failed in earlier audits. |
| R4-TEMO-6 pinch zoom and double-tap centre | `[Claude: design]` | A pinch needs a zoom/offset applied inside `render_map()` and in every `trade_mapdraw.py` position helper, and the page script would have to tell Python the new view through a new exposed function. Gesture work over a redrawn canvas; also best done together with R4-TEPC-1 so the map has one zoom model. |

| Item | Decision | Steps |
|------|----------|-------|
| R4-PE-5 | C | 0 |
| R4-PE-6 | C | 0 |
| R4-TEPC-1 | C | 0 |
| R4-TEPC-4 | C | 0 |
| R4-TEPC-5 | C | 0 |
| R4-TEMO-1 | C | 0 |
| R4-TEMO-6 | C | 0 |

Totals: A 0, B 0, C 7.
