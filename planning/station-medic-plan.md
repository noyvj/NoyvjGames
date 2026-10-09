# Station Medic (slug `station-medic`, section SM, TODO QI-13) - Groundwork Plan

Source: the Quick ideas round, owner-approved: "help the crew of a space station by solving triage puzzles with limited supplies. Nobody dies on screen; a bad call means restore and try a different plan." Checked against `PLAYER-PROFILE.md`: helper and healer role (yes), quiet tragic-but-gentle and flawed characters, space and science fiction, dark moody low-poly look, many short wins that build one bigger picture, three goals always visible, easy-to-medium base difficulty, no hard-lose states, no timers, no all-good hero, optional leaderboards (none here). Personal project, no BCM tag, working title. Tone shared with `lighthouse-plan.md` (cozy with a little unease, never delivered) and the shape of `robot-script-plan.md`.

## 1. Concept
Lowlight Station is a worn ring far from anywhere, and you are its only medic since Dr. Aurel left. The infirmary is quiet and dim. Each shift a handful of crew (one to four) come in with signs. You decide which scans to run, which treatments to give, and in what order, from a small supply cabinet that restocks between shifts. Triage here is a deduction and resource puzzle, not a race: nothing counts down, the ward never changes while you think, and the answer can always be worked out from what is on screen.
**Nobody dies on screen, and nothing is ever lost.** A bad call (a wrong treatment, a reaction to a chart note, a wasted supply) does not end anything: the patient is "settled later by Tally's night round" and the shift records a cost. A cost only changes the shift's seal (Clean, Steady, Rough). You can always Restore the shift to its start and try a different plan, borrow a missing supply (cost 1), or settle a patient with comfort care (cost 1), so no state is a dead end.
**Fiction notice:** every condition, test and treatment is invented for the station. The game gives no real medical advice and never uses real drug or disease names; a banned-word lint in the tests enforces this.

## 2. The rules (a pure function of the case and the list of actions)
- A case ("shift") holds 1-4 patients, a stock of supplies, a pool of "conditions on the ring this week", and the chapter's tools (tests, beds, robot). The sheet shows the pool: each condition's signs, the scans that read positive for it, and the treatments that cure it.
- A patient shows all the signs of their true condition (two conditions at once from chapter 7: the union of both). Scans are yes/no readings (a finding is positive if any true condition carries it). The player can always list the matching conditions: signs equal, readings agree.
- Actions: `scan` (a test, uses its supply), `treat` (a treatment, uses its supply), `steady` (a steadying band or Tally), `isolate` / `release` (the quarantine bed), `comfort` (settle a patient, cost 1), `borrow` (a missing supply, cost 1), `restore` (back to the start, free).
- A cure closes the patient clean. A treatment that only eases settles them with cost 1. A treatment that cures nothing here wastes its supply, cost 1. A chart note (for example "avoids brine") forbids treatments with that tag: giving one is a reaction, cost 2, patient settled. Two `heavy` treatments on one patient clash: cost 2.
- Shaking patients cannot take a scan or treatment until steadied (a band, or Tally if assigned). Contagious patients scanned or treated in the ward cost 2 (once): isolate them first; the bed holds one patient and frees when that patient is closed or released.
- Shift grade: cost 0 Clean, 1-2 Steady, 3 or more Rough. Every grade clears the shift; the best is kept and only rises.
- Determinism: `shift.apply` has no clock and no randomness. A solver (depth-first, careful policy: scan only to split the candidates, isolate before touching a patient who might be contagious, treat only when the diagnosis is certain) runs in the tests on EVERY authored shift and must find a no-cost plan.

## 3. Hint ladder, goals, stats
- Nudge (one plain sentence about where to look), Hint (names the scan or the kind of treatment), Answer (the exact next step, with a button that does it). Free, never touches a grade, climbs one rung per press and resets with the shift.
- Three goals strip: the next three achievements that can be worked on now, each with a count and a bar, any order. Stats strip: Shifts done, Clean shifts, Records (codex pages), Patients seen. A tally panel counts scans, treatments, restores, borrows, hints, comfort rounds.

## 4. Chapters (60 shifts, 8 chapters; chapter n+1 opens at 5 of chapter n's shifts done; any order inside)
1. **Quiet Hours** (7): signs only; each condition has one look. Learn the sheet, the cabinet and the seal.
2. **The Second Look** (8): look-alike conditions; scans split them; scans cost supplies, so you cannot scan everyone.
3. **Chart Notes** (8): contraindications; the usual cure is forbidden, so use the other one; easing treatments appear.
4. **Shared Shelves** (8): supplies used by both a scan and a treatment; stock is short; triage means choosing who gets what and who is scanned.
5. **The Cold Room** (8): the quarantine bed, contagious conditions, ordering by bed.
6. **Steady Hands** (8): shaking patients, steadying bands, and Tally, a second medic robot who can steady one patient per shift.
7. **Two at Once** (7): patients with two conditions; pick cures that do not clash.
8. **The Long Night** (6): everything together; the last shift closes the station's year and the Station file.

## 5. Crew and the record
Ten crew with a short quiet story each (five or six beats, shown when you settle that crew member in an authored shift, so playing order never changes which beat comes next), plus Tally's own beats: Maren (hydroponics, hoards seed stock), Dov (chief engineer, hides a cracked-weld report), Imre (cadet who says he is older), Nell (quartermaster, adjusts the counts to keep a reserve), Teo (night cook, cannot sleep), Halloran (pilot who stopped flying), Yusra (comms, listens to one silent frequency), Kit (drone wrangler, dark jokes), Orla (commander, cold calls, warm underneath), Pell (a retired surveyor, forgetful). Everyone is flawed and gentle; the medic is too: your own log shows a habit of keeping people at arm's length. Nobody dies; some leave, some stay.
The **Record** (codex) fills in: every condition (first cured), treatment (first cure), scan (first run), crew file (per beat), and Station notes (one per chapter). It is collectable and 100% is reachable. It opens with the fiction notice.

## 6. Achievements (14; computed from facts, none hidden, none timed or luck based)
1 First Shift (1 shift); 2 Ten Shifts (10); 3 Chapter Closed (every shift of one chapter); 4 Halfway Round (4 chapters); 5 The Long Night (all 60); 6 Clean Hands (5 Clean); 7 Steady Work (25 Clean); 8 Spotless Ward (every shift Clean); 9 Careful Eyes (20 scans run); 10 Door Closed (3 quarantine shifts Clean); 11 Tally's Friend (5 robot shifts Clean); 12 Pages Filled (half the Record); 13 The Whole Record (all of it); 14 Quiet Company (every crew story told).

## 7. Stack, save and tests
- Pyodide Python, plain HTML/CSS with code-drawn SVG (low-poly faceted busts, beds, cabinet), no build step, no audio. Engine: `lexicon.py` (signs, tests, treatments, conditions), `cases_*.py` (60 shifts), `cast.py`, `shift.py` (rules), `solver.py`, `codex.py`, `progress.py`, `achievements.py`, `render.py`, `info.py`, `game.py` (`handle(json)`, `get_state()`, `load_state()`). `app.js` is glue.
- Save: best grade per shift, the unfinished shift as a list of action tokens (replayed and re-checked on load), hint rungs, tally, flags, record facts. Only fully validated state loads; new keys only when non-default; `achievements_earned` written, never read.
- Tests: lexicon consistency (every sign set distinguishable by scans), shift rules, solver on every shift (solvable, deducible, a no-cost plan), a perfect-play run earns every achievement, fiction-notice and banned-word lint (invented conditions only; no real drug or disease names, no dosing, no death words), no clock and no randomness, accessibility, shell, Desktop boot.

## 8. Milestones
| # | Milestone | Content | Status |
|---|-----------|---------|--------|
| 1 | Engine | lexicon, shift rules, solver, chapters 1-2 (15 shifts), tests | Done |
| 2 | Infirmary UI | ward, bedside panel, cabinet, sheet, log, result card, restore, save contract, favicon. Playable slice | Done |
| 3 | Chapters 3-5, hints, record | 24 more shifts, hint ladder, three-goals strip, crew files, Record (codex) | Done |
| 4 | Chapters 6-8 | 21 more shifts (60 in all), Tally, finale. First complete game | Done |
| 5 | Standard kit | opening screen, tutorial, About with the fiction notice, What's New, keyboard help, confirm dialogs, light theme, accessibility pass | Done |
| 6 | Achievements | 14 achievements, panel, toast, manifest, reachability test | Done |
| 7 | Desktop boot and wrap-up | `pc-config.json`, `pc.css`, `pc.js`, generated `pc.html`, docs, changelog | Done |

## 9. Open questions for the owner (defaults used meanwhile)
1. The sheet narrows the conditions for you (dims the ones that do not match). Keep it on by default, with a setting to turn it off for a harder game? Default: on.
2. Should a Rough shift still count toward opening the next chapter? Default: yes, any grade clears a shift.
3. Borrow (cost 1) and comfort care (cost 1) as always-available fallbacks so nothing is a dead end. Keep? Default: keep.
4. Setting and names: Lowlight Station, Tally the robot, Dr. Aurel (absent). Keep or rename? Default: keep.
5. The crew flaws (hoarded seed stock, an adjusted supply count, a hidden weld report) are gentle but real. Any you would drop? Default: keep all.
6. Chapters open at 5 of 8 shifts done. Prefer every chapter open from the start? Default: gated.
