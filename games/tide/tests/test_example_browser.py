"""Example browser test: copy this file for a new browser test of Tide's page.

It opens the real page (the shared helper starts a server and waits for the Python engine), clicks the real
"Advance Season" button and checks that the season counter on screen goes from 1 to 2 and the page threw no script errors."""
import pytest
from browser_helpers import open_game  # the `base` fixture comes from conftest.py

pytest.importorskip("playwright.sync_api")
from playwright.sync_api import sync_playwright  # noqa: E402


def test_advancing_a_season_shows_season_two(base):
    with sync_playwright() as p:
        browser, page = open_game(p, base)
        # the first render() has run once the invest buttons stop reading "Loading..."
        page.wait_for_function("document.querySelector('#output-invest-button').textContent !== 'Loading...'")
        assert page.inner_text("#season-display") == "Season 1"
        page.click("#advance-season-button")
        page.wait_for_function("document.querySelector('#season-display').innerText === 'Season 2'")
        assert page.inner_text("#season-display") == "Season 2"
        assert page.page_errors == []
        browser.close()
