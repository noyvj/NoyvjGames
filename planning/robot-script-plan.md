# Robot Script (slug `robot-script`, section RS, TODO QI-3) - Groundwork Plan

Source: the Quick ideas round, owner-approved: "give a robot a short list of instructions to clear a room (Lightbot style). No timer, medals for using fewer steps, and a free sandbox once you finish." Checked against `PLAYER-PROFILE.md`: coding and logic puzzles (yes), robots and science fiction, dark and moody low-poly, collecting and solving, three goals visible at all times, easy to 100%, no tutorial needed, no timers, no loss of progress, no all-good hero. Personal project, no BCM tag, working title. The shared baseline (save, settings, achievements, changelog, tutorial, confirm dialog, accessibility, Desktop boot) is the same kit as Pocket Bazaar and Dead Reckoning.

## 1. Concept
A decommissioned maintenance deck on a station that nobody has the budget to demolish. A literal-minded maintenance robot waits at the start of each room and does exactly what your instruction list says, including the foolish parts. You build the list from a short toolbox, press Run, and watch it clear the room: reach the exit, light the switches, carry the parts to their sockets. A mistake is never a loss: the robot stops where it went wrong, tells you why in plain words, and your list is still there to fix. Nothing is timed. Look: a dark, faceted low-poly room drawn as SVG (floor and wall tiles in two shades per tile, a lit exit pad), every object distinct by shape and label as well as colour.

## 2. The rules (a pure function of room and program)
- Room: up to 8x8 cells (a corridor may be 10 long, 64 cells at most). Tiles: floor, wall, exit pad, parts (to carry), sockets (to fill), switches 1-3 and doors A-C (door N opens once switch N is lit). The robot starts on a tile facing a direction.
- Actions: `F` forward, `L`/`R` turn, `G` pick up a part on this tile, `P` place the carried part into a socket here, `S` light the switch here. Carry capacity one.
- Control: `rep N {..}` (2-9 times), `until [not] cond {..}`, `if [not] cond {..} else {..}`, and `call A` / `call B` for saved sub-routines (A calls nothing, B may call A, no recursion). Conditions: `blocked` (wall, edge or closed door ahead), `part`, `socket`, `switch` (unlit one here), `carrying`, `exit`.
- A room is cleared when the program ends with every goal met: robot on the exit (if the room has one), every socket filled, every switch lit, and (rooms with parts but no sockets) every part collected.
- A bump (wall, edge, closed door), a pointless grab or place, or a loop that never ends (a safety stop after 2000 actions, not an energy limit) halts the run with a plain message and the robot stays where it stopped. Retry or edit freely.
- Determinism: `run(room, program)` has no randomness and no clock; the same pair always makes the same trace. Reference solutions and a breadth-first solver run in tests on every room.

## 3. Medals, par, hints (no timer anywhere)
- "Steps" are instructions in your list (every instruction, block header and call counts one; sub-routine bodies count too). Par is the length of the authored reference solution. Bronze: cleared. Silver: within par plus a third (at least 2). Gold: at or under par. Medals only ever go up; your best list per room is kept.
- Hint ladder per room, all free, never touching a medal: Nudge (one plain sentence about the room), Hint (what the reference is made of: how many loops, branches, calls, and the first move), Answer (the reference list, with a button to put it in the editor). Using the Answer is never hidden or shamed; clearing a room that way still counts as a clear.
- Easy to 100%: every room has a proven par, every medal is reachable with the Answer in hand, chapters open at 5 of 7 rooms cleared (never all), nothing can be missed or expire.

## 4. Level design: 40 rooms in six chapters, then the sandbox
1. **Moving** (7 rooms, `F G P S`): straight corridors that teach the ideas: count the steps, light a switch to open a door, carry one part to a socket, finish on the exit.
2. **Turning** (7, adds `L R`): L-shaped and S-shaped rooms, detours round walls, a part around a corner, two deliveries one at a time. Par equals the solver's minimum here.
3. **Loops** (7, adds `rep`): staircases, rows of parts, a spiral. The loop is what gets gold; the same room can still be cleared long-hand.
4. **Sub-routines** (7, adds A and B): one fetch-and-deliver move reused three times, mirrored halves, a routine that calls a routine.
5. **Conditionals** (7, adds `if` and `until`): "walk until the wall", "pick up only if there is a part", the same list working for a room that changes shape.
6. **The Long Shift** (5, everything): bigger rooms that mix the lot. The last room clears the deck and opens the sandbox.
- Chapter n+1 opens when 5 of chapter n's rooms are cleared. Inside a chapter any room can be played in any order.
- **Sandbox** (opens after The Long Shift): paint a room (walls, parts, sockets, switches, doors, exit, start), write any program with all instructions, run it as often as you like. No goal, no medals; runs and tiles built count on screen. Layout saved with the account.

## 5. Companion and collectable hook
Scrap, a salvage drone left half-dismantled in the deck's workshop, is rebuilt from the parts you earn: one part per room, 40 in all, in ten zones (treads, chassis, two arms, head, lens, antenna, lamp, plating, voice box). A part's finish follows the medal (rusted, clean, polished), so a better list upgrades the same part, never a new grind. The Workshop panel draws Scrap from what you have and lists every part with the room it comes from (nothing hidden). Scrap is quiet, dry and not cheerful: it comments on a clear in a line or two, sometimes sulks that it would have done it differently. All story lines sit behind the shared story toggle; nothing needed to play is ever in them.

## 6. Always-visible goals and visible stats
A strip of the next three goals, any order, each with progress ("Clear 10 rooms 4/10"), taken from the achievements that can already be earned in open chapters. Stats strip: Rooms cleared, Gold medals, Parts, Runs. A tally panel adds instructions written, bumps, hints asked, sandbox runs and tiles built. Every Run, edit, hint and sandbox action moves one of these.

## 7. Achievements (14; computed from facts; none hidden, none luck or time based)
1 First Light (clear 1 room); 2 Ten Down (10 rooms); 3 Chapter Closed (clear every room of one chapter); 4 Halfway There (3 chapters); 5 Shift Done (all 6 chapters, 40 rooms); 6 Fine Work (5 gold); 7 Clockwork (20 gold); 8 Perfect Script (40 gold); 9 Loop the Loop (clear a room with a repeat); 10 Phone a Friend (clear a room with a sub-routine call); 11 Two Minds (clear a room with an if or until); 12 Learned From a Bump (clear a room after a halted run); 13 Second Opinion (use all three hint rungs, anywhere); 14 Tinkerer (10 sandbox runs).

## 8. Stack, save and tests
- Pyodide Python, plain HTML/CSS, no build step. Engine: `dsl.py` (program text, validation, size), `room.py`, `run.py` (interpreter and trace), `editor.py` (structured edits with a cursor and undo), `rooms_*.py` (40 rooms with reference solutions), `progress.py`, `companion.py`, `render.py` (room and Scrap SVG strings), `sandbox.py`, `achievements.py`, `info.py`, `game.py` (`handle(json)`, `get_state()`, `load_state()`). `app.js` is glue. Dev-only `tools/solver.py` (breadth-first, minimum actions).
- Save: best list per cleared room (stored as program text, re-run and re-checked on load), drafts of unfinished lists, hint rungs used, flags, tally, sandbox layout. Only fully validated state loads; new keys appear only when non-default; `achievements_earned` is written and never read back.
- Tests: interpreter semantics, DSL round trip, every room solved by its reference at its par, flat rooms checked against the solver minimum, every medal threshold reachable, editor ops, save round trip and tampering, achievements all reachable by a reference-only player, accessibility and shell checks, no clock and no randomness in the engine.

## 9. Milestones
| # | Milestone | Content | Status |
|---|-----------|---------|--------|
| 1 | Engine | DSL, room, interpreter, solver, chapter 1 (7 rooms) with references and tests | Done |
| 2 | Room UI | SVG room, structured editor, run/step/skip playback, result card with medal, room picker, favicon, settings, save contract. Playable slice | Done |
| 3 | Chapters 2-3, medals, hints | 14 more rooms, chapter gating, hint ladder, three-goals strip, Scrap and the Workshop | Done |
| 4 | Chapters 4-6 and the sandbox | 19 more rooms (40 in all) and the free sandbox. First complete game | Done |
| 5 | Standard kit | Opening screen, tutorial, About, What's New, keyboard help, confirm dialogs, light theme, accessibility pass | Done |
| 6 | Achievements | 14 achievements, panel and toast, manifest, reachability test | Done |
| 7 | Desktop boot and wrap-up | `pc-config.json`, `pc.css`, `pc.js`, generated `pc.html`, docs, changelog | Done |

## 10. Open questions for the owner (defaults used meanwhile)
1. Should the sandbox open earlier than the end of The Long Shift (for example after chapter 3)? Default: after the last chapter, as asked.
2. Scrap's tone: a quiet, dry, slightly sulky salvage drone, never a cheerful hero. Keep, or make it chattier or silent? Default: quiet.
3. Medal rule: gold at the reference length, silver within a third more. Make gold stricter or looser? Default: as written.
4. Chapter 1 has no turning, so its rooms are straight corridors and very short. Bring `L R` in from room 4 instead? Default: keep it pure.
5. Chapters open at 5 of 7 rooms cleared. Prefer every room open from the start? Default: gated.
