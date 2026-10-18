"""Example browser test: copy this file for a new browser test of Rule Finder's page.

It opens the real page (the shared helper starts a server and waits for the Python engine), types an item into the number builder of the
first case, presses the real Send button and checks that the gate answers, the "Tests" count goes up, the item is listed and the page
threw no script errors."""
import pytest
from browser_helpers import open_game  # the `base` fixture comes from conftest.py

pytest.importorskip("playwright.sync_api")
from playwright.sync_api import sync_playwright  # noqa: E402


def test_sending_a_number_to_the_gate_counts_a_test_and_lists_the_item(base):
    with sync_playwright() as p:
        browser, page = open_game(p, base)
        page.wait_for_selector("#num-input", state="visible")
        assert page.inner_text("#stat-tests") == "0"
        listed = page.locator("#through-list > *").count() + page.locator("#stopped-list > *").count()  # the starting examples
        page.fill("#num-input", "7")
        page.click("#send-button")
        page.wait_for_function("document.querySelector('#stat-tests').innerText === '1'")
        assert page.locator("#through-list > *").count() + page.locator("#stopped-list > *").count() == listed + 1
        assert page.page_errors == []
        browser.close()
