# Le Champ de Mots: LA-8 notes (drafted 2026-10-18)

Steps are in `local-ai/incoming/champ-de-mots.txt` (lint: 0 problems). 17 open items labelled `[local AI: after split]`. This game's open items are mostly new mini-games, new art, gesture work or shared-shell work, so only one of them cuts into exact steps.

## A list (relabel `[local AI: yes]`)
None.

## B list (chains)
- L-31 (3 steps): achievement card restyle with farm glyphs. Step 1 is a table of ten (emoji, word) pairs, one per achievement in `achievements.json`, plus `glyph_for()`; step 2 draws the glyph (an `aria-hidden` span) in front of each earned row's label; step 3 is the per-style CSS. The item says "themed across High-def, Low-poly, Text-based and Cartoon", which does not say how, so the step fixes it: High-def keeps the plain glyph, Low-poly puts it on a hexagonal cream tile (`clip-path`), Cartoon rings it, Text-based shows the crop's name in brackets instead of the picture. Easy to adjust if the owner wants different looks. No saves, no new modules.

## C list (not for the local AI)
| Item | Label | Reason |
|------|-------|--------|
| L-1 farm economy (rest) | `[needs you]` | The notes record that the owner said the watering can must stay cosmetic and that coins come from watering only (the single-source rule was kept on purpose). Harvest coins from mastered plots, a bigger can that reminds neighbours, decor and a market stall all change those answers or add content, so the owner has to say which parts they now want. |
| L-3 Voyage minigame | `[Claude: design]` | A new minigame: a fixed city route, a saved perk and collection track, free-hint and second-try perks, and feeding the ledger. A new module plus saved state plus a lot of content; far more than 150 lines per step and several decisions. |
| L-22 Pomodoro timer | `[Claude: design]` | A new kind of timer (not a question game, so the minigame base class does not fit), the owner's explicit exception to the no-timer and no-animation tests, plus numbers nobody has chosen (length, bonus size). Touches `boot.js`'s shared one-second tick and the pledge tests. |
| L-23 scarecrow mascot | `[Claude: art]` | Drawn poses and outfits; also only ten achievements exist to unlock outfits with. Also an explicit animation exception. |
| R4-PN-2 greenhouse | `[Claude: art]` | Low-poly potted plants drawn in code on a shelf, one per automated plot. |
| R4-PN-3 visiting student | `[needs you]` | A new helper role: what "teaching" means and how it counts as practice is a design choice. |
| R4-PN-9 verb compiler | `[Claude: design]` | A new puzzle (ending rules per person, tests turning green), with a generator and its own ledger mode. |
| R4-PN-10 word flow boards | `[Claude: design]` | Flow-Free path routing needs a board generator that guarantees a solution, plus drag-drawn paths that cannot cross; drag and board work failed in earlier audits. |
| R4-PN-11 grammar rule board | `[Claude: design]` | A Baba-Is-You style rule-tile puzzle: a rules engine and hand-made boards. |
| R4-PN-19 French skill tree | `[needs you]` | A big tree whose nodes level up with plot growth and never refund; the nodes and their thresholds are a content decision. |
| R4-PN-26 unpack the crate | `[Claude: art]` | A drawn room and household items, labelled by the player, with new vocabulary content. |
| R4-CHPC-2 Alt+letter accent layer | `[Claude: design]` | The Alt+letter mapping is not settled (which letter gives which accented form, how to cycle), and Alt+letter is a menu shortcut on Windows and a dead key on a Mac, so it needs trying on real keyboards. It also needs a cheat chart that works on both pages. |
| R4-CHPC-5 three-column study desk | `[Claude: shared]` | Dragging and docking windows is the shared Desktop shell (`shared/pc-shell.js`). |
| R4-CHMO-1 full-screen question card | `[Claude: design]` | Replaces the layout of the main practice panel for phones with a bottom accent bar and large buttons; a layout rewrite, not one step. |
| R4-CHMO-2 swipe to water | `[Claude: design]` | A swipe gesture on the farm cells; gesture work failed in earlier audits and the farm cells are rebuilt on each redraw. |
| R4-CHMO-7 portrait minigame lobby | `[needs you]` | "Your best score on each" has no source today: only Blitz and Sprint keep a best, and only for the page load; the other games keep none. Saved bests need a new save key and score tracking in several modules, so the owner should say whether session-only is acceptable. |

| Item | Decision | Steps |
|------|----------|-------|
| L-1 | C | 0 |
| L-3 | C | 0 |
| L-22 | C | 0 |
| L-23 | C | 0 |
| L-31 | B | 3 |
| R4-PN-2 | C | 0 |
| R4-PN-3 | C | 0 |
| R4-PN-9 | C | 0 |
| R4-PN-10 | C | 0 |
| R4-PN-11 | C | 0 |
| R4-PN-19 | C | 0 |
| R4-PN-26 | C | 0 |
| R4-CHPC-2 | C | 0 |
| R4-CHPC-5 | C | 0 |
| R4-CHMO-1 | C | 0 |
| R4-CHMO-2 | C | 0 |
| R4-CHMO-7 | C | 0 |

Totals: A 0, B 1 item (3 steps), C 16.
