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
GAME = "continuum"


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


def scene_ready(page):
    page.wait_for_timeout(3000)
    return page.evaluate("!!(window.ContinuumScene && window.ContinuumScene.ready())")


def test_the_wheel_zooms_the_camera_and_stops_at_the_limits(base):
    with sync_playwright() as p:
        browser, page = open_game(p, base)
        if not scene_ready(page):
            pytest.skip("no WebGL")

        # Zoom in (deltaY negative)
        page.evaluate("""
            const el = document.querySelector('#visual3d-container');
            el.dispatchEvent(new WheelEvent('wheel', { deltaY: -100, bubbles: true, cancelable: true }));
        """)
        dist = page.evaluate("window.ContinuumScene.cameraState().distance")
        assert abs(dist - 9.5 / 1.1) < 0.01

        # Thirty more wheel-up events
        for _ in range(30):
            page.evaluate("""
                const el = document.querySelector('#visual3d-container');
                el.dispatchEvent(new WheelEvent('wheel', { deltaY: -100, bubbles: true, cancelable: true }));
            """)
        dist = page.evaluate("window.ContinuumScene.cameraState().distance")
        assert dist == 3.5

        # Sixty events with deltaY 100 (zoom out)
        for _ in range(60):
            page.evaluate("""
                const el = document.querySelector('#visual3d-container');
                el.dispatchEvent(new WheelEvent('wheel', { deltaY: 100, bubbles: true, cancelable: true }));
            """)
        dist = page.evaluate("window.ContinuumScene.cameraState().distance")
        assert dist == 16.0

        # No JS errors expected during interaction.
        browser.close()
