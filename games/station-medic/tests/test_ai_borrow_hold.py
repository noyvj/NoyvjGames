"""R4-SMMO-8: press and hold a supply shelf to borrow a spare of it through the shared confirm, which names the cost.
Static wiring plus a real-browser check (skipped when Playwright or Pyodide's CDN is unavailable)."""

import contextlib
import functools
import http.server
import re
import socket
import threading
import urllib.request
from pathlib import Path

import pytest

GAME_DIR = Path(__file__).resolve().parent.parent
ROOT = GAME_DIR.parents[1]
APP = (GAME_DIR / "app.js").read_text(encoding="utf-8")
HTML = (GAME_DIR / "index.html").read_text(encoding="utf-8")


def test_the_hold_is_wired_to_elements_that_exist_and_sends_a_known_action():
    assert 'id="cabinet-list"' in HTML and 'id="borrow-row"' in HTML
    block = APP.split("function _initBorrowHold")[1].split("function wire()")[0]
    assert '$("cabinet-list")' in block and "data-item" in block and "e.timeStamp - t0 >= HOLD_MS" in block
    assert 'action: "borrow", item: item.i' in block and "askThen(" in block
    assert "setTimeout" not in block and "setInterval" not in block
    assert "_initBorrowHold();" in APP.split("function wire()")[1]
    # every shelf node carries the data-item the hold reads
    assert "li.dataset.item = String(i.i)" in APP
    # the keyboard and one-tap path stays
    assert 'action: "borrow", item: i.i' in APP.split("var row = $(\"borrow-row\")")[1][:400]


def test_the_old_unreachable_confirm_sheet_is_gone():
    assert "borrow-confirm" not in HTML and "borrow-confirm" not in APP


def _online():
    try:
        urllib.request.urlopen("https://cdn.jsdelivr.net/pyodide/v0.26.4/full/pyodide.js", timeout=5).close()
        return True
    except Exception:
        return False


@pytest.fixture(scope="module")
def base():
    pytest.importorskip("playwright.sync_api")
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
    yield "http://localhost:%d/games/station-medic/" % port
    server.shutdown()


READY = "document.querySelector('#engine-status') && document.querySelector('#engine-status').textContent === ''"


def _hold(page, selector, ms):
    page.locator(selector).first.evaluate("e => e.scrollIntoView({ block: 'center' })")   # clear of the fixed ad bar
    box = page.locator(selector).first.bounding_box()
    x, y = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
    page.mouse.move(x, y)
    page.mouse.down()
    page.wait_for_timeout(ms)
    page.mouse.up()


def _borrows(page):
    return page.evaluate("window.stationMedicView().tally.borrows")


@pytest.mark.parametrize("width,height", [(360, 740), (1440, 900)])
def test_a_long_press_asks_with_the_cost_and_borrowing_counts(base, width, height):
    from playwright.sync_api import sync_playwright
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": width, "height": height}, service_workers="block")
        ctx.route("**/*fastapicloud*/**", lambda route: route.abort())
        page = ctx.new_page()
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(base + "index.html#play")
        page.wait_for_function(READY, timeout=90000)
        sel = "#cabinet-list li.shelf:not(.empty) .shelf-pick"
        page.wait_for_selector("#cabinet-list", state="attached")
        if page.locator(sel).count() == 0:        # a phone shows one tab at a time: the first shift has no scans, so use Treatments
            page.click("#cabinet-tab-treat")
        page.wait_for_selector(sel, state="visible")
        before = _borrows(page)

        # a short press only picks the shelf up
        _hold(page, sel, 50)
        assert not page.get_by_role("button", name=re.compile("Borrow it")).is_visible()
        assert page.locator(sel).first.get_attribute("aria-pressed") == "true"
        _hold(page, sel, 50)      # put it back

        # a long press asks, naming the cost, and does not pick the shelf up
        _hold(page, sel, 900)
        confirm = page.get_by_role("button", name=re.compile("Borrow it"))
        confirm.wait_for(state="visible")
        assert "costs 1" in page.locator("body").inner_text()
        assert page.locator(sel).first.get_attribute("aria-pressed") == "false"
        assert _borrows(page) == before
        confirm.click()
        page.wait_for_function("(b) => window.stationMedicView().tally.borrows === b + 1", arg=before)
        browser.close()
    assert errors == []
