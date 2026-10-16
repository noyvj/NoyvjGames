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
GAME = "thaw"


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


def open_game(p, base, width=360, height=740):
    browser = p.chromium.launch()
    ctx = browser.new_context(viewport={"width": width, "height": height}, service_workers="block")
    ctx.route("**/*fastapicloud*/**", lambda route: route.abort())
    page = ctx.new_page()
    page.goto(base + "index.html#play")
    page.wait_for_function(READY, timeout=90000)
    return browser, page


def test_info_page_becomes_swipeable_on_mobile(base):
    with sync_playwright() as p:
        browser, page = open_game(p, base)
        page.click("#info-page-toggle-button")
        page.wait_for_selector("#info-page-panel:not([hidden])", timeout=5000)

        display = page.evaluate("() => window.getComputedStyle(document.querySelector('#info-page-panel')).display")
        assert display == "flex", "Panel should switch to flex on mobile"

        overflow = page.evaluate("() => window.getComputedStyle(document.querySelector('#info-page-panel')).overflowX")
        assert overflow == "auto", "Panel should allow horizontal scroll on mobile"

        assert page.is_visible(".info-page-dots"), "Dots container should be visible"

        dots = page.query_selector_all(".info-page-dot")
        assert len(dots) == 3, f"Expected 3 dots, got {len(dots)}"

        browser.close()
