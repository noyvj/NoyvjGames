# Terminal Logs (slug `terminal-logs`, TODO QI-30) - Groundwork Plan

Source: the Quick ideas round (D6), owner-approved: "a choose-your-own-adventure told only through a computer terminal's logs and your commands." Checked against `PLAYER-PROFILE.md`: computers and science fiction, Lifeline-style branching story, a notebook that fills in, collecting and solving, quiet tragic-but-gentle characters (never an all-good hero), hint ladder, free rewinds, no timers, no visual novel, no on-screen death, coding and logic interest. Personal project, no BCM tag, working title. One-line pitch: you log in to the dead computer of a survey ship, read what the crew and the ship left behind, and choose which commands to run until you know what happened to the Anselm.

## 1. Concept
The ship's computer, **ORRERY-7**, still runs on a failing battery. You sit at its terminal. There are no faces and no narrator beyond the machine: only files, logs, mail spools, scripts and the commands you run. The story is what the files say and what happens when you run things: a quiet cruise that went wrong because of small decisions, people who were kind and flawed (a navigator who hid a fault, a medic who copied private messages, a captain who delayed a turn-back), and a ship's AI daemon that kept a few things safe.
- 2-minute session: `ls`, open two logs, run one small script and see a log line change.
- 20-minute session: unlock a deck's files, find a missing log, choose whether to send a recovered message, and reach one of five endings.
- Look: dark terminal in a clean low-poly frame (phosphor-dim text with a bold weight, not only colour for emphasis); a button palette of commands (`list`, `read`, `search`, `run`, `unlock`, `send`, `help`) so phones need no typing, with real typing optional. Quiet; optional generated key-clicks via `shared/sfx.js`.
- Nobody dies on screen; deaths are far in the past and told with restraint if at all (people left, were lost on the way back, were rescued): see the tone lint.

## 2. Rules (a pure function of the file system, the state and the commands)
- The ship is a small virtual file system: about 140 files in 9 directories (`/crew`, `/log`, `/mail`, `/nav`, `/med`, `/eng`, `/archive`, `/bin`, `/tmp`). Files are text logs, mail threads, config files or scripts. Each file has an id and clue tags.
- Commands: `list` (directory), `read` (file), `search <word>` (finds files containing it), `run <script>` (a handful of authored scripts with visible effects), `unlock <door>` (with a key or code you have read), `send <message>` (choose one of a few recovered drafts), `help`. Every command is a button; the argument is picked from what you have seen.
- **Choice forks:** at 12 authored points a script offers a branch (restore power to the lab or the bridge; forward the captain's last message or hold it; open the logbook to the relief crew). Branches decide which of five endings you reach; nothing is lost, and every fork can be rewound.
- Locked doors are story logic, not progression gates: every locked file shows "needs: a code you have not read yet" with the directory the code lives in, so there is no strict order.
- No randomness, no clock, no typed free text beyond command arguments from a fixed set.

## 3. Content size
- About 140 files, 40 of them essential log entries; 14 scripts; 12 forks; 5 endings: **Relief Crew** (the logbook is handed over), **The Long Return** (the ship turns back), **Quiet Archive** (everything is sealed), **Kept Safe** (the daemon's quiet duty is honoured), **Last Message** (the captain's message is sent).
- An **Archive Index** lists every file as read or unread, grouped by directory.

## 4. How fairness is PROVED (tests)
- A graph validator treats files, keys and scripts as nodes: every file is reachable from the start by a command path, every unlock key is findable before the door that needs it (no circular dependency), and from every reachable state at least one command makes progress or opens a new file.
- A search over fork states proves all five endings are reachable, and that every ending is reachable without any command the player cannot have discovered from the files read so far.
- The shortest path to each ending is recorded as par; the hint ladder reads it.
- Determinism and replay: state is the list of commands taken, replayed on load. Source scan for clock and randomness.
- Tone lint: no gore, no self-harm, no on-screen death; the dead are referred to by gentle past tense only.

## 5. Bigger picture, goals, hints
- The **Ship Map**: the nine directories as decks of a faceted cutaway that brighten as their files are read; a completion percentage bar.
- Three goals always in view (any order): the next three unearned achievements with counts and bars. Stats strip: Files read, Scripts run, Forks seen, Endings.
- Hint ladder (opt-in; first rung asks "Would you like a suggestion?"): Nudge (which directory to look at), Hint (which file or key matters), Answer (the exact next command with a button that runs it).
- Free rewind to any command; nothing collected is ever lost; all endings keep their pages.

## 6. Achievements (14; computed from facts)
1 First Login; 2 Ten Files; 3 Deck Read (a whole directory); 4 Every Directory; 5 Whole Archive (all 140 files); 6 First Script; 7 All Scripts (14); 8 First Fork; 9 Every Fork (12); 10 First Ending; 11 Three Endings; 12 Every Ending (5); 13 Back Up (rewind 5 times); 14 Second Opinion (all three hint rungs at one fork).

## 7. Real-world facts
Fiction: the ship, crew and events are invented. The About and Sources page shows live-read, dated notes on real tools the commands imitate (the POSIX/GNU manual pages for `ls`, `grep`, `cat`), clearly marked as background. More game than teaching.

## 8. Stack, save and reuse
- Pyodide Python, plain HTML/CSS with a text-first renderer, no build step. Modules: `fs.py` (files, tags), `files_*.py`, `scripts.py`, `shell.py` (commands), `forks.py`, `endings.py`, `index.py`, `validate.py`, `progress.py`, `hints.py`, `render.py`, `achievements.py`, `info.py`, `game.py`, `app.js`.
- Reuses Stranded's rewind and branch-map engine pattern, Logic Gates' "chips as kept results" idea for scripts, `shared/narrative_log.py`, `hint-ladder.js`, `goals-panel.js`, `save-widget.js`, `story-toggle.js`.
- Save: command list (replayed), files read, scripts run, endings seen, hint rungs, flags, tally. Only validated state loads.

## 9. Milestones
| # | Milestone | Content |
|---|-----------|---------|
| 1 | Engine | File system, command rules, graph validator, first two directories (about 30 files) with tests |
| 2 | Terminal UI | Terminal frame, command palette, file list, rewind, ship map, save contract. Playable slice |
| 3 | The ship fills in | Remaining directories, scripts, forks, Archive Index, hint ladder, three-goals strip |
| 4 | Endings | The five endings, par paths, final polish of the logs. First complete game |
| 5 | Standard kit | Opening screen, tutorial, settings, About with live-read sources and fiction notice, What's New, keyboard help, light theme, accessibility pass |
| 6 | Achievements | 14 achievements, panel and toast, manifest, reachability test |
| 7 | Desktop boot and wrap-up | `pc-config.json`, `pc.css`, `pc.js`, generated `pc.html`, docs, changelog |

## 10. Open questions for the owner (defaults used meanwhile)
1. Buttons only, or also a real typing line for commands (with autocomplete) on desktop? Default: both, typing optional.
2. Should the ship's daemon speak (short lines in its own log voice) or should there be no voice at all, only files? Default: short daemon lines, behind the Story toggle.
