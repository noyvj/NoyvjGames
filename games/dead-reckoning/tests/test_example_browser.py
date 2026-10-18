"""Example browser test: copy this file for a new browser test of Dead Reckoning's page.

It opens the real page (the shared helper starts a server and waits for the Python engine), adds a leg to the plan of the
first chart and checks that the leg appears in the list, the legs total reads 1 and the page threw no script errors."""
import pytest
from browser_helpers import open_game  # the `base` fixture comes from conftest.py

pytest.importorskip("playwright.sync_api")
from playwright.sync_api import sync_playwright  # noqa: E402


def test_adding_a_leg_puts_it_in_the_plan_and_the_total(base):
    with sync_playwright() as p:
        browser, page = open_game(p, base)
        page.wait_for_selector("#chart-holder svg", state="attached")   # the first view is drawn after the engine is ready
        page.wait_for_selector("#add-leg-button:not([disabled])")
        assert page.text_content("#total-legs") == "0"
        assert page.locator("#legs-list > li.leg").count() == 0       # an empty plan shows one "No legs yet" note instead
        page.click("#add-leg-button")
        page.wait_for_selector("#legs-list > li.leg", state="visible")
        assert page.locator("#legs-list > li.leg").count() == 1
        assert page.text_content("#total-legs") == "1"
        assert page.page_errors == []
        browser.close()
