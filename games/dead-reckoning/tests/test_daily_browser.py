"""The Daily Chart in a real browser (Playwright; skipped when it or Pyodide's CDN is unavailable). The browser's clock is
fixed, so the view passes a known date to the engine. The Desktop page is checked at desktop width only (that layout is
for wide windows). Requests to the live backend are blocked: nothing is ever sent there."""

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


@pytest.mark.parametrize("page_name,width,height", [("index.html", 1440, 900), ("index.html", 360, 740), ("pc.html", 1440, 900)])
def test_sail_an_archive_chart_from_the_calendar(base, page_name, width, height):
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": width, "height": height}, service_workers="block")
        ctx.clock.set_fixed_time("2026-10-20T09:00:00Z")
        ctx.route("**/*fastapicloud*/**", lambda route: route.abort())
        page = ctx.new_page()
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(base + page_name + "#play")
        page.evaluate("localStorage.clear()")
        page.reload()
        page.wait_for_function(READY, timeout=90000)

        def toggle():
            if page_name == "pc.html":
                page.click("button.pc-icon-button[title*='Daily'], button.pc-icon-button[aria-label*='Daily']")
            else:
                page.click("#daily-toggle-button")

        toggle()
        assert "Chart 20" in page.inner_text("#daily-today")
        page.click("[data-testid=dead-reckoning-daily-archive]")
        assert page.locator("[data-testid=dead-reckoning-daily-day]:not([disabled])").count() == 20
        page.click("[data-date='2026-10-05']")
        page.wait_for_function("document.querySelector('#chart-title').textContent === 'Daily Chart 5'", timeout=30000)
        assert "2026-10-05" in page.inner_text("[data-testid=dead-reckoning-daily-line]")
        assert page.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth") <= 1
        page.evaluate("""() => {
            window.pyodide.runPython("legs = charts.par_legs(run['chart_id'])\\nrun['legs'] = sim.clean_legs(_chart(), legs, limit=12)");
            window.deadReckoningRefresh();
        }""")
        page.click("#sail-button")
        page.click("#skip-button")
        assert page.inner_text("#result-stars-text").startswith("3 of 3 stars")
        if not page.is_visible("#daily-panel"):
            toggle()
        assert "Played 1 of 20" in page.inner_text("[data-testid=dead-reckoning-daily-tally]")
        assert page.evaluate("window.pyodide.runPython('meta[\"practice_seeds_played\"]')") == 0
        page.reload()
        page.wait_for_function(READY, timeout=90000)
        if not page.is_visible("#daily-panel"):
            toggle()
        assert "Played 1 of 20" in page.inner_text("[data-testid=dead-reckoning-daily-tally]")
        browser.close()
    assert errors == []
