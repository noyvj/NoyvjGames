"""The Daily Job in a real browser (Playwright; skipped when it or Pyodide's CDN is unavailable). The clock is fixed
by the browser, so the view passes a known date to the engine. Never touches the live backend."""

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
    yield "http://localhost:%d/games/heist-committee/" % port
    server.shutdown()


@pytest.mark.parametrize("page_name,width,height", [("index.html", 1440, 900), ("index.html", 360, 740), ("pc.html", 1440, 900), ("pc.html", 360, 740)])
def test_play_an_archive_day_from_the_calendar(base, page_name, width, height):
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
        page.wait_for_function("window.HC && window.HC.view", timeout=90000)
        assert "Day 20" in page.inner_text("#daily-today")
        page.click("[data-testid=heist-daily-archive]")
        assert page.locator("[data-testid=heist-daily-day]:not([disabled])").count() == 20
        page.click("[data-date='2026-10-05']")
        assert page.evaluate("HC.view.phase") == "scout" and page.evaluate("HC.view.daily.number") == 5
        page.click("[data-testid=heist-to-recruit]")
        assert page.locator("[data-testid^=heist-check-]").count() == 0          # every quirk is already on the file
        for cid in page.evaluate("HC.view.offer.map(c => c.id)")[:5]:
            page.click("[data-testid=heist-hire-%s]" % cid)
        page.click("[data-testid=heist-confirm-crew]")
        assert page.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth") <= 1
        page.evaluate("HC.send({action: 'start_heist'})")
        page.evaluate("HC.send({action: 'skip'})")
        page.evaluate("HC.send({action: 'finish'})")
        assert "Daily Job 5" in page.inner_text("[data-testid=heist-daily-result]")
        page.click("[data-testid=heist-back-to-board]")
        assert "Played 1 of 20" in page.inner_text("[data-testid=heist-daily-tally]")
        assert page.evaluate("HC.view.cash") == 300 and page.evaluate("HC.view.reputation") == 0
        page.reload()
        page.wait_for_function("window.HC && window.HC.view", timeout=90000)
        assert "Played 1 of 20" in page.inner_text("[data-testid=heist-daily-tally]")
        browser.close()
    assert errors == []
