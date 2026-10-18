"""Example browser test: copy this file for a new browser test of Slingshot's page.

It opens the real page (the shared helper starts a server and waits for the Python engine), adds a burn to the plan of the first mission,
presses the real Fly button and checks that the burn row, the result card and the "Flights" count appear and the page threw no script errors."""
import pytest
from browser_helpers import open_game  # the `base` fixture comes from conftest.py

pytest.importorskip("playwright.sync_api")
from playwright.sync_api import sync_playwright  # noqa: E402


def test_adding_a_burn_and_flying_the_plan_shows_a_result_and_counts_a_flight(base):
    with sync_playwright() as p:
        browser, page = open_game(p, base)
        page.wait_for_selector("#add-burn-button:not([disabled])")
        assert page.inner_text("#stat-flights") == "0"
        page.click("#add-burn-button")
        page.wait_for_function("document.querySelector('#stat-edits').innerText === '1'")
        assert page.locator("#burn-list > *").count() >= 1
        page.click("#fly-button")
        page.wait_for_selector("#result-card", state="visible")
        page.wait_for_function("document.querySelector('#stat-flights').innerText === '1'")
        assert page.inner_text("#result-title") != ""
        assert page.page_errors == []
        browser.close()
