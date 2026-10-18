"""Example browser test: copy this file for a new browser test of Drift's page.

It opens the real page (the shared helper starts a server and waits for the Python engine), clicks the real
Housing "Invest" button and checks that the total capacity and the funds on screen change and the page threw no
script errors."""
import pytest
from browser_helpers import open_game  # the `base` fixture comes from conftest.py

pytest.importorskip("playwright.sync_api")
from playwright.sync_api import sync_playwright  # noqa: E402


def test_investing_in_housing_raises_the_visible_capacity_and_spends_funds(base):
    with sync_playwright() as p:
        browser, page = open_game(p, base)
        assert page.inner_text("#total-capacity-display") == "Total capacity: 0"
        assert page.inner_text("#funds-display") == "Funds: 300"
        page.click("#housing-invest-button")
        page.wait_for_function("document.getElementById('total-capacity-display').innerText !== 'Total capacity: 0'")
        assert page.inner_text("#total-capacity-display") == "Total capacity: 10"
        assert page.inner_text("#funds-display") == "Funds: 280"
        assert page.page_errors == []
        browser.close()
