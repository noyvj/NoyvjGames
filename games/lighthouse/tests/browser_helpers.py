"""Shared set-up for a test that drives the real page in a browser (Playwright, headless Chromium).

    from browser_helpers import open_game      # tests/conftest.py puts this folder on sys.path

`base` is a module-scoped fixture: it starts its own local web server for the repository and gives the address of THIS
game's folder (the game is the folder two levels above the test file). conftest.py imports it, so every test file can
simply take a `base` argument (importing it again in a test file makes flake8 report F811; `from browser_helpers
import base, open_game` still works if you must). `open_game(p, base, width, height)` opens
index.html#play ("#play" skips the opening screen, which would cover the page), blocks the service worker and the
backend, waits until the Python engine has loaded (this can take a minute) and returns (browser, page). Page script
errors are collected in `page.page_errors`. Copy tests/test_example_browser.py for a new browser test.
"""
import contextlib
import functools
import http.server
import socket
import threading
import urllib.request
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]

# The game is ready when the Python engine has loaded: newer games empty their #engine-status line, older ones (no
# such line) have window.pyodide with get_state. This one check works in every game; do not write your own wait for
# a button or panel instead.
READY = ("(() => { const s = document.querySelector('#engine-status');"
         " if (s) return s.textContent === '' || s.hidden;"
         " return !!window.pyodide && !!window.pyodide.globals.get('get_state'); })()")


def _online():
    """The games load Pyodide from a CDN; without network a browser test can only time out, so it is skipped."""
    try:
        urllib.request.urlopen("https://cdn.jsdelivr.net/pyodide/v0.26.4/full/pyodide.js", timeout=5).close()
        return True
    except Exception:
        return False


@pytest.fixture(scope="module")
def base(request):
    if not _online():
        pytest.skip("Pyodide's CDN is not reachable")
    game = Path(str(request.node.fspath)).resolve().parents[1].name

    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *args):
            pass

    handler = functools.partial(Quiet, directory=str(ROOT))
    with contextlib.closing(socket.socket()) as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    server = http.server.ThreadingHTTPServer(("127.0.0.1", port), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield "http://localhost:%d/games/%s/" % (port, game)
    server.shutdown()


def open_game(p, base, width=1280, height=800):
    browser = p.chromium.launch()
    ctx = browser.new_context(viewport={"width": width, "height": height}, service_workers="block")
    ctx.route("**/*fastapicloud*/**", lambda route: route.abort())
    page = ctx.new_page()
    page.page_errors = []
    page.on("pageerror", lambda error: page.page_errors.append(str(error)))
    page.goto(base + "index.html#play")
    page.wait_for_function(READY, timeout=90000)
    return browser, page
