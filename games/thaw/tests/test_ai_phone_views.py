"""R4-THMO-2, -4, -5, -7, -8, -10 (Thaw phone views): wiring checks plus a real-browser pass at phone width.

The static checks read the page and script files and compare ids, settings and CSS gates (no browser). The live ones drive
Thaw in headless Chromium with real touch input (skipped when Playwright or Pyodide's CDN is unavailable). Nothing is sent to the live backend."""

import contextlib
import functools
import http.server
import re
import socket
import threading
import urllib.request
from pathlib import Path

import pytest

BASE_DIR = Path(__file__).resolve().parent.parent
ROOT = BASE_DIR.parents[1]
PAGES = ("index.html", "pc.html")
SCRIPTS = ("focus-mode.js", "haptic-feedback.js", "info-page-swipe.js", "landscape-grid.js", "mobile-invest.js", "archive-swipe.js")


def _read(name):
    return (BASE_DIR / name).read_text(encoding="utf-8")


def _page_ids(page):
    return set(re.findall(r'\bid="([^"]+)"', _read(page)))


# --------------------------------------------------------------------------------------------- static wiring
@pytest.mark.parametrize("page", PAGES)
def test_every_new_script_is_loaded_on_both_pages_after_the_dom(page):
    html = _read(page)
    body_end = html.index("</body>")
    for name in SCRIPTS:
        tag = '<script src="%s"></script>' % name
        assert html.count(tag) == 1, name
        assert html.index(tag) > html.index('id="game"') and html.index(tag) < body_end, name


@pytest.mark.parametrize("name", SCRIPTS)
def test_every_id_a_new_script_looks_up_exists_in_both_pages(name):
    js = _read(name)
    wanted = set(re.findall(r'getElementById\("([^"]+)"\)', js))
    wanted |= set(re.findall(r"querySelector(?:All)?\(\"#([A-Za-z0-9_-]+)", js))
    for page in PAGES:
        missing = {i for i in wanted if i not in _page_ids(page)}
        assert not missing, (name, page, missing)


def test_the_new_settings_have_a_control_and_a_flag_that_resets():
    settings = _read("settings.js")
    pairs = {
        "thaw-no-haptics": "no-haptics-checkbox", "thaw-info-list": "info-list-checkbox",
        "thaw-hide-board": "hide-board-checkbox", "thaw-no-pull-archive": "no-pull-archive-checkbox",
    }
    for key, box in pairs.items():
        assert '"%s"' % key in settings and '"%s"' % box in settings, key
        for page in PAGES:
            assert 'id="%s"' % box in _read(page), (box, page)
            assert 'id="%s" checked' % box not in _read(page)
    # resetFlags walks the FLAGS table, so a flag in the table is reset by "Reset to default" with the others
    assert "function resetFlags" in settings and "FLAGS.forEach" in settings


def test_the_css_does_not_remove_the_reduced_motion_rules_for_the_crate():
    css = _read("style.css")
    assert ':root[data-reduced-motion="true"] .crate-visual.crate-waiting' in css
    assert ':root[data-reduced-motion="true"] .crate-visual.crate-opening' in css


def test_the_phone_rules_sit_inside_a_narrow_screen_or_short_landscape_query():
    css = _read("style.css")
    # a base rule may only hide these; the visible layout comes from a query
    for selector in ("#focus-mode-dots", "#mobile-invest-details", "#landscape-board", ".info-page-dots", ".archive-sheet-close"):
        base_rules = re.findall(r"(?m)^%s\s*\{([^}]*)\}" % re.escape(selector), css)
        assert base_rules, selector
        assert all("display: none" in rule for rule in base_rules), selector


# --------------------------------------------------------------------------------------------- live pass
pw = pytest.importorskip("playwright.sync_api")


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
    yield "http://localhost:%d/games/thaw/" % port
    server.shutdown()


READY = "!!window.pyodide && !!window.pyodide.globals.get('get_state') && document.querySelector('#output-invest-button') && document.querySelector('#output-invest-button').innerText.indexOf('Invest') === 0"
INIT_VIBRATE = "window.__buzz = []; navigator.vibrate = function (p) { window.__buzz.push(p); return true; };"


def _open(browser, base, errors, width=360, height=740, page_name="index.html", touch=True):
    ctx = browser.new_context(viewport={"width": width, "height": height}, has_touch=touch, is_mobile=touch, service_workers="block")
    ctx.route("**/*fastapicloud*/**", lambda route: route.abort())
    ctx.add_init_script(INIT_VIBRATE)
    page = ctx.new_page()
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(base + page_name + "#play")
    page.evaluate("localStorage.clear()")
    page.reload()
    page.wait_for_function(READY, timeout=90000)
    return ctx, page


def _drag(ctx, page, x0, y0, x1, y1, steps=8):
    cdp = ctx.new_cdp_session(page)
    cdp.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": [{"x": x0, "y": y0}]})
    for step in range(1, steps + 1):
        cdp.send("Input.dispatchTouchEvent", {"type": "touchMove", "touchPoints": [{"x": x0 + (x1 - x0) * step / steps, "y": y0 + (y1 - y0) * step / steps}]})
    cdp.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})
    page.wait_for_timeout(200)


def _centre(page, selector):
    page.locator(selector).scroll_into_view_if_needed()
    page.wait_for_timeout(100)
    box = page.locator(selector).bounding_box()
    return box["x"] + box["width"] / 2.0, box["y"] + box["height"] / 2.0


def _set_funds_and_render(page, funds):
    page.evaluate("(f) => { window.pyodide.runPython('region.funds = %s\\nrender()' % f); }", funds)


def test_focus_mode_is_off_by_default_then_focuses_and_remembers(base):
    errors = []
    with pw.sync_playwright() as p:
        browser = p.chromium.launch()
        ctx, page = _open(browser, base, errors)
        assert page.is_visible("#focus-mode-dots")
        assert page.is_visible("#b-region-card") and page.is_visible("#c-region-card") and page.is_visible("#status")
        assert page.get_attribute("#focus-dot-all", "aria-pressed") == "true"
        page.click("#focus-dot-b")
        assert page.is_visible("#b-region-card") and not page.is_visible("#c-region-card") and not page.is_visible("#status")
        page.click("#focus-dot-a")
        assert page.is_visible("#status") and not page.is_visible("#region-comparison")
        page.reload()
        page.wait_for_function(READY, timeout=90000)
        assert page.get_attribute("#game", "data-focus") == "a"
        assert page.get_attribute("#focus-dot-a", "aria-pressed") == "true"
        page.click("#focus-dot-all")
        assert page.get_attribute("#game", "data-focus") is None
        assert page.is_visible("#b-region-card") and page.is_visible("#c-region-card")
        assert page.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth") <= 30
        # 44px targets for the four buttons
        for name in ("all", "a", "b", "c"):
            box = page.locator("#focus-dot-" + name).bounding_box()
            assert box["height"] >= 44 and box["width"] >= 44
        browser.close()
    assert errors == []


def test_focus_buttons_are_phone_only(base):
    errors = []
    with pw.sync_playwright() as p:
        browser = p.chromium.launch()
        for page_name in PAGES:
            ctx, page = _open(browser, base, errors, 1440, 900, page_name, touch=False)
            assert not page.is_visible("#focus-mode-dots"), page_name
        browser.close()
    assert errors == []


def _advance_to(page, start_rise):
    """Puts Region A at `start_rise` degrees and redraws; the next Advance Round click is then a real player action."""
    page.evaluate("(t) => { window.pyodide.runPython('region.temperature = ' + t + '\\nrender()'); }", start_rise)
    page.wait_for_timeout(100)
    page.evaluate("window.__buzz = []")


def test_haptics_buzz_once_per_upward_milestone_crossing_and_can_be_switched_off(base):
    errors = []
    with pw.sync_playwright() as p:
        browser = p.chromium.launch()
        ctx, page = _open(browser, base, errors)
        # instant digits so the readout moves in one step
        page.evaluate("document.documentElement.setAttribute('data-instant-digits', 'true')")
        _advance_to(page, 8.4)
        page.click("#advance-round-button")           # 8.4 -> about 9.4: no milestone
        page.wait_for_timeout(300)
        assert page.evaluate("window.__buzz") == []
        _advance_to(page, 9.6)
        page.click("#advance-round-button")           # crosses +10
        page.wait_for_timeout(300)
        buzz = page.evaluate("window.__buzz")
        assert len(buzz) == 1 and buzz[0] == [120]
        assert page.evaluate("document.querySelector('#temperature-display').classList.contains('threshold-crossed-pulse')")
        page.wait_for_timeout(1000)
        _advance_to(page, 14.6)
        page.click("#advance-round-button")           # crosses +15: a longer pattern
        page.wait_for_timeout(300)
        longer = page.evaluate("window.__buzz")
        assert len(longer) == 1 and len(longer[0]) > 1 and sum(longer[0]) > 120
        # the off switch (Settings flag) stops it
        page.evaluate("document.documentElement.setAttribute('data-no-haptics', 'true')")
        _advance_to(page, 19.6)
        page.click("#advance-round-button")
        page.wait_for_timeout(300)
        assert page.evaluate("window.__buzz") == []
        # reduced motion stops it, and a big jump (a save loading) never buzzes
        page.evaluate("document.documentElement.setAttribute('data-no-haptics', 'false')")
        page.evaluate("document.documentElement.setAttribute('data-reduced-motion', 'true')")
        _advance_to(page, 24.6)
        page.click("#advance-round-button")
        page.wait_for_timeout(300)
        assert page.evaluate("window.__buzz") == []
        assert not page.evaluate("document.querySelector('#temperature-display').classList.contains('threshold-crossed-pulse')")
        page.evaluate("document.documentElement.setAttribute('data-reduced-motion', 'false')")
        _advance_to(page, 2.0)
        page.evaluate("window.pyodide.runPython('region.temperature = 12.0\\nrender()')")
        page.wait_for_timeout(200)
        assert page.evaluate("window.__buzz") == []
        browser.close()
    assert errors == []


def _active_dot(page):
    return page.evaluate("Array.from(document.querySelectorAll('#info-page-dots .info-page-dot')).findIndex(d => d.classList.contains('active'))")


def test_real_story_cards_swipe_with_dots_and_can_be_a_list(base):
    errors = []
    with pw.sync_playwright() as p:
        browser = p.chromium.launch()
        ctx, page = _open(browser, base, errors)
        assert not page.is_visible("#info-page-dots")                         # panel closed: no dots
        page.click("#info-page-toggle-button")
        page.wait_for_selector("#info-page-framing:visible")
        assert page.is_visible("#info-page-dots")
        assert page.locator("#info-page-dots .info-page-dot").count() == 3 and _active_dot(page) == 0
        assert page.evaluate("getComputedStyle(document.querySelector('#info-page-panel')).display") == "flex"
        assert page.evaluate("document.querySelector('#info-page-panel').scrollWidth > document.querySelector('#info-page-panel').clientWidth")
        assert page.get_attribute("#info-page-panel", "tabindex") == "0"
        # a real finger swipe moves to the second card and the dot follows
        x, y = _centre(page, "#info-page-framing")
        _drag(ctx, page, x + 100, y, x - 100, y)
        page.wait_for_timeout(500)
        assert _active_dot(page) >= 1                  # a flick may carry on to the third card; it never stays on the first
        assert page.evaluate("document.querySelector('#info-page-panel').scrollLeft") > 100
        # the Settings switch turns the cards back into the plain list
        page.evaluate("document.documentElement.setAttribute('data-info-list', 'true')")
        page.wait_for_timeout(100)
        assert page.evaluate("getComputedStyle(document.querySelector('#info-page-panel')).display") == "block"
        assert not page.is_visible("#info-page-dots")
        assert page.get_attribute("#info-page-panel", "tabindex") is None
        browser.close()
    assert errors == []


def test_real_story_stays_a_plain_list_on_a_wide_screen(base):
    errors = []
    with pw.sync_playwright() as p:
        browser = p.chromium.launch()
        for page_name in PAGES:
            ctx, page = _open(browser, base, errors, 1440, 900, page_name, touch=False)
            page.evaluate("document.querySelector('#info-page-toggle-button').click()")
            page.wait_for_timeout(200)
            assert page.evaluate("getComputedStyle(document.querySelector('#info-page-panel')).display") != "flex", page_name
            assert not page.is_visible("#info-page-dots"), page_name
        browser.close()
    assert errors == []
