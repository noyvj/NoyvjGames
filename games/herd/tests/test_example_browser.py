"""The working example of a browser test: copy this file to start a new one.

It opens the real page in Chromium (one Pyodide boot, up to a minute), clicks one real main button the way a player
would and checks what the player sees, plus that the page raised no errors. The setup lives in browser_helpers.py;
the `base` fixture (the local server) comes from conftest.py, so it is only named as a test argument.
"""
import pytest

pytest.importorskip("playwright.sync_api")
from playwright.sync_api import sync_playwright  # noqa: E402

from browser_helpers import open_game  # noqa: E402


def test_clicking_grow_herd_adds_the_first_cow_and_raises_no_page_errors(base):
    with sync_playwright() as p:
        browser, page = open_game(p, base)
        assert page.inner_text("#herd-display") == "Herd size: 0"
        page.click("#grow-herd-button")
        page.wait_for_function("document.getElementById('herd-display').innerText !== 'Herd size: 0'")
        assert page.inner_text("#herd-display") == "Herd size: 1"
        assert page.errors == []
        browser.close()
