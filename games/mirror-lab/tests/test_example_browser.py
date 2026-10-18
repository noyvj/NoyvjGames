"""Example browser test: copy this file for a new browser test of Mirror Lab's page.

It opens the real page (the shared helper starts a server and waits for the Python engine), chooses the mirror from the tray of the
first bench, taps the slot the beam needs and checks that the bench is cleared on screen and the page threw no script errors."""
import pytest
from browser_helpers import open_game  # the `base` fixture comes from conftest.py

pytest.importorskip("playwright.sync_api")
from playwright.sync_api import sync_playwright  # noqa: E402


def test_placing_the_mirror_on_the_first_bench_lights_the_sensor_and_clears_it(base):
    with sync_playwright() as p:
        browser, page = open_game(p, base)
        assert page.inner_text("#bench-heading") != ""
        assert page.inner_text("#lit-line").startswith("0 of 1 sensor lit")
        if page.get_attribute("button.tray-btn[data-piece='mirror']", "aria-pressed") != "true":  # a bench with one kind of piece holds it already
            page.click("button.tray-btn[data-piece='mirror']")
        page.click(".ml-hit[data-r='3'][data-c='4']")  # the slot of the stored answer for bench c1-1
        page.wait_for_function("document.querySelector('#lit-line').innerText.startsWith('1 of 1 sensor lit')")
        page.wait_for_selector("#verdict-card", state="visible")
        assert page.is_enabled("#next-button")
        assert page.page_errors == []
        browser.close()
