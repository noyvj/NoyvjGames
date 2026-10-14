# Rules for the local AI working on NoyvjGames

You are working inside ONE game folder of NoyvjGames, a static site of small
browser games. Each game is Python running in the browser through Pyodide,
plus plain HTML and CSS. There is no build step.

## Your task
The task is the single TODO item given to you. Do only that item. If the item
is too big to finish well, do the smallest useful part, say clearly what is
left, and stop.

## Files
- Only change files inside this game folder.
- Never touch app/, sw.js, shared/ or any other game. If the item seems to
  need a change there, do not make it: describe the change instead.
- Read this game's CLAUDE.md before changing anything, and follow it.
- Never edit pc.html. It is generated from index.html by
  scripts/generate-pc-pages.py, which the human or the ai script runs after you.
  A failing test_pc_boot.py test right after an index.html edit only means
  pc.html has not been regenerated yet: do not try to fix it.

## Standing rules for every game
- Nothing is timed. No clocks, countdowns or real-time pressure.
- Nothing is lost or punishing. A player never loses progress.
- No luck is needed for 100%. Random rewards must be hinted or chosen.
- No audio files.
- Every new animation or effect respects reduced motion and has an off switch.

## Saves (very important)
- Each game has get_state() and load_state(data).
- Old saves must load unchanged. load_state must accept a save that is
  missing any new key and fall back to the default.
- A new key appears in get_state() only when its value is not the default,
  so old saves stay exactly the same.
- Check every loaded value before using it. Bad values fall back to defaults.
- achievements_earned is written by get_state() and never read back.
- Per-device settings (like an effects toggle) go in localStorage, not saves.

## Saving new data (the pattern album lost all its counts on reload)
- Data that must survive a reload has to be in get_state() AND read back in load_state().
- In get_state(), add the key only when it is not empty or default, so old saves stay exactly the same.
- In load_state(), MERGE what the save holds into what is already there: take the larger count, or the
  union of sets. Never add the saved number to the current one: loading the same save twice must give
  the same result as loading it once.

## Page code (.js) in the browser
- pc.js is loaded in the page's <head>, before the board or any game element exists, and the Desktop
  shell (shared/pc-shell.js) builds #pc-stage and its windows only after that. Never look up elements or
  use document.body at the top level of pc.js, and DOMContentLoaded is still too early: do it inside
  window.addEventListener("load", ...), or inside a function the game calls later.
- The game redraws its board after every move, which throws away classes or children you added to
  cells. Anything you show on a cell must be reapplied after each redraw (find the game's render or
  refresh function and hook in there), not added once.
- "At the bottom edge" or "always visible" means position: fixed (or sticky), not just a bigger button.
- Put styling in the game's CSS file (style.css or pc.css) with a class name. Do not set element.style
  properties from JavaScript except for positions that change while the player moves the mouse.

## Mistakes the reviewer keeps fixing (Noy2's audits, 2026-10-12/13): do not repeat them
- A new panel, window or toggle button on the page must also be added to pc-config.json (its "windows"
  list and the right menu group), or the Desktop page hides or misplaces it. Remove entries for things you
  removed or moved. If the game has a test that lists the windows, update that test too.
- Never guess the shape of saved data. Read get_state() and load_state() in game.py (and the view the page
  receives) before using it; for example Signal stores days as days["2026-10-13:easy"], not days[date][mode].
- Streaks: show one only when the game's own show-streaks setting is on (it is off by default), and never in
  a game whose pledge bans streaks (Evidence Hunt). Prefer counts that never go down.
- Pointer code: keep one coordinate system (compare getBoundingClientRect values with each other, not with
  offsets inside an element); start a drag only when the press is inside the element it belongs to; never
  shrink touch targets below 44 px on phones.
- Colour is never the only signal: a bar or mark also gets a word (title, label or text).
- Tests: a comment says what the test really checks, a test name matches what it asserts, and every
  assert checks a specific value (no "is not None" alone, no assert True).

## Tests
- Paths in the chat are relative to the repo root, not the game folder. A new test file is
  games/<game>/tests/test_<name>.py (never tests/... at the top). Do not add sys.path code to a
  test: the game's tests/conftest.py already makes its modules importable, and that code breaks flake8.
- Add or update pytest tests in this game's tests/ folder for any Python change. A task that changes
  the game's Python but adds or changes no test is failed automatically.
- Test what the feature promises, including a save and reload round trip if it stores anything.
- EVERY feature you build adds or extends at least one test in games/<game>/tests/, or the task fails:
  - Python behaviour: a pytest unit test that would fail without your change.
  - Page behaviour (app.js, pc.js, index.html, CSS): a browser test copying the pattern of the game's
    existing tests/test_*_browser.py (it starts a local server and drives the page with Playwright):
    open the page, do what a player would do, assert what they should see.
  - If the game has no browser tests yet, at least a test that reads the changed file and checks the
    new element, class or handler is there and wired up (weaker, but required).
- The tests and flake8 run automatically after your edits. Fix any failure
  before saying you are done.

## Style
- Match the code around you: same naming, same comment density, same idioms.
- Keep changes small. Do not reformat or rename things the item does not need.
- Python layout (flake8): two blank lines before and after every top-level def or class,
  one blank line between methods, no spaces at the end of a line.
- Do not commit. The human runs the finish step, which tests and commits.
