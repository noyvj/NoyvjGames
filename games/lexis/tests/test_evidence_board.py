from pathlib import Path

import pytest

pytest.importorskip("playwright.sync_api")
from playwright.sync_api import sync_playwright  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]
GAME = "lexis"


@pytest.fixture(scope="module")
def base():
    import contextlib
    import functools
    import http.server
    import socket
    import threading

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


READY = "document.querySelector('#engine-status') && document.querySelector('#engine-status').textContent === ''"


def open_game(p, base, width=1280, height=800):
    browser = p.chromium.launch()
    ctx = browser.new_context(viewport={"width": width, "height": height}, service_workers="block")
    ctx.route("**/*fastapicloud*/**", lambda route: route.abort())
    page = ctx.new_page()
    page.goto(base + "index.html#play")
    page.wait_for_function(READY, timeout=90000)
    return browser, page


def test_evidence_board_toggle_opens_panel(base):
    with sync_playwright() as p:
        browser, page = open_game(p, base)
        page.click("#evidence-toggle-button")
        assert page.is_visible("#evidence-board-panel")
        browser.close()


def test_python_state_includes_evidence_pins():
    import game

    game.state.evidence_pins = {"pin0": "test_name"}
    state_data = game.get_state()
    assert "evidence_pins" in state_data
    assert state_data["evidence_pins"]["pin0"] == "test_name"


def test_python_load_state_merges_evidence_pins():
    import game

    game.state.evidence_pins = {"pin0": "old_name"}

    load_data = {
        "evidence_pins": {"pin1": "new_name"},
        "station": [0, "shut"],
        "tray": [],
        "stock": []
    }
    game.load_state(load_data)

    assert game.state.evidence_pins["pin0"] == "old_name"
    assert game.state.evidence_pins["pin1"] == "new_name"
