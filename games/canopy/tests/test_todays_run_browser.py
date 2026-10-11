"""Z-5c in a real browser (Playwright; skipped when it or Pyodide's CDN is unavailable): Today's run starts an Expedition on the UTC
date's seed, asks before giving up a forest, does not restart the run already under way, and finishing it on today's seed (never an
older day's) counts once in the shared record the hub reads. The browser clock is fixed. Requests to the live backend are blocked:
nothing is ever sent there."""

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
    yield "http://localhost:%d/games/canopy/" % port
    server.shutdown()


READY = "!!window.pyodide && !!window.pyodide.globals.get('start_todays_run') && !!document.querySelector('#todays-run-slot button')"

FINISH = """() => {
    window.pyodide.runPython(`
global forest_tick
forest_tick = EXPEDITION_TICKS - 1
tick()
`);
    return window.pyodide.runPython('expedition_finished()');
}"""


def press(page):
    """Scroll the button to the middle of the page and click it (on a phone the docked bars cover the page's edges)."""
    page.locator("#todays-run-slot button").evaluate("e => { e.scrollIntoView({block: 'center'}); e.click(); }")


def open_panel(page):
    page.evaluate("document.getElementById('expedition-toggle-button').click()")
    page.wait_for_function("document.querySelector('#todays-run-slot button') && document.querySelector('#todays-run-slot button').offsetParent !== null", timeout=10000)


def expedition_seed(page):
    return page.evaluate("window.pyodide.runPython('current_expedition[\"seed\"] if current_expedition else \"\"')")


@pytest.mark.parametrize("page_name,width,height", [("index.html", 1440, 900), ("index.html", 360, 740), ("pc.html", 1440, 900)])
def test_todays_run_starts_the_dated_expedition_and_finishing_it_counts_once(base, page_name, width, height):
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
        today = page.evaluate("NoyvjSeed.daily.seed('canopy', '2026-10-20')")
        old = page.evaluate("NoyvjSeed.daily.seed('canopy', '2026-10-19')")

        # an Expedition on an older day's seed (begun as yesterday's run might have been) never counts
        page.evaluate("(s) => window.pyodide.globals.get('start_expedition')(s)", old)
        assert expedition_seed(page) == old
        assert page.evaluate(FINISH) is True
        assert page.evaluate("localStorage.getItem('noyvj-daily-v1')") is None

        # a forest is at stake (the finished Expedition's), so the button asks first; cancelling changes nothing
        open_panel(page)
        assert "Play today's run" in page.inner_text("#todays-run-slot") and today in page.inner_text("#todays-run-slot")
        press(page)
        page.wait_for_selector("#confirm-dialog-confirm", state="visible", timeout=10000)
        assert page.inner_text("#confirm-dialog-confirm") == "Start today's run" and today in page.inner_text("#confirm-dialog-message")
        assert "Nothing has changed yet" in page.inner_text("#expedition-seed-message")
        assert expedition_seed(page) == old
        page.click("#confirm-dialog-cancel")
        assert expedition_seed(page) == old

        # confirming starts today's run
        press(page)
        page.click("#confirm-dialog-confirm")
        assert expedition_seed(page) == today
        assert "Today's run is on" in page.inner_text("#expedition-seed-message")
        assert page.evaluate("NoyvjSeed.current()") == today
        assert page.evaluate("localStorage.getItem('noyvj-daily-v1')") is None     # starting is not finishing

        # the run already under way is never restarted
        press(page)
        assert "already playing today's run" in page.inner_text("#expedition-seed-message")
        assert page.evaluate("window.pyodide.runPython('forest_tick')") == 0

        # finishing it on today's seed counts once
        assert page.evaluate(FINISH) is True
        record = page.evaluate("JSON.parse(localStorage.getItem('noyvj-daily-v1'))")
        assert record["date"] == "2026-10-20" and list(record["runs"]) == ["canopy"]
        assert record["runs"]["canopy"]["seed"] == today and record["runs"]["canopy"]["text"].startswith("Expedition score ")
        assert record["runs"]["canopy"]["score"] > 0 and record["streaks"]["canopy"]["count"] == 1
        assert "Today's run done" in page.inner_text("#todays-run-slot")
        page.evaluate("window.pyodide.runPython('start_expedition(current_expedition[\"seed\"])')")
        assert page.evaluate(FINISH) is True
        assert page.evaluate("JSON.parse(localStorage.getItem('noyvj-daily-v1')).streaks.canopy.count") == 1
        assert page.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth") <= 1
        browser.close()
    assert errors == []
