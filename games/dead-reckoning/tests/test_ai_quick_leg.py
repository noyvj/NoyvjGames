"""R4-DEPC-1: the Desktop quick-leg box ("090 6kn 2h"). The engine part: add_leg may name the new leg's values, and they are forced onto the
legal grid like any edit. The page part (Playwright; skipped when it or Pyodide's CDN is unavailable): the box is really on the Desktop page, a typed
leg lands in the plan, a bad one is explained, and the Classic page does not show the box. Nothing is ever sent to the live backend."""

import contextlib
import functools
import http.server
import socket
import threading
import urllib.request
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]


def test_add_leg_with_values_adds_one_cleaned_leg_and_one_undo_step(g):
    v = g.call("add_leg", heading=90, speed=6, hours=2)
    assert v["legs"] == [{"heading": 90, "speed": 6.0, "hours": 2.0}]
    v = g.call("add_leg", heading=400, speed=99, hours=0.2)
    assert v["legs"][1] == {"heading": 40, "speed": 7.0, "hours": 0.5}
    v = g.call("undo")
    assert len(v["legs"]) == 1 and v["legs"][0]["heading"] == 90


def test_add_leg_without_values_is_unchanged_and_bad_values_fall_back(g):
    plain = g.call("add_leg")["legs"][0]
    g.call("clear")
    junk = g.call("add_leg", heading="north", speed=True, hours=None)["legs"][0]
    assert junk == plain                      # a value that is not a number is ignored: that field keeps its default
    half = g.call("add_leg", hours=3)["legs"][1]
    assert half["hours"] == 3.0 and half["heading"] == plain["heading"]


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


def _open(browser, base, page_name, width, height, errors):
    ctx = browser.new_context(viewport={"width": width, "height": height}, service_workers="block")
    ctx.route("**/*fastapicloud*/**", lambda route: route.abort())
    page = ctx.new_page()
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(base + page_name + "#play")
    page.evaluate("localStorage.clear()")
    page.reload()
    page.wait_for_function(READY, timeout=90000)
    return page


def test_the_quick_leg_box_adds_a_typed_leg_on_the_desktop_page(base):
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = _open(browser, base, "pc.html", 1440, 900, errors)
        assert page.is_visible("#quick-leg-input")
        page.click("#quick-leg-input")
        page.fill("#quick-leg-input", "090 6kn 2h")
        page.press("#quick-leg-input", "Enter")
        assert page.input_value("#leg-0-heading") == "90" and page.input_value("#leg-0-speed") == "6" and page.input_value("#leg-0-hours") == "2"
        assert page.input_value("#quick-leg-input") == ""
        page.fill("#quick-leg-input", "270 4 1.5")      # units are optional
        page.press("#quick-leg-input", "Enter")
        assert page.input_value("#leg-1-heading") == "270" and page.input_value("#leg-1-hours") == "1.5"
        page.fill("#quick-leg-input", "sideways fast")
        page.press("#quick-leg-input", "Enter")
        assert "not a leg" in page.inner_text("#quick-leg-note") and page.get_attribute("#quick-leg-input", "aria-invalid") == "true"
        assert page.locator("#legs-list > li").count() == 2
        page.click("body", position={"x": 5, "y": 5})
        page.keyboard.press("l")                         # L jumps to the box
        assert page.evaluate("document.activeElement.id") == "quick-leg-input"
        browser.close()
    assert errors == []


def test_the_classic_page_does_not_show_the_quick_leg_box(base):
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = _open(browser, base, "index.html", 1440, 900, errors)
        assert not page.is_visible("#quick-leg-input")
        browser.close()
    assert errors == []
