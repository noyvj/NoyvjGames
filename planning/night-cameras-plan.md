# Night Cameras (slug `night-cameras`, TODO QI-27) - Groundwork Plan

Source: the Quick ideas round (D3), owner-approved: "investigate odd events by switching between security cameras; no jump scares, and the answer is a deduction." Checked against `PLAYER-PROFILE.md`: loves Phasmophobia's investigate-and-learn feel and anomaly games, deduction, spatial and logic puzzles, helper role, dark moody, quiet, no timers, no jump scares, no gore, a hint ladder, easy to 100%, a bigger picture that fills in. Personal project, no BCM tag, working title. One-line pitch: a night desk with eight small monitors; something odd happened in the building and the footage, scrubbed frame by frame, tells you what, with a gentle answer every time.

## 1. Concept
You are the overnight watcher at **Hollis Cold Annex**, a mostly empty building (an invented records store with a loading dock, a lift and a rooftop). Each **Case** begins with a one-line report ("The east door was open at six", "The lift went up on its own", "A box moved"). Eight cameras show fixed views as small low-poly stills; a **scrub bar** steps through twelve fixed frames of the night (no real time, no playback pressure). People and things (a cleaner, a courier, the cat, a maintenance robot, the draught, a delivery drone) move between rooms on schedules you can only see where a camera looks. You switch cameras, compare frames, mark what you saw on a **who-was-where** grid, then name the cause: who or what, and where/when.
- 2-minute session: a one-room, three-camera case: scrub four frames, see the courier leave the door ajar, answer.
- 20-minute session: a chapter of six cases, ending with an odd case that chains two events.
- Look: dark, clean low-poly stills (SVG), rooms as a small floor plan, a faint "REC" caption (text, not blood-red flash). No sudden motion, no loud events, no faces in distress. Every answer is a mundane or quietly sad one (a robot looking for an old route; the night cleaner moving a box to reach a plug).

## 2. Rules (a pure function of the case and the notebook)
- The world is a small deterministic simulation: a floor-plan graph, 2 to 5 actors with fixed schedules (room per frame), and a few object states (door open or shut, box moved, light on or off). Frames are rendered from the true world.
- A camera covers certain rooms (some cover a corridor and a doorway; some are **down** on certain frames; some have a blind side). You only ever see what a camera shows.
- The notebook (who-was-where grid, with Seen / Not seen / Maybe marks) is the player's, never the game's. Optionally the game can outline contradictions between marks and footage (a setting, on by default).
- The final answer picks an actor and a time frame (and for chained cases, two). A wrong answer is never a dead end: the game says which frame contradicts it and keeps the notebook. Seal grades: Clean (first answer), Steady, Rough; every grade clears.
- Determinism: no clock, no randomness.

## 3. Content size
- 36 cases in six chapters: One Door, Two Rooms, The Lift, Blind Corners, Tampered Footage (a camera down at the key moment), The Long Night (chained cases).
- 14 actors in the cast across all cases; 6 buildings (annex floors, dock, roof, archive stack, plant room, lobby).
- A **Night Book** of 40 quiet "what was it" notes (each solved case adds its one-line explanation and an invented witness remark).

## 4. How fairness is PROVED (tests)
- A hypothesis solver (`tools/solver.py`) enumerates every actor-per-frame assignment that is consistent with the footage the cameras can show and the case sheet. A test requires **exactly one** consistent culprit/frame at the end, and that the minimum set of cameras needed is at most the case's listed set (so the case can be solved with the footage given).
- It also proves **no single camera** solves any case above chapter 1 (so switching matters), and that every camera listed is useful (removing it makes the case ambiguous).
- Frame renderer test: every frame is a pure function of the world; the same case always makes the same eight images.
- Tone lint: no jump-scare, gore or death words in captions; no sudden-change flag in any frame diff.

## 5. Bigger picture, goals, hints
- The **Annex map** is the picture: six floors/areas, each dark until a case there is cleared, then lit with a small plaque. The Night Book fills as cases close.
- Three goals always visible (any order): the next three unearned achievements with counts and bars. Stats strip: Cases closed, Clean, Cameras used, Night Book notes.
- Hint ladder (opt-in; first rung asks "Would you like a suggestion?"): Nudge (which frame to look at), Hint (which camera shows the key moment), Answer (marks the culprit's route on the grid and offers to fill the answer).
- Every chapter and case is open from the start; the order is only a suggestion (cases get harder down the list).

## 6. Achievements (14; computed from facts)
1 First Case; 2 Ten Cases; 3 Chapter Closed; 4 Whole Night (all 36); 5 Clean Eye (first answer right, 5 times); 6 Twenty Clean; 7 Spotless Log (every case Clean); 8 Right Camera (solve with the fewest cameras 5 times); 9 Blind Corner Cleared (a case with a camera down); 10 Two Events (a chained case); 11 Night Book Half; 12 Night Book Full; 13 Second Opinion (all three hint rungs on one case); 14 Quiet Building (see all six areas lit).

## 7. Real-world facts
None, fiction. The building, people and events are invented. The About page may note, read live and dated, the public explainer on how CCTV frame rates and blind spots work (named source), marked as background only.

## 8. Stack, save and reuse
- Pyodide Python, plain HTML/CSS with code-drawn SVG stills, no build step, no audio. Modules: `world.py` (graph, actors, schedules), `cases_*.py`, `cameras.py`, `frames.py` (render data), `notebook.py`, `solver.py`, `nightbook.py`, `progress.py`, `hints.py`, `render.py`, `achievements.py`, `info.py`, `game.py`, `app.js`.
- Reuses Evidence Hunt's notebook marks pattern, Dead Reckoning's step-by-step reveal idea, `shared/hint-ladder.js`, `goals-panel.js`, `save-widget.js`, `level-select.js`.
- Save: best seal per case, the notebook marks per open case, hint rungs, flags, tally. Only validated state loads.

## 9. Milestones
| # | Milestone | Content |
|---|-----------|---------|
| 1 | Engine | World graph, schedules, camera coverage, frame builder, hypothesis solver, chapter 1 (6 cases) with proofs and tests |
| 2 | Desk UI | Monitor wall, scrub bar, floor plan, notebook grid, answer and result card, save contract. Playable slice |
| 3 | Chapters 2-4, Night Book, hints | 18 more cases, Night Book, annex map, hint ladder, three-goals strip |
| 4 | Chapters 5-6 | 12 more cases (36 in all), camera-down cases, chained cases. First complete game |
| 5 | Standard kit | Opening screen, tutorial, settings, About, What's New, keyboard help, confirm dialogs, light theme, accessibility pass |
| 6 | Achievements | 14 achievements, panel and toast, manifest, reachability test |
| 7 | Desktop boot and wrap-up | `pc-config.json`, `pc.css`, `pc.js`, generated `pc.html`, docs, changelog |

## 10. Open questions for the owner (defaults used meanwhile)
1. Should the game mark contradictions between your notes and the footage for you (a setting), on or off by default? Default: on.
2. Is a mundane or gently sad explanation for every case right, or should a few cases stay unexplained (an anomaly note, like Lighthouse's optional layer)? Default: every case explained.
