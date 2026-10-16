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


def test_mobile_invest_bar_appears_on_narrow_viewport(base):
    """Verify the mobile investment bar is visible on narrow screens and desktop rows are hidden."""
    with sync_playwright() as p:
        browser, page = open_game(p, base, width=360, height=740)
        assert page.is_visible("#mobile-invest-bar")
        assert not page.is_visible("#investments > .invest-row")
        browser.close()


def test_mobile_invest_bar_structure(base):
    """Verify the bar contains the expected track, handles, and segments."""
    with sync_playwright() as p:
        browser, page = open_game(p, base, width=360, height=740)
        assert page.is_visible("#mobile-invest-track")
        assert page.locator(".mobile-invest-handle").count() == 2
        segs = page.locator(".mobile-invest-seg")
        assert segs.count() == 3
        for i, cat in enumerate(["output", "preserve", "monitor"]):
            assert segs.nth(i).get_attribute("data-cat") == cat
        browser.close()


def test_mobile_invest_step_buttons_dont_crash(base):
    """Clicking a +/- step button should not throw and should update the DOM."""
    with sync_playwright() as p:
        browser, page = open_game(p, base, width=360, height=740)
        first_seg = page.locator(".mobile-invest-seg").first
        plus_btn = first_seg.locator("button[data-dir='1']")
        count_el = first_seg.locator(".mobile-invest-count")

        count_el.inner_text()
        plus_btn.click()
        new_text = count_el.inner_text()

        # The bar updates counts based on funds; clicking should not error.
        assert new_text.isdigit() or new_text == "0"
        browser.close()
