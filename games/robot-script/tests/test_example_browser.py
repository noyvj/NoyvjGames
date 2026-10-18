"""Example browser test: copy this file for a new browser test of Robot Script's page.

It opens the real page (the shared helper starts a server and waits for the Python engine), taps the real "Forward"
instruction in the palette and checks that the list on screen grows to one step and the page threw no script errors."""
import pytest
from browser_helpers import open_game  # the `base` fixture comes from conftest.py

pytest.importorskip("playwright.sync_api")
from playwright.sync_api import sync_playwright  # noqa: E402


def test_tapping_forward_adds_one_step_to_the_list(base):
    with sync_playwright() as p:
        browser, page = open_game(p, base)
        page.wait_for_selector("[data-testid=robot-script-add-F]", state="visible")
        assert page.inner_text("#size-line").startswith("0 steps")
        page.click("[data-testid=robot-script-add-F]")
        page.wait_for_function("document.querySelector('#size-line').innerText.startsWith('1 step ')")
        assert page.inner_text("#size-line").startswith("1 step in your list")
        assert page.page_errors == []
        browser.close()
