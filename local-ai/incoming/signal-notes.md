# Signal: LA-8 notes (s3b, drafted 2026-10-19)

`local-ai/incoming/signal.txt` holds no steps (header comment only, lint: 0 problems). 3 open items labelled `[local AI: after split]`; all three are C. Signal's map in CLAUDE.md is accurate; `index.html` is not over its cap (`tests/test_file_sizes.py` limits every editable file to 14,000 estimated tokens, and nothing here adds markup).

## A list
None.

## B list
None.

## C list (not for the local AI)
| Item | Label | Reason |
|------|-------|--------|
| R4-PU-4 distress calls: each solve locates a lost probe, clearing a sector opens the next | `[Claude: design]` | A new progression layer on top of the daily/archive/practice puzzles: how many solves per sector, whether daily, archive or practice solves count (the rules say archive and practice never touch streaks), a sector map and the save format are all undecided, and it must not change the frozen daily puzzles (`tests/fixtures/daily_v1.json`). |
| R4-SIPC-5 hold Space to overlay each ping's reach rings | `[needs you]` | Space is already the "mark this tile" key on a focused tile (`app.js` board keydown), so "hold Space" would mark tiles. Which key should it be (suggest G for "guide")? The rest is easy once decided: the ring for a ping with reading v lies at Manhattan distance radius minus v (for 0 < v < radius), tiles show how many rings cross them as a number, drawn from the player's own pings only. Also note `pc.js` already uses held Shift for a distance ruler on the Desktop page. |
| R4-SIMO-1 hold a tile for a magnifier bubble | `[Claude: design]` | Looks already built: `app.js` has the "hold-to-aim magnifier (R4-SIMO-1, phone only)" section, a Settings checkbox `#magnifier-checkbox`, and `tests/test_ai_magnifier.py`. The bubble names the tile and any reading it already has; a "ping preview" cannot exist without revealing what a ping returns. Claude should verify on a phone width and tick the item. |

| Item | Decision | Steps |
|------|----------|-------|
| R4-PU-4 | C | 0 |
| R4-SIPC-5 | C | 0 |
| R4-SIMO-1 | C | 0 |

Totals: A 0, B 0, C 3.
