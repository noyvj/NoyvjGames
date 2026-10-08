"""shared/goals-panel.js + goals-panel.css in headless Chromium (planning/TODO.md FY-53): at most three
goals at a time, progress bar plus text, promotion from the game's queue, polite announcements, no
timers, hides when there is nothing to show, an on/off hook, themes, 44 px, 360 px, reduced motion.
The panel never decides a rule: it only shows what the game's getGoals() says. No network."""

import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from conftest import page_html  # noqa: E402

STYLE = ('<style>body{margin:0;padding:12px;font-family:system-ui;background:#12162a;color:#eee}'
         'html[data-theme="light"] body{background:#eef2fc;color:#1b2033}</style>')
PAGE = page_html(STYLE + '<link rel="stylesheet" href="/shared/goals-panel.css">',
                 '<h1>Game</h1><div id="slot"></div><label><input type="checkbox" id="opt"> Show goals</label>'
                 '<script src="/shared/goals-panel.js"></script>')
PAGE_NO_LINK = page_html(STYLE, '<div id="slot"></div><script src="/shared/goals-panel.js"></script>')

GOALS = [
    {"id": "smelters", "label": "Reach 5 Smelters", "current": 3, "target": 5, "reward": "Unlocks the Foundry", "done": False},
    {"id": "ore", "label": "Mine 1000 ore", "progress": {"current": 250, "target": 1000}, "reward": "+10% ore", "done": False},
    {"id": "visit", "label": "Open the Archive", "reward": "A new tab", "done": False},
    {"id": "furnaces", "label": "Reach 10 Furnaces", "current": 0, "target": 10, "reward": "Unlocks Alloys", "done": False},
    {"id": "first", "label": "Build a Smelter", "current": 1, "target": 1, "done": True},
]

SETUP = """(goals) => {
  window.__goals = goals;
  window.__panel = NoyvjGoals.mount('#slot', {game: 'sol', goals: () => window.__goals,
    onChange: (v) => (window.__changes = (window.__changes || 0) + 1)});
}"""


def open_page(harness, page=PAGE, init=(), size=(1440, 900), theme=None, **kw):
    h = harness(size=size, init_scripts=list(init), **kw)
    h.pages["/t.html"] = page
    h.goto()
    if theme:
        h.page.evaluate("t => document.documentElement.setAttribute('data-theme', t)", theme)
    return h


def mount(h, goals=GOALS):
    h.page.evaluate(SETUP, goals)
    return h


def texts(h):
    return h.page.evaluate("[...document.querySelectorAll('.noyvj-goals-item .noyvj-goals-text')].map(e => e.textContent)")


def finish(h, gid):
    h.page.evaluate("""(gid) => { const g = __goals.find((x) => x.id === gid); g.done = true;
      if (g.target) g.current = g.target; __panel.refresh(); }""", gid)


# --------------------------------------------------------------------------------------------
def test_shows_the_first_three_unfinished_goals_with_text_bar_and_reward(harness):
    h = mount(open_page(harness))
    assert texts(h) == ["Reach 5 Smelters: 3 of 5", "Mine 1000 ore: 250 of 1,000", "Open the Archive"]
    assert h.page.locator(".noyvj-goals-item").count() == 3
    rewards = h.page.evaluate("[...document.querySelectorAll('.noyvj-goals-item')].map(li => li.querySelector('.noyvj-goals-reward').textContent)")
    assert rewards == ["Reward: Unlocks the Foundry", "Reward: +10% ore", "Reward: A new tab"]
    widths = h.page.evaluate("[...document.querySelectorAll('.noyvj-goals-fill')].map(e => e.style.width)")
    assert widths[:2] == ["60%", "25%"]
    bars_visible = h.page.evaluate("[...document.querySelectorAll('.noyvj-goals-bar')].map(e => !e.hidden)")
    assert bars_visible == [True, True, False]                                   # a plain tick has no bar
    assert h.page.inner_text(".noyvj-goals-tally") == "1 of 5 done"
    assert h.page.inner_text(".noyvj-goals-title") == "Goals"
    assert not h.errors


def test_never_more_than_three_whatever_the_game_asks(harness):
    h = open_page(harness)
    h.page.evaluate("""(goals) => { window.__goals = goals; window.__panel = NoyvjGoals.mount('#slot', {game: 'a', goals, maxVisible: 99}); }""", GOALS)
    assert h.page.locator(".noyvj-goals-item").count() == 3
    two = open_page(harness)
    two.page.evaluate("""(goals) => { NoyvjGoals.mount('#slot', {game: 'a', goals, maxVisible: 2}); }""", GOALS)
    assert two.page.locator(".noyvj-goals-item").count() == 2
    assert two.page.evaluate("NoyvjGoals.MAX_VISIBLE") == 3


def test_semantics_list_region_and_hidden_decorations(harness):
    h = mount(open_page(harness))
    assert h.page.evaluate("document.querySelector('.noyvj-goals').tagName") == "SECTION"
    title_id = h.page.get_attribute(".noyvj-goals", "aria-labelledby")
    assert h.page.inner_text("#" + title_id) == "Goals"
    assert h.page.evaluate("document.querySelector('.noyvj-goals-list').tagName") == "UL"
    assert h.page.evaluate("[...document.querySelectorAll('.noyvj-goals-list > *')].every(e => e.tagName === 'LI')")
    assert h.page.get_attribute(".noyvj-goals-list", "aria-labelledby") == title_id
    assert h.page.get_attribute(".noyvj-goals-bar", "aria-hidden") == "true"      # the text already says "3 of 5"
    live = ".noyvj-goals-sr"
    assert h.page.get_attribute(live, "role") == "status" and h.page.get_attribute(live, "aria-live") == "polite"
    assert h.page.get_attribute(".noyvj-goals", "tabindex") == "-1"
    h.page.evaluate("__panel.focus()")
    assert h.page.evaluate("document.activeElement.classList.contains('noyvj-goals')")


def test_labels_and_rewards_are_text_never_markup(harness):
    h = open_page(harness)
    h.page.evaluate("""() => NoyvjGoals.mount('#slot', {game: 'x', goals: [{id: 'a', label: '<b>Bold</b> <img src=x onerror="window.__p=1">', current: 1, target: 2, reward: '<i>r</i>'}]})""")
    assert h.page.locator("#slot b, #slot img, #slot i").count() == 0
    assert h.page.evaluate("window.__p") is None
    assert "<b>Bold</b>" in h.page.inner_text(".noyvj-goals-text")


def test_completing_a_goal_promotes_the_next_and_announces_it(harness):
    h = mount(open_page(harness))
    assert h.page.inner_text(".noyvj-goals-sr") == ""                              # the first paint is silent
    assert h.page.is_hidden(".noyvj-goals-note")
    finish(h, "smelters")
    h.page.wait_for_function("document.querySelector('.noyvj-goals-sr').textContent !== ''")
    said = h.page.evaluate("document.querySelector('.noyvj-goals-sr').textContent")
    assert said == "Goal complete: Reach 5 Smelters. Reward: Unlocks the Foundry. New goal: Reach 10 Furnaces."
    assert texts(h) == ["Mine 1000 ore: 250 of 1,000", "Open the Archive", "Reach 10 Furnaces: 0 of 10"]
    note = h.page.inner_text(".noyvj-goals-note-text")
    assert note == "✓ Done: Reach 5 Smelters. Reward: Unlocks the Foundry"
    assert h.page.inner_text(".noyvj-goals-tally") == "2 of 5 done"
    assert h.page.get_attribute(".noyvj-goals-note", "aria-live") is None          # only one live region speaks
    h.page.click(".noyvj-goals-dismiss")
    assert h.page.is_hidden(".noyvj-goals-note")
    assert h.page.get_attribute(".noyvj-goals-dismiss", "aria-label")


def test_two_goals_finished_at_once_are_both_announced(harness):
    h = mount(open_page(harness))
    h.page.evaluate("""() => { __goals[0].done = true; __goals[1].done = true; __panel.refresh(); }""")
    h.page.wait_for_function("document.querySelector('.noyvj-goals-sr').textContent !== ''")
    said = h.page.evaluate("document.querySelector('.noyvj-goals-sr').textContent")
    assert said.startswith("Goal complete: Reach 5 Smelters.") and "Goal complete: Mine 1000 ore." in said
    assert texts(h) == ["Open the Archive", "Reach 10 Furnaces: 0 of 10"]


def test_the_last_goal_ends_in_an_every_goal_done_message(harness):
    h = open_page(harness)
    goals = [{"id": "a", "label": "One", "current": 0, "target": 1, "done": False}]
    mount(h, goals)
    finish(h, "a")
    h.page.wait_for_function("document.querySelector('.noyvj-goals-sr').textContent.includes('Every goal is done')")
    assert h.page.locator(".noyvj-goals-item").count() == 0
    assert "Every goal is done" in h.page.inner_text(".noyvj-goals-done")
    assert h.page.is_visible(".noyvj-goals-done") and h.page.inner_text(".noyvj-goals-tally") == "1 of 1 done"


def test_refresh_updates_in_place_and_only_calls_back_on_real_change(harness):
    h = mount(open_page(harness))
    h.page.evaluate("document.querySelector('.noyvj-goals-item').__mine = 'same node'")
    h.page.evaluate("() => { __goals[0].current = 4; __panel.refresh(); }")
    assert h.page.evaluate("document.querySelector('.noyvj-goals-item').__mine") == "same node"
    assert texts(h)[0] == "Reach 5 Smelters: 4 of 5"
    assert h.page.evaluate("document.querySelector('.noyvj-goals-fill').style.width") == "80%"
    before = h.page.evaluate("__changes")
    h.page.evaluate("__panel.refresh(); __panel.refresh()")
    assert h.page.evaluate("__changes") == before                                  # nothing changed, no callback
    assert h.page.evaluate("__panel.visibleIds()") == ["smelters", "ore", "visit"]


def test_the_panel_never_decides_a_rule(harness):
    h = open_page(harness)
    mount(h, [{"id": "a", "label": "Held back", "current": 9, "target": 5, "done": False},
              {"id": "b", "label": "Implied", "current": 5, "target": 5}])
    assert texts(h) == ["Held back: 5 of 5"]                                      # explicit done:false wins; display is clamped
    assert h.page.evaluate("document.querySelector('.noyvj-goals-fill').style.width") == "100%"
    assert h.page.inner_text(".noyvj-goals-tally") == "1 of 2 done"                # b has no done flag, so it is derived


def test_bad_goal_data_is_ignored(harness):
    h = open_page(harness)
    mount(h, [None, 5, "x", {}, {"id": "", "label": "no id"}, {"id": "x"}, {"id": "ok", "label": "Fine", "current": -4, "target": "bad"},
              {"id": "ok", "label": "Duplicate id"}, {"id": 7, "label": "Numeric id", "current": 1, "target": 2}])
    assert texts(h) == ["Fine", "Numeric id: 1 of 2"]
    h.page.evaluate("__goals = 'nonsense'; __panel.refresh()")
    assert h.page.is_hidden(".noyvj-goals")
    h.page.evaluate("__goals = () => { throw new Error('boom'); }; __panel.refresh()")
    assert h.page.is_hidden(".noyvj-goals")
    assert not h.errors


def test_hides_itself_when_the_game_has_no_goals_and_returns_when_it_has_some(harness):
    h = open_page(harness)
    mount(h, [])
    assert h.page.is_hidden(".noyvj-goals")
    assert h.page.evaluate("document.querySelector('.noyvj-goals').hidden")
    h.page.evaluate("__goals = [{id: 'a', label: 'Later goal', current: 0, target: 3}]; __panel.refresh()")
    assert h.page.is_visible(".noyvj-goals") and texts(h) == ["Later goal: 0 of 3"]
    assert h.page.inner_text(".noyvj-goals-sr") == ""                              # appearing is not a completion


def test_enabled_switch_hides_remembers_and_stays_quiet(harness):
    h = mount(open_page(harness))
    h.page.evaluate("__panel.setEnabled(false)")
    assert h.page.is_hidden(".noyvj-goals") and h.page.evaluate("__panel.isEnabled()") is False
    assert h.page.evaluate("localStorage.getItem('noyvj-goals:sol')") == "off"
    finish(h, "smelters")                                                           # completes while switched off
    h.page.evaluate("__panel.setEnabled(true)")
    assert h.page.is_visible(".noyvj-goals")
    assert texts(h)[0] == "Mine 1000 ore: 250 of 1,000"
    assert h.page.evaluate("document.querySelector('.noyvj-goals-sr').textContent") == ""   # no announcement for what happened while off
    assert h.page.evaluate("localStorage.getItem('noyvj-goals:sol')") == "on"
    h.page.evaluate("__panel.setEnabled(false)")
    h.page.reload()
    h.page.evaluate(SETUP, GOALS)                                                   # a fresh mount remembers the choice
    assert h.page.is_hidden(".noyvj-goals") and h.page.evaluate("__panel.isEnabled()") is False


def test_enabled_option_overrides_the_stored_choice_and_callback_fires(harness):
    h = open_page(harness)
    h.page.evaluate("localStorage.setItem('noyvj-goals:sol', 'off')")
    h.page.evaluate("""(goals) => { window.__f = []; window.__panel = NoyvjGoals.mount('#slot', {game: 'sol', goals, enabled: true,
      onEnabledChange: (on) => __f.push(on)}); }""", GOALS)
    assert h.page.is_visible(".noyvj-goals")
    h.page.evaluate("__panel.setEnabled(false, {persist: false}); __panel.setEnabled(false); __panel.setEnabled(true)")
    assert h.page.evaluate("__f") == [False, True]


def test_bind_checkbox_two_way(harness):
    h = mount(open_page(harness))
    h.page.evaluate("() => { window.__unbind = NoyvjGoals.bindCheckbox(__panel, '#opt'); }")
    assert h.page.is_checked("#opt")
    h.page.uncheck("#opt")
    assert h.page.is_hidden(".noyvj-goals")
    h.page.check("#opt")
    assert h.page.is_visible(".noyvj-goals")
    h.page.evaluate("__unbind()")
    h.page.uncheck("#opt")
    assert h.page.is_visible(".noyvj-goals")


def test_change_event_refreshes_panels_and_can_name_a_game(harness):
    h = mount(open_page(harness))
    h.page.evaluate("__goals[0].current = 5; document.dispatchEvent(new CustomEvent('noyvj-goals-change', {detail: {game: 'other'}}))")
    assert texts(h)[0] == "Reach 5 Smelters: 3 of 5"
    h.page.evaluate("document.dispatchEvent(new CustomEvent('noyvj-goals-change', {detail: {game: 'sol'}}))")
    assert texts(h)[0] == "Reach 5 Smelters: 5 of 5"
    h.page.evaluate("__goals[0].current = 1; document.dispatchEvent(new CustomEvent('noyvj-goals-change'))")
    assert texts(h)[0] == "Reach 5 Smelters: 1 of 5"
    h.page.evaluate("__goals[0].current = 2; NoyvjGoals.refreshAll()")
    assert texts(h)[0] == "Reach 5 Smelters: 2 of 5"
    h.page.evaluate("__panel.destroy(); __goals[0].current = 4; NoyvjGoals.refreshAll()")
    assert h.page.locator(".noyvj-goals").count() == 0


def test_no_timers_no_network_no_markup_injection(harness):
    counter = ("window.__timers = 0; for (const n of ['setTimeout', 'setInterval', 'requestAnimationFrame']) {"
               "const o = window[n]; window[n] = function () { window.__timers++; return o.apply(this, arguments); }; }")
    h = open_page(harness, init=[counter])
    mount(h)
    finish(h, "smelters")
    h.page.evaluate("__panel.refresh(); __panel.setEnabled(false); __panel.setEnabled(true)")
    assert h.page.evaluate("window.__timers") == 0
    assert h.api_calls == []
    # no countdown or urgency wording anywhere in the panel
    body = h.page.inner_text(".noyvj-goals").lower()
    assert not re.search(r"timer|expires|hurry|deadline|left to|countdown|\d+:\d\d", body)


def test_links_its_own_stylesheet_when_the_page_forgot(harness):
    h = open_page(harness, page=PAGE_NO_LINK)
    mount(h)
    h.page.wait_for_function("getComputedStyle(document.querySelector('.noyvj-goals')).borderTopWidth === '1px'")
    assert h.page.locator("link[href*='goals-panel.css']").count() == 1


def test_progress_is_not_colour_alone(harness):
    h = mount(open_page(harness))
    bar = h.page.evaluate("""() => { const s = getComputedStyle(document.querySelector('.noyvj-goals-bar'));
      return [s.borderTopWidth, s.borderTopStyle]; }""")
    assert bar == ["1px", "solid"]
    assert h.page.evaluate("getComputedStyle(document.querySelector('.noyvj-goals-text'), '::before').content") != "none"
    assert "3 of 5" in texts(h)[0]


# --------------------------------------------------------------------------------------------
# Look: sizes, themes, reduced motion
# --------------------------------------------------------------------------------------------
@pytest.mark.parametrize("size", [(1440, 900), (360, 740)])
@pytest.mark.parametrize("theme", ["dark", "light"])
def test_fits_compactly_with_44px_controls_and_no_overflow(harness, size, theme):
    h = open_page(harness, size=size, touch=size[0] < 500, theme=theme)
    mount(h)
    finish(h, "smelters")                                                           # shows the dismissible note too
    assert h.page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    box = h.page.evaluate("(() => { const r = document.querySelector('.noyvj-goals').getBoundingClientRect(); return [r.right, r.height]; })()")
    assert box[0] <= size[0] and box[1] < 330
    dismiss = h.page.evaluate("(() => { const r = document.querySelector('.noyvj-goals-dismiss').getBoundingClientRect(); return [r.width, r.height]; })()")
    assert min(dismiss) >= 44
    assert h.page.evaluate("""[...document.querySelectorAll('.noyvj-goals-text, .noyvj-goals-reward')].every(e => e.scrollWidth <= e.clientWidth + 1)""")


def lum(css):
    r, g, b = [int(float(x)) for x in re.findall(r"[\d.]+", css)[:3]]
    f = lambda c: ((c / 255 + 0.055) / 1.055) ** 2.4 if c / 255 > 0.03928 else c / 255 / 12.92  # noqa: E731
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)


def test_light_and_dark_tokens_differ_and_text_is_legible(harness):
    seen = {}
    for theme in ("dark", "light"):
        h = mount(open_page(harness, theme=theme))
        seen[theme] = h.page.evaluate("""() => { const s = getComputedStyle(document.querySelector('.noyvj-goals'));
          return [s.backgroundColor, s.color, getComputedStyle(document.querySelector('.noyvj-goals-reward')).color,
                  getComputedStyle(document.querySelector('.noyvj-goals-fill')).backgroundColor]; }""")
    assert seen["dark"] != seen["light"]
    for theme, (bg, fg, muted, fill) in seen.items():
        page_bg = 0.01 if theme == "dark" else 0.85
        lb = lum(bg) * 0.78 + page_bg * 0.22 if "rgba" in bg else lum(bg)
        for colour in (fg, muted):
            lf = lum(colour)
            assert (max(lb, lf) + 0.05) / (min(lb, lf) + 0.05) >= 4.5, (theme, colour)
        assert fill != bg


def test_motion_only_when_allowed(harness):
    h = mount(open_page(harness))
    finish(h, "smelters")                                                           # promotes "furnaces": it gets the pop class
    css = "getComputedStyle(document.querySelector('.noyvj-goals-item--new')).animationName"
    assert h.page.locator(".noyvj-goals-item--new").count() == 1
    assert h.page.evaluate(css) == "noyvj-goals-pop"
    assert h.page.evaluate("getComputedStyle(document.querySelector('.noyvj-goals-fill')).transitionDuration") != "0s"
    h.page.evaluate("document.documentElement.setAttribute('data-reduced-motion', 'true')")
    assert h.page.evaluate(css) == "none"
    assert h.page.evaluate("getComputedStyle(document.querySelector('.noyvj-goals-fill')).transitionDuration") == "0s"
    os_reduced = harness(media={"reduced_motion": "reduce"})
    os_reduced.pages["/t.html"] = PAGE
    os_reduced.goto()
    mount(os_reduced)
    finish(os_reduced, "smelters")
    assert os_reduced.page.evaluate(css) == "none"
    assert os_reduced.page.evaluate("getComputedStyle(document.querySelector('.noyvj-goals-fill')).transitionDuration") == "0s"
    # the announcement is made either way
    os_reduced.page.wait_for_function("document.querySelector('.noyvj-goals-sr').textContent.startsWith('Goal complete')")


def test_the_pop_class_goes_away_on_the_next_refresh(harness):
    h = mount(open_page(harness))
    finish(h, "smelters")
    assert h.page.locator(".noyvj-goals-item--new").count() == 1
    h.page.evaluate("__panel.refresh()")
    assert h.page.locator(".noyvj-goals-item--new").count() == 0


def test_screen_reader_only_text_is_not_visible_on_screen(harness):
    h = mount(open_page(harness))
    size = h.page.evaluate("(() => { const r = document.querySelector('.noyvj-goals-sr').getBoundingClientRect(); return [r.width, r.height]; })()")
    assert size[0] <= 1 and size[1] <= 1
