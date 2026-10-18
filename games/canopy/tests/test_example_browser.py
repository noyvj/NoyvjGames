"""Example browser test: copy this file for a new browser test of Canopy's page.

It opens the real page (the shared helper starts a server and waits for the Python engine), selects a plot tile,
clicks the real "Clear" button and checks that the harvested income on screen goes up and the page threw no script errors."""
import pytest
from browser_helpers import open_game  # the `base` fixture comes from conftest.py

pytest.importorskip("playwright.sync_api")
from playwright.sync_api import sync_playwright  # noqa: E402


def test_clearing_a_plot_adds_harvested_income(base):
    with sync_playwright() as p:
        browser, page = open_game(p, base)
        # setup() has run once the action buttons stop reading "Loading..."
        page.wait_for_function("document.querySelector('#clear-button').textContent !== 'Loading...'")
        assert page.inner_text("#income-display") == "Harvested income: 0.0"
        # a fresh plot holds no value until the first game tick (one second); clearing it before then pays nothing
        page.wait_for_function("document.querySelector('#standing-value-display').innerText !== 'Standing forest value: 0.0'")
        page.click("#plot-1")
        page.wait_for_selector("#plot-1.plot-selected")  # the page redraws the grid after a click: wait for it
        page.click("#clear-button")
        page.wait_for_selector("#plot-1.plot-bare")
        page.wait_for_function("document.querySelector('#income-display').innerText !== 'Harvested income: 0.0'")
        assert float(page.inner_text("#income-display").split(":")[1]) > 0
        assert page.page_errors == []
        browser.close()
