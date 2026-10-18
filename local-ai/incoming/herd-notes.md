# Herd: LA-8 notes (drafted 2026-10-18)

Steps are in `local-ai/incoming/herd.txt` (lint: 0 problems). 9 open items labelled `[local AI: after split]`.

## A list (relabel `[local AI: yes]`)
None. Nothing in Herd is a single small step: the only buildable item needs new per-round data first.

## B list (chains)
- F-3 (7 steps): round replay. The item says it "needs a per-round state record", and the farm keeps only methane, funds, the lever log and the advisor history per round. Steps: (1) a new `round_records` list on `FarmState` (`[herd_size, coupling_ratio, pressure_fraction]` per round, aligned with `methane_history`, copied by `clone_farm`); (2) save and load it (`herd_savegame.py`, key written only after the first advance, validated entry by entry, padded with `None` for old saves exactly like `funds_history`); (3) `replay_frame(index)`; (4) the two text builders (`replay_text`, `replay_marker_items`); (5) the slider handler, `render_replay()`, a live variable `replay_index` and the test ids; (6) the markup inside the existing `#collection-extras` details (next to the lever history) plus the Desktop window member; (7) wiring in `game.py` plus a browser test.
  Interpretations the owner should know about: the replay is a slider with a words readout, a coupling gauge (the existing `coupling_gauge_svg`) and a list of that round's lever purchases and advisor choices; "pasture cows" are shown as a count ("cows shown 2 of 5", the same thresholds the pasture picture uses), and "haze" as the pressure haze percentage and the methane-wisp percentage (the two haze cues the pasture already has). It does not redraw the pasture picture itself, because that picture is driven by the live farm and moving it through history would risk the real page. Nothing is timed (it is a slider, not a playback), nothing is saved except the new per-round record, and the readout is text so colour is never the only signal.

Notes for the audit: the replay block adds roughly 600 bytes to `index.html`, which is the one file allowed above the token cap in `tests/test_file_sizes.py`: check the cap. Step 7 wires a listener in `game.py`; the human then runs `scripts/generate-pc-pages.py` because `index.html` and `pc-config.json` changed. The save change is the one place the step can go wrong, so review step 2 against `tests/test_save_widget.py` and `tests/test_save_recovery.py`.

## C list (not for the local AI)
| Item | Label | Reason |
|------|-------|--------|
| F-12 offline-first polish | `[Claude: shared]` | Precaching Pyodide and the offline fallback are `sw.js` and `offline-manifest.json` changes, and the queued stats and feedback submit lives in the shared community-stat and feedback code and the backend contract. Nothing here can be done inside `games/herd/` alone. |
| GF-2 succession upgrade tree | `[Claude: design]` | Four unlocks (a second capture unit, a second advisor option, a rare breed with better odds, a farmhouse skin) need balance numbers, new perks in `LEGACY_PERKS`, a save shape and a rule for "no luck" on the rare breed; the TODO also marks it as needing W-3. |
| R4-PH-2 Extension Officer | `[Claude: design]` | A whole new mode: three computer-run farms, a rule for which lever helps each most, a score for helping. New simulation and save data. |
| R4-PH-4 barn robots | `[Claude: art]` | Low-poly robots that you collect and watch working are mostly art and animation; the collecting rules are open too. |
| R4-PH-5 three farm identities | `[needs you]` | Three identities with their own goal lists and badges so each reaches 100 percent: content and balance decisions only the owner can make. |
| R4-HEPC-1 clickable pasture | `[Claude: design]` | The pasture is a fixed illustration of five cows, not paddocks; a clickable map with hover cards per paddock is a new layout and a new model of the farm. |
| R4-HEPC-7 three-round lever planner | `[needs you]` | Already largely built as the F-9 what-if planner (`herd_planner.py`: queue purchases for the next 5 or 10 rounds on a scratch copy, a projection chart with methane). The only difference from the item text is a 3-round horizon. Say whether to tick it as done, or ask for `PLAN_HORIZONS = (3, 5, 10)` as a one-line change. |
| R4-HEMO-1 portrait scene with swipe cards | `[Claude: design]` | Swipe-to-buy cards and a long-press cost chart over the whole main screen: gesture work that failed in earlier audits, and a swipe that spends money needs a design for undo. |

| Item | Decision | Steps |
|------|----------|-------|
| F-3 | B | 7 |
| F-12 | C | 0 |
| GF-2 | C | 0 |
| R4-PH-2 | C | 0 |
| R4-PH-4 | C | 0 |
| R4-PH-5 | C | 0 |
| R4-HEPC-1 | C | 0 |
| R4-HEPC-7 | C | 0 |
| R4-HEMO-1 | C | 0 |

Totals: A 0, B 1 item (7 steps), C 8.
