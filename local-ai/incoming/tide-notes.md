# Tide: LA-8 batch 1 (session s1, 2026-10-18)

Steps are in `local-ai/incoming/tide.txt`: 15 lines (1 single item plus 14 steps in 3 chains), lint reports 0 problems. Everything was
built and its tests run in a scratch copy of `games/tide` first; the whole Tide suite passed there (719 passed, `test_wiring_oct8.py`
deselected because it needs files outside the game folder).

## A (relabel `[local AI: yes]`)
| Item | Line | Why it is one step |
|------|------|--------------------|
| R4-TI-2 managed retreat | `R4-TI-2` | Managed retreat already exists (`managed_retreat()`); the item adds the three viewpoints. One method (`retreat_voices`) that writes three ticker lines, plus one test file: about 25 changed lines. |

## B (split)
| Item | Chain | Steps | What the chain builds |
|------|-------|-------|-----------------------|
| R4-TI-4 seaweed farms | `chain:R4-TI-4` | 6 | up to 6 farms (cost 40, soak up 0.6 acidity a season, upkeep 2 funds a season), `seaweed_farms` saved only when not 0, an invest-style row with a Plant button, lines in the acidity and funds breakdowns |
| R4-PI-12 wave bench | `chain:R4-PI-12` | 4 | tide and surge sliders plus a phase slider, combined peak = sqrt(a^2 + b^2 + 2ab cos phase), a session "settings tried / highest peak found" line |
| R4-TIPC-8 season filmstrip | `chain:R4-TIPC-8` | 4 | a row of buttons for the last 12 seasons under the existing look-back slider; clicking one calls the existing `scrub_to` |

## C (no steps written)
| Item | Label | Reason |
|------|-------|--------|
| GD-2 Harbor Charter | `[Claude: wire the shared skill tree]` | needs `shared/skill-tree.js` and its Python mirror wired through `boot.js`, plus the Charter Mark earn rates, which are not given. The "(needs W-3)" in the item is stale: W-3 is already ticked. |
| GD-10 Harbor Trials | `[Claude: wire the shared level select]` | needs `shared/level-select.js`, a new `levels.json` (sw.js and the offline manifest) and the par scores and stars, which are not given. "(needs W-1)" is stale: W-1 is already ticked. |
| R4-PI-1 Lighthouse Night | `[Claude: look and art]` | a dark low-poly night scene; overlaps shared/night-mode.js |
| R4-PI-2 rescue boats | `[needs you]` | the "choose which gate or light to open" choice, its outcomes and the restore rule are undefined |
| R4-PI-7 marine radio story | `[Claude: story writing]` | |
| R4-PI-10 harbour mysteries | `[needs you]` | which logs, causes and clues are undefined |
| R4-PI-15 harbour cross-section | `[Claude: layered SVG art]` | |
| R4-PI-16 Europa dome harbour | `[needs you]` | a new scenario with its own numbers and look |
| R4-PI-22 wreck sites | `[needs you]` | "revealed by survey" has no existing survey mechanic; the salvage items are content |
| R4-PI-24 chart-reading puzzles | `[needs you]` | the puzzle generator (bearings, soundings) needs a design |
| R4-PI-25 boatyard | `[needs you]` | a sorting game with a shelf of logs: new mechanic and content |
| R4-PI-29 low-poly 3D coast | `[Claude: 3D]` | |
| R4-TIPC-1 place a seawall by clicking the coast | `[Claude: map UI and placement model]` | hover range preview on a tile grid that is rebuilt on every render, and a placement model that does not exist (adaptation is a count today) |
| R4-TIPC-6 then/now divider | `[Claude: drag]` | a draggable wipe |
| R4-TIMO-1 drag a seawall icon | `[Claude: drag]` | |
| R4-TIMO-4 double-tap zoom | `[Claude: gesture]` | |
| R4-TIMO-6 swipeable meter cards | `[Claude: swipe]` | |
| R4-TIMO-8 tap-and-hold bottom sheet | `[Claude: hold gesture and sheet]` | |

## Table
| Item | Decision | Steps |
|------|----------|-------|
| GD-2 | C | 0 |
| GD-10 | C | 0 |
| R4-TI-2 | A | 1 |
| R4-TI-4 | B | 6 |
| R4-PI-1 | C | 0 |
| R4-PI-2 | C | 0 |
| R4-PI-7 | C | 0 |
| R4-PI-10 | C | 0 |
| R4-PI-12 | B | 4 |
| R4-PI-15 | C | 0 |
| R4-PI-16 | C | 0 |
| R4-PI-22 | C | 0 |
| R4-PI-24 | C | 0 |
| R4-PI-25 | C | 0 |
| R4-PI-29 | C | 0 |
| R4-TIPC-1 | C | 0 |
| R4-TIPC-6 | C | 0 |
| R4-TIPC-8 | B | 4 |
| R4-TIMO-1 | C | 0 |
| R4-TIMO-4 | C | 0 |
| R4-TIMO-6 | C | 0 |
| R4-TIMO-8 | C | 0 |

## Things to know
- `index.html` is at 62,964 bytes against a 64,000 byte cap (16,000 tokens). The three chains add about 900 bytes (63,891 measured), so
  they just fit; nothing else can be added before the cap is raised.
- `tests/test_oct9_pass.py::test_settings_and_page_carry_the_plain_label_pieces` pins exactly three `data-plain="` attributes in
  `index.html`; the seaweed step says not to add one. This is not in the CLAUDE.md map.
- The chains touch some of the same lines (`game.py` listener tuples, `tests/conftest.py` before `INITIALLY_DISABLED_IDS`,
  `tide_flavour.py` end of file): trivial conflicts if more than one is merged.
- R4-TI-4 adds acidity relief at a price, so it does not change the delayed-consequence lesson: fish yield still follows accumulated
  acidity on its lag. Nothing in the existing core-number tests moves because a game with 0 farms is unchanged.
- R4-TIPC-8 reuses the existing scrubber (`scrub_to`, read-only look back), so a click never changes the run.

## Where the CLAUDE.md map was wrong or missing something
- The map is accurate for what I used (the `tide_*.py` file map, the late-bound names and the ids). Missing: the fake DOM
  `getElementById` returns None for a missing id (so new render code must check `is not None`), and the pinned `data-plain` count above.
- "managed retreat ... move the lowest row inland" (R4-TI-2) already exists in `tide_model_town.py`; the TODO text reads as if it were
  new. The TODO item could be reworded to "add the three viewpoints".
