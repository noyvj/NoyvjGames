# Zero-G Shift (slug `zero-g-shift`, TODO QI-9) - Groundwork Plan

Source: the Quick ideas round (A9), owner-approved: "Sokoban-style crate pushing, but everything keeps sliding until it hits something." Checked against `PLAYER-PROFILE.md`: spatial puzzles first, space stations, one puzzle at a time, forms a bigger picture, three goals visible, no timers, restore always available, easy-to-medium base difficulty, dark moody low-poly. Personal project, no BCM tag, working title.

Pitch: in a weightless cargo bay, every push sends you or a crate gliding until something stops it, so you plan each slide to dock every crate.

## 1. Concept
- You are a loader in a drifting freight bay (invented: Bay 9 of the hauler Marrow). You are pressed against a wall; thrust in one direction and you slide until you hit something. If a crate is in your way you stop against it and it slides on. Crates stop against walls, other crates or posts. A dock pad catches a crate on contact.
- 2-minute session: two or three small bays. 20-minute session: a whole deck.
- Look: dark bay, faceted low-poly crates, posts and pads in grey-blue, a lit grid. Crates carry a number or shape, pads match them, so no colour-only coding. Quiet tone; one tired loadmaster note per bay (optional).

## 2. Core rules (a pure function of the bay and the move list)
- Grid 5x5 to 10x10. Cells: floor, wall, post (a one-cell obstacle), pad (matching crate sticks), hatch (a crate slides through, you do not), bumper (stops you but flings nothing), airlock door (opens when its pad is full).
- Move: Up, Down, Left, Right. The player slides until blocked. If the next cell holds a crate, the crate slides until it is blocked and the player stops where they were (a "push"). Crates cannot push crates (a crate stopped by a crate stays put).
- A bay is cleared when every crate sits on a pad. Par is the shortest solution (in moves) found by the solver; medals for Par, Par+3 and Done.
- Free tools: Step back, Restart (both free, unlimited, and shown as words), and Can I still win? (tells you if the current position can still be solved; see proofs).

## 3. Content size
48 bays in six decks of 8: Cargo Floor (open slides), Crates (one crate), Posts and Pads, Hatches, Bumpers and Doors, The Long Hold (large, multi-crate). Deck n+1 opens at 5 of 8 cleared; any order inside.

## 4. How correctness is PROVED
- Dev tool `tools/solver.py` runs breadth-first search over (player, crates) states for every bay. Tests assert every bay is solvable, par equals the BFS shortest length and is stored, no bay has a solution of fewer than 4 moves, and every bay has at most 3 optimal solutions (so a stored hint line is fair).
- Dead-state detection uses the same search from the current position (state space is small; the largest bay stays under 400k states): "Can I still win?" returns yes or no and, for no, names the move that broke it, but never changes the position.
- Determinism: pure functions, no clock, no random; the move list replays to the same bay.

## 5. Collection and 100%
- The Cargo Manifest: a ledger of 48 crates-delivered stamps (one per bay) shown on a ship cutaway, bay by bay lighting up; the manifest has a second column for Par medals. 100% = all 48 delivered; par medals are a bonus. States only go up.

## 6. Goals and hint ladder
- Three always-visible goals, any order, with bars. Stats strip: Bays cleared, Par medals, Moves, Decks done. The tally counts moves, step backs and restarts.
- Ladder (first rung asks "Would you like a suggestion?"): Nudge (which crate to look at first), Hint (the first move of the stored line as a ghost arrow), Answer (the whole line as a ghost path with a "Play it" button). Free, on request, never affects the medal.

## 7. Achievements (14)
First Delivery; Ten Bays; Twenty-Four Bays; All Forty-Eight; Deck Done; Four Decks; At Par (5); Par Hand (20); Perfect Hold (every par medal in one deck); Long Slide (one slide of 8 or more cells); Doorkeeper (clear a bumper-and-door bay); Hatch Runner; Back Out (use Step back after a dead end); Nothing Wasted (clear a bay in exactly par with no hint).

## 8. Real-world facts
None, fiction. The About page names the genre (Sokoban, ice-sliding puzzles) as inspiration only.

## 9. Reuse
Grid engine and `tools/solver.py` pattern from Hull Repair and Logic Gates; board renderer style from Hull Repair (`render.py`); `level-select.js`, `hint-ladder.js`, `goals-panel.js`, `opening-screen.js`, `confirm-dialog.js`, `info_page.py`, `announcer.js`, `pc-shell.js`; optional `sfx.js` thuds.

## 10. Milestones
| # | Milestone | Content |
|---|-----------|---------|
| 1 | Engine and solver | Slide rules, BFS solver, dead-state check, deck 1 (8 bays) with proofs |
| 2 | Bay UI | SVG bay, swipe and keys, slide animation (toggleable), step back and restart, save contract. Playable slice |
| 3 | Decks 2-4 | 24 more bays, posts, pads, hatches, manifest panel, deck gating |
| 4 | Decks 5-6, hints, goals | 16 more bays (48), bumpers and doors, hint ladder, three-goals strip, par medals. First complete game |
| 5 | Standard kit | Opening screen, tutorial, About with Sources, What's New, keyboard help, confirm dialogs, light theme, accessibility |
| 6 | Achievements | 14 achievements, panel and toast, manifest, reachability test |
| 7 | Desktop boot and wrap-up | `pc-config.json`, `pc.css`, `pc.js`, generated `pc.html`, docs, changelog |

## 11. Open questions for the owner
1. Is a free Step back fine in a move-by-move puzzle (it is not a story choice)? Default: yes, with Restart always free too.
2. Should the player also slide when they push a crate (recoil)? Default: no, the player stops.
