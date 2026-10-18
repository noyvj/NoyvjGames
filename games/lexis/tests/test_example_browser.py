"""Example browser test: copy this file for a new browser test of Lexis' page.

It opens the real page (the shared helper starts a server and waits for the Python engine), clicks the real "Next
transmission" button on planet 1 and checks that the first transmission appears on screen and the page threw no
script errors."""
import pytest
from browser_helpers import open_game  # the `base` fixture comes from conftest.py

pytest.importorskip("playwright.sync_api")
from playwright.sync_api import sync_playwright  # noqa: E402


def test_next_transmission_adds_a_scene_to_the_list(base):
    with sync_playwright() as p:
        browser, page = open_game(p, base)
        page.wait_for_selector("#next-scene-button", state="visible")
        before = page.locator("#scene-list > *").count()
        page.click("#next-scene-button")
        page.wait_for_function(
            "(n) => document.querySelectorAll('#scene-list > *').length > n", arg=before)
        assert page.locator("#scene-list > *").count() == before + 1
        assert page.page_errors == []
        browser.close()
