# Glitch Hunter (slug `glitch-hunter`, TODO QI-23) - Groundwork Plan

Source: the Quick ideas round (C3), owner-approved: "small levels with deliberate, harmless exploits; the goal is to break the rules and the log records every glitch you found." Checked against `PLAYER-PROFILE.md`: loves watching glitch and build-breaking videos, feels clever finding the one broken build, collecting and solving, a collection that fills in, three goals at once, easy to 100%, no tutorial needed, no timers, nothing lost, dry dark humour. Personal project, no BCM tag, working title. One-line pitch: you are a night-shift tester in an old test lab; every tiny room states its rules, and your job is to break them on purpose and log how.

## 1. Concept
Each level is a **test room**: a small grid world (4x4 to 8x8) from a dead company's build, with a card on the wall that lists its rules in plain words ("Doors need a key. A box moves one tile when pushed. You carry one thing."). Somewhere in the room's code is a flaw. You are not trying to win the room; you are trying to find an action sequence that makes one of the posted rules false (carry two things, walk through a door, push a box through a wall, reach the exit with no key). When the rule breaks the room shows a calm "GLITCH" stamp, the room does not crash, and the **Glitch Log** gains a page: the rule that failed, your exact moves replayed as a small clip, and a one-line dry note from the tester before you ("Boxes remember where they were. Rude.").
- 2-minute session: open Room 3, read the three rules, push a box into a door on the same move you step, see the stamp, read the log page, take the next room.
- 20-minute session: a chapter of six rooms where later rooms reuse earlier flaws in new ways, ending with filling gaps in the log from rooms you skipped.
- Look: clean dark low-poly, one flat-faceted SVG tile set, glitches shown by a brief outline shift plus a text stamp (never colour alone). Quiet; optional generated sound cues only through `shared/sfx.js`.
- Everything is harmless: no crash screens, no lost saves, no real exploits of the player's browser or the site. "Reset room" is free and instant.

## 2. Rules (a pure function of room, state and moves)
- The room engine is a small deterministic rule set (move, push, pick up, drop, use key, conveyor, switch, counter). Each room switches on a few **quirks**, each a named, deliberate defect in one rule: Same-Step (two effects resolve in the wrong order), Off-By-One (a boundary check lets you step one tile too far), Wrap (a counter rolls from 255 to 0), Double-Apply (an item effect fires twice), Stale-Copy (a box keeps its old position for a step), Sticky-Slot (the carry slot is not cleared). Quirks are plain flags in the room file, so the engine code is clean and the flaw is data.
- A **glitch** is an engine event the room's rule card says cannot happen. Each room lists its glitches (1 to 3) with a short id, the rule it breaks and a par move count.
- Fixed room contents, no randomness, no clock. An optional **Free Poke** mode lets you try anything in a room with no goals; the log still records any glitch found.

## 3. Content size
- 36 test rooms in six chapters of six: Doors and Keys, Pushing Boxes, Conveyors, Counters, Order of Things, Everything At Once.
- About 56 glitches across them (some rooms hide two or three, a few rooms are "clean" decoys that teach the player to read the rule card; decoys count in the log as "no glitch here, checked").
- A finale room, "The Original Build", combines six quirks.

## 4. How fairness is PROVED (tests)
- `tools/solver.py` explores every reachable state of every room by breadth-first search (rooms are tiny) up to a depth cap and records every glitch event it can reach. Tests demand: the set found equals the listed set exactly (no hidden unlisted glitch, no unreachable listed glitch), each glitch is reachable within its par moves + 6, and a decoy room reaches none.
- Every room can be left by a normal route (no glitch needed) so a player is never stuck; Reset always restores the start.
- Determinism test: the same move list replays to the same state and events; the engine source is scanned for clocks and randomness. Replays in the log are re-run on load and rejected if they no longer produce the glitch.
- Harmlessness lint: no room file touches the page, storage or network.

## 5. Bigger picture, goals, hints
- **Glitch Log** is the collection: 56 pages grouped by chapter, each page "found" or "not yet" (a dashed blank titled with the rule it breaks, so the hunt has a target, never a spoiler). A **Defect Wall** shows the six quirks as a poster that fills as you discover each in a new room.
- Three goals always in view (any order): the next three unearned achievements with counts and bars. Stats strip: Rooms checked, Glitches found, Quirks known, Decoys cleared.
- Hint ladder (each rung opened on request, first rung asks "Would you like a suggestion?"): Nudge (which rule is weakest), Hint (which two things interact, shown as two highlighted tiles), Answer (the full move list as a ghost with a "Play it" button; using it still counts as a find).
- Rooms are all open from the start. A chapter's last room asks nothing of the earlier ones.

## 6. Achievements (14; computed from facts)
1 First Crack (1 glitch); 2 Ten Cracks (10); 3 Chapter Broken (every glitch in one chapter); 4 Half the Wall (3 quirks known); 5 Whole Defect Wall (all 6 quirks); 6 Fifty-Six Faults (all glitches); 7 Clean Bill (clear 3 decoys); 8 By The Book (leave 10 rooms by the normal route); 9 One Move Wonder (find a glitch at par or better, 5 times); 10 Two for One (two glitches in one room); 11 Rewind Habit (use Reset after a find 10 times); 12 Free Poke (find a glitch in Free Poke mode); 13 Second Opinion (all three hint rungs on one room); 14 The Original Build (finale room).

## 7. Real-world facts
Short "Famous glitches" cards on the About and Sources page, read live from named sources and dated on screen: the Pac-Man level 256 counter wrap, the Super Mario Bros "minus world", and the 1983 "Space Invaders speed-up" (a side effect of fewer sprites to draw). Each card names its source page and the read date; offline shows the stored text with its stored date. More game than teaching.

## 8. Stack, save and reuse
- Pyodide Python, plain HTML/CSS with code-drawn SVG, no build step. Modules: `rules.py`, `quirks.py`, `rooms_*.py`, `solver.py` (dev and tests), `logbook.py`, `progress.py`, `hints.py`, `render.py`, `achievements.py`, `info.py`, `game.py` (`handle(json)`, `get_state()`, `load_state()`), `app.js` glue. Same shape as Hull Repair and Evidence Hunt.
- Reuses `shared/hint-ladder.js`, `goals-panel.js`, `save-widget.js`, `level-select.js`, `confirm-dialog.js`, `keyboard-shortcuts.js`, `story-toggle.js` and the info-page kit.
- Save: found glitches with their stored move lists (re-validated on load), quirks known, hint rungs, flags, tally. Only fully validated state loads; `achievements_earned` is written and never read back.

## 9. Milestones
| # | Milestone | Content |
|---|-----------|---------|
| 1 | Engine | Room rules, quirk flags, breadth-first glitch solver, chapter 1 (6 rooms) with proofs and tests |
| 2 | Room UI | SVG room, move and keyboard input, rule card, glitch stamp and replay clip, Reset, save contract. Playable slice |
| 3 | Chapters 2-4 and the log | 18 more rooms, Glitch Log, Defect Wall, hint ladder, three-goals strip |
| 4 | Chapters 5-6 and the finale | 12 more rooms (36 in all), decoys, Free Poke, The Original Build. First complete game |
| 5 | Standard kit | Opening screen, tutorial, settings, About with live-read sources, What's New, confirm dialogs, light theme, accessibility pass |
| 6 | Achievements | 14 achievements, panel and toast, manifest, reachability test |
| 7 | Desktop boot and wrap-up | `pc-config.json`, `pc.css`, `pc.js`, generated `pc.html`, docs, changelog |

## 10. Open questions for the owner (defaults used meanwhile)
1. Should the tester's log notes be dry and dark in voice, or plainer? Default: dry and short, behind the Story toggle.
2. Should "decoy" rooms (no glitch to find) exist at all, or does every room hide one? Default: 3 decoys across the game.
