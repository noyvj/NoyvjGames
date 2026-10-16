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


def open_game(p, base, width=360, height=740):
    browser = p.chromium.launch()
    ctx = browser.new_context(viewport={"width": width, "height": height}, service_workers="block")
    ctx.route("**/*fastapicloud*/**", lambda route: route.abort())
    page = ctx.new_page()
    page.goto(base + "index.html#play")
    page.wait_for_function(READY, timeout=90000)
    return browser, page


def test_mobile_top_strip_exists_and_is_visible_on_narrow_viewport(base):
    with sync_playwright() as p:
        _, page = open_game(p, base, width=360, height=740)
        strip = page.locator("#mobile-top-strip")
        assert strip.is_visible(), "Mobile top strip should be visible on narrow viewport"


def test_mobile_top_strip_updates_with_round_funds_methane(base):
    with sync_playwright() as p:
        _, page = open_game(p, base, width=360, height=740)
        strip = page.locator("#mobile-top-strip")
        assert strip.is_visible()

        # Check initial values match main displays
        round_disp = page.locator("#round-display").text_content()
        funds_disp = page.locator("#funds-display").text_content()
        methane_disp = page.locator("#methane-display").text_content()

        assert page.locator("#mobile-round").text_content() == round_disp
        assert page.locator("#mobile-funds").text_content() == funds_disp
        assert page.locator("#mobile-methane").text_content() == methane_disp


def test_mobile_strip_label_changes_with_methane_bands(base):
    with sync_playwright() as p:
        _, page = open_game(p, base, width=360, height=740)
        label = page.locator("#mobile-strip-label")

        # Initially methane is 0 -> band-low
        assert "band-low" in label.get_attribute("class")

        # Simulate high methane by directly updating the display
        page.evaluate("""
          document.getElementById('methane-display').textContent = 'Methane: 151';
        """)
        page.wait_for_timeout(200)
        assert "band-high" in label.get_attribute("class")

        # Simulate mid methane
        page.evaluate("""
          document.getElementById('methane-display').textContent = 'Methane: 75';
        """)
        page.wait_for_timeout(200)
        assert "band-mid" in label.get_attribute("class")
