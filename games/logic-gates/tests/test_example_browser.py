"""Example browser test: copy this file for a new browser test of Logic Gates' page.

It opens the real page (the shared helper starts a server and waits for the Python engine), flips switch A on the first
level and checks that the switch reads "A = 1", the flips counter goes from 0 to 1 and the page threw no script errors."""
import pytest
from browser_helpers import open_game  # the `base` fixture comes from conftest.py

pytest.importorskip("playwright.sync_api")
from playwright.sync_api import sync_playwright  # noqa: E402


def test_flipping_a_switch_updates_the_switch_and_the_flips_counter(base):
    with sync_playwright() as p:
        browser, page = open_game(p, base)
        page.wait_for_selector("#switch-A", state="visible")
        assert page.inner_text("#switch-A") == "A = 0"
        assert page.inner_text("#stat-flips") == "0"
        page.click("#switch-A")
        page.wait_for_function("document.querySelector('#switch-A').innerText === 'A = 1'")
        assert page.inner_text("#stat-flips") == "1"
        assert page.page_errors == []
        browser.close()
