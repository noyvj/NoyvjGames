"""Example browser test: copy this file for a new browser test of Heist Committee's page.

It opens the real page (the shared helper starts a server and waits for the Python engine), takes the first job on the
contract board and checks that the case file opens (the status line in the top bar changes) and the page threw no script
errors."""
import pytest
from browser_helpers import open_game  # the `base` fixture comes from conftest.py

pytest.importorskip("playwright.sync_api")
from playwright.sync_api import sync_playwright  # noqa: E402


def test_taking_a_job_opens_the_case_file(base):
    with sync_playwright() as p:
        browser, page = open_game(p, base)
        page.wait_for_selector("[data-testid='heist-take-pigeon_museum']", state="visible")
        assert page.text_content("#hud-status") == "Contract board"
        page.click("[data-testid='heist-take-pigeon_museum']")
        page.wait_for_selector("#phase-scout", state="visible")
        assert page.is_hidden("#phase-board")
        assert page.text_content("#hud-status") == "Case file"
        assert page.page_errors == []
        browser.close()
