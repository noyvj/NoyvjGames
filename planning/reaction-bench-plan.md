# Reaction Bench (slug `reaction-bench`, TODO QI-4) - Groundwork Plan

Source: the Quick ideas round (A4), owner-approved: "balance chemical reactions to synthesise compounds, and fill a periodic table as you discover each element's uses." Checked against `PLAYER-PROFILE.md`: collecting ("one of each"), solving, chemistry named as a new subject interest, "more game than teaching", short wins that fill a bigger picture, three goals visible, no timers, no losing progress. Personal project, no BCM tag, working title.

Pitch: a quiet night-shift lab where you balance equations with dials to synthesise compounds, and every new element you use lights a tile on a growing periodic table.

## 1. Concept
- You are the technician in an unlit materials lab on a research station (invented: Halde Station). A work order board asks for compounds (water, rust, table salt, ammonia...). Each order is an equation with empty coefficient dials; you turn the dials until the atom ledger below reads equal on both sides, then press Run and the compound drops onto the Shelf.
- 2-minute session: balance two or three easy reactions, one new element tile lights. 20-minute session: finish a chapter's worth, watch the table fill in a row.
- Look: clean dark bench, low-poly glass flasks drawn as SVG, atoms as faceted shapes (shape and letter, never colour alone). Quiet tone; a lab-assistant robot (Fennel) says one short dry line per order, behind the story toggle.

## 2. Core rules (a pure function of the equation and the coefficients)
- A reaction is a list of reactant formulas, a list of product formulas and a coefficient for each (1 to 12). The atom ledger counts each element on each side live and shows the difference as a number with a sign (+2, -1, 0) plus a tick or cross glyph per element row.
- Balanced means every element's count is equal. Run is only available then. Wrong settings never fail anything: the ledger just says what is off.
- Chapter twists: from chapter 2 the player picks the products from a short list ("what comes out?"), from chapter 3 a formula can hide a polyatomic group shown as a bracket, in chapter 4 a displacement order asks which of two metals wins, in chapter 5 a two-step route (make the intermediate, then use it).
- Safety: only everyday and textbook-safe reactions (water, rust, salt, lime, fertiliser, fuels burning, photosynthesis). A banned-list lint in tests rejects explosives, drugs and toxic-weapon chemistry.

## 3. Content size
40 reactions in 5 chapters of 8: Bench Basics (combine), Burning (combustion), Oxides and Salts, Acids, Bases and Swaps, Works (industrial routes such as ammonia and sulphuric acid). Chapter n+1 opens when 5 of chapter n are done; any order inside. The table has 36 bench elements (the ones the 40 reactions use) drawn in the true periodic layout; the other cells are drawn faint and labelled "not on this bench" and are not needed for 100%.

## 4. How correctness is PROVED by tests
- A formula parser plus exact-fraction integer nullspace solver (dev tool `tools/balance.py`, pure Python) balances every authored reaction. Tests assert the nullspace has exactly one dimension, the smallest positive integer solution equals the stored answer, and the stored answer passes the same ledger the player uses.
- Mass conservation is checked a second way with a bundled atomic-mass snapshot (left mass equals right mass to 0.01).
- Product-choice rounds: tests prove exactly one product set balances out of the candidates offered.
- Determinism: no clock and no random anywhere (no shuffled lists; the candidate order is fixed in data).

## 5. Collection, 100%, bigger picture
- The Periodic Table panel: a tile per bench element, dark until the element is first used; tapping a lit tile opens its card (name, symbol, the reactions it appears in, a one-line use, live facts below). Element cards are the "discover each element's use" part.
- The Shelf: 40 compounds as labelled flasks, filled when synthesised. Both complete at 36 elements and 40 compounds. States only go up; nothing expires; Run can be repeated freely.

## 6. Goals and hint ladder
- Three always-visible goals (any order): the next three unearned achievements with counts and bars. Stats strip: Reactions balanced, Elements found, Compounds shelved, Hints used. Every dial turn and Run moves a visible count (the tally panel counts dial turns and runs).
- Hint ladder: first rung asks "Would you like a suggestion?". Nudge (names the one element that is easiest to fix first), Hint (shows which dial is off and by how much), Answer (sets the coefficients, with a button). Each rung opens only on request, is free, and never touches a clear.

## 7. Achievements (14, computed from facts)
First Balance; Ten on the Shelf; Twenty Shelved; Every Flask (40); Fire Starter (all of chapter 2); Salt of the Earth (every salt); Acid Test (chapter 4); The Works (chapter 5); Quarter Table (9 elements); Half Table (18); Full Table (36); Oxygen Everywhere (oxygen in 15 reactions); Straight Through (10 reactions with no hint); Right Product (10 product-choice rounds right first time).

## 8. Real-world facts
Each element card shows its name, atomic mass and group read live from the PubChem Periodic Table JSON service (pubchem.ncbi.nlm.nih.gov), with the fetch date shown ("read 2026-..."), and a bundled snapshot as offline fallback marked as such. One-line uses are authored, with the Royal Society of Chemistry periodic table named on the Sources page. More game than teaching.

## 9. Reuse
Engine pattern from Hull Repair (`rules.py`, `progress.py`, `hints.py`, `render.py`, `achievements.py`, `info.py`, `game.py` with `handle(json)`); shared `hint-ladder.js`, `goals-panel.js`, `level-select.js`, `opening-screen.js`, `confirm-dialog.js`, `info_page.py`, `announcer.js`, `pc-shell.js`; optional `sfx.js` clicks.

## 10. Milestones
| # | Milestone | Content |
|---|-----------|---------|
| 1 | Engine | Formula parser, ledger, nullspace balancer, banned-list lint, chapter 1 (8 reactions) with proofs |
| 2 | Bench UI | SVG bench, coefficient dials with keyboard and touch, atom ledger, Run and Shelf, save contract. Playable slice |
| 3 | Chapters 2-3 and table | 16 more reactions, product-choice rounds, bracket groups, the periodic table panel and element cards, chapter gating |
| 4 | Chapters 4-5, hints, goals | 16 more reactions (40 total), two-step routes, hint ladder, three-goals strip, live PubChem facts. First complete game |
| 5 | Standard kit | Opening screen, tutorial, About with Sources, What's New, keyboard help, confirm dialogs, light theme, accessibility pass |
| 6 | Achievements | 14 achievements, panel and toast, manifest, reachability test |
| 7 | Desktop boot and wrap-up | `pc-config.json`, `pc.css`, `pc.js`, generated `pc.html`, docs, changelog |

## 11. Open questions for the owner
1. Should the table cover only the 36 bench elements for 100%, or all 118 with the unused ones also given a use card? Default: 36, the rest faint and optional.
2. Is a free sandbox bench (type any formulas and have the ledger check them) wanted after chapter 5? Default: no.
