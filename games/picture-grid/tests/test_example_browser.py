"""Example browser test: copy this file for a new browser test of Picture Grid's page.

It opens the real page (the shared helper starts a server and waits for the Python engine), chooses the Fill tool, marks the cell under
the keyboard ring with Space and checks that the "Cells filled" count goes up, Undo wakes up and the page threw no script errors."""
import pytest
from browser_helpers import open_game  # the `base` fixture comes from conftest.py

pytest.importorskip("playwright.sync_api")
from playwright.sync_api import sync_playwright  # noqa: E402


def test_filling_a_cell_counts_on_the_stats_strip_and_enables_undo(base):
    with sync_playwright() as p:
        browser, page = open_game(p, base)
        page.wait_for_selector("#board rect.b-bg")
        assert page.inner_text("#stat-cells") == "0"
        assert page.is_disabled("#undo-button")
        page.click("#mode-fill-button")
        page.focus("#board")
        page.keyboard.press("Space")
        page.wait_for_function("document.querySelector('#stat-cells').innerText === '1'")
        assert page.is_enabled("#undo-button")
        page.click("#undo-button")
        page.wait_for_function("document.querySelector('#undo-button').disabled")
        assert page.page_errors == []
        browser.close()
