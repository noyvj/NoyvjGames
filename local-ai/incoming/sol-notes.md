# SOL: LA-8 notes (drafted 2026-10-18)

Steps are in `local-ai/incoming/sol.txt` (lint: 0 problems). 19 open items labelled `[local AI: after split]`.

## A list (relabel `[local AI: yes]`)
None. The only item the TODO calls small, R4-PS-10, needs the achievements catalogue, its checks and two pinned catalogue-size tests, so it is a 2-step chain.

## B list (chains)
- R4-PS-10 (2 steps): six riddle achievements, three per step. Conditions are live-derived like the first achievement batch (they use planet_state). Raises the `<= 40` cap in `tests/test_achievements.py` and the `== 36` count in `tests/test_scarcity.py` (36 -> 39 -> 42).
- R4-SOMO-6 (2 steps): battery saver. Engine first (tick throttle after `_ghost_tick()`, localStorage key `sol-battery-saver`), then the settings checkbox plus CSS plus a browser test. The simulation still runs every tick; only the display and check work runs once a second.
- R4-PS-11 (7 steps): sticker album. Stickers are 34 lifetime ids (`World:kind`), stored in a new save key `stickers_earned` that is written only when non-empty and validated against `STICKER_IDS` on load. The item mentions ships; SOL has no ships, so only buildings (Auto-Miner, Recycler, Sky City), trade routes and terraformed worlds get stickers.
- R4-PS-4 (5 steps): maintenance robot log. Five lines, shared across worlds with the world name filled in, unlocked from live state (arrived, generator, recycler, route, terraformed); nothing is saved. The panel shows the world you are on.

Both panel chains (PS-11 and PS-4) edit the same places (`index.html` toolbar, `pc-config.json`, `shortcuts.js`, `tests/conftest.py` ELEMENT_IDS, `sol_runstate.py` LIVE_NAMES, `sol_run.py`, `sol_handlers.py`, `game.py`), so expect trivial merge conflicts if both are audited together. `index.html` has under 900 bytes of headroom under its 21,500-token cap (`tests/test_file_sizes.py`); the three additions (battery row, two panels) are about 700 bytes together, so the next index.html change will need a cap review.

## C list (not for the local AI)
| Item | Label | Reason |
|------|-------|--------|
| R4-SO-2 orbital depot | `[Claude: design]` | Shared storage across worlds with different resources: how much each unit holds, how draws are priced, and how it interacts with trade routes are all economy-design choices that change `sol_sim.py` and `sol_econ.py` balance. |
| R4-SO-3 signature buildings | `[needs you]` | Eight special rules (one per world) with balance numbers; the Venus example changes ecology decay, which is core sim. |
| R4-SO-4 research forks | `[Claude: design]` | Choose-one nodes with a swap fee touch the research tree tables, `_clean_researched_nodes()` and saves. |
| R4-SO-11 alternate openings | `[needs you]` | Starting kits and unlock orders for Mars/Venus starts are design decisions, and the game assumes Earth start everywhere. |
| R4-SO-13 rescue worlds | `[needs you]` | Needs authored puzzle scenarios (starting states, building limits, targets). |
| R4-PS-3 three ways to finish | `[needs you]` | Three goal ladders and badges, all content decisions. |
| R4-PS-9 express opening | `[needs you]` | Pacing numbers for a five-minute second system; touches the first-run balance. |
| R4-PS-12 Mastery web | `[Claude: design]` | Huge tree, no refunds, fed by achievements and exploration: a new save structure and many tuned nodes. |
| R4-PS-22 Other Stars | `[Claude: design]` | Seeded generation of new systems needs a world-data layer the game does not have (worlds are fixed in `sol_rules.py`). |
| R4-PS-24 colony tales | `[Claude: design]` | Three-sentence stories from the log need authored text templates and a choice of which events count; prose quality is not something to leave to the local model. |
| R4-PS-29 tidy base mode | `[Claude: design]` | A per-world map with arranged buildings is a new grid UI and engine with its own save data. |
| R4-SOPC-2 docked windows | `[Claude: shared]` | Snapping and resizing windows is done by the shared Desktop shell (`shared/pc-shell.js`), which the local AI may not touch. |
| R4-SOPC-5 Ctrl+K palette | `[Claude: shared]` | Needs to reach worlds, windows, settings and research nodes across both pages and the Desktop shell; keyboard guard rules and the research tree make it hard to write as exact steps. |
| R4-SOPC-7 star chart zoom and pan | `[Claude: design]` | Pan/zoom on a redrawn chart is a task type that failed in earlier audits; the Overview rebuilds its markup. |
| R4-SOMO-1 world carousel | `[Claude: design]` | Swipe gestures over the whole main screen, one view per world; gesture work failed in earlier audits. |

| Item | Decision | Steps |
|------|----------|-------|
| R4-SO-2 | C | 0 |
| R4-SO-3 | C | 0 |
| R4-SO-4 | C | 0 |
| R4-SO-11 | C | 0 |
| R4-SO-13 | C | 0 |
| R4-PS-3 | C | 0 |
| R4-PS-4 | B | 5 |
| R4-PS-9 | C | 0 |
| R4-PS-10 | B | 2 |
| R4-PS-11 | B | 7 |
| R4-PS-12 | C | 0 |
| R4-PS-22 | C | 0 |
| R4-PS-24 | C | 0 |
| R4-PS-29 | C | 0 |
| R4-SOPC-2 | C | 0 |
| R4-SOPC-5 | C | 0 |
| R4-SOPC-7 | C | 0 |
| R4-SOMO-1 | C | 0 |
| R4-SOMO-6 | B | 2 |

Totals: A 0, B 4 items (16 steps), C 15.
