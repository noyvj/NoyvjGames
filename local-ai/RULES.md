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
    The test must START ITS OWN SERVER. Never write a fixed address like http://localhost:8073 (nothing listens
    there), and there is no pytest.playwright: use playwright.sync_api. Name the file test_<name>_browser.py and
    start it with exactly this (change GAME to the folder name), then write tests that take `base`:

        import contextlib
        import functools
        import http.server
        import socket
        import threading
        from pathlib import Path

        import pytest

        pytest.importorskip("playwright.sync_api")
        from playwright.sync_api import sync_playwright  # noqa: E402

        ROOT = Path(__file__).resolve().parents[3]
        GAME = "slingshot"


        @pytest.fixture(scope="module")
        def base():
            class Quiet(http.server.SimpleHTTPRequestHandler):
                def log_message(self, *args):
                    pass

            handler = functools.partial(Quiet, directory=str(ROOT))
            with contextlib.closing(socket.socket()) as s:
                s.bind(("127.0.0.1", 0))
                port = s.getsockname()[1]
            server = http.server.ThreadingHTTPServer(("127.0.0.1", port), handler)
            threading.Thread(target=server.serve_forever, daemon=True).start()
            yield "http://localhost:%d/games/%s/" % (port, GAME)
            server.shutdown()


        # The game is ready when the Python engine has loaded (it can take a minute): newer games empty their
        # #engine-status line, older ones (no such line) have window.pyodide with get_state. This one check works
        # in every game; do not write your own wait for a button or panel instead. "#play" in the address skips
        # the opening screen, which otherwise covers the page and makes every click time out.
        READY = ("(() => { const s = document.querySelector('#engine-status');"
                 " if (s) return s.textContent === '' || s.hidden;"
                 " return !!window.pyodide && !!window.pyodide.globals.get('get_state'); })()")


        def open_game(p, base, width=1280, height=800):
            browser = p.chromium.launch()
            ctx = browser.new_context(viewport={"width": width, "height": height}, service_workers="block")
            ctx.route("**/*fastapicloud*/**", lambda route: route.abort())
            page = ctx.new_page()
            page.goto(base + "index.html#play")
            page.wait_for_function(READY, timeout=90000)
            return browser, page


        def test_the_new_button_opens_its_panel(base):
            with sync_playwright() as p:
                browser, page = open_game(p, base)
                page.click("#the-new-button")
                assert page.is_visible("#the-new-panel")
                browser.close()

    Before you click something, make sure it is visible at that window size (a panel may be closed, or a phone
    layout may hide it); open what contains it first. For a phone layout, call open_game(p, base, 360, 740).
  - If the game has no browser tests yet, at least a test that reads the changed file and checks the
    new element, class or handler is there and wired up (weaker, but required).
- The tests and flake8 run automatically after your edits. Fix any failure
  before saying you are done.
- Edit an existing test file with small SEARCH/REPLACE blocks. Never paste a second copy of its imports or tests
  into it (flake8 F811 "redefinition"): add only the new test functions.
- Finishing a milestone: set its Status to Done in the game's CLAUDE.md milestone table. Some games have a test
  that pins that table (for example tests/test_assets_and_shell.py, test_the_claude_md_milestone_table_...):
  update that test's expected statuses in the same change, or it fails.

## Style
- Match the code around you: same naming, same comment density, same idioms.
- Keep changes small. Do not reformat or rename things the item does not need.
- Python layout (flake8): two blank lines before and after every top-level def or class,
  one blank line between methods, no spaces at the end of a line.
- Do not commit. The human runs the finish step, which tests and commits.

## More mistakes from the 2026-10-14/15 audits of the Round 4 batches (about 100 ideas; almost none worked as pushed)
Run `python local-ai/static_check.py <game>` yourself before you say you are done: it reads the page code
and lists most of these. A finding means look at that line.
- Every id you look up with getElementById, $() or querySelector("#...") must exist: in index.html, or created by
  your own code BEFORE the lookup. Write the element in index.html first, then the code that uses it.
- An event has one target. If you send it with window.dispatchEvent, listen with window.addEventListener (not
  document), and the other way round.
- Never read a data-xxx attribute (dataset.xxx) that you have not made something write. Say where it is set.
- Only send the engine an action it has: open game.py, find the action in handle(), and use the exact
  name and arguments. Do not invent actions (swipe, load_draft). If the engine lacks one, do not build the idea;
  say what engine change it needs.
- A setting needs all of: a checkbox or control in index.html, code that applies it on load, a reset path
  ("Reset display settings"), and it lives in localStorage. A label wrapped around its input must not also have
  its own click handler (it toggles twice and does nothing).
- Keyboard guards that skip keys while a dialog is open: write [role='dialog']:not([hidden]). On the Desktop
  page every window frame is a role=dialog that is hidden when closed, and a plain [role='dialog'] makes every
  shortcut dead there.
- Do not scale, transform or add elements to the game's SVG board: the engine rebuilds it on every move and
  your change is lost. Put the zoom or highlight on a wrapper element or reapply it after each render.
- A panel, sheet or drawer that is hidden by default needs a visible button that opens it AND a way to close it
  (button and Escape). A position: fixed panel that starts off-screen with nothing to open it is a dead feature.
- Do not rename or remove an id that other code uses (for example #undo-button): search the game folder for it first.
- Reduced motion: test with window.matchMedia("(prefers-reduced-motion: reduce)").matches (call .matches), and give
  every new effect an off switch in Settings. Vibration (navigator.vibrate) is allowed; sound is not.
- Timers: some games' pledge tests count setTimeout and setInterval in app.js. Use the event's timeStamp for
  hold and long-press instead of a timer.
- Prefer a smaller idea that really works over a big idea half-built. If you cannot finish an idea, do the smallest
  working part and say what is left; a panel that nothing opens counts as not done.
- Write tests that check the wiring: the id in the HTML equals the id in the JS, a setting is read back on load,
  a new key survives get_state then load_state. A test that only checks an element exists is not enough.
