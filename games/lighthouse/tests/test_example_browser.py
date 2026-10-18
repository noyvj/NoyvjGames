"""Example browser test: copy this file for a new browser test of Lighthouse's page.

It opens the real page (the shared helper starts a server and waits for the Python engine), clicks the real "Light the
lamp" button of the evening plan and checks that the night panel opens and the page threw no script errors."""
import pytest
from browser_helpers import open_game  # the `base` fixture comes from conftest.py

pytest.importorskip("playwright.sync_api")
from playwright.sync_api import sync_playwright  # noqa: E402


def test_lighting_the_lamp_opens_the_night_panel(base):
    with sync_playwright() as p:
        browser, page = open_game(p, base)
        page.wait_for_selector("#light-lamp-button", state="visible")
        assert page.is_hidden("#night-panel")
        page.click("#light-lamp-button")
        page.wait_for_selector("#night-panel", state="visible")
        assert page.is_hidden("#evening-panel")
        assert page.page_errors == []
        browser.close()
