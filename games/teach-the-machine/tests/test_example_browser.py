"""Example browser test: copy this file for a new browser test of Teach the Machine's page.

It opens the real page (the shared helper starts a server and waits for the Python engine), presses the real Train button on the first
lesson, then Test, and checks that the "Trained" count goes up, Pip's tree and the test result appear and the page threw no script
errors."""
import pytest
from browser_helpers import open_game  # the `base` fixture comes from conftest.py

pytest.importorskip("playwright.sync_api")
from playwright.sync_api import sync_playwright  # noqa: E402


def test_training_and_testing_pip_shows_the_tree_and_the_result(base):
    with sync_playwright() as p:
        browser, page = open_game(p, base)
        page.wait_for_selector("#train-button:not([disabled])")
        assert page.inner_text("#stat-trains") == "0"
        assert page.is_hidden("#tree-box")
        page.click("#train-button")
        page.wait_for_selector("#tree-box", state="visible")
        page.wait_for_function("document.querySelector('#stat-trains').innerText === '1'")
        page.wait_for_selector("#test-button:not([disabled])")
        page.click("#test-button")
        page.wait_for_selector("#result-box", state="visible")
        assert page.page_errors == []
        browser.close()
