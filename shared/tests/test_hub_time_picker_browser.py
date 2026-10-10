"""The hub's "How long have you got?" picker (planning/TODO.md QI-50) in headless Chromium: the three
lengths map to the hand-written game-sessions.json tiers, games the visitor has not started come first,
it announces politely, opens and closes, and nothing reaches the network beyond the mocked backend."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SESSIONS = json.loads((ROOT / "game-sessions.json").read_text())["games"]


QUIET = "localStorage.setItem('hub-onboarding-seen','1'); localStorage.setItem('tutorial-seen:hub','1')"


def open_hub(harness, init=(), size=(1440, 900)):
    h = harness(size=size, init_scripts=[QUIET] + list(init))
    h.goto("/index.html")
    h.page.wait_for_function("document.querySelectorAll('.title-card-session').length > 0")
    return h


def open_picker(h):
    h.page.click("#time-picker-button")
    return h


def pick(h, key):
    h.page.click(f'.time-picker-choice[data-time="{key}"]')


def names(h):
    return h.page.evaluate("[...document.querySelectorAll('#time-picker-results a')].map(a => a.textContent)")


def slugs_for(*tiers):
    return {slug for slug, tier in SESSIONS.items() if tier in tiers}


def test_picker_is_closed_until_opened_and_toggles(harness):
    h = open_hub(harness)
    assert h.page.is_hidden("#time-picker")
    assert h.page.get_attribute("#time-picker-button", "aria-expanded") == "false"
    open_picker(h)
    assert h.page.is_visible("#time-picker")
    assert h.page.get_attribute("#time-picker-button", "aria-expanded") == "true"
    h.page.click("#time-picker-button")
    assert h.page.is_hidden("#time-picker")


def test_five_minutes_lists_only_the_short_games(harness):
    h = open_hub(harness)
    open_picker(h)
    pick(h, "5")
    found = names(h)
    assert len(found) == len(slugs_for("short")) > 0
    assert all("About 5 min" in n for n in found)
    assert h.page.get_attribute('.time-picker-choice[data-time="5"]', "aria-pressed") == "true"
    assert h.page.get_attribute('.time-picker-choice[data-time="15"]', "aria-pressed") == "false"


def test_fifteen_minutes_adds_the_medium_games_and_caps_the_list(harness):
    h = open_hub(harness)
    open_picker(h)
    pick(h, "15")
    found = names(h)
    assert 0 < len(found) <= 6
    assert all(("About 5 min" in n) or ("About 20 min" in n) for n in found)
    note = h.page.inner_text("#time-picker-note")
    assert f"of {len(slugs_for('short', 'medium'))}" in note


def test_all_night_lists_the_long_form_games(harness):
    h = open_hub(harness)
    open_picker(h)
    pick(h, "night")
    found = names(h)
    assert len(found) == len(slugs_for("long"))
    assert all("Long-form" in n for n in found)


def test_games_not_started_come_first_and_are_marked(harness):
    init = "localStorage.setItem('savecode:signal', 'ABCD-1234')"
    h = open_hub(harness, init=[init])
    open_picker(h)
    pick(h, "5")
    found = names(h)
    assert "(new to you)" in found[0]
    assert "(new to you)" not in found[-1]
    assert "Signal" in found[-1]


def test_links_go_to_the_game_pages_and_text_is_plain(harness):
    h = open_hub(harness)
    open_picker(h)
    pick(h, "night")
    hrefs = h.page.evaluate("[...document.querySelectorAll('#time-picker-results a')].map(a => a.getAttribute('href'))")
    assert hrefs and all(href.startswith("games/") for href in hrefs)
    assert h.page.evaluate("document.querySelectorAll('#time-picker-results *:not(li):not(a)').length") == 0


def test_note_is_a_polite_status_and_no_page_errors(harness):
    h = open_hub(harness)
    assert h.page.get_attribute("#time-picker-note", "role") == "status"
    assert h.page.get_attribute("#time-picker-note", "aria-live") == "polite"
    open_picker(h)
    pick(h, "15")
    assert h.errors == []


def test_fits_a_phone_without_sideways_scroll(harness):
    h = open_hub(harness, size=(360, 740))
    open_picker(h)
    pick(h, "15")
    assert h.page.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth")
    assert h.page.evaluate("[...document.querySelectorAll('.time-picker-choice')].every(b => b.getBoundingClientRect().height >= 44)")
