"""Example browser test: copy this file for a new browser test of Evidence Hunt's page.

It opens the real page (the shared helper starts a server and waits for the Python engine), packs the first piece of
equipment for the first case and checks that the bag count on screen goes up, the piece shows "In the bag" and the page
threw no script errors."""
import pytest
from browser_helpers import open_game  # the `base` fixture comes from conftest.py

pytest.importorskip("playwright.sync_api")
from playwright.sync_api import sync_playwright  # noqa: E402

GEAR = "[data-testid='evidence-hunt-gear-0']"


def test_packing_a_piece_of_equipment_fills_the_bag(base):
    with sync_playwright() as p:
        browser, page = open_game(p, base)
        page.wait_for_selector(GEAR, state="visible")
        assert page.text_content("#bag-count").startswith("(0 of ")  # text_content: the CSS shows it in capitals
        page.click(GEAR)
        page.wait_for_function("document.querySelector('#bag-count').textContent.startsWith('(1 of ')")
        assert "In the bag" in page.text_content(GEAR)
        assert page.page_errors == []
        browser.close()
