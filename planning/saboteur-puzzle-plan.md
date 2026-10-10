# Saboteur Puzzle (slug `saboteur-puzzle`, TODO QI-33) - Groundwork Plan

Source: the Quick ideas round (E3), owner-approved: "a solo logic puzzle where you work out who among the crew is sabotaging the ship from their statements." Checked against `PLAYER-PROFILE.md`: Among Us is the best gaming memory, logic and deduction puzzles, Phasmophobia-style learn-more-get-easier, clever over fast, quiet dry humour, no all-good hero, no timers, nothing lost, a hint ladder, easy to 100%. Personal project, no BCM tag, working title. One-line pitch: six crew, one lie that matters; read their statements, mark who could be telling the truth, and name the saboteur.

## 1. Concept
The long-haul ship **Pallas** has had three small failures this week (a stuck airlock, a muted alarm, a tampered log). You are the quartermaster, the only one with no reason to lie. A **Case** gives you a crew of 4 to 8, a deck plan with rooms, a short **door log** (who passed which door when, partial) and a **statement sheet**: each crew member says one to three things ("I was in the galley the whole shift", "Orsa was with me", "Whoever muted the alarm is shorter than me"). Your job is to work out who sabotaged what.
- 2-minute session: a four-crew case, three statements each, one clean contradiction, name the saboteur.
- 20-minute session: a chapter of six cases that add roles and twists, ending with a two-saboteur case.
- Look: dark, clean low-poly deck plan and a notebook grid. Crew shown as faceted bust icons with a name and a role word, never colour alone. Quiet, dry. No on-screen harm: sabotage is a stuck door or a muted lamp. Nobody is a monster; the saboteur always has a small reason, shown on the case file after you solve it.

## 2. Rules (a pure function of the case and your marks)
- **Roles:** Crew (truthful about what they know), Saboteur (may lie), and role twists added by chapter: Engineer (truthful and knows door states), Joker (lies harmlessly, not a saboteur), Fainter (truthful but forgets one room), Pair (two crew who always agree). The roles present in a case are listed on its sheet.
- A statement is one of a small closed set of forms: located(person, room, shift), with(person, person, shift), saw(person, person, room), count(room, shift, n), height or order comparisons (chapter 5). Every statement is true or false given the real world.
- The notebook lets you tick each statement as **True**, **False** or **Unsure**, and each crew member as **Honest**, **Could lie** or **Saboteur**. The game never fills this in for you. An optional **contradiction check** (a setting, on by default) outlines marks that cannot all be right.
- Naming the wrong person is not a dead end: the game shows the statement that conflicts, you can try again, and Restore is free. Seal: Clean (first name correct), Steady, Rough; every grade clears.
- A deterministic engine: no clock, no randomness (seeded generator for Endless).

## 3. Content size
- 40 authored cases in five chapters of eight: Knights and Liars (one rule), Rooms and Shifts (adds the door log), Roles (Engineer, Joker), Pairs and Fainters, Two Saboteurs.
- An **Endless** mode with a seeded generator and a solver gate (shareable seed code like `SABOTEURPUZZLE-7G0F4`, via `shared/seed.py`).
- 24 crew with short, quiet, flawed personal files; a small Pallas log of 40 lines.

## 4. How fairness is PROVED (tests)
- `solver.py` enumerates every role assignment and every world consistent with the sheet (a small constraint search). A test requires **exactly one** consistent saboteur set per case, that every statement is used by some deduction (no filler), and that the case cannot be solved by any single statement (so you must combine).
- A "shortest deduction chain" is computed and stored for hints; tests check it is no longer than 6 steps for chapters 1 to 3.
- Endless generator: for 2,000 seeds, the solver confirms a unique answer or discards the seed; the seed to case map is deterministic.
- Tone lint: no violence; the "reason" file for each saboteur is checked for banned words.

## 5. Bigger picture, goals, hints
- The **Pallas Log** and **Crew Files** are the collection: 24 crew files fill (one beat each time that crew member appears truthful, liar or saboteur), 40 log lines fill per case. A deck map lights up with each cleared case.
- Three goals always visible (any order): the next three unearned achievements with counts and bars. Stats strip: Cases closed, Clean, Crew files, Seeds solved.
- Hint ladder (opt-in; first rung asks "Would you like a suggestion?"): Nudge (which statement to look at), Hint (which two statements conflict), Answer (the chain of deductions, step by step, and the saboteur).
- Every case is open from the start; the order is a suggestion.

## 6. Achievements (14; computed from facts)
1 First Name (1 case); 2 Ten Cases; 3 Chapter Closed; 4 All Forty; 5 Clean Eye (first name right, 5 times); 6 Twenty Clean; 7 Spotless Log (all authored cases Clean); 8 No Checks (solve 5 cases with the contradiction check off); 9 Two Saboteurs; 10 Joker Spotted; 11 Crew Files Half; 12 Crew Files Full; 13 Seeds (solve 5 endless seeds); 14 Second Opinion (all three hint rungs on one case).

## 7. Real-world facts
None, fiction. The About page may cite, read live and dated, the classic knights-and-knaves logic puzzle origins (named source) as background only.

## 8. Stack, save and reuse
- Pyodide Python, plain HTML/CSS with code-drawn SVG, no build step. Modules: `statements.py` (forms), `roles.py`, `cases_*.py`, `solver.py`, `gen.py`, `notebook.py`, `crewfiles.py`, `progress.py`, `hints.py`, `render.py`, `achievements.py`, `info.py`, `game.py`, `app.js`.
- Reuses Evidence Hunt's notebook, solver gate and seeded practice generator patterns, `shared/seed.py`, `run-code.js`, `hint-ladder.js`, `goals-panel.js`, `save-widget.js`, `level-select.js`.
- Save: best seal per case, notebook marks, crew files, endless seeds, hint rungs, flags.

## 9. Milestones
| # | Milestone | Content |
|---|-----------|---------|
| 1 | Engine | Statement forms, role rules, constraint solver, chapter 1 (8 cases) with uniqueness proofs |
| 2 | Case UI | Deck plan, statement sheet, notebook grid, naming and result card, save contract. Playable slice |
| 3 | Chapters 2-4, crew files, hints | 24 more cases, crew files, Pallas log, contradiction check, hint ladder, three-goals strip |
| 4 | Chapter 5 and Endless | 8 more cases (40 in all), seeded generator with solver gate, seed codes. First complete game |
| 5 | Standard kit | Opening screen, tutorial, settings, About, What's New, keyboard help, confirm dialogs, light theme, accessibility pass |
| 6 | Achievements | 14 achievements, panel and toast, manifest, reachability test |
| 7 | Desktop boot and wrap-up | `pc-config.json`, `pc.css`, `pc.js`, generated `pc.html`, docs, changelog |

## 10. Open questions for the owner (defaults used meanwhile)
1. Should each saboteur have a small sympathetic reason shown after the case (a debt, a fear), or should the reason stay unknown? Default: a small reason shown.
2. Should the contradiction check be on by default, with a setting to turn it off for a harder game? Default: on.
