"""Z-1c in a real browser (Playwright; skipped when it or Pyodide's CDN is unavailable): the year's seed is shown and
copied, a typed seed always gives the same year, a wrong seed is explained, and the seed survives a reload."""

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
    yield "http://localhost:%d/games/lighthouse/" % port
    server.shutdown()


READY = "document.querySelector('#engine-status') && document.querySelector('#engine-status').textContent === ''"
ENGINE_SEED = "window.pyodide.globals.get('get_state')().toJs({dict_converter: Object.fromEntries}).run.seed"


@pytest.mark.parametrize("page_name,width,height", [("index.html", 1440, 900), ("index.html", 360, 740), ("pc.html", 1440, 900)])
def test_the_years_seed_is_shown_copied_and_can_be_started_from(base, page_name, width, height):
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": width, "height": height}, service_workers="block")
        ctx.grant_permissions(["clipboard-read", "clipboard-write"])
        ctx.route("**/*fastapicloud*/**", lambda route: route.abort())
        page = ctx.new_page()
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(base + page_name + "#play")
        page.evaluate("localStorage.clear()")
        page.reload()
        page.wait_for_function(READY, timeout=90000)
        page.wait_for_function("NoyvjSeed.current().indexOf('LIGHTHOUSE-') === 0", timeout=30000)
        first = page.evaluate("NoyvjSeed.current()")
        page.evaluate("document.getElementById('settings-panel').hidden = false")
        assert first in page.inner_text("#seed-copy-slot")
        page.click("#seed-copy-slot .noyvj-seed-copy button")
        assert page.evaluate("navigator.clipboard.readText()") == first

        def start(text):
            page.evaluate("document.getElementById('settings-panel').hidden = false")
            page.fill("#seed-start-slot input", text)
            page.click("#seed-start-slot button[type=submit]")
            page.click("button:has-text('Start from this seed')")
            page.wait_for_function("NoyvjSeed.current() === 'LIGHTHOUSE-K7F2Q'", timeout=10000)
            return page.evaluate(ENGINE_SEED)

        a = start("k7f2q")
        b = start("LIGHTHOUSE-K7F2Q")
        assert a == b and isinstance(a, int)
        assert "LIGHTHOUSE-K7F2Q" in page.inner_text("#seed-copy-slot")
        page.fill("#seed-start-slot input", "TIDE-K7F2Q")
        page.click("#seed-start-slot button[type=submit]")
        assert "for TIDE" in page.inner_text("#seed-start-slot .noyvj-seed-error")
        page.reload()
        page.wait_for_function(READY, timeout=90000)
        page.wait_for_function("NoyvjSeed.current() === 'LIGHTHOUSE-K7F2Q'", timeout=30000)
        assert page.evaluate(ENGINE_SEED) == a
        assert page.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth") <= 1
        browser.close()
    assert errors == []
