# Dead Reckoning: LA-8 notes (s3b, drafted 2026-10-19)

Steps are in `local-ai/incoming/dead-reckoning.txt` (lint: 0 problems). 11 open items labelled `[local AI: after split]`.

## A list
- LA-12 relabel `[local AI: yes]`: a one-line test fix. I ran the test on the Mac and found the cause: it is a bug in the test helper `_swipe`, not in `swipe-legs.js`. After the undo, the third leg card sits under the sticky bottom dock (`elementFromPoint` returns `#undo-button`), so the touch never reaches the card. Scrolling the card to the middle of the screen first fixes it (checked by hand: the swipe then removes leg 3).

## B list (chains)
- R4-DEPC-5 (2 steps): hold R and drag to measure distance and bearing. Shown as text in a new `#measure-readout` line; no line is drawn on the chart because the engine rebuilds the SVG on every move (and a line in the Desktop chart window would not scroll with it). A drag with R held does not set the ruler point (the click after the drag is swallowed).
- R4-DEPC-3 (3 steps): hover readout. Engine `render.zone_readouts` (charted numbers only, tide at the chart's start hour), view key `sea`, then `#chart-readout` plus a mouse-move handler. The numbers shown are the charted ones, so the truth is not leaked.

Note: both chains define a helper `chartXY` in `app.js` (duplicate name, same body). Whichever chain is merged second must drop its copy (a trivial merge fix). `index.html` has no size cap test in this game.

## C list (not for the local AI)
| Item | Label | Reason |
|------|-------|--------|
| R4-DEPC-2 wheel zoom and drag pan | `[Claude: design]` | Zoom and pan over the SVG chart that the engine rebuilds on every move; in this task type earlier local-AI work failed. Needs a decision on where the transform lives (holder wrapper vs viewBox) and how it works in the Desktop chart window. |
| R4-DEPC-4 right-click menu | `[Claude: design]` | "Drop a fix mark" and "Add a waypoint" are not defined by the game (the only point tool is the ruler point; a waypoint has no heading, speed or hours). Needs the owner's meaning. |
| R4-DEPC-7 editable plan table | `[Claude: design]` | A second layout for the leg editor with tab order, live redraw and the two-ship and Watch modes; large and mostly a design question. |
| R4-DEMO-2 pinch zoom and pan | `[Claude: design]` | Two-finger gesture on the rebuilt SVG; same failure type as R4-DEPC-2. |
| R4-DEMO-3 long-press to drop a fix mark | `[Claude: design]` | A tap already sets the ruler point; what a "fix mark" is, and what long-press adds, is not defined. |
| R4-DEMO-6 portrait chart with plan bottom sheet | `[Claude: design]` | Bottom sheets failed in earlier audits; a whole alternate phone layout. |
| R4-DEMO-8 draggable floating leg editor | `[Claude: design]` | Drag of a floating card over the chart and its snap points; layout design. |
| R4-DEMO-9 landscape full-screen chart | `[Claude: design]` | Full-screen chart with a floating editor is a new landscape layout; undefined where the dock, HUD and result card go. |

| Item | Decision | Steps |
|------|----------|-------|
| LA-12 | A | 1 |
| R4-DEPC-2 | C | 0 |
| R4-DEPC-3 | B | 3 |
| R4-DEPC-4 | C | 0 |
| R4-DEPC-5 | B | 2 |
| R4-DEPC-7 | C | 0 |
| R4-DEMO-2 | C | 0 |
| R4-DEMO-3 | C | 0 |
| R4-DEMO-6 | C | 0 |
| R4-DEMO-8 | C | 0 |
| R4-DEMO-9 | C | 0 |

Totals: A 1, B 2 items (5 steps), C 8.
