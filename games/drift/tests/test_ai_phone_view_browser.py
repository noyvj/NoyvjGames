"""R4-DRMO-2 and R4-DRMO-3 in a real phone-width page: the swipe cards and the pinned Advance Round
button with its strain ring."""
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
GAME = "drift"

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


def open_game(p, base, width=360, height=740):
    browser = p.chromium.launch()
    ctx = browser.new_context(viewport={"width": width, "height": height}, service_workers="block")
    ctx.route("**/*fastapicloud*/**", lambda route: route.abort())
    page = ctx.new_page()
    page.goto(base + "index.html#play")
    page.wait_for_function(READY, timeout=90000)
    page.wait_for_timeout(800)
    return browser, page


def advance(page, times):
    for _ in range(times):
        page.click("#advance-round-button", force=True)
        page.wait_for_timeout(250)


def test_swipe_cards_reachable_and_neighbour_can_be_opened(base):
    with sync_playwright() as p:
        browser, page = open_game(p, base)
        # Before the neighbour exists: one card, no way across.
        assert page.is_hidden("#swipe-to-neighbor")
        assert page.is_hidden("#neighbor-panel")
        advance(page, 4)
        assert page.is_visible("#swipe-to-neighbor")
        page.click("#swipe-to-neighbor")
        page.wait_for_timeout(900)
        left = page.eval_on_selector("#neighbor-panel", "e => e.getBoundingClientRect().x")
        assert 0 <= left < 40, "neighbouring district card should be the one on screen"
        # The open button must still work on a phone (the first version hid it).
        assert page.is_visible("#neighbor-open-button")
        page.click("#neighbor-open-button")
        page.wait_for_timeout(300)
        assert page.is_visible("#neighbor-housing-button")
        page.click("#swipe-to-region")
        page.wait_for_timeout(900)
        assert page.eval_on_selector("#mobile-swipe-container", "e => Math.round(e.scrollLeft)") == 0
        assert page.evaluate("document.documentElement.scrollWidth") <= 360
        browser.close()


def test_advance_button_stays_pinned_and_ring_follows_strain(base):
    with sync_playwright() as p:
        browser, page = open_game(p, base)
        assert page.get_attribute("#advance-round-button", "data-strain") == "stable"
        advance(page, 4)
        assert page.get_attribute("#advance-round-button", "data-strain") == "critical"
        assert "critical" in page.get_attribute("#advance-round-button", "title")
        page.evaluate("window.scrollTo(0, 0)")
        top = page.eval_on_selector("#advance-round-button", "e => e.getBoundingClientRect().y")
        page.evaluate("document.getElementById('game').scrollIntoView({block: 'end'})")
        bottom = page.eval_on_selector("#advance-round-button", "e => e.getBoundingClientRect().y")
        assert top == bottom, "the button moved when the page scrolled, so it is not pinned"
        assert 600 < top < 740
        browser.close()
