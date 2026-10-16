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
GAME = "herd"


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


def test_i_key_shows_pasture_labels(base):
    with sync_playwright() as p:
        browser, page = open_game(p, base)
        # Check data-label attributes exist on pasture elements
        labels = page.query_selector_all("[data-label]")
        assert len(labels) > 0, "Pasture elements should have data-label attributes"

        # Hold 'I' to show labels
        page.keyboard.down("i")
        page.wait_for_timeout(100)
        pasture = page.query_selector("#pasture-visual")
        assert pasture.is_visible() and "labels-on" in pasture.get_attribute("class"), "Pasture should have labels-on class while holding I"

        # Release 'I' to hide labels (with slight delay handled by JS, but we check immediately or after)
        page.keyboard.up("i")
        page.wait_for_timeout(200)  # Wait for debounce
        assert "labels-on" not in pasture.get_attribute("class"), "Pasture should lose labels-on class after releasing I"

        browser.close()
