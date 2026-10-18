# Chronicle: LA-8 notes (drafted 2026-10-18)

Steps are in `local-ai/incoming/chronicle.txt` (lint: 0 problems). 19 open items labelled `[local AI: after split]`.

## A list (relabel `[local AI: yes]`)
- R4-CLPC-6 (arrow keys move a card along the timeline, Enter places it): one block in `onKey` in `app.js`, one help line in `index.html`, one browser test. Interpretation, stated in the step: with a card picked up, an arrow key moves focus onto the first open slot (or the last for Left/Up); the existing slot-arrow code then moves between slots and Enter on a focused slot already places the card (slots are buttons). The owner may have meant something different (moving a placed card one slot at a time); the step says exactly what it builds.

## B list (chains)
- R4-CLP-21 (4 steps): same year around the world. Lists only moments the player has already learned (as the Archive does), so no puzzle answer leaks; engine function, action `year` (read-only, no save change), markup, page script plus a browser test that learns one moment through `window.pyodide.runPython`. With one set today the panel shows one set's moments; it picks up new sets without change.
- R4-CLP-23 (7 steps): puzzle shelf. A bookmark is `{name, set, section, round}` because a puzzle is a pure function of those (so replaying it is the existing `start` action). At most 20, names up to 30 characters, same name replaces. New save key `bookmarks` written only when non-empty and cleaned one item at a time on load, schema stays 3. Engine (state, save/remove, play, save/load, view key), then markup, then the drawing code, then wiring plus a browser test.

Notes for the audit: both chains add a toolbar button, a panel and a KeyboardShortcuts `panels` pair in `index.html`, so they touch the same lines; the second to merge needs a trivial conflict fix. The `bookmarks` and `year` additions are not in the CLAUDE.md "view keys / actions" lists (the steps do not edit CLAUDE.md); add them when merging.

## C list (not for the local AI)
| Item | Label | Reason |
|------|-------|--------|
| CH-11 presidents set in full | `[needs you]` | Three live sources per claim read from the web, plus the owner's own review and sign-off of the set. |
| CH-12 history of food and Ancient Greece sets, set picker | `[Claude: live web data]` | Authoring two whole sets needs sources read from the web (three per claim, two institutions); the set picker already exists. |
| CH-13 polish, accessibility pass, hub registration, Desktop boot | `[Claude: shared]` | Hub card, `sw.js`, `shared/site-settings.js`, `pc.html` and the backend report table are all outside the game folder (and `scripts/generate-last-updated.py` has to be re-run). |
| R4-CLP-3 archivist character | `[needs you]` | A character and an art direction (no generated images allowed) for restoring a shelf; the look is the owner's call. |
| R4-CLP-4 dark low-poly vault | `[Claude: art]` | Code-drawn 3D-style scene; art and layout, not an exact step. |
| R4-CLP-8 world mosaic | `[needs you]` | The owner's note asks for several era maps and a one-location timeline map; map art and the tile-per-solve rules are open design. |
| R4-CLP-10 logic-grid puzzle | `[Claude: design]` | A new mode and puzzle generator (clue wording from claims, a solver proving uniqueness, a pinned fixture and `SEED_VERSION`). |
| R4-CLP-12 branching witness letters | `[needs you]` | Authored story content for a real documented person, each branch needing sourced claims. |
| R4-CLP-18 Historian's Tree | `[Claude: design]` | A big skill tree gating tools and views, with the owner's note about unlocking "classified" views; the unlock rules are undecided. |
| R4-CLP-22 diplomat's seat | `[needs you]` | Authored treaty content with each delegation's documented position and sources. |
| R4-CLP-24 low-poly dig site | `[Claude: art]` | Code-drawn scene plus a layer-per-era mechanic. |
| R4-CLPC-1 timeline lanes | `[Claude: design]` | Draggable lane reordering over the timeline board; drag work and board re-layout failed in earlier audits. |
| R4-CLPC-3 free-canvas cause web | `[Claude: design]` | Free drag, mouse-drawn threads and scroll-pan over an SVG board that is rebuilt on every move. |
| R4-CLMO-1 vertical timeline with tray | `[Claude: design]` | A whole alternate layout for phones, tap targets and a bottom tray. |
| R4-CLMO-4 long-press sources sheet | `[Claude: design]` | Long-press plus a bottom sheet; bottom sheets and gesture timing failed in earlier audits (and the rules forbid timers for long-press). |
| R4-CLMO-5 century ruler | `[Claude: design]` | A draggable thumb that scrolls a long timeline; drag gestures failed in earlier audits. |

| Item | Decision | Steps |
|------|----------|-------|
| CH-11 | C | 0 |
| CH-12 | C | 0 |
| CH-13 | C | 0 |
| R4-CLP-3 | C | 0 |
| R4-CLP-4 | C | 0 |
| R4-CLP-8 | C | 0 |
| R4-CLP-10 | C | 0 |
| R4-CLP-12 | C | 0 |
| R4-CLP-18 | C | 0 |
| R4-CLP-21 | B | 4 |
| R4-CLP-22 | C | 0 |
| R4-CLP-23 | B | 7 |
| R4-CLP-24 | C | 0 |
| R4-CLPC-1 | C | 0 |
| R4-CLPC-3 | C | 0 |
| R4-CLPC-6 | A | 1 |
| R4-CLMO-1 | C | 0 |
| R4-CLMO-4 | C | 0 |
| R4-CLMO-5 | C | 0 |

Totals: A 1, B 2 items (11 steps), C 16.
