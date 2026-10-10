# Loadout Lab (slug `loadout-lab`, TODO QI-22) - Groundwork Plan

Source: the Quick ideas round (C2), owner-approved: "combine parts to reach target numbers, with a catalogue of every combination you have found, including the one overpowered build per challenge." Checked against `PLAYER-PROFILE.md`: finding the one broken build feels clever, collecting every combination, optimising that is easy to get working and deeper with real depth (not spreadsheet level), robots and science fiction, planning with no randomness, three goals, no timers, nothing lost. No roguelike or deck mechanics: parts are fixed and always available. Personal project, no BCM tag, working title.

Pitch: snap parts together in a small robot workshop to hit exact target numbers, log every build you find, and hunt for the one cheeky overpowered combination hiding in each challenge.

## 1. Concept
- You are the test engineer at a robotics lab (invented: Quarry Lab). Each challenge asks for a rover or drone build that reaches target stats (for example Haul 48 or more with Heat 10 or less, or exactly Speed 30). A build has four slots: Core, Drive, Frame, Tool. Twenty-four parts (all open from the start) each add or multiply stats.
- 2-minute session: one easy target. 20-minute session: several challenges and a hunt for a Broken Build.
- Look: dark workbench, faceted low-poly part tiles, stat bars with numbers (never bars alone). Quiet, dry tone; the lab's inventory robot comments on each build in a few words.

## 2. Core rules (a pure stat calculator)
- Stats: Power, Haul, Speed, Heat, Mass. Each part has base numbers, a small set of tags (e.g. "ion", "cargo", "cool") and synergy rules: pair bonuses (Ion Core with Ion Drive: Power times 1.25), caps (Heat above 20 halves Speed) and one conversion (Tool turns Mass into Haul).
- A challenge states required stats (at least, at most, or exactly) over any of the five. A build Passes when all hold. Parts are never consumed: you can reuse every part in every build.
- Luck: none. All multipliers are fixed and shown in the Why panel, which lists every line of the stat calculation.
- Every challenge has one hidden Broken Build: the strict maximum of the challenge's headline stat over all legal builds, which far exceeds what the intended solutions reach. Finding and Running it files a "Broken" stamp. Broken builds are encouraged, not hidden behind a ban: there is no cost to using them.

## 3. Content size
40 challenges in 5 chapters of 8: First Builds (exact targets), Heat and Haul (bounds), Pairs (synergy hunting), Conversions (the Tool slot), The Whole Lab (all five stats, tight bounds). Chapter n+1 opens at 5 of 8; any order inside. 24 parts; builds per challenge range up to 24^4, but only legal-slot ones count, about 38,000.

## 4. How correctness is PROVED
- Dev tool `tools/enumerate.py` evaluates every legal build for every challenge. Tests assert: at least 2 and at most 60 builds pass (so there is room to find your own), the cheapest-Mass pass is stored as par, the Broken Build is the unique argmax of the headline stat and is at least 1.8 times the best intended pass, and the evaluator is the same function the UI uses.
- Catalogue size is exact: total distinct (part set, challenge) passes are counted and stored, so the player's Found/Total counter is truthful.
- Determinism: integer or exact-fraction arithmetic with a fixed rounding rule; no clock, no random.

## 5. Collection and 100%
- The Build Book: a catalogue of every pass found, listed per challenge as "found 3 of 11 passes" with the builds named by their parts; plus a Parts Shelf of 24 parts with the combinations that include them, and 40 Broken stamps. 100% = all 40 challenges passed; "All passes found" per challenge and the Broken stamps are bonus columns with their own counters (a bonus is never required for the main percentage). States only go up.

## 6. Goals and hint ladder
- Three always-visible goals, any order, with bars. Stats strip: Challenges passed, Builds found, Broken stamps, Parts used. The tally counts runs and swaps; every Run adds to Builds found if it is new.
- Ladder (first rung asks "Would you like a suggestion?"): Nudge (which stat to chase first and why), Hint (one part of a passing build as a ghost), Answer (a full passing build, with a "Build it" button). The Broken Build gets its own rung: "Would you like a clue about a surprising build?" (a one-line pointer to the synergy). Free, on request.

## 7. Achievements (14)
First Pass; Ten Passes; Twenty Passes; Forty Passes; First Broken; Ten Broken; All Broken; Pair Bonus (trigger 10 pair bonuses); Cool Head (pass with Heat 0); Light Load (pass with Mass 5 or less); Found Them All (every pass of one challenge); Parts Shelf (use every part); Conversion Done (chapter 4); One Of Everything (200 distinct builds found).

## 8. Real-world facts
None, fiction. The About page names the real ideas behind part synergy and caps (diminishing returns, thermal limits) as text only, with sources named.

## 9. Reuse
Pure-Python engine with `handle(json)`; enumerator tool in the pattern of Logic Gates and Hull Repair solvers; Pocket Bazaar's catalogue and decoration shelf; shared `level-select.js`, `hint-ladder.js`, `goals-panel.js`, `opening-screen.js`, `info_page.py`, `announcer.js`, `pc-shell.js`.

## 10. Milestones
| # | Milestone | Content |
|---|-----------|---------|
| 1 | Stat engine and enumerator | Parts, synergy rules, evaluator, full-build enumerator, chapter 1 (8 challenges) with proofs |
| 2 | Workshop UI | Slots and part tiles, live stat panel with Why lines, Run, save contract. Playable slice |
| 3 | Chapters 2-3 | 16 more challenges, bounds and pair bonuses, Build Book |
| 4 | Chapters 4-5, hints, goals | 16 more challenges (40), conversions, Broken stamps, hint ladder including the Broken clue, three-goals strip. First complete game |
| 5 | Standard kit | Opening screen, tutorial, About with Sources, What's New, keyboard help, confirm dialogs, light theme, accessibility |
| 6 | Achievements | 14 achievements, panel and toast, manifest, reachability test |
| 7 | Desktop boot and wrap-up | `pc-config.json`, `pc.css`, `pc.js`, generated `pc.html`, docs, changelog |

## 11. Open questions for the owner
1. Should finding every pass of a challenge count towards 100%, or stay a bonus? Default: bonus only, so 100% stays easy.
2. Should the Broken Build ever be nerfed or banned from a "fair" challenge variant? Default: no, Broken is always allowed and celebrated.
