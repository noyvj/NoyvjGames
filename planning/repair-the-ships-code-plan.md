# Repair the Ship's Code (slug `repair-the-ship-s-code`, TODO QI-34) - Groundwork Plan

Source: the Quick ideas round (G1), owner-approved: "learn Python by fixing a starship's broken functions, with tests that go green as you fix each one." Checked against `PLAYER-PROFILE.md`: coding and logic puzzle games (yes), space and computers, helper and fixer role, short wins that build a bigger picture, hint ladder, easy-to-medium base difficulty, "more game than teaching", working it out themselves, no timers, nothing lost. Personal project, no BCM tag, working title. One-line pitch: the starship **Wren** is limping home on broken functions; open a system, read its failing tests, fix the code and watch the lights come back.

## 1. Concept
The ship's computer has 36 small broken Python functions, one per ship system (`fuel_left`, `cabin_temperature`, `is_airlock_safe`, `next_waypoint`...). Each level shows the **system panel** (what it does in a sentence), the **code** in a plain editor, and a **test list** in plain words ("fuel_left(100, 25) should give 75: got 125"). Fix the code, press **Run**, and each test turns from a red cross to a green tick (shape plus word, never colour alone). When all tests pass the system lights on a cutaway of the ship.
- 2-minute session: one short function with a single wrong sign, three tests go green.
- 20-minute session: a chapter of six functions; the last one calls the earlier five, so the ship's system chart connects.
- Look: dark, clean low-poly ship cutaway and a calm editor (monospace, line numbers, big tap targets, a phone-friendly mode where you tap a token to swap it for a short list of options, plus full typing). Quiet; optional generated clicks only.
- **Nothing the player writes can harm anything:** code runs in a locked-down interpreter inside Pyodide, with a built-in allowlist, no imports beyond `math`, no files, no network, a step budget (a counted number of operations, not a timer) that stops runaway loops with a friendly "that loop did not end", and output capped.

## 2. Rules (a pure function of the level, the code and the tests)
- A level has: a title, a plain sentence, the broken source, a list of tests (call, expected, shown in words), and a hidden set of extra cases. A level is **fixed** when the code passes all shown and hidden tests.
- Python subset taught in order: values and arithmetic, if/else, comparison and `and`/`or`/`not`, `while` and `for`, lists, strings, dicts, small functions calling functions. Each chapter lists what is allowed so early levels never ask for later ideas.
- **Run** is unlimited and free. **Reset** restores the broken code. The editor keeps the player's last attempt per level.
- Errors are shown in plain words first ("Line 3: `fuel` was not defined") then the raw Python message on request.
- No clock, no randomness, no network.

## 3. Content size
- 36 levels in six chapters of six: Numbers (arithmetic and rounding), Choices (if/else), Repeats (loops), Lists, Words (strings), Systems (dicts and calling functions), with a final **Home Run** level that calls many.
- 5 to 8 shown tests and 6 to 12 hidden tests per level; about 360 test cases in all; 36 one-paragraph **Systems notes** shown after fixing.
- A **Bug Bestiary** of 12 bug kinds (off by one, wrong operator, wrong variable, missing return, wrong comparison, forgotten edge case, integer versus float, etc.), 3 examples each.

## 4. How fairness is PROVED (tests)
- For every level: the broken source **fails** at least one shown test; the stored reference fix **passes** every test; the recorded minimal edit (one line or token, stored as the "bug diff") turns the broken source into code that passes. All run in the same locked-down runner the game uses.
- **Mutation tests:** each level has 3 to 6 plausible wrong fixes (return the expected value, hard-code the shown cases, fix one branch only) and the test set must **fail** every one, so a shortcut cannot win.
- The runner's sandbox is tested: imports, `open`, `eval`, attribute tricks, infinite loops, deep recursion and huge output are all stopped safely, and the page is untouched.
- Determinism: same code, same result. Hint rung 3 shows the reference fix and is verified to pass.

## 5. Bigger picture, goals, hints
- The **Wren cutaway**: 36 ship systems drawn as faceted modules, dim until fixed, then lit with their note. A completion percentage bar sits above. The Bug Bestiary fills as you meet each bug kind.
- Three goals always visible (any order): the next three unearned achievements with counts and bars. Stats strip: Systems fixed, Tests green, Bug kinds, Runs.
- Hint ladder (opt-in; first rung asks "Would you like a suggestion?"): Nudge (which line to look at), Hint (the kind of bug, in words), Answer (the corrected line shown as a diff, with an Apply button). Answer-assisted fixes still count as fixed.
- Chapters are all open from the start; the order is a suggestion.

## 6. Achievements (14; computed from facts)
1 First Green (fix 1); 2 Ten Systems; 3 Chapter Online (a whole chapter); 4 Wren Awake (all 36); 5 All Ticks (a fix on the first run, 5 times); 6 Careful Reading (read the failing test before running, 10 times); 7 Bug Hunter (3 bug kinds); 8 Full Bestiary (all 12); 9 No Peeking (a chapter with no hint rung above Nudge); 10 Loop Tamer (all loop levels); 11 Word Smith (all string levels); 12 Home Run; 13 Tidy Fix (a fix that changes only the buggy line); 14 Second Opinion (all three hint rungs on one level).

## 7. Real-world facts
Real famous software bugs as optional "Afterward" cards read live from named, dated sources: the Ariane 5 flight 501 conversion overflow (the ESA inquiry report), the Mars Climate Orbiter units mix-up (NASA's investigation board report), and the Y2K two-digit year. Python behaviour notes cite the official Python documentation (docs.python.org) with the read date. More game than teaching.

## 8. Stack, save and reuse
- Pyodide Python, plain HTML/CSS, no build step. Modules: `sandbox.py` (restricted runner with step budget), `levels_*.py` (broken, fix, tests, hidden tests), `check.py`, `bestiary.py`, `progress.py`, `hints.py`, `render.py`, `achievements.py`, `info.py`, `game.py`, `app.js` (editor glue).
- Reuses the dev-only mutation checker pattern from Logic Gates' truth-table verifier, `shared/hint-ladder.js`, `goals-panel.js`, `save-widget.js`, `level-select.js`, `shared/run-code.js` for sharing a fix summary (optional).
- Save: per level the last code (capped length), fixed flag, hint rungs, bestiary, flags, tally. Only validated state loads; saved code is never executed on load, only on Run.

## 9. Milestones
| # | Milestone | Content |
|---|-----------|---------|
| 1 | Engine | Sandbox runner with step budget, level format, checker, chapter 1 (6 levels) with fix, bug-diff and mutation proofs |
| 2 | Editor UI | Editor, tests list, Run and Reset, ship cutaway, phone token mode, save contract. Playable slice |
| 3 | Chapters 2-4, bestiary, hints | 18 more levels, Bug Bestiary, hint ladder, three-goals strip |
| 4 | Chapters 5-6 and Home Run | 12 more levels (36 in all), final level. First complete game |
| 5 | Standard kit | Opening screen, tutorial, settings, About with live-read sources, What's New, keyboard help, light theme, accessibility pass |
| 6 | Achievements | 14 achievements, panel and toast, manifest, reachability test |
| 7 | Desktop boot and wrap-up | `pc-config.json`, `pc.css`, `pc.js`, generated `pc.html`, docs, changelog |

## 10. Open questions for the owner (defaults used meanwhile)
1. Should phones get the tap-a-token editor only, or a normal keyboard editor too? Default: both, token mode first on small screens.
