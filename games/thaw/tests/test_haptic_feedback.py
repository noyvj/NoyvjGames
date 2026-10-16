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


def test_haptic_feedback_triggers_on_threshold_crossing(base):
    with sync_playwright() as p:
        browser, page = open_game(p, base)
        # Ensure reduced motion is off for the test
        page.evaluate("document.documentElement.dataset.reducedMotion = 'false'")

        advance_btn = page.locator("#advance-round-button")
        # Advance until temperature crosses 10.0 (approx 10 rounds)
        for _ in range(12):
            advance_btn.click()
            page.wait_for_timeout(300)

        # The pulse class should be attached briefly when crossing the threshold
        pulse_el = page.locator("#temperature-display.threshold-crossed-pulse")
        assert pulse_el.count() > 0, \
            "Temperature display should have received .threshold-crossed-pulse class when crossing a threshold"

        browser.close()
