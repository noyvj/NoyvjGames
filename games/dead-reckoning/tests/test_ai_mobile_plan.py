"""R4-DEMO-5 (swipe a leg card left to remove it, with an undo bar) and R4-DEMO-7 (the plan left on a chart is offered back). Playwright at phone
width (skipped when it or Pyodide's CDN is unavailable). The swipes are real touch events through the browser's own input pipeline. Nothing
is ever sent to the live backend."""

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


def _open(browser, base, errors):
    ctx = browser.new_context(viewport={"width": 360, "height": 740}, has_touch=True, is_mobile=True, service_workers="block")
    ctx.route("**/*fastapicloud*/**", lambda route: route.abort())
    page = ctx.new_page()
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(base + "index.html#play")
    page.evaluate("localStorage.clear()")
    page.reload()
    page.wait_for_function(READY, timeout=90000)
    return ctx, page


def _add_leg(page, heading):
    n = page.locator("#legs-list > li.leg").count()
    page.click("#add-leg-button")
    page.fill("#leg-%d-heading" % n, str(heading))
    page.press("#leg-%d-heading" % n, "Tab")


def _headings(page):
    return [page.input_value("#leg-%d-heading" % i) for i in range(page.locator("#legs-list > li.leg").count())]


def _swipe(ctx, page, selector, dx, dy=0):
    """A one-finger drag starting on the element's heading line, as a real touch."""
    page.locator(selector).scroll_into_view_if_needed()
    box = page.locator(selector).bounding_box()
    x, y = box["x"] + box["width"] * 0.5, box["y"] + box["height"] * 0.5
    cdp = ctx.new_cdp_session(page)
    cdp.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": [{"x": x, "y": y}]})
    for step in range(1, 9):
        cdp.send("Input.dispatchTouchEvent", {"type": "touchMove", "touchPoints": [{"x": x + dx * step / 8.0, "y": y + dy * step / 8.0}]})
    cdp.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})
    page.wait_for_timeout(150)


def test_swiping_a_leg_card_left_removes_it_and_the_bar_brings_it_back(base):
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx, page = _open(browser, base, errors)
        for heading in (10, 20, 30):
            _add_leg(page, heading)
        assert _headings(page) == ["10", "20", "30"]
        assert page.get_attribute("#undo-button", "id") == "undo-button" and not page.is_visible("#leg-undo-bar")
        head = "#legs-list > li:nth-child(2) .leg-head strong"
        _swipe(ctx, page, head, 40)                         # right: nothing
        _swipe(ctx, page, head, -40)                        # too short: nothing
        assert _headings(page) == ["10", "20", "30"]
        _swipe(ctx, page, head, -150)
        assert _headings(page) == ["10", "30"]
        assert page.is_visible("#leg-undo-bar") and "Leg 2 removed" in page.inner_text("#leg-undo-bar")
        page.click("#leg-undo-button")
        assert _headings(page) == ["10", "20", "30"] and not page.is_visible("#leg-undo-bar")
        # a swipe, then any other edit: the bar goes away rather than undoing the wrong thing
        _swipe(ctx, page, "#legs-list > li:nth-child(3) .leg-head strong", -150)
        assert _headings(page) == ["10", "20"] and page.is_visible("#leg-undo-bar")
        _add_leg(page, 40)
        assert not page.is_visible("#leg-undo-bar") and _headings(page) == ["10", "20", "40"]
        # the Remove button is still the keyboard path, and the dock's Undo still works and is a real, enabled control
        page.click("#legs-list > li:nth-child(1) button:has-text('Remove')")
        assert _headings(page) == ["20", "40"]
        page.click("#undo-button")
        assert _headings(page) == ["10", "20", "40"]
        assert page.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth") <= 1
        browser.close()
    assert errors == []


def _start(page, index):
    page.evaluate("""(i) => {
        const id = window.pyodide.runPython("charts.ORDER[" + i + "]");
        window.pyodide.runPython("handle(json.dumps({'action': 'start', 'chart_id': '" + id + "'}))");
        window.deadReckoningRefresh();
    }""", index)


def test_the_plan_left_on_a_chart_is_offered_back_and_resumed_leg_for_leg(base):
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx, page = _open(browser, base, errors)
        _add_leg(page, 77)
        _add_leg(page, 123)
        page.fill("#leg-1-hours", "2.5")
        page.press("#leg-1-hours", "Tab")
        assert not page.is_visible("#draft-indicator")                        # nothing is offered while the plan is on screen
        _start(page, 1)                                                       # off to another chart ...
        assert page.locator("#legs-list > li.leg").count() == 0 and not page.is_visible("#draft-indicator")
        _start(page, 0)                                                       # ... and back: the legs are offered
        assert page.is_visible("#draft-indicator") and "2 legs" in page.inner_text("#draft-text")
        assert page.locator("#legs-list > li.leg").count() == 0
        page.click("#draft-resume-button")
        assert _headings(page) == ["77", "123"] and page.input_value("#leg-1-hours") == "2.5"
        assert not page.is_visible("#draft-indicator")
        # emptying the plan on purpose forgets the draft
        page.click("#clear-button")
        _start(page, 1)
        _start(page, 0)
        assert not page.is_visible("#draft-indicator")
        # a draft can be discarded
        _add_leg(page, 5)
        _start(page, 1)
        _start(page, 0)
        assert page.is_visible("#draft-indicator") and "1 leg " in page.inner_text("#draft-text") + " "
        page.click("#draft-discard-button")
        assert not page.is_visible("#draft-indicator")
        _start(page, 1)
        _start(page, 0)
        assert not page.is_visible("#draft-indicator")
        # a broken stored draft is ignored, never an error
        page.evaluate("localStorage.setItem('dead-reckoning:drafts', '[{\"chart\": 7, \"legs\": \"x\"}, null, {\"chart\": \"a\", \"legs\": [{\"heading\": \"x\"}]}]')")
        _start(page, 1)
        _start(page, 0)
        assert not page.is_visible("#draft-indicator")
        browser.close()
    assert errors == []
