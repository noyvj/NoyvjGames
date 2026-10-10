"""D-12: choose, pin and reorder the main panels; presets; remembered in localStorage. Real index.html and ui.js,
game not booted (see browser_support.py)."""

import json

from .browser_support import chromium, tide_page  # noqa: F401

ORDER = """() => [...document.getElementById('game').children]
  .filter(e => ['status','sea-level-section','coastline-comparison','settlement-section','programmes-section'].includes(e.id)
               || e.classList.contains('coastline-scene')).map(e => e.id || 'coast')"""
HIDDEN = """() => [...document.querySelectorAll('[data-dash-hidden]')].map(e => e.id || 'coast').sort()"""


def open_page(tide_page, stored=None, size=(1280, 800)):
    t = tide_page(size=size, touch=False)
    if stored is not None:
        text = stored if isinstance(stored, str) else json.dumps(stored)
        t.context.add_init_script(f"localStorage.setItem('tide-dashboard-v1', {json.dumps(text)})")
    return t, t.open()


def click(page, selector):
    page.evaluate("s => document.querySelector(s).click()", selector)


def test_default_is_standard_and_changes_nothing(tide_page):
    t, page = open_page(tide_page)
    assert page.inner_text("#dashboard-toggle-button") == "🧩 Dashboard: Standard"
    assert page.evaluate(ORDER) == ["status", "sea-level-section", "coast", "coastline-comparison", "settlement-section", "programmes-section"]
    assert page.evaluate(HIDDEN) == []
    assert page.evaluate("document.getElementById('dashboard-show-all').hidden")


def test_presets_hide_and_reorder_and_are_remembered(tide_page):
    t, page = open_page(tide_page)
    click(page, "#dashboard-toggle-button")
    click(page, '[data-dash-focus="preset-compact"]')
    assert page.evaluate(ORDER)[:3] == ["coast", "status", "programmes-section"]
    assert page.evaluate(HIDDEN) == ["coastline-comparison", "sea-level-section", "settlement-section"]
    assert "3 panels are hidden" in page.inner_text("#dashboard-note")
    page.reload()
    assert page.inner_text("#dashboard-toggle-button") == "🧩 Dashboard: Compact"
    assert page.evaluate(HIDDEN) == ["coastline-comparison", "sea-level-section", "settlement-section"]
    click(page, "#dashboard-show-all")
    assert page.evaluate(HIDDEN) == [] and "Custom" in page.inner_text("#dashboard-toggle-button")
    click(page, "#dashboard-toggle-button")
    click(page, '[data-dash-focus="preset-standard"]')
    assert page.evaluate(ORDER) == ["status", "sea-level-section", "coast", "coastline-comparison", "settlement-section", "programmes-section"]


def test_postcard_and_analyst_presets(tide_page):
    t, page = open_page(tide_page)
    click(page, "#dashboard-toggle-button")
    click(page, '[data-dash-focus="preset-analyst"]')
    assert page.evaluate(ORDER) == ["status", "sea-level-section", "coastline-comparison", "coast", "programmes-section", "settlement-section"]
    click(page, '[data-dash-focus="preset-postcard"]')
    assert page.evaluate(HIDDEN) == ["programmes-section", "sea-level-section", "status"]
    assert page.evaluate(ORDER)[0] == "coast"


def test_pin_hide_and_move_make_it_custom(tide_page):
    t, page = open_page(tide_page)
    click(page, "#dashboard-toggle-button")
    click(page, '[data-dash-focus="pin-settlement"]')
    assert page.evaluate(ORDER)[0] == "settlement-section"
    click(page, '[data-dash-focus="down-meters"]')
    assert page.evaluate(ORDER)[1:3] == ["sea-level-section", "status"]
    click(page, '[data-dash-focus="show-compare"]')
    assert page.evaluate(HIDDEN) == ["coastline-comparison"]
    saved = json.loads(page.evaluate("localStorage.getItem('tide-dashboard-v1')"))
    assert saved["preset"] == "custom" and saved["pinned"] == ["settlement"] and saved["hidden"] == ["compare"]
    assert page.evaluate("document.getElementById('dashboard-toggle-button').textContent").endswith("Custom")


def test_bad_storage_falls_back_to_standard_and_fills_gaps(tide_page):
    t, page = open_page(tide_page, stored="{not json")
    assert page.inner_text("#dashboard-toggle-button").endswith("Standard")
    t2, page2 = open_page(tide_page, stored={"preset": "x", "order": ["coast", "nope", "coast"], "hidden": ["bogus", "sea"], "pinned": 5})
    assert page2.evaluate(ORDER)[0] == "coast" and len(page2.evaluate(ORDER)) == 6
    assert page2.evaluate(HIDDEN) == ["sea-level-section"]


def test_desktop_layout_is_left_alone(tide_page):
    t, page = open_page(tide_page, stored={"preset": "compact", "order": ["coast"], "hidden": ["sea"], "pinned": []})
    page.evaluate("document.documentElement.setAttribute('data-layout','pc')")
    assert page.evaluate("getComputedStyle(document.getElementById('dashboard-bar')).display") == "none"
