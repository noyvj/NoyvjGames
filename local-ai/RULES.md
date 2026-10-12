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

## Tests
- Add or update pytest tests in this game's tests/ folder for any Python change.
- The tests and flake8 run automatically after your edits. Fix any failure
  before saying you are done.

## Style
- Match the code around you: same naming, same comment density, same idioms.
- Keep changes small. Do not reformat or rename things the item does not need.
- Python layout (flake8): two blank lines before and after every top-level def or class,
  one blank line between methods, no spaces at the end of a line.
- Do not commit. The human runs the finish step, which tests and commits.
