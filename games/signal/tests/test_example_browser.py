"""Example browser test: copy this file for a new browser test of Signal's page.

It opens the real page (the shared helper starts a server and waits for the Python engine), pings the centre tile of
the board the way a player would and checks that the pings counter goes down by one and the page threw no script
errors."""
import re

import pytest
from browser_helpers import open_game  # the `base` fixture comes from conftest.py

pytest.importorskip("playwright.sync_api")
from playwright.sync_api import sync_playwright  # noqa: E402


def _pings_left(page):
    return int(re.search(r"Pings: (\d+)/", page.inner_text("#pings-text")).group(1))


def test_pinging_a_tile_uses_one_ping(base):
    with sync_playwright() as p:
        browser, page = open_game(p, base)
        page.wait_for_function("window.SignalPage.engineReady")  # boot answered (earlier taps would only be queued)
        page.wait_for_function("document.querySelector('#pings-text') && /Pings: \\d+\\//.test(document.querySelector('#pings-text').innerText)")
        before = _pings_left(page)
        page.click("#board .cell[data-r='4'][data-c='4']")
        page.wait_for_function("(n) => !document.querySelector('#pings-text').innerText.includes('Pings: ' + n + '/')", arg=before)
        assert _pings_left(page) == before - 1
        assert page.page_errors == []
        browser.close()
