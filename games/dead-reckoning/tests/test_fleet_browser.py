"""Two ships in a real browser (Playwright; skipped when it or Pyodide's CDN is unavailable): plan both ships on the page, sail, read the
reveal, and open a two-ship practice chart from the toggle. Requests to the live backend are blocked: nothing is ever sent there."""

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


def _set_leg(page, i, heading, speed, hours):
    for field, value in (("heading", heading), ("speed", speed), ("hours", hours)):
        page.fill("#leg-%d-%s" % (i, field), str(value))
        page.press("#leg-%d-%s" % (i, field), "Tab")


@pytest.mark.parametrize("page_name,width,height", [("index.html", 1440, 900), ("index.html", 360, 740), ("pc.html", 1440, 900)])
def test_plan_two_ships_sail_and_read_the_reveal(base, page_name, width, height):
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": width, "height": height}, service_workers="block")
        ctx.route("**/*fastapicloud*/**", lambda route: route.abort())
        page = ctx.new_page()
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(base + page_name + "#play")
        page.evaluate("localStorage.clear()")
        page.reload()
        page.wait_for_function(READY, timeout=90000)
        page.evaluate("""() => {
            window.pyodide.runPython("for c in charts.ORDER[:-7]:\\n    meta['charts'][c] = dict(state.new_record(), stars=1)\\nhandle(json.dumps({'action': 'start', 'chart_id': 'two-01'}))");
            window.deadReckoningRefresh();
        }""")
        assert page.is_visible("#ship-box") and "at least 1 nm apart" in page.inner_text("#chart-goal")
        page.click("#add-leg-button")
        _set_leg(page, 0, 90, 4, 4)
        page.click("#ship-b-button")
        assert page.get_attribute("#ship-b-button", "aria-pressed") == "true"
        page.click("#add-leg-button")
        _set_leg(page, 0, 0, 4, 4)
        assert "inside the 1 nm rule" in page.inner_text("#fleet-line")
        page.click("#sail-button")
        page.get_by_role("button", name="Sail", exact=True).last.click()      # the confirm: the plots meet
        page.wait_for_selector("#skip-button", state="visible")
        page.click("#skip-button")
        assert page.inner_text("#result-stars-text").startswith("2 of 3 stars")
        assert "Ship A - Landfall" in page.inner_text("#result-criteria") and "Apart:" in page.inner_text("#result-criteria")
        assert page.locator("#dr-true-track-2").count() == 1 and page.locator(".dr-approach-true").count() == 1
        assert page.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth") <= 1
        # a retry is free: the same two plans come back
        page.click("#retry-button")
        assert page.locator("#ship-box").is_visible() and "Ship B (1 leg)" in page.inner_text("#ship-b-button")
        browser.close()
    assert errors == []


def test_the_practice_toggle_opens_a_two_ship_chart_with_a_t_code(base):
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 1440, "height": 900}, service_workers="block")
        ctx.route("**/*fastapicloud*/**", lambda route: route.abort())
        page = ctx.new_page()
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(base + "index.html#play")
        page.evaluate("localStorage.clear()")
        page.reload()
        page.wait_for_function(READY, timeout=90000)
        page.click("#picker-toggle-button")
        page.check("#practice-two-checkbox")
        page.locator("#practice-levels button").first.click()
        page.wait_for_function("document.querySelector('#practice-line') && !document.querySelector('#practice-line').hidden", timeout=60000)
        text = page.inner_text("#practice-line")
        assert "two ships" in text and "DR1T-" in text and page.is_visible("#ship-box")
        browser.close()
    assert errors == []
