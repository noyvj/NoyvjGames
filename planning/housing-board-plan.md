# Housing Board (slug `housing-board`, TODO QI-20) - Groundwork Plan

Source: the Quick ideas round (B8), owner-approved: "allocate a limited set of homes between competing needs and see how each side judges the result." Checked against `PLAYER-PROFILE.md`: housing named as a caring topic, helper role, real-world games show several points of view, planning with no randomness, "fun that happens to be accurate", three goals, no timers, nothing lost. Personal project, no BCM tag, working title. Different from Water Works (a spatial flow network): this is an assignment puzzle with a panel of judges.

Pitch: match households to a few available homes, then hear five members of the allocation board say what they think and why, until you find an arrangement every side can accept.

## 1. Concept
- You are the clerk of an invented town's allocation board (Linden Reach). Each round, a handful of homes come free (a ground-floor flat, a three-bed house, a studio near the station) and a longer list of households wait: a family of five, a nurse on night shifts, an older man who cannot manage stairs, a student couple, a young person leaving care. You assign each home to one household (or hold it for a later round when the rules allow). Then the board speaks.
- 2-minute session: one small round (3 homes). 20-minute session: a chapter of four or five rounds.
- Look: dark council office, faceted low-poly floor plans of homes as cards, households as small portraits with shape tags. Quiet respectful tone; no one is a villain, each voice has a fair point.

## 2. Core rules (pure functions)
- Homes have attributes: bedrooms, step-free access, nearness to work/school/care, rent band, and a "hold" flag. Households have needs: size, accessibility need, a work/school/care anchor, time already waiting, and an urgency (a safe place tonight).
- Assignment: drag a household to a home (one each). Unassigned households stay on the list. The Board's five voices judge using explicit, on-screen rules: the Tenants' Advocate (need and urgency first), the Access Officer (accessible homes go to those who need them), the Finance Officer (rent band and void costs), the Landlords' Association (stable, consistent rules and fair waiting), and a Neighbour from the street (balanced streets, keeping local ties).
- Verdicts per voice: Pleased, Mixed, Concerned, each with one plain reason. Cleared when no voice is Concerned (Settlement); Pleased by at least three is Good Fit; all five Pleased is Common Ground.
- Reset any round freely; nothing is lost.

## 3. Content size
30 rounds in 5 chapters of 6: The Small Street (3 homes, 3 households), Waiting Lists, Access First, Money Is Tight (adds the Finance voice's cost rule), The Whole Estate (5 homes, 8 households). Chapter n+1 opens at 4 of 6; any order inside. Households and voices are invented and recurring.

## 4. How fairness is PROVED
- Dev tool `tools/assign.py` brute-forces all assignments for every round (at most 8 homes, so at most 40,320 permutations of choosing households) and counts those with no Concerned voice. Tests assert at least one Settlement exists per round, a Common Ground assignment exists in at least 70% of rounds, and for each round the "obvious" assignment (first on the list gets the best home) leaves at least one voice Concerned in the starred rounds, so the puzzle is real.
- Voice rules are data, each shown in words on screen; tests lint that every verdict text names which rule decided it. Determinism: no clock, no random.
- Respect lint: no stereotyping words, every household has dignity-first wording.

## 5. Collection and 100%
- The Case Book: 30 round files, each stamped Settlement, Good Fit or Common Ground, plus 24 named households and 5 board members whose notes grow as you meet them. A town map of Linden Reach fills in street by street. 100% = all 30 rounds Settled; Good Fit and Common Ground stamps are bonus columns. States only go up.

## 6. Goals and hint ladder
- Three always-visible goals, any order, with bars. Stats strip: Rounds settled, Good Fits, Common Grounds, Households housed. The tally counts assignments and resets.
- Ladder (first rung asks "Would you like a suggestion?"): Nudge (which household has the fewest suitable homes), Hint (one assignment as a ghost with the voice it satisfies), Answer (a Settlement as ghosts, with a button). Free, on request.

## 7. Achievements (14)
First Home; Ten Rounds; Twenty Rounds; All Thirty; Settlement (first); Good Fit (10); Common Ground (10); Small Street Done; Access First Done; Money Is Tight Done; The Whole Estate; Neighbours Met (12 households); Whole Case Book (all 24 + 5); Fair Hearing (hear every voice's reason on a round before assigning).

## 8. Real-world facts
Each chapter opens with two or three dated facts read live from named sources: the UK Department for Levelling Up, Housing and Communities homelessness statistics (gov.uk/government/collections/homelessness-statistics), the US HUD Annual Homeless Assessment Report (huduser.gov) and Eurostat's housing cost overburden data (ec.europa.eu/eurostat), each with a read date, bundled snapshot as fallback. The About page shows how the five voices map to real arguments, without telling the player which is right. Households are invented. Fun first, accurate second.

## 9. Reuse
Assignment logic and result-card style from Heist Committee and Trade Empire; case-book pattern from Station Medic; shared `level-select.js`, `hint-ladder.js`, `goals-panel.js`, `opening-screen.js`, `info_page.py`, `narrative_log.py`, `announcer.js`, `pc-shell.js`.

## 10. Milestones
| # | Milestone | Content |
|---|-----------|---------|
| 1 | Rules and judges | Homes, households, five voices, verdict engine, assignment brute-forcer, chapter 1 (6 rounds) with proofs |
| 2 | Board UI | Home cards, household portraits, drag assign, voices panel with reasons, reset, save contract. Playable slice |
| 3 | Chapters 2-3 | 12 more rounds, waiting lists and access, Case Book |
| 4 | Chapters 4-5, hints, goals | 12 more rounds (30), finance voice, whole estate, town map, hint ladder, three-goals strip, live facts. First complete game |
| 5 | Standard kit | Opening screen, tutorial, About with Sources, What's New, keyboard help, confirm dialogs, light theme, accessibility |
| 6 | Achievements | 14 achievements, panel and toast, manifest, reachability test |
| 7 | Desktop boot and wrap-up | `pc-config.json`, `pc.css`, `pc.js`, generated `pc.html`, docs, changelog |

## 11. Open questions for the owner
1. Should one late chapter include a round with no Common Ground (an honest tension) where Settlement is the best possible? Default: no, every round has a Settlement and most have Common Ground.
2. Is a policy-flavoured country setting (UK, US, neutral invented) preferred? Default: a neutral invented town.
