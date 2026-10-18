# Loop: LA-7 live-data notes (2026-10-19)

Steps are in `local-ai/incoming/loop-live.txt` (lint: 0 problems), one chain `LA7-LOOP` of 8 steps for GH-22 and FY-36 (the two items ask for the same cards). Data: `games/loop/data/materials.json` (rebuilt by `games/loop/tools/fetch_materials.py`, tested by `tests/test_materials_snapshot.py`).

## What was frozen
Wikipedia REST page summaries (`https://en.wikipedia.org/api/rest_v1/page/summary/<title>`, `access-control-allow-origin: *`, text CC BY-SA 4.0): 24 materials, six per goods category: electronics (Copper, Gold, Lithium, Cobalt, Silicon, Aluminium), clothing (Cotton, Wool, Polyester, Nylon, Linen, Silk), furniture (Oak, Pine, Bamboo, Rattan, Glass, Polyurethane) and the secret Ship-Breaking Yard (Iron, Steel, Nickel, Chromium, Manganese, Zinc). Each has the first two sentences of the article, the article link, the API URL, the revision and the page timestamp. The page reads them live (when the cards panel first opens) and falls back to the dated snapshot; the source line says which.

## A list (`[local AI: in steps]`)
GH-22 and FY-36 together: remember the best circularity per category in the career (new field `best_circular`), the card logic (six thresholds, rarity words), the markup, the render, the loading plus the live read, a browser test.

## Defaults the owner may change (listed here because the steps hard-code them)
- Unlock thresholds 10, 25, 40, 60, 80 and 100 percent circular in one cycle, per goods category; rarity words common, common, uncommon, rare, epic, legendary. The TODO text only says "circular-fraction thresholds".
- Which material belongs to which category (design choice). The facts are Wikipedia's.
- The cards are art-free text lines ("art-free stat blocks" in GH-22): name, category, rarity and the fact; the in-game stat shown is the threshold reached. Richer stat blocks need a decision about which numbers to show.

## C list
None. The "[conflict: ...]" tag on GH-22 is answered: the card text is the dated, named Wikipedia text, read live when possible.

## For the Claude who audits
- `pc.html` is generated: new element ids (`cards-panel`, `cards-summary`, `cards-list`, `cards-source`) need `scripts/generate-pc-pages.py` before `shared/tests/test_pc_games.py` passes.
- Adding `best_circular` to `CAREER_BEST_FIELDS` is additive; old saves load unchanged.
