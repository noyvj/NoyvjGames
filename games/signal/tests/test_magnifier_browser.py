"""Tests for the mobile magnifier bubble feature (R4-SIMO-1)."""

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
GAME = "signal"


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
    try:
        page.wait_for_function(READY, timeout=30000)
    except Exception:
        pytest.skip("Pyodide engine did not load in time (network or environment issue)")
    return browser, page


def test_magnifier_bubble_shows_on_touch(base):
    """Verify the magnifier bubble appears when touching a cell on mobile."""
    with sync_playwright() as p:
        # Use mobile viewport from the start so the engine creates the magnifier
        browser, page = open_game(p, base, width=360, height=740)

        # Find a cell button
        cell = page.query_selector(".cell")
        assert cell is not None, "No cell found on board"

        # Simulate pointer down on the cell
        box = cell.bounding_box()
        page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
        page.mouse.down()

        # Check if magnifier bubble is visible
        magnifier = page.query_selector(".magnifier-bubble.visible")
        assert magnifier is not None, "Magnifier bubble did not appear"

        # Check if coordinate is displayed
        coord_text = magnifier.query_selector(".coord").text_content()
        assert coord_text is not None and len(coord_text) > 0, "Coordinate not displayed in magnifier"

        page.mouse.up()
        browser.close()


def test_magnifier_bubble_hidden_on_pointerup(base):
    """Verify the magnifier bubble hides when pointer is released."""
    with sync_playwright() as p:
        # Use mobile viewport from the start so the engine creates the magnifier
        browser, page = open_game(p, base, width=360, height=740)

        # Find a cell button
        cell = page.query_selector(".cell")
        assert cell is not None, "No cell found on board"

        # Simulate pointer down on the cell
        box = cell.bounding_box()
        page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
        page.mouse.down()

        # Check if magnifier bubble is visible
        magnifier = page.query_selector(".magnifier-bubble.visible")
        assert magnifier is not None, "Magnifier bubble did not appear"

        # Release pointer
        page.mouse.up()

        # Check if magnifier bubble is hidden
        magnifier_after = page.query_selector(".magnifier-bubble.visible")
        assert magnifier_after is None, "Magnifier bubble should be hidden after pointer up"

        browser.close()


def test_magnifier_bubble_not_shown_on_desktop(base):
    """Verify the magnifier bubble is not created on desktop view."""
    with sync_playwright() as p:
        # Use desktop viewport so the engine does NOT create the magnifier
        browser, page = open_game(p, base, width=1280, height=800)

        # Check if magnifier bubble exists
        magnifier = page.query_selector(".magnifier-bubble")
        assert magnifier is None, "Magnifier bubble should not exist on desktop"

        browser.close()


def test_magnifier_bubble_shows_on_touch_mobile(base):
    """Verify the magnifier bubble appears when touching a cell on mobile."""
    with sync_playwright() as p:
        # Use mobile viewport from the start so the engine creates the magnifier
        browser, page = open_game(p, base, width=360, height=740)

        # Find a cell button
        cell = page.query_selector(".cell")
        assert cell is not None, "No cell found on board"

        # Simulate pointer down on the cell
        box = cell.bounding_box()
        page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
        page.mouse.down()

        # Check if magnifier bubble is visible
        magnifier = page.query_selector(".magnifier-bubble.visible")
        assert magnifier is not None, "Magnifier bubble did not appear"

        # Check if coordinate is displayed
        coord_text = magnifier.query_selector(".coord").text_content()
        assert coord_text is not None and len(coord_text) > 0, "Coordinate not displayed in magnifier"

        page.mouse.up()
        browser.close()
