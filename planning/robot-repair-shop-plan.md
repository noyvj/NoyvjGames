# Robot Repair Shop (slug `robot-repair-shop`, TODO QI-14) - Groundwork Plan

Source: the Quick ideas round (B2), owner-approved: "fix quirky robots by solving their fault puzzles; each repaired robot becomes a friend that gives you a gift later." Checked against `PLAYER-PROFILE.md`: robots, a helper and healer role, collecting one of each, quiet tragic-but-gentle characters with a robot that shows feeling, short wins into a slow arc, three goals, no timers, nothing lost, friendly welcome-back. Personal project, no BCM tag, working title. Related but distinct from Station Medic (hidden-cause deduction over patients) and Robot Script (programming): here each robot is a small wiring puzzle.

Pitch: robots roll into a quiet workshop with odd faults; probe them, work out their crossed wiring, fix it, and each repaired robot later drops by with a small gift.

## 1. Concept
- You run a dim repair bay (invented: Sparrow Row Workshop). A robot arrives with a quirk: a lamp that blinks when asked to wave, an arm that only turns left, a hum that sounds like a question. Open its panel: a short row of Commands (inputs) wired to Actions (outputs) through a patch bay. You send test commands (probes), watch what the robot does, then rewire the patches until every command does what it should.
- 2-minute session: one small robot. 20-minute session: three or four robots and a visit.
- Look: dark workshop, faceted low-poly robots with a lamp that shows mood (the lamp also shows a word, not only colour). Robots barely speak; one dry caption each. Tone: warm, a little sad (a robot who still waits for its owner), never harmed.

## 2. Core rules (pure functions)
- A robot has 3 to 6 commands and the same number of actions. Its wiring is a permutation, possibly with one inverter (swaps left and right on that wire) or one stuck wire (the action never fires until a bypass part is fitted).
- Probe: press a command and see the robot's action in its animation and in a printed line. Probes are free and unlimited; the Probe count is recorded only for a "few probes" tag.
- Rewire: drag a patch cable from a command to an action; the Test Rig then runs all commands in order and marks each Right or Wrong with a word. Fixed when every command matches the robot's Wanted list (shown as a card).
- Parts: inverter, bypass and later a delay-buffer part are given in the bin; each is used on purpose by the puzzle.

## 3. Content size
36 robots in 6 shelves (chapters) of 6: Little Helpers (3 wires), Four-Wire Folk, Inverters, Stuck Wires, Chains (two robots wired in series), The Big Ones (6 wires, all parts). Shelf n+1 opens at 4 of 6; any order inside. Each robot has a name, a one-line story and a gift.

## 4. How correctness is PROVED
- Dev tool `tools/consistent.py` enumerates every wiring consistent with the probes so far. Tests assert: every robot is solvable; the stored fix is the unique wiring that matches its Wanted list; and a probe plan exists that identifies the hidden wiring uniquely in at most 'n' probes (par), found by search and stored per robot.
- The inverter and stuck-wire parts are only ever required where the probes alone cannot hide them (tests: a robot marked "needs a bypass" is unsolvable without one).
- Determinism: no clock, no random; animations are cosmetic.

## 5. Friends and gifts (collection)
- Each repaired robot becomes a Friend on the Friends shelf (36 slots). A friend visits the shop after your NEXT repair (turn-based, never a real-time wait, never missed) and leaves a gift: one of 36 small items such as a spare tool, a new probe type, a shelf decoration or a story note. Gifts are tools and keepsakes only, never a currency to grind. Some gifts help later: "Stethoscope" shows which wire carries a signal (a free extra hint rung), "Spare Bypass" is a part. The visiting friend can be tapped at any time to collect.
- 100% = all 36 robots repaired and all 36 gifts received; gifts always arrive eventually because each visit is queued by repairs, not by days.

## 6. Goals and hint ladder
- Three always-visible goals, any order, with bars. Stats strip: Robots repaired, Friends, Gifts, Fewest-probe tags. The tally counts probes and rewires.
- Ladder (first rung asks "Would you like a suggestion?"): Nudge (which command to probe next), Hint (names one correct cable), Answer (the full wiring as ghosts, with a button). Free, on request.

## 7. Achievements (14)
First Repair; Ten Repaired; Twenty-Five Repaired; All Thirty-Six; First Friend Visit; Ten Gifts; All Gifts; Shelf Done; Three Shelves; Right First Time (a robot fixed with one rewire); Few Probes (10 par tags); Inverted (fix an inverter robot); Bypass (fix a stuck-wire robot); Chain Gang (chapter 5).

## 8. Real-world facts
None, fiction. The About page notes the electronics ideas behind patch bays and signal chains as text only, with sources named.

## 9. Reuse
Wiring and `handle(json)` pattern from Logic Gates; collectable shelf from Station Medic's crew Record; Stranded's quiet captions; shared `level-select.js`, `hint-ladder.js`, `goals-panel.js`, `opening-screen.js`, `info_page.py`, `narrative_log.py`, `announcer.js`, `pc-shell.js`.

## 10. Milestones
| # | Milestone | Content |
|---|-----------|---------|
| 1 | Engine and checker | Wiring model, probes, parts, consistent-wiring search, shelf 1 (6 robots) with proofs |
| 2 | Bay UI | SVG patch bay, probe buttons, cable dragging and keyboard, Test Rig, save contract. Playable slice |
| 3 | Shelves 2-4 | 18 more robots, inverters and stuck wires, Friends shelf and visit queue |
| 4 | Shelves 5-6, gifts, hints, goals | 12 more robots (36), 36 gifts, hint ladder, three-goals strip. First complete game |
| 5 | Standard kit | Opening screen, tutorial, About with Sources, What's New, keyboard help, confirm dialogs, light theme, accessibility |
| 6 | Achievements | 14 achievements, panel and toast, manifest, reachability test |
| 7 | Desktop boot and wrap-up | `pc-config.json`, `pc.css`, `pc.js`, generated `pc.html`, docs, changelog |

## 11. Open questions for the owner
1. Should a friend's visit also unlock a tiny optional favour (like a free extra probe type), or stay purely a keepsake? Default: a few gifts are tools, the rest keepsakes.
