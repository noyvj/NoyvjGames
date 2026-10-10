"""shared/calm-mode.js + calm-mode.css in headless Chromium (planning/TODO.md QI-51): off by default,
the switch sets one page attribute, targets grow to 56 px, motion stops, a fixed click-through dim
layer appears, the one-handed dock shows only while on (hand choice, at most four buttons), the calm
filter hides and restores items, storage tolerated blocked, keyboard use, themes, 360 px, no timers,
no network, no console errors."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from conftest import page_html  # noqa: E402

STYLE = ('<style>body{margin:0;padding:12px;font-family:system-ui;background:#12162a;color:#eee}'
         'button{min-height:20px}input{min-height:10px}@keyframes spin{to{transform:rotate(360deg)}} #spin{animation:spin 2s linear infinite;width:20px;height:20px;background:red}'
         '#slide{transition:margin-left 2s;margin-left:0}</style>')
PAGE = page_html(STYLE + '<link rel="stylesheet" href="/shared/calm-mode.css">',
                 '<h1>Game</h1><button id="btn">Press</button><input id="inp" type="text">'
                 '<div id="spin"></div><div id="slide"></div><div id="slot"></div>'
                 '<ul id="games"><li data-tags="calm quiet" id="g1">Canopy</li><li data-tags="arcade" id="g2">Blitz</li>'
                 '<li data-tags="" data-calm="true" id="g3">Tide</li></ul>'
                 '<script src="/shared/calm-mode.js"></script>')


def load(harness, **kw):
    h = harness(**kw)
    h.pages["/t.html"] = PAGE
    page = h.goto()
    page.wait_for_function("window.NoyvjCalm")
    return h, page


def test_it_is_off_by_default_and_changes_nothing(harness):
    h, page = load(harness)
    assert page.evaluate("NoyvjCalm.isOn()") is False
    assert page.get_attribute("html", "data-calm") == "false"
    assert page.evaluate("document.querySelector('#btn').getBoundingClientRect().height") < 40
    assert float(page.evaluate("getComputedStyle(document.querySelector('.noyvj-calm-dim')).opacity")) == 0
    assert page.locator(".noyvj-calm-dock").count() == 0 and h.errors == []


def test_on_enlarges_targets_dims_and_stops_motion(harness):
    h, page = load(harness)
    page.evaluate("NoyvjCalm.setOn(true)")
    assert page.get_attribute("html", "data-calm") == "true"
    assert page.evaluate("document.querySelector('#btn').getBoundingClientRect().height") >= 56
    assert page.evaluate("document.querySelector('#inp').getBoundingClientRect().height") >= 56
    assert float(page.evaluate("getComputedStyle(document.querySelector('.noyvj-calm-dim')).opacity")) > 0.2
    assert page.evaluate("getComputedStyle(document.querySelector('.noyvj-calm-dim')).pointerEvents") == "none"
    assert page.evaluate("getComputedStyle(document.querySelector('#spin')).animationDuration") in ("0.001s", "1e-06s", "0s")
    assert page.evaluate("parseFloat(getComputedStyle(document.documentElement).fontSize)") >= 17
    page.click("#btn")  # clicks pass through the dim layer
    page.evaluate("NoyvjCalm.setOn(false)")
    assert page.evaluate("document.querySelector('#btn').getBoundingClientRect().height") < 40


def test_the_choice_persists_and_blocked_storage_is_tolerated(harness):
    h, page = load(harness)
    page.evaluate("NoyvjCalm.setOn(true)")
    page.reload()
    page.wait_for_function("window.NoyvjCalm")
    assert page.evaluate("NoyvjCalm.isOn()") is True and page.get_attribute("html", "data-calm") == "true"
    page.evaluate("NoyvjCalm.toggle()")
    page.reload()
    page.wait_for_function("window.NoyvjCalm")
    assert page.evaluate("NoyvjCalm.isOn()") is False
    blocked = harness(init_scripts=["Object.defineProperty(window, 'localStorage', {get(){ throw new Error('blocked'); }});"])
    blocked.pages["/t.html"] = PAGE
    p2 = blocked.goto()
    p2.wait_for_function("window.NoyvjCalm")
    p2.evaluate("NoyvjCalm.setOn(true)")
    assert p2.evaluate("NoyvjCalm.isOn()") is True and blocked.errors == []


def test_the_dock_shows_only_while_on_with_at_most_four_buttons(harness):
    h, page = load(harness)
    page.evaluate("window.__clicks = []; NoyvjCalm.setDock([{id:'a',label:'Water',onClick:()=>__clicks.push('a')},{id:'b',label:'Next'},"
                  "{label:'Menu'},{label:'Four'},{label:'Five'},{label:'   '},null]); 0")
    assert page.locator(".noyvj-calm-dock").count() == 0  # off: nothing shown
    page.evaluate("NoyvjCalm.setOn(true)")
    assert page.locator(".noyvj-calm-dock button").count() == 4
    box = page.locator(".noyvj-calm-dock").bounding_box()
    assert box["y"] + box["height"] >= 639  # fixed to the bottom edge
    assert all(b["height"] >= 64 for b in [page.locator(".noyvj-calm-dock button").nth(i).bounding_box() for i in range(4)])
    page.click(".noyvj-calm-dock button >> nth=0")
    assert page.evaluate("__clicks") == ["a"]
    page.evaluate("NoyvjCalm.setOn(false)")
    assert page.locator(".noyvj-calm-dock").count() == 0
    page.evaluate("NoyvjCalm.setOn(true); NoyvjCalm.clearDock()")
    assert page.locator(".noyvj-calm-dock").count() == 0


def test_the_hand_choice_moves_the_dock_and_is_validated(harness):
    h, page = load(harness)
    page.evaluate("NoyvjCalm.setDock([{label:'One'},{label:'Two'}]); NoyvjCalm.setOn(true)")
    assert page.get_attribute(".noyvj-calm-dock", "data-hand") == "right"
    right_x = page.locator(".noyvj-calm-dock button").first.bounding_box()["x"]
    assert page.evaluate("NoyvjCalm.setHand('left')") is True
    assert page.get_attribute(".noyvj-calm-dock", "data-hand") == "left"
    assert page.locator(".noyvj-calm-dock button").first.bounding_box()["x"] < right_x
    assert page.evaluate("NoyvjCalm.setHand('middle')") is False and page.evaluate("NoyvjCalm.getHand()") == "left"


def test_the_filter_hides_non_calm_items_and_restores_them(harness):
    h, page = load(harness)
    page.evaluate("window.__f = NoyvjCalm.filter('#games', {itemSelector: 'li'}); 0")
    assert page.locator("#games li:visible").count() == 3
    page.evaluate("NoyvjCalm.setOn(true)")
    visible = page.eval_on_selector_all("#games li", "els => els.filter(e => !e.hidden).map(e => e.id)")
    assert visible == ["g1", "g3"]  # a calm tag, and data-calm="true"
    assert "showing 2 of 3" in page.inner_text(".noyvj-calm-count")
    assert page.evaluate("__f.shown()") == 2 and page.evaluate("__f.total()") == 3
    page.evaluate("NoyvjCalm.setOn(false)")
    assert page.locator("#games li:visible").count() == 3 and page.locator(".noyvj-calm-count").count() == 0
    page.evaluate("NoyvjCalm.setOn(true); __f.destroy()")
    assert page.locator("#games li:visible").count() == 3


def test_an_item_the_page_hid_itself_stays_hidden(harness):
    h, page = load(harness)
    page.evaluate("document.getElementById('g2').hidden = true; NoyvjCalm.filter('#games', {itemSelector: 'li', note: false}); NoyvjCalm.setOn(true); NoyvjCalm.setOn(false)")
    assert page.evaluate("document.getElementById('g2').hidden") is True  # hidden by the page itself: calm never un-hides it


def test_custom_tags_and_the_default_calm_list(harness):
    h, page = load(harness)
    page.evaluate("NoyvjCalm.filter('#games', {itemSelector: 'li', getTags: n => n.id === 'g2' ? ['gentle'] : [], calmTags: ['gentle']}); NoyvjCalm.setOn(true)")
    visible = page.eval_on_selector_all("#games li", "els => els.filter(e => !e.hidden).map(e => e.id)")
    assert visible == ["g2", "g3"]
    games = page.evaluate("NoyvjCalm.CALM_GAMES")
    assert "canopy" in games and "dead-reckoning" in games and len(games) == len(set(games))


def test_events_fire_once_per_real_change_and_unsubscribe(harness):
    h, page = load(harness)
    page.evaluate("window.__log = []; document.addEventListener('noyvj-calm-change', e => __log.push(e.detail.on));"
                  " window.__off = NoyvjCalm.onChange(s => __log.push('cb:' + s.on)); 0")
    page.evaluate("NoyvjCalm.setOn(true); NoyvjCalm.setOn(true); NoyvjCalm.setOn(false); __off(); NoyvjCalm.setOn(true); 0")
    assert page.evaluate("__log") == ["cb:true", True, "cb:false", False, True]


def test_the_settings_control_explains_and_works_from_the_keyboard(harness):
    h, page = load(harness)
    page.evaluate("NoyvjCalm.mount('#slot'); 0")
    text = page.inner_text(".noyvj-calm-control").lower()
    assert "off by default" in text and "56 pixels" in text and "calm games" in text
    page.focus("#btn")
    page.keyboard.press("Tab")
    page.keyboard.press("Tab")
    assert page.evaluate("document.activeElement.tagName") in ("INPUT", "SELECT")
    page.check(".noyvj-calm-control input[type=checkbox]")
    assert page.evaluate("NoyvjCalm.isOn()") is True and "is on" in page.inner_text(".noyvj-calm-control [role=status]")
    page.select_option(".noyvj-calm-control select", "left")
    assert page.evaluate("NoyvjCalm.getHand()") == "left"
    assert page.get_attribute(".noyvj-calm-control [role=status]", "aria-live") == "polite"
    page.uncheck(".noyvj-calm-control input[type=checkbox]")
    assert page.evaluate("NoyvjCalm.isOn()") is False and h.errors == []


def test_bind_checkbox_keeps_a_games_own_checkbox_in_step(harness):
    h = harness()
    h.pages["/t.html"] = PAGE.replace('<div id="slot"></div>', '<input type="checkbox" id="c">')
    page = h.goto()
    page.wait_for_function("window.NoyvjCalm")
    page.evaluate("NoyvjCalm.bindCheckbox('#c'); 0")
    page.check("#c")
    assert page.evaluate("NoyvjCalm.isOn()") is True
    page.evaluate("NoyvjCalm.setOn(false)")
    assert page.is_checked("#c") is False


def test_no_timers_no_network_no_markup_injection(harness):
    counter = ("window.__timers = 0; for (const n of ['setTimeout', 'setInterval', 'requestAnimationFrame']) {"
               "const o = window[n]; window[n] = function () { window.__timers++; return o.apply(this, arguments); }; }")
    h = harness(init_scripts=[counter])
    h.pages["/t.html"] = PAGE
    page = h.goto()
    page.wait_for_function("window.NoyvjCalm")
    page.evaluate("NoyvjCalm.mount('#slot'); NoyvjCalm.setDock([{label:'<img src=x onerror=window.__pwned=1>'}]); NoyvjCalm.setOn(true); 0")
    assert page.evaluate("window.__timers") == 0 and h.api_calls == []
    assert page.evaluate("window.__pwned") is None
    assert "<img" in page.inner_text(".noyvj-calm-dock")  # shown as text


@pytest.mark.parametrize("theme", ["dark", "light"])
def test_it_works_in_both_themes_and_fits_a_small_phone(harness, theme):
    h = harness(size=(360, 640), touch=True)
    h.pages["/t.html"] = PAGE.replace('<html lang="en" >', f'<html lang="en" data-theme="{theme}">')
    page = h.goto()
    page.wait_for_function("window.NoyvjCalm")
    page.evaluate("NoyvjCalm.mount('#slot'); NoyvjCalm.setDock([{label:'Water'},{label:'Next'},{label:'More'}]); NoyvjCalm.setOn(true); 0")
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    assert h.errors == []


def test_more_contrast_turns_the_dim_off(harness):
    h = harness(media={"contrast": "more"})
    h.pages["/t.html"] = PAGE
    page = h.goto()
    page.wait_for_function("window.NoyvjCalm")
    page.evaluate("NoyvjCalm.setOn(true)")
    assert float(page.evaluate("getComputedStyle(document.querySelector('.noyvj-calm-dim')).opacity")) == 0
