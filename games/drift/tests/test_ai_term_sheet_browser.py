"""R4-DRMO-9 in a real phone-width page: long-press on a term opens the bottom sheet, a tap still opens the
popover, the keyboard path works, and the sheet does not cover the Advance Round button, the floating buttons
or the ad bar."""
import contextlib
import functools
import http.server
import socket
import threading
from pathlib import Path

import pytest

pytest.importorskip("playwright.sync_api")
from playwright.sync_api import sync_playwright  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]
GAME = "drift"
CHIP = "#glossary-capacity-button"

READY = ("(() => { const s = document.querySelector('#engine-status');"
         " if (s) return s.textContent === '' || s.hidden;"
         " return !!window.pyodide && !!window.pyodide.globals.get('get_state'); })()")


@pytest.fixture(scope="module")
def base():
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *args):
            pass

    handler = functools.partial(Quiet, directory=str(ROOT))
    with contextlib.closing(socket.socket()) as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    server = http.server.ThreadingHTTPServer(("127.0.0.1", port), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield "http://localhost:%d/games/%s/" % (port, GAME)
    server.shutdown()


def open_game(p, base, width=360, height=740, touch=False):
    browser = p.chromium.launch()
    ctx = browser.new_context(viewport={"width": width, "height": height}, service_workers="block",
                              has_touch=touch, is_mobile=touch)
    ctx.route("**/*fastapicloud*/**", lambda route: route.abort())
    page = ctx.new_page()
    page.goto(base + "index.html#play")
    page.wait_for_function(READY, timeout=90000)
    page.wait_for_timeout(800)
    page.locator(CHIP).scroll_into_view_if_needed()
    return browser, ctx, page


def hold(page, ms):
    box = page.locator(CHIP).bounding_box()
    page.mouse.move(box["x"] + 10, box["y"] + 8)
    page.mouse.down()
    page.wait_for_timeout(ms)
    page.mouse.up()


def active_id(page):
    return page.evaluate("document.activeElement.id")


def test_tap_still_opens_the_popover_and_a_long_press_opens_the_sheet(base):
    with sync_playwright() as p:
        browser, _ctx, page = open_game(p, base)
        assert page.is_hidden("#glossary-sheet")
        page.click(CHIP)
        assert page.get_attribute(CHIP, "aria-expanded") == "true"
        assert page.is_hidden("#glossary-sheet")
        page.click(CHIP)
        hold(page, 150)                                    # a short press is a tap: popover pinned, no sheet
        assert page.is_hidden("#glossary-sheet")
        assert page.get_attribute(CHIP, "aria-expanded") == "true"
        page.click(CHIP)
        hold(page, 650)
        assert page.is_visible("#glossary-sheet")
        assert page.inner_text("#glossary-sheet-title") == "Capacity"
        assert "housing" in page.inner_text("#glossary-sheet-text").lower()
        assert page.is_visible("#glossary-sheet-more")          # Capacity has a Real Story link
        assert page.get_attribute(CHIP, "aria-expanded") == "false", "the long-press must not also pin the popover"
        assert active_id(page) == "glossary-sheet"
        browser.close()


def test_sheet_clears_buttons_and_ad_bar_and_the_page_does_not_scroll_sideways(base):
    with sync_playwright() as p:
        browser, _ctx, page = open_game(p, base)
        hold(page, 650)
        page.wait_for_timeout(500)   # the slide-up is 0.2s
        boxes = page.evaluate("""(() => {
            const r = e => { const b = e.getBoundingClientRect(); return [b.left, b.top, b.right, b.bottom]; };
            const out = {sheet: r(document.getElementById('glossary-sheet')), others: {}};
            for (const e of document.querySelectorAll('body *')) {
                if (e.id === 'glossary-sheet' || e.closest('#glossary-sheet')) continue;
                if (getComputedStyle(e).position !== 'fixed') continue;
                const b = r(e);
                if (b[2] - b[0] <= 0 || (b[2] - b[0] >= innerWidth && b[3] - b[1] >= innerHeight)) continue;
                out.others[e.id || e.className] = b;
            }
            return out;
        })()""")
        sl, st, sr, sb = boxes["sheet"]
        assert sl >= 0 and sr <= 360 and st >= 0
        for name in ("advance-round-wrap", "ad-bar ad-bar--bottom", "theme-toggle-floating", "story-toggle"):
            ol, ot, orr, ob = boxes["others"][name]
            overlap = not (orr <= sl or ol >= sr or ob <= st or ot >= sb)
            assert not overlap, "the sheet covers " + name
        assert page.evaluate("document.documentElement.scrollWidth") <= 360
        browser.close()


def test_escape_close_button_outside_tap_and_focus_return(base):
    with sync_playwright() as p:
        browser, _ctx, page = open_game(p, base)
        hold(page, 650)
        page.keyboard.press("Escape")
        assert page.is_hidden("#glossary-sheet")
        assert active_id(page) == "glossary-capacity-button"
        hold(page, 650)
        page.click("#glossary-sheet-close")
        assert page.is_hidden("#glossary-sheet")
        assert active_id(page) == "glossary-capacity-button"
        hold(page, 650)
        page.mouse.click(180, 100)
        assert page.is_hidden("#glossary-sheet")
        browser.close()


def test_keyboard_path_and_tab_stays_inside_the_sheet(base):
    with sync_playwright() as p:
        browser, _ctx, page = open_game(p, base)
        page.focus("#glossary-integration-button")
        page.keyboard.press("Enter")                       # pins the popover as ever
        assert page.is_visible("#glossary-sheet-open")
        page.focus("#glossary-sheet-open")
        page.keyboard.press("Enter")
        assert page.is_visible("#glossary-sheet")
        assert page.inner_text("#glossary-sheet-title") == "Integration"
        assert active_id(page) == "glossary-sheet"
        order = []
        for _ in range(3):
            page.keyboard.press("Tab")
            order.append(active_id(page))
        assert order == ["glossary-sheet-close", "glossary-sheet-more", "glossary-sheet-close"]
        page.keyboard.press("Escape")
        assert active_id(page) == "glossary-integration-button"
        # the context-menu key on a focused term (Menu / Shift+F10) opens it too; a term with no Real Story link hides that button
        page.focus("#glossary-strain-button")
        page.evaluate("document.activeElement.dispatchEvent(new MouseEvent('contextmenu', {bubbles: true, cancelable: true}))")
        assert page.is_visible("#glossary-sheet")
        assert page.inner_text("#glossary-sheet-title") == "Strain"
        assert page.is_hidden("#glossary-sheet-more")
        browser.close()


def test_real_story_link_opens_the_real_story_and_closes_the_sheet(base):
    with sync_playwright() as p:
        browser, _ctx, page = open_game(p, base)
        assert page.evaluate("document.getElementById('info-page-panel').hidden")
        hold(page, 650)
        page.click("#glossary-sheet-more")
        page.wait_for_timeout(300)
        assert page.is_hidden("#glossary-sheet")
        assert not page.evaluate("document.getElementById('info-page-panel').hidden")
        browser.close()


def test_touch_long_press_opens_the_sheet_without_pinning_the_popover(base):
    with sync_playwright() as p:
        browser, ctx, page = open_game(p, base, touch=True)
        box = page.locator(CHIP).bounding_box()
        point = {"x": box["x"] + box["width"] / 2, "y": box["y"] + box["height"] / 2}
        cdp = ctx.new_cdp_session(page)

        def touch(ms):
            cdp.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": [point]})
            page.wait_for_timeout(ms)
            cdp.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})
            page.wait_for_timeout(300)

        touch(80)
        assert page.get_attribute(CHIP, "aria-expanded") == "true" and page.is_hidden("#glossary-sheet")
        touch(80)
        assert page.get_attribute(CHIP, "aria-expanded") == "false"
        touch(900)
        assert page.is_visible("#glossary-sheet")
        assert page.get_attribute(CHIP, "aria-expanded") == "false"
        assert active_id(page) == "glossary-sheet"
        browser.close()


def test_nothing_happens_on_a_wide_screen(base):
    with sync_playwright() as p:
        browser, _ctx, page = open_game(p, base, width=1440, height=900)
        assert page.is_hidden("#glossary-sheet-open")
        hold(page, 650)
        assert page.is_hidden("#glossary-sheet")
        browser.close()
