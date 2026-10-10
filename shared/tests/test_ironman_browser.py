"""shared/ironman.js + ironman.css in headless Chromium (planning/TODO.md QI-53): an opt-in hard-fail
switch per game, never the default, with a plain explanation, a lock that says why, an
html[data-ironman] attribute, a change event, a badge and a guard around restore/undo/rewind actions.
The component is plumbing only: the game decides what Ironman means. Themes, 44 px, 360 px, reduced
motion, no timers, no network."""

import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from conftest import page_html  # noqa: E402

STYLE = ('<style>body{margin:0;padding:12px;font-family:system-ui;background:#12162a;color:#eee}'
         'html[data-theme="light"] body{background:#eef2fc;color:#1b2033}</style>')
PAGE = page_html(STYLE + '<link rel="stylesheet" href="/shared/ironman.css">',
                 '<h1>Game</h1><div id="head"></div><div id="slot"></div><button id="restore">Restore</button>'
                 '<script src="/shared/ironman.js"></script>')
PAGE_NO_LINK = page_html(STYLE, '<div id="slot"></div><script src="/shared/ironman.js"></script>')

SETUP = """() => {
  window.__locked = false; window.__changes = []; window.__events = []; window.__global = []; window.__restored = 0;
  document.addEventListener('noyvj-ironman-change', (e) => __events.push(e.detail));
  NoyvjIronman.onChange((on, game) => __global.push([on, game]));
  window.__sw = NoyvjIronman.mount('#slot', {game: 'medic', badgeName: 'Iron Medic', explain: 'A fainted crew member stays out.',
    canChange: () => !window.__locked, onChange: (on) => __changes.push(on)});
}"""

SWITCH = "#slot input[role='switch']"


def open_page(harness, page=PAGE, init=(), size=(1440, 900), theme=None, **kw):
    h = harness(size=size, init_scripts=list(init), **kw)
    h.pages["/t.html"] = page
    h.goto()
    if theme:
        h.page.evaluate("t => document.documentElement.setAttribute('data-theme', t)", theme)
    return h


def mount(h):
    h.page.evaluate(SETUP)
    return h


def state(h):
    return h.page.inner_text(".noyvj-ironman-state")


# --------------------------------------------------------------------------------------------
def test_off_by_default_with_a_labelled_switch_and_a_plain_explanation(harness):
    h = mount(open_page(harness))
    assert h.page.evaluate("NoyvjIronman.isOn('medic')") is False
    assert h.page.evaluate("localStorage.getItem('noyvj-ironman:medic')") is None
    assert h.page.get_attribute("html", "data-ironman") is None
    assert not h.page.is_checked(SWITCH) and state(h) == "Off"
    assert h.page.get_attribute(SWITCH, "role") == "switch"
    assert h.page.get_attribute(SWITCH, "type") == "checkbox"
    assert h.page.inner_text(".noyvj-ironman-title") == "Ironman mode"
    text = h.page.inner_text(".noyvj-ironman").lower()
    assert "no restoring" in text and "no rewinding" in text
    assert "optional" in text and "off by default" in text
    assert "iron medic badge" in text
    assert "a fainted crew member stays out." in text
    assert h.page.is_visible(".noyvj-ironman-explain")                               # always visible, not tucked away
    assert h.page.is_hidden(".noyvj-ironman-lock")
    # the switch is named by its label and described by the explanation
    assert h.page.evaluate("document.querySelector('label.noyvj-ironman-row').contains(document.querySelector('input[role=switch]'))")
    assert h.page.get_attribute(SWITCH, "aria-describedby").split()[0] == h.page.get_attribute(".noyvj-ironman-explain", "id")
    assert not h.errors


def test_default_label_and_badge_name(harness):
    h = open_page(harness)
    h.page.evaluate("() => NoyvjIronman.mount('#slot', {game: 'x', label: 'Hard mode'})")
    assert h.page.inner_text(".noyvj-ironman-title") == "Hard mode"
    assert "Ironman badge" in h.page.inner_text(".noyvj-ironman-explain")
    assert h.page.locator(".noyvj-ironman-explain--extra").count() == 0


def test_turning_it_on_sets_storage_attribute_event_and_callbacks(harness):
    h = mount(open_page(harness))
    h.page.check(SWITCH)
    assert h.page.evaluate("NoyvjIronman.isOn('medic')") is True
    assert h.page.evaluate("localStorage.getItem('noyvj-ironman:medic')") == "on"
    assert h.page.get_attribute("html", "data-ironman") == "true"
    assert state(h) == "On" and h.page.get_attribute(SWITCH, "aria-checked") == "true"
    assert h.page.evaluate("__events") == [{"game": "medic", "on": True}]
    assert h.page.evaluate("__changes") == [True] and h.page.evaluate("__global") == [[True, "medic"]]
    assert h.page.evaluate("NoyvjIronman.isOn('other')") is False                    # per game


def test_it_can_be_turned_off_before_a_run_starts_and_leaves_no_trace(harness):
    h = mount(open_page(harness))
    h.page.check(SWITCH)
    h.page.uncheck(SWITCH)
    assert h.page.evaluate("localStorage.getItem('noyvj-ironman:medic')") is None    # absent = off, never the string "off"
    assert h.page.get_attribute("html", "data-ironman") is None
    assert h.page.evaluate("__changes") == [True, False]
    assert h.page.evaluate("__events") == [{"game": "medic", "on": True}, {"game": "medic", "on": False}]


def test_locked_switch_is_disabled_and_says_why_and_cannot_be_flipped(harness):
    h = mount(open_page(harness))
    h.page.check(SWITCH)
    h.page.evaluate("__locked = true; __sw.refresh()")
    assert h.page.is_disabled(SWITCH)
    assert h.page.is_visible(".noyvj-ironman-lock")
    assert h.page.inner_text(".noyvj-ironman-lock").strip() == "Ironman can only be changed before a run starts."
    assert h.page.get_attribute(SWITCH, "aria-describedby").split()[-1] == h.page.get_attribute(".noyvj-ironman-lock", "id")
    h.page.click("label.noyvj-ironman-row", force=True)
    assert h.page.evaluate("NoyvjIronman.isOn('medic')") is True and h.page.is_checked(SWITCH)
    # a script that flips the checkbox anyway is put back
    h.page.evaluate("() => { const i = document.querySelector(\"input[role='switch']\"); i.disabled = false; i.checked = false; i.dispatchEvent(new Event('change', {bubbles: true})); }")
    assert h.page.evaluate("NoyvjIronman.isOn('medic')") is True and h.page.is_checked(SWITCH)
    # unlocked again: usable
    h.page.evaluate("__locked = false; __sw.refresh()")
    assert h.page.is_enabled(SWITCH) and h.page.is_hidden(".noyvj-ironman-lock")
    h.page.uncheck(SWITCH)
    assert h.page.evaluate("NoyvjIronman.isOn('medic')") is False


def test_locked_when_off_cannot_be_turned_on_either(harness):
    h = mount(open_page(harness))
    h.page.evaluate("__locked = true; __sw.refresh()")
    assert h.page.is_disabled(SWITCH) and not h.page.is_checked(SWITCH)
    assert "before a run starts" in h.page.inner_text(".noyvj-ironman-lock")
    assert h.page.evaluate("NoyvjIronman.isOn('medic')") is False


def test_without_can_change_the_switch_is_free_both_ways(harness):
    h = open_page(harness)
    h.page.evaluate("() => { window.__sw = NoyvjIronman.mount('#slot', {game: 'free'}); }")
    h.page.check(SWITCH)
    assert h.page.evaluate("NoyvjIronman.isOn('free')") is True
    h.page.uncheck(SWITCH)
    assert h.page.evaluate("NoyvjIronman.isOn('free')") is False


def test_a_throwing_can_change_locks_rather_than_breaking(harness):
    h = open_page(harness)
    h.page.evaluate("() => { NoyvjIronman.mount('#slot', {game: 'g', canChange: () => { throw new Error('boom'); }}); }")
    assert h.page.is_disabled(SWITCH) and not h.errors


def test_release_lets_the_game_turn_it_off_even_when_locked(harness):
    h = mount(open_page(harness))
    h.page.check(SWITCH)
    h.page.evaluate("__locked = true; __sw.refresh()")
    assert h.page.evaluate("NoyvjIronman.release('medic')") is True
    assert not h.page.is_checked(SWITCH) and state(h) == "Off" and h.page.is_disabled(SWITCH)
    assert h.page.evaluate("localStorage.getItem('noyvj-ironman:medic')") is None
    assert h.page.get_attribute("html", "data-ironman") is None
    assert h.page.evaluate("__changes") == [True, False]
    assert h.page.evaluate("NoyvjIronman.release('medic')") is False                  # nothing to release: no extra event
    assert h.page.evaluate("__events.length") == 2
    h.page.evaluate("__locked = false; __sw.refresh(); NoyvjIronman.refreshAll()")
    h.page.check(SWITCH)
    h.page.evaluate("__sw.release()")                                                 # the handle can release too
    assert not h.page.is_checked(SWITCH)


def test_the_choice_is_remembered_across_a_reload_and_sets_the_attribute_on_mount(harness):
    h = mount(open_page(harness))
    h.page.check(SWITCH)
    h.page.reload()
    assert h.page.get_attribute("html", "data-ironman") is None                       # nothing names a game until it mounts
    mount(h)
    assert h.page.is_checked(SWITCH) and state(h) == "On"
    assert h.page.get_attribute("html", "data-ironman") == "true"
    assert h.page.evaluate("__changes") == []                                         # restoring state is not a change


def test_a_second_tab_or_script_changing_it_is_picked_up_on_refresh(harness):
    h = mount(open_page(harness))
    h.page.evaluate("localStorage.setItem('noyvj-ironman:medic', 'on'); NoyvjIronman.refreshAll()")
    assert h.page.is_checked(SWITCH)
    h.page.evaluate("localStorage.setItem('noyvj-ironman:medic', 'something else'); NoyvjIronman.refreshAll()")
    assert not h.page.is_checked(SWITCH)                                              # only the exact value "on" counts


# ---- guard -----------------------------------------------------------------------------------
def test_guard_runs_the_action_when_off(harness):
    h = mount(open_page(harness))
    assert h.page.evaluate("NoyvjIronman.guard('medic', () => { __restored++; })") is True
    assert h.page.evaluate("__restored") == 1
    assert h.page.evaluate("NoyvjIronman.guard('medic', () => false)") is False       # the action itself declined
    assert h.page.evaluate("NoyvjIronman.guard('medic')") is True                     # nothing to run
    assert h.page.locator(".noyvj-ironman-notice").count() == 0                       # no message when it is allowed


def test_guard_blocks_announces_and_shows_the_same_words(harness):
    h = mount(open_page(harness))
    h.page.check(SWITCH)
    assert h.page.evaluate("NoyvjIronman.guard('medic', () => { __restored++; })") is False
    assert h.page.evaluate("__restored") == 0
    h.page.wait_for_function("document.querySelector('.noyvj-ironman-notice-text').textContent !== ''")
    assert h.page.inner_text(".noyvj-ironman-notice-text") == "Ironman is on: this cannot be undone."
    notice = ".noyvj-ironman-notice"
    assert h.page.get_attribute(notice, "role") == "status" and h.page.get_attribute(notice, "aria-live") == "polite"
    assert h.page.is_visible(notice)
    h.page.click(".noyvj-ironman-notice-close")
    assert h.page.is_hidden(notice)
    h.page.evaluate("NoyvjIronman.guard('medic', () => {}, {message: 'Rewinding is off in Ironman.'})")
    h.page.wait_for_function("document.querySelector('.noyvj-ironman-notice-text').textContent !== ''")
    assert h.page.inner_text(".noyvj-ironman-notice-text") == "Rewinding is off in Ironman."
    assert h.page.locator(".noyvj-ironman-notice").count() == 1                       # one shared notice, reused
    h.page.evaluate("NoyvjIronman.release('medic')")
    assert h.page.evaluate("NoyvjIronman.guard('medic', () => { __restored++; })") is True
    assert h.page.evaluate("__restored") == 1


def test_guard_works_with_a_real_button(harness):
    h = mount(open_page(harness))
    h.page.evaluate("document.getElementById('restore').onclick = () => NoyvjIronman.guard('medic', () => { __restored++; }); 0")
    h.page.click("#restore")
    assert h.page.evaluate("__restored") == 1
    h.page.check(SWITCH)
    h.page.click("#restore")
    assert h.page.evaluate("__restored") == 1


def test_guard_when_on_in_a_game_that_never_mounted_the_switch(harness):
    h = open_page(harness)
    h.page.evaluate("localStorage.setItem('noyvj-ironman:solo', 'on')")
    assert h.page.evaluate("NoyvjIronman.guard('solo', () => 1)") is False
    assert h.page.evaluate("NoyvjIronman.isOn('solo')") is True


# ---- badge -----------------------------------------------------------------------------------
def test_badge_is_a_shape_plus_text_element_the_game_can_place(harness):
    h = mount(open_page(harness))
    h.page.evaluate("""() => { document.getElementById('head').append(NoyvjIronman.badge('medic', {name: 'Iron Medic'}));
      document.getElementById('head').append(NoyvjIronman.badge('medic')); }""")
    assert h.page.evaluate("[...document.querySelectorAll('.noyvj-ironman-badge')].map(b => b.textContent)") == ["Iron Medic", "Ironman"]
    assert h.page.evaluate("getComputedStyle(document.querySelector('.noyvj-ironman-badge'), '::before').content") != "none"
    assert h.page.evaluate("getComputedStyle(document.querySelector('.noyvj-ironman-badge')).borderTopWidth") == "2px"
    assert h.page.evaluate("NoyvjIronman.badge('x') instanceof HTMLElement")
    assert h.page.evaluate("NoyvjIronman.badge('x', {name: '   '}).textContent") == "Ironman"


def test_text_is_text_never_markup(harness):
    h = open_page(harness)
    evil = '<img src=x onerror="window.__p=1"><b>x</b>'
    h.page.evaluate("""(e) => { NoyvjIronman.mount('#slot', {game: 'g', label: e, explain: e, badgeName: e});
      document.getElementById('head').append(NoyvjIronman.badge('g', {name: e}));
      localStorage.setItem('noyvj-ironman:g', 'on'); NoyvjIronman.guard('g', null, {message: e}); }""", evil)
    h.page.wait_for_function("document.querySelector('.noyvj-ironman-notice-text').textContent !== ''")
    assert h.page.locator("#slot img, #slot b, #head img, #head b, .noyvj-ironman-notice img, .noyvj-ironman-notice b").count() == 0
    assert h.page.evaluate("window.__p") is None
    assert evil in h.page.inner_text(".noyvj-ironman-title")
    assert not h.errors


# ---- events and listeners --------------------------------------------------------------------
def test_on_change_unsubscribe_and_a_throwing_listener(harness):
    h = mount(open_page(harness))
    h.page.evaluate("""() => { window.__a = []; window.__off = NoyvjIronman.onChange((on) => __a.push(on));
      NoyvjIronman.onChange(() => { throw new Error('listener bug'); }); }""")
    h.page.check(SWITCH)
    h.page.evaluate("__off()")
    h.page.uncheck(SWITCH)
    assert h.page.evaluate("__a") == [True]
    assert not h.errors
    assert h.page.evaluate("typeof NoyvjIronman.onChange('nope')") == "function"


def test_two_games_on_one_page_stay_separate(harness):
    h = open_page(harness)
    h.page.evaluate("""() => { document.getElementById('head').id = 'one'; const b = document.createElement('div'); b.id = 'two'; document.body.append(b);
      window.__a = NoyvjIronman.mount('#one', {game: 'a'}); window.__b = NoyvjIronman.mount('#two', {game: 'b'}); }""")
    h.page.check("#one input[role='switch']")
    assert h.page.evaluate("NoyvjIronman.isOn('a')") is True and h.page.evaluate("NoyvjIronman.isOn('b')") is False
    assert not h.page.is_checked("#two input[role='switch']")
    h.page.evaluate("__a.destroy(); NoyvjIronman.refreshAll()")
    assert h.page.locator(".noyvj-ironman").count() == 1


# ---- storage blocked -------------------------------------------------------------------------
BLOCK = """(() => { const f = () => { throw new DOMException('blocked', 'SecurityError'); };
  Object.defineProperty(window, 'localStorage', {get: f, configurable: true}); })()"""


def test_blocked_storage_is_tolerated_and_state_lasts_the_session(harness):
    h = open_page(harness, init=[BLOCK])
    mount(h)
    h.page.check(SWITCH)
    assert h.page.evaluate("NoyvjIronman.isOn('medic')") is True and not h.errors
    assert h.page.get_attribute("html", "data-ironman") == "true"
    assert h.page.evaluate("NoyvjIronman.guard('medic', () => 1)") is False
    h.page.evaluate("NoyvjIronman.release('medic')")
    assert h.page.evaluate("NoyvjIronman.isOn('medic')") is False and not h.page.is_checked(SWITCH)
    assert not h.errors


QUOTA = """(() => { Storage.prototype.setItem = function () { throw new DOMException('full', 'QuotaExceededError'); }; })()"""


def test_writes_that_fail_still_hold_for_the_session(harness):
    h = open_page(harness, init=[QUOTA])
    mount(h)
    h.page.check(SWITCH)
    assert h.page.evaluate("NoyvjIronman.isOn('medic')") is True and h.page.is_checked(SWITCH)
    h.page.uncheck(SWITCH)
    assert h.page.evaluate("NoyvjIronman.isOn('medic')") is False
    assert not h.errors


def test_links_its_own_stylesheet_when_the_page_forgot(harness):
    h = open_page(harness, page=PAGE_NO_LINK)
    mount(h)
    h.page.wait_for_function("getComputedStyle(document.querySelector('.noyvj-ironman')).borderTopWidth === '1px'")
    assert h.page.locator("link[href*='ironman.css']").count() == 1


def test_no_timers_no_network_no_console_noise(harness):
    counter = ("window.__timers = 0; for (const n of ['setTimeout', 'setInterval', 'requestAnimationFrame']) {"
               "const o = window[n]; window[n] = function () { window.__timers++; return o.apply(this, arguments); }; }")
    h = open_page(harness, init=[counter])
    mount(h)
    h.page.check(SWITCH)
    h.page.evaluate("NoyvjIronman.guard('medic', () => 1); __sw.refresh(); NoyvjIronman.release('medic'); NoyvjIronman.badge('medic')")
    assert h.page.evaluate("window.__timers") == 0
    assert h.api_calls == []
    assert not h.errors
    assert not [m for m in h.console if m[0] in ("error", "warning")]


# ---- keyboard --------------------------------------------------------------------------------
def test_works_from_the_keyboard_and_keeps_focus_on_the_switch(harness):
    h = mount(open_page(harness))
    h.page.focus(SWITCH)
    h.page.keyboard.press("Space")
    assert h.page.is_checked(SWITCH) and state(h) == "On"
    assert h.page.evaluate("document.activeElement.getAttribute('role')") == "switch"
    h.page.keyboard.press("Space")
    assert not h.page.is_checked(SWITCH)
    assert h.page.evaluate("document.activeElement.getAttribute('role')") == "switch"
    h.page.evaluate("__locked = true; __sw.refresh()")
    assert h.page.evaluate("document.activeElement === document.querySelector(\"input[role='switch']\")") is False   # disabled controls leave the tab order
    h.page.keyboard.press("Tab")
    assert h.page.evaluate("document.activeElement.getAttribute('role')") != "switch"


def test_guard_notice_close_button_is_keyboard_reachable(harness):
    h = mount(open_page(harness))
    h.page.check(SWITCH)
    h.page.evaluate("NoyvjIronman.guard('medic', () => 1)")
    h.page.focus(".noyvj-ironman-notice-close")
    h.page.keyboard.press("Enter")
    assert h.page.is_hidden(".noyvj-ironman-notice")


# ---- look: sizes, themes, reduced motion -----------------------------------------------------
@pytest.mark.parametrize("size", [(1440, 900), (360, 740)])
@pytest.mark.parametrize("theme", ["dark", "light"])
def test_fits_with_44px_targets_and_no_overflow(harness, size, theme):
    h = open_page(harness, size=size, touch=size[0] < 500, theme=theme)
    mount(h)
    h.page.check(SWITCH)
    h.page.evaluate("__locked = true; __sw.refresh(); NoyvjIronman.guard('medic', () => 1)")
    assert h.page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    for sel in (SWITCH, "label.noyvj-ironman-row", ".noyvj-ironman-notice-close"):
        w, ht = h.page.evaluate("(s) => { const r = document.querySelector(s).getBoundingClientRect(); return [r.width, r.height]; }", sel)
        assert w >= 44 and ht >= 44, sel
    box = h.page.evaluate("(() => { const r = document.querySelector('.noyvj-ironman').getBoundingClientRect(); return [r.left, r.right]; })()")
    assert box[0] >= 0 and box[1] <= size[0]
    notice = h.page.evaluate("(() => { const r = document.querySelector('.noyvj-ironman-notice').getBoundingClientRect(); return [r.left, r.right]; })()")
    assert notice[0] >= 0 and notice[1] <= size[0]
    assert h.page.evaluate("""[...document.querySelectorAll('.noyvj-ironman-explain, .noyvj-ironman-title')].every(e => e.scrollWidth <= e.clientWidth + 1)""")


def lum(css):
    r, g, b = [int(float(x)) for x in re.findall(r"[\d.]+", css)[:3]]
    f = lambda c: ((c / 255 + 0.055) / 1.055) ** 2.4 if c / 255 > 0.03928 else c / 255 / 12.92  # noqa: E731
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)


def test_light_and_dark_tokens_differ_and_text_is_legible(harness):
    seen = {}
    for theme in ("dark", "light"):
        h = mount(open_page(harness, theme=theme))
        h.page.check(SWITCH)
        seen[theme] = h.page.evaluate("""() => { const s = getComputedStyle(document.querySelector('.noyvj-ironman'));
          return [s.backgroundColor, s.color, getComputedStyle(document.querySelector('.noyvj-ironman-explain')).color,
                  getComputedStyle(document.querySelector('.noyvj-ironman-state')).color]; }""")
    assert seen["dark"] != seen["light"]
    for theme, (bg, fg, muted, on_state) in seen.items():
        page_bg = 0.01 if theme == "dark" else 0.85
        lb = lum(bg) * 0.78 + page_bg * 0.22 if "rgba" in bg else lum(bg)
        for colour in (fg, muted, on_state):
            lf = lum(colour)
            assert (max(lb, lf) + 0.05) / (min(lb, lf) + 0.05) >= 4.5, (theme, colour)


def test_os_light_preference_is_followed_without_a_theme_attribute(harness):
    h = harness(media={"color_scheme": "light"})
    h.pages["/t.html"] = PAGE
    h.goto()
    mount(h)
    assert h.page.evaluate("getComputedStyle(document.querySelector('.noyvj-ironman')).color") == "rgb(27, 32, 51)"


def test_state_is_not_colour_alone(harness):
    h = mount(open_page(harness))
    h.page.evaluate("document.documentElement.setAttribute('data-reduced-motion', 'true')")   # no mid-slide measurements
    off = h.page.evaluate("(() => { const k = document.querySelector('.noyvj-ironman-knob').getBoundingClientRect(); const t = document.querySelector('.noyvj-ironman-track').getBoundingClientRect(); return k.left - t.left; })()")
    h.page.check(SWITCH)
    on = h.page.evaluate("(() => { const k = document.querySelector('.noyvj-ironman-knob').getBoundingClientRect(); const t = document.querySelector('.noyvj-ironman-track').getBoundingClientRect(); return k.left - t.left; })()")
    assert on - off > 15                                                              # the knob moves
    assert state(h) == "On"                                                           # and the word changes
    assert h.page.evaluate("getComputedStyle(document.querySelector('.noyvj-ironman')).borderTopWidth") == "2px"
    h.page.evaluate("__locked = true; __sw.refresh()")
    assert h.page.evaluate("getComputedStyle(document.querySelector('.noyvj-ironman-track')).borderTopStyle") == "dashed"   # locked has a shape cue too
    assert h.page.evaluate("getComputedStyle(document.querySelector('.noyvj-ironman-lock'), '::before').content") != "none"


def test_knob_motion_only_when_allowed(harness):
    h = mount(open_page(harness))
    css = "getComputedStyle(document.querySelector('.noyvj-ironman-knob')).transitionDuration"
    assert h.page.evaluate(css) != "0s"
    h.page.evaluate("document.documentElement.setAttribute('data-reduced-motion', 'true')")
    assert h.page.evaluate(css) == "0s"
    os_reduced = harness(media={"reduced_motion": "reduce"})
    os_reduced.pages["/t.html"] = PAGE
    os_reduced.goto()
    mount(os_reduced)
    assert os_reduced.page.evaluate(css) == "0s"
    os_reduced.page.check(SWITCH)                                                     # works the same without motion
    assert os_reduced.page.evaluate("NoyvjIronman.isOn('medic')") is True


def test_hidden_attribute_wins_over_class_display(harness):
    h = mount(open_page(harness))
    assert h.page.evaluate("getComputedStyle(document.querySelector('.noyvj-ironman-lock')).display") == "none"
