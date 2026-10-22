"""shared/next-achievement.js + next-achievement.css in headless Chromium (planning/TODO.md H-24): the "next up" chip picks the
closest unearned achievement from the list a game already has (highest have/need, then fewest still needed, then the
game's order), never a hidden or locked one, shows the count in words beside a bar, says when everything is earned, hides
with no list, can open the achievements panel, writes text only, touches the DOM only on a change, follows the theme and
fits 360 px. No timers, no storage, no network."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from conftest import page_html  # noqa: E402

STYLE = ('<style>body{margin:0;padding:12px;font-family:system-ui;background:#12162a;color:#eee}'
         'html[data-theme="light"] body{background:#eef2fc;color:#1b2033}</style>')
BODY = ('<button id="ach-toggle" type="button" onclick="window.__opened = (window.__opened || 0) + 1">Achievements</button>'
        '<div id="chip"></div><div id="chip2"></div><script src="/shared/next-achievement.js"></script>')
PAGE = page_html(STYLE, BODY)

LIST = [
    {"id": "first", "label": "First Spark", "description": "Patch your first room.", "earned": True, "have": 1, "need": 1},
    {"id": "ten", "label": "Ten Lit", "description": "Patch 10 rooms.", "earned": False, "have": 3, "need": 10},
    {"id": "tidy", "label": "Tidy Work", "description": "Restore 5 rooms.", "earned": False, "have": 2, "need": 5},
    {"id": "valve", "label": "Mind the Valve", "description": "Join a board through a valve.", "earned": False, "have": 0, "need": 1},
    {"id": "secret", "label": "Secret", "description": "Hush.", "earned": False, "have": 9, "need": 10, "hidden": True},
]


def open_page(harness, size=(1440, 900), theme=None):
    h = harness(size=size)
    h.pages["/t.html"] = PAGE
    h.goto()
    if theme:
        h.page.evaluate("t => document.documentElement.setAttribute('data-theme', t)", theme)
    return h


def pick(h, data):
    return h.page.evaluate("l => NoyvjNextUp.pick(l)", data)


def show(h, data, opts=None):
    h.page.evaluate("([l, o]) => { window.__chip = NoyvjNextUp.show('#chip', l, o || undefined); }", [data, opts])


def chip_text(h):
    return h.page.evaluate("document.querySelector('#chip .noyvj-nextup').innerText.replace(/\\s+/g, ' ').trim()")


# --------------------------------------------------------------------------------------------
def test_pick_takes_the_highest_have_over_need_and_skips_earned_and_hidden(harness):
    h = open_page(harness)
    got = pick(h, LIST)
    assert got == {"id": "tidy", "label": "Tidy Work", "description": "Restore 5 rooms.", "have": 2, "need": 5}
    assert h.page.evaluate("l => NoyvjNextUp.text(NoyvjNextUp.pick(l))", LIST) == "Next up: Tidy Work, 2 of 5"
    assert h.errors == []


def test_ties_go_to_the_fewest_still_needed_then_to_the_game_order(harness):
    h = open_page(harness)
    tie = [{"id": "a", "label": "A", "have": 5, "need": 10}, {"id": "b", "label": "B", "have": 1, "need": 2},
           {"id": "c", "label": "C", "have": 1, "need": 2}]
    assert pick(h, tie)["id"] == "b"
    nothing = [{"id": "x", "label": "X", "have": 0, "need": 3}, {"id": "y", "label": "Y"}, {"id": "z", "label": "Z", "need": 1}]
    assert pick(h, nothing)["id"] == "z"     # 0 progress everywhere: fewest still needed (1) first
    plain = [{"id": "p", "name": "Plain"}, {"id": "q", "title": "Other"}]
    assert pick(h, plain) == {"id": "p", "label": "Plain", "description": "", "have": None, "need": None}


def test_locked_bad_and_already_reached_entries_are_left_out(harness):
    h = open_page(harness)
    data = [None, 5, "x", {"id": "", "label": ""}, {"id": "lock", "label": "Locked", "have": 4, "need": 5, "locked": True},
            {"id": "gone", "label": "Not here", "have": 4, "need": 5, "available": False},
            {"id": "full", "label": "Full", "have": 12, "need": 10},
            {"id": "ok", "label": "Fine", "have": "2", "need": "4"},
            {"id": "neg", "label": "Negative", "have": -3, "need": 4}]
    got = pick(h, data)
    assert got["id"] == "ok" and got["have"] == 2 and got["need"] == 4
    assert pick(h, []) is None and pick(h, None) is None and pick(h, {"a": 1}) is None
    assert h.errors == []


def test_the_chip_shows_the_name_the_count_in_words_a_bar_and_the_description(harness):
    h = open_page(harness)
    show(h, LIST)
    assert chip_text(h) == "Next up: Tidy Work 2 of 5 Restore 5 rooms."
    root = "#chip .noyvj-nextup"
    assert h.page.get_attribute(root, "data-achievement-id") == "tidy"
    assert h.page.get_attribute(root, "data-state") == "next"
    assert h.page.evaluate("[document.querySelector('#chip progress').max, document.querySelector('#chip progress').value]") == [5, 2]
    assert h.page.get_attribute("#chip progress", "aria-label") == "Tidy Work: 2 of 5"
    assert h.page.evaluate("document.querySelectorAll('#chip .noyvj-nextup').length") == 1
    # A one-step achievement has no count and no bar.
    show(h, [{"id": "v", "label": "Mind the Valve", "have": 0, "need": 1}])
    assert chip_text(h) == "Next up: Mind the Valve"
    assert h.page.is_hidden("#chip progress") and h.page.is_hidden("#chip .noyvj-nextup-count")
    assert h.page.evaluate("document.querySelectorAll('#chip .noyvj-nextup').length") == 1   # updated, not mounted twice


def test_all_earned_says_so_and_no_list_hides_the_chip(harness):
    h = open_page(harness)
    show(h, [{"id": "a", "label": "A", "earned": True}, {"id": "s", "label": "S", "earned": True, "hidden": True}])
    assert chip_text(h) == "Every achievement earned."
    assert h.page.get_attribute("#chip .noyvj-nextup", "data-state") == "done"
    assert h.page.get_attribute("#chip .noyvj-nextup", "data-achievement-id") is None
    show(h, [])
    assert h.page.is_hidden("#chip .noyvj-nextup")
    show(h, LIST, None)
    assert h.page.is_visible("#chip .noyvj-nextup")
    h.page.evaluate("NoyvjNextUp.show('#chip2', [{id: 'a', label: 'A', earned: true}], {doneText: 'All done here.'})")
    assert h.page.inner_text("#chip2").strip() == "All done here."


def test_the_change_event_fires_only_when_the_chosen_achievement_changes(harness):
    h = open_page(harness)
    h.page.evaluate("window.__ev = []; document.addEventListener('noyvj-nextup-change', e => __ev.push(e.detail))")
    show(h, LIST)
    show(h, LIST)
    later = json.loads(json.dumps(LIST))
    later[2]["have"] = 3
    show(h, later)                      # same achievement, new count: no event, new text
    assert chip_text(h).startswith("Next up: Tidy Work 3 of 5")
    later[2]["earned"] = True
    show(h, later)
    assert h.page.evaluate("__ev") == [{"id": "tidy", "previous": None}, {"id": "ten", "previous": "tidy"}]


def test_the_dom_is_left_alone_when_nothing_changed(harness):
    h = open_page(harness)
    show(h, LIST)
    h.page.evaluate("""window.__muts = 0;
      new MutationObserver(m => { __muts += m.length; }).observe(document.getElementById('chip'),
        {subtree: true, childList: true, attributes: true, characterData: true});""")
    show(h, json.loads(json.dumps(LIST)))
    h.page.evaluate("new Promise(r => requestAnimationFrame(() => r()))")
    assert h.page.evaluate("__muts") == 0


def test_text_is_never_markup(harness):
    h = open_page(harness)
    show(h, [{"id": "x", "label": "<img src=x onerror=window.__pwned=1>", "description": "<b>bold</b>", "have": 1, "need": 3}])
    assert h.page.evaluate("document.querySelectorAll('#chip img, #chip b').length") == 0
    assert "<img src=x" in chip_text(h)
    assert h.page.evaluate("window.__pwned === undefined")


def test_opens_makes_a_44px_button_that_clicks_the_achievements_toggle(harness):
    h = open_page(harness)
    show(h, LIST, {"opens": "#ach-toggle"})
    assert h.page.evaluate("document.querySelector('#chip .noyvj-nextup').tagName") == "BUTTON"
    assert h.page.get_attribute("#chip button", "aria-label") == "Next up: Tidy Work, 2 of 5. Open the achievements."
    assert h.page.evaluate("document.querySelector('#chip button').getBoundingClientRect().height") >= 44
    h.page.click("#chip button")
    assert h.page.evaluate("window.__opened") == 1
    h.page.focus("#chip button")
    h.page.keyboard.press("Enter")
    assert h.page.evaluate("window.__opened") == 2


def test_the_stylesheet_is_linked_once_and_the_theme_changes_the_colours(harness):
    h = open_page(harness)
    show(h, LIST)
    assert h.page.evaluate("document.querySelectorAll('link[href*=\"next-achievement.css\"]').length") == 1
    h.page.wait_for_function("getComputedStyle(document.querySelector('#chip .noyvj-nextup')).borderLeftWidth === '4px'")
    h.page.evaluate("document.documentElement.setAttribute('data-theme', 'dark')")
    dark = h.page.evaluate("getComputedStyle(document.querySelector('#chip .noyvj-nextup')).color")
    h.page.evaluate("document.documentElement.setAttribute('data-theme', 'light')")
    light = h.page.evaluate("getComputedStyle(document.querySelector('#chip .noyvj-nextup')).color")
    assert dark != light


def test_it_fits_a_360px_screen(harness):
    h = open_page(harness, size=(360, 740))
    long = [{"id": "l", "label": "An achievement with a really quite long name indeed", "description": "x " * 60,
             "have": 123456, "need": 1000000}]
    show(h, long)
    h.page.wait_for_function("getComputedStyle(document.querySelector('#chip .noyvj-nextup')).borderLeftWidth === '4px'")
    assert h.page.evaluate("document.documentElement.scrollWidth") <= 360
    assert h.page.evaluate("document.querySelector('#chip .noyvj-nextup').getBoundingClientRect().right") <= 360


def test_a_missing_target_returns_null_and_destroy_removes_the_chip(harness):
    h = open_page(harness)
    assert h.page.evaluate("NoyvjNextUp.show('#nope', [])") is None
    show(h, LIST)
    assert h.page.evaluate("window.__chip.entry().id") == "tidy"
    h.page.evaluate("window.__chip.destroy()")
    assert h.page.evaluate("document.querySelectorAll('#chip .noyvj-nextup').length") == 0
    show(h, LIST)       # mounts again after destroy
    assert h.page.evaluate("document.querySelectorAll('#chip .noyvj-nextup').length") == 1


def test_no_timers_storage_or_network_in_the_source():
    src = (Path(__file__).resolve().parents[1] / "next-achievement.js").read_text(encoding="utf-8")
    for word in ("setTimeout", "setInterval", "localStorage", "sessionStorage", "fetch(", "XMLHttpRequest", "innerHTML"):
        assert word not in src, word
