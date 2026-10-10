# Evidence Hunt (slug `evidence-hunt`, section EH, TODO QI-29) - Groundwork Plan

Source: the Quick ideas round, owner-approved: "Evidence Hunt: a Phasmophobia-lite deduction game where you collect evidence and name the ghost, solo first with an optional co-op by invite code." Checked against `PLAYER-PROFILE.md`: investigative, learn-the-rules feel, puzzle-like, dark moody low-poly look, short wins that build a bigger picture, three goals always visible, collecting, no jump scares or on-screen harm, no hard-lose states, no timers, easy-to-medium base difficulty with options for harder play, hints only on request. Tone shared with `lighthouse-plan.md` (every odd detail has a warm resolution) and the shape of `station-medic-plan.md` (deduction, solver-checked fairness, restore). Personal project, no BCM tag, working title. SOLO only; co-op is parked. Hub registration is a separate job.

## 1. Concept
You are the quiet investigator the client calls when a house feels wrong. Each case is a haunted house drawn as a dark floor plan. You open the client's book of **visitors** (the sheet), pack a few pieces of equipment, walk the rooms by tapping them, take readings that come back as plain text, and work out which kind of spirit is in the house from the evidence rules. Then you name it. **Spirits are fictional and gentle in outcome:** a solved case ends with a quiet warm note about who the spirit was (a piano tuner who loved the house, a child waiting for a parent who is on the way). There is no audio, no jump scare, no timer, no chase, nobody is harmed on screen and nothing is ever lost. The kinds, houses and readings are all invented.
Fiction notice on the About page: the spirits and rules are made up and the game says nothing about the real world.

## 2. The rules (a pure function of the case and the list of actions)
- **Evidence (6)**, each read with one piece of **equipment**: Cold spot (thermometer), Stray charge (EMF reader), Writing (notebook), Faint lights (camera), Prints (dust), Glow marks (violet lamp).
- **Spirit kinds (12)**, each with exactly 3 evidence and 2 **behaviours** (tidy, mover, shy, curious, fond of one room, roams). Evidence sets are chosen so kinds overlap in two of three, so one reading never decides alone. Behaviours come as the client's account (a line or two in the case file) and from how many rooms are restless (fond = one, roams = two or more).
- **A case** holds a house (rooms on one to three floors), a short list of suspects on the sheet, the truth (one kind, or two in the "two presences" chapter), the restless rooms, a kit size (3 or 4 pieces), and room features. Entering a room is free and shows at once whether it is **restless** or **still**. A reading is **positive** in a restless room if the spirit there has that evidence, **clear** if not. A room **feature** (draughty window, old wiring, writing desk, street-lit window, damp floor, glow paint) makes one reading there **doubtful**: it looks positive but is only the house, so it counts as no information. A **keepsake** (chapter 4) masks every reading in its room, and looking at it gives one more line of testimony.
- **Kit:** pick up to the kit size before your first reading; after that a swap is "back to the van" (a second trip, cost 1). Walking, entering and looking are always free.
- **Accuse:** name the kind (or the two kinds). Right ends the case. Wrong costs 1 and nothing else: the notebook stays and you can try again or Restore (free). Two presences: a half-right answer says so.
- **Seal:** cost 0 Clean, 1-2 Steady, 3 or more Rough. Every seal clears the case; the best is kept and only rises.
- **Determinism:** `Case.apply` has no clock and no randomness. A solver runs in the tests on EVERY authored case: from the case file alone (rooms, accounts, sheet) a careful plan with one trip and no wrong accusation must exist, the answer must be unique once everything is read, and kit choice must matter.

## 3. Hint ladder, goals, stats
- Nudge (a plain sentence), Hint (names the equipment or room), Answer (the exact next step with a "Do it for me" button). Free, never touches a seal, climbs one rung per press and resets after each action. Opt-in only, never highlighted unasked.
- Three goals always visible (the next three unearned achievements, any order, with bars). Stats strip: Cases solved, Clean cases, Guide pages, Readings. Tally (collapsed): rooms entered, readings, accusations, second thoughts (wrong), restores, hints, trips, sandbox cases.
- **From memory (optional):** cover the sheet's evidence lines for kinds whose guide page is already complete. Never forced.

## 4. Chapters (40 cases, 5 chapters; chapter n+1 opens at 5 of chapter n's cases; any order inside)
1. **First Visits** (8): more rooms each time, from three to seven, one or two restless rooms, a sheet of three to five, kit of 3.
2. **Misleading Readings** (8): features make readings doubtful; a good plan reads the restless room that the house does not fool.
3. **Two Presences** (8): two spirits in two restless rooms; name both.
4. **Keepsakes** (8): a keepsake masks its room and carries one more line of testimony; returning it is the warm end.
5. **The Big Houses** (8): ten to fourteen rooms on three floors, everything together, kit of 4; the last case closes the book.

## 5. Sandbox and the field guide
- **Sandbox:** a generated case from a short code `EH3-1K9X2` (difficulty 1-5 plus a base-36 seed, the pattern of Dead Reckoning's practice codes). The same code always makes the same house; the generator keeps only cases the solver proves fair, and a seed that fails falls back to a nearby one. Sandbox cases count toward guide evidence, readings and an achievement but never gate or change authored seals. No shared files are edited.
- **Field guide (codex, collectable):** Spirits (12; a page fills as you confirm its evidence by positive readings and learn it when you name it correctly, then adds its note), Evidence (6, first positive reading), Equipment (6, first use), Keepsakes (8, returned), House notes (5, one per finished chapter). 37 pages; all reachable from the authored cases alone.

## 6. Achievements (14; computed from facts, none hidden, none timed or luck based)
1 First Case; 2 Ten Cases; 3 Chapter Closed (all cases of one chapter); 4 Three Chapters; 5 The Last House (all 40); 6 Clean Work (5 Clean); 7 Spotless Book (all Clean); 8 Careful Notes (60 readings); 9 Every Spirit (12 met); 10 Two at Once (4 two-presence cases); 11 Keepsakes Home (all 8 returned); 12 Fresh Eyes (3 sandbox cases); 13 From Memory (5 cases with the sheet covered); 14 The Whole Guide (every page).

## 7. Stack, save and tests
- Pyodide Python, plain HTML/CSS (floor plan as a grid of faceted room tiles, code-drawn SVG scene and kind emblems), no build step, no audio. Modules: `lexicon.py`, `houses.py`, `casekit.py`, `cases_1..5.py`, `casework.py` (rules), `solver.py` (fairness and the policy behind hints), `gen.py` (sandbox), `progress.py`, `codex.py`, `achievements.py`, `render.py`, `hints.py`, `info.py`, `game.py` (`handle(json)`, `get_state()`, `load_state()`), `app.js` glue.
- Save: best seal per case, the unfinished case as a list of action tokens (replayed and re-checked on load), tally, guide facts, sandbox progress. Only fully validated state loads; new keys only when non-default; `achievements_earned` written, never read.
- Tests: lexicon consistency, case rules, solver on every case, a perfect-play run that earns every achievement, banned-word lint (death, gore, timer, energy words), no clock or randomness in code, accessibility, shell, Desktop boot.

## 8. Milestones
| # | Milestone | Content | Status |
|---|-----------|---------|--------|
| 1 | Engine | lexicon, houses, case rules, solver, all 40 cases, tests | Done |
| 2 | Case UI | floor plan, kit, notebook, accuse, restore, save contract, favicon. Playable slice | Done |
| 3 | Guide and hints | hint ladder, three-goals strip, field guide, keepsake return | Done |
| 4 | Sandbox and finale | seeded codes, generator, last case. First complete game | Planned |
| 5 | Standard kit | opening screen, tutorial, About with the fiction notice, What's New, keyboard help, confirm dialogs, light theme, accessibility | Planned |
| 6 | Achievements | 14 achievements, panel, toast, manifest, reachability test | Planned |
| 7 | Desktop boot | `pc-config.json`, `pc.css`, `pc.js`, generated `pc.html`, docs | Planned |

## 9. Open questions for the owner (defaults used meanwhile)
1. Restless rooms mark themselves the moment you step in. Prefer finding them only by taking readings (harder)? Default: marked, with a later optional hard setting.
2. The client's account gives behaviours for free. Prefer the player to infer them from room signs instead? Default: account.
3. Kit of 3 (4 in the big houses) makes you choose. Prefer taking everything and no choice? Default: kit of 3 to 4.
4. A second trip to the van costs a seal point. Prefer it free? Default: costs 1.
5. Spirit kind names (Hearthkeeper, Glimmer, Draughtling, Scrivener, Candlewick, Pacer, Lullwisp, Tangle, Mothlight, Ledger, Hushling, Spindle) and the warm endings. Keep or rename? Default: keep.
6. Co-op by invite code is parked. Revisit after the solo game is played? Default: parked.
