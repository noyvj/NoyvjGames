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


def test_methane_thermometer_structure_and_toggle(base):
    """R4-HEMO-4: thermometer exists, updates on methane change, and toggles open state."""
    with sync_playwright() as p:
        browser, page = open_game(p, base)

        # Check structure exists
        assert page.locator("#methane-thermo-fill").count() == 1
        assert page.locator("#methane-thermo-breakdown").count() == 1

        # Initially hidden because methane is 0
        thermo = page.locator("#methane-thermometer")
        assert not thermo.is_visible()

        # Simulate methane > 0 to trigger observer
        page.locator("#methane-display").evaluate("el => el.textContent = 'Methane: 50'")
        page.wait_for_timeout(100)

        assert thermo.is_visible()

        # Tap to open breakdown
        thermo.click()
        assert thermo.evaluate("el => el.classList.contains('open')")

        browser.close()
