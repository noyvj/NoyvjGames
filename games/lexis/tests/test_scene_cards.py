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


def open_game(p, base, width=360, height=740):
    browser = p.chromium.launch()
    ctx = browser.new_context(viewport={"width": width, "height": height}, service_workers="block")
    ctx.route("**/*fastapicloud*/**", lambda route: route.abort())
    page = ctx.new_page()
    page.goto(base + "index.html#play")
    page.wait_for_function(READY, timeout=90000)
    return browser, page


def test_scene_card_toggle_shows_cards(base):
    """Test that clicking the 'Play scenes' button shows the card container and hides the list."""
    with sync_playwright() as p:
        browser, page = open_game(p, base)

        # Initially, scene list should be visible (or at least not hidden by card container)
        # We need to trigger a scene first to have content
        page.click("#next-scene-button")
        page.wait_for_timeout(1000)  # Wait for engine to process

        # The toggle button should appear if there are scenes
        toggle_btn = page.query_selector("#scene-card-toggle-button")
        assert toggle_btn is not None, "Scene card toggle button should exist"

        # Initially card container is hidden
        card_container = page.query_selector("#scene-card-container")
        assert card_container.get_attribute("hidden") is not None, "Card container should be hidden initially"

        # Click the toggle button
        toggle_btn.click()

        # Card container should now be visible
        assert card_container.get_attribute("hidden") is None, "Card container should be visible after toggle"

        browser.close()


def test_scene_card_rendered_with_content(base):
    """Test that scene cards are rendered with correct content."""
    with sync_playwright() as p:
        browser, page = open_game(p, base)

        # Trigger a scene
        page.click("#next-scene-button")
        page.wait_for_timeout(1000)

        # Toggle to card view
        toggle_btn = page.query_selector("#scene-card-toggle-button")
        if toggle_btn:
            toggle_btn.click()
            page.wait_for_timeout(500)

            card_container = page.query_selector("#scene-card-container")
            assert card_container is not None

            # Check for scene cards
            cards = card_container.query_selector_all(".scene-card")
            assert len(cards) > 0, "At least one scene card should be rendered"

            # Check content of the first card
            first_card = cards[0]
            # Should contain transmission number
            strong_text = first_card.query_selector("strong").text_content()
            assert "Transmission 1" in strong_text, f"First card should show 'Transmission 1', got: {strong_text}"

        browser.close()
