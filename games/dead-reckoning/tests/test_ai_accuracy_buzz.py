"""R4-DEMO-4: a plot that ends within a nautical mile of where the ship really ended up gets a line on the result card and one short buzz
where the browser has one. The buzz follows Reduce motion and the Effects switch. Engine part: the reveal carries the plot's error in nm.
Page part (Playwright; skipped when it or Pyodide's CDN is unavailable): a stubbed navigator.vibrate is called once on a reveal that is within
a mile, never with Effects off or Reduce motion on, and the line still shows. Nothing is ever sent to the live backend."""

import contextlib
import functools
import http.server
import socket
import threading
import urllib.request
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]


def test_the_reveal_carries_the_plots_error_in_nautical_miles(g):
    g.call("add_leg")
    v = g.call("sail")
    assert v["phase"] == "reveal"
    err = v["reveal"]["forecast_error_nm"]
    assert err is not None and 0 <= err <= 1.0           # the first chart is calm: the honest plot lands where the ship does
    assert "Your plot put you" in " ".join(v["reveal"]["lines"])


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
STUB = "window.__buzz = 0; navigator.vibrate = function () { window.__buzz += 1; return true; };"


def _sail_once(browser, base, storage):
    ctx = browser.new_context(viewport={"width": 360, "height": 740}, service_workers="block")
    ctx.route("**/*fastapicloud*/**", lambda route: route.abort())
    ctx.add_init_script(STUB)
    page = ctx.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(base + "index.html#play")
    page.evaluate("localStorage.clear()")
    for key, value in storage.items():
        page.evaluate("([k, v]) => localStorage.setItem(k, v)", [key, value])
    page.reload()
    page.wait_for_function(READY, timeout=90000)
    page.click("#add-leg-button")
    page.click("#sail-button")
    page.wait_for_function("!document.querySelector('#playback').hidden || !document.querySelector('#result-card').hidden", timeout=30000)
    if page.is_visible("#skip-button"):
        page.click("#skip-button")
    page.wait_for_selector("#result-card:not([hidden])", timeout=30000)
    return page, errors


def test_the_buzz_fires_once_and_follows_effects_and_reduced_motion(base):
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page, errors = _sail_once(browser, base, {})
        assert page.is_visible("#dr-accuracy-indicator") and "within a mile" in page.inner_text("#dr-accuracy-indicator")
        assert page.evaluate("window.__buzz") == 1
        assert errors == []

        page, errors = _sail_once(browser, base, {"dead-reckoning-effects": "false"})
        assert page.is_visible("#dr-accuracy-indicator")                      # the words stay; only the buzz is an effect
        assert page.evaluate("window.__buzz") == 0

        page, errors = _sail_once(browser, base, {"dead-reckoning-reduced-motion": "true"})
        assert page.is_visible("#dr-accuracy-indicator")
        assert page.evaluate("window.__buzz") == 0
        browser.close()
