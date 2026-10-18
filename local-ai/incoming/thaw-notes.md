# Thaw: LA-8 notes (drafted 2026-10-18)

Steps are in `local-ai/incoming/thaw.txt` (lint: 0 problems). 8 open items labelled `[local AI: after split]`.

## A list (relabel `[local AI: yes]`)
None.

## B list (chains)
- R4-THPC-1 (2 steps): shared time cursor. The four regions already have four mini graphs on the page at once (`#graph`, `#b-graph`, `#c-graph`, `#d-graph`, each with its own hover and arrow-key crosshair from `graph-crosshair.js`). Interpretation, stated in the steps: the item's "four panes" are those four existing cards, so the steps add only the sharing and change no layout. Step 1 pulls the cross-line-and-dot code out of `show()` into `place()`/`unplace()` (behaviour unchanged, a static test); step 2 adds `syncOthers()`, which places the cursor on the other graphs at the same round (nearest point, because each graph keeps at most 80 points and labels read "Round N: ..."), and a browser test. Only the graph being read keeps its text readout, so a screen reader is not spoken to four times. Pure page script, no Python, no save, nothing timed.

## C list (not for the local AI)
| Item | Label | Reason |
|------|-------|--------|
| G-10 full keyboard and screen-reader play | `[Claude: design]` | Everything concrete is already built (aria-live round summary, mini-graph labels and arrow-key readout, focus rings). What is left is the audit itself: playing the whole game with the keyboard only and listing what fails. The fixes are unknown until then, so there is nothing to write as exact steps; a human or Claude has to run the audit first. |
| GG-3 Station Upgrade skill tree | `[on hold]` | The TODO says it needs W-3 and GG-2; it also needs the owner's choice of upgrades, costs and how finishing a mode earns research credit. |
| R4-PT-1 drone fleet | `[Claude: design]` | Low-poly drones you build, name and upgrade, each upgrade a wiring puzzle: new art, a new puzzle and new save data. |
| R4-PT-2 field team missions | `[Claude: design]` | A helper mode with its own rules, targets and retry logic; also changes how a region fails or recovers. |
| R4-THPC-2 pattern markers and clickable legend | `[needs you]` | There is no single chart with a line per region to put a legend on: each region has its own mini graph, and the pattern lines and end markers (G-14) already exist behind the "graph patterns" setting. Say whether to build a new combined chart (new drawing code and layout) or to let a legend show and hide the four region cards. |
| R4-THPC-6 wheel zoom on the graph | `[needs you]` | A bare mouse wheel over a 120-px graph would trap page scrolling; Aftermath's map uses Ctrl+wheel for that reason. Also each region draws its own graph and the crosshair labels and `data-pts` count rounds from the first, so a "last 10 rounds" window needs a decision (button, Ctrl+wheel or plain wheel) before it can be cut into steps. |
| R4-THMO-6 pinch to overlay two graphs | `[Claude: design]` | A two-finger gesture that merges two graphs and shades the gap: gesture work failed in earlier audits and needs a combined chart that does not exist yet. |

| Item | Decision | Steps |
|------|----------|-------|
| G-10 | C | 0 |
| GG-3 | C | 0 |
| R4-PT-1 | C | 0 |
| R4-PT-2 | C | 0 |
| R4-THPC-1 | B | 2 |
| R4-THPC-2 | C | 0 |
| R4-THPC-6 | C | 0 |
| R4-THMO-6 | C | 0 |

Totals: A 0, B 1 item (2 steps), C 7.
