"""Example browser test: copy this file for a new browser test of Station Medic's page.

It opens the real page (the shared helper starts a server and waits for the Python engine), treats the one patient of the
first shift with the only treatment on the shelf and checks that the result card opens and the page threw no script errors."""
import pytest
from browser_helpers import open_game  # the `base` fixture comes from conftest.py

pytest.importorskip("playwright.sync_api")
from playwright.sync_api import sync_playwright  # noqa: E402


def test_treating_the_first_patient_opens_the_result_card(base):
    with sync_playwright() as p:
        browser, page = open_game(p, base)
        page.wait_for_selector("[data-testid='station-medic-treat-0']", state="visible")
        assert page.is_hidden("#result-card")
        page.click("[data-testid='station-medic-treat-0']")
        page.wait_for_selector("#result-card", state="visible")
        assert "A clean shift" in page.inner_text("#result-text")  # first shift: the one patient has one cure on the shelf
        assert page.page_errors == []
        browser.close()
