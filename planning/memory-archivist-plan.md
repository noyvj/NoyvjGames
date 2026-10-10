# Memory Archivist (slug `memory-archivist`, TODO QI-18) - Groundwork Plan

Source: the Quick ideas round (B6), owner-approved: "restore corrupted memories from a damaged AI by putting scraps back in order (dark, quiet, science fiction)." Checked against `PLAYER-PROFILE.md`: computers and AI, dark moody science fiction, a notebook being filled in (lore matters when it is a notebook), quiet tragic-but-gentle characters (the AI is flawed, not a hero), helper and healer role, short wins into one slow story, logic puzzles, no timers, nothing lost, no visual-novel structure (the story is the reward for a puzzle, never a choice tree). Personal project, no BCM tag, working title.

Pitch: a damaged caretaker AI keeps its memories in scrambled scraps, and you put each memory back in the one order that fits.

## 1. Concept
- You are the archivist sent to a dead survey station to restore HALCY (invented), the caretaker AI. Its memory core is split into forty memories, each cut into five to nine scraps (one line, a sensor reading, an object state). You lay the scraps in a timeline strip. When the order is right the memory plays as a short text (the AI speaking in the first person, polite, unsure, sometimes wrong) and joins the Archive.
- 2-minute session: one short memory. 20-minute session: a bank of eight, with the story forming.
- Look: dark core room, text scraps as faceted slabs with a small glyph per state, a faint scan-line (toggleable). Quiet tone; no on-screen death: people "left", "were taken off", "stopped answering".

## 2. Core rules (a unique-ordering puzzle, never a guess)
- A scrap is a short line plus a state tag set: time words ("dusk"), object states (lamp on or off, door open or closed, cup full or empty, snow or no snow), who is present, and references ("the one who took the cup" refers to an earlier scrap). Constraints are derived by the engine from the tags: a state changes at most once per memory in one direction, a reference must come after its target, a present person cannot be in two places.
- The player drags scraps into slots; a Check reports how many are in the right place as a number, never which ones. Scraps that contradict (two states that cannot both hold at the same time) are flagged in the Notes pane when they sit next to each other.
- A memory is Restored when the order satisfies all constraints; by design this is exactly one order. Corruption levels (1 to 3) hide some tags until the player Cleans a scrap (a free action that reveals its tags).

## 3. Content size
40 memories in 5 banks of 8: Kitchen Hours (5 scraps), Corridors (6), The Garden Deck (7), Night Shift (8), The Last Winter (9, tying the story together). Bank n+1 opens when 5 of 8 are restored; any order inside. Each bank tells one thread: HALCY looks after a crew of four; the main thread is that it forgot to warn them once, and has been repairing itself around that gap. Nothing graphic. HALCY is neither villain nor hero.

## 4. How correctness is PROVED
- Dev tool `tools/orders.py` enumerates every permutation of a memory's scraps (at most 9 so at most 362,880) and counts those satisfying the constraints. Tests assert exactly ONE satisfying order for every memory and that it equals the stored order.
- Deducibility: a second solver (constraint propagation only, no search) must finish the memory, so a player can always reason to the answer without trying everything.
- Text lint: no scrap includes a death word, a method of harm or a joke about mental-health behaviours; fixed-data only, no random, no clock.

## 5. Collection and 100%
- The Archive: 40 memories in a corridor of drawers, each opened with its restored text, plus a timeline view that arranges all restored memories along the station's whole story, with gaps shown as dark spaces. The Archive reads as one story at the end. 100% = all 40 restored; Clean runs (restored with no Check) are bonus. States only go up.

## 6. Goals and hint ladder
- Three always-visible goals, any order, with bars. Stats strip: Memories restored, Archive percent, Scraps placed, Banks done. The tally counts placements, Checks and Cleans.
- Ladder (first rung asks "Would you like a suggestion?"): Nudge (which pair of scraps must go in a certain order and why, in words), Hint (the next scrap in the order as a ghost), Answer (the whole order, with a "Place them" button). Free, on request.

## 7. Achievements (14)
First Memory; Ten Restored; Twenty Restored; All Forty; Kitchen Done; Corridors Done; Garden Done; Night Done; The Last Winter; Clean Run (5 with no Check); No Hints (10 with none); Deep Clean (clean 50 scraps); Whole Story (open the timeline when complete); Quiet Listener (read 20 restored texts to the end).

## 8. Real-world facts
None, fiction. The About page names the real ideas behind it (how computer memory degrades, the idea of an unreliable narrator) as text, with sources named.

## 9. Reuse
Pure-Python engine with `handle(json)`; story lines via `narrative_log.py` and the story toggle (the text IS the reward, so only decorative asides are toggled); the notebook pattern from Evidence Hunt and Stranded's archive; shared `level-select.js`, `hint-ladder.js`, `goals-panel.js`, `opening-screen.js`, `info_page.py`, `announcer.js`, `pc-shell.js`.

## 10. Milestones
| # | Milestone | Content |
|---|-----------|---------|
| 1 | Constraint engine and prover | Scrap tags, constraint derivation, permutation counter, propagation solver, bank 1 (8 memories) with proofs |
| 2 | Core UI | Scrap slabs, timeline slots, drag and keyboard reordering, Check, Notes pane, save contract. Playable slice |
| 3 | Banks 2-3 | 16 more memories, corruption levels and Clean, the Archive corridor |
| 4 | Banks 4-5, hints, goals | 16 more memories (40), the timeline view, hint ladder, three-goals strip. First complete game |
| 5 | Standard kit | Opening screen, tutorial, About with Sources, What's New, keyboard help, confirm dialogs, light theme, accessibility |
| 6 | Achievements | 14 achievements, panel and toast, manifest, reachability test |
| 7 | Desktop boot and wrap-up | `pc-config.json`, `pc.css`, `pc.js`, generated `pc.html`, docs, changelog |

## 11. Open questions for the owner
1. Is a 40-memory story about a flawed caretaker AI the right tone, or should HALCY be gentler with less of a mistake behind it? Default: a small, forgivable mistake, never a disaster.
2. Should Check show how many scraps are right, or only Right or Not yet? Default: the number.
