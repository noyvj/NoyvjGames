"""R4-PBMO-4: on a phone the three customers are a row of cards across the full width and the whole stall (stats,
customers, board, crates, tool dock) fits one portrait screen. The desktop queue keeps its centred 26rem width.
Browser part is skipped when Playwright or Pyodide's CDN is unavailable."""

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
STYLE = (GAME_DIR / "style.css").read_text(encoding="utf-8")


def _media_600_blocks():
    out = []
    for m in re.finditer(r"@media \(max-width: 600px\) \{", STYLE):
        depth, i = 1, m.end()
        while depth:
            depth += {"{": 1, "}": -1}.get(STYLE[i], 0)
            i += 1
        out.append(STYLE[m.end():i - 1])
    return "\n".join(out)


def test_the_full_width_queue_rule_is_phone_only():
    base = re.search(r"^\.queue \{[^}]*\}", STYLE, re.M).group(0)
    assert "max-width: 26rem" in base and "width: 100%" not in base
    phone = _media_600_blocks()
    assert re.search(r"\.queue \{[^}]*width: 100%", phone)
    assert re.search(r"\.board \{[^}]*width: 100%", phone, re.S)


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
    yield "http://localhost:%d/games/pocket-bazaar/" % port
    server.shutdown()


READY = "document.querySelector('#engine-status') && document.querySelector('#engine-status').textContent === ''"


def _open_day(p, base, width, height):
    browser = p.chromium.launch()
    ctx = browser.new_context(viewport={"width": width, "height": height}, service_workers="block")
    ctx.route("**/*fastapicloud*/**", lambda route: route.abort())
    page = ctx.new_page()
    page.goto(base + "index.html#play")
    page.wait_for_function(READY, timeout=90000)
    page.click("#start-day-button")
    page.wait_for_selector("#queue .customer", state="visible")
    return browser, page


def test_the_phone_stall_fits_one_screen_without_sideways_scroll(base):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser, page = _open_day(p, base, 360, 740)
        info = page.evaluate("""() => {
          const r = s => document.querySelector(s).getBoundingClientRect();
          const q = r('#queue'), b = r('#board'), d = r('#mobile-dock');
          return {scrollW: document.documentElement.scrollWidth, qLeft: q.left, qRight: q.right, bBottom: b.bottom, dTop: d.top,
                  dockShown: getComputedStyle(document.querySelector('#mobile-dock')).display !== 'none'};
        }""")
        browser.close()
    assert info["scrollW"] <= 360
    assert info["qLeft"] >= 0 and info["qRight"] <= 360
    assert info["dockShown"] and info["bBottom"] <= info["dTop"] + 1
