"""Example browser test: copy this file for a new browser test of Chronicle's page.

It opens the real page (the shared helper starts a server and waits for the Python engine), picks up the first card in
the tray, taps slot 1 and checks that the slot now shows that card and the page threw no script errors."""
import pytest
from browser_helpers import open_game  # the `base` fixture comes from conftest.py

pytest.importorskip("playwright.sync_api")
from playwright.sync_api import sync_playwright  # noqa: E402


def test_tapping_a_card_then_a_slot_places_the_card(base):
    with sync_playwright() as p:
        browser, page = open_game(p, base)
        page.wait_for_selector("#tray .card")  # the first puzzle is drawn once the engine has answered
        title = page.inner_text("#tray .card")
        page.click("#tray .card")
        page.click("#slots .slot[data-slot='0']")
        page.wait_for_function("document.querySelector(\"#slots .slot[data-slot='0'] .slot-card\").innerText !== 'Empty'")
        assert page.inner_text("#slots .slot[data-slot='0'] .slot-card") == title
        assert page.inner_text("#slots .slot[data-slot='0'] .slot-state") == "Placed"
        assert page.page_errors == []
        browser.close()
