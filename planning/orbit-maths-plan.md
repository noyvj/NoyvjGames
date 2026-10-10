# Orbit Maths (slug `orbit-maths`, TODO QI-38) - Groundwork Plan

Source: the Quick ideas round (G5), owner-approved: "short maths puzzles in a rocket-launch frame (ratios, speeds, fuel)." Checked against `PLAYER-PROFILE.md`: maths, physics and space are named interests, short wins building into a bigger picture, working it out themselves, "more game than teaching", easy-to-medium base difficulty, hint ladder, no timers (a launch has no countdown to beat), nothing lost. Personal project, no BCM tag, working title. One-line pitch: a small launch team has one rocket to get right, and every number on the checklist is a short puzzle you can solve with a pencil and a calm head.

## 1. Concept
You are the numbers clerk at **Pellam Pad**, a small launch site. A launch needs a **checklist** of 40 items, each a short puzzle with a clean answer: how much fuel for a burn, how fast the second stage must be to catch the first, the mixing ratio of two propellants, how long the transfer takes. Each puzzle is a **sheet** with a low-poly picture of the situation, the numbers it gives, and one question. You type or dial an answer (a number or one pick from a short list). A correct answer ticks the item and a part of the rocket lights up.
- 2-minute session: three small ratio items (mix 2 parts to 3), a tick each.
- 20-minute session: a stage of eight items, ending with the stage's rocket section standing lit on the pad, and the optional launch animation.
- Look: dark, clean low-poly pad and rocket drawn as SVG; each sheet has its numbers set large with units written as words. Quiet; optional generated sound only via `shared/sfx.js`. The **launch** is a short, non-interactive reveal (no countdown pressure: it begins when you press **Launch**).

## 2. Rules (a pure function of the sheet and the answer)
- Each sheet has data (labelled numbers with units), a question, an expected answer (a whole number, a decimal with a stated rounding rule, or a pick from 3 to 5 options), and an **explanation** (a worked method in 3 to 5 short lines, revealed after a clear or on the Answer rung).
- The answer is checked exactly (integers, fractions) or within a stated tolerance (a half unit of the stated rounding), with the unit shown. Every sheet is **sufficient**: it can be solved from the numbers given and basic arithmetic; none depend on outside knowledge or a calculator beyond a simple one (a built-in calculator panel is available on the sheet).
- Wrong answers are never penalised: the sheet says "not yet", shows the first line of the method on request, and tries are unlimited. No clock, no randomness (Practice sheets are seeded).

## 3. Content size
- 40 sheets in five stages of eight: **Pad** (ratios, proportions, mixing), **Liftoff** (speed, distance, time, unit conversion), **Burn** (fuel use, mass, simple rocket-equation steps with given numbers), **Orbit** (circular speed from given numbers, period as distance over speed, averages), **Transfer** (combine two earlier ideas in one sheet).
- A **Practice Pad** of seeded sheets for each stage so a stage can be repeated; 12 "Real figures" bonus sheets built on live-read facts (below).
- A **Notebook** of 20 short method pages (Ratio, Rate, Units, Average...) that fill as the matching sheets are cleared.

## 4. How fairness is PROVED (tests)
- Every sheet has an independent check: the expected answer is computed twice (a reference formula and an exact `Fraction` evaluation), and the two must agree; an "unused data" lint flags any given number that the solution never uses unless the sheet marks it as a decoy.
- A **sufficiency** test: a symbolic dependency check shows the answer is a function only of the numbers listed on the sheet.
- Answer-format tests: every integer answer is an integer, every decimal sheet states its rounding, and units are consistent (a small units checker verifies dimensional consistency of the reference formula).
- Practice generator: for 2,000 seeds, the answer is exact under the stated rounding and never ambiguous. Determinism: no clock, no randomness except seeded.
- Real-figure sheets: the stored figures are dated, and the sheet still works with the stored figures if the live read fails.

## 5. Bigger picture, goals, hints
- The **Pad View** is the picture: a five-stage rocket on a dark pad whose sections light as stages complete, with a completion percentage bar. The **Notebook** is the collection.
- Three goals always visible (any order): the next three unearned achievements with counts and bars. Stats strip: Items ticked, Stages lit, Notebook pages, Practice sheets.
- Hint ladder (opt-in; first rung asks "Would you like a suggestion?"): Nudge (which of the given numbers matters), Hint (the first step of the method), Answer (the full worked method and the number, with a Fill in button; the item still ticks).
- Every stage and sheet is open from the start; the order is a suggestion.

## 6. Achievements (14; computed from facts)
1 First Tick; 2 Ten Ticks; 3 Stage Lit (a whole stage); 4 Rocket Standing (all five stages); 5 All Forty; 6 First Try (right on the first answer, 10 times); 7 Thirty First Tries; 8 Notebook Half; 9 Notebook Full (20 pages); 10 Real Figures (3 bonus sheets); 11 Whole Real Set (12); 12 Practice Twenty; 13 Launch (watch the launch); 14 Second Opinion (all three hint rungs on one sheet).

## 7. Real-world facts
The **Real figures** sheets use numbers read live from named, dated sources and shown with the read date: for example the International Space Station's orbital speed and altitude (NASA), Earth's escape velocity (NASA planetary fact sheet) and a published launch vehicle's liftoff mass and payload (the operator's user guide). If a live read fails, the stored figure and its date are shown instead. Fiction around them is invented. More game than teaching, and the sheets never claim engineering accuracy beyond the given numbers.

## 8. Stack, save and reuse
- Pyodide Python, plain HTML/CSS with code-drawn SVG, no build step. Modules: `sheets_*.py`, `units.py`, `check.py` (exact and tolerance), `gen.py` (Practice Pad), `facts.py` (stored and live figures), `notebook.py`, `rocket.py` (stage state), `progress.py`, `hints.py`, `render.py`, `achievements.py`, `info.py`, `game.py`, `app.js` (number pad, dial).
- Reuses Dead Reckoning's units and number-input patterns, `shared/seed.py`, `hint-ladder.js`, `goals-panel.js`, `save-widget.js`, `level-select.js`, the info-page kit.
- Save: ticked sheets with first-try flags, notebook, practice seeds, hint rungs, launch watched, flags.

## 9. Milestones
| # | Milestone | Content |
|---|-----------|---------|
| 1 | Engine | Sheet format, exact checker, units checker, sufficiency lint, stage 1 (8 sheets) with proofs |
| 2 | Sheet UI | Sheet layout, number pad and dial, calculator panel, method reveal, pad view, save contract. Playable slice |
| 3 | Stages 2-4, notebook, hints | 24 more sheets, Notebook, hint ladder, three-goals strip |
| 4 | Stage 5 and the launch | 8 more sheets (40 in all), Practice Pad, launch reveal. First complete game |
| 5 | Standard kit | Opening screen, tutorial, settings, About with live-read sources, What's New, keyboard help, light theme, accessibility pass |
| 6 | Achievements | 14 achievements, panel and toast, manifest, reachability test; Real figures sheets |
| 7 | Desktop boot and wrap-up | `pc-config.json`, `pc.css`, `pc.js`, generated `pc.html`, docs, changelog |

## 10. Open questions for the owner (defaults used meanwhile)
1. Should the physics stay at ratios, speeds and fuel with given numbers (no formulas to memorise), or include the real rocket equation with logarithms in the last stage? Default: simple steps with given numbers; no logarithms.
2. Should a built-in calculator be allowed on every sheet, or only on the last two stages? Default: every sheet.
