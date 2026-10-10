# Fog Rescue (slug `fog-rescue`, TODO QI-15) - Groundwork Plan

Source: the Quick ideas round (B3), owner-approved: "guide lost animals or travellers out of a dark foggy forest by lighting the right lanterns in the right order." Checked against `PLAYER-PROFILE.md`: a helper role, dark moody setting with fog, one puzzle at a time, short wins into a bigger picture, nothing lost, no on-screen harm, no timers. Related to the foggy-forest dream game idea as a possible small piece, built as a separate game and not tied to it. Personal project, no BCM tag, working title.

Pitch: carry one small flame through a dark forest, lighting lanterns one after another so that lost animals and travellers follow the glow home.

## 1. Concept
- You are the lamp-keeper of an old forest road (invented: the Thornwick Wood). Fog hides the paths. You hold one flame; light a lantern next to you and the lost ones in its glow walk to it. Light the next lantern along and they follow. Lead them all to the cabin at the forest edge.
- 2-minute session: a clearing with two creatures. 20-minute session: a full wood with five different lost ones.
- Look: near-black forest of faceted low-poly trees, soft pools of lantern light, fog as layered translucent shapes (toggleable). Each lost one has a shape and a word label (Fawn, Owl, Fox, Traveller), never colour alone. Quiet tone: the creatures are shy, nobody is hurt, a lost one who is not led simply waits.

## 2. Core rules (a pure function of the wood and the lantern sequence)
- The wood is a graph of tiles joined by paths; lanterns stand on some tiles; trees block. Your flame sits on one lantern. You may light only a lantern linked to the current flame by a path of at most 'reach' steps (shown as a dotted ring).
- Lighting a lantern moves the flame there (the previous lantern goes out) and every lost one that can see it (within the new lantern's glow radius along open paths) takes a fixed walk toward it: Fawn walks all the way to it, Traveller walks up to 3 steps, Owl glides over trees to the lit lantern but only if it is within 2, Fox keeps its distance (stops 2 tiles away and will not go through a lit tile), Lamb follows the nearest other creature instead.
- Lit tiles stay bright until the flame leaves; creatures standing on the cabin tile are safe and settle there. Cleared when every lost one is at the cabin.
- You can always Relight from the start, Step back or Restore the sequence; there is no limit on lanterns lit.

## 3. Content size
40 woods in 5 chapters of 8: The Edge (Fawn and Traveller only), The Orchard (Owl), The Bog (reach and blocked paths), The Old Road (Fox and Lamb), The Heart of the Wood (all five). Chapter n+1 opens at 5 of 8; any order inside. Par is the fewest lanterns lit.

## 4. How correctness is PROVED
- Dev tool `tools/solve.py` runs breadth-first search over (flame, creatures) states for every wood. Tests assert solvable, par equals the BFS minimum, stored, and no wood is solvable in fewer than 3 lanterns (so none are trivial).
- Creature rules have golden tests (each creature's walk in a table of small boards).
- "Can I still reach home?" (dead-state check) uses the same search and is exposed as a free button; there are no true dead ends (Restore always returns to the start). Determinism: pure functions, no clock, no random.

## 5. Collection and 100%
- The Lost and Found board: 40 woods, each with the creatures and travellers led home, shown as a small illustrated card in a cabin window row; plus a Cast book of the 5 creature kinds and 12 named travellers (each with a one-line quiet story). The forest map on the wall lights up path by path with each cleared wood. 100% = all 40 led home; fewest-lantern tags are bonus. States only go up.

## 6. Goals and hint ladder
- Three always-visible goals, any order, with bars. Stats strip: Woods cleared, Creatures home, Travellers home, Par tags. The tally counts lanterns lit, step backs and restores.
- Ladder (first rung asks "Would you like a suggestion?"): Nudge (which creature to think about first), Hint (the first lantern to light as a ghost), Answer (the full sequence as a ghost route with a "Light them" button). Free, on request.

## 7. Achievements (14)
First Light; Ten Woods; Twenty Woods; All Forty; Edge Done; Orchard Done; Bog Done; Old Road Done; Heart of the Wood; Every Creature (all five kinds home); Twelve Travellers (the whole named cast); Few Flames (10 par tags); Fox at the Door (lead the Fox home); Waiting Patiently (restore after a dead end).

## 8. Real-world facts
None, fiction. The About page lists the folklore and woodland-ecology sources that inspired the animal behaviour as text only.

## 9. Reuse
Graph/grid engine, BFS tool and renderer from Hull Repair and Zero-G Shift (same repo patterns); cast book like Station Medic's crew Record; Stranded's quiet captions; shared `level-select.js`, `hint-ladder.js`, `goals-panel.js`, `opening-screen.js`, `info_page.py`, `ambient-bg.css`, `announcer.js`, `pc-shell.js`.

## 10. Milestones
| # | Milestone | Content |
|---|-----------|---------|
| 1 | Engine and solver | Graph, lantern and creature rules, BFS solver, dead-state check, chapter 1 (8 woods) with proofs |
| 2 | Wood UI | SVG wood and fog, tap-to-light, glow animation (toggleable), step back and restore, save contract. Playable slice |
| 3 | Chapters 2-3 | 16 more woods, Owl, reach and blocked paths, Lost and Found board |
| 4 | Chapters 4-5, hints, goals | 16 more woods (40), Fox and Lamb, Cast book, hint ladder, three-goals strip. First complete game |
| 5 | Standard kit | Opening screen, tutorial, About with Sources, What's New, keyboard help, confirm dialogs, light theme, accessibility |
| 6 | Achievements | 14 achievements, panel and toast, manifest, reachability test |
| 7 | Desktop boot and wrap-up | `pc-config.json`, `pc.css`, `pc.js`, generated `pc.html`, docs, changelog |

## 11. Open questions for the owner
1. Should this stay a standalone game or be set aside to become part of the foggy-forest dream game later? Default: standalone now, reusable later.
