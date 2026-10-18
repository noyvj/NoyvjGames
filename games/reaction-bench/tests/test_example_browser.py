"""Example browser test: copy this file for a new browser test of Reaction Bench's page.

It opens the real page (the shared helper starts a server and waits for the Python engine), turns the first dial of the first order (the
ledger stops reading equal and Run is switched off), turns it back and presses the real Run button; the compound goes on the shelf and the
"On the shelf" count on screen goes up. The page must throw no script errors."""
import pytest
from browser_helpers import open_game  # the `base` fixture comes from conftest.py

pytest.importorskip("playwright.sync_api")
from playwright.sync_api import sync_playwright  # noqa: E402


def test_balancing_the_first_order_and_pressing_run_shelves_the_compound(base):
    with sync_playwright() as p:
        browser, page = open_game(p, base)
        page.wait_for_selector("#run-button[aria-disabled='false']")  # the first order (carbon dioxide) starts balanced at 1, 1, 1
        assert page.inner_text("#stat-shelved").startswith("0")
        page.focus(".dial .dial-val >> nth=0")
        page.keyboard.press("ArrowUp")  # a dial turns: the ledger no longer reads equal
        page.wait_for_selector("#run-button[aria-disabled='true']")  # Run is greyed with aria-disabled, not `disabled`
        page.keyboard.press("ArrowDown")  # and back
        page.wait_for_selector("#run-button[aria-disabled='false']")
        page.click("#run-button")
        page.wait_for_selector("#shelved-card", state="visible")
        page.wait_for_function("document.querySelector('#stat-shelved').innerText.startsWith('1')")
        assert page.page_errors == []
        browser.close()
