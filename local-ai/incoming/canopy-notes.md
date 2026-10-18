# Canopy: LA-8 batch 1 (session s1, 2026-10-18)

Steps are in `local-ai/incoming/canopy.txt`: 10 steps in 2 chains, lint reports 0 problems. Both chains were built and run in a
scratch copy of `games/canopy` first; the whole Canopy suite passed there (after `scripts/generate-pc-pages.py`, which `ai.ps1`
runs before every test run), apart from `tests/test_todays_run_browser.py` `[index.html-360-740]`, which already fails on main.

## A (relabel `[local AI: yes]`)
None.

## B (split)
| Item | Chain | Steps | What the chain builds |
|------|-------|-------|-----------------------|
| R4-PC-8 forest floor finds | `chain:R4-PC-8` | 4 | 30 named finds (10 fungi, 10 feathers, 10 old tools) revealed in a fixed order, one per Tend on a fully grown plot; the shelf count lives in localStorage (`canopy_finds_v1`), never in a save (Canopy's meta-progress rule); a "Forest floor finds" panel shows the shelf |
| R4-CAPC-6 seasons scrub bar | `chain:R4-CAPC-6` | 6 | one frame per finished season (last 20: one letter per plot), saved only when not empty, a "Season time-lapse" slider panel with a letter map and legend |

## C (no steps written)
| Item | Label | Reason |
|------|-------|--------|
| R4-CA-1 river | `[needs you]` | where the river runs, what upstream/downstream means on the grid and how much it dries are undefined; it changes growth numbers pinned by four core-number tests |
| R4-CA-2 access roads | `[needs you]` | road placement, the clearing discount and the wildlife split are undefined |
| R4-CA-3 natural regrowth | `[needs you]` | free recovery changes the replant economy and the Pacifist/Scorched challenges and the replant contract; the owner should decide whether it is opt-in |
| R4-PC-1 wildlife rescue | `[needs you]` | the carry-two-taps interaction and the shelter badges need a design |
| R4-PC-2 Night Forest look | `[Claude: look and animals]` | a visual theme plus eight new animals with art and text; overlaps shared/night-mode.js |
| R4-PC-4 Dome Garden (Mars) | `[needs you]` | a new level set with its own rules and numbers |
| R4-PC-5 Valley Map | `[Claude: painted art]` | the map is art |
| R4-PC-6 three mastery paths | `[needs you]` | the goal list of each path is undefined |
| R4-PC-7 forest fog | `[needs you]` | which plots start hidden, what fog hides and how tending clears it are undefined; it lives inside `render_grid()` |
| R4-PC-10 Gothic Hollow | `[Claude: look and levels]` | a new look and level set |
| R4-PC-11 branching ranger story | `[Claude: story writing]` | |
| R4-PC-12 farmer partners | `[needs you]` | request rules and the viewpoints are design |
| R4-PC-14 3D forest view | `[Claude: 3D]` | WebGL/low-poly renderer |
| R4-PC-15 Explorer achievements | `[Claude: achievements]` | ten new achievements break the catalog cap in `tests/test_achievements.py` (`5 <= len <= 40`, Canopy has 32), need story chapters and change the hub-wide totals; the ten definitions are not given |
| R4-PC-18 grove puzzles | `[Claude: new puzzle engine]` | |
| R4-PC-20 cabin cutaway | `[Claude: cutaway art]` | |
| R4-PC-24 three voices | `[Claude: story writing]` | |
| R4-CAPC-2 zoom, pan, minimap | `[Claude: zoom and pan]` | wheel/drag transforms on a grid that `render_grid()` rebuilds every second |
| R4-CAPC-8 drag onto the Seed Vault | `[Claude: drag UI]` | drag gestures fail for the local AI |
| R4-CAMO-1 portrait fill, pinch | `[Claude: gestures]` | |
| R4-CAMO-7 bed-time mode | `[needs you]` | overlaps shared/calm-mode.js and shared/night-mode.js (shared files); "hide numbers except one" needs a decision on which one |

## Table
| Item | Decision | Steps |
|------|----------|-------|
| R4-CA-1 | C | 0 |
| R4-CA-2 | C | 0 |
| R4-CA-3 | C | 0 |
| R4-PC-1 | C | 0 |
| R4-PC-2 | C | 0 |
| R4-PC-4 | C | 0 |
| R4-PC-5 | C | 0 |
| R4-PC-6 | C | 0 |
| R4-PC-7 | C | 0 |
| R4-PC-8 | B | 4 |
| R4-PC-10 | C | 0 |
| R4-PC-11 | C | 0 |
| R4-PC-12 | C | 0 |
| R4-PC-14 | C | 0 |
| R4-PC-15 | C | 0 |
| R4-PC-18 | C | 0 |
| R4-PC-20 | C | 0 |
| R4-PC-24 | C | 0 |
| R4-CAPC-2 | C | 0 |
| R4-CAPC-6 | B | 6 |
| R4-CAPC-8 | C | 0 |
| R4-CAMO-1 | C | 0 |
| R4-CAMO-7 | C | 0 |

## Things to know
- `index.html` is at 58,992 bytes against a 60,000 byte cap (15,000 tokens). The two panels add about 570 bytes (59,566 measured), so
  they fit with about 430 bytes to spare; nothing else can be added to it before the cap is raised.
- Both chains add a line to `tests/conftest.py` after the `ELEMENT_IDS` list and an entry to `pc-config.json` `zones.side` (finds:
  last, time-lapse: first) and edit `canopy_forecast.py` (`render_season_forecast()`: time-lapse first line, finds last line): trivial
  conflicts if both are merged.
- R4-CAPC-6 is not an animation: nothing autoplays (nothing timed), the player drags a slider. Frames are saved per forest (a Reset
  Session empties them) because they describe that forest.
- R4-PC-8 deliberately needs no luck: find N is always the same thing, and a Tend on a fully grown plot (`maturity_fraction() >= 1.0`)
  always reveals the next one.

## Where the CLAUDE.md map was wrong or missing something
- The map does not mention `_el(id)` in `canopy_helpers.py`: it returns None where the test fake DOM would raise `KeyError` for an id
  missing from `ELEMENT_IDS`, so new page code should look elements up with `_el` (the steps do).
- The browser-test note should mention that the pace buttons of `shared/time-controls.js` (`#time-controls button[data-speed="4"]`)
  make a season (40 ticks) pass in about 10 seconds, which is the only way to test anything that needs a season to end.
- `tests/test_gb3_markup.py::test_the_desktop_page_is_not_stale` fails after any `index.html` or `pc-config.json` edit until
  `scripts/generate-pc-pages.py` has run; `ai.ps1` runs it before each test run, so this is harmless, but the map could say so.
