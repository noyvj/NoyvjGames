"""Example browser test: copy this file for a new browser test of Stranded's page.

It opens the real page (the shared helper starts a server and waits for the Python engine), reads Ines's first messages one tap
at a time, sends the first reply and checks that the reply appears in the chat, the sent counter reads 1 and the page threw no
script errors."""
import pytest
from browser_helpers import open_game  # the `base` fixture comes from conftest.py

pytest.importorskip("playwright.sync_api")
from playwright.sync_api import sync_playwright  # noqa: E402

CHOICE = "[data-testid='stranded-choice-0']"
NEXT = "[data-testid='stranded-next']"


def test_sending_the_first_reply_puts_it_in_the_chat_and_counts_it(base):
    with sync_playwright() as p:
        browser, page = open_game(p, base)
        # one message per tap is the default: tap "Next message" until the replies are offered
        while not page.is_visible(CHOICE):
            page.click(NEXT)
        assert page.text_content("#stat-sent") == "0"  # text_content: the tally block may be collapsed (inner_text would be empty)
        page.click(CHOICE)
        page.wait_for_selector("#chat .msg.you", state="visible")
        assert page.text_content("#stat-sent") == "1"
        assert page.page_errors == []
        browser.close()
