"""Example browser test: copy this file for a new browser test of Hull Repair's page.

It opens the real page (the shared helper starts a server and waits for the Python engine), presses the real "Hint"
button and checks that the first hint rung (the nudge) appears with words in it, the hints tally goes up and the page
threw no script errors."""
import pytest
from browser_helpers import open_game  # the `base` fixture comes from conftest.py

pytest.importorskip("playwright.sync_api")
from playwright.sync_api import sync_playwright  # noqa: E402


def test_pressing_hint_shows_the_nudge_and_counts_the_hint(base):
    with sync_playwright() as p:
        browser, page = open_game(p, base)
        page.wait_for_selector("#hint-button", state="visible")
        assert page.is_hidden("#hint-nudge")
        assert page.text_content("#stat-hints") == "0"  # the tally sits in a closed <details>: read textContent
        page.click("#hint-button")
        page.wait_for_selector("#hint-nudge", state="visible")
        assert page.inner_text("#hint-nudge").strip() != ""
        assert page.text_content("#stat-hints") == "1"
        assert page.page_errors == []
        browser.close()
