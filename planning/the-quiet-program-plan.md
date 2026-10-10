# The Quiet Program (slug `the-quiet-program`, TODO QI-26) - Groundwork Plan

Source: the Quick ideas round (D2), owner-approved: "advise a broken but gentle program on a failing computer network (a tragic, quiet character in the spirit of the one you like)." Checked against `PLAYER-PROFILE.md`: tragic, quiet, broken-savior characters (never an all-good hero), a barely-speaking companion that shows emotion, helper and healer role, computers and robots, dark moody, short wins that build a slow arc, a hint ladder, no timers, nothing lost, no self-harm and no self-hatred spirals. Personal project, no BCM tag, working title. One-line pitch: a failing network is held together by a gentle old program called Wick, and you are the one voice it listens to while it tries to deliver the last messages.

## 1. Concept
**Wick** is a relay-routing daemon on the Harrow Net, a string of 14 dim data nodes between small stations that no longer have many users. Wick is courteous, forgetful and a little apologetic; its memory is corrupting a slice at a time. It cannot decide well for itself any more, so it asks you. It is not sad about itself in a spiral: it is steady, curious, and loves delivering things.
Each **Evening** is one routing puzzle: a network diagram with links that are open, flaky (works on alternate beats) or down, a few messages waiting to cross, and Wick's current **fault card** (plain words: "Wick forgets the first instruction in a batch", "Wick repeats a message if a link flaps"). You choose, from a short list of advice lines ("Send it by the north link", "Wait one beat", "Send two copies", "Remember this"), the order and the routes. Wick carries them out beat by beat. A good plan delivers everything; a flawed plan delivers some, and Wick says so kindly.
- 2-minute session: one Evening on a four-node net, a small warm reply from Wick.
- 20-minute session: a chapter of six Evenings and the memory fragments it unlocks.
- Look: dark, clean low-poly diagram, links drawn with shape and dash pattern (open solid, flaky dashed, down broken), Wick as a small lamp with a face of three lights showing mood in words too. Quiet. **Nothing dies on screen; "going quiet" is only the net's ending, handled softly.**

## 2. Rules (a pure function of the net, the faults and the plan)
- A plan is an ordered list of advice actions. Beats are turns, not time. Each link carries one message per beat; flaky links work on odd beats only; down links never. Some messages are urgent (must arrive by a stated beat) and a few must go to two places.
- Wick's faults are deterministic rules: Forgets-First (drops the first action unless you add "Remember this" before it), Repeats-On-Flap, Ignores-North (never uses a named link without a nudge), Shy-Of-Silence (insists on sending something every beat). They are listed on the fault card, never hidden.
- Result per Evening: Delivered (all), Mostly (some), Quiet (none); each is a clear. Delivered also earns the Evening's memory fragment. Replay is free; Restore resets to the start.

## 3. Content size
- 30 Evenings in five chapters (Two Nodes, Three Roads, The Flicker, The Forgetting, The Last Ring), nets growing from 4 to 14 nodes, plus 3 short "Quiet Hours" interludes (no puzzle, a conversation only).
- 40 memory fragments (what Wick kept: a song title, a lighthouse timetable, a child's name for a relay), each a short dry-gentle text with a small low-poly keepsake icon.
- Three gentle endings: **The Last Message** (all delivered), **Archived** (Wick preserved, quiet), **Left Running** (Wick keeps the net alive). They are warm or bittersweet; none harms anyone; all can be reached from the Last Ring in any order.

## 4. How fairness is PROVED (tests)
- A solver (`tools/solver.py`) searches the plan space of every Evening under the posted faults (depth-first with beat pruning) and must find a plan that delivers everything; it also records the number of distinct perfect plans and the shortest one (par).
- Deducibility test: with the faults shown, a perfect plan can be derived from the diagram alone (no hidden state; Wick's behaviour is a pure function of the visible fault list).
- Wick-mood function is checked to depend only on the delivered ratio, never on retries.
- Determinism: no clock or randomness in the engine (source scan). Save plans replay and are re-checked on load. Banned-word lint: no self-harm language, no on-screen death words.

## 5. Bigger picture, goals, hints
- The **Harrow Net map** is the bigger picture: 14 nodes, each dark until an Evening there is delivered, then lit and labelled with the fragment found there. A lit net brightens the whole lamp-face of Wick.
- Three goals always in view (any order): the next three unearned achievements with counts and bars. Stats strip: Evenings kept, Delivered, Fragments, Nodes lit.
- Hint ladder (opt-in, first rung asks "Would you like a suggestion?"): Nudge (which link or fault matters most), Hint (the first action of a perfect plan as a ghost), Answer (the whole plan with a button to enact it).
- Every chapter and Evening is open from the start (the order is only a suggestion; the nets grow in size, so early ones teach the faults). Any grade counts as a clear.

## 6. Achievements (14; computed from facts)
1 First Evening (clear 1); 2 Ten Evenings (10); 3 Chapter Kept (a whole chapter); 4 Whole Net (all 30); 5 Delivered (first perfect); 6 Twenty Delivered (20 perfect); 7 Every One Delivered (all 30 perfect); 8 First Fragment; 9 Twenty Fragments; 10 Everything Kept (40 fragments); 11 Short Way (match par on 5 Evenings); 12 Remembered (use "Remember this" to beat Forgets-First); 13 Quiet Company (hear all three Quiet Hours); 14 Three Endings (see all endings).

## 7. Real-world facts
Minimal: a "How real networks route" card on the About page, read live from a named source and dated on screen (for example a public explainer of packet routing, plus the history of store-and-forward networks such as FidoNet). Marked as background; the game is fiction and more game than teaching.

## 8. Stack, save and reuse
- Pyodide Python, plain HTML/CSS with code-drawn SVG, no build step. Modules: `net.py` (graph, links), `wick.py` (faults and mood), `evenings_*.py`, `plan.py` (rules), `solver.py`, `fragments.py`, `endings.py`, `progress.py`, `hints.py`, `render.py`, `achievements.py`, `info.py`, `game.py`, `app.js`.
- Reuses the Station Medic pattern (plans as action tokens replayed on load), Stranded's story toggle for the interludes, `shared/hint-ladder.js`, `goals-panel.js`, `save-widget.js`, `story-toggle.js`.
- Save: best grade per Evening, current plan tokens, fragments, endings seen, hint rungs, flags. Only validated state loads; `achievements_earned` written, never read.

## 9. Milestones
| # | Milestone | Content |
|---|-----------|---------|
| 1 | Engine | Net, link and beat rules, Wick faults, solver proof, chapter 1 (6 Evenings) with tests |
| 2 | Evening UI | SVG net, advice lines, beat playback, Wick lamp, result card, Restore, save contract. Playable slice |
| 3 | Chapters 2-3, fragments, hints | 12 more Evenings, memory fragments, net map, hint ladder, three-goals strip |
| 4 | Chapters 4-5 and endings | 12 more Evenings (30 in all), Quiet Hours, three endings. First complete game |
| 5 | Standard kit | Opening screen, tutorial, settings, About with the fiction note, What's New, confirm dialogs, light theme, accessibility pass |
| 6 | Achievements | 14 achievements, panel and toast, manifest, reachability test |
| 7 | Desktop boot and wrap-up | `pc-config.json`, `pc.css`, `pc.js`, generated `pc.html`, docs, changelog |

## 10. Open questions for the owner (defaults used meanwhile)
1. Wick is steady and kind rather than sad; its decline is gradual forgetting. Is that the right tragic level, or should it be sadder or lighter? Default: as written.
2. Should Wick's apologies and thanks be spoken in short lines for every Evening, or only on the first and last of each chapter? Default: short every Evening, behind the Story toggle.
