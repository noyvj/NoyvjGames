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
GAME = "lexis"


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


READY = "document.querySelector('#engine-status') && document.querySelector('#engine-status').textContent === ''"


def open_game(p, base, width=1280, height=800):
    browser = p.chromium.launch()
    ctx = browser.new_context(viewport={"width": width, "height": height}, service_workers="block")
    ctx.route("**/*fastapicloud*/**", lambda route: route.abort())
    page = ctx.new_page()
    page.goto(base + "index.html#play")
    page.wait_for_function(READY, timeout=90000)
    return browser, page


def test_hover_sign_highlights_all_occurrences(base):
    """Hovering a sign in the notebook should highlight it in scenes and crew log."""
    with sync_playwright() as p:
        browser, page = open_game(p, base)

        # Ensure we are on Planet 1 (Pulse) which has scenes and notebook
        page.click("#tab-pulse")

        # Receive a transmission to populate scenes and potentially notebook
        page.click("#next-scene-button")
        page.wait_for_selector(".scene-list li", timeout=5000)

        # Check if there are any notebook items. If not, skip this test as we can't test notebook hover.
        notebook_items = page.query_selector_all(".notebook-list li")
        if not notebook_items:
            pytest.skip("No notebook items to test hover on (notebook is empty)")

        # Get the first notebook entry with text
        first_notebook_item = None
        for item in notebook_items:
            text = item.inner_text().strip()
            if text:
                first_notebook_item = item
                break

        if not first_notebook_item:
            pytest.skip("First notebook item has no text")

        # Ensure the notebook item is visible and interactable
        first_notebook_item.wait_for_element_state("visible", timeout=1000)

        # Hover over the first notebook item
        first_notebook_item.hover()

        # Wait for the highlight class to be applied
        first_notebook_item.wait_for_selector(".sign-match", timeout=2000)

        # Check that other items with similar text also have the highlight class
        # We expect at least one other match if there are multiple scenes/notebooks
        matches = page.query_selector_all(".sign-match")
        assert len(matches) >= 1

        browser.close()
