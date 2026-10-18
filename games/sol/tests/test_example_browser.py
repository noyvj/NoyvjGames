"""Example browser test: copy this file for a new browser test of SOL's page.

It opens the real page (the shared helper starts a server and waits for the Python engine), clicks the real
"Mine Iron" button and checks that the Iron count on screen goes up and the page threw no script errors."""
import pytest
from browser_helpers import open_game  # the `base` fixture comes from conftest.py

pytest.importorskip("playwright.sync_api")
from playwright.sync_api import sync_playwright  # noqa: E402


def test_mining_iron_raises_the_visible_iron_count(base):
    with sync_playwright() as p:
        browser, page = open_game(p, base)
        page.wait_for_selector("#click-button:not([disabled])")  # setup() enables it once the engine is wired
        assert page.inner_text("#resource-count") == "0"
        page.click("#click-button")
        page.wait_for_function("document.querySelector('#resource-count').innerText !== '0'")
        assert int(page.inner_text("#resource-count")) >= 1
        assert page.page_errors == []
        browser.close()
