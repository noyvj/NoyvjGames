"""Z-5c in a real browser (Playwright; skipped when it or Pyodide's CDN is unavailable): Today's run starts the classic schedule at
the UTC date's seed, never replaces a run under way, and finishing it on today's seed (never an older day's) counts once in the
shared record the hub reads. The browser clock is fixed. Requests to the live backend are blocked: nothing is ever sent there."""

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
    yield "http://localhost:%d/games/aftermath/" % port
    server.shutdown()


READY = "!!window.pyodide && !!window.pyodide.globals.get('start_todays_run') && !!document.querySelector('#todays-run-slot button')"

FINISH = """() => {
    for (let i = 0; i < 9; i++) {
        const done = window.pyodide.runPython('run.is_complete()');
        if (done) break;
        document.getElementById('resolve-event-button').click();
    }
    return window.pyodide.runPython('run.is_complete()');
}"""


def open_panel(page, page_name):
    """Classic keeps the codes panel as a closed <details>; the Desktop page opens it from Menu > Records."""
    if page_name == "pc.html":
        page.click("#pc-menu-button")
        page.click("button:has-text('Run codes and Today')")
    else:
        page.evaluate("document.getElementById('challenge-panel').open = true")


def press(page):
    """Scroll the button to the middle of the page and click it (on a phone the docked bars cover the page's edges)."""
    page.locator("#todays-run-slot button").evaluate("e => { e.scrollIntoView({block: 'center'}); e.click(); }")


@pytest.mark.parametrize("page_name,width,height", [("index.html", 1440, 900), ("index.html", 360, 740), ("pc.html", 1440, 900)])
def test_todays_run_starts_the_dated_schedule_and_finishing_it_counts_once(base, page_name, width, height):
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
        today = page.evaluate("NoyvjSeed.daily.seed('aftermath', '2026-10-20')")
        old = page.evaluate("NoyvjSeed.daily.seed('aftermath', '2026-10-19')")

        # a run begun on an older day's seed never counts
        page.evaluate("(s) => window.pyodide.globals.get('start_todays_run')(s)", old)
        assert page.evaluate(FINISH) is True
        assert page.evaluate("localStorage.getItem('noyvj-daily-v1')") is None

        # the button starts today's run
        open_panel(page, page_name)
        assert "Play today's run" in page.inner_text("#todays-run-slot") and today in page.inner_text("#todays-run-slot")
        press(page)
        assert "Today's run started" in page.inner_text("#todays-run-note")
        assert page.evaluate("window.pyodide.runPython('run.challenge[\"daily_seed\"]')") == today
        assert page.evaluate("window.pyodide.runPython('run.event_index')") == 0
        assert page.evaluate("NoyvjSeed.current()") == today
        assert page.evaluate("localStorage.getItem('noyvj-daily-v1')") is None     # starting is not finishing

        # a run under way is never replaced
        page.evaluate("document.getElementById('resolve-event-button').click()")
        press(page)
        assert "Nothing was changed" in page.inner_text("#todays-run-note")
        assert page.evaluate("window.pyodide.runPython('run.event_index')") == 1

        # finishing it on today's seed counts once
        assert page.evaluate(FINISH) is True
        record = page.evaluate("JSON.parse(localStorage.getItem('noyvj-daily-v1'))")
        assert record["date"] == "2026-10-20" and list(record["runs"]) == ["aftermath"]
        assert record["runs"]["aftermath"]["seed"] == today and record["runs"]["aftermath"]["text"].startswith("Ended with ")
        assert record["streaks"]["aftermath"]["count"] == 1
        press(page)
        assert "Today's run done" in page.inner_text("#todays-run-slot")
        assert page.evaluate(FINISH) is True
        assert page.evaluate("JSON.parse(localStorage.getItem('noyvj-daily-v1')).streaks.aftermath.count") == 1
        assert page.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth") <= 1
        browser.close()
    assert errors == []
