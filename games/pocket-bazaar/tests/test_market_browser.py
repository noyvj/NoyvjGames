"""The Daily Market in a real browser (Playwright; skipped when it or Pyodide's CDN is unavailable). The browser's clock
is fixed, so the view passes a known date to the engine. The Desktop page is checked at desktop width only (that layout
is for wide windows, as the rest of this game's Desktop tests assume). Never touches the live backend."""

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
    yield "http://localhost:%d/games/pocket-bazaar/" % port
    server.shutdown()


READY = "document.querySelector('#engine-status') && document.querySelector('#engine-status').textContent === '' && !document.querySelector('#market-panel').hidden"


@pytest.mark.parametrize("page_name,width,height", [("index.html", 1440, 900), ("index.html", 360, 740), ("pc.html", 1440, 900)])
def test_play_an_archive_market_from_the_calendar(base, page_name, width, height):
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": width, "height": height}, service_workers="block")
        ctx.clock.set_fixed_time("2026-10-20T09:00:00Z")
        page = ctx.new_page()
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(base + page_name + "#play")
        page.evaluate("localStorage.clear()")
        page.reload()
        page.wait_for_function(READY, timeout=90000)
        assert "Market 20" in page.inner_text("#market-today")
        page.click("[data-testid=pocket-bazaar-market-archive]")
        assert page.locator("[data-testid=pocket-bazaar-market-day]:not([disabled])").count() == 20
        page.click("[data-date='2026-10-05']")
        assert page.evaluate("document.getElementById('game').dataset.phase") == "open"
        assert "Daily Market 5" in page.inner_text("#market-open-banner")
        assert page.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth") <= 1
        page.click("#crates button >> nth=0")
        # finish the market with the engine's own greedy player, then let the page redraw
        page.evaluate("""() => {
            window.pyodide.runPython("import marketbot\\nmarketbot.play(stall.day, list(stall.families()))\\nstall.close_market()");
            window.pocketBazaarRefresh();
        }""")
        assert page.evaluate("document.getElementById('game').dataset.phase") == "closed"
        assert page.is_visible("[data-testid=pocket-bazaar-market-result]")
        assert "Market 2026-10-05 is done" in page.inner_text("[data-testid=pocket-bazaar-market-result]")
        assert "Played 1 of 20" in page.inner_text("[data-testid=pocket-bazaar-market-tally]")
        assert page.evaluate("document.getElementById('stat-coins').textContent") == "0"
        page.reload()
        page.wait_for_function(READY, timeout=90000)
        assert "Played 1 of 20" in page.inner_text("[data-testid=pocket-bazaar-market-tally]")
        browser.close()
    assert errors == []
