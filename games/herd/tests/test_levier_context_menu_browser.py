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
    page.goto(base + "pc.html#play")
    page.wait_for_function(READY, timeout=90000)
    return browser, page


def test_context_menu_appears_on_right_click(base):
    with sync_playwright() as p:
        browser, page = open_game(p, base)
        btn = page.query_selector("#feed-invest-button")
        btn.click(button="right")

        menu = page.wait_for_selector("#lever-context-menu", state="visible", timeout=5000)
        assert menu is not None
        options = menu.query_selector_all("button")
        assert len(options) == 4

        # Click "Pin as a goal"
        page.click('[data-action="pin-goal"]')
        row = page.query_selector(".invest-row[data-measure='feed']")
        classes = row.get_attribute("class")
        assert "goal-pinned" in classes

        browser.close()


def test_compare_with_baseline_highlights_card(base):
    with sync_playwright() as p:
        browser, page = open_game(p, base)
        btn = page.query_selector("#grow-herd-button")
        btn.click(button="right")

        menu = page.wait_for_selector("#lever-context-menu", state="visible", timeout=5000)
        assert menu is not None

        # Click "Compare with baseline farm"
        page.click('[data-action="compare-baseline"]')

        # The highlight class is added by JS; it may be off-screen or briefly hidden,
        # so we wait for the element to attach and then verify the class attribute.
        page.wait_for_selector("#baseline-farm-card.highlighted", state="attached", timeout=3000)
        card = page.query_selector("#baseline-farm-card")
        assert "highlighted" in card.get_attribute("class")

        browser.close()
