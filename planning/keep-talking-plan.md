# Keep Talking (slug `keep-talking`, TODO QI-31) - Groundwork Plan

Source: the Quick ideas round (E1), owner-approved: "two players each see half of a puzzle and have to talk it out (voice or text in whatever app they already use), joined by an invite link." Checked against `PLAYER-PROFILE.md`: loved Keep Talking and Nobody Explodes for how people communicate badly, Among Us banter, co-op where two friends fix one problem, optional friend ties, helper role, no timers, no chat built in, no mandatory friend feature. Personal project, no BCM tag, working title. One-line pitch: one player holds the control panel, the other holds the manual, and neither can solve the vault door alone.

## 1. Concept
A sealed salvage vault ("the Tern Locker") must be opened one **module** at a time. The **Panel** player sees the physical thing (wires, symbols, dials, lamps, a small maze with markers). The **Manual** player sees the rules (which wire to cut when, which symbol column, what each lamp pattern means) but not the panel. They talk in whatever voice or text app they already use; the game has **no chat, no emotes, no names**. When they agree they each tap the answer. A module opens; a vault door opens after a handful.
- 2-minute session: one short module (three wires and a rule), a "talk it out", a click.
- 20-minute session: a whole job of four modules in a different order for each player, with a cool-down card.
- Look: dark, clean low-poly, two distinct screens (Panel and Manual) with large buttons; every symbol told apart by shape and name, never colour alone. **No timer, no explosion, no alarm**; nothing blows up. A wrong answer is a soft hum and a "not quite, check it again" note; tries are counted in the tally, never punished.
- **Invite link:** a seed-based link such as `.../keep-talking/?join=KTALK-7G0F4&role=manual`. The link carries only the job's seed (the same as `shared/seed.py`) and a role. Both browsers compute the same halves from the seed, so **no server is needed to play** and nothing about either player leaves their browser. No account is needed. The player who opens the link chooses Panel or Manual; the host sends the other the link.
- **Solo mode (plays both halves):** a companion, **Pim**, a small maintenance bot, plays the other half in words, with deliberately imperfect descriptions ("the pointy one on the left"). You ask Pim from a list of questions ("What is in the third slot?", "Is the lamp steady or blinking?") and decide what to do. You can swap roles in solo each job. Solo is the whole game; friends are optional.

## 2. Rules (a pure function of the seed)
- Module kinds: **Wires** (cut the right wire from a rule table), **Symbol Pad** (press symbols in the order of a manual column), **Dials** (set dial positions from a sheet), **Lamps** (a blink pattern as steady/short/long marks, no sound, mapped to a code), **Maze** (a grid with markers; the manual shows walls; find the path). A job is 3 to 5 modules chosen by seed.
- The generator makes a Panel and a Manual from one seed. The **information split** is guaranteed: the Panel alone leaves at least 2 consistent answers; the Manual alone leaves at least 2; together they give exactly one.
- Verification is local on each device: each player enters the agreed answer; each device checks it against the seed's solution. A job counts for a player when their own device sees the right answer. (A determined cheat could read the solution in dev tools. This is a friendly game; there is no leaderboard.)
- No clock, no randomness (seeded), no chat, no names exchanged.

## 3. Content size
- 36 authored jobs in six chapters of six, each chapter adds a module kind (Wires, Symbols, Dials, Lamps, Maze, Everything Together), plus an **Endless** practice mode that deals seeded jobs from a seed typed or pasted.
- About 90 manual pages (rule tables), 40 symbols, and 18 Pim descriptions per module kind for solo mode.

## 4. How fairness is PROVED (tests)
- A property test over thousands of seeds per module kind: the answer is unique, the Panel alone leaves at least 2 candidates, the Manual alone leaves at least 2, and the pair yields 1.
- Cross-language test: `shared/seed.js` and `shared/seed.py` generate the same seed code, and the module halves are computed in Python only, so both browsers (via Pyodide) agree by construction; a test replays 200 seeds twice and compares.
- Solo-mode test: a bot that asks Pim the optimal question list solves every authored job in a bounded number of questions.
- Source scan: no network, clock or `random` in the engine; the invite link validator rejects any parameter that is not a valid seed or role.

## 5. Bigger picture, goals, hints
- The **Vault Wall** is the picture: a faceted wall of 36 sealed lockers that open as jobs close (solo or together), plus a "worked with a friend" mark per locker that is a mark, never a requirement.
- Three goals always visible (any order): the next three unearned achievements with counts and bars. Stats strip: Jobs opened, Modules, Friend jobs, Pim questions.
- Hint ladder (opt-in; first rung asks "Would you like a suggestion?"): Nudge (which column or wire matters), Hint (names the rule), Answer (the exact action; in a pair, only your own half's step is shown, and both players must opt in separately).
- Every chapter and job is open from the start.

## 6. Achievements (14; computed from facts)
1 First Lock (open a vault); 2 Ten Locks; 3 Chapter Open (all of one chapter); 4 Whole Wall (all 36); 5 Wires Down; 6 Right Symbols; 7 Steady Dials; 8 Lamp Reader; 9 Maze Runner; 10 Pim Pair (10 solo modules with Pim); 11 Together (first friend job); 12 Five Together; 13 Endless Ten (10 endless jobs); 14 Second Opinion (all three hint rungs on one module).

## 7. Real-world facts
None, fiction. The About page notes (read live and dated) the origin of the asymmetric-information co-op genre (a named public source) as background only.

## 8. Stack, save and reuse
- Pyodide Python, plain HTML/CSS with code-drawn SVG, no build step, no audio files (optional generated cues via `shared/sfx.js`). Modules: `kinds_*.py` (module generators), `jobs.py`, `halves.py` (Panel and Manual views), `solver.py`, `pim.py` (solo companion), `invite.py` (link parse and validate), `progress.py`, `hints.py`, `render.py`, `achievements.py`, `info.py`, `game.py`, `app.js`.
- Reuses `shared/seed.js` and `seed.py`, `run-code.js` (job summary code), `hint-ladder.js`, `goals-panel.js`, `save-widget.js`, `level-select.js`, Evidence Hunt's seeded-generator pattern.
- Save: jobs opened (solo, friend), hint rungs, flags, tally. Nothing about the friend is stored.

## 9. Milestones
| # | Milestone | Content |
|---|-----------|---------|
| 1 | Engine | Seed to job, Wires and Symbol Pad generators, information-split proofs, 12 jobs with tests |
| 2 | Solo UI | Panel and Manual screens, Pim, solo roles, answer entry, save contract. Playable slice (solo) |
| 3 | More modules | Dials, Lamps, Maze, 24 more jobs (36 in all), hint ladder, three-goals strip. First complete game |
| 4 | Invite links | Invite link parsing, role choice, two-browser play, tamper-proof link validator, Endless mode |
| 5 | Standard kit | Opening screen, tutorial, settings, About, What's New, keyboard help, light theme, accessibility pass |
| 6 | Achievements | 14 achievements, panel and toast, manifest, reachability test |
| 7 | Desktop boot and wrap-up | `pc-config.json`, `pc.css`, `pc.js`, generated `pc.html`, docs, changelog |

## 10. Open questions for the owner (defaults used meanwhile)
1. Is "no server, each device checks its own answer" fine, knowing a determined cheat could peek? Default: yes (no leaderboards, so nothing to cheat).
2. Should a friend job be started from a short code you can read aloud as well as an invite link? Default: both (code is the seed).
