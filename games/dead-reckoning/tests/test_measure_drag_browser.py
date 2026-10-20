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
GAME = "dead-reckoning"


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


def test_measure_readout_element_and_initial_text(base):
    with sync_playwright() as p:
        browser, page = open_game(p, base)
        page.wait_for_selector("#chart-holder svg", timeout=30000)

        readout = page.locator("#measure-readout")
        assert readout.is_visible()
        assert "Hold R and drag" in readout.text_content()

        # Verify the readout updates when dragging on the chart while holding R
        bbox = page.locator("#chart-holder svg").first.bounding_box()
        cx = bbox["x"] + bbox["width"] / 2
        cy = bbox["y"] + bbox["height"] / 2

        page.keyboard.down("r")
        page.mouse.move(cx, cy)
        page.mouse.down(button="left")
        page.mouse.move(cx + 50, cy + 50)

        import re
        # Wait a frame for the event to process
        page.wait_for_timeout(100)
        text = readout.text_content()
        assert re.search(r"Measure: \d+\.?\d* nm on \d{3}", text)

        page.keyboard.up("r")
        page.mouse.up(button="left")
        browser.close()
