# Water Works (slug `water-works`, TODO QI-16) - Groundwork Plan

Source: the Quick ideas round (B4), owner-approved: "route clean water to villages with trade-offs between town, farm and wild land, shown from several people's points of view." Checked against `PLAYER-PROFILE.md`: water named as a caring topic, real-world games show several points of view, helper role, planning three steps ahead with no randomness, "fun that happens to be accurate", three goals, no timers, nothing lost. Personal project, no BCM tag, working title.

Pitch: lay channels, wells and reservoirs across a dry valley, then listen to what each of five people thinks of the result and find a plan they can all live with.

## 1. Concept
- You are the water planner for an invented river valley (Teal Valley, later others). A map shows a spring or river, a town, farms, a stretch of wild wetland, a downstream village and hills between. You spend a works budget on channels, wells, a reservoir and filters, and set how the flow is shared at each fork. Then you read the Voices panel: the townsfolk, farmers, wetland keeper, downstream villagers and the town clerk each rate the plan (Content, Wary, Troubled) and say why in one plain line.
- 2-minute session: one small valley with two voices. 20-minute session: a full valley with five voices and a drought.
- Look: dark relief map, faceted low-poly hills and glass-blue water lines (flow shown by width and a number, not colour alone). Quiet tone.

## 2. Core rules (pure functions)
- The map is a small graph of nodes (source, junctions, town, farm plots, wetland, village) with capacity-limited edges. The player buys links and parts from a limited budget, and sets share dials at forks (steps of 10%).
- Flow is computed by a fixed algorithm (a max-flow with the player's shares, rounded in fixed order); drought scenarios (a "dry year" toggle) halve the source. Each voice has an explicit transparent judging rule shown on tap (for example town: enough for its homes in a dry year; farm: irrigated share of fields; wild: wetland keeps at least a set trickle; downstream: gets at least its old share; clerk: spend within budget and a spare of 10%).
- Verdicts: Content (all of that voice's rule met), Wary (met in a normal year but not a dry year, or just under), Troubled (clearly unmet). A plan is Settled when no voice is Troubled; Common ground when every voice is at least Wary in both years; Fair share when all are Content in the normal year and none Troubled in the dry year.
- Nothing is lost: undo any purchase, Restart a valley, the budget refunds fully.

## 3. Content size
36 valleys in 5 chapters: Teal Valley (two voices), The Orchard Plain (adds farm), Reed Marsh (adds the wild), The Long River (adds downstream), Dry Years (all five voices and the dry-year toggle). Valley n+1 opens at 5 done; any order inside.

## 4. How fairness is PROVED
- Dev tool `tools/plans.py` enumerates all legal plans (purchase sets within the budget and share dial settings on a coarse grid) for every valley. Tests assert: a Fair share plan exists; the cheapest Common ground plan is stored; and for each valley at least one "single-voice" plan (satisfying only the loudest voice) exists but leaves another Troubled, so the trade-off is real and not decoration.
- Flow is deterministic (no random, no clock) with golden tests for forks, loops and capacity limits. Voices' rules are data, linted to be explicitly written on screen.
- Balance: the number of Fair share plans is between 1 and 40 per valley so the player is neither lost nor given a free pass.

## 5. Collection and 100%
- The Valley Atlas: 36 valleys on a wall map of a growing region; each shows a status stamp (Settled, Common ground, Fair share). The Voices Book collects 36 named people (a farmer, a clerk, a keeper) with a short "what I wanted and what I got" note as you meet them. 100% = every valley Settled; Common ground and Fair share stamps are bonuses with their own counters. States only go up.

## 6. Goals and hint ladder
- Three always-visible goals, any order, with bars. Stats strip: Valleys settled, Common ground, Fair share, Voices met. The tally counts purchases and dial changes.
- Ladder (first rung asks "Would you like a suggestion?"): Nudge (which voice is Troubled and why), Hint (one purchase or dial setting as a ghost), Answer (the cheapest Common ground plan as a ghost, with a button). Free, on request.

## 7. Achievements (14)
First Water; Ten Valleys; Thirty-Six Valleys; Settled (a first Troubled-free plan); Common Ground (10 stamps); Fair Share (10 stamps); All Fair (every valley Fair share); Voices Heard (12 named people); Whole Book (all 36); Reed Marsh Done; Long River Done; Dry Years Done; Cheap and Fair (a Fair share plan under budget by 20%); Both Years (a plan Content in the normal year and Wary in dry).

## 8. Real-world facts
Each chapter opens with two or three dated facts read live from named sources: the WHO/UNICEF Joint Monitoring Programme (washdata.org) on safe drinking water, the FAO AQUASTAT database (fao.org/aquastat) on water use by sector, and the USGS Water Science School (usgs.gov) on a few basics. Each fact shows its read date; a bundled snapshot is the fallback. The valleys are invented, and the About page says which numbers are real and which are made up. Fun first, accurate second; no single "right" opinion is pushed.

## 9. Reuse
Graph engine and `tools/` enumerator in the pattern of Hull Repair and Trade Empire's allocation logic; Heist Committee's multi-voice result card idea; shared `level-select.js`, `hint-ladder.js`, `goals-panel.js`, `opening-screen.js`, `info_page.py`, `narrative_log.py`, `announcer.js`, `pc-shell.js`.

## 10. Milestones
| # | Milestone | Content |
|---|-----------|---------|
| 1 | Flow model and judges | Graph, flow rule, voices and verdicts, plan enumerator, chapter 1 (7 valleys) with proofs |
| 2 | Map UI | SVG map, buying links and parts, share dials, Voices panel with reasons, save contract. Playable slice |
| 3 | Chapters 2-3 | 15 more valleys, farm and wild voices, Valley Atlas |
| 4 | Chapters 4-5, hints, goals | 14 more valleys (36), downstream and dry years, Voices Book, hint ladder, three-goals strip, live facts. First complete game |
| 5 | Standard kit | Opening screen, tutorial, About with Sources, What's New, keyboard help, confirm dialogs, light theme, accessibility |
| 6 | Achievements | 14 achievements, panel and toast, manifest, reachability test |
| 7 | Desktop boot and wrap-up | `pc-config.json`, `pc.css`, `pc.js`, generated `pc.html`, docs, changelog |

## 11. Open questions for the owner
1. Should every valley have a Fair share plan (everyone Content), or should a few late valleys be honest "no perfect plan" cases where Common ground is the best? Default: a Fair share plan always exists, but the late ones are tight.
2. Should the voices be able to disagree with each other in text (a short exchange) or only react to the plan? Default: react to the plan only.
