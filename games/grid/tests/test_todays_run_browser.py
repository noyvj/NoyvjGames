"""Z-5c in a real browser (Playwright; skipped when it or Pyodide's CDN is unavailable): Today's run puts the UTC date's seed on a
fresh run, never replaces a run under way, and finishing a run on today's seed (never an older day's) counts once in the
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
    yield "http://localhost:%d/games/grid/" % port
    server.shutdown()


READY = "document.querySelector('#scenario-toggle-button') && document.querySelector('#scenario-toggle-button').textContent !== 'Loading...' && !!window.pyodide"

PLAY_AND_FINISH = """() => {
    window.pyodide.runPython(`
for _ in range(6):
    runstate.state.advance_round(rng=lambda: 1.0, age_rng=lambda: 1.0)
runstate.state.plant_counts["solar"] = 5
`);
    return window.pyodide.runPython("finish_run()");
}"""


def open_run_setup(page, page_name):
    """Classic shows the difficulty row at the top; the Desktop page keeps it in a window under Menu > Game."""
    if page_name == "pc.html":
        page.click("#pc-menu-button")
        page.click("button:has-text('Difficulty and run setup')")


@pytest.mark.parametrize("page_name,width,height", [("index.html", 1440, 900), ("index.html", 360, 740), ("pc.html", 1440, 900)])
def test_todays_run_sets_the_dated_seed_and_finishing_it_counts_once(base, page_name, width, height):
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
        today = page.evaluate("NoyvjSeed.daily.seed('grid', '2026-10-20')")
        old = page.evaluate("NoyvjSeed.daily.seed('grid', '2026-10-19')")
        own = page.evaluate("window.pyodide.runPython('runstate.state.seed')")
        assert own != today

        # a run begun on an older day's seed, and an ordinary run, never count
        page.evaluate("(s) => window.pyodide.globals.get('start_todays_run')(s)", old)
        assert page.evaluate(PLAY_AND_FINISH) is not None
        assert page.evaluate("window.pyodide.runPython('runstate.state.seed')") != old
        assert page.evaluate(PLAY_AND_FINISH) is not None
        assert page.evaluate("localStorage.getItem('noyvj-daily-v1')") is None

        # the button puts today's seed on the fresh run
        open_run_setup(page, page_name)
        assert "Play today's run" in page.inner_text("#todays-run-slot") and today in page.inner_text("#todays-run-slot")
        page.click("#todays-run-slot button")
        assert today in page.inner_text("#todays-run-note") and "counts it for today" in page.inner_text("#todays-run-note")
        assert page.evaluate("window.pyodide.runPython('runstate.state.seed')") == today
        assert page.evaluate("NoyvjSeed.current()") == today
        assert page.evaluate("localStorage.getItem('noyvj-daily-v1')") is None   # setting a seed is not finishing

        # a run under way is never replaced
        page.evaluate("window.pyodide.runPython('runstate.state.advance_round(rng=lambda: 1.0, age_rng=lambda: 1.0)')")
        funds = page.evaluate("window.pyodide.runPython('runstate.state.funds')")
        page.click("#todays-run-slot button")
        assert "Nothing was changed" in page.inner_text("#todays-run-note")
        assert page.evaluate("window.pyodide.runPython('runstate.state.seed')") == today
        assert page.evaluate("window.pyodide.runPython('runstate.state.funds')") == funds
        assert page.evaluate("window.pyodide.runPython('runstate.state.round_number')") == 2

        # finishing the run on today's seed counts once
        assert page.evaluate(PLAY_AND_FINISH) is not None
        record = page.evaluate("JSON.parse(localStorage.getItem('noyvj-daily-v1'))")
        assert record["date"] == "2026-10-20" and list(record["runs"]) == ["grid"]
        assert record["runs"]["grid"]["seed"] == today and record["runs"]["grid"]["text"].startswith("Grade ")
        assert record["streaks"]["grid"]["count"] == 1
        page.click("#todays-run-slot button")
        assert page.evaluate("window.pyodide.runPython('runstate.state.seed')") == today
        assert "Today's run done" in page.inner_text("#todays-run-slot")
        assert page.evaluate(PLAY_AND_FINISH) is not None
        assert page.evaluate("JSON.parse(localStorage.getItem('noyvj-daily-v1')).streaks.grid.count") == 1
        assert page.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth") <= 1
        browser.close()
    assert errors == []
