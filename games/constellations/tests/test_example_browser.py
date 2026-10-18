"""Example browser test: copy this file for a new browser test of Constellations' page.

It opens the real page (the shared helper starts a server and waits for the Python engine), picks up star A with the keyboard, joins it to
star D (a line the first chart allows) and checks that the "Lines drawn" count goes up, Undo wakes up and the page threw no script errors."""
import pytest
from browser_helpers import open_game  # the `base` fixture comes from conftest.py

pytest.importorskip("playwright.sync_api")
from playwright.sync_api import sync_playwright  # noqa: E402


def test_joining_two_stars_draws_a_line_and_enables_undo(base):
    with sync_playwright() as p:
        browser, page = open_game(p, base)
        page.wait_for_selector("#board [data-star='0']")
        assert page.inner_text("#stat-lines") == "0"
        assert page.is_disabled("#undo-button")
        page.focus("#board")
        page.keyboard.press("a")  # the ring goes to star A
        page.keyboard.press("Enter")  # pick it up
        page.keyboard.press("d")  # the ring goes to star D
        page.keyboard.press("Enter")  # join A and D
        page.wait_for_function("document.querySelector('#stat-lines').innerText === '1'")
        assert page.is_enabled("#undo-button")
        page.click("#undo-button")
        page.wait_for_function("document.querySelector('#undo-button').disabled")
        assert page.page_errors == []
        browser.close()
