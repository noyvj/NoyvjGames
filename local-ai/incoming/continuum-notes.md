# Continuum: LA-8 notes (drafted 2026-10-18)

Steps are in `local-ai/incoming/continuum.txt` (lint: 0 problems). 8 open items labelled `[local AI: after split]`.

## A list (relabel `[local AI: yes]`)
None.

## B list (chains)
- R4-COPC-1 and R4-COMO-4 (6 steps, one chain named `R4-COPC-1`, `# replaces:` lists both items): the 3D settlement camera. Both items change the same few variables in `attachDragControls()` in `render3d.js`, and the two-finger tap needs the "last preset used", so they are one chain: (1) wheel zoom with limits 3.5 to 16 and a read-only `ContinuumScene.cameraState()`; (2) browser test for it; (3) right-drag pan on the ground plane (a look-at target limited to +-6, reset by every preset), `contextmenu` suppressed, middle-click auto-scroll suppressed; (4) browser test for the pan with the exact formulas; (5) R4-COMO-4: a two-finger tap (no movement over 12 px, under 400 ms by `event.timeStamp`, never a timer) re-applies the last preset; (6) browser test for it. The 1 to 4 camera presets, the left-drag orbit and the Hamlet overlay (`notifyChange()` is called after every camera move) are kept. Interpretation: the item says "middle-drag orbit", but a press with any button except the right one already orbits, so no new orbit code was written; the middle button just stops the browser's auto-scroll.
  Important for the audit: the header comment of `render3d.js` says nothing in it is covered by pytest because the harness has no WebGL. The static tests only check that the code is present; the browser tests skip when Three.js or WebGL is not available in the headless browser, so a pass may mean "skipped". Claude should run the page live (3D on) before merging this chain and check wheel, right-drag, a touch emulation and the Hamlet view's buttons following the camera.

## C list (not for the local AI)
| Item | Label | Reason |
|------|-------|--------|
| R4-PO-1 Lantern keeper | `[Claude: design]` | A walking helper mode inside the city: new movement, deliveries, residents' needs and stat effects. A whole new mode with its own save data and balance. |
| R4-PO-2 Relic hunt | `[needs you]` | 64 relics (eight per era) need names, descriptions and a rule for what "finding" one in a Look Back view means; creative content and interaction design, and the museum case is a new panel. |
| R4-PO-4 Robot caretakers | `[Claude: design]` | Commissioning and naming robot helpers that each take a job touches the roles, the economy and the save; the models to collect need design. |
| R4-COPC-4 mission-control layout | `[Claude: shared]` | Docked panes with resizable dividers are done by the shared Desktop shell (`shared/pc-shell.js`), which the local AI may not touch. |
| R4-COMO-1 portrait full-screen 3D with a bottom sheet | `[Claude: design]` | Pinch zoom, a tap-a-building sheet and a bottom-sheet gesture over the 3D scene; bottom sheets and gestures failed in earlier audits, and picking a building needs the Hamlet overlay's projection code. Part of it (pinch) could follow the camera chain above once that is audited. |
| R4-COMO-6 low-power 2D view | `[needs you]` | The 2D fallback (`.settlement-visual`), the 2D/3D toggle button and lite mode already exist. What is new is a flat illustrated map with a tap sheet per building: say whether the existing 2D diorama is enough or a new map is wanted (new art). |

| Item | Decision | Steps |
|------|----------|-------|
| R4-PO-1 | C | 0 |
| R4-PO-2 | C | 0 |
| R4-PO-4 | C | 0 |
| R4-COPC-1 | B | 6 (shared with R4-COMO-4) |
| R4-COPC-4 | C | 0 |
| R4-COMO-1 | C | 0 |
| R4-COMO-4 | B | (steps 5 and 6 of the R4-COPC-1 chain) |
| R4-COMO-6 | C | 0 |

Totals: A 0, B 2 items (6 steps in one chain), C 6.
