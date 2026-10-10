# Food Bank (slug `food-bank`, TODO QI-19) - Groundwork Plan

Source: the Quick ideas round (B7), owner-approved: "plan a week of meals and deliveries for a food bank with a limited budget and several families' needs." Checked against `PLAYER-PROFILE.md`: food named as a caring topic, helper role, planning with no randomness, real-world games show several points of view, "fun that happens to be accurate", three goals, no timers or pressure, nothing lost. Personal project, no BCM tag, working title.

Pitch: stock the shelves, pack the boxes and plan the deliveries for one week so that every family gets what they actually need, on a budget that never quite stretches.

## 1. Concept
- You coordinate a small neighbourhood food bank (invented: Larch Street Pantry). A week is seven days. Each day brings donated lots that arrive by fixed schedule (a case of tinned beans on Tuesday), a budget to buy fresh items, and a pack-and-deliver step. Each family has a card: how many, what they cannot eat (allergy, no pork, vegetarian), whether they can cook or have a fridge, the days they can receive a delivery, and what would help most (extra baby food, soft foods for an elderly neighbour).
- 2-minute session: pack one day's boxes. 20-minute session: plan and finish a full week.
- Look: dark storeroom with warm lamps, faceted low-poly crates and boxes; allergen and diet marks as shape plus word (e.g. a "N" tile for nuts). Quiet, respectful tone: families are people, each with a name and a short line, never a statistic.

## 2. Core rules (pure functions)
- State: shelf stock by item with a "good until" day (shown as a number, spoilage is a puzzle constraint inside a week, not a clock), money, and per-family needs met so far.
- Actions per day: buy (within the day's budget), pack a box (choose items for a family), schedule a delivery (a day the family allows) or a pickup, and swap an item. Nothing is lost by changing a plan; the week can be reset to any day.
- Each family scores Met (all needs met and nothing they cannot eat), Mostly (all safe, one want missing) or Short (any unsafe item, or a core need missing). An unsafe item (an allergen) cannot be packed at all: the game blocks it with a plain explanation, not a punishment.
- Week result: every family Met is "Full week"; every family at least Mostly is "Covered"; the budget is a hard rule you plan within.

## 3. Content size
36 weeks in 6 seasons of 6: First Week (3 families, easy), Autumn Intake, Winter Boxes, Spring Gaps, Summer Holidays (school meals gap), The Big Week (6 families and tight budget). Week n+1 opens at 4 of 6 done; any order inside. Families recur across weeks with their own short notes.

## 4. How fairness is PROVED
- Dev tool `tools/plan.py` is a depth-first search with pruning over buy/pack/schedule actions for every week. Tests assert a Full week plan exists within the budget; the cheapest Full week cost is stored as par; and the obvious greedy plan (packing the cheapest items first) is shown to leave at least one family Short in the starred weeks, so the planning matters.
- Allergen and diet rules have table tests; spoilage dates are validated so no donated lot is unusable before it arrives; determinism (no clock, no random).
- Respect lint: every family line is checked against a banned-words list (no stereotyping, no pity language).

## 5. Collection and 100%
- The Pantry Wall: a board of 36 weeks and a Neighbours book of 24 named families and volunteers, each with a short note that grows as you serve them (e.g. what a daughter likes for lunch). 100% = all 36 weeks Covered; Full week stamps are a second column and a bonus. States only go up.

## 6. Goals and hint ladder
- Three always-visible goals, any order, with bars. Stats strip: Weeks covered, Full weeks, Families met, Meals packed. The tally counts boxes packed and deliveries scheduled.
- Ladder (first rung asks "Would you like a suggestion?"): Nudge (which family is hardest to feed and why), Hint (one purchase or box as a ghost), Answer (the cheapest Full week as a ghost, with a "Plan it" button). Free, on request.

## 7. Achievements (14)
First Box; Ten Weeks; Twenty Weeks; All Thirty-Six; Covered (first); Full Week (10); Every Season Covered; Thrifty (finish 5 weeks 10% under budget); Allergy Safe (20 weeks with no blocked allergen attempt); Neighbours Book (12 notes); Whole Book (all 24); Summer Gap Closed; The Big Week; Quiet Hands (500 meals packed).

## 8. Real-world facts
Each season opens with two or three dated facts read live from named sources: the FAO State of Food Security and Nutrition report data (fao.org/publications/sofi), the USDA Household Food Security report (ers.usda.gov) and Our World in Data (ourworldindata.org) on hunger, each with a read date, with a bundled snapshot as fallback. Several points of view are shown on the About page (volunteer, donor, family, shopkeeper). Families and numbers inside the game are invented and marked so. Fun first, accurate second.

## 9. Reuse
Supply-and-allocation logic style from Station Medic's cabinet and Trade Empire; daily-step planner pattern from Pocket Bazaar; collection book from Station Medic's Record; shared `level-select.js`, `hint-ladder.js`, `goals-panel.js`, `opening-screen.js`, `info_page.py`, `narrative_log.py`, `announcer.js`, `pc-shell.js`.

## 10. Milestones
| # | Milestone | Content |
|---|-----------|---------|
| 1 | Rules and planner | Items, needs, spoilage, packing and delivery rules, plan search, season 1 (6 weeks) with proofs |
| 2 | Pantry UI | Day view, shelf and box panels, family cards, delivery planner, reset to any day, save contract. Playable slice |
| 3 | Seasons 2-4 | 18 more weeks, new needs, Pantry Wall and Neighbours book |
| 4 | Seasons 5-6, hints, goals | 12 more weeks (36), summer gap and big week, hint ladder, three-goals strip, live facts. First complete game |
| 5 | Standard kit | Opening screen, tutorial, About with Sources, What's New, keyboard help, confirm dialogs, light theme, accessibility |
| 6 | Achievements | 14 achievements, panel and toast, manifest, reachability test |
| 7 | Desktop boot and wrap-up | `pc-config.json`, `pc.css`, `pc.js`, generated `pc.html`, docs, changelog |

## 11. Open questions for the owner
1. Should the diet and allergy rules use real-world categories (nut allergy, halal, vegetarian) or invented ones? Default: a small set of real categories, handled respectfully.
2. Is a "what would you change" voice from volunteers or families after each week wanted? Default: yes, one short line per family.
