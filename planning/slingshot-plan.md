# Slingshot (slug `slingshot`, TODO QI-6) - Groundwork Plan

Source: the Quick ideas round (A6), owner-approved: "plan fuel burns and gravity assists to reach moons in a simple but real solar-system model, with the planet data read from a named source." Checked against `PLAYER-PROFILE.md`: space, physics named as an interest, planning three steps ahead (no randomness), collecting every moon, solve one puzzle at a time, "more game than teaching", Kerbal bounced them (so no cockpit flying or tutorial wall), no timers. Personal project, no BCM tag, working title.

Pitch: plan a probe's burns on a quiet chart, then watch the flight play out exactly as planned, and use planets' gravity to reach each moon on a fuel budget.

## 1. Concept
- You are a flight planner at a small mission desk (invented: Kestrel Desk). Each mission names a moon and gives a probe with a fuel budget in "delta-v". You place burns (when, which way, how much) on a timeline, press Fly, and the probe follows the plan on a top-down chart. Nothing is piloted live; you adjust the plan and fly it again.
- 2-minute session: one short transfer. 20-minute session: a gravity-assist mission to a far moon, tuned over a few tries.
- Look: dark star chart, faceted low-poly planets, glowing path with tick marks; moons as small labelled points with the chart zoom steps. Quiet voices: the probe's flat status lines, one dry note from the desk supervisor (optional).

## 2. Core rules (a deterministic simulation)
- Model: 2D, the Sun plus the eight planets on circular coplanar orbits (periods and radii from the data source), probes follow gravity from the Sun and the nearby planet in a fixed-step integrator (velocity-Verlet, fixed step, no float randomness). Planet moons are reached by patched-conic: once inside a planet's sphere of influence the probe's motion is planet-centred and the target moon is a point on a circular orbit around it.
- A burn is (start step, heading, strength). Total strength must not exceed the budget. Success: pass within the moon's capture radius at a speed below its capture speed (a short brake burn is part of the plan). A miss is not a loss: Fly just ends with a report ("passed 1.2 million km wide") and you edit the plan.
- Scrubber: drag back and forth over the whole flight; the game also shows a "predicted path" for the next burn so planning is not trial and error.

## 3. Content size
36 missions in 5 chapters: Near Neighbours (Moon, direct transfers), The Inner Run (Mars with Phobos and Deimos), Slingshots (Venus and Earth assists), Giants (Jupiter's four big moons), Far Shore (Saturn, Titan, Uranus, Triton). Chapter n+1 opens at 5 of n done; any order inside.

## 4. How fairness is PROVED
- Every mission has a stored reference plan (burns list). Tests fly it in the real engine and assert it succeeds with at least 10% budget to spare; the budget is the reference cost plus 25% slack so the player is not asked for perfection.
- Determinism: same plan twice gives the same path to the last digit (fixed step, no random, no clock). Test of energy drift (a free-flying probe loses less than 0.5% of orbital energy over a year) and period checks for each planet against the source data.
- A solver (dev tool `tools/porkchop.py`) scans launch window and burn size on a coarse grid and confirms that at least one distinct second plan exists (so the mission is not a single narrow needle).
- Live-data test: parsing of the data file is covered by fixtures; the offline snapshot loads when the network does not.

## 5. Collection and 100%
- The Moon Atlas: a chart of the Solar System with 36 destinations marked, each lit when reached, with the best fuel ("saved 12%"). Moon cards show a short fact. 100% = all 36 reached at any fuel; "Thrifty" (under reference fuel) is a bonus. States only go up.

## 6. Goals and hint ladder
- Three always-visible goals: next three unearned achievements with bars. Stats strip: Moons reached, Fuel saved, Flights, Hints. The tally counts flights and burns edited.
- Hint ladder (first rung asks "Would you like a suggestion?"): Nudge (which body's gravity helps and roughly when), Hint (ghost of the first burn), Answer (the whole reference plan as a ghost with a "Use it" button). Free, on request, never touches a medal.

## 7. Achievements (14)
First Flight; Near Neighbour (reach the Moon); Red Neighbour (Mars); Ten Moons; Twenty Moons; All Thirty-Six; Slingshot (first gravity assist); Double Assist; Thrifty (5 missions under reference fuel); Frugal Fleet (20 missions under); Four Giants (Jupiter's big moons); The Ringed One (Titan); Far Shore (Triton); Scrubber (use the scrubber 100 times).

## 8. Real-world facts
Planet masses, radii, orbital radii and periods and the moon radii are read live from the NASA Planetary Fact Sheet and JPL Solar System Dynamics "Planetary Satellite Physical Parameters" pages, with the read date shown on the Sources page and each atlas card, and a bundled snapshot as offline fallback (marked "bundled copy, dated"). The model is simplified (circular, coplanar) and the About page says so plainly. More game than teaching.

## 9. Reuse
Seeded-sim pattern from Dead Reckoning (`sim.py`, stored par routes, `charts` data); SVG chart rendering; shared `level-select.js`, `hint-ladder.js`, `goals-panel.js`, `opening-screen.js`, `info_page.py`, `pc-shell.js`, optional `sfx.js`.

## 10. Milestones
| # | Milestone | Content |
|---|-----------|---------|
| 1 | Physics core | Planet data module, integrator, burns, patched-conic capture, reference-plan checker, chapter 1 (7 missions) with proofs |
| 2 | Planner UI | Chart, burn editor, Fly, scrubber, predicted path, results card, save contract. Playable slice |
| 3 | Chapters 2-3 | 15 more missions, Mars moons, gravity assists, mission picker, Moon Atlas |
| 4 | Chapters 4-5, hints, goals | 14 more missions (36 total), giants and far shore, hint ladder, three-goals strip, live data. First complete game |
| 5 | Standard kit | Opening screen, tutorial, About with Sources, What's New, keyboard help, confirm dialogs, light theme, accessibility |
| 6 | Achievements | 14 achievements, panel and toast, manifest, reachability test |
| 7 | Desktop boot and wrap-up | `pc-config.json`, `pc.css`, `pc.js`, generated `pc.html`, docs, changelog |

## 11. Open questions for the owner
1. Is 2D circular-orbit "simple but real" the right level, or do you want elliptical orbits for the inner planets? Default: circular, said plainly on About.
2. Reached-with-any-fuel counts as 100%; is "Thrifty" only a bonus? Default: yes, bonus only.
