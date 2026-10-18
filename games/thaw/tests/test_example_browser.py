"""Example browser test: copy this file for a new browser test of Thaw's page.

It opens the real page (the shared helper starts a server and waits for the Python engine), clicks the real
"Advance Round" button and checks that the round counter on screen goes from 1 to 2 and the page threw no script errors."""
import pytest
from browser_helpers import open_game  # the `base` fixture comes from conftest.py

pytest.importorskip("playwright.sync_api")
from playwright.sync_api import sync_playwright  # noqa: E402


def test_advancing_a_round_shows_round_two(base):
    with sync_playwright() as p:
        browser, page = open_game(p, base)
        # the first render() has run once the invest buttons stop reading "Loading..."
        page.wait_for_function("document.querySelector('#output-invest-button').textContent !== 'Loading...'")
        assert page.inner_text("#round-display") == "Round 1"
        page.click("#advance-round-button")
        page.wait_for_function("document.querySelector('#round-display').innerText === 'Round 2'")
        assert page.inner_text("#round-display") == "Round 2"
        assert page.page_errors == []
        browser.close()
