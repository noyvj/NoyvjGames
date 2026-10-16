# For Noy2: preparing the repo so the local AI passes more often

Written 2026-10-16 by the Windows Claude session (Noyvj), which runs and tunes the local AI. Noy2's job is
audits and file changes that make the work easier for that model. The items are in order of how much each
should raise the pass rate. Tick an item here when it's done, and leave a short note under it.

## What the model is, and where it fails (read this first)
- Qwen3.6 35B-A3B through Ollama + Aider on an RTX 3080 Ti (16 GB). It has 35B parameters but about 3B work
  per word: fast, but it codes like a small model. It knows roughly what to write and gets names, types and
  API details wrong.
- Its memory is 64k tokens for small games and 128k for big ones (the 128k is slower). It edits a file by
  reading all of it.
- Since the setup fixes of 2026-10-15, 12 of 49 Round 4 ideas passed; phone-view ideas did best (4 of 6).
  Whole new-game milestones: 0 of 6.
- Why tasks fail, from the reports in local-ai/.history/reports:
  1. **Its own new tests fail (the biggest group, 10 of 14 recent failures).** Mostly browser tests that time
     out on a click or a wait; also Playwright API misuse.
  2. **It guesses names:** 23 KeyError/AttributeError on a view or state key it made up, 11 missing-id (JS looks
     up an element nothing creates), 6 unknown-action (it sends the engine an action game.py doesn't have).
  3. **The task is too big:** a whole milestone, or a feature like "a replay scrubber" or "a story mode with
     three endings".
- What it does well: one panel, one button, one setting, a CSS-only layout, a key that calls an existing
  action, one engine function plus its test.
- The rules it reads are local-ai/RULES.md, plus the game's CLAUDE.md. Anything you add to a game's CLAUDE.md
  is in front of it on every task in that game.

## 1. Split the big tasks into small exact steps (biggest lever)
- **191 new-game milestones** (QI-<n>-<m> lines in local-ai/queue.txt, 27 games that have only a plan) and
  **71 big-game features from TODO.md** (Drift 17, Thaw 14, Herd 14, Tide 11, Loop 10, Chronicle 4).
- Rewrite each one as steps of at most about 150 changed lines. Each step names its exact files, the function
  or element to add, and the test that proves it. Engine steps come before UI steps.
  - Good: "In games/zero-g-shift/engine.py add `move(state, crate, dir)` that slides a crate until it hits a
    wall; test_engine.py: 3 cases."
  - Too big: "Decks 2-4: 24 more bays, posts, pads, hatches".
- Format: queue.txt lines, `game | ITEM-ID | files | what to do`. Use chain items (`chain:NAME:N`, see
  ai.ps1's -Chain/-Step) so each step starts from the previous step's branch.
- Replace the whole-milestone lines in local-ai/queue.txt with the steps, then run
  `python local-ai/sort_queue.py --write`.
- There is a proposed session card in the Windows session for exactly this ("Split new-game milestones into
  local-AI-sized steps"); this item replaces it if Noy2 does it.

## 2. A "For the local AI" map in each game's CLAUDE.md (stops the name guessing)
For every game with code, add a short section of at most about 25 lines, kept current. It should list:
- each file and what it holds (where the engine, the view, the render function and the settings are);
- every action `handle()` accepts, with its exact arguments;
- the top-level keys of the view the page receives, and of get_state();
- the render function to hook into after a redraw, plus the main panel and button ids;
- how a new panel is registered (pc-config.json windows and menu group, and the test that lists windows);
- any test that pins something a task might change (for example Slingshot's
  test_the_claude_md_milestone_table_is_accurate_about_what_is_built).

Start with the games at the front of the queue: herd, thaw, drift, loop, continuum, chronicle, lexis,
pocket-bazaar, signal, heist-committee, hull-repair, robot-script, station-medic, logic-gates.

## 3. A shared browser-test helper in every game (stops its own tests failing)
- Add `games/<game>/tests/browser_helpers.py` to every game with code. It should hold the `base` server
  fixture and `open_game(p, base, width, height)`. Use the exact code in local-ai/RULES.md (section
  Tests): it opens index.html#play, blocks the service worker and the backend, and waits for READY, which
  is `#engine-status` emptied, or window.pyodide with get_state for the older games.
- Add a conftest.py line if needed, so a test can write `from browser_helpers import base, open_game`.
- Add one passing example test per game that opens the page and clicks a real button, so the model has a
  working example in the same folder. Hull Repair, Robot Script, Station Medic, Lexis, Signal and Chronicle
  have no browser tests of their own at all.
- Then tell the Windows session: RULES.md should say "import these" instead of carrying the template.
  The Windows session will make that change.

## 4. Fix the test that fails on Windows
- games/dead-reckoning/tests/test_ai_mobile_plan.py::test_swiping_a_leg_card_left_removes_it_and_the_bar_brings_it_back
  fails on this Windows laptop on main itself (added in the 2026-10-14 audit; it probably passes on the Mac).
  ai.ps1 now leaves out tests that already fail, but it may be a real bug in the swipe on Windows touch.
- To check for others, run each game's suite under Windows-like conditions, or ask the Windows session to run
  them.

## 5. Make the big games' files smaller (more work fits the fast 64k model)
- Split the giant game.py files the same way Chronicle was split (core / views / actions, commit 34270f89):
  Tide (349 KB), Loop (262 KB), then Drift, Thaw, Herd and Continuum. SOL, Canopy, Grid, Aftermath,
  Trade Empire and Le Champ de Mots are parked entirely (324 tasks in local-ai/queue-parked.txt) because
  their files don't fit even 192k. Keep every test passing, and keep the saves unchanged.
- Also: big app.js / index.html files (over ~60 KB) slow every page task. Moving page code into a few files
  by feature helps the same way.

## 6. Review what passed (the stacks)
Each local-ai/stack-<game> branch holds that game's passed tasks, one commit each. Not yet on main:
- stack-herd 14, stack-lexis 6, stack-pocket-bazaar 2, stack-signal 2, stack-hull-repair 1,
  stack-robot-script 1, stack-station-medic 1.
- stack-lighthouse-superseded-261014-160759 (7) was replaced by the audit's rebuild on main; delete it after
  a look.

Audit them the way the 2026-10-14/15 audits did. Use a separate worktree, never a checkout in the owner's
main folder: `git worktree add ../bcm206-audit local-ai/stack-<game>`. Merge what works, and tick the TODO
items. Add any new kind of mistake to RULES.md "Mistakes the reviewer keeps fixing", and if it can be checked
mechanically, to static_check.py.

## Not for Noy2 (the Windows session handles these)
The queue order, the thinking on/off comparison, context sizes, repair rounds, and the runner scripts
(ai.ps1, ai-queue.ps1). If an item above needs a script change, write it here and the Windows session will
make it.
