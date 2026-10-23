"""R4-RSMO-1: on a phone the instruction palette is a bottom keypad of large buttons with the list scrolling above it, and a
step's letter is a grip (hold, drag up or down, release) that reorders the list. Static wiring plus a real-browser check
(skipped when Playwright or Pyodide's CDN is unavailable)."""

import contextlib
import functools
import http.server
import re
import socket
import threading
import urllib.request
from pathlib import Path

import pytest
from .pagefiles import app_text

GAME_DIR = Path(__file__).resolve().parent.parent
ROOT = GAME_DIR.parents[1]
APP = app_text()
HTML = (GAME_DIR / "index.html").read_text(encoding="utf-8")
CSS = (GAME_DIR / "style.css").read_text(encoding="utf-8")


def _phone_css():
    out = []
    for m in re.finditer(r"@media \(max-width: 600px\) \{", CSS):
        depth, i = 1, m.end()
        while depth:
            depth += {"{": 1, "}": -1}.get(CSS[i], 0)
            i += 1
        out.append(CSS[m.end():i - 1])
    return "\n".join(out)


def test_the_keypad_is_the_real_palette_and_only_a_phone_fixes_it_to_the_bottom():
    assert 'id="palette"' in HTML and 'id="keypad"' not in HTML and "keypad" not in APP
    assert not re.search(r"^\.palette[^{]*\{[^}]*position: fixed", CSS, re.M)
    phone = _phone_css()
    assert re.search(r'html:not\(\[data-layout="pc"\]\) #palette \{[^}]*position: fixed[^}]*bottom: calc\(50px', phone)
    assert "min-height: 2.9rem" in phone       # 46px, over the 44px target


def test_the_reorder_grip_uses_known_engine_actions_and_no_timers():
    block = APP.split("function _initReorderHandles")[1].split("function wire()")[0]
    assert '$("program")' in block and 'id="program"' in HTML
    assert 'action: "move"' in block and "e.timeStamp - drag.t0" in block
    assert "setTimeout" not in block and "setInterval" not in block
    assert "_initReorderHandles();" in APP.split("function wire()")[1]
    assert "dataset.a = node.a" in APP and 'el("span", "node-glyph"' in APP


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
    yield "http://localhost:%d/games/robot-script/" % port
    server.shutdown()


READY = "document.querySelector('#engine-status') && document.querySelector('#engine-status').textContent === ''"


def _open(p, base, width, height, page_name="index.html"):
    browser = p.chromium.launch()
    ctx = browser.new_context(viewport={"width": width, "height": height}, service_workers="block")
    ctx.route("**/*fastapicloud*/**", lambda route: route.abort())
    page = ctx.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(base + page_name + "#play")
    page.wait_for_function(READY, timeout=90000)
    return browser, page, errors


def _labels(page):
    return page.evaluate("[...document.querySelectorAll('#program .node-label')].map(n => n.textContent)")


def test_the_phone_keypad_adds_steps_and_a_held_grip_reorders_them(base):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser, page, errors = _open(p, base, 360, 740)
        page.click("#rooms-toggle-button")
        page.click("[data-testid='robot-script-room-face-the-pad']")      # a room whose toolbox is F L R
        page.wait_for_selector("[data-testid='robot-script-add-L']", state="attached")
        pal = page.evaluate("""() => {
          const r = document.querySelector('#palette').getBoundingClientRect();
          const b = [...document.querySelectorAll('#palette button')].map(x => x.getBoundingClientRect());
          return {position: getComputedStyle(document.querySelector('#palette')).position, top: r.top, bottom: r.bottom,
                  minH: Math.min(...b.map(x => x.height)), minW: Math.min(...b.map(x => x.width)), n: b.length,
                  scrollW: document.documentElement.scrollWidth, vh: innerHeight};
        }""")
        assert pal["position"] == "fixed" and pal["n"] >= 3
        assert pal["minH"] >= 44 and pal["minW"] >= 44 and pal["bottom"] <= pal["vh"] - 49
        assert pal["scrollW"] <= 360
        for key in ("F", "L", "R"):
            page.click("[data-testid='robot-script-add-%s']" % key)
        first = _labels(page)
        assert len(first) == 3
        page.locator("#program").evaluate("e => e.scrollIntoView({ block: 'center' })")      # clear of the keypad and the ad bar
        # a quick press on the grip does nothing
        g = page.locator("#program .node-glyph").first.bounding_box()
        page.mouse.move(g["x"] + g["width"] / 2, g["y"] + g["height"] / 2)
        page.mouse.down()
        page.mouse.move(g["x"] + g["width"] / 2, g["y"] + 100)
        page.mouse.up()
        assert _labels(page) == first
        # hold, drag down two places, release
        g = page.locator("#program .node-glyph").first.bounding_box()
        x, y = g["x"] + g["width"] / 2, g["y"] + g["height"] / 2
        page.mouse.move(x, y)
        page.mouse.down()
        page.wait_for_timeout(700)
        page.mouse.move(x, y + 90, steps=4)
        page.mouse.up()
        assert _labels(page) == [first[1], first[2], first[0]]
        page.click("#undo-button")        # a reorder is an ordinary edit
        page.click("#undo-button")
        assert _labels(page) == first
        browser.close()
    assert errors == []


@pytest.mark.parametrize("page_name", ["index.html", "pc.html"])
def test_the_palette_is_not_fixed_on_a_wide_window(base, page_name):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser, page, errors = _open(p, base, 1440, 900, page_name)
        assert page.evaluate("getComputedStyle(document.querySelector('#palette')).position") != "fixed"
        browser.close()
    assert errors == []
