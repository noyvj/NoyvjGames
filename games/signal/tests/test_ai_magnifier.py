"""R4-SIMO-1: hold a tile on a phone and a bubble above the finger names the tile. Page code cannot be run without a
browser, so these tests check the wiring the first version got wrong (handlers bound while the element was still null,
a reference to a checkbox that did not exist) and, when Playwright is installed, drive it with touch pointer events."""

import contextlib
import functools
import http.server
import re
import socket
import threading
from pathlib import Path

import pytest
from .pagefiles import app_text, engine_text

GAME_DIR = Path(__file__).resolve().parent.parent
APP = app_text()
SETTINGS = (GAME_DIR / "settings.js").read_text(encoding="utf-8")
STYLE = (GAME_DIR / "style.css").read_text(encoding="utf-8")
HTML = (GAME_DIR / "index.html").read_text(encoding="utf-8")


def test_handlers_are_bound_from_wire_and_the_bubble_is_built_on_demand():
    assert "wireMagnifier(boardEl);" in APP[APP.index("  function wire() {"):APP.index("  // ---- hold-to-aim magnifier")]
    show = APP[APP.index("function showMagnifier"):APP.index("function wireMagnifier")]
    assert 'el("div", "magnifier-bubble")' in show and "document.body.appendChild(magnifier)" in show
    # the first version only bound its handlers `if (magnifier)` before anything had created it
    assert "if (magnifier) {" not in APP


def test_only_a_held_touch_shows_it_and_everything_else_cancels_it():
    wire = APP[APP.index("function wireMagnifier"):APP.index("  function init() {")]
    assert 'ev.pointerType !== "touch"' in wire and "MAGNIFIER_HOLD_MS" in wire
    assert "pointercancel" in wire and "pointerup" in wire and "isPrimary" in wire
    rmenu = APP[APP.index("function showRMenu"):APP.index("function hideRMenu")]
    assert "hideMagnifier();" in rmenu                         # the long-press menu and the bubble never show together


def test_the_setting_has_a_control_a_read_a_reset_and_is_per_device():
    assert 'id="magnifier-checkbox"' in HTML
    assert 'signal-magnifier' in APP and 'MAGNIFIER_KEY = "signal-magnifier"' in SETTINGS
    assert 'getElementById("magnifier-checkbox")' in SETTINGS
    assert re.search(r'magBox\.addEventListener\("change"', SETTINGS)
    reset = SETTINGS[SETTINGS.index('on("display-reset-button"'):]
    assert 'set(MAGNIFIER_KEY, "on")' in reset and "magBox.checked = true" in reset
    assert "magnifier" not in engine_text()      # never in the save


def test_css_is_phone_only_and_every_class_js_adds_is_styled():
    block = STYLE[STYLE.index("/* R4-SIMO-1"):]
    assert block.count("@media (max-width: 600px)") == 1
    for cls in ("magnifier-bubble", "mag-coord", "mag-state", "visible"):
        assert "." + cls in block
    assert STYLE.count(".magnifier-bubble") == block.count(".magnifier-bubble")       # nothing outside the phone block
    assert "transition" not in block and "animation" not in block                     # no motion to switch off


# ---- live check with touch pointer events (skipped without Playwright) ----------------------------------------------
pytest.importorskip("playwright.sync_api")
from playwright.sync_api import sync_playwright  # noqa: E402

ROOT = GAME_DIR.parents[1]


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
    yield "http://localhost:%d/games/signal/" % port
    server.shutdown()


TOUCH = """(args) => {
  const cell = document.querySelector('#board .cell[data-r="' + args.r + '"][data-c="' + args.c + '"]');
  const b = cell.getBoundingClientRect();
  const x = b.left + b.width / 2, y = b.top + b.height / 2;
  const init = { bubbles: true, cancelable: true, pointerType: "touch", isPrimary: true, pointerId: 7, clientX: x, clientY: y };
  cell.dispatchEvent(new PointerEvent("pointerdown", init));
  return { x, y };
}"""


def _open(p, base, width):
    browser = p.chromium.launch()
    ctx = browser.new_context(viewport={"width": width, "height": 740}, service_workers="block")
    page = ctx.new_page()
    page.goto(base + "index.html#play")
    page.wait_for_selector("#board .cell")
    return browser, page


def test_hold_shows_the_bubble_above_the_finger_and_release_hides_it(base):
    with sync_playwright() as p:
        browser, page = _open(p, base, 360)
        pos = page.evaluate(TOUCH, {"r": 3, "c": 3})
        page.wait_for_selector(".magnifier-bubble.visible", timeout=2000)
        assert page.inner_text(".magnifier-bubble .mag-coord") == "D4"
        assert page.inner_text(".magnifier-bubble .mag-state")
        box = page.eval_on_selector(".magnifier-bubble", "e => { const r = e.getBoundingClientRect(); return {top: r.top, bottom: r.bottom, left: r.left, right: r.right}; }")
        assert box["bottom"] <= pos["y"] and box["left"] >= 0 and box["right"] <= 360
        page.evaluate("() => document.querySelector('#board').dispatchEvent(new PointerEvent('pointerup', {bubbles: true, pointerType: 'touch', isPrimary: true}))")
        assert page.query_selector(".magnifier-bubble.visible") is None
        browser.close()


def test_setting_off_and_mouse_and_wide_windows_never_show_it(base):
    with sync_playwright() as p:
        browser, page = _open(p, base, 360)
        page.evaluate("() => localStorage.setItem('signal-magnifier', 'off')")
        page.evaluate(TOUCH, {"r": 2, "c": 2})
        page.wait_for_timeout(400)
        assert page.query_selector(".magnifier-bubble.visible") is None
        page.evaluate("() => localStorage.removeItem('signal-magnifier')")
        page.mouse.move(100, 400)
        page.mouse.down()
        page.wait_for_timeout(400)
        assert page.query_selector(".magnifier-bubble.visible") is None
        page.mouse.up()
        browser.close()
        browser, page = _open(p, base, 1280)
        page.evaluate(TOUCH, {"r": 2, "c": 2})
        page.wait_for_timeout(400)
        assert page.query_selector(".magnifier-bubble") is None
        browser.close()
