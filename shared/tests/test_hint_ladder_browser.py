"""shared/hint-ladder.js + hint-ladder.css in headless Chromium (planning/TODO.md QI-54): a nudge, then a
hint, then the answer, one button, an inline confirmation before the answer, labelled rungs that stay
visible, a silent reset when the game moves to another puzzle, per-game counts, an on/off hook, themes,
44 px, 360 px, reduced motion, no timers, no network. The component never decides a rule: it only shows
what the game's getPuzzle() says."""

import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from conftest import page_html  # noqa: E402

STYLE = ('<style>body{margin:0;padding:12px;font-family:system-ui;background:#12162a;color:#eee}'
         'html[data-theme="light"] body{background:#eef2fc;color:#1b2033}</style>')
PAGE = page_html(STYLE + '<link rel="stylesheet" href="/shared/hint-ladder.css">',
                 '<h1>Game</h1><div id="slot"></div><label><input type="checkbox" id="opt"> Show hints</label>'
                 '<script src="/shared/hint-ladder.js"></script>')
PAGE_NO_LINK = page_html(STYLE, '<div id="slot"></div><script src="/shared/hint-ladder.js"></script>')

P1 = {"id": "L1", "nudge": "Look at the right-hand wire.", "hint": "An AND gate comes first.", "answer": "AND, then NOT."}
P2 = {"id": "L2", "nudge": "Second nudge.", "hint": "Second hint.", "answer": "Second answer."}

SETUP = """(p) => {
  window.__puzzle = p; window.__revealed = [];
  window.__events = []; document.addEventListener('noyvj-hints-reveal', (e) => __events.push(e.detail));
  window.__ladder = NoyvjHints.mount('#slot', {game: 'logic', getPuzzle: () => window.__puzzle,
    onReveal: (rung, id) => __revealed.push([rung, id])});
}"""


def open_page(harness, page=PAGE, init=(), size=(1440, 900), theme=None, **kw):
    h = harness(size=size, init_scripts=list(init), **kw)
    h.pages["/t.html"] = page
    h.goto()
    if theme:
        h.page.evaluate("t => document.documentElement.setAttribute('data-theme', t)", theme)
    return h


def mount(h, puzzle=P1):
    h.page.evaluate(SETUP, puzzle)
    return h


def button(h):
    return h.page.evaluate("""() => { const b = document.querySelector('.noyvj-hints-ask');
      return b.hidden ? null : b.textContent; }""")


def press(h):
    h.page.click(".noyvj-hints-ask")


def shown(h):
    return h.page.evaluate("[...document.querySelectorAll('.noyvj-hints-item')].map(li => "
                           "[li.querySelector('.noyvj-hints-label').textContent, li.querySelector('.noyvj-hints-text').textContent])")


def reveal_all(h):
    press(h)
    press(h)
    press(h)
    h.page.click(".noyvj-hints-yes")


# --------------------------------------------------------------------------------------------
def test_starts_with_one_button_and_no_hint_shown(harness):
    h = mount(open_page(harness))
    assert h.page.is_visible(".noyvj-hints")
    assert button(h) == "Need a hint?"
    assert shown(h) == []
    assert h.page.is_hidden(".noyvj-hints-list") and h.page.is_hidden(".noyvj-hints-confirm")
    assert h.page.inner_text(".noyvj-hints-tally") == "0 of 3 shown"
    assert h.page.inner_text(".noyvj-hints-title") == "Hints"
    assert h.page.evaluate("__ladder.rungShown()") == 0 and h.page.evaluate("__ladder.used()") == []
    assert h.page.inner_text(".noyvj-hints-sr") == ""                              # nothing is said before a press
    assert not h.errors


def test_rungs_come_in_order_with_labels_and_button_text(harness):
    h = mount(open_page(harness))
    press(h)
    assert shown(h) == [["Nudge", P1["nudge"]]]
    assert button(h) == "Another hint"
    press(h)
    assert shown(h) == [["Nudge", P1["nudge"]], ["Hint", P1["hint"]]]
    assert button(h) == "Show the answer"
    assert h.page.inner_text(".noyvj-hints-tally") == "2 of 3 shown"
    assert h.page.evaluate("__ladder.used()") == ["nudge", "hint"] and h.page.evaluate("__ladder.rungShown()") == 2
    assert h.page.is_hidden(".noyvj-hints-confirm")                                # not asked until the answer is next pressed
    assert h.page.evaluate("__revealed") == [["nudge", "L1"], ["hint", "L1"]]


def test_the_answer_asks_once_inline_and_keeps_every_rung_visible(harness):
    h = mount(open_page(harness))
    press(h)
    press(h)
    press(h)                                                                        # asks, does not reveal
    assert shown(h)[-1][0] == "Hint"
    assert h.page.is_visible(".noyvj-hints-confirm") and button(h) is None
    assert h.page.evaluate("document.querySelector('.noyvj-hints-confirm').closest('dialog, [aria-modal]')") is None
    assert h.page.evaluate("document.querySelector('.noyvj-hints-confirm').getAttribute('role')") == "group"
    assert h.page.evaluate("document.activeElement.className") == "noyvj-hints-no"   # focus lands on the safe choice
    assert "Show the answer?" in h.page.inner_text(".noyvj-hints-question")
    assert h.page.evaluate("__revealed.length") == 2
    h.page.click(".noyvj-hints-yes")
    assert shown(h) == [["Nudge", P1["nudge"]], ["Hint", P1["hint"]], ["Answer", P1["answer"]]]
    assert h.page.is_hidden(".noyvj-hints-confirm") and button(h) is None           # the ladder is complete
    assert h.page.evaluate("__ladder.used()") == ["nudge", "hint", "answer"]
    assert h.page.evaluate("document.activeElement.classList.contains('noyvj-hints-item')")   # focus not lost to the body
    assert h.page.inner_text(".noyvj-hints-tally") == "3 of 3 shown"


def test_not_yet_cancels_and_returns_focus_to_the_button(harness):
    h = mount(open_page(harness))
    press(h)
    press(h)
    press(h)
    h.page.click(".noyvj-hints-no")
    assert h.page.is_hidden(".noyvj-hints-confirm") and button(h) == "Show the answer"
    assert h.page.evaluate("document.activeElement.className") == "noyvj-hints-ask"
    assert h.page.locator(".noyvj-hints-item").count() == 2
    press(h)
    h.page.keyboard.press("Escape")                                                 # Escape also cancels
    assert h.page.is_hidden(".noyvj-hints-confirm") and h.page.locator(".noyvj-hints-item").count() == 2
    assert h.page.evaluate("document.activeElement.className") == "noyvj-hints-ask"


def test_confirm_answer_false_shows_the_answer_straight_away(harness):
    h = open_page(harness)
    h.page.evaluate("""(p) => { window.__puzzle = p; window.__ladder = NoyvjHints.mount('#slot', {game: 'g', getPuzzle: () => __puzzle, confirmAnswer: false}); }""", P1)
    press(h)
    press(h)
    press(h)
    assert [r[0] for r in shown(h)] == ["Nudge", "Hint", "Answer"]


def test_missing_rungs_just_shorten_the_ladder(harness):
    h = open_page(harness)
    mount(h, {"id": "a", "hint": "Only a hint."})
    assert button(h) == "Need a hint?" and h.page.inner_text(".noyvj-hints-tally") == "0 of 1 shown"
    press(h)
    assert shown(h) == [["Hint", "Only a hint."]] and button(h) is None
    h.page.evaluate("__ladder.reset(); __puzzle = {id: 'b', nudge: 'N', answer: 'A'}; __ladder.refresh()")
    assert h.page.inner_text(".noyvj-hints-tally") == "0 of 2 shown"
    press(h)
    assert button(h) == "Show the answer"                                           # next is the answer, after a nudge
    press(h)
    assert h.page.is_visible(".noyvj-hints-confirm")
    h.page.click(".noyvj-hints-yes")
    assert shown(h) == [["Nudge", "N"], ["Answer", "A"]]
    # an answer-only puzzle starts with the plain entry label and then asks
    h.page.evaluate("__puzzle = {id: 'c', answer: 'Z'}; __ladder.refresh()")
    assert button(h) == "Need a hint?"
    press(h)
    assert h.page.is_visible(".noyvj-hints-confirm") and shown(h) == []
    h.page.click(".noyvj-hints-yes")
    assert shown(h) == [["Answer", "Z"]]
    # no usable rung at all, no puzzle, an unusable puzzle, or a throwing getPuzzle: hidden, never broken
    for bad in ("{id: 'd'}", "{id: 'e', nudge: '  ', hint: 5}", "null", "{nudge: 'no id'}", "'nonsense'"):
        h.page.evaluate(f"__puzzle = {bad}; __ladder.refresh()")
        if bad == "{id: 'e', nudge: '  ', hint: 5}":
            assert shown(h) == [] and h.page.is_visible(".noyvj-hints")             # the numeric hint counts as a rung
        else:
            assert h.page.is_hidden(".noyvj-hints"), bad
    assert not h.errors


def test_a_throwing_getpuzzle_hides_the_ladder(harness):
    h = open_page(harness)
    h.page.evaluate("""() => { window.__ladder = NoyvjHints.mount('#slot', {game: 'g', getPuzzle: () => { throw new Error('boom'); }}); }""")
    assert h.page.is_hidden(".noyvj-hints") and not h.errors


def test_a_different_puzzle_id_resets_silently_and_the_same_id_keeps_state(harness):
    h = mount(open_page(harness))
    press(h)
    press(h)
    assert h.page.locator(".noyvj-hints-item").count() == 2
    h.page.evaluate("__ladder.refresh(); __ladder.refresh()")                       # same id: nothing changes
    assert h.page.locator(".noyvj-hints-item").count() == 2
    h.page.evaluate("__puzzle = null; __ladder.refresh()")                          # a transient null keeps it too
    assert h.page.is_hidden(".noyvj-hints")
    h.page.evaluate("__puzzle = " + repr(P1).replace("'", '"') + "; __ladder.refresh()")
    assert h.page.locator(".noyvj-hints-item").count() == 2
    h.page.wait_for_function("document.querySelector('.noyvj-hints-sr').textContent !== ''")
    h.page.evaluate("document.querySelector('.noyvj-hints-sr').textContent = ''")
    h.page.evaluate("__puzzle = " + repr(P2).replace("'", '"') + "; __ladder.refresh()")
    assert shown(h) == [] and button(h) == "Need a hint?"
    assert h.page.evaluate("__ladder.rungShown()") == 0
    assert h.page.inner_text(".noyvj-hints-sr") == ""                               # silent
    assert h.page.evaluate("__events.length") == 2                                  # no event for a reset
    press(h)
    assert shown(h) == [["Nudge", "Second nudge."]]


def test_reset_hides_the_rungs_again_but_keeps_the_counts(harness):
    h = mount(open_page(harness))
    press(h)
    h.page.evaluate("__ladder.reset()")
    assert shown(h) == [] and h.page.evaluate("__ladder.used()") == []
    assert button(h) == "Need a hint?"
    assert h.page.evaluate("NoyvjHints.stats('logic')") == {"nudges": 1, "hints": 0, "answers": 0, "puzzles": 1}


def test_reveals_are_announced_politely_and_the_first_paint_is_silent(harness):
    h = mount(open_page(harness))
    live = ".noyvj-hints-sr"
    assert h.page.get_attribute(live, "role") == "status" and h.page.get_attribute(live, "aria-live") == "polite"
    press(h)
    h.page.wait_for_function("document.querySelector('.noyvj-hints-sr').textContent !== ''")
    assert h.page.evaluate("document.querySelector('.noyvj-hints-sr').textContent") == "Nudge: Look at the right-hand wire."
    press(h)
    h.page.wait_for_function("document.querySelector('.noyvj-hints-sr').textContent.startsWith('Hint')")
    press(h)
    h.page.click(".noyvj-hints-yes")
    h.page.wait_for_function("document.querySelector('.noyvj-hints-sr').textContent.startsWith('Answer')")
    assert h.page.get_attribute(".noyvj-hints-list", "aria-live") is None           # only one live region speaks


def test_semantics_section_ordered_list_and_text_labels(harness):
    h = mount(open_page(harness))
    press(h)
    assert h.page.evaluate("document.querySelector('.noyvj-hints').tagName") == "SECTION"
    title_id = h.page.get_attribute(".noyvj-hints", "aria-labelledby")
    assert h.page.inner_text("#" + title_id) == "Hints"
    assert h.page.evaluate("document.querySelector('.noyvj-hints-list').tagName") == "OL"
    assert h.page.evaluate("[...document.querySelectorAll('.noyvj-hints-list > *')].every(e => e.tagName === 'LI')")
    assert h.page.get_attribute(".noyvj-hints", "tabindex") == "-1"
    h.page.evaluate("__ladder.focus()")
    assert h.page.evaluate("document.activeElement.classList.contains('noyvj-hints')")
    assert h.page.evaluate("document.querySelector('.noyvj-hints-ask').tagName") == "BUTTON"


def test_events_and_callbacks_carry_game_id_and_rung(harness):
    h = mount(open_page(harness))
    press(h)
    press(h)
    press(h)
    h.page.click(".noyvj-hints-yes")
    assert h.page.evaluate("__events") == [{"game": "logic", "id": "L1", "rung": r} for r in ("nudge", "hint", "answer")]
    assert h.page.evaluate("__revealed") == [["nudge", "L1"], ["hint", "L1"], ["answer", "L1"]]
    h.page.evaluate("""() => { NoyvjHints.mount('#slot', {game: 'x', getPuzzle: () => ({id: 'q', nudge: 'n'}), onReveal: () => { throw new Error('game bug'); }}); }""")
    h.page.locator(".noyvj-hints-ask").nth(1).click()
    assert not h.errors                                                             # a throwing callback does not break the ladder


def test_texts_are_text_never_markup(harness):
    h = open_page(harness)
    evil = '<img src=x onerror="window.__p=1"> <b>bold</b>'
    mount(h, {"id": "<i>x</i>", "nudge": evil, "hint": evil, "answer": evil})
    reveal_all(h)
    assert h.page.locator("#slot img, #slot b, #slot i").count() == 0
    assert h.page.evaluate("window.__p") is None
    assert evil in h.page.inner_text(".noyvj-hints-item[data-rung='answer'] .noyvj-hints-text")
    assert h.page.evaluate("document.querySelector('.noyvj-hints-sr').textContent").startswith("Answer: <img")
    assert not h.errors


# ---- the per-game counts ---------------------------------------------------------------------
def test_stats_count_puzzles_per_rung_and_persist(harness):
    h = mount(open_page(harness))
    assert h.page.evaluate("NoyvjHints.stats('logic')") == {"nudges": 0, "hints": 0, "answers": 0, "puzzles": 0}
    press(h)                                                                        # L1: nudge
    h.page.evaluate("__puzzle = " + repr(P2).replace("'", '"') + "; __ladder.refresh()")
    press(h)
    press(h)                                                                        # L2: nudge, hint
    h.page.evaluate("__puzzle = {id: 'L3', answer: 'x'}; __ladder.refresh()")
    press(h)
    h.page.click(".noyvj-hints-yes")                                                # L3: answer only
    assert h.page.evaluate("NoyvjHints.stats('logic')") == {"nudges": 3, "hints": 2, "answers": 1, "puzzles": 3}
    raw = h.page.evaluate("JSON.parse(localStorage.getItem('noyvj-hints:logic'))")
    assert raw["puzzles"] == {"L1": 1, "L2": 2, "L3": 3}
    # re-using the same rung again does not count a puzzle twice
    h.page.evaluate("__puzzle = " + repr(P1).replace("'", '"') + "; __ladder.refresh()")
    press(h)
    assert h.page.evaluate("NoyvjHints.stats('logic')")["puzzles"] == 3
    # another game is separate
    assert h.page.evaluate("NoyvjHints.stats('other')") == {"nudges": 0, "hints": 0, "answers": 0, "puzzles": 0}
    h.page.reload()
    assert h.page.evaluate("NoyvjHints.stats('logic')") == {"nudges": 3, "hints": 2, "answers": 1, "puzzles": 3}


def test_stats_are_capped_at_500_ids_dropping_the_oldest(harness):
    h = mount(open_page(harness))
    h.page.evaluate("""() => { for (let i = 0; i < 520; i++) { __puzzle = {id: String(i), nudge: 'n'}; __ladder.refresh();
      document.querySelector('.noyvj-hints-ask').click(); } }""")
    st = h.page.evaluate("NoyvjHints.stats('logic')")
    assert st["puzzles"] == 500 and st["nudges"] == 500
    raw = h.page.evaluate("JSON.parse(localStorage.getItem('noyvj-hints:logic'))")
    assert len(raw["puzzles"]) == 500 and "0" not in raw["puzzles"] and "519" in raw["puzzles"] and "20" in raw["puzzles"]
    assert "19" not in raw["puzzles"]


def test_stats_ignore_corrupt_storage(harness):
    h = open_page(harness)
    h.page.evaluate("localStorage.setItem('noyvj-hints:logic', '{not json')")
    assert h.page.evaluate("NoyvjHints.stats('logic')") == {"nudges": 0, "hints": 0, "answers": 0, "puzzles": 0}
    h.page.evaluate("localStorage.setItem('noyvj-hints:logic', JSON.stringify({puzzles: {a: 2, b: 9, c: 'x', d: 3}}))")
    assert h.page.evaluate("NoyvjHints.stats('logic')") == {"nudges": 2, "hints": 2, "answers": 1, "puzzles": 2}
    mount(h)
    press(h)                                                                        # still works on top of that data
    assert h.page.evaluate("NoyvjHints.stats('logic')")["puzzles"] == 3


BLOCK = """(() => { const f = () => { throw new DOMException('blocked', 'SecurityError'); };
  Object.defineProperty(window, 'localStorage', {get: f, configurable: true}); })()"""


def test_blocked_storage_is_tolerated_and_counts_stay_in_memory(harness):
    h = open_page(harness, init=[BLOCK])
    mount(h)
    press(h)
    press(h)
    assert shown(h)[-1][0] == "Hint" and not h.errors
    assert h.page.evaluate("NoyvjHints.stats('logic')") == {"nudges": 1, "hints": 1, "answers": 0, "puzzles": 1}
    h.page.evaluate("__ladder.setEnabled(false)")                                   # the switch works without storage too
    assert h.page.is_hidden(".noyvj-hints") and h.page.evaluate("__ladder.isEnabled()") is False
    assert not h.errors


# ---- the settings switch ---------------------------------------------------------------------
def test_enabled_switch_hides_remembers_and_comes_back_with_state(harness):
    h = mount(open_page(harness))
    press(h)
    h.page.evaluate("__ladder.setEnabled(false)")
    assert h.page.is_hidden(".noyvj-hints") and h.page.evaluate("__ladder.isEnabled()") is False
    assert h.page.evaluate("localStorage.getItem('noyvj-hints-pref:logic')") == "off"
    h.page.evaluate("__ladder.setEnabled(true)")
    assert h.page.is_visible(".noyvj-hints") and h.page.locator(".noyvj-hints-item").count() == 1
    assert h.page.evaluate("localStorage.getItem('noyvj-hints-pref:logic')") == "on"
    h.page.evaluate("__ladder.setEnabled(false)")
    h.page.reload()
    mount(h)
    assert h.page.is_hidden(".noyvj-hints") and h.page.evaluate("__ladder.isEnabled()") is False
    h.page.evaluate("__ladder.setEnabled(true, {persist: false})")
    assert h.page.evaluate("localStorage.getItem('noyvj-hints-pref:logic')") == "off"


def test_enabled_option_overrides_the_stored_choice(harness):
    h = open_page(harness)
    h.page.evaluate("localStorage.setItem('noyvj-hints-pref:logic', 'off')")
    h.page.evaluate("""(p) => { window.__ladder = NoyvjHints.mount('#slot', {game: 'logic', getPuzzle: () => p, enabled: true}); }""", P1)
    assert h.page.is_visible(".noyvj-hints")


def test_bind_checkbox_two_way(harness):
    h = mount(open_page(harness))
    h.page.evaluate("() => { window.__unbind = NoyvjHints.bindCheckbox(__ladder, '#opt'); }")
    assert h.page.is_checked("#opt")
    h.page.uncheck("#opt")
    assert h.page.is_hidden(".noyvj-hints")
    h.page.check("#opt")
    assert h.page.is_visible(".noyvj-hints")
    h.page.evaluate("__unbind()")
    h.page.uncheck("#opt")
    assert h.page.is_visible(".noyvj-hints")


def test_change_event_and_refresh_all_and_destroy(harness):
    h = mount(open_page(harness))
    press(h)
    h.page.evaluate("__puzzle = " + repr(P2).replace("'", '"') + "; document.dispatchEvent(new CustomEvent('noyvj-hints-change', {detail: {game: 'other'}}))")
    assert shown(h)[0][1] == P1["nudge"]                                            # an event for another game is ignored
    h.page.evaluate("document.dispatchEvent(new CustomEvent('noyvj-hints-change', {detail: {game: 'logic'}}))")
    assert shown(h) == [] and button(h) == "Need a hint?"                           # now it follows the game's new puzzle
    press(h)
    h.page.evaluate("__puzzle = " + repr(P1).replace("'", '"') + "; NoyvjHints.refreshAll()")
    assert shown(h) == []
    h.page.evaluate("__ladder.destroy(); NoyvjHints.refreshAll()")
    assert h.page.locator(".noyvj-hints").count() == 0


def test_a_press_after_the_game_moved_on_resets_instead_of_revealing_the_wrong_puzzle(harness):
    h = mount(open_page(harness))
    press(h)
    h.page.evaluate("__puzzle = " + repr(P2).replace("'", '"'))                      # the game forgot to call refresh()
    press(h)
    assert shown(h) == [] and button(h) == "Need a hint?"
    assert h.page.evaluate("__revealed") == [["nudge", "L1"]]
    press(h)
    assert shown(h) == [["Nudge", "Second nudge."]]


def test_links_its_own_stylesheet_when_the_page_forgot(harness):
    h = open_page(harness, page=PAGE_NO_LINK)
    mount(h)
    h.page.wait_for_function("getComputedStyle(document.querySelector('.noyvj-hints')).borderTopWidth === '1px'")
    assert h.page.locator("link[href*='hint-ladder.css']").count() == 1


def test_no_timers_no_network_no_urgency_wording(harness):
    counter = ("window.__timers = 0; for (const n of ['setTimeout', 'setInterval', 'requestAnimationFrame']) {"
               "const o = window[n]; window[n] = function () { window.__timers++; return o.apply(this, arguments); }; }")
    h = open_page(harness, init=[counter])
    mount(h)
    reveal_all(h)
    h.page.evaluate("__ladder.reset(); __ladder.setEnabled(false); __ladder.setEnabled(true); NoyvjHints.stats('logic')")
    assert h.page.evaluate("window.__timers") == 0
    assert h.api_calls == []
    h.page.evaluate("__ladder.reset()")
    press(h)
    body = h.page.inner_text(".noyvj-hints").lower()
    assert not re.search(r"timer|expires|hurry|deadline|left to|countdown|\d+:\d\d", body)
    assert not [m for m in h.console if m[0] in ("error", "warning")]


def test_rungs_are_not_colour_alone(harness):
    h = mount(open_page(harness))
    reveal_all(h)
    marks = h.page.evaluate("""() => [...document.querySelectorAll('.noyvj-hints-label')].map(e => getComputedStyle(e, '::before').content)""")
    assert len(set(marks)) == 3 and "none" not in marks
    styles = h.page.evaluate("""() => [...document.querySelectorAll('.noyvj-hints-item')].map(e => getComputedStyle(e).borderLeftStyle)""")
    assert styles == ["solid", "dashed", "double"]


# ---- keyboard --------------------------------------------------------------------------------
def test_works_from_the_keyboard_with_enter_and_space(harness):
    h = mount(open_page(harness))
    h.page.focus(".noyvj-hints-ask")
    h.page.keyboard.press("Enter")
    assert shown(h) == [["Nudge", P1["nudge"]]]
    assert h.page.evaluate("document.activeElement.className") == "noyvj-hints-ask"   # focus stays on the button
    h.page.keyboard.press("Space")
    assert [r[0] for r in shown(h)] == ["Nudge", "Hint"]
    h.page.keyboard.press("Enter")                                                  # asks
    assert h.page.evaluate("document.activeElement.className") == "noyvj-hints-no"
    h.page.keyboard.press("Shift+Tab")
    assert h.page.evaluate("document.activeElement.className") == "noyvj-hints-yes"
    h.page.keyboard.press("Enter")
    assert [r[0] for r in shown(h)] == ["Nudge", "Hint", "Answer"]
    assert h.page.evaluate("document.activeElement.classList.contains('noyvj-hints-item')")
    assert h.page.evaluate("document.activeElement.tagName") == "LI"


# ---- look: sizes, themes, reduced motion -----------------------------------------------------
@pytest.mark.parametrize("size", [(1440, 900), (360, 740)])
@pytest.mark.parametrize("theme", ["dark", "light"])
def test_fits_with_44px_controls_and_no_overflow(harness, size, theme):
    h = open_page(harness, size=size, touch=size[0] < 500, theme=theme)
    mount(h, {"id": "long", "nudge": "word " * 30, "hint": "x" * 120, "answer": "answer " * 20})
    press(h)
    press(h)
    press(h)                                                                        # confirm showing
    boxes = h.page.evaluate("""() => ['.noyvj-hints-yes', '.noyvj-hints-no'].map(s => { const r = document.querySelector(s).getBoundingClientRect(); return [r.width, r.height]; })""")
    assert min(min(b) for b in boxes) >= 44
    assert h.page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    h.page.click(".noyvj-hints-yes")
    assert h.page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    box = h.page.evaluate("(() => { const r = document.querySelector('.noyvj-hints').getBoundingClientRect(); return [r.left, r.right]; })()")
    assert box[0] >= 0 and box[1] <= size[0]
    h.page.evaluate("__puzzle = {id: 'short', nudge: 'n', hint: 'h'}; __ladder.refresh()")
    ask = h.page.evaluate("(() => { const r = document.querySelector('.noyvj-hints-ask').getBoundingClientRect(); return [r.width, r.height]; })()")
    assert min(ask) >= 44


def lum(css):
    r, g, b = [int(float(x)) for x in re.findall(r"[\d.]+", css)[:3]]
    f = lambda c: ((c / 255 + 0.055) / 1.055) ** 2.4 if c / 255 > 0.03928 else c / 255 / 12.92  # noqa: E731
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)


def test_light_and_dark_tokens_differ_and_text_is_legible(harness):
    seen = {}
    for theme in ("dark", "light"):
        h = mount(open_page(harness, theme=theme))
        press(h)
        seen[theme] = h.page.evaluate("""() => { const s = getComputedStyle(document.querySelector('.noyvj-hints'));
          return [s.backgroundColor, s.color, getComputedStyle(document.querySelector('.noyvj-hints-tally')).color,
                  getComputedStyle(document.querySelector('.noyvj-hints-label')).color]; }""")
    assert seen["dark"] != seen["light"]
    for theme, (bg, fg, muted, label) in seen.items():
        page_bg = 0.01 if theme == "dark" else 0.85
        lb = lum(bg) * 0.78 + page_bg * 0.22 if "rgba" in bg else lum(bg)
        for colour in (fg, muted, label):
            lf = lum(colour)
            assert (max(lb, lf) + 0.05) / (min(lb, lf) + 0.05) >= 4.5, (theme, colour)


def test_os_light_preference_is_followed_without_a_theme_attribute(harness):
    h = harness(media={"color_scheme": "light"})
    h.pages["/t.html"] = PAGE
    h.goto()
    mount(h)
    assert h.page.evaluate("getComputedStyle(document.querySelector('.noyvj-hints')).color") == "rgb(27, 32, 51)"


def test_motion_only_when_allowed(harness):
    h = mount(open_page(harness))
    press(h)
    css = "getComputedStyle(document.querySelector('.noyvj-hints-item')).animationName"
    assert h.page.evaluate(css) == "noyvj-hints-in"
    h.page.evaluate("document.documentElement.setAttribute('data-reduced-motion', 'true')")
    assert h.page.evaluate(css) == "none"
    os_reduced = harness(media={"reduced_motion": "reduce"})
    os_reduced.pages["/t.html"] = PAGE
    os_reduced.goto()
    mount(os_reduced)
    press(os_reduced)
    assert os_reduced.page.evaluate(css) == "none"
    os_reduced.page.wait_for_function("document.querySelector('.noyvj-hints-sr').textContent.startsWith('Nudge')")   # still announced


def test_screen_reader_only_text_is_not_visible_on_screen(harness):
    h = mount(open_page(harness))
    size = h.page.evaluate("(() => { const r = document.querySelector('.noyvj-hints-sr').getBoundingClientRect(); return [r.width, r.height]; })()")
    assert size[0] <= 1 and size[1] <= 1


def test_hidden_attribute_wins_over_class_display(harness):
    h = mount(open_page(harness))
    assert h.page.evaluate("getComputedStyle(document.querySelector('.noyvj-hints-confirm')).display") == "none"
    assert h.page.evaluate("getComputedStyle(document.querySelector('.noyvj-hints-list')).display") == "none"
