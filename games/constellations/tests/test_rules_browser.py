"""Browser test for the 'Rules in plain words' content rendering."""

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
GAME = "constellations"


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


READY = ("(() => { const s = document.querySelector('#engine-status');"
         " if (s) return s.textContent === '' || s.hidden;"
         " return !!window.pyodide && !!window.pyodide.globals.get('get_state'); })()")


def open_game(p, base, width=1280, height=800):
    browser = p.chromium.launch()
    ctx = browser.new_context(viewport={"width": width, "height": height}, service_workers="block")
    ctx.route("**/*fastapicloud*/**", lambda route: route.abort())
    page = ctx.new_page()
    page.goto(base + "index.html#play")
    page.wait_for_function(READY, timeout=90000)
    return browser, page


def test_rules_in_plain_words_appear_in_about_panel(base):
    with sync_playwright() as p:
        browser, page = open_game(p, base)
        page.click("#info-page-toggle-button")
        page.wait_for_selector("#info-page-panel:not([hidden])", timeout=5000)
        assert page.is_visible("#rules-heading")
        rules_list = page.locator("#plain-rules-list li")
        assert rules_list.count() >= 3
        first_rule_text = rules_list.first.inner_text().lower()
        assert "star" in first_rule_text or "line" in first_rule_text or "number" in first_rule_text
        browser.close()
