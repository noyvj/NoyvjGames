"""shared/night-mode.js + night-mode.css in headless Chromium (planning/TODO.md QI-52): off by default,
three modes (off, auto, on) and three strengths, the auto window wraps midnight, the clock is read on load
and when the tab comes back (no timers), the overlay is one aria-hidden click-through element, settings
persist and tolerate blocked storage, the settings control works from the keyboard, themes, 360 px,
no network, no console errors."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from conftest import page_html  # noqa: E402

STYLE = ('<style>body{margin:0;padding:12px;font-family:system-ui;background:#12162a;color:#eee}'
         'html[data-theme="light"] body{background:#eef2fc;color:#1b2033}</style>')
LINK = '<link rel="stylesheet" href="/shared/night-mode.css">'
PAGE = page_html(STYLE + LINK, '<h1>Game</h1><button id="btn">Press</button><div id="slot"></div>'
                 '<script src="/shared/night-mode.js"></script>')


def at(hour, minute=0):
    return f"() => new Date(2026, 9, 10, {hour}, {minute}, 0)"


def load(harness, **kw):
    h = harness(**kw)
    h.pages["/t.html"] = PAGE
    page = h.goto()
    page.wait_for_function("window.NoyvjNight")
    return h, page


def test_it_is_off_by_default_even_at_night(harness):
    h, page = load(harness)
    page.evaluate(f"NoyvjNight.configure({{now: {at(23)}}})")
    assert page.evaluate("NoyvjNight.getMode()") == "off"
    assert page.evaluate("NoyvjNight.isActive()") is False
    assert page.get_attribute("html", "data-night") == "off"
    assert h.errors == []


def test_auto_follows_the_clock_and_wraps_midnight(harness):
    h, page = load(harness)
    page.evaluate("NoyvjNight.setMode('auto')")
    for hour, expected in ((12, False), (21, False), (22, True), (23, True), (0, True), (5, True), (6, False), (14, False)):
        page.evaluate(f"NoyvjNight.configure({{now: {at(hour)}}})")
        assert page.evaluate("NoyvjNight.isActive()") is expected, hour
        assert page.get_attribute("html", "data-night") == ("on" if expected else "off"), hour
    page.evaluate(f"NoyvjNight.configure({{start: 20, end: 23, now: {at(21)}}})")  # a window that does not wrap
    assert page.evaluate("NoyvjNight.isActive()") is True
    page.evaluate(f"NoyvjNight.configure({{now: {at(23, 30)}}})")
    assert page.evaluate("NoyvjNight.isActive()") is False


def test_on_ignores_the_clock_and_off_turns_it_back(harness):
    h, page = load(harness)
    page.evaluate(f"NoyvjNight.configure({{now: {at(12)}}})")
    page.evaluate("NoyvjNight.setMode('on')")
    assert page.get_attribute("html", "data-night") == "on"
    page.evaluate("NoyvjNight.setMode('off')")
    assert page.get_attribute("html", "data-night") == "off"
    assert page.evaluate("NoyvjNight.setMode('banana')") is False
    assert page.evaluate("NoyvjNight.getMode()") == "off"


def test_the_overlay_is_one_hidden_click_through_element_and_tints_when_on(harness):
    h, page = load(harness)
    assert page.locator(".noyvj-night-overlay").count() == 1
    assert page.get_attribute(".noyvj-night-overlay", "aria-hidden") == "true"
    assert page.evaluate("getComputedStyle(document.querySelector('.noyvj-night-overlay')).pointerEvents") == "none"
    assert float(page.evaluate("getComputedStyle(document.querySelector('.noyvj-night-overlay')).opacity")) == 0
    page.evaluate("NoyvjNight.setMode('on')")
    page.wait_for_function("parseFloat(getComputedStyle(document.querySelector('.noyvj-night-overlay')).opacity) > 0.5")
    page.evaluate("NoyvjNight.apply()")
    assert page.locator(".noyvj-night-overlay").count() == 1  # never a second one
    page.click("#btn")  # clicks pass through to the page
    assert page.evaluate("getComputedStyle(document.querySelector('.noyvj-night-overlay')).mixBlendMode") == "multiply"


def test_levels_change_the_strength_and_persist(harness):
    h, page = load(harness, media={"reduced_motion": "reduce"})
    page.evaluate("NoyvjNight.setMode('on')")
    seen = {}
    for level in ("soft", "medium", "deep"):
        assert page.evaluate(f"NoyvjNight.setLevel('{level}')") is True
        seen[level] = float(page.evaluate("getComputedStyle(document.querySelector('.noyvj-night-overlay')).opacity"))
        assert page.get_attribute("html", "data-night-level") == level
    assert seen["soft"] < seen["medium"] < seen["deep"]
    assert page.evaluate("NoyvjNight.setLevel('blinding')") is False
    page.reload()
    page.wait_for_function("window.NoyvjNight")
    assert page.evaluate("NoyvjNight.getLevel()") == "deep" and page.evaluate("NoyvjNight.getMode()") == "on"


def test_the_clock_is_read_when_the_tab_comes_back_not_on_a_timer(harness):
    counter = ("window.__timers = 0; for (const n of ['setTimeout', 'setInterval', 'requestAnimationFrame']) {"
               "const o = window[n]; window[n] = function () { window.__timers++; return o.apply(this, arguments); }; }")
    h = harness(init_scripts=[counter])
    h.pages["/t.html"] = PAGE
    page = h.goto()
    page.wait_for_function("window.NoyvjNight")
    page.evaluate("NoyvjNight.setMode('auto')")
    page.evaluate(f"NoyvjNight.configure({{now: {at(12)}}})")
    assert page.get_attribute("html", "data-night") == "off"
    page.evaluate("window.__clock = new Date(2026, 9, 10, 23, 0, 0); NoyvjNight.configure({now: () => window.__clock})")
    page.evaluate("window.__clock = new Date(2026, 9, 10, 12, 0, 0); NoyvjNight.apply()")
    assert page.get_attribute("html", "data-night") == "off"
    page.evaluate("window.__clock = new Date(2026, 9, 10, 23, 30, 0); window.dispatchEvent(new Event('focus'))")
    assert page.get_attribute("html", "data-night") == "on"
    assert page.evaluate("window.__timers") == 0


def test_events_and_listeners_fire_once_per_real_change(harness):
    h, page = load(harness)
    page.evaluate("window.__log = []; document.addEventListener('noyvj-night-change', e => __log.push(e.detail));"
                  " NoyvjNight.onChange(s => __log.push('cb:' + s.mode)); 0")
    page.evaluate("NoyvjNight.setMode('on'); NoyvjNight.setMode('on'); NoyvjNight.setLevel('deep')")
    log = page.evaluate("__log")
    modes = [x for x in log if isinstance(x, dict)]
    assert [m["mode"] for m in modes] == ["on", "on"] and modes[-1]["level"] == "deep" and modes[0]["active"] is True
    assert log.count("cb:on") == 2


def test_blocked_storage_still_works_for_this_page(harness):
    h = harness(init_scripts=["Object.defineProperty(window, 'localStorage', {get(){ throw new Error('blocked'); }});"])
    h.pages["/t.html"] = PAGE
    page = h.goto()
    page.wait_for_function("window.NoyvjNight")
    assert page.evaluate("NoyvjNight.getMode()") == "off"
    page.evaluate("NoyvjNight.setMode('on')")
    assert page.evaluate("NoyvjNight.isActive()") is True
    assert h.errors == []


def test_the_settings_control_shows_the_choices_explains_and_is_keyboard_usable(harness):
    h, page = load(harness)
    page.evaluate(f"NoyvjNight.configure({{now: {at(12)}}}); NoyvjNight.mount('#slot'); 0")
    assert "off by default" in page.inner_text(".noyvj-night-control").lower()
    labels = page.eval_on_selector_all(".noyvj-night-control select:first-of-type option", "els => els.map(e => e.textContent)")
    assert labels == ["Off", "Automatic (after 10pm)", "Always on"]
    mode = page.locator(".noyvj-night-control select").first
    page.focus("#btn")
    page.keyboard.press("Tab")  # the first control in the panel is reachable from the keyboard
    assert page.evaluate("document.activeElement.tagName") == "SELECT"
    mode.select_option("auto")
    assert page.evaluate("NoyvjNight.getMode()") == "auto"
    assert "Automatic" in page.inner_text(".noyvj-night-state")
    mode.select_option("on")
    assert page.get_attribute("html", "data-night") == "on"
    assert page.get_attribute(".noyvj-night-state", "aria-live") == "polite"
    box = page.locator(".noyvj-night-control select").first.bounding_box()
    assert box["height"] >= 44
    assert h.errors == []


def test_bind_select_keeps_a_games_own_select_in_step(harness):
    h = harness()
    h.pages["/t.html"] = PAGE.replace('<div id="slot"></div>', '<select id="m"><option>off</option><option>auto</option><option>on</option></select>'
                                      '<select id="l"><option>soft</option><option>medium</option><option>deep</option></select>')
    page = h.goto()
    page.wait_for_function("window.NoyvjNight")
    page.evaluate("NoyvjNight.bindSelect('#m'); NoyvjNight.bindSelect('#l', {level: true}); 0")
    page.select_option("#m", "on")
    page.select_option("#l", "deep")
    assert page.evaluate("NoyvjNight.getMode()") == "on" and page.evaluate("NoyvjNight.getLevel()") == "deep"
    page.evaluate("NoyvjNight.setMode('off')")
    assert page.input_value("#m") == "off"


@pytest.mark.parametrize("theme", ["dark", "light"])
def test_it_works_under_both_themes(harness, theme):
    h = harness()
    h.pages["/t.html"] = PAGE.replace("<html lang=\"en\" >", f'<html lang="en" data-theme="{theme}">')
    page = h.goto()
    page.wait_for_function("window.NoyvjNight")
    page.evaluate("NoyvjNight.setMode('on')")
    assert page.get_attribute("html", "data-night") == "on"
    assert h.errors == []


def test_it_fits_a_small_phone_and_makes_no_requests_beyond_its_own_files(harness):
    h = harness(size=(360, 640), touch=True)
    h.pages["/t.html"] = PAGE
    page = h.goto()
    page.wait_for_function("window.NoyvjNight")
    page.evaluate("NoyvjNight.mount('#slot'); NoyvjNight.setMode('on'); 0")
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    assert h.api_calls == [] and h.errors == []


def test_more_contrast_turns_the_tint_off(harness):
    h = harness(media={"contrast": "more"})
    h.pages["/t.html"] = PAGE
    page = h.goto()
    page.wait_for_function("window.NoyvjNight")
    page.evaluate("NoyvjNight.setMode('on')")
    assert float(page.evaluate("getComputedStyle(document.querySelector('.noyvj-night-overlay')).opacity")) == 0
