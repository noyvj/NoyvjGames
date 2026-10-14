"""R4-DEPC-9: Ctrl+P on the Desktop page prints a clean chart sheet with the plan listed. Playwright (skipped when it or Pyodide's CDN is
unavailable): with the print media on, the chart really takes space on the page, the plan is written out as text, nothing of the screen chrome is
left, and the sheet uses paper colours even from the dark theme. Nothing is ever sent to the live backend."""

import contextlib
import functools
import http.server
import socket
import threading
import urllib.request
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
pytest.importorskip("playwright.sync_api")
from playwright.sync_api import sync_playwright  # noqa: E402


def _online():
    try:
        urllib.request.urlopen("https://cdn.jsdelivr.net/pyodide/v0.26.4/full/pyodide.js", timeout=5).close()
        return True
    except Exception:
        return False


@pytest.fixture(scope="module")
def base():
    if not _online():
        pytest.skip("Pyodide's CDN is not reachable")

    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *args):
            pass

    handler = functools.partial(Quiet, directory=str(ROOT))
    with contextlib.closing(socket.socket()) as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    server = http.server.ThreadingHTTPServer(("127.0.0.1", port), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield "http://localhost:%d/games/dead-reckoning/" % port
    server.shutdown()


READY = "document.querySelector('#engine-status') && document.querySelector('#engine-status').textContent === '' && document.querySelector('#chart-holder svg')"


def test_the_print_sheet_has_the_chart_and_the_plan_as_text_in_paper_colours(base):
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 1440, "height": 900}, service_workers="block")
        ctx.route("**/*fastapicloud*/**", lambda route: route.abort())
        page = ctx.new_page()
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(base + "pc.html#play")
        page.evaluate("localStorage.clear(); localStorage.setItem('theme', 'dark')")
        page.reload()
        page.wait_for_function(READY, timeout=90000)
        page.evaluate("document.documentElement.setAttribute('data-theme', 'dark')")
        page.fill("#quick-leg-input", "090 6kn 2h")
        page.press("#quick-leg-input", "Enter")
        page.fill("#quick-leg-input", "045 5kn 1.5h")
        page.press("#quick-leg-input", "Enter")
        page.evaluate("window.dispatchEvent(new Event('beforeprint'))")
        page.emulate_media(media="print")
        items = page.locator("#print-plan li").all_inner_texts()
        assert items == ["Leg 1: steer 090 at 6 kn for 2 h", "Leg 2: steer 045 at 5 kn for 1.5 h"]
        box = page.locator("#chart-holder svg.dr-chart").bounding_box()
        assert box["width"] > 300 and box["height"] > 300
        for hidden in ("#pc-hintbar", ".ad-bar", "#add-leg-button", "#sail-button", "#quick-leg-input", "#result-panel"):
            assert not page.locator(hidden).first.is_visible(), hidden
        assert page.is_visible("#chart-title") and page.is_visible("#total-legs")
        assert page.evaluate("getComputedStyle(document.body).backgroundColor") == "rgb(255, 255, 255)"
        assert page.evaluate("getComputedStyle(document.documentElement).getPropertyValue('--sea').trim()") == "#dfe9e8"
        page.evaluate("window.dispatchEvent(new Event('afterprint'))")
        assert page.locator("#print-plan").count() == 0
        page.emulate_media(media="screen")
        assert page.is_visible("#sail-button")
        browser.close()
    assert errors == []
