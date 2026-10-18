"""Shared setup for browser tests (Playwright): the `base` server fixture and open_game().

Copy tests/test_example_browser.py to start a new browser test. Write
    from browser_helpers import open_game
and take `base` as a test argument: tests/conftest.py puts this folder on sys.path and registers the `base` fixture
for every test (importing `base` by name as well works, but flake8 then reports F811 on the test function).
open_game(p, base, width, height) returns (browser, page); the page has `page.errors`, a list of uncaught page
errors, so a test can assert it stayed empty.
"""
import contextlib
import functools
import http.server
import socket
import threading
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
GAME = "trade-empire"

# The game is ready when the Python engine has loaded (it can take a minute): newer games empty their
# #engine-status line, older ones (no such line) have window.pyodide with get_state. "#play" in the address skips
# the opening screen, which otherwise covers the page and makes every click time out.
READY = ("(() => { const s = document.querySelector('#engine-status');"
         " if (s) return s.textContent === '' || s.hidden;"
         " return !!window.pyodide && !!window.pyodide.globals.get('get_state'); })()")


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


def open_game(p, base, width=1280, height=800):
    browser = p.chromium.launch()
    ctx = browser.new_context(viewport={"width": width, "height": height}, service_workers="block")
    ctx.route("**/*fastapicloud*/**", lambda route: route.abort())
    page = ctx.new_page()
    page.errors = []
    page.on("pageerror", lambda error: page.errors.append(str(error)))
    page.goto(base + "index.html#play")
    page.wait_for_function(READY, timeout=90000)
    return browser, page
