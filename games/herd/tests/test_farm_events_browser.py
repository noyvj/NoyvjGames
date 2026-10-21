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
GAME = "herd"


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


def test_farm_event_card_exists_and_is_hidden_by_default(base):
    with sync_playwright() as p:
        browser, page = open_game(p, base)
        card = page.query_selector("#farm-event-card")
        assert card is not None
        assert card.is_hidden()
        btn_a = page.query_selector("#event-choice-a")
        btn_b = page.query_selector("#event-choice-b")
        assert btn_a is not None
        assert btn_b is not None
        browser.close()


def test_farm_event_card_opens_and_both_buttons_work(base):
    with sync_playwright() as p:
        browser, page = open_game(p, base)
        page.evaluate("""() => {
            const py = window.pyodide;
            py.runPython(`
import herd_runstate as rs
from herd_rules import FARM_EVENTS
from herd_renderer import render
rs.farm.herd_size = 4
rs.farm.event_active = True
rs.farm.event_choice_made = False
rs.farm.event_data = FARM_EVENTS[0]
render()
`);
        }""")
        assert page.is_visible("#farm-event-card")
        assert "neighbour" in page.inner_text("#event-text")
        assert page.is_enabled("#event-choice-a")
        before = page.inner_text("#herd-display")
        page.click("#event-choice-b")  # Refuse: the card closes and nothing else changes
        assert page.is_hidden("#farm-event-card")
        assert page.inner_text("#herd-display") == before
        browser.close()
