"""Example browser test: copy this file for a new browser test of Loop's page.

It opens the real page (the shared helper starts a server and waits for the Python engine), clicks the real
"Repair Networks" buy button and checks that the repair count and the funds on screen change and the page threw no
script errors."""
import pytest
from browser_helpers import open_game  # the `base` fixture comes from conftest.py

pytest.importorskip("playwright.sync_api")
from playwright.sync_api import sync_playwright  # noqa: E402


def test_buying_a_repair_network_raises_the_visible_count_and_spends_funds(base):
    with sync_playwright() as p:
        browser, page = open_game(p, base)
        assert page.inner_text("#repair-count") == "0"
        assert page.inner_text("#funds-display") == "Funds: 300"
        page.click("#repair-invest-button")
        page.wait_for_function("document.getElementById('repair-count').innerText !== '0'")
        assert page.inner_text("#repair-count") == "1"
        assert page.inner_text("#funds-display") == "Funds: 280"
        assert page.page_errors == []
        browser.close()
