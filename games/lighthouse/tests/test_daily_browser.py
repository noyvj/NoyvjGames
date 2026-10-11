"""Z-5c in a real browser (Playwright; skipped when it or Pyodide's CDN is unavailable): Today's run sails a year from the UTC
date's seed, asks first, and a year from today's seed (never an older day's) counts once in the shared daily record when it
reaches the year end. The browser clock is fixed. Requests to the live backend are blocked: nothing is ever sent there."""

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
ENGINE_RUN = "window.pyodide.globals.get('get_state')().toJs({dict_converter: Object.fromEntries}).run"


def _to_year_end(page):
    """Put the loaded year at its year end (the page redraws through load_state, like a save being loaded)."""
    page.evaluate("""() => {
        const s = window.pyodide.globals.get('get_state')().toJs({dict_converter: Object.fromEntries});
        s.run.phase = 'yearend'; s.run.night = 40; s.run.mode = 'year';
        window.pyodide.globals.get('load_state')(window.pyodide.toPy(s));
    }""")


@pytest.mark.parametrize("page_name,width,height", [("index.html", 1440, 900), ("index.html", 360, 740), ("pc.html", 1440, 900)])
def test_todays_run_starts_the_dated_year_and_the_year_end_records_it_once(base, page_name, width, height):
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
        page.wait_for_function("NoyvjSeed.current().indexOf('LIGHTHOUSE-') === 0", timeout=30000)
        daily = page.evaluate("NoyvjSeed.daily.seed('lighthouse', '2026-10-20')")
        ordinary = page.evaluate("NoyvjSeed.current()")
        assert ordinary != daily
        page.evaluate("document.getElementById('settings-panel').hidden = false")
        assert "Play today's run" in page.inner_text("#daily-slot")
        assert daily in page.inner_text("#daily-slot")

        # an ordinary year ending today never counts
        _to_year_end(page)
        assert page.evaluate("localStorage.getItem('noyvj-daily-v1')") is None

        # Today's run asks first; cancelling changes nothing
        page.evaluate("document.getElementById('settings-panel').hidden = false")
        page.click("#daily-slot button")
        assert "sail today" in page.inner_text("#confirm-dialog-overlay").lower()
        page.click("#confirm-dialog-cancel")
        assert page.evaluate("NoyvjSeed.current()") == ordinary

        page.click("#daily-slot button")
        page.click("#confirm-dialog-confirm")
        page.wait_for_function("NoyvjSeed.current() === '%s'" % daily, timeout=10000)
        assert page.evaluate(ENGINE_RUN + ".seed_text") == daily
        assert page.evaluate("localStorage.getItem('noyvj-daily-v1')") is None   # starting is not finishing

        _to_year_end(page)
        record = page.evaluate("JSON.parse(localStorage.getItem('noyvj-daily-v1'))")
        assert record["date"] == "2026-10-20" and list(record["runs"]) == ["lighthouse"]
        assert record["runs"]["lighthouse"]["seed"] == daily and record["runs"]["lighthouse"]["text"].startswith("Year kept")
        assert record["streaks"]["lighthouse"]["count"] == 1
        _to_year_end(page)   # a second draw of the same screen counts nothing more
        assert page.evaluate("JSON.parse(localStorage.getItem('noyvj-daily-v1')).streaks.lighthouse.count") == 1
        assert "Today's run done" in page.inner_text("#yearend-daily")

        # a year from an older day's seed does not count the next day
        page.evaluate("localStorage.removeItem('noyvj-daily-v1')")
        old = page.evaluate("NoyvjSeed.daily.seed('lighthouse', '2026-10-19')")
        page.evaluate("document.getElementById('settings-panel').hidden = false")
        page.fill("#seed-start-slot input", old)
        page.click("#seed-start-slot button[type=submit]")
        page.click("button:has-text('Start from this seed')")
        page.wait_for_function("NoyvjSeed.current() === '%s'" % old, timeout=10000)
        _to_year_end(page)
        assert page.evaluate("localStorage.getItem('noyvj-daily-v1')") is None
        assert page.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth") <= 1
        browser.close()
    assert errors == []
