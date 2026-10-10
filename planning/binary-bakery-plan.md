# Binary Bakery (slug `binary-bakery`, TODO QI-37) - Groundwork Plan

Source: the Quick ideas round (G4), owner-approved: "a calm game where you build numbers from binary switches to fill orders." Checked against `PLAYER-PROFILE.md`: calm "routine you know by heart" feel, collecting every item (one of each bake), coding and maths interest, Unpacking-style calm, short wins building one bigger picture, three goals, easy to 100%, no timers, orders that never expire. Personal project, no BCM tag, working title. One-line pitch: a night bakery run by switches, where every order is a number and every number is a row of trays turned on or off.

## 1. Concept
You work the night counter at **Two's Bakery**, a small shop that bakes only in powers of two. A rack of **trays** holds 1, 2, 4, 8, 16... buns each. A switch above every tray turns it on or off; the oven bakes what is on. A customer **order slip** asks for an exact count ("13 rolls for the early train"), and you flip trays to match. A bell, a warm drawer and a thank-you note when it is right.
- 2-minute session: three short orders on 4 trays (up to 15), a mini routine you can do half asleep.
- 20-minute session: a whole day-card of eight orders with a batch order (a bag of 5 and a bag of 9), then a message cake.
- Look: dark, warm, faceted low-poly bakery counter as SVG; trays drawn with their count printed (the place value is a number and a bun-stack shape, never colour only); switches are large toggles with the word On or Off. Quiet; optional generated clink and bell via `shared/sfx.js`.
- **Nothing waits angrily.** Customers do not leave, there is no clock, no stock to run out, no money to lose. Orders sit on the spike until you serve them.

## 2. Rules (a pure function of the order and the switch row)
- A switch row is n bits (4, 6, 8, up to 12). The tray value of bit i is 2^i. The count is the sum of on trays. An order is fulfilled when the count equals the target.
- Order kinds, introduced by chapter: **Exact** (make N), **Batch** (make N1 and N2 in two tray rows, shared oven), **Add** (two trays-in-hand rows must sum to N, carry shown), **Broken Tray** (some switches are stuck On or Off and the target is reachable by exactly one setting), **Letter Cake** (spell a word: each letter is an ASCII/Unicode code written as bits), **Half-Byte Icing** (hex digits: two 4-bit nibbles make one byte).
- Presentation helpers (always optional): show the sum so far, show the binary string, show the place values. A setting hides them for a harder game.
- No clock, no randomness (orders are authored; the Practice Counter uses seeded orders).

## 3. Content size
- 42 order slips in six chapters of seven: Four Trays (0 to 15), Six Trays (0 to 63), A Full Byte (0 to 255), Two Bags (batch and add), Broken Trays, Letter Cakes and Icing.
- A **Bake Book** of 48 bakes (a bun, a loaf, a braid...) each tied to one order slip number, with a low-poly drawing and a one-line note; a seeded **Practice Counter** with endless slips for repeating the routine.
- About 40 customers with a quiet line each (a night nurse, a train guard, a lighthouse keeper), none rude.

## 4. How fairness is PROVED (tests)
- For every authored order, a brute-force solver over all switch settings (up to 12 bits) confirms the target is reachable and, for Exact and Broken Tray orders, that the solution is **unique**; Add and Batch orders list all solutions found and the stored one is among them.
- Letter Cake codes are checked against Python's `ord` and the Unicode chart for every letter used; Hex icing is checked against `int(x, 16)`.
- A completion simulator plays every order with the stored solution and confirms the Bake Book fills to 48 of 48.
- Determinism and source scan: no clock, no randomness in the engine; the Practice Counter takes a seed from `shared/seed.py` and its output is a pure function of it.

## 5. Bigger picture, goals, hints
- The **Shop Front** is the picture: a dark shop window that fills with the 48 bakes as slips are served; the number of lit lamps follows the percentage bar above. The Bake Book is the collection (shelf of 48).
- Three goals always visible (any order): the next three unearned achievements with counts and bars. Stats strip: Slips served, Bakes, Trays flipped, Practice slips.
- Hint ladder (opt-in; first rung asks "Would you like a suggestion?"): Nudge (the biggest tray that fits), Hint (which trays to turn on, shown as a ghost for the first half), Answer (the full row with a button that sets it).
- Every chapter and slip open from the start; the order is a suggestion.

## 6. Achievements (14; computed from facts)
1 First Bell (serve 1); 2 Ten Slips; 3 Day Done (a whole chapter); 4 Full Counter (all 42); 5 Right First Time (10 slips with no wrong flips); 6 Quick Hands (use the fewest flips 10 times); 7 Bake Book Half (24 bakes); 8 Bake Book Full (48); 9 Big Byte (serve 255); 10 Carry (first Add slip); 11 Stuck Tray (first Broken Tray slip); 12 First Word (first Letter Cake); 13 Practice Twenty (20 practice slips); 14 Second Opinion (all three hint rungs on one slip).

## 7. Real-world facts
Small cards read live from named, dated sources on the About page: the binary system's history (Leibniz's 1703 essay, Boole) and the ASCII/Unicode tables used by the letter cakes. The numbers themselves are exact maths and are tested in code. More game than teaching.

## 8. Stack, save and reuse
- Pyodide Python, plain HTML/CSS with code-drawn SVG, no build step. Modules: `bits.py`, `orders_*.py`, `solver.py`, `bakebook.py`, `practice.py`, `progress.py`, `hints.py`, `render.py`, `achievements.py`, `info.py`, `game.py`, `app.js`.
- Reuses Logic Gates' switch-and-lamp rendering ideas, Pocket Bazaar's calm-shop framing and no-pressure pledge test, `shared/seed.py`, `hint-ladder.js`, `goals-panel.js`, `save-widget.js`, `level-select.js`.
- Save: best (fewest flips) per slip, bakes, hint rungs, practice seeds, flags, tally.

## 9. Milestones
| # | Milestone | Content |
|---|-----------|---------|
| 1 | Engine | Bit rows, order kinds, exhaustive solver, chapters 1-2 (14 slips) with proofs |
| 2 | Counter UI | SVG counter, trays and switches, order spike, bell, save contract. Playable slice |
| 3 | Chapters 3-5, Bake Book, hints | 21 more slips, Bake Book, shop front, hint ladder, three-goals strip |
| 4 | Chapter 6 and Practice Counter | 7 more slips (42 in all), letter cakes and hex icing, seeded practice. First complete game |
| 5 | Standard kit | Opening screen, tutorial, settings, About with live-read sources, What's New, keyboard help, light theme, accessibility pass |
| 6 | Achievements | 14 achievements, panel and toast, manifest, reachability test |
| 7 | Desktop boot and wrap-up | `pc-config.json`, `pc.css`, `pc.js`, generated `pc.html`, docs, changelog |

## 10. Open questions for the owner (defaults used meanwhile)
1. Should helper displays (running sum, binary string) be on by default, with a setting to hide them for a harder game? Default: on.
2. Should negative numbers (two's complement) be a late optional chapter? Default: no, kept out.
