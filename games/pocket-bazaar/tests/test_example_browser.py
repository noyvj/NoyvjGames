"""Example browser test: copy this file for a new browser test of Pocket Bazaar's page.

It opens the real page (the shared helper starts a server and waits for the Python engine), opens the stall with the
real "Open the stall" button, puts a crate on the board and checks that the crates tally goes up and the page
threw no script errors."""
import pytest
from browser_helpers import open_game  # the `base` fixture comes from conftest.py

pytest.importorskip("playwright.sync_api")
from playwright.sync_api import sync_playwright  # noqa: E402


def test_opening_the_stall_and_adding_a_crate_raises_the_crate_count(base):
    with sync_playwright() as p:
        browser, page = open_game(p, base)
        page.wait_for_selector("#start-day-button", state="visible")
        page.click("#start-day-button")
        page.wait_for_function("document.getElementById('game').dataset.phase === 'open'")
        assert page.text_content("#stat-crates") == "0"  # the tally sits in a closed <details>: read textContent, not innerText
        page.click("#crates button >> nth=0")
        page.wait_for_function("document.querySelector('#stat-crates').textContent !== '0'")
        assert page.text_content("#stat-crates") == "1"
        assert page.page_errors == []
        browser.close()
