# Stranded (slug `stranded`, section SD, TODO QI-25) - Groundwork Plan

Source: the Quick ideas round, owner-approved: "you advise a stranded astronaut by text over many branching days; there is no waiting timer, and you can go back and try a different path." Checked against `PLAYER-PROFILE.md`: Lifeline-style branching with a lot of branches but optional story, short wins that build a bigger picture, quiet tragic-but-gentle characters, a flawed protagonist (never an all-good hero), no hard-lose states, nothing that loses progress, many ways to the end, an easy path to 100% via a branch map, three goals always visible, dark low-poly look, space and robots, dry humour. Tone shared with `lighthouse-plan.md` (quiet, warm resolution, nothing harmful on screen). Personal project, no BCM tag, working title. Hub registration is a separate job.

## 1. Concept
You are Harbour, the night voice on a thin text-only comms line to **Ines Varga**, a field engineer alone on **Orrin**, a small grey moon, at **Sparrow Relay**, a silent relay station she was sent to relight. Her lander **Kestrel** is hurt, the line only holds while a small dish stays pointed, and a relief ship, **Marigold**, is on its way. A comms screen shows the conversation as bubbles on a dark low-poly moonscape. Each of the 12 days is a short scene of messages (2 to 4 choices); Ines answers every choice.
Ines is stubborn, funny, proud and a hoarder of tiny comforts (a classified chocolate bar). She overrode a warning light before launch and has told nobody; she has not opened a message from her brother Pavel. She is not an obedient hero: she argues, hides things and sometimes does the opposite. A small dormant maintenance robot, **Bit**, barely beeps but shows feeling with its lamp.
**No waiting and no clocks.** Replies appear at once, or one per tap (a setting). Nothing happens while you are away; "days" are story scenes, never real time. **No on-screen death**, no peril that cannot be undone; bad outcomes are lost chances, awkward silences and thinner supplies. Fiction notice: the moon, station, ships and people are invented.

## 2. Structure
- 12 days, about 62 scenes (days 1-7 shared with small variants, day 8 a choice of three roads, days 9-11 one arc each, day 12 the ending), 9 endings, all warm or bittersweet: Lantern, Quiet Keeper, Pavel at the Door (relay arc); Straight Up, Half a Lander, Bit Comes Home (lander arc); Marigold Arrives, Quiet Line, A Straight Line (wait arc, some reachable from more than one arc).
- Scenes are nodes, choices are edges. The engine is a pure deterministic graph walker: state = the list of choice numbers taken since the start (replayed to get the scene, three stats and a few flags). No randomness, no clock.
- **Branch map:** a panel with every day, every scene (seen or "?") and every choice (tried solid, untried dashed), with a "Go there" button on any seen scene (the engine finds a route over choices you have already taken) and "Show me a loose end" that takes you to the nearest untried choice. 100% is a walk down the loose ends.
- **Rewind:** a free "Rewind to here" on every choice you made; it restores exactly the earlier state. Collectables, map, endings and counters are never lost by rewinding.
- **What if:** once you have tried two different choices in a scene, the other choices show where they lead (a day and title, never the text), so a fork can be read as a comparison.
- **Hint ladder (opt-in):** Nudge (which day has a loose end), Hint (which scene), Answer (which choice, with a button that takes you there).
- Choices can be locked by a stat ("Needs Trust 4", shown with the reason); every scene always has at least one open choice.

## 3. Stats and goals
- **Trust, Supplies, Hope** (0 to 10, shown as bars with numbers and words, always visible). Choices move them; they gate some choices and pick between endings. They reset when you rewind to an earlier point (they are the state of that moment); nothing else does.
- Progress strip (permanent): Scenes seen, Paths tried, Endings, Archive pages, and a Completion percentage bar. A Tally (collapsed) counts choices made, rewinds, peeks, hints, jumps.
- Three goals, always in view, any order: the next three unearned achievements with counts and bars.
- Narrator: a one- or two-line intro per day in Harbour's dry log voice, switchable with the site's Story toggle (nothing needed to play is hidden).

## 4. Collectables (the Archive, about 29)
Log entries (11, Ines's mission log), found items (10, things on the moon: a camp sketch, the classified bar, Bit's cracked lamp, plaque rubbing...), recordings (8, Ines's voice notes, shown as text). Each is found by a scene or a choice on a particular branch; unfound ones show a hint ("a day 5 branch") so 100% is plannable. A reachability test proves each can be found.

## 5. Achievements (14, computed from facts, none hidden or timed)
First Words (1 choice); Three Days In; All Twelve Days; Someone Comes (1 ending); Four Ways Home (4 endings); Every Road Home (all 9); Second Thoughts (1 rewind); A Look Ahead (1 what-if peek); Half the Map (half the choices tried); Every Path (all of them); Every Place (all scenes seen); Log Keeper (all logs); Pocket Full (all items); Her Voice (all recordings).

## 6. Stack, save and tests
- Pyodide Python, plain HTML/CSS with code-drawn SVG, no build step, no audio. Modules: `kit.py` (story builders), `story_*.py` (scene tables), `lore.py` (collectables, days, narrator), `walker.py` (rules), `story.py` (merged graph, ending table), `explore.py` (map, loose ends, routes, peek), `achievements.py`, `render.py`, `info.py`, `game.py` (`handle(json)`, `get_state()`, `load_state()`), `app.js` glue.
- Save: current path as a string of choice numbers (replayed and re-checked), tried choices, seen scenes, endings, found collectables, tally. Only fully validated state loads; new keys only when non-default; `achievements_earned` written, never read.
- Tests: every scene reachable, every ending reachable, no dead ends, no trapping cycles, every choice has a reply, every choice reachable (stat gates included), every collectable findable, rewind restores the exact earlier state, the pure walker is deterministic, banned-word lint (death, timers, energy, clocks), no clock or random in code, accessibility, shell, Desktop boot, a whole-game run that earns every achievement.

## 7. Milestones
| # | Milestone | Content | Status |
|---|-----------|---------|--------|
| 1 | Engine and the whole story | kit, walker, explore (reachability search, routes, loose ends, peek), lore, 59 scenes in four story tables, 9 endings, graph tests | Done |
| 2 | Comms UI | chat view, stats, choices, rewind, save contract, favicon. Playable slice | Done |
| 3 | Branch map and what-if | map panel and overview, Go there, loose-end button, what-if peek in the UI | Done |
| 4 | Archive, goals, hint ladder | collectables panel, three goals, nudges. First complete game | Done |
| 5 | Standard kit | opening screen, tutorial, About with fiction notice, What's New, keyboard help, confirm dialogs, light theme, accessibility | Done |
| 6 | Achievements | 14 achievements, panel, toast, manifest, reachability test | Todo |
| 7 | Desktop boot | `pc-config.json`, `pc.css`, `pc.js`, generated `pc.html`, docs | Todo |

## 8. Open questions for the owner (defaults used meanwhile)
1. Replies arrive at once by default, with a "one message per tap" setting. Prefer tap by default? Default: at once.
2. Ines is the flawed one (hides a warning-light override, avoids her brother's message); you are a plain voice. Should Harbour have a flaw of their own too? Default: a small one in the narrator log (a bad first message).
3. Stats gate some choices and some endings. Prefer no locks at all, only different replies? Default: gates, always with a visible reason and an open alternative.
4. Names and setting: Ines Varga, Orrin, Sparrow Relay, Kestrel, Marigold, Bit, Pavel. Keep or rename? Default: keep.
5. The brother who flies the relief ship is revealed only if she opens his message (or at the door). Keep the twist? Default: keep.
6. Nine endings, none with a death or a loss of the astronaut. Want one that is sadder (still gentle)? Default: Quiet Line is the saddest.
