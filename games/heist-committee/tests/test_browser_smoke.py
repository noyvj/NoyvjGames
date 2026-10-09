"""A real-browser pass over every phase at desktop and phone width (Playwright, skipped when it or the network for
Pyodide is unavailable). Never touches the live backend: the page is served from a throwaway local server and the
save widget is only looked at, never used."""

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
def url():
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
    yield "http://localhost:%d/games/heist-committee/index.html#play" % port
    server.shutdown()


@pytest.fixture(scope="module")
def browser():
    with sync_playwright() as p:
        b = p.chromium.launch()
        yield b
        b.close()


def overflow(page):
    return page.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")


def drive(page, width):
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(page.url_under_test)
    page.wait_for_function("window.HC && window.HC.view", timeout=90000)
    page.evaluate("localStorage.clear()")
    page.reload()
    page.wait_for_function("window.HC && window.HC.view", timeout=90000)
    assert overflow(page) <= 1, "board overflows horizontally"
    page.click("[data-testid=heist-take-pigeon_museum]")
    assert overflow(page) <= 1, "case file overflows horizontally"
    page.click("[data-testid=heist-to-recruit]")
    assert overflow(page) <= 1, "recruit overflows horizontally"
    ids = page.eval_on_selector_all("[data-testid^=heist-hire-]", "els=>els.map(e=>e.dataset.testid.replace('heist-hire-',''))")
    for i in ids[:5]:
        page.click("[data-testid=heist-hire-%s]" % i)
    page.click("[data-testid=heist-confirm-crew]")
    page.wait_for_selector("#timeline .cell")
    assert overflow(page) <= 1, "plan overflows horizontally"
    placements = (("sweet_talk", 0, 0), ("lockpick", 1, 1), ("lookout", 2, 1), ("lookout", 2, 2), ("carry", 4, 3), ("drive", 3, 4))
    for action, lane, beat in placements:
        page.click("[data-testid=heist-tray-%s]" % action)
        page.click("[data-testid=heist-cell-%d-%d]" % (lane, beat))
        page.keyboard.press("Escape")
    assert "Lockpick" in page.get_attribute("[data-testid=heist-cell-1-1]", "aria-label")
    page.click("[data-testid=heist-start]")
    page.click("[data-testid=confirm-dialog-confirm]")
    page.click("[data-testid=heist-next-beat]")
    assert overflow(page) <= 1, "playback overflows horizontally"
    page.click("[data-testid=heist-skip]")
    page.click("[data-testid=heist-finish]")
    page.wait_for_selector("[data-testid=heist-banner]")
    assert overflow(page) <= 1, "payout overflows horizontally"
    assert page.inner_text("[data-testid=heist-writeup]").strip()
    assert not errors, errors


@pytest.mark.parametrize("width,height", [(1440, 900), (360, 740)])
def test_every_phase_fits_and_runs(browser, url, width, height):
    page = browser.new_page(viewport={"width": width, "height": height})
    page.url_under_test = url
    try:
        drive(page, width)
    finally:
        page.close()


def test_touch_targets_on_a_phone_are_big_enough(browser, url):
    page = browser.new_page(viewport={"width": 360, "height": 740})
    try:
        page.goto(url)
        page.wait_for_function("window.HC && window.HC.view", timeout=90000)
        page.evaluate("localStorage.clear()")
        page.reload()
        page.wait_for_function("window.HC && window.HC.view", timeout=90000)
        page.click("[data-testid=heist-take-pigeon_museum]")
        page.click("[data-testid=heist-to-recruit]")
        ids = page.eval_on_selector_all("[data-testid^=heist-hire-]", "els=>els.map(e=>e.dataset.testid.replace('heist-hire-',''))")
        for i in ids[:5]:
            page.click("[data-testid=heist-hire-%s]" % i)
        page.click("[data-testid=heist-confirm-crew]")
        page.wait_for_selector("#timeline .cell")
        small = page.evaluate("""() => Array.from(document.querySelectorAll('#game button, #tray-panel button'))
            .filter(b => b.offsetParent !== null)
            .map(b => {
              const r = b.getBoundingClientRect();
              return [b.dataset.testid || b.id || b.textContent.trim().slice(0, 20), Math.round(r.width), Math.round(r.height)];
            })
            .filter(x => x[2] < 40 || x[1] < 40)""")
        assert not small, small
    finally:
        page.close()


def test_the_opening_screen_is_skipped_by_the_play_hash_and_shows_without_it(browser, url):
    page = browser.new_page(viewport={"width": 1440, "height": 900})
    try:
        page.goto(url.replace("#play", ""))
        page.get_by_role("button", name="New Game").wait_for(state="visible", timeout=30000)
    finally:
        page.close()
